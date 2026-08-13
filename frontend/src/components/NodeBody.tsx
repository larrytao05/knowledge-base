import Link from "next/link";
import { UnresolvedLink } from "@/components/UnresolvedLink";
import { groupFrom, normalizeTitle, stripCode, WIKILINK_RE } from "@/lib/wikilinks";
import type { LinkRef } from "@/types";

export function NodeBody({ body, linksOut }: { body: string; linksOut: LinkRef[] }) {
  const resolvedByNorm = new Map<string, LinkRef>();
  for (const ref of linksOut) {
    resolvedByNorm.set(normalizeTitle(ref.target_raw), ref);
  }

  const parts: React.ReactNode[] = [];
  let lastIndex = 0;

  // Match against the code-stripped body so offsets skip links that live inside
  // code blocks/spans (blanking preserves string length, so indices still map
  // back onto the raw body). Each match is read on its own - pairing matches up
  // with extractLinks by position desyncs on the targets extractLinks skips.
  const stripped = stripCode(body);
  for (const match of stripped.matchAll(WIKILINK_RE)) {
    const start = match.index ?? 0;
    const end = start + match[0].length;

    // Groups come out of the raw body, not the stripped copy, so a link holding
    // inline code keeps its real text - both in what is shown and in the title a
    // click would create.
    // The indexer ignores empty targets, so they are not links here either -
    // leaving lastIndex alone renders them as the plain text they are.
    const target = (groupFrom(body, match, 1) ?? "").trim();
    if (!target) continue;

    parts.push(body.slice(lastIndex, start));

    const aliasGroup = groupFrom(body, match, 3);
    const alias = aliasGroup ? aliasGroup.trim() : null;
    const label = alias ?? body.slice(start, end);
    const resolved = resolvedByNorm.get(normalizeTitle(target));

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
      parts.push(<UnresolvedLink key={start} target={target} label={label} />);
    }

    lastIndex = end;
  }
  parts.push(body.slice(lastIndex));

  return <div className="whitespace-pre-wrap text-sm text-foreground">{parts}</div>;
}
