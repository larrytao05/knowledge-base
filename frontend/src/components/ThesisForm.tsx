"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { createThesis } from "@/lib/api";
import { Card } from "./Card";
import { Spinner } from "./Spinner";

const inputClass =
  "rounded border border-border-default bg-background px-3 py-2 text-sm text-foreground " +
  "placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent";

export function ThesisForm() {
  const router = useRouter();
  const [ticker, setTicker] = useState("");
  const [thesisText, setThesisText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await createThesis({ ticker, thesis_text: thesisText });
      setTicker("");
      setThesisText("");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create thesis");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <div className="flex flex-col gap-1">
          <label htmlFor="ticker" className="text-sm font-medium">
            Ticker
          </label>
          <input
            id="ticker"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="NVDA"
            required
            maxLength={10}
            className={`${inputClass} font-mono uppercase`}
          />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="thesis" className="text-sm font-medium">
            Thesis
          </label>
          <textarea
            id="thesis"
            value={thesisText}
            onChange={(e) => setThesisText(e.target.value)}
            placeholder="AI datacenter capex growth continues through 2027..."
            required
            rows={3}
            className={inputClass}
          />
        </div>
        {error && <p className="text-sm text-red-400">{error}</p>}
        <button
          type="submit"
          disabled={submitting}
          className="inline-flex w-fit items-center gap-2 rounded bg-accent px-4 py-2 text-sm font-medium text-background hover:bg-accent/90 disabled:opacity-50"
        >
          {submitting && <Spinner className="h-4 w-4" />}
          {submitting ? "Adding..." : "Add thesis"}
        </button>
      </form>
    </Card>
  );
}
