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
export const WIKILINK_RE = /\[\[([^[\]|#\n]+?)(?:#([^[\]|\n]+?))?(?:\|([^[\]\n]+?))?\]\]/g;
const WHITESPACE_RUN_RE = /\s+/g;
const NON_NEWLINE_RE = /[^\n]/g;
// The remainder of a link the caret sits inside, up to and including its closer.
const LINK_TAIL_RE = /^[^[\]\n]*\]\]/;
// Characters the wikilink grammar gives its own meaning, so a title containing
// one can never be addressed by a `[[link]]` (Obsidian bans the same set).
const UNLINKABLE_TITLE_RE = /[[\]#|\r\n]/;

// Replaces per UTF-16 code unit, not per code point: string offsets are code
// units, so spreading the match would shorten it for non-BMP characters (emoji,
// rare CJK) and shift every offset after a code span that contains one.
function blank(match: string): string {
  return match.replace(NON_NEWLINE_RE, " ");
}

export function stripCode(text: string): string {
  const withoutFences = text.replace(FENCED_CODE_RE, blank);
  return withoutFences.replace(INLINE_CODE_RE, blank);
}

/** Read a group of a match made against the stripped text back out of the
 * original. The groups are located by splitting the stripped match on the "#"
 * and "|" its own character classes exclude, then slicing the raw text at those
 * offsets - blanking preserves them. Re-parsing the raw span instead would let
 * a "#", "|" or "]]" hidden inside inline code split it differently from the
 * blanked copy the backend and the indexer agree on. The "d" flag would give
 * the offsets directly but needs an ES2022 target; this file stays on ES2017. */
export function groupFrom(text: string, match: RegExpExecArray, group: number): string | null {
  const start = (match.index ?? 0) + 2;
  const inner = match[0].slice(2, -2);

  const hash = inner.indexOf("#");
  const pipe = inner.indexOf("|");
  const aliasAt = pipe < 0 ? inner.length : pipe;
  const anchorAt = hash < 0 || hash > aliasAt ? aliasAt : hash;

  const span = (from: number, to: number): string | null =>
    from < to ? text.slice(start + from, start + to) : null;

  if (group === 1) return span(0, anchorAt);
  if (group === 2) return anchorAt < aliasAt ? span(anchorAt + 1, aliasAt) : null;
  return pipe < 0 ? null : span(aliasAt + 1, inner.length);
}

export function extractLinks(body: string): Link[] {
  const stripped = stripCode(body);
  const links: Link[] = [];
  for (const match of stripped.matchAll(WIKILINK_RE)) {
    const raw = (groupFrom(body, match, 1) ?? "").trim();
    if (!raw) continue;
    const anchorGroup = groupFrom(body, match, 2);
    const aliasGroup = groupFrom(body, match, 3);
    links.push({
      raw,
      anchor: anchorGroup ? anchorGroup.trim() : null,
      alias: aliasGroup ? aliasGroup.trim() : null,
      norm: normalizeTitle(raw),
    });
  }
  return links;
}

export function isLinkableTitle(title: string): boolean {
  return title.trim().length > 0 && !UNLINKABLE_TITLE_RE.test(title);
}

export interface WikilinkQuery {
  start: number;
  query: string;
}

/** The `[[` autocomplete query the caret sits in, or null if it doesn't sit in one. */
export function activeWikilinkQuery(text: string, caret: number): WikilinkQuery | null {
  const before = text.slice(0, caret);
  const start = before.lastIndexOf("[[");
  if (start < 0) return null;

  const query = before.slice(start + 2);
  if (query.includes("[") || query.includes("]") || query.includes("\n")) return null;
  // Blanking preserves offsets, so an opener still present in the stripped text
  // is one that lives outside any code block/span.
  if (stripCode(text).slice(start, start + 2) !== "[[") return null;

  return { start, query };
}

export function insertWikilink(
  text: string,
  query: WikilinkQuery,
  title: string,
): { text: string; caret: number } {
  const rest = text.slice(query.start + 2 + query.query.length);
  // The caret can sit anywhere inside an existing link, so replace through that
  // link's closer - consuming only a closer sitting right at the caret would
  // leave the rest of the old target stranded in the prose.
  const tail = LINK_TAIL_RE.exec(rest);
  const remainder = tail ? rest.slice(tail[0].length) : rest;
  const link = `[[${title}]]`;
  return {
    text: text.slice(0, query.start) + link + remainder,
    caret: query.start + link.length,
  };
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
