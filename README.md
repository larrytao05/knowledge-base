# Thesis Tracker

Write a short investment thesis for a stock. An LLM agent (via [OpenRouter](https://openrouter.ai)) searches the web for recent evidence and checks it against your thesis, returning a verdict (on track / diverging / unclear) with reasoning and sources.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) for the Python backend
- Node.js 20+ for the Next.js frontend
- A free [OpenRouter](https://openrouter.ai/keys) API key

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

- Data is stored in SQLite at `backend/thesis_tracker.db`. `DATABASE_URL` in `backend/.env` can be swapped to a Postgres URL later without code changes.
- `OPENROUTER_MODEL` defaults to `openrouter/free`, an auto-router alias that picks a currently-healthy free model for you — this is more reliable than pinning a specific `:free` model, since individual free models get rate-limited or pulled from the free tier without notice. If you want a specific model instead, check [openrouter.ai/models?max_price=0](https://openrouter.ai/models?max_price=0) and set `OPENROUTER_MODEL` in `backend/.env` — no code change needed.
- Web search is done via OpenRouter's built-in `web` plugin, so no separate search API key is needed.
