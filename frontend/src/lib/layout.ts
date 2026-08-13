import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  type SimulationNodeDatum,
} from "d3-force";
import type { GraphData, Verdict } from "@/types";

export interface LayoutNode {
  id: string;
  title: string;
  verdict: Verdict | null;
  degree: number;
  x: number;
  y: number;
}

export interface LayoutEdge {
  source: string;
  target: string;
}

export interface GraphLayout {
  nodes: LayoutNode[];
  edges: LayoutEdge[];
  width: number;
  height: number;
}

interface SimNode extends SimulationNodeDatum {
  id: string;
  title: string;
  verdict: Verdict | null;
  degree: number;
}

const TICKS = 300;

function finite(value: number | undefined, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

export function computeGraphLayout(data: GraphData, width: number, height: number): GraphLayout {
  if (data.nodes.length === 0) {
    return { nodes: [], edges: [], width, height };
  }

  if (data.nodes.length === 1) {
    const only = data.nodes[0];
    return {
      nodes: [{ ...only, x: width / 2, y: height / 2 }],
      edges: [],
      width,
      height,
    };
  }

  const simNodes: SimNode[] = data.nodes.map((node) => ({ ...node }));
  const simEdges = data.edges.map((edge) => ({ source: edge.source, target: edge.target }));

  const simulation = forceSimulation(simNodes)
    .force(
      "link",
      forceLink<SimNode, { source: string; target: string }>(simEdges)
        .id((d) => d.id)
        .distance(80),
    )
    .force("charge", forceManyBody().strength(-150))
    .force("center", forceCenter(width / 2, height / 2))
    .force("collide", forceCollide<SimNode>().radius((d) => 8 + d.degree * 2))
    .stop();

  for (let i = 0; i < TICKS; i++) {
    simulation.tick();
  }

  const nodes: LayoutNode[] = simNodes.map((node) => ({
    id: node.id,
    title: node.title,
    verdict: node.verdict,
    degree: node.degree,
    x: finite(node.x, width / 2),
    y: finite(node.y, height / 2),
  }));

  return { nodes, edges: data.edges, width, height };
}
