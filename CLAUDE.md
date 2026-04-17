# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

**Prima Pagina** is a self-hosted RSS aggregation PWA with LLM-based article tagging and digest generation, targeting 2–10 users. It is a monorepo with a FastAPI backend and a Vue 3 frontend.

---

## Development commands

### Backend (in `backend/`)

```bash
# Install dependencies
uv sync --group dev

# Run dev server (hot reload)
uvicorn app.main:app --reload --port 8000

# Run all tests (SECRET_KEY and ENCRYPTION_KEY must be set)
SECRET_KEY=test ENCRYPTION_KEY=dGVzdA== python -m pytest tests/ -v

# Run a single test file
SECRET_KEY=test ENCRYPTION_KEY=dGVzdA== python -m pytest tests/test_auth.py -v

# Run a single test
SECRET_KEY=test ENCRYPTION_KEY=dGVzdA== python -m pytest tests/test_auth.py::test_login -v

# Database migrations
python -m alembic upgrade head
python -m alembic revision --autogenerate -m "description"
```

> **Note**: use `python` / `uvicorn` / `pytest` directly from the venv (`.venv/bin/`), or activate it with `source .venv/bin/activate`. `uv run` may hang on this system due to network access attempts.

### Frontend (in `frontend/`)

```bash
npm install
npm run dev       # Vite dev server on :5173
npm run build     # Production build
npm run preview   # Preview production build
```

### Full stack (Docker)

```bash
# Development (hot reload, ports exposed)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# Production
docker compose up

# With PostgreSQL
docker compose --profile postgres up

# With Ollama
docker compose --profile ollama up
```

---

## Architecture

### Monorepo layout

- `backend/app/` — FastAPI application
  - `main.py` — app entrypoint, lifespan hooks, router mounts
  - `config.py` — `Settings` via pydantic-settings (all config from env vars)
  - `database.py` — async SQLAlchemy engine, session factory, declarative `Base`
  - `models/` — SQLAlchemy ORM models
  - `schemas/` — Pydantic request/response schemas (separate from models)
  - `api/` — FastAPI routers; `deps.py` holds shared dependencies (`get_current_user`, `get_db`)
  - `services/` — business logic (feed fetcher, full-text, ranking, RSS generator, scheduler, LLM)
  - `plugins/` — notification plugin system
- `frontend/src/` — Vue 3 app
  - `stores/` — Pinia stores (`auth`, `feeds`, `articles`, `ui`)
  - `views/` — page-level components (`FrontPage`, `Reader`, `ArticleView`, `Admin`, `Login`)
  - `i18n/locales/` — translation files for `it`, `en`, `fr`, `de`, `es`, `pt`

### Key architectural decisions

**Database**: SQLite (default, via `aiosqlite`) or PostgreSQL — switched only by the `DATABASE_URL` env var; no code changes needed. All DB access is async via SQLAlchemy 2.x.

**Authentication**: Session-based (not JWT). Sessions stored in DB (`sessions` table); session UUID is the `pp_session` cookie value (`HttpOnly`, `SameSite=Lax`). CSRF via double-submit cookie (`X-CSRF-Token` header required for POST/PUT/DELETE/PATCH).

**Scheduler**: APScheduler runs in-process with the FastAPI app. Feed polling jobs fire per-feed at `fetch_interval_min` intervals; digest generation is a cron job (default `0 7 * * *`).

**LLM abstraction**: `services/llm/base.py` defines an abstract `LLMProvider`. Concrete implementations in `ollama.py` and `claude.py`. Provider selection is driven by `LLMConfig` records in DB (`use_for` JSONB field distinguishes tagging vs. digest providers). API keys encrypted at rest with Fernet; key stored in `ENCRYPTION_KEY` env var.

**Full-text extraction**: Triggered on-demand when a user opens an article (`fulltext_status == 'pending'`). Backend responds immediately with the excerpt + `fulltext_loading: true`; frontend polls or uses WebSocket for the update. Uses `trafilatura`.

**Front Page scoring**: `score = recency × source_weight × category_affinity × read_penalty`. Recency decays with 12-hour half-life. Category affinity is derived from the user's reading history.

**Virtual Feeds → Atom**: `GET /api/v1/virtual-feeds/{id}/rss?token={rss_token}` returns Atom 1.0. Token is a static UUID stored on the `VirtualFeed` record.

### API conventions

- Base path: `/api/v1/`
- Pagination: `?page=1&size=20` → `{items, total, page, pages}`
- Errors: `{detail: string, code: string}`
- Category names are JSONB `{"it": "...", "en": "..."}` — always returned in the language the client requests via `Accept-Language`

### Environment variables

```env
DATABASE_URL=sqlite+aiosqlite:///./data/prima_pagina.db
SECRET_KEY=<64 bytes hex>
ENCRYPTION_KEY=<Fernet key>
SESSION_MAX_AGE_DAYS=30
SECURE_COOKIES=false          # true in production
ALLOWED_ORIGINS=http://localhost:5173
OLLAMA_ENDPOINT=http://ollama:11434
ANTHROPIC_API_KEY=
FEED_DEFAULT_INTERVAL_MIN=60
DIGEST_CRON=0 7 * * *
APP_ENV=development
LOG_LEVEL=INFO
```

### Development task plan

| Task | Title | Deps |
|------|-------|------|
| T01 | Monorepo setup, Docker, DB, config | — |
| T02 | Session-based auth | T01 |
| T03 | Feed management: global catalog + subscriptions | T02 |
| T04 | Feed fetcher: scheduler, polling, parsing, dedup | T03 |
| T05 | Article API: list, detail, user states, fulltext on-demand | T04 |
| T06 | Frontend scaffold: Vue 3, routing, auth UI, i18n | T02 |
| T07 | Frontend Reader: feed/article list, inline reading | T05, T06 |
| T08 | LLM service: provider abstraction, Ollama + Claude, tagging | T05 |
| T09 | Virtual Feed: CRUD, filters, RSS/Atom endpoint | T05, T08 |
| T10 | Digest: LLM generation, scheduling, storage | T08, T09 |
| T11 | Frontend Front Page: newspaper layout, digest | T07, T10 |
| T12 | Plugin system: base interface + Telegram | T10 |
| T13 | Admin panel: users, sessions, LLM config, plugins | T12 |
| T14 | Polish: full i18n, PWA offline, docs | T13 |

Detailed task specs are in `docs/tasks/T01.md` etc.