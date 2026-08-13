import re
from dataclasses import dataclass

_FENCED_CODE_RE = re.compile(r"^```[^\n]*\n.*?^```[ \t]*$", re.DOTALL | re.MULTILINE)
_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")

_WIKILINK_RE = re.compile(
    r"\[\[(?P<target>[^\[\]|#\n]+?)(?:#(?P<anchor>[^\[\]|\n]+?))?(?:\|(?P<alias>[^\[\]\n]+?))?\]\]"
)

_WHITESPACE_RUN_RE = re.compile(r"\s+")

# Characters the wikilink grammar gives its own meaning, so a title containing
# one can never be addressed by a `[[link]]` (Obsidian bans the same set).
_UNLINKABLE_TITLE_RE = re.compile(r"[\[\]#|\r\n]")

UNLINKABLE_TITLE_REASON = "must not be blank or contain any of [ ] # | or a line break"


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


def _group_from(text: str, match: re.Match[str], name: str) -> str | None:
    """Read a group of a match made against the stripped text back out of the
    original: blanking preserves offsets, so the spans line up, but the stripped
    copy has any inline code inside the group blanked out."""
    start, end = match.span(name)
    if start < 0:
        return None
    return text[start:end]


def extract_links(body: str) -> list[Link]:
    stripped = strip_code(body)
    links = []
    for match in _WIKILINK_RE.finditer(stripped):
        raw = (_group_from(body, match, "target") or "").strip()
        if not raw:
            continue
        anchor_group = _group_from(body, match, "anchor")
        alias_group = _group_from(body, match, "alias")
        anchor = anchor_group.strip() if anchor_group else None
        alias = alias_group.strip() if alias_group else None
        links.append(Link(raw=raw, anchor=anchor, alias=alias, norm=normalize_title(raw)))
    return links


def is_linkable_title(title: str) -> bool:
    """Whether a `[[wikilink]]` can address this title at all."""
    return bool(title.strip()) and not _UNLINKABLE_TITLE_RE.search(title)


def rewrite_links(text: str, old_norm: str, new_target: str) -> str:
    """Retarget every `[[old]]` in `text` at `new_target`, keeping anchors and
    aliases. Matching runs against the code-stripped text (blanking preserves
    offsets) so links inside code blocks/spans are left alone."""
    if not is_linkable_title(new_target):
        return text

    stripped = strip_code(text)
    parts: list[str] = []
    last_end = 0

    for match in _WIKILINK_RE.finditer(stripped):
        # Compare the raw target, the same one `extract_links` indexes by - the
        # stripped copy blanks any code span inside it, so the two would disagree
        # about a title like "Using `git rebase`" and leave the link dangling.
        target = _group_from(text, match, "target") or ""
        if normalize_title(target) != old_norm:
            continue
        # Read the kept groups off the original text: the stripped copy has any
        # code span inside an anchor or alias blanked out.
        anchor = _group_from(text, match, "anchor")
        alias = _group_from(text, match, "alias")
        parts.append(text[last_end : match.start()])
        parts.append(f"[[{new_target}")
        if anchor:
            parts.append(f"#{anchor}")
        if alias:
            parts.append(f"|{alias}")
        parts.append("]]")
        last_end = match.end()

    if not parts:
        return text
    parts.append(text[last_end:])
    return "".join(parts)


def normalize_title(s: str) -> str:
    stripped = s.strip()
    if stripped.lower().endswith(".md"):
        stripped = stripped[:-3]
    collapsed = _WHITESPACE_RUN_RE.sub(" ", stripped)
    return collapsed.casefold()
