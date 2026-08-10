import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Card } from "@/components/Card";
import { TriggerCheckButton } from "@/components/TriggerCheckButton";
import { VerdictBadge } from "@/components/VerdictBadge";
import { getThesis } from "@/lib/api";
import { formatRelativeTime } from "@/lib/format";

type Props = {
  params: Promise<{ id: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  try {
    const thesis = await getThesis(Number(id));
    return { title: `${thesis.ticker} – Thesis Tracker` };
  } catch {
    return { title: "Thesis Tracker" };
  }
}

export default async function ThesisDetailPage({ params }: Props) {
  const { id } = await params;
  const thesisId = Number(id);

  let thesis;
  try {
    thesis = await getThesis(thesisId);
  } catch {
    notFound();
  }

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-12">
      <div>
        <h1 className="font-mono text-2xl font-semibold text-accent">{thesis.ticker}</h1>
        <p className="mt-2 whitespace-pre-wrap text-sm text-foreground">{thesis.thesis_text}</p>
        <p className="mt-2 text-xs text-muted">Added {formatRelativeTime(thesis.created_at)}</p>
      </div>

      <TriggerCheckButton thesisId={thesis.id} />

      <div className="flex flex-col gap-4">
        <h2 className="text-lg font-medium">Checks</h2>
        {thesis.checks.length === 0 && <p className="text-sm text-muted">No checks yet.</p>}
        {thesis.checks.map((check) => (
          <Card key={check.id} className="flex flex-col gap-2">
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
        ))}
      </div>
    </main>
  );
}
