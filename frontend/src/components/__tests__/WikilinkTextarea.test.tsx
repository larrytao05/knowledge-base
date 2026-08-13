import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { listNodes } from "@/lib/api";
import type { NodeSummary } from "@/types";
import { WikilinkTextarea } from "../WikilinkTextarea";

vi.mock("@/lib/api", () => ({ listNodes: vi.fn() }));

function summary(id: string, title: string): NodeSummary {
  return {
    id,
    title,
    tags: [],
    excerpt: "",
    updated_at: "2024-01-01T00:00:00Z",
    latest_verdict: null,
  };
}

function Harness() {
  const [value, setValue] = useState("");
  return <WikilinkTextarea id="body" value={value} onChange={setValue} rows={4} className="" />;
}

function type(text: string): HTMLTextAreaElement {
  const textarea = screen.getByRole("textbox") as HTMLTextAreaElement;
  fireEvent.change(textarea, { target: { value: text, selectionStart: text.length } });
  return textarea;
}

describe("WikilinkTextarea", () => {
  afterEach(cleanup);

  beforeEach(() => {
    vi.mocked(listNodes).mockResolvedValue([
      summary("aaaaaaaaaaaa", "Target Note"),
      summary("bbbbbbbbbbbb", "Tangent Note"),
    ]);
  });

  it("opens the dropdown once [[ is typed", async () => {
    render(<Harness />);
    type("See [[");

    expect(await screen.findByText("Target Note")).toBeInTheDocument();
    expect(screen.getByText("Tangent Note")).toBeInTheDocument();
  });

  it("filters options by what has been typed", async () => {
    render(<Harness />);
    type("See [[Targ");

    expect(await screen.findByText("Target Note")).toBeInTheDocument();
    expect(screen.queryByText("Tangent Note")).not.toBeInTheDocument();
  });

  it("stays closed when the caret is not in a wikilink", async () => {
    render(<Harness />);
    type("See Targ");

    await waitFor(() => expect(screen.queryByText("Target Note")).not.toBeInTheDocument());
  });

  it("stays closed inside inline code", async () => {
    render(<Harness />);
    type("`[[Targ`");

    await waitFor(() => expect(screen.queryByText("Target Note")).not.toBeInTheDocument());
  });

  it("inserts the highlighted option on Enter", async () => {
    render(<Harness />);
    const textarea = type("See [[T");
    await screen.findByText("Target Note");

    fireEvent.keyDown(textarea, { key: "Enter" });

    expect(textarea.value).toBe("See [[Target Note]]");
  });

  it("moves the highlight with the arrow keys", async () => {
    render(<Harness />);
    const textarea = type("See [[T");
    await screen.findByText("Target Note");

    fireEvent.keyDown(textarea, { key: "ArrowDown" });
    fireEvent.keyDown(textarea, { key: "Enter" });

    expect(textarea.value).toBe("See [[Tangent Note]]");
  });

  it("closes the existing brackets instead of doubling them", async () => {
    render(<Harness />);
    const textarea = screen.getByRole("textbox") as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: "See [[T]]", selectionStart: 7 } });
    await screen.findByText("Target Note");

    fireEvent.keyDown(textarea, { key: "Enter" });

    expect(textarea.value).toBe("See [[Target Note]]");
  });

  it("does not offer titles a wikilink cannot address", async () => {
    vi.mocked(listNodes).mockResolvedValue([
      summary("cccccccccccc", "C# notes"),
      summary("aaaaaaaaaaaa", "Target Note"),
    ]);
    render(<Harness />);
    type("See [[");

    expect(await screen.findByText("Target Note")).toBeInTheDocument();
    expect(screen.queryByText("C# notes")).not.toBeInTheDocument();
  });

  it("moves the caret even when the completion changes nothing", async () => {
    render(<Harness />);
    const textarea = screen.getByRole("textbox") as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: "See [[Target Note]]", selectionStart: 17 } });
    await screen.findByText("Target Note");

    fireEvent.keyDown(textarea, { key: "Enter" });

    expect(textarea.value).toBe("See [[Target Note]]");
    expect(textarea.selectionStart).toBe(19);
  });

  it("dismisses the dropdown on Escape", async () => {
    render(<Harness />);
    const textarea = type("See [[T");
    await screen.findByText("Target Note");

    fireEvent.keyDown(textarea, { key: "Escape" });

    expect(screen.queryByText("Target Note")).not.toBeInTheDocument();
  });
});
