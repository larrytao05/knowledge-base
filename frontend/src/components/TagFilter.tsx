import Link from "next/link";

export function TagFilter({ tags, activeTag, q }: { tags: string[]; activeTag?: string; q?: string }) {
  if (tags.length === 0) return null;

  function hrefFor(tag?: string) {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (tag) params.set("tag", tag);
    const qs = params.toString();
    return qs ? `/?${qs}` : "/";
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      {tags.map((tag) => (
        <Link
          key={tag}
          href={hrefFor(tag)}
          className={`rounded-full border px-3 py-1 font-mono text-xs ${
            tag === activeTag
              ? "border-accent bg-accent/10 text-accent"
              : "border-border-subtle text-muted hover:border-accent/50 hover:text-accent"
          }`}
        >
          {tag}
        </Link>
      ))}
      {activeTag && (
        <Link href={hrefFor()} className="font-mono text-xs text-muted hover:text-accent">
          clear
        </Link>
      )}
    </div>
  );
}
