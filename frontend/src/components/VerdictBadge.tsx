import type { Verdict } from "@/types";

const LABELS: Record<Verdict, string> = {
  on_track: "On Track",
  diverging: "Diverging",
  unclear: "Unclear",
};

const STYLES: Record<Verdict, string> = {
  on_track: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
  diverging: "bg-red-500/10 text-red-400 border-red-500/30",
  unclear: "bg-amber-500/10 text-amber-400 border-amber-500/30",
};

export function VerdictBadge({ verdict }: { verdict: Verdict }) {
  return (
    <span
      className={`inline-block rounded-full border px-3 py-1 font-mono text-xs font-medium tracking-wide ${STYLES[verdict]}`}
    >
      {LABELS[verdict]}
    </span>
  );
}
