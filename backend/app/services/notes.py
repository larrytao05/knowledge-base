import secrets
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.deps import Vault
from app.models import Node
from app.schemas import NodeUpdate
from app.services.indexer import sync_vault
from app.services.locks import path_lock
from app.services.vault_io import (
    allocate_path,
    atomic_write,
    read_note,
    safe_join,
    serialize_note,
    slugify,
)


class StaleContentError(Exception):
    """Raised when a PATCH's content_hash no longer matches the file on disk."""


class MalformedNoteError(Exception):
    """Raised when trying to write to a node whose frontmatter failed to parse."""


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
    ticker: str | None,
    tags: list[str],
) -> Node:
    node_id = _new_id()
    path = allocate_path(vault.root, slugify(title))

    frontmatter: dict[str, object] = {"id": node_id, "title": title}
    if ticker:
        frontmatter["ticker"] = ticker
    if tags:
        frontmatter["tags"] = tags
    frontmatter["created"] = _iso_now()

    atomic_write(path, serialize_note(frontmatter, body))
    sync_vault(db, vault.root)

    node = db.get(Node, node_id)
    if node is None:
        raise RuntimeError(f"node {node_id} missing from index immediately after sync")
    return node


def update_node(db: Session, vault: Vault, node: Node, payload: NodeUpdate) -> Node:
    if node.fm_error is not None:
        raise MalformedNoteError(node.fm_error)

    path = safe_join(vault.root, *Path(node.path).parts)
    provided = payload.model_fields_set

    with path_lock(path):
        current = read_note(path)
        if current.content_hash != payload.content_hash:
            raise StaleContentError(node.id)

        frontmatter = dict(current.frontmatter)
        if "title" in provided and payload.title is not None:
            frontmatter["title"] = payload.title
        if "ticker" in provided:
            if payload.ticker:
                frontmatter["ticker"] = payload.ticker
            else:
                frontmatter.pop("ticker", None)
        if "tags" in provided:
            if payload.tags:
                frontmatter["tags"] = payload.tags
            else:
                frontmatter.pop("tags", None)

        body = payload.body if "body" in provided and payload.body is not None else current.body

        backup_dir = vault.root / ".vault-backups"
        atomic_write(path, serialize_note(frontmatter, body), backup_dir=backup_dir)

    sync_vault(db, vault.root)

    updated = db.get(Node, node.id)
    if updated is None:
        raise RuntimeError(f"node {node.id} missing from index immediately after sync")
    return updated
