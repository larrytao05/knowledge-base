import logging
import secrets
import time
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.deps import Vault
from app.models import Check, Node, NodeLink
from app.schemas import NodeUpdate
from app.services.agent import CheckResult
from app.services.indexer import sync_vault, title_from_frontmatter
from app.services.locks import path_lock
from app.services.vault_io import (
    allocate_path,
    atomic_write,
    read_note,
    safe_join,
    serialize_note,
    slugify,
)
from app.services.wikilinks import is_linkable_title, normalize_title, rewrite_links

logger = logging.getLogger(__name__)


class StaleContentError(Exception):
    """Raised when a PATCH's content_hash no longer matches the file on disk."""


class MalformedNoteError(Exception):
    """Raised when trying to write to a node whose frontmatter failed to parse."""


class UnlinkableTitleError(Exception):
    """Raised when a rename would leave the note unaddressable by any wikilink.
    Only renames are held to this - a title already on disk is taken as it is."""


class TitleConflictError(Exception):
    """Raised when a rename would collide with another note's title. Duplicate
    titles are tolerated in general, but a rename also rewrites `[[old title]]`
    in other files, and that rewrite can't be undone by renaming back."""


def _new_id() -> str:
    return secrets.token_hex(6)


def _iso_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def create_node(
    db: Session,
    vault: Vault,
    *,
    title: str,
    body: str,
    tags: list[str],
) -> Node:
    node_id = _new_id()
    path = allocate_path(vault.root, slugify(title))

    frontmatter: dict[str, object] = {"id": node_id, "title": title}
    if tags:
        frontmatter["tags"] = tags
    frontmatter["created"] = _iso_now()

    atomic_write(path, serialize_note(frontmatter, body))
    sync_vault(db, vault.root)

    node = db.get(Node, node_id)
    if node is None:
        raise RuntimeError(f"node {node_id} missing from index immediately after sync")
    return node


def _title_taken(db: Session, new_norm: str, skip_id: str) -> bool:
    stmt = select(Node.id).where(
        Node.title_norm == new_norm, Node.kind == "note", Node.id != skip_id
    )
    return db.scalars(stmt).first() is not None


def _inbound_link_sources(old_norm: str, *, skip_id: str) -> Select[tuple[Node]]:
    # Check notes link to the node they report on, but they aren't notes the user
    # wrote or can see - counting them would overstate what a rename touched.
    return (
        select(Node)
        .join(NodeLink, NodeLink.source_id == Node.id)
        .where(NodeLink.target_norm == old_norm, Node.kind == "note", Node.id != skip_id)
        .distinct()
    )


def _malformed_note_sources(skip_id: str) -> Select[tuple[Node]]:
    return select(Node).where(
        Node.kind == "note", Node.fm_error.is_not(None), Node.id != skip_id
    )


def _rewrite_inbound_links(
    db: Session, vault: Vault, *, old_norm: str, new_title: str, skip_id: str
) -> int:
    """Retarget `[[old title]]` in every other note at the new title. The files
    are the source of truth, so the index is only used to pick candidates - each
    one is re-read from disk and rewritten in place.

    A file that can't be rewritten is logged and counted rather than raised: the
    rename itself is already on disk, so failing the whole request here would
    report an edit that actually applied as a write failure, and would skip the
    reindex that the rewritten files still need. The count goes back to the
    client so a partial rewrite isn't reported as a clean one."""
    backup_dir = vault.root / ".vault-backups"
    skipped = 0

    indexed = list(db.scalars(_inbound_link_sources(old_norm, skip_id=skip_id)))
    # A note whose frontmatter failed to parse has no link rows for the index to
    # nominate, but its body can still hold the link, and rewriting works off the
    # raw text so the broken frontmatter is carried through untouched.
    seen = {other.id for other in indexed}
    malformed = [
        other
        for other in db.scalars(_malformed_note_sources(skip_id=skip_id))
        if other.id not in seen
    ]

    for other, from_index in [(o, True) for o in indexed] + [(o, False) for o in malformed]:
        path = safe_join(vault.root, *Path(other.path).parts)
        try:
            with path_lock(path):
                text = path.read_text(encoding="utf-8")
                rewritten = rewrite_links(text, old_norm, new_title)
                if rewritten == text:
                    # The index says this file links here, so finding nothing to
                    # rewrite means the two disagree about the target - report it
                    # rather than let a dangling link pass as a clean rename. A
                    # malformed note was only a guess, so a miss there is normal.
                    if from_index:
                        skipped += 1
                        logger.warning(
                            "no link to retarget in %s despite an index entry", other.path
                        )
                    continue
                atomic_write(path, rewritten, backup_dir=backup_dir)
        except OSError as exc:
            skipped += 1
            logger.warning("could not retarget links in %s: %s", other.path, exc)

    return skipped


def update_node(
    db: Session, vault: Vault, node: Node, payload: NodeUpdate
) -> tuple[Node, int, int]:
    """Returns the reindexed note, how many inbound-link rewrites failed, and how
    many were deliberately left pointing at the old title."""
    if node.fm_error is not None:
        raise MalformedNoteError(node.fm_error)

    path = safe_join(vault.root, *Path(node.path).parts)
    provided = payload.model_fields_set

    with path_lock(path):
        current = read_note(path)
        if current.content_hash != payload.content_hash:
            raise StaleContentError(node.id)

        old_title = title_from_frontmatter(current) or path.stem
        new_title = old_title
        frontmatter = dict(current.frontmatter)
        if "title" in provided and payload.title is not None:
            frontmatter["title"] = payload.title
            new_title = payload.title
        if "tags" in provided:
            if payload.tags:
                frontmatter["tags"] = payload.tags
            else:
                frontmatter.pop("tags", None)

        body = payload.body if "body" in provided and payload.body is not None else current.body

        old_norm = normalize_title(old_title)
        new_norm = normalize_title(new_title)
        renamed = new_norm != old_norm
        if renamed and not is_linkable_title(new_title):
            raise UnlinkableTitleError(new_title)
        if renamed and _title_taken(db, new_norm, node.id):
            raise TitleConflictError(new_title)
        # Another note keeping the old title makes every `[[old title]]` mean
        # that one, including the ones in this note's own body - so the same
        # guard the inbound rewrite uses has to hold here too, or a reference to
        # the other note would quietly become a self-reference.
        shared_old_title = renamed and _title_taken(db, old_norm, node.id)
        if renamed and not shared_old_title:
            # Self-links go through this write rather than the loop below, which
            # has to skip this note to avoid clobbering what is written here.
            body = rewrite_links(body, old_norm, new_title)

        backup_dir = vault.root / ".vault-backups"
        atomic_write(path, serialize_note(frontmatter, body), backup_dir=backup_dir)

    skipped = 0
    left_alone = 0
    if shared_old_title:
        # Inbound links are left alone for the same reason: the old title is now
        # unambiguous, so they resolve to the note that kept it. Nothing failed
        # here, so this is counted apart from the rewrites that did.
        left_alone = len(list(db.scalars(_inbound_link_sources(old_norm, skip_id=node.id))))
    elif renamed:
        skipped = _rewrite_inbound_links(
            db, vault, old_norm=old_norm, new_title=new_title, skip_id=node.id
        )

    sync_vault(db, vault.root)

    updated = db.get(Node, node.id)
    if updated is None:
        raise RuntimeError(f"node {node.id} missing from index immediately after sync")
    return updated, skipped, left_alone


def write_check_note(db: Session, vault: Vault, node: Node, result: CheckResult) -> Check:
    check_id = _new_id()
    slug = f"{slugify(node.title)}-{int(time.time())}"
    path = allocate_path(vault.root, slug, subdir="checks")

    frontmatter: dict[str, object] = {
        "id": check_id,
        "type": "check",
        "node_id": node.id,
        "verdict": result.verdict,
        "checked": _iso_now(),
        "sources": [s.model_dump() for s in result.sources],
    }
    # A title no wikilink can address is referenced as plain text rather than as
    # a `[[link]]` that would parse as something else entirely.
    reference = f"[[{node.title}]]" if is_linkable_title(node.title) else node.title
    body = f"Check of {reference} - verdict: {result.verdict}\n\n{result.reasoning}\n"

    atomic_write(path, serialize_note(frontmatter, body))
    sync_vault(db, vault.root)

    check = db.get(Check, check_id)
    if check is None:
        raise RuntimeError(f"check {check_id} missing from index immediately after sync")
    return check
