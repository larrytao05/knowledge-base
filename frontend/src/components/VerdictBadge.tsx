import { VERDICT_BADGE_CLASSES, VERDICT_LABELS } from "@/lib/verdict";
import type { Verdict } from "@/types";

export function VerdictBadge({ verdict }: { verdict: Verdict }) {
  return (
    <span
      className={`inline-block rounded-full border px-3 py-1 font-mono text-xs font-medium tracking-wide ${VERDICT_BADGE_CLASSES[verdict]}`}
    >
      {VERDICT_LABELS[verdict]}
    </span>
  );
}
