"use client";

import { useMemo, useRef, useState, type MouseEvent, type WheelEvent } from "react";
import { useRouter } from "next/navigation";
import { computeGraphLayout } from "@/lib/layout";
import { VERDICT_FILL_CLASSES } from "@/lib/verdict";
import type { GraphData } from "@/types";

const WIDTH = 800;
const HEIGHT = 600;
const MIN_ZOOM = 0.2;
const MAX_ZOOM = 5;

interface ViewBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

export function GraphView({ data }: { data: GraphData }) {
  const router = useRouter();
  const layout = useMemo(() => computeGraphLayout(data, WIDTH, HEIGHT), [data]);
  const [viewBox, setViewBox] = useState<ViewBox>({ x: 0, y: 0, w: WIDTH, h: HEIGHT });
  const svgRef = useRef<SVGSVGElement>(null);
  const dragRef = useRef<{ x: number; y: number } | null>(null);

  const nodeById = useMemo(() => new Map(layout.nodes.map((n) => [n.id, n])), [layout.nodes]);

  function clamp(value: number, min: number, max: number) {
    return Math.min(Math.max(value, min), max);
  }

  function handleWheel(e: WheelEvent<SVGSVGElement>) {
    e.preventDefault();
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const cursorX = viewBox.x + ((e.clientX - rect.left) / rect.width) * viewBox.w;
    const cursorY = viewBox.y + ((e.clientY - rect.top) / rect.height) * viewBox.h;
    const factor = e.deltaY > 0 ? 1.1 : 0.9;
    const newW = clamp(viewBox.w * factor, WIDTH / MAX_ZOOM, WIDTH / MIN_ZOOM);
    const newH = clamp(viewBox.h * factor, HEIGHT / MAX_ZOOM, HEIGHT / MIN_ZOOM);
    setViewBox({
      x: cursorX - ((cursorX - viewBox.x) / viewBox.w) * newW,
      y: cursorY - ((cursorY - viewBox.y) / viewBox.h) * newH,
      w: newW,
      h: newH,
    });
  }

  function handleMouseDown(e: MouseEvent<SVGSVGElement>) {
    dragRef.current = { x: e.clientX, y: e.clientY };
  }

  function handleMouseMove(e: MouseEvent<SVGSVGElement>) {
    const start = dragRef.current;
    const svg = svgRef.current;
    if (!start || !svg) return;
    const rect = svg.getBoundingClientRect();
    const dx = ((e.clientX - start.x) / rect.width) * viewBox.w;
    const dy = ((e.clientY - start.y) / rect.height) * viewBox.h;
    dragRef.current = { x: e.clientX, y: e.clientY };
    setViewBox((prev) => ({ ...prev, x: prev.x - dx, y: prev.y - dy }));
  }

  function handleMouseUp() {
    dragRef.current = null;
  }

  if (data.nodes.length === 0) {
    return <p className="text-sm text-muted">No nodes yet.</p>;
  }

  return (
    <div className="flex h-full w-full flex-col gap-2">
      <svg
        ref={svgRef}
        viewBox={`${viewBox.x} ${viewBox.y} ${viewBox.w} ${viewBox.h}`}
        className="h-full w-full cursor-grab select-none rounded-lg border border-border-subtle bg-surface active:cursor-grabbing"
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <g stroke="currentColor" className="text-border-default" strokeOpacity={0.4}>
          {layout.edges.map((edge, i) => {
            const source = nodeById.get(edge.source);
            const target = nodeById.get(edge.target);
            if (!source || !target) return null;
            return (
              <line key={i} x1={source.x} y1={source.y} x2={target.x} y2={target.y} />
            );
          })}
        </g>
        <g>
          {layout.nodes.map((node) => (
            <circle
              key={node.id}
              cx={node.x}
              cy={node.y}
              r={6 + node.degree * 1.5}
              className={`cursor-pointer ${VERDICT_FILL_CLASSES[node.verdict ?? "none"]}`}
              onClick={() => router.push(`/nodes/${node.id}`)}
            >
              <title>{node.title}</title>
            </circle>
          ))}
        </g>
      </svg>
      {data.unresolved.length > 0 && (
        <p className="text-xs text-muted">
          {data.unresolved.length} unresolved link{data.unresolved.length === 1 ? "" : "s"}:{" "}
          {data.unresolved.join(", ")}
        </p>
      )}
    </div>
  );
}
