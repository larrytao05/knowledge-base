"use client";

import { useEffect, useRef, useState } from "react";
import { listNodes } from "@/lib/api";
import {
  activeWikilinkQuery,
  insertWikilink,
  isLinkableTitle,
  type WikilinkQuery,
} from "@/lib/wikilinks";
import type { NodeSummary } from "@/types";

const MAX_OPTIONS = 8;
const DEBOUNCE_MS = 120;

interface Props {
  id: string;
  value: string;
  onChange: (value: string) => void;
  rows: number;
  className: string;
  placeholder?: string;
  disabled?: boolean;
}

// Re-filtering the last search locally keeps the list from blanking out between
// keystrokes: extending the query only ever narrows what the server would return.
// Titles that no wikilink can address (notes written outside the app) are dropped
// rather than offered as a completion that would never resolve.
function matchingOptions(nodes: NodeSummary[], queryText: string | null): NodeSummary[] {
  if (queryText === null) return [];
  const needle = queryText.toLowerCase();
  return nodes
    .filter((n) => isLinkableTitle(n.title) && n.title.toLowerCase().includes(needle))
    .slice(0, MAX_OPTIONS);
}

export function WikilinkTextarea({
  id,
  value,
  onChange,
  rows,
  className,
  placeholder,
  disabled,
}: Props) {
  const ref = useRef<HTMLTextAreaElement>(null);
  const pendingCaret = useRef<number | null>(null);
  const [query, setQuery] = useState<WikilinkQuery | null>(null);
  const [fetched, setFetched] = useState<NodeSummary[]>([]);
  const [active, setActive] = useState(0);
  const [dismissedAt, setDismissedAt] = useState<number | null>(null);

  const queryText = query ? query.query : null;
  const options = matchingOptions(fetched, queryText);
  const activeIndex = active < options.length ? active : 0;
  const open = query !== null && query.start !== dismissedAt && options.length > 0;

  useEffect(() => {
    if (queryText === null) return;

    let cancelled = false;
    const timer = setTimeout(async () => {
      try {
        const results = await listNodes({ q: queryText });
        if (!cancelled) setFetched(results);
      } catch {
        if (!cancelled) setFetched([]);
      }
    }, DEBOUNCE_MS);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [queryText]);

  useEffect(() => {
    if (pendingCaret.current === null) return;
    ref.current?.setSelectionRange(pendingCaret.current, pendingCaret.current);
    pendingCaret.current = null;
  }, [value]);

  function syncQuery(el: HTMLTextAreaElement) {
    const next = activeWikilinkQuery(el.value, el.selectionStart);
    setQuery(next);
    setActive(0);
    if (next === null || next.start !== dismissedAt) setDismissedAt(null);
  }

  function choose(option: NodeSummary) {
    if (!query) return;
    const next = insertWikilink(value, query, option.title);
    onChange(next.text);
    setQuery(null);
    setDismissedAt(null);

    if (next.text === value) {
      // The completion changed nothing, so no re-render is coming to run the
      // effect - move the caret now instead of leaving a stale pending one.
      ref.current?.setSelectionRange(next.caret, next.caret);
      return;
    }
    pendingCaret.current = next.caret;
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (!open || !query) return;
    // Enter commits an IME candidate mid-composition; taking it as a selection
    // here would throw the composition away.
    if (event.nativeEvent.isComposing) return;

    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive((activeIndex + 1) % options.length);
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((activeIndex - 1 + options.length) % options.length);
      return;
    }
    if (event.key === "Enter" || event.key === "Tab") {
      event.preventDefault();
      choose(options[activeIndex]);
      return;
    }
    if (event.key === "Escape") {
      event.preventDefault();
      setDismissedAt(query.start);
    }
  }

  return (
    <div className="relative">
      <textarea
        id={id}
        ref={ref}
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
          syncQuery(e.target);
        }}
        onSelect={(e) => syncQuery(e.currentTarget)}
        onKeyDown={handleKeyDown}
        onBlur={() => setQuery(null)}
        rows={rows}
        placeholder={placeholder}
        disabled={disabled}
        className={`w-full ${className}`}
      />
      {open && !disabled && (
        <ul className="absolute left-0 top-full z-10 mt-1 max-h-56 w-full overflow-auto rounded border border-border-default bg-background py-1">
          {options.map((option, i) => (
            <li key={option.id}>
              <button
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onMouseEnter={() => setActive(i)}
                onClick={() => choose(option)}
                className={`block w-full px-3 py-1.5 text-left text-sm ${
                  i === activeIndex ? "bg-accent/15 text-accent" : "text-foreground"
                }`}
              >
                {option.title}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
