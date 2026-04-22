# Changelog

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
