import re
from dataclasses import dataclass

_FENCED_CODE_RE = re.compile(r"^```[^\n]*\n.*?^```[ \t]*$", re.DOTALL | re.MULTILINE)
_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")

_WIKILINK_RE = re.compile(
    r"\[\[(?P<target>[^\[\]|#\n]+?)(?:#(?P<anchor>[^\[\]|\n]+?))?(?:\|(?P<alias>[^\[\]\n]+?))?\]\]"
)

_WHITESPACE_RUN_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class Link:
    raw: str
    anchor: str | None
    alias: str | None
    norm: str


def _blank(match: re.Match[str]) -> str:
    return "".join(c if c == "\n" else " " for c in match.group(0))


def strip_code(text: str) -> str:
    without_fences = _FENCED_CODE_RE.sub(_blank, text)
    return _INLINE_CODE_RE.sub(_blank, without_fences)


def extract_links(body: str) -> list[Link]:
    stripped = strip_code(body)
    links = []
    for match in _WIKILINK_RE.finditer(stripped):
        raw = match.group("target").strip()
        if not raw:
            continue
        anchor_group = match.group("anchor")
        alias_group = match.group("alias")
        anchor = anchor_group.strip() if anchor_group else None
        alias = alias_group.strip() if alias_group else None
        links.append(Link(raw=raw, anchor=anchor, alias=alias, norm=normalize_title(raw)))
    return links


def normalize_title(s: str) -> str:
    stripped = s.strip()
    if stripped.lower().endswith(".md"):
        stripped = stripped[:-3]
    collapsed = _WHITESPACE_RUN_RE.sub(" ", stripped)
    return collapsed.casefold()
