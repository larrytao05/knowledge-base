import Link from "next/link";
import { Card } from "@/components/Card";
import { GraphView } from "@/components/GraphView";
import { getGraph } from "@/lib/api";

export default async function GraphPage() {
  const graph = await getGraph();

  return (
    <main className="mx-auto flex max-w-4xl flex-col gap-6 px-4 py-12">
      <div>
        <Link href="/" className="text-sm text-muted hover:text-accent">
          &larr; Back
        </Link>
        <h1 className="mt-2 text-2xl font-semibold">Graph</h1>
      </div>

      <Card className="h-[600px] w-full">
        <GraphView data={graph} />
      </Card>
    </main>
  );
}
