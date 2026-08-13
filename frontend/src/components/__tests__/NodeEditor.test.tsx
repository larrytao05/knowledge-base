import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, updateNode } from "@/lib/api";
import type { NodeDetail } from "@/types";
import { NodeEditor } from "../NodeEditor";

vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh: vi.fn() }) }));
// ApiError stays real - the component branches on `instanceof`.
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  updateNode: vi.fn(),
  listNodes: vi.fn().mockResolvedValue([]),
}));

function detail(overrides: Partial<NodeDetail> = {}): NodeDetail {
  return {
    id: "aaaaaaaaaaaa",
    title: "Old Title",
    path: "old-title.md",
    tags: [],
    body: "This note is [[Old Title]].",
    content_hash: "a".repeat(64),
    fm_error: null,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
    links_out: [],
    backlinks: [],
    checks: [],
    link_rewrite_skipped: 0,
    links_left_at_old_title: 0,
    ...overrides,
  };
}

const mockUpdate = vi.mocked(updateNode);

describe("NodeEditor", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  // A rename retargets this note's own wikilinks server-side. If the form kept
  // the pre-rename body while adopting the new hash, the next save would push
  // the stale body back up under a hash the server accepts - reverting the
  // rewrite with the conflict guard none the wiser.
  it("saves the server's rewritten body on a subsequent save", async () => {
    const saved = detail({
      title: "New Title",
      body: "This note is [[New Title]].",
      content_hash: "b".repeat(64),
    });
    mockUpdate.mockResolvedValue(saved);

    render(<NodeEditor node={detail()} />);
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(mockUpdate).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(mockUpdate).toHaveBeenCalledTimes(2));

    expect(mockUpdate.mock.calls[1][1]).toMatchObject({
      content_hash: "b".repeat(64),
      title: "New Title",
      body: "This note is [[New Title]].",
    });
  });

  // Adopting the saved note is what stops a rename's self-link rewrite being
  // reverted, but it also overwrites the form - so nothing may be typed into it
  // while the save is in flight.
  it("locks the fields while a save is in flight", async () => {
    let settle: ((saved: NodeDetail) => void) | null = null;
    mockUpdate.mockReturnValue(
      new Promise<NodeDetail>((resolve) => {
        settle = resolve;
      }),
    );

    render(<NodeEditor node={detail()} />);
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(screen.getByLabelText("Title")).toBeDisabled());
    expect(screen.getByLabelText("Tags")).toBeDisabled();
    expect(screen.getByLabelText("Body")).toBeDisabled();

    settle!(detail({ content_hash: "b".repeat(64) }));
    await waitFor(() => expect(screen.getByLabelText("Title")).toBeEnabled());
  });

  it("shows the reason a rename was refused instead of the reload prompt", async () => {
    const reason = "another note is already titled 'New Title'";
    mockUpdate.mockRejectedValue(new ApiError(409, { detail: reason }, reason));

    render(<NodeEditor node={detail()} />);
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText(reason)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Reload/ })).not.toBeInTheDocument();
  });

  it("offers to reload when the note changed on disk", async () => {
    mockUpdate.mockRejectedValue(
      new ApiError(
        409,
        { detail: { message: "content changed on disk", current: detail() } },
        "409 Conflict",
      ),
    );

    render(<NodeEditor node={detail()} />);
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText("content changed on disk")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Reload/ })).toBeEnabled();
  });
});
