import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { VerdictBadge } from "../VerdictBadge";

describe("VerdictBadge", () => {
  it("renders the label for each verdict", () => {
    render(<VerdictBadge verdict="diverging" />);
    expect(screen.getByText("Diverging")).toBeInTheDocument();
  });
});
