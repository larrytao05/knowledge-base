import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { LinkRef } from "@/types";
import { NodeBody } from "../NodeBody";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

function link(overrides: Partial<LinkRef>): LinkRef {
  return { target_raw: "", alias: null, node_id: null, title: null, ...overrides };
}

const resolvedTarget = link({
  target_raw: "Target",
  node_id: "aaaaaaaaaaaa",
  title: "Target",
});

describe("NodeBody", () => {
  afterEach(cleanup);

  it("renders an empty link target as plain text without shifting later links", () => {
    const { container } = render(
      <NodeBody body="a [[  ]] b [[Target]] c" linksOut={[resolvedTarget]} />,
    );

    expect(container.textContent).toBe("a [[  ]] b [[Target]] c");
    expect(screen.getByRole("link", { name: "[[Target]]" })).toHaveAttribute(
      "href",
      "/nodes/aaaaaaaaaaaa",
    );
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("keeps offsets aligned when a code span holds a non-BMP character", () => {
    const body = "see `x😀y` then [[Target]] end";
    const { container } = render(<NodeBody body={body} linksOut={[resolvedTarget]} />);

    expect(container.textContent).toBe(body);
    expect(screen.getByRole("link", { name: "[[Target]]" })).toBeInTheDocument();
  });

  it("offers to create an unresolved link", () => {
    render(<NodeBody body="see [[Missing]]" linksOut={[link({ target_raw: "Missing" })]} />);

    expect(screen.getByRole("button", { name: "[[Missing]]" })).toHaveAttribute(
      "title",
      'Create "Missing"',
    );
  });

  it("labels an aliased link with its alias", () => {
    render(<NodeBody body="see [[Target|the alias]]" linksOut={[resolvedTarget]} />);

    expect(screen.getByRole("link", { name: "the alias" })).toBeInTheDocument();
  });

  // Groups have to come off the raw body: the stripped copy blanks inline code,
  // which would drop the backticked text out of the label and out of the title a
  // click would create.
  it("keeps inline code inside an alias", () => {
    render(<NodeBody body="see [[Target|a `b` c]]" linksOut={[resolvedTarget]} />);

    expect(screen.getByRole("link", { name: "a `b` c" })).toBeInTheDocument();
  });

  it("keeps inline code inside an unresolved target", () => {
    render(<NodeBody body="see [[Mis`s`ing]]" linksOut={[link({ target_raw: "Mis`s`ing" })]} />);

    expect(screen.getByRole("button")).toHaveAttribute("title", 'Create "Mis`s`ing"');
  });
});
