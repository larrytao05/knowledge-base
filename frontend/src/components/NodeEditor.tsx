"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Card } from "@/components/Card";
import { Spinner } from "@/components/Spinner";
import { WikilinkTextarea } from "@/components/WikilinkTextarea";
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

/** Both the stale-content conflict and a rename collision come back as 409, but
 * only the former carries an object detail with the note to reload from. */
function staleContentDetail(
  err: unknown,
): { message?: string; current?: NodeDetail | null } | null {
  if (!(err instanceof ApiError) || err.status !== 409) return null;
  const detail = (err.body as { detail?: unknown } | null)?.detail;
  if (!detail || typeof detail !== "object") return null;
  return detail as { message?: string; current?: NodeDetail | null };
}

export function NodeEditor({ node }: { node: NodeDetail }) {
  const router = useRouter();
  const [title, setTitle] = useState(node.title);
  const [tagsText, setTagsText] = useState(node.tags.join(", "));
  const [body, setBody] = useState(node.body);
  const [contentHash, setContentHash] = useState(node.content_hash);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conflict, setConflict] = useState<ConflictState | null>(null);
  const [skipped, setSkipped] = useState(0);
  const [leftAlone, setLeftAlone] = useState(0);

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

  // A save can rewrite the body server-side (renaming retargets this note's own
  // wikilinks), so the form has to take the saved note back or the next save
  // would push the pre-rename body up under a hash the server just accepted.
  function adopt(saved: NodeDetail) {
    setTitle(saved.title);
    setTagsText(saved.tags.join(", "));
    setBody(saved.body);
    setContentHash(saved.content_hash);
  }

  async function performSave(hash: string) {
    setSaving(true);
    setError(null);
    try {
      const updated = await updateNode(node.id, {
        content_hash: hash,
        title,
        body,
        tags: parseTags(tagsText),
      });
      adopt(updated);
      setConflict(null);
      setSkipped(updated.link_rewrite_skipped);
      setLeftAlone(updated.links_left_at_old_title);
      router.refresh();
    } catch (err) {
      const detail = staleContentDetail(err);
      if (detail) {
        setConflict({
          message: detail.message ?? "This note changed on disk",
          current: detail.current ?? null,
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
    adopt(conflict.current);
    setConflict(null);
    setSkipped(0);
    setLeftAlone(0);
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
          disabled={saving}
          className={inputClass}
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
          disabled={saving}
          className={inputClass}
        />
      </div>
      <div className="flex flex-col gap-1">
        <label htmlFor="body" className="text-sm font-medium">
          Body
        </label>
        <WikilinkTextarea
          id="body"
          value={body}
          onChange={setBody}
          rows={12}
          disabled={saving}
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

      {skipped > 0 && (
        <p className="text-sm text-amber-400">
          Renamed, but {skipped} {skipped === 1 ? "note" : "notes"} linking here could not be
          updated - their links still point at the old title.
        </p>
      )}

      {leftAlone > 0 && (
        <p className="text-sm text-muted">
          {leftAlone} {leftAlone === 1 ? "note still links" : "notes still link"} to the old title,
          left alone because another note still goes by it.
        </p>
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
