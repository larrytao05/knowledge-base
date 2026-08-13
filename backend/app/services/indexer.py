import re
import secrets
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Check, Node, NodeLink
from app.services.vault_io import (
    ParsedNote,
    file_signature,
    iter_note_files,
    read_note,
    stamp_id,
)
from app.services.wikilinks import extract_links, normalize_title

_ID_RE = re.compile(r"[a-f0-9]{12}")
_RECENT_WRITE_NS = 2_000_000_000
VALID_VERDICTS = {"on_track", "diverging", "unclear"}


@dataclass
class SyncStats:
    added: int = 0
    updated: int = 0
    removed: int = 0
    errors: list[str] = field(default_factory=list)


def _new_id() -> str:
    return secrets.token_hex(6)


def _coerce_tags(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(t) for t in value if isinstance(t, str | int | float)]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _coerce_datetime(value: Any, mtime_ns: int) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            pass
    return datetime.fromtimestamp(mtime_ns / 1e9, tz=UTC)


def _title_from_frontmatter(parsed: ParsedNote) -> str | None:
    if parsed.error is not None:
        return None
    title = parsed.frontmatter.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    return None


def _is_dirty(existing: Node | None, mtime_ns: int, size: int) -> bool:
    if existing is None:
        return True
    if (existing.mtime_ns, existing.size) != (mtime_ns, size):
        return True
    return abs(time.time_ns() - mtime_ns) < _RECENT_WRITE_NS


def _resolve_id_and_existing(
    path: Path,
    parsed: ParsedNote,
    existing_by_path: Node | None,
    existing_by_id: dict[str, Node],
) -> tuple[str, ParsedNote, Node | None]:
    """Resolve the stable id for a file and the DB row it corresponds to (if
    any). Frontmatter id is authoritative and is looked up by id, not just
    path, so a renamed file reattaches to its existing row instead of
    colliding with it on the next insert."""
    fm_id = parsed.frontmatter.get("id") if parsed.error is None else None
    if isinstance(fm_id, str) and _ID_RE.fullmatch(fm_id):
        return fm_id, parsed, existing_by_id.get(fm_id, existing_by_path)

    if existing_by_path is not None:
        return existing_by_path.id, parsed, existing_by_path

    new_id = _new_id()
    if parsed.error is None:
        mtime_ns, _ = file_signature(path)
        if abs(time.time_ns() - mtime_ns) >= _RECENT_WRITE_NS and stamp_id(path, new_id):
            return new_id, read_note(path), None
    return new_id, parsed, None


def _index_note_file(
    db: Session,
    path: Path,
    rel_path: str,
    kind: str,
    existing_by_path: Node | None,
    existing_by_id: dict[str, Node],
) -> tuple[str, ParsedNote, bool]:
    parsed = read_note(path)
    node_id, parsed, existing = _resolve_id_and_existing(
        path, parsed, existing_by_path, existing_by_id
    )
    mtime_ns, size = file_signature(path)

    title = _title_from_frontmatter(parsed) or path.stem
    tags = _coerce_tags(parsed.frontmatter.get("tags")) if parsed.error is None else []
    created_raw = parsed.frontmatter.get("created") if parsed.error is None else None

    is_new = existing is None
    node = existing or Node(id=node_id)
    node.id = node_id
    node.path = rel_path
    node.title = title
    node.title_norm = normalize_title(title)
    node.kind = kind
    node.tags = tags
    node.body = parsed.body
    node.content_hash = parsed.content_hash
    node.mtime_ns = mtime_ns
    node.size = size
    node.fm_error = parsed.error
    node.created_at = _coerce_datetime(created_raw, mtime_ns)
    node.updated_at = datetime.fromtimestamp(mtime_ns / 1e9, tz=UTC)
    db.add(node)

    db.execute(delete(NodeLink).where(NodeLink.source_id == node_id))
    if parsed.error is None:
        for link in extract_links(parsed.body):
            db.add(
                NodeLink(
                    source_id=node_id,
                    target_raw=link.raw,
                    target_norm=link.norm,
                    alias=link.alias,
                )
            )

    return node_id, parsed, is_new


def _sync_check_row(
    db: Session, node_id: str, rel_path: str, parsed: ParsedNote, errors: list[str]
) -> None:
    if parsed.error is not None:
        return

    fm = parsed.frontmatter
    target_id = fm.get("node_id")
    if not isinstance(target_id, str) or db.get(Node, target_id) is None:
        errors.append(f"{rel_path}: check note references unknown node_id {target_id!r}")
        return

    verdict = fm.get("verdict")
    if verdict not in VALID_VERDICTS:
        verdict = "unclear"

    sources: list[dict[str, Any]] = []
    raw_sources = fm.get("sources")
    if isinstance(raw_sources, list):
        for entry in raw_sources:
            if isinstance(entry, dict) and isinstance(entry.get("url"), str):
                sources.append({"title": entry.get("title"), "url": entry["url"]})

    model = fm.get("model")

    check = db.get(Check, node_id) or Check(id=node_id)
    check.node_id = target_id
    check.path = rel_path
    check.verdict = verdict
    check.reasoning = str(fm.get("reasoning") or parsed.body.strip())
    check.sources = sources
    check.model = model if isinstance(model, str) else None
    check.created_at = _coerce_datetime(fm.get("checked"), time.time_ns())
    db.add(check)


def sync_vault(db: Session, vault_root: Path) -> SyncStats:
    stats = SyncStats()

    existing_by_path: dict[str, Node] = {n.path: n for n in db.scalars(select(Node))}
    existing_by_id: dict[str, Node] = {n.id: n for n in existing_by_path.values()}
    seen_paths: set[str] = set()
    dirty_checks: list[tuple[str, str, ParsedNote]] = []

    for path in iter_note_files(vault_root):
        rel_parts = path.relative_to(vault_root).parts
        rel_path = "/".join(rel_parts)
        seen_paths.add(rel_path)

        try:
            mtime_ns, size = file_signature(path)
        except OSError as exc:
            stats.errors.append(f"{rel_path}: {exc}")
            continue

        existing = existing_by_path.get(rel_path)
        if not _is_dirty(existing, mtime_ns, size):
            continue

        kind = "check" if rel_parts[0] == "checks" else "note"
        try:
            node_id, parsed, is_new = _index_note_file(
                db, path, rel_path, kind, existing, existing_by_id
            )
        except OSError as exc:
            stats.errors.append(f"{rel_path}: {exc}")
            continue

        if is_new:
            stats.added += 1
        else:
            stats.updated += 1

        if kind == "check":
            dirty_checks.append((node_id, rel_path, parsed))

    # A node row's `.path` may have been updated in place above (a file
    # reattached to its existing row via a stable frontmatter id, e.g. after
    # a rename) - check the row's current path, not the pre-scan snapshot
    # key, or a rename would both keep and delete the same row.
    for node_row in list(existing_by_path.values()):
        if node_row.path not in seen_paths:
            db.delete(node_row)
            stats.removed += 1

    db.flush()

    for node_id, rel_path, parsed in dirty_checks:
        _sync_check_row(db, node_id, rel_path, parsed, stats.errors)

    db.commit()
    return stats
