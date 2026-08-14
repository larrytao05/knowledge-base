# Knowledge Base

A personal knowledge base: write markdown notes ("nodes"), link them with `[[wikilinks]]`, tag them, and browse an in-app graph of how they connect. Any node can be fact-checked against the web by an LLM agent (via [OpenRouter](https://openrouter.ai)), returning a verdict (on track / diverging / unclear) with reasoning and sources.

Markdown files under `vault/` are the source of truth — SQLite is just a rebuildable index built by scanning that folder. Edit a note directly on disk (in an editor, or Obsidian by opening `vault/` as a vault) and the app picks it up.

## What it does

- **Write and edit notes** in the browser, or on disk in any editor. Both directions stay in sync.
- **Link notes with `[[wikilinks]]`**, including `[[Note#Heading]]` anchors and `[[Note|display text]]` aliases. Typing `[[` in a note body opens a keyboard-navigable completion list of existing notes.
- **Link to notes that don't exist yet.** Unresolved links render distinctly and clicking one creates that note and opens it — the link-first workflow Obsidian popularized.
- **Follow links in both directions.** Every note shows its outgoing links and its backlinks; the reverse index is derived, never stored in the file.
- **Rename safely.** Renaming a note retargets `[[old title]]` across every other file in the vault, preserving anchors and aliases, and reports honestly when it deliberately left links alone.
- **Browse the graph.** Notes are nodes, resolved links are edges, laid out with a force simulation and colored by the latest fact-check verdict.
- **Fact-check a note.** An LLM agent searches the web, then returns a structured verdict with reasoning and cited sources. The result is written back into the vault as its own markdown file.

## Stack

### Backend (`backend/`)

| | |
|---|---|
| Language | Python 3.12+ |
| Framework | FastAPI, served by uvicorn |
| ORM | SQLAlchemy 2.0 (typed `Mapped[...]` models) |
| Database | SQLite — a derived index, not a store of record |
| Validation | Pydantic v2, settings via pydantic-settings + `.env` |
| Frontmatter | PyYAML, with a custom dumper that quotes strings YAML would otherwise reinterpret |
| LLM | `openai` SDK pointed at OpenRouter's base URL |
| Tooling | `uv`, ruff (line length 100), mypy in `strict` mode, pytest + httpx |

Three tables. `nodes` holds one row per markdown file — id, path, title, normalized title, kind (`note` or `check`), tags, body, content hash, and the `(mtime_ns, size)` signature used for change detection. `node_links` holds one row per wikilink occurrence, storing both the raw target and its normalized form. `checks` holds fact-check results with their verdict, reasoning, and sources.

Services split by concern: `vault_io` (parsing, serializing, atomic writes, path safety), `indexer` (scanning the vault into the tables), `wikilinks` (the link grammar), `notes` (create/update/rename orchestration), `agent` (the OpenRouter call), `locks` (concurrency).

### Frontend (`frontend/`)

| | |
|---|---|
| Framework | Next.js 16.3, App Router |
| UI | React 19.2, TypeScript 5 |
| Styling | Tailwind CSS v4 (via `@tailwindcss/postcss`) |
| Graph layout | `d3-force` |
| Testing | Vitest, Testing Library, jsdom |
| Tooling | ESLint 9 with `eslint-config-next` |

Pages are React Server Components that fetch from the API and pass data into client components for anything interactive — the note editor, the wikilink autocomplete, the graph canvas.

### API

```
GET    /api/nodes              list + search (?q=, ?tag=)
POST   /api/nodes              create
GET    /api/nodes/{id}         detail, with links_out, backlinks, checks
PATCH  /api/nodes/{id}         update title / body / tags
POST   /api/nodes/{id}/checks  run a fact-check
GET    /api/graph              nodes, edges, unresolved link targets
POST   /api/vault/reindex      rebuild the index from disk
```

## Design decisions

**The files are the product; the database is a cache.** Every byte a user cares about lives in a `.md` file under `vault/`. SQLite exists only to make queries fast and can be deleted at any time — `POST /api/vault/reindex` rebuilds it by walking the folder. Nothing is ever written to the index that can't be recovered from the files, which is what makes it safe to edit the same vault in Obsidian and in this app.

**Sync happens on read, cheaply.** Rather than watch the filesystem, a FastAPI dependency re-scans the vault before handling a request, throttled to once every 300ms. A file is only re-parsed when its `(mtime_ns, size)` signature changes — plus a two-second grace window, since a same-size edit written moments ago can otherwise look unchanged.

**Notes are identified by a stamped id, not by their path.** The indexer writes a short hex `id` into each file's frontmatter, so renaming or moving a file on disk doesn't create a new note or orphan its fact-check history.

**Writes are atomic, locked, and backed up.** Every write goes through a write-to-temp-then-rename, guarded by a per-path lock, with the previous contents copied into `.vault-backups/`. A rename touches many files at once, so partial failure is expected to be survivable rather than impossible: individual files can't be truncated, the index is always re-synced afterwards, and the response reports how many files it couldn't update instead of failing an edit that already applied.

**Concurrent edits are caught, not clobbered.** `PATCH` requires the `content_hash` the client last saw. If the file changed underneath — usually because it was edited in Obsidian — the API returns 409 along with the current state, and the editor offers to reload or overwrite.

**The wikilink grammar is implemented twice, and kept honest.** The parser exists in Python (for indexing and rename rewriting) and in TypeScript (for rendering and autocomplete), because both sides need it and shipping a WASM build for a personal app isn't worth it. The risk is drift, so the two are deliberately structured to agree: same character classes, same normalization (strip `.md`, collapse whitespace, casefold), and group offsets computed the same way rather than by re-parsing.

**Links inside code are not links.** Fenced blocks and inline spans are blanked out before matching — replaced with spaces of identical length, so every offset in the stripped copy still maps onto the original text. That invariant is what lets the renderer highlight links in raw prose and the rewriter splice replacements into raw file text.

**A rename only retargets links it's sure about.** If another note still holds the old title, inbound `[[old title]]` links are left alone: they now unambiguously mean the note that kept the title, and rewriting them would silently repoint them at a note they never referenced. The API distinguishes "deliberately left alone" from "failed to update" so the UI doesn't raise an alarm for a correct outcome.

**Titles the grammar can't address are rejected at creation, tolerated on disk.** A title containing `[`, `]`, `#`, or `|` can never be reached by a `[[wikilink]]` (Obsidian bans the same set), so creating one is a 422. But a vault co-edited elsewhere may already contain such a title, and refusing to save those notes would make them permanently uneditable — so they load and edit fine, and only a *rename to* an unaddressable title is refused.

**Fact-checks are notes too.** A check isn't a database row with a file attached; it's a markdown file in `vault/checks/` with the verdict in its frontmatter, indexed like anything else. The vault stays a complete, portable record of everything the app knows.

**The model is a configuration detail.** `OPENROUTER_MODEL` defaults to `openrouter/free`, an auto-router alias that picks a currently-healthy free model. Swapping models is an env var, not a code change, and web search goes through OpenRouter's built-in `web` plugin so there's no second API key to manage.

## Repository layout

```
backend/
  app/
    routers/     nodes, graph, vault
    services/    vault_io, indexer, wikilinks, notes, agent, locks
    models.py    SQLAlchemy tables
    schemas.py   Pydantic request/response models
  tests/
frontend/
  src/
    app/         App Router pages
    components/  editor, autocomplete, graph, cards
    lib/         API client, wikilink parser, force layout
vault/           your notes (gitignored)
```

## Prerequisites

- [uv](https://docs.astral.sh/uv/) for the Python backend
- Node.js 20+ for the Next.js frontend
- A free [OpenRouter](https://openrouter.ai/keys) API key (only needed to run fact-checks)

## Setup

```
make install
cp backend/.env.example backend/.env      # fill in OPENROUTER_API_KEY
cp frontend/.env.local.example frontend/.env.local
```

## Run

```
make backend-dev    # http://localhost:8000
make frontend-dev   # http://localhost:3000
```

(run each in its own terminal)

## Checks

```
make lint
make typecheck
make test
```

## Notes

- Notes live as `.md` files in `vault/` (gitignored — personal data, not code); the SQLite index at `backend/vault_index.db` can be deleted and rebuilt at any time via `POST /api/vault/reindex`, since it's derived entirely from the files.
- `OPENROUTER_MODEL` defaults to `openrouter/free`, an auto-router alias that picks a currently-healthy free model for you — this is more reliable than pinning a specific `:free` model, since individual free models get rate-limited or pulled from the free tier without notice. If you want a specific model instead, check [openrouter.ai/models?max_price=0](https://openrouter.ai/models?max_price=0) and set `OPENROUTER_MODEL` in `backend/.env` — no code change needed.
- Web search is done via OpenRouter's built-in `web` plugin, so no separate search API key is needed.
- The frontend pins an exact Next.js version, and its docs ship inside `frontend/node_modules/next/dist/docs/`. Check those rather than general Next.js knowledge when touching App Router code.
