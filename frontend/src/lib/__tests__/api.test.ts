import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, getNode, openOrCreateNode } from "../api";

function jsonResponse(body: unknown): Response {
  return {
    ok: true,
    json: async () => body,
  } as Response;
}

function errorResponse(status: number, body: unknown): Response {
  return {
    ok: false,
    status,
    statusText: "Unprocessable Content",
    text: async () => JSON.stringify(body),
  } as Response;
}

describe("request error messages", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  async function messageFor(status: number, body: unknown): Promise<string> {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(errorResponse(status, body)));
    return getNode("aaaaaaaaaaaa").then(
      () => "did not throw",
      (err) => (err as ApiError).message,
    );
  }

  it("surfaces a string detail", async () => {
    expect(await messageFor(409, { detail: "another note is already titled 'X'" })).toBe(
      "another note is already titled 'X'",
    );
  });

  it("surfaces validation reasons without pydantic's prefix", async () => {
    const body = { detail: [{ msg: "Value error, a title must not be blank", loc: ["title"] }] };
    expect(await messageFor(422, body)).toBe("a title must not be blank");
  });

  it("falls back to the status line for an object detail", async () => {
    const body = { detail: { message: "content changed on disk", current: null } };
    expect(await messageFor(409, body)).toBe("409 Unprocessable Content");
  });
});

describe("openOrCreateNode", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("reuses a note whose title matches the link target", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse([{ id: "aaa", title: "Target Note" }]));
    vi.stubGlobal("fetch", fetchMock);

    expect(await openOrCreateNode("  target   note.md ")).toBe("aaa");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("creates the note when nothing matches", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([{ id: "aaa", title: "Something Else" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "bbb" }));
    vi.stubGlobal("fetch", fetchMock);

    expect(await openOrCreateNode("New Note")).toBe("bbb");
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({ title: "New Note" });
  });
});
