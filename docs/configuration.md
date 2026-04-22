# Configuration Reference

All configuration is via environment variables. Copy `.env.example` to `.env` and edit.

## Required

| Variable | Type | Description |
|----------|------|-------------|
| `SECRET_KEY` | string | Secret key for cryptographic signatures. Generate: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ENCRYPTION_KEY` | string | Fernet key for encrypting API keys at rest. Generate: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |

## Database

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/prima_pagina.db` | Database connection URL. Use `postgresql+asyncpg://user:pass@host/db` for PostgreSQL. |

## Authentication & Security

| Variable | Default | Description |
|----------|---------|-------------|
| `SESSION_MAX_AGE_DAYS` | `30` | Session lifetime in days |
| `SECURE_COOKIES` | `false` | Set `true` in production with HTTPS. Enables `Secure` cookie flag and HSTS header. |
| `ALLOWED_ORIGINS` | `http://localhost:5173` | Comma-separated CORS origins. In production: `https://your-domain.com` |

## Initial Admin

These only take effect on first startup if no admin user exists.

| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_USERNAME` | `admin` | Initial admin username |
| `ADMIN_EMAIL` | _(empty)_ | Initial admin email |
| `ADMIN_PASSWORD` | _(empty)_ | Initial admin password. **Required** for first login. |

## Feed Polling

| Variable | Default | Description |
|----------|---------|-------------|
| `FEED_DEFAULT_INTERVAL_MIN` | `60` | Default polling interval per feed (minutes) |

## Digest Generation

| Variable | Default | Description |
|----------|---------|-------------|
| `DIGEST_CRON` | `0 7 * * *` | Cron expression for automatic daily digest (default: 07:00) |

## LLM Providers

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_ENDPOINT` | `http://localhost:11434` | Ollama server URL |
| `ANTHROPIC_API_KEY` | _(empty)_ | API key for Anthropic Claude |

## Application

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_BASE_URL` | `http://localhost:5173` | Frontend base URL (used in notification links) |
| `APP_ENV` | `development` | `development` or `production`. Affects CSP headers and logging. |
| `LOG_LEVEL` | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

## Example .env for Production

```env
SECRET_KEY=<64-char hex>
ENCRYPTION_KEY=<Fernet key>
DATABASE_URL=sqlite+aiosqlite:///./data/prima_pagina.db
SESSION_MAX_AGE_DAYS=30
SECURE_COOKIES=true
ALLOWED_ORIGINS=https://news.example.com
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<strong password>
FEED_DEFAULT_INTERVAL_MIN=60
DIGEST_CRON=0 7 * * *
APP_BASE_URL=https://news.example.com
APP_ENV=production
LOG_LEVEL=INFO
```
