import { describe, expect, it } from "vitest";
import { computeGraphLayout } from "../layout";
import type { GraphData } from "@/types";

function expectFinite(n: number) {
  expect(Number.isFinite(n)).toBe(true);
  expect(Number.isNaN(n)).toBe(false);
}

describe("computeGraphLayout", () => {
  it("returns an empty layout for zero nodes without throwing", () => {
    const data: GraphData = { nodes: [], edges: [], unresolved: [] };
    const layout = computeGraphLayout(data, 800, 600);
    expect(layout).toEqual({ nodes: [], edges: [], width: 800, height: 600 });
  });

  it("places a single node at a finite position", () => {
    const data: GraphData = {
      nodes: [{ id: "a", title: "A", ticker: null, verdict: null, degree: 0 }],
      edges: [],
      unresolved: [],
    };
    const layout = computeGraphLayout(data, 800, 600);
    expect(layout.nodes).toHaveLength(1);
    expectFinite(layout.nodes[0].x);
    expectFinite(layout.nodes[0].y);
  });

  it("produces finite positions for every node in a small multi-node graph", () => {
    const data: GraphData = {
      nodes: [
        { id: "a", title: "A", ticker: null, verdict: "on_track", degree: 2 },
        { id: "b", title: "B", ticker: "BB", verdict: "diverging", degree: 1 },
        { id: "c", title: "C", ticker: null, verdict: "unclear", degree: 1 },
      ],
      edges: [
        { source: "a", target: "b" },
        { source: "a", target: "c" },
      ],
      unresolved: [],
    };
    const layout = computeGraphLayout(data, 800, 600);
    expect(layout.nodes).toHaveLength(3);
    for (const node of layout.nodes) {
      expectFinite(node.x);
      expectFinite(node.y);
    }
  });

  it("returns edges that reference ids present in the output nodes", () => {
    const data: GraphData = {
      nodes: [
        { id: "a", title: "A", ticker: null, verdict: null, degree: 1 },
        { id: "b", title: "B", ticker: null, verdict: null, degree: 1 },
      ],
      edges: [{ source: "a", target: "b" }],
      unresolved: [],
    };
    const layout = computeGraphLayout(data, 800, 600);
    const ids = new Set(layout.nodes.map((n) => n.id));
    for (const edge of layout.edges) {
      expect(ids.has(edge.source)).toBe(true);
      expect(ids.has(edge.target)).toBe(true);
    }
  });
});
