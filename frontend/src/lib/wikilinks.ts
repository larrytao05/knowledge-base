export interface Link {
  raw: string;
  anchor: string | null;
  alias: string | null;
  norm: string;
}

// Named capture groups and the regex "s" (dotAll) flag require an ES2018+ compile
// target; this project's tsconfig targets ES2017, so positional groups and
// [\s\S] (dotAll's lazy-any-char equivalent) are used instead.
const FENCED_CODE_RE = /^```[^\n]*\n[\s\S]*?^```[ \t]*$/gm;
const INLINE_CODE_RE = /`[^`\n]*`/g;
const WIKILINK_RE = /\[\[([^[\]|#\n]+?)(?:#([^[\]|\n]+?))?(?:\|([^[\]\n]+?))?\]\]/g;
const WHITESPACE_RUN_RE = /\s+/g;

function blank(match: string): string {
  return [...match].map((c) => (c === "\n" ? "\n" : " ")).join("");
}

export function stripCode(text: string): string {
  const withoutFences = text.replace(FENCED_CODE_RE, blank);
  return withoutFences.replace(INLINE_CODE_RE, blank);
}

export function extractLinks(body: string): Link[] {
  const stripped = stripCode(body);
  const links: Link[] = [];
  for (const match of stripped.matchAll(WIKILINK_RE)) {
    const raw = (match[1] ?? "").trim();
    if (!raw) continue;
    const anchorGroup = match[2];
    const aliasGroup = match[3];
    links.push({
      raw,
      anchor: anchorGroup ? anchorGroup.trim() : null,
      alias: aliasGroup ? aliasGroup.trim() : null,
      norm: normalizeTitle(raw),
    });
  }
  return links;
}

export function normalizeTitle(s: string): string {
  let stripped = s.trim();
  if (stripped.toLowerCase().endsWith(".md")) {
    stripped = stripped.slice(0, -3);
  }
  const collapsed = stripped.replace(WHITESPACE_RUN_RE, " ");
  // JS has no direct equivalent of Python's str.casefold(); toLowerCase() is the closest
  // built-in and diverges for a few codepoints (e.g. German "ß" casefolds to "ss" in Python
  // but stays "ß" under toLowerCase()) - not addressed here since exact Unicode casefold
  // parity isn't needed for this personal app.
  return collapsed.toLowerCase();
}
