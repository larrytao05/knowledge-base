import Link from "next/link";
import { Card } from "@/components/Card";
import { ThesisForm } from "@/components/ThesisForm";
import { listTheses } from "@/lib/api";

export default async function Home() {
  const theses = await listTheses();

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-8 px-4 py-12">
      <div>
        <h1 className="text-2xl font-semibold">Thesis Tracker</h1>
        <p className="mt-1 text-sm text-muted">
          Write an investment thesis. An agent checks it against the news.
        </p>
      </div>

      <ThesisForm />

      <div className="flex flex-col gap-3">
        {theses.length === 0 && (
          <p className="text-sm text-muted">No theses yet — add one above.</p>
        )}
        {theses.map((thesis) => (
          <Link key={thesis.id} href={`/theses/${thesis.id}`}>
            <Card className="transition-colors hover:border-accent/50">
              <div className="font-mono font-medium text-accent">{thesis.ticker}</div>
              <p className="mt-1 line-clamp-2 text-sm text-muted">{thesis.thesis_text}</p>
            </Card>
          </Link>
        ))}
      </div>
    </main>
  );
}
