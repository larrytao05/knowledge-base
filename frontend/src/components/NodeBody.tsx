import Link from "next/link";
import { extractLinks, normalizeTitle, stripCode } from "@/lib/wikilinks";
import type { LinkRef } from "@/types";

const WIKILINK_RE = /\[\[([^[\]|#\n]+?)(?:#([^[\]|\n]+?))?(?:\|([^[\]\n]+?))?\]\]/g;

export function NodeBody({ body, linksOut }: { body: string; linksOut: LinkRef[] }) {
  const links = extractLinks(body);
  const resolvedByNorm = new Map<string, LinkRef>();
  for (const ref of linksOut) {
    resolvedByNorm.set(normalizeTitle(ref.target_raw), ref);
  }

  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let linkIndex = 0;

  // Match against the code-stripped body so offsets skip links that live inside
  // code blocks/spans (blanking preserves string length, so indices still map
  // back onto the raw body) and stay in lockstep with extractLinks's matches.
  const stripped = stripCode(body);
  for (const match of stripped.matchAll(WIKILINK_RE)) {
    const start = match.index ?? 0;
    const end = start + match[0].length;
    parts.push(body.slice(lastIndex, start));

    const link = links[linkIndex];
    linkIndex += 1;
    const label = link?.alias ?? match[0];
    const resolved = link ? resolvedByNorm.get(link.norm) : undefined;

    if (resolved?.node_id) {
      parts.push(
        <Link
          key={start}
          href={`/nodes/${resolved.node_id}`}
          className="text-accent hover:underline"
        >
          {label}
        </Link>,
      );
    } else {
      parts.push(
        <span key={start} className="text-muted underline decoration-dotted">
          {label}
        </span>,
      );
    }

    lastIndex = end;
  }
  parts.push(body.slice(lastIndex));

  return <div className="whitespace-pre-wrap text-sm text-foreground">{parts}</div>;
}
