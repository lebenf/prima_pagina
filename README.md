# Prima Pagina

Self-hosted RSS aggregation PWA with LLM-based article tagging and digest generation.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (package manager)
- Node.js 20+ (frontend, from T06 onwards)
- Docker / Podman with Compose (optional)

## Quick start (backend)

```bash
cd backend

# Install dependencies
uv sync --group dev

# Copy and edit environment variables
cp ../.env.example .env
# Edit .env: set SECRET_KEY and ENCRYPTION_KEY (see generation commands inside the file)

# Create data directory and run migrations
mkdir -p data
python -m alembic upgrade head

# Start development server
uvicorn app.main:app --reload --port 8000
```

Health check: `curl http://localhost:8000/api/v1/health`

## Run tests

```bash
cd backend
SECRET_KEY=test ENCRYPTION_KEY=<any-base64> python -m pytest tests/ -v
```

## Docker (full stack)

```bash
# Copy and configure environment
cp .env.example .env

# Development (hot reload)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# Production
docker compose up
```

## Development task plan

See `CLAUDE.md` for architecture details and `docs/tasks/` for individual task specs.

| Task | Status |
|------|--------|
| T01 — Monorepo setup, Docker, DB, config | ✅ |
| T02 — Session-based auth | ⬜ |
| T03 — Feed management | ⬜ |
| T04 — Feed fetcher & scheduler | ⬜ |
| T05 — Article API | ⬜ |
| T06 — Frontend scaffold | ⬜ |
| T07 — Frontend Reader | ⬜ |
| T08 — LLM service | ⬜ |
| T09 — Virtual Feeds | ⬜ |
| T10 — Digest | ⬜ |
| T11 — Frontend Front Page | ⬜ |
| T12 — Plugin system | ⬜ |
| T13 — Admin panel | ⬜ |
| T14 — Polish & PWA | ⬜ |
