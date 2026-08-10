import { describe, expect, it } from "vitest";
import { extractLinks, normalizeTitle, stripCode } from "../wikilinks";

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
