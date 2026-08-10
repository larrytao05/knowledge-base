import hashlib
import os
import re
import shutil
import tempfile
import time
import unicodedata
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

MAX_SLUG_LEN = 80

_WINDOWS_RESERVED = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{n}" for n in range(1, 10)),
    *(f"lpt{n}" for n in range(1, 10)),
}

_SLUG_RUN_RE = re.compile(r"[^a-z0-9]+")

_FRONTMATTER_RE = re.compile(
    r"\A﻿?---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.S
)

_YAML_BOOL_WORDS = (
    "y|Y|yes|Yes|YES|n|N|no|No|NO|true|True|TRUE|false|False|FALSE|on|On|ON|off|Off|OFF"
)
_YAML_INT_RE = r"[+-]?[0-9]+"
_YAML_FLOAT_RE = r"[+-]?[0-9]*\.[0-9]+"
_YAML_NULL_RE = r"null|Null|NULL|~"
_YAML_DATE_RE = r"[0-9]{4}-[0-9]{2}-[0-9]{2}"

_YAML_AMBIGUOUS_RE = re.compile(
    rf"({_YAML_BOOL_WORDS}|{_YAML_INT_RE}|{_YAML_FLOAT_RE}|{_YAML_NULL_RE}|{_YAML_DATE_RE})"
)

_NOTE_EXCLUDED_DIRS = {".vault-backups", ".trash"}


@dataclass(frozen=True)
class ParsedNote:
    frontmatter: dict[str, Any]
    body: str
    raw: str
    content_hash: str
    error: str | None


class VaultPathError(Exception):
    pass


def slugify(title: str) -> str:
    normalized = unicodedata.normalize("NFKD", title)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii").lower()
    collapsed = _SLUG_RUN_RE.sub("-", ascii_only).strip("-")
    truncated = collapsed[:MAX_SLUG_LEN].strip("-")
    if not truncated:
        return "note"
    if truncated.lower() in _WINDOWS_RESERVED:
        return f"{truncated}-note"
    return truncated


def safe_join(vault_root: Path, *parts: str) -> Path:
    resolved_root = vault_root.resolve()
    candidate = (vault_root / Path(*parts)).resolve()
    if not candidate.is_relative_to(resolved_root):
        raise VaultPathError(f"path escapes vault root: {parts!r}")
    return candidate


class _QuotingDumper(yaml.SafeDumper):
    pass


def _represent_str(dumper: yaml.SafeDumper, value: str) -> yaml.ScalarNode:
    if _YAML_AMBIGUOUS_RE.fullmatch(value):
        return dumper.represent_scalar("tag:yaml.org,2002:str", value, style='"')
    return dumper.represent_scalar("tag:yaml.org,2002:str", value)


_QuotingDumper.add_representer(str, _represent_str)


def parse_note(text: str) -> ParsedNote:
    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return ParsedNote(
            frontmatter={}, body=text, raw=text, content_hash=content_hash, error=None
        )

    try:
        loaded = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        return ParsedNote(
            frontmatter={}, body=text, raw=text, content_hash=content_hash, error=str(exc)
        )

    if not isinstance(loaded, dict):
        error = f"frontmatter must be a mapping, got {type(loaded).__name__}"
        return ParsedNote(
            frontmatter={}, body=text, raw=text, content_hash=content_hash, error=error
        )

    body = text[match.end() :]
    if body.startswith("\n"):
        body = body[1:]
    return ParsedNote(
        frontmatter=loaded, body=body, raw=text, content_hash=content_hash, error=None
    )


def serialize_note(fm: Mapping[str, Any], body: str) -> str:
    # yaml.safe_dump hardcodes Dumper=SafeDumper internally and raises on an
    # explicit Dumper= override, so use yaml.dump with a SafeDumper subclass
    # instead - equally safe since _QuotingDumper never dumps arbitrary objects.
    yaml_text = yaml.dump(
        dict(fm),
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        Dumper=_QuotingDumper,
    )
    return f"---\n{yaml_text}---\n\n{body.rstrip(chr(10))}\n"


def read_note(path: Path) -> ParsedNote:
    text = path.read_text(encoding="utf-8")
    return parse_note(text)


def atomic_write(path: Path, text: str, *, backup_dir: Path | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if backup_dir is not None and path.exists():
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / f"{path.stem}.{int(time.time())}{path.suffix}"
        shutil.copy2(path, backup_path)

    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise


def allocate_path(vault_root: Path, slug: str, subdir: str = "") -> Path:
    for suffix in ("",) + tuple(f"-{n}" for n in range(2, 100)):
        candidate = safe_join(vault_root, subdir, f"{slug}{suffix}.md")
        try:
            fd = os.open(candidate, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            os.close(fd)
            return candidate
        except FileExistsError:
            continue
    raise VaultPathError(f"too many filename collisions for slug {slug!r}")


def iter_note_files(vault_root: Path) -> Iterator[Path]:
    for path in vault_root.rglob("*.md"):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(vault_root).parts
        if any(part.startswith(".") for part in rel_parts):
            continue
        if any(part in _NOTE_EXCLUDED_DIRS for part in rel_parts):
            continue
        yield path


def file_signature(path: Path) -> tuple[int, int]:
    st = path.stat()
    return (st.st_mtime_ns, st.st_size)


def stamp_id(path: Path, note_id: str) -> bool:
    text = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)

    if not match:
        atomic_write(path, f"---\nid: {note_id}\n---\n\n{text}")
        return True

    try:
        loaded = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return False

    if not isinstance(loaded, dict):
        return False

    if "id" in loaded:
        return False

    insert_at = text.index("\n", match.start()) + 1
    new_text = f"{text[:insert_at]}id: {note_id}\n{text[insert_at:]}"
    atomic_write(path, new_text)
    return True
