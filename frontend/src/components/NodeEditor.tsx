"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Card } from "@/components/Card";
import { Spinner } from "@/components/Spinner";
import { ApiError, updateNode } from "@/lib/api";
import type { NodeDetail } from "@/types";

const inputClass =
  "rounded border border-border-default bg-background px-3 py-2 text-sm text-foreground " +
  "placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent";

interface ConflictState {
  message: string;
  current: NodeDetail | null;
}

function parseTags(text: string): string[] {
  return text
    .split(",")
    .map((t) => t.trim())
    .filter((t) => t.length > 0);
}

export function NodeEditor({ node }: { node: NodeDetail }) {
  const router = useRouter();
  const [title, setTitle] = useState(node.title);
  const [ticker, setTicker] = useState(node.ticker ?? "");
  const [tagsText, setTagsText] = useState(node.tags.join(", "));
  const [body, setBody] = useState(node.body);
  const [contentHash, setContentHash] = useState(node.content_hash);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conflict, setConflict] = useState<ConflictState | null>(null);

  if (node.fm_error) {
    return (
      <Card className="flex flex-col gap-2">
        <p className="text-sm font-medium text-foreground">
          Editing disabled - invalid frontmatter
        </p>
        <p className="whitespace-pre-wrap text-sm text-red-400">{node.fm_error}</p>
      </Card>
    );
  }

  async function performSave(hash: string) {
    setSaving(true);
    setError(null);
    try {
      const updated = await updateNode(node.id, {
        content_hash: hash,
        title,
        body,
        ticker: ticker.trim() ? ticker.trim() : null,
        tags: parseTags(tagsText),
      });
      setContentHash(updated.content_hash);
      setConflict(null);
      router.refresh();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        const body = err.body as { detail?: { message?: string; current?: NodeDetail | null } };
        setConflict({
          message: body?.detail?.message ?? "This note changed on disk",
          current: body?.detail?.current ?? null,
        });
      } else {
        setError(err instanceof Error ? err.message : "Failed to save");
      }
    } finally {
      setSaving(false);
    }
  }

  function handleReload() {
    if (!conflict?.current) return;
    const current = conflict.current;
    setTitle(current.title);
    setTicker(current.ticker ?? "");
    setTagsText(current.tags.join(", "));
    setBody(current.body);
    setContentHash(current.content_hash);
    setConflict(null);
  }

  function handleOverwrite() {
    if (!conflict?.current) return;
    performSave(conflict.current.content_hash);
  }

  return (
    <Card className="flex flex-col gap-3">
      <div className="flex flex-col gap-1">
        <label htmlFor="title" className="text-sm font-medium">
          Title
        </label>
        <input
          id="title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className={inputClass}
        />
      </div>
      <div className="flex flex-col gap-1">
        <label htmlFor="ticker" className="text-sm font-medium">
          Ticker
        </label>
        <input
          id="ticker"
          value={ticker}
          onChange={(e) => setTicker(e.target.value.toUpperCase())}
          className={`${inputClass} font-mono uppercase`}
        />
      </div>
      <div className="flex flex-col gap-1">
        <label htmlFor="tags" className="text-sm font-medium">
          Tags
        </label>
        <input
          id="tags"
          value={tagsText}
          onChange={(e) => setTagsText(e.target.value)}
          placeholder="tag-one, tag-two"
          className={inputClass}
        />
      </div>
      <div className="flex flex-col gap-1">
        <label htmlFor="body" className="text-sm font-medium">
          Body
        </label>
        <textarea
          id="body"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={12}
          className={`${inputClass} font-mono`}
        />
      </div>

      {conflict && (
        <div className="flex flex-col gap-2 rounded border border-amber-500/30 bg-amber-500/10 p-3">
          <p className="text-sm text-amber-400">{conflict.message}</p>
          <p className="text-xs text-muted">
            Your unsaved changes are still in the form above. Choose how to proceed.
          </p>
          <div className="flex gap-2">
            <button
              onClick={handleReload}
              disabled={!conflict.current}
              className="rounded border border-border-default px-3 py-1 text-xs text-foreground hover:border-accent hover:text-accent disabled:opacity-50"
            >
              Reload (discard my changes)
            </button>
            <button
              onClick={handleOverwrite}
              disabled={!conflict.current}
              className="rounded border border-border-default px-3 py-1 text-xs text-foreground hover:border-accent hover:text-accent disabled:opacity-50"
            >
              Overwrite
            </button>
          </div>
        </div>
      )}

      {error && <p className="text-sm text-red-400">{error}</p>}

      <button
        onClick={() => performSave(contentHash)}
        disabled={saving}
        className="inline-flex w-fit items-center gap-2 rounded bg-accent px-4 py-2 text-sm font-medium text-background hover:bg-accent/90 disabled:opacity-50"
      >
        {saving && <Spinner className="h-4 w-4" />}
        {saving ? "Saving..." : "Save"}
      </button>
    </Card>
  );
}
