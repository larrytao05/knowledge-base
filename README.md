# Knowledge Base

A personal knowledge base: write markdown notes ("nodes"), link them with `[[wikilinks]]`, tag them, and browse an in-app graph of how they connect. Any node can carry a stock ticker, in which case an LLM agent (via [OpenRouter](https://openrouter.ai)) can fact-check it against the web, returning a verdict (on track / diverging / unclear) with reasoning and sources.

Markdown files under `vault/` are the source of truth — SQLite is just a rebuildable index built by scanning that folder. Edit a note directly on disk (in an editor, or Obsidian by opening `vault/` as a vault) and the app picks it up.

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
