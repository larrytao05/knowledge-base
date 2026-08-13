import { describe, expect, it } from "vitest";
import {
  activeWikilinkQuery,
  extractLinks,
  insertWikilink,
  isLinkableTitle,
  normalizeTitle,
  stripCode,
} from "../wikilinks";

describe("extractLinks", () => {
  it("extracts a plain wikilink", () => {
    const links = extractLinks("See [[Target]] for details.");
    expect(links).toEqual([{ raw: "Target", anchor: null, alias: null, norm: "target" }]);
  });

  it("extracts a wikilink with an alias", () => {
    const links = extractLinks("See [[Target|Alias]].");
    expect(links).toEqual([{ raw: "Target", anchor: null, alias: "Alias", norm: "target" }]);
  });

  it("extracts a wikilink with an anchor", () => {
    const links = extractLinks("See [[Target#anchor]].");
    expect(links).toEqual([{ raw: "Target", anchor: "anchor", alias: null, norm: "target" }]);
  });

  it("extracts a wikilink with an anchor and an alias", () => {
    const links = extractLinks("See [[Target#anchor|Alias]].");
    expect(links).toEqual([
      { raw: "Target", anchor: "anchor", alias: "Alias", norm: "target" },
    ]);
  });

  it("ignores links inside fenced code blocks", () => {
    const body = "before\n```\n[[Ignored]]\n```\nafter [[Real]]";
    const links = extractLinks(body);
    expect(links).toEqual([{ raw: "Real", anchor: null, alias: null, norm: "real" }]);
  });

  it("ignores links inside inline code", () => {
    const body = "use `[[Ignored]]` but not [[Real]]";
    const links = extractLinks(body);
    expect(links).toEqual([{ raw: "Real", anchor: null, alias: null, norm: "real" }]);
  });

  it("extracts multiple links in one body", () => {
    const links = extractLinks("[[One]] and [[Two|Second]] and [[Three#anchor]]");
    expect(links.map((l) => l.raw)).toEqual(["One", "Two", "Three"]);
    expect(links.map((l) => l.norm)).toEqual(["one", "two", "three"]);
  });

  it("preserves line offsets when stripping code (blank keeps newlines)", () => {
    const body = "a\n```\nfence\n```\nb";
    const stripped = stripCode(body);
    expect(stripped.split("\n").length).toBe(body.split("\n").length);
  });
});

describe("stripCode offsets", () => {
  it("keeps offsets stable when a code span holds a non-BMP character", () => {
    // Emoji are two UTF-16 code units; blanking per code point would shorten the
    // text and shift every offset after the code span.
    const body = "see `x😀y` then [[Target]] end";
    const stripped = stripCode(body);

    expect(stripped.length).toBe(body.length);
    const start = stripped.indexOf("[[Target]]");
    expect(body.slice(start, start + "[[Target]]".length)).toBe("[[Target]]");
  });

  it("keeps offsets stable when a fenced block holds a non-BMP character", () => {
    const body = "a\n```\n😀 fenced\n```\n[[Target]]";
    expect(stripCode(body).length).toBe(body.length);
  });
});

describe("activeWikilinkQuery", () => {
  it("triggers on an empty query right after the brackets", () => {
    expect(activeWikilinkQuery("see [[", 6)).toEqual({ start: 4, query: "" });
  });

  it("captures what has been typed so far", () => {
    expect(activeWikilinkQuery("see [[Tar", 9)).toEqual({ start: 4, query: "Tar" });
  });

  it("allows spaces in the query", () => {
    expect(activeWikilinkQuery("[[two words", 11)).toEqual({ start: 0, query: "two words" });
  });

  it("does not trigger without an opener", () => {
    expect(activeWikilinkQuery("plain text", 10)).toBeNull();
  });

  it("does not trigger once the link is closed", () => {
    expect(activeWikilinkQuery("[[Target]] more", 15)).toBeNull();
  });

  it("does not trigger across a newline", () => {
    expect(activeWikilinkQuery("[[\nnext line", 12)).toBeNull();
  });

  it("does not trigger inside a fenced code block", () => {
    expect(activeWikilinkQuery("```\n[[Tar\n```\n", 9)).toBeNull();
  });

  it("does not trigger inside inline code", () => {
    expect(activeWikilinkQuery("`[[Tar`", 6)).toBeNull();
  });

  it("uses the opener nearest the caret", () => {
    expect(activeWikilinkQuery("[[One]] and [[Tw", 16)).toEqual({ start: 12, query: "Tw" });
  });

  it("still triggers after a code span holding a non-BMP character", () => {
    const text = "`x😀y` [[Tar";
    expect(activeWikilinkQuery(text, text.length)).toEqual({
      start: text.indexOf("[["),
      query: "Tar",
    });
  });
});

describe("isLinkableTitle", () => {
  it("accepts ordinary titles", () => {
    expect(isLinkableTitle("Nvidia AI capex")).toBe(true);
  });

  it("rejects titles holding wikilink syntax characters", () => {
    for (const unsafe of ["C# notes", "foo]] bar", "x[y", "a|b", "two\nlines", "crlf\r"]) {
      expect(isLinkableTitle(unsafe)).toBe(false);
    }
  });

  it("rejects blank titles", () => {
    expect(isLinkableTitle("   ")).toBe(false);
  });
});

describe("insertWikilink", () => {
  it("inserts a closed link in place of the query", () => {
    const result = insertWikilink("see [[Tar", { start: 4, query: "Tar" }, "Target Note");
    expect(result.text).toBe("see [[Target Note]]");
    expect(result.caret).toBe(result.text.length);
  });

  it("consumes brackets that are already closed", () => {
    const result = insertWikilink("see [[Tar]] end", { start: 4, query: "Tar" }, "Target Note");
    expect(result.text).toBe("see [[Target Note]] end");
    expect(result.caret).toBe("see [[Target Note]]".length);
  });

  it("keeps the text after the caret", () => {
    const result = insertWikilink("a [[b c", { start: 2, query: "b" }, "Beta");
    expect(result.text).toBe("a [[Beta]] c");
    expect(result.caret).toBe("a [[Beta]]".length);
  });

  // Arrowing the caret into an existing link opens the dropdown, so Enter has to
  // replace that whole link rather than strand the rest of its target in prose.
  it("replaces the whole link when the caret sits inside one", () => {
    const query = activeWikilinkQuery("See [[Target Note]] end", 8);
    expect(query).toEqual({ start: 4, query: "Ta" });
    const result = insertWikilink("See [[Target Note]] end", query!, "Chosen Note");
    expect(result.text).toBe("See [[Chosen Note]] end");
    expect(result.caret).toBe("See [[Chosen Note]]".length);
  });

  it("replaces the whole link when the caret sits inside an aliased one", () => {
    const query = activeWikilinkQuery("See [[Target|shown]] end", 8);
    const result = insertWikilink("See [[Target|shown]] end", query!, "Chosen");
    expect(result.text).toBe("See [[Chosen]] end");
  });
});

describe("normalizeTitle", () => {
  it("collapses whitespace runs", () => {
    expect(normalizeTitle("Foo   Bar\tBaz")).toBe("foo bar baz");
  });

  it("casefolds", () => {
    expect(normalizeTitle("FOO Bar")).toBe("foo bar");
  });

  it("strips a trailing .md extension", () => {
    expect(normalizeTitle("Notes.md")).toBe("notes");
  });

  it("strips a trailing .MD extension case-insensitively", () => {
    expect(normalizeTitle("Notes.MD")).toBe("notes");
  });

  it("handles unicode and mixed-case titles", () => {
    // JS toLowerCase() matches Python casefold() for this input; the known
    // divergence (e.g. German "ß") is documented in wikilinks.ts.
    expect(normalizeTitle("Café ÜBER")).toBe("café über");
  });
});
