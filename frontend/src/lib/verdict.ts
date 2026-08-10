import type { Verdict } from "@/types";

export const VERDICT_LABELS: Record<Verdict, string> = {
  on_track: "On Track",
  diverging: "Diverging",
  unclear: "Unclear",
};

export const VERDICT_BADGE_CLASSES: Record<Verdict, string> = {
  on_track: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
  diverging: "bg-red-500/10 text-red-400 border-red-500/30",
  unclear: "bg-amber-500/10 text-amber-400 border-amber-500/30",
};

export const VERDICT_FILL_CLASSES: Record<Verdict | "none", string> = {
  on_track: "fill-emerald-400",
  diverging: "fill-red-400",
  unclear: "fill-amber-400",
  none: "fill-muted",
};
