from pathlib import Path

import pytest

from app.services.vault_io import (
    VaultPathError,
    allocate_path,
    atomic_write,
    file_signature,
    iter_note_files,
    parse_note,
    safe_join,
    serialize_note,
    slugify,
    stamp_id,
)


def test_slugify_plain_ascii() -> None:
    assert slugify("Hello World") == "hello-world"


def test_slugify_unicode_accents() -> None:
    assert slugify("Café Résumé") == "cafe-resume"


def test_slugify_only_punctuation() -> None:
    assert slugify("!!! ??? ...") == "note"


def test_slugify_truncates_long_title() -> None:
    title = "a" * 200
    result = slugify(title)
    assert len(result) == 80
    assert result == "a" * 80


@pytest.mark.parametrize(
    "reserved",
    ["con", "prn", "aux", "nul", "com1", "com9", "lpt1", "lpt9", "CON", "Com3"],
)
def test_slugify_windows_reserved_names(reserved: str) -> None:
    assert slugify(reserved) == f"{reserved.lower()}-note"


def test_safe_join_normal_parts_stay_inside(tmp_path: Path) -> None:
    result = safe_join(tmp_path, "sub", "note.md")
    assert result == (tmp_path / "sub" / "note.md").resolve()


def test_safe_join_rejects_parent_traversal(tmp_path: Path) -> None:
    with pytest.raises(VaultPathError):
        safe_join(tmp_path, "../../etc/passwd")


def test_safe_join_rejects_absolute_path_part(tmp_path: Path) -> None:
    with pytest.raises(VaultPathError):
        safe_join(tmp_path, "/etc/passwd")


def test_safe_join_rejects_embedded_traversal(tmp_path: Path) -> None:
    with pytest.raises(VaultPathError):
        safe_join(tmp_path, "a/../../x.md")


def test_parse_note_no_frontmatter() -> None:
    text = "# Just a note\n\nSome body text.\n"
    parsed = parse_note(text)
    assert parsed.body == text
    assert parsed.frontmatter == {}
    assert parsed.error is None


def test_parse_note_valid_frontmatter() -> None:
    text = "---\ntitle: Hello\ntags:\n  - a\n  - b\n---\n\nBody text here.\n"
    parsed = parse_note(text)
    assert parsed.frontmatter == {"title": "Hello", "tags": ["a", "b"]}
    assert parsed.body == "Body text here.\n"
    assert parsed.error is None


def test_parse_note_malformed_yaml_preserves_everything() -> None:
    text = "---\nfoo: {bar\n---\n\nBody text.\n"
    parsed = parse_note(text)
    assert parsed.frontmatter == {}
    assert parsed.error is not None
    assert parsed.body == text
    assert parsed.raw == text


def test_parse_note_malformed_yaml_tab_indentation() -> None:
    text = "---\nfoo:\n\tbar: baz\n---\n\nBody text.\n"
    parsed = parse_note(text)
    assert parsed.frontmatter == {}
    assert parsed.error is not None
    assert parsed.body == text
    assert parsed.raw == text


def test_parse_note_frontmatter_not_a_mapping() -> None:
    text = "---\n- a\n- b\n---\n\nBody text.\n"
    parsed = parse_note(text)
    assert parsed.frontmatter == {}
    assert parsed.error is not None
    assert "mapping" in parsed.error
    assert parsed.body == text
    assert parsed.raw == text


def test_content_hash_always_set() -> None:
    import hashlib

    text = "no frontmatter here"
    parsed = parse_note(text)
    assert parsed.content_hash == hashlib.sha256(text.encode("utf-8")).hexdigest()


@pytest.mark.parametrize("value", ["NO", "123", "true", "2026-08-09", "yes", "null"])
def test_serialize_note_round_trip_preserves_ambiguous_strings(value: str) -> None:
    fm = {"ticker": value, "tags": ["a", "b"]}
    serialized = serialize_note(fm, "Body content.")
    parsed = parse_note(serialized)
    assert parsed.error is None
    assert parsed.frontmatter["ticker"] == value
    assert isinstance(parsed.frontmatter["ticker"], str)


def test_serialize_note_normal_strings_not_quoted() -> None:
    fm = {"title": "A Normal Title"}
    serialized = serialize_note(fm, "Body.")
    assert '"A Normal Title"' not in serialized


def test_atomic_write_creates_exact_content_no_tmp_left(tmp_path: Path) -> None:
    target = tmp_path / "note.md"
    atomic_write(target, "hello world\n")
    assert target.read_text(encoding="utf-8") == "hello world\n"
    remaining = list(tmp_path.iterdir())
    assert remaining == [target]
    assert not any(p.suffix == ".tmp" for p in remaining)


def test_atomic_write_backs_up_existing_file(tmp_path: Path) -> None:
    target = tmp_path / "note.md"
    target.write_text("original content\n", encoding="utf-8")
    backup_dir = tmp_path / ".vault-backups"

    atomic_write(target, "new content\n", backup_dir=backup_dir)

    assert target.read_text(encoding="utf-8") == "new content\n"
    backups = list(backup_dir.iterdir())
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "original content\n"


def test_allocate_path_increments_on_collision(tmp_path: Path) -> None:
    first = allocate_path(tmp_path, "my-note")
    assert first == tmp_path / "my-note.md"
    assert first.exists()

    second = allocate_path(tmp_path, "my-note")
    assert second == tmp_path / "my-note-2.md"

    third = allocate_path(tmp_path, "my-note")
    assert third == tmp_path / "my-note-3.md"


def test_iter_note_files_top_level(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("a", encoding="utf-8")
    files = list(iter_note_files(tmp_path))
    assert tmp_path / "a.md" in files


def test_iter_note_files_skips_dot_directories(tmp_path: Path) -> None:
    backup_dir = tmp_path / ".vault-backups"
    backup_dir.mkdir()
    (backup_dir / "x.md").write_text("x", encoding="utf-8")

    files = list(iter_note_files(tmp_path))
    assert backup_dir / "x.md" not in files


def test_iter_note_files_recurses_into_normal_dirs(tmp_path: Path) -> None:
    checks_dir = tmp_path / "checks"
    checks_dir.mkdir()
    (checks_dir / "c.md").write_text("c", encoding="utf-8")

    files = list(iter_note_files(tmp_path))
    assert checks_dir / "c.md" in files


def test_iter_note_files_ignores_non_md(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("text", encoding="utf-8")
    files = list(iter_note_files(tmp_path))
    assert tmp_path / "notes.txt" not in files


def test_file_signature(tmp_path: Path) -> None:
    target = tmp_path / "note.md"
    target.write_text("hello", encoding="utf-8")
    sig = file_signature(target)
    st = target.stat()
    assert sig == (st.st_mtime_ns, st.st_size)


def test_stamp_id_inserts_first_line_preserves_rest(tmp_path: Path) -> None:
    target = tmp_path / "note.md"
    original = (
        "---\n"
        "title: My Note\n"
        "# a comment\n"
        "tags:\n"
        "  - a\n"
        "  - b\n"
        "description: |\n"
        "  multi-line\n"
        "  value here\n"
        "---\n\n"
        "Body content.\n"
    )
    target.write_text(original, encoding="utf-8")

    result = stamp_id(target, "abc123")

    assert result is True
    new_text = target.read_text(encoding="utf-8")
    lines = new_text.splitlines(keepends=True)
    assert lines[0] == "---\n"
    assert lines[1] == "id: abc123\n"
    assert "".join(lines[2:]) == "".join(original.splitlines(keepends=True)[1:])


def test_stamp_id_no_frontmatter_prepends(tmp_path: Path) -> None:
    target = tmp_path / "note.md"
    target.write_text("Just body text.\n", encoding="utf-8")

    result = stamp_id(target, "xyz789")

    assert result is True
    new_text = target.read_text(encoding="utf-8")
    assert new_text == "---\nid: xyz789\n---\n\nJust body text.\n"


def test_stamp_id_already_has_id_untouched(tmp_path: Path) -> None:
    target = tmp_path / "note.md"
    original = "---\nid: existing-id\ntitle: My Note\n---\n\nBody.\n"
    target.write_text(original, encoding="utf-8")

    result = stamp_id(target, "new-id")

    assert result is False
    assert target.read_text(encoding="utf-8") == original


def test_stamp_id_malformed_frontmatter_untouched(tmp_path: Path) -> None:
    target = tmp_path / "note.md"
    original = "---\nfoo: {bar\n---\n\nBody.\n"
    target.write_text(original, encoding="utf-8")

    result = stamp_id(target, "new-id")

    assert result is False
    assert target.read_text(encoding="utf-8") == original
