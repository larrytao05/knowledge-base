import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { BacklinkList } from "@/components/BacklinkList";
import { CheckCard } from "@/components/CheckCard";
import { NodeBody } from "@/components/NodeBody";
import { NodeEditor } from "@/components/NodeEditor";
import { RunCheckButton } from "@/components/RunCheckButton";
import { UnresolvedLink } from "@/components/UnresolvedLink";
import { ApiError, getNode } from "@/lib/api";
import { formatRelativeTime } from "@/lib/format";
import type { LinkRef } from "@/types";

type Props = {
  params: Promise<{ id: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  try {
    const node = await getNode(id);
    return { title: node.title };
  } catch {
    return { title: "Node" };
  }
}

function LinkList({ links, emptyLabel }: { links: LinkRef[]; emptyLabel: string }) {
  if (links.length === 0) {
    return <p className="text-sm text-muted">{emptyLabel}</p>;
  }

  return (
    <ul className="flex flex-col gap-1">
      {links.map((l, i) => (
        <li key={i}>
          {l.node_id ? (
            <Link href={`/nodes/${l.node_id}`} className="text-sm text-accent hover:underline">
              {l.title ?? l.target_raw}
            </Link>
          ) : (
            <UnresolvedLink
              target={l.target_raw}
              label={l.alias ?? l.target_raw}
              className="text-sm"
            />
          )}
        </li>
      ))}
    </ul>
  );
}

export default async function NodeDetailPage({ params }: Props) {
  const { id } = await params;

  let node;
  try {
    node = await getNode(id);
  } catch (err) {
    if (err instanceof ApiError && (err.status === 404 || err.status === 422)) {
      notFound();
    }
    throw err;
  }

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-12">
      <Link href="/" className="text-sm text-muted hover:text-accent">
        ← Back
      </Link>

      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-3">
          <h1 className="font-mono text-2xl font-semibold text-foreground">
            {node.title}
          </h1>
        </div>
        {node.tags.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {node.tags.map((tag) => (
              <span
                key={tag}
                className="rounded-full border border-border-subtle px-2 py-0.5 text-xs text-muted"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
        <p className="text-xs text-muted">
          Created {formatRelativeTime(node.created_at)} · Updated{" "}
          {formatRelativeTime(node.updated_at)}
        </p>
      </div>

      <div className="flex flex-col gap-2">
        <h2 className="text-lg font-medium">Body</h2>
        <NodeBody body={node.body} linksOut={node.links_out} />
      </div>

      <NodeEditor node={node} />

      <RunCheckButton nodeId={node.id} />

      <div className="flex flex-col gap-2">
        <h2 className="text-lg font-medium">Links</h2>
        <LinkList links={node.links_out} emptyLabel="No links yet." />
      </div>

      <div className="flex flex-col gap-2">
        <h2 className="text-lg font-medium">Backlinks</h2>
        <BacklinkList backlinks={node.backlinks} />
      </div>

      <div className="flex flex-col gap-4">
        <h2 className="text-lg font-medium">Checks</h2>
        {node.checks.length === 0 && <p className="text-sm text-muted">No checks yet.</p>}
        {node.checks.map((check) => (
          <CheckCard key={check.id} check={check} />
        ))}
      </div>
    </main>
  );
}
