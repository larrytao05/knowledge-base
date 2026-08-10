"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Spinner } from "@/components/Spinner";
import { ApiError, runNodeCheck } from "@/lib/api";

export function RunCheckButton({ nodeId }: { nodeId: string }) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    setLoading(true);
    setError(null);
    try {
      await runNodeCheck(nodeId);
      router.refresh();
    } catch (err) {
      if (err instanceof ApiError && err.status === 502) {
        setError(err.message);
      } else {
        setError(err instanceof Error ? err.message : "Check failed");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-1">
      <button
        onClick={handleClick}
        disabled={loading}
        className="inline-flex w-fit items-center gap-2 rounded bg-accent px-4 py-2 text-sm font-medium text-background hover:bg-accent/90 disabled:opacity-50"
      >
        {loading && <Spinner className="h-4 w-4" />}
        {loading ? "Running check..." : "Run check now"}
      </button>
      {loading && <p className="text-xs text-muted">This can take up to 30s.</p>}
      {error && <p className="text-sm text-red-400">{error}</p>}
    </div>
  );
}
