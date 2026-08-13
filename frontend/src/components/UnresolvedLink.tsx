"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { openOrCreateNode } from "@/lib/api";

export function UnresolvedLink({
  target,
  label,
  className,
}: {
  target: string;
  label: string;
  className?: string;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  async function handleClick() {
    setBusy(true);
    setFailed(false);
    try {
      const id = await openOrCreateNode(target);
      router.push(`/nodes/${id}`);
    } catch {
      setFailed(true);
      setBusy(false);
    }
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={busy}
      title={failed ? `Could not create "${target}"` : `Create "${target}"`}
      className={`underline decoration-dotted hover:text-accent disabled:opacity-50 ${
        failed ? "text-red-400" : "text-muted"
      } ${className ?? ""}`}
    >
      {label}
    </button>
  );
}
