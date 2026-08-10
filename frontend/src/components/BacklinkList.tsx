import Link from "next/link";
import type { LinkRef } from "@/types";

export function BacklinkList({ backlinks }: { backlinks: LinkRef[] }) {
  const resolved = backlinks.filter((b) => b.node_id !== null);

  if (resolved.length === 0) {
    return <p className="text-sm text-muted">No backlinks yet.</p>;
  }

  return (
    <ul className="flex flex-col gap-1">
      {resolved.map((b, i) => (
        <li key={i}>
          <Link href={`/nodes/${b.node_id}`} className="text-sm text-accent hover:underline">
            {b.title ?? b.target_raw}
          </Link>
        </li>
      ))}
    </ul>
  );
}
