import os
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.models import Node, NodeLink
from app.services.indexer import sync_vault
from tests.conftest import TestSessionLocal


@pytest.fixture
def db() -> Iterator[Session]:
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


def _write(path: Path, text: str, *, ago_seconds: float = 5.0) -> None:
    path.write_text(text, encoding="utf-8")
    past_ns = time.time_ns() - int(ago_seconds * 1_000_000_000)
    os.utime(path, ns=(past_ns, past_ns))


def test_external_file_is_indexed(vault_root: Path, db: Session) -> None:
    _write(
        vault_root / "external.md",
        '---\ntitle: "Rates stay high"\ntags: [macro]\n---\n\nBody here.\n',
    )

    stats = sync_vault(db, vault_root)

    assert stats.added == 1
    node = db.query(Node).filter(Node.title == "Rates stay high").one()
    assert node.tags == ["macro"]
    assert node.kind == "note"
    assert node.fm_error is None


def test_external_modification_is_picked_up(vault_root: Path, db: Session) -> None:
    path = vault_root / "note.md"
    _write(path, "---\ntitle: Note\n---\n\noriginal body\n")
    sync_vault(db, vault_root)

    _write(path, "---\ntitle: Note\n---\n\nmodified body, edited outside the app\n", ago_seconds=0)
    stats = sync_vault(db, vault_root)

    assert stats.updated == 1
    node = db.query(Node).filter(Node.path == "note.md").one()
    assert "modified body" in node.body


def test_external_deletion_removes_node(vault_root: Path, db: Session) -> None:
    path = vault_root / "gone.md"
    _write(path, "---\ntitle: Gone\n---\n\nbody\n")
    sync_vault(db, vault_root)
    assert db.query(Node).filter(Node.path == "gone.md").count() == 1

    path.unlink()
    stats = sync_vault(db, vault_root)

    assert stats.removed == 1
    assert db.query(Node).filter(Node.path == "gone.md").count() == 0


def test_external_note_creates_backlink(vault_root: Path, db: Session) -> None:
    _write(vault_root / "source.md", "---\ntitle: Source\n---\n\nSee [[Target Note]].\n")

    sync_vault(db, vault_root)

    source = db.query(Node).filter(Node.title == "Source").one()
    links = db.query(NodeLink).filter(NodeLink.source_id == source.id).all()
    assert len(links) == 1
    assert links[0].target_raw == "Target Note"
    assert links[0].target_norm == "target note"


def test_unresolved_link_resolves_when_target_created(vault_root: Path, db: Session) -> None:
    _write(vault_root / "source.md", "---\ntitle: Source\n---\n\nSee [[Target Note]].\n")
    sync_vault(db, vault_root)

    assert db.query(Node).filter(Node.title_norm == "target note").count() == 0

    _write(vault_root / "target.md", "---\ntitle: Target Note\n---\n\nHere it is.\n")
    sync_vault(db, vault_root)

    target = db.query(Node).filter(Node.title_norm == "target note").one()
    source = db.query(Node).filter(Node.title == "Source").one()
    link = db.query(NodeLink).filter(NodeLink.source_id == source.id).one()
    assert link.target_norm == target.title_norm


def test_malformed_yaml_node_is_listed_with_full_body_preserved(
    vault_root: Path, db: Session
) -> None:
    raw = "---\ntitle: [unclosed\n---\n\nThis body must not be lost.\n"
    _write(vault_root / "broken.md", raw)

    stats = sync_vault(db, vault_root)

    assert stats.added == 1
    node = db.query(Node).filter(Node.path == "broken.md").one()
    assert node.fm_error is not None
    assert node.body == raw


def test_id_is_stamped_into_frontmatter_and_survives_rename(vault_root: Path, db: Session) -> None:
    original = vault_root / "original.md"
    _write(original, "---\ntitle: Stable\n---\n\nbody\n")

    sync_vault(db, vault_root)
    node = db.query(Node).filter(Node.path == "original.md").one()
    stamped_id = node.id
    assert "id:" in original.read_text()

    renamed = vault_root / "renamed.md"
    original.rename(renamed)
    past_ns = time.time_ns() - 5_000_000_000
    os.utime(renamed, ns=(past_ns, past_ns))

    stats = sync_vault(db, vault_root)

    # The renamed file's stable id matches the existing row, so it's reused
    # in place - not deleted-and-recreated.
    assert stats.removed == 0
    assert stats.added == 0
    assert stats.updated == 1
    renamed_node = db.query(Node).filter(Node.path == "renamed.md").one()
    assert renamed_node.id == stamped_id
    assert db.query(Node).filter(Node.path == "original.md").count() == 0
