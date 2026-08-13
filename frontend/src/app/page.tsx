import Link from "next/link";
import { Card } from "@/components/Card";
import { NodeForm } from "@/components/NodeForm";
import { SearchBar } from "@/components/SearchBar";
import { TagFilter } from "@/components/TagFilter";
import { VerdictBadge } from "@/components/VerdictBadge";
import { listNodes } from "@/lib/api";
import { formatRelativeTime } from "@/lib/format";

function firstValue(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export default async function Home(props: PageProps<"/">) {
  const params = await props.searchParams;
  const q = firstValue(params.q);
  const tag = firstValue(params.tag);
  const nodes = await listNodes({ q, tag });
  const tags = Array.from(new Set(nodes.flatMap((node) => node.tags))).sort();

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-8 px-4 py-12">
      <div>
        <h1 className="text-2xl font-semibold">Knowledge Base</h1>
        <p className="mt-1 text-sm text-muted">
          Write notes, link them with [[wikilinks]], and tag them.
        </p>
      </div>

      <NodeForm />

      <div className="flex flex-col gap-4">
        <SearchBar />
        <TagFilter tags={tags} activeTag={tag} q={q} />
      </div>

      <div className="flex flex-col gap-3">
        {nodes.length === 0 && (
          <p className="text-sm text-muted">No nodes yet — add one above.</p>
        )}
        {nodes.map((node) => (
          <Link key={node.id} href={`/nodes/${node.id}`}>
            <Card className="transition-colors hover:border-accent/50">
              <div className="flex items-start justify-between gap-4">
                <div className="flex flex-col gap-1">
                  <div className="font-medium">{node.title}</div>
                </div>
                {node.latest_verdict && <VerdictBadge verdict={node.latest_verdict} />}
              </div>
              {node.excerpt && (
                <p className="mt-1 line-clamp-2 text-sm text-muted">{node.excerpt}</p>
              )}
              <div className="mt-2 flex flex-wrap items-center gap-2">
                {node.tags.map((t) => (
                  <span
                    key={t}
                    className="rounded-full border border-border-subtle px-2 py-0.5 font-mono text-xs text-muted"
                  >
                    {t}
                  </span>
                ))}
                <span className="ml-auto text-xs text-muted">
                  {formatRelativeTime(node.updated_at)}
                </span>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </main>
  );
}
