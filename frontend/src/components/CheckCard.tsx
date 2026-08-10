import { Card } from "@/components/Card";
import { VerdictBadge } from "@/components/VerdictBadge";
import { formatRelativeTime } from "@/lib/format";
import type { CheckRead } from "@/types";

export function CheckCard({ check }: { check: CheckRead }) {
  return (
    <Card className="flex flex-col gap-2">
      <div className="flex items-center justify-between gap-2">
        <VerdictBadge verdict={check.verdict} />
        <span className="text-xs text-muted">{formatRelativeTime(check.created_at)}</span>
      </div>
      <p className="whitespace-pre-wrap text-sm text-foreground">{check.reasoning}</p>
      {check.sources.length > 0 && (
        <div className="flex flex-wrap gap-2 pt-1">
          {check.sources.map((source, i) => (
            <a
              key={i}
              href={source.url}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded border border-border-default px-2 py-1 text-xs text-muted hover:border-accent hover:text-accent"
            >
              {source.title ?? source.url}
            </a>
          ))}
        </div>
      )}
    </Card>
  );
}
