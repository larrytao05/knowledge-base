"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

const inputClass =
  "flex-1 rounded border border-border-default bg-background px-3 py-2 text-sm text-foreground " +
  "placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent";

export function SearchBar() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [q, setQ] = useState(searchParams.get("q") ?? "");

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const params = new URLSearchParams(searchParams.toString());
    if (q) {
      params.set("q", q);
    } else {
      params.delete("q");
    }
    router.push(`/?${params.toString()}`);
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Search nodes..."
        className={inputClass}
      />
      <button
        type="submit"
        className="rounded border border-border-default px-3 py-2 text-sm font-medium hover:border-accent hover:text-accent"
      >
        Search
      </button>
    </form>
  );
}
