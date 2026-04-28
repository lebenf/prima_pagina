# Changelog

## [0.2.0] — 2026-04-28

### Features

- **T15 — Article votes**: Thumbs-up/thumbs-down per article; updates per-user topic preferences (`user_topic_preferences`); vote weight normalised to `[0.1, 2.0]` for front-page ranking; optimistic UI with rollback on error; `VoteButtons` component reused in Reader toolbar, HeroArticle, SecondRowArticle, CategoryColumn, and ArticleDrawer
- **T16 — Intelligent full-text extraction**: Three modes per feed (`trafilatura` / `script` / `auto`); LLM analyses sample HTML and produces CSS selectors for content/title/author/date; selectors validated before saving; exponential moving average `success_rate`; layout change detection via body-structure hash; `consecutive_failures ≥ 5` auto-disables script and triggers background regeneration; admin API: `GET /feeds/{id}/extraction-script`, `POST /feeds/{id}/extraction-script/regenerate`
- **T17 — Related articles**: Computed after tagging; shared across users (stored in `article_llm_data`); LLM selects top 5 from candidates with overlapping tags within a 72-hour window; silent fallback when no LLM configured; "Leggi anche" section in Reader
- **T18 — Full-text search**: `GET /api/v1/search?q=` with highlighted snippets (`<mark>`); SQLite LIKE / PostgreSQL `tsvector` + `ts_rank`; filters: feed, category, date range; `Ctrl+K` / `⌘K` global shortcut opens SearchModal; arrow-key navigation; debounce 300 ms
- **T19 — ArticleDrawer and deep linking**: Slide-from-right drawer in Front Page; URL as single source of truth (`?article={id}`); shareable, browser-navigable; fulltext loaded on open with polling; body scroll lock; related-article navigation inline; "Open in Reader" button; `?article=` query param also handled in Reader view (fetches article directly and selects it)
- **T20 — Invitations, password confirmation, digest errors, extraction script UI**:
  - Admin generates single-use invite links (`/join?token=…`); links optionally bound to an email; configurable expiry (default 7 days); revocable before use; full list with status (active / expired / used)
  - Public registration page: validates token, pre-fills bound email (readonly), auto-login after successful registration
  - Password confirmation field added to admin user creation and public registration
  - Failed digests persisted with `status = "failed"` and `generation_error`; front page shows red banner with error message and Retry button; DigestModal shows error detail and hint
  - Admin feed table: Fulltext column with colour-coded script badge (green ≥ 80 %, orange 50–80 %, red < 50 % or inactive); click opens ExtractionScriptModal with CSS selectors table, stats grid, and Regenerate button

### Improvements

- LLM config timeout field (30–3600 s) exposed in admin UI and stored in DB (migration 0007)
- `FeedResponse` includes `extraction_script` (batch-loaded, no N+1)
- `DigestResponse` includes `status` and `generation_error` fields
- All 6 i18n locales updated with new keys (auth registration, invitations, digest errors, copy-link)

### Bug fixes

- `from __future__ import annotations` placement in `schemas/feed.py` caused SyntaxError at import time
- `FeedResponse.model_validate(feed)` triggered SQLAlchemy async lazy-load outside greenlet; fixed by building response dict from column attributes only
- `ArticleDrawer` scroll-lock watcher missing `{ immediate: true }` — body overflow not set on initial open
- Teleport stub missing from ArticleDrawer tests — `wrapper.find()` failed to locate teleported content
- `POST /auth/register/{token}` returned 422 for users with no subscribed feeds (DigestError propagated too early)

## [0.1.0] — 2026-04-22

Initial release.

### Features

- **T01 — Monorepo setup**: Docker Compose stack (backend + frontend + optional PostgreSQL + optional Ollama), SQLite default database, async SQLAlchemy, Alembic migrations, pydantic-settings configuration
- **T02 — Session-based auth**: Session table with UUID tokens, HttpOnly cookies, CSRF double-submit, rate-limited login, initial admin auto-creation
- **T03 — Feed management**: Global feed catalog, per-user subscriptions with `notify_on_new` flag, category system with multilingual names, auto-discovery of feed metadata
- **T04 — Feed fetcher**: APScheduler per-feed polling, RSS/Atom parsing, HTML sanitization, deduplication by GUID, backoff on errors, favicon download
- **T05 — Article API**: List/detail endpoints with pagination, user states (read/starred), on-demand full-text extraction via trafilatura, WebSocket push for fulltext ready
- **T06 — Frontend scaffold**: Vue 3 + Vite + Pinia + vue-router + vue-i18n, AppLayout with sidebar/header/navigation, LoginView, SettingsView stub, 6-language i18n (IT/EN/FR/DE/ES/PT)
- **T07 — Frontend Reader**: Feed list with subscribe/unsubscribe, article list with infinite scroll, inline ArticleReader with full-text loading, keyboard navigation (j/k/r/s/o), RelativeTime component
- **T08 — LLM service**: Abstract LLMProvider with Ollama and Claude implementations, background tagging worker, LLM config CRUD with encrypted API keys, admin health-check endpoint
- **T09 — Virtual Feeds**: Filter by category/tags/source, Atom 1.0 RSS export with token auth, CRUD API
- **T10 — Digest**: LLM-generated press digest with parallel fulltext prefetch, scheduled daily generation (cron), on-demand API, HTML sanitization, Telegram notification dispatch
- **T11 — Frontend Front Page**: Newspaper layout (hero + second row + category columns), digest banner, DigestModal with server-rendered HTML, front-page scoring (recency × source weight × category affinity × read penalty)
- **T12 — Plugin system**: Abstract NotificationPlugin interface, Telegram bot plugin (sendMessage, inline keyboard, HTML parse mode, 4096-char truncation), PluginManager with asyncio.gather dispatch, per-user or global scope
- **T13 — Admin panel**: Tab-based admin UI (users/sessions/feeds/categories/LLM/plugins), CRUD for all entities, inline health check for LLM providers, test connection for plugins, dynamic schema-driven plugin config form
- **T14 — Polish**: Complete 6-language i18n (170 keys per locale), PWA offline mode (NetworkFirst articles, service worker), security headers middleware (CSP/HSTS/X-Frame-Options), SSRF validation for feed URLs, code splitting (vue-vendor/i18n/axios chunks), comprehensive documentation (README, deployment, configuration, user guide)
