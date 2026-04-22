# Deployment Guide

## Prerequisites

- Docker 24+ or Podman 4+ with Compose plugin
- At least 1 GB RAM (2 GB recommended if running Ollama)
- Ports 80 and 8000 available (or configure differently)

---

## Development Setup

```bash
git clone <repo-url>
cd prima-pagina
cp .env.example .env
# Edit .env — set SECRET_KEY, ENCRYPTION_KEY, ADMIN_PASSWORD

docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

- Frontend (Vite dev server with HMR): http://localhost:5173
- Backend (uvicorn --reload): http://localhost:8000
- API docs: http://localhost:8000/api/docs

---

## Production with SQLite (1–3 users)

Suitable for personal use. SQLite file is stored in a named Docker volume.

```bash
cp .env.example .env
# Edit .env:
#   SECURE_COOKIES=true
#   ALLOWED_ORIGINS=https://your-domain.com
#   APP_BASE_URL=https://your-domain.com
#   APP_ENV=production
#   ADMIN_PASSWORD=<strong password>

docker compose up -d
```

---

## Production with PostgreSQL

```bash
# Add to .env:
DATABASE_URL=postgresql+asyncpg://prima_pagina:${DB_PASSWORD}@db/prima_pagina
DB_PASSWORD=<strong db password>

docker compose --profile postgres up -d
```

---

## With Self-hosted Ollama

```bash
docker compose --profile ollama up -d
```

Add GPU support (NVIDIA):

```yaml
# docker-compose.override.yml
services:
  ollama:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

After startup, pull a model:

```bash
docker exec prima_pagina_ollama ollama pull llama3.2
```

Then configure the LLM provider in Admin → LLM → Add provider.

---

## Reverse Proxy

### Caddy (recommended — automatic HTTPS)

```caddyfile
news.example.com {
    reverse_proxy /api/* localhost:8000
    reverse_proxy localhost:80
}
```

### Nginx

```nginx
server {
    listen 443 ssl;
    server_name news.example.com;

    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        proxy_pass http://localhost:80;
        proxy_set_header Host $host;
    }
}
```

### Traefik (Docker labels)

```yaml
# Add to backend service in docker-compose.yml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.prima-api.rule=Host(`news.example.com`) && PathPrefix(`/api`)"
  - "traefik.http.services.prima-api.loadbalancer.server.port=8000"
```

---

## HTTPS with Let's Encrypt (Caddy)

Caddy handles certificate issuance automatically:

```bash
# Install Caddy
apt install caddy

# /etc/caddy/Caddyfile
news.example.com {
    reverse_proxy /api/* localhost:8000
    reverse_proxy localhost:80
}

systemctl reload caddy
```

---

## Backup and Restore

### SQLite

```bash
# Backup
docker run --rm \
  -v prima_pagina_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/prima_pagina_$(date +%Y%m%d_%H%M%S).tar.gz /data

# Restore
docker compose down
docker run --rm \
  -v prima_pagina_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/prima_pagina_YYYYMMDD_HHMMSS.tar.gz -C /
docker compose up -d
```

### PostgreSQL

```bash
# Backup
docker exec prima_pagina_db pg_dump -U prima_pagina prima_pagina \
  | gzip > backups/prima_pagina_$(date +%Y%m%d).sql.gz

# Restore
gunzip < backups/prima_pagina_YYYYMMDD.sql.gz \
  | docker exec -i prima_pagina_db psql -U prima_pagina prima_pagina
```

---

## Updating

```bash
docker compose pull
docker compose up -d
```

Migrations run automatically on startup via the backend's lifespan hook.

---

## Monitoring

Health check endpoint:

```bash
curl http://localhost:8000/api/v1/health
# {"status": "ok", "env": "production"}
```

Logs:

```bash
docker compose logs -f backend
docker compose logs -f frontend
```

Log level is controlled by the `LOG_LEVEL` environment variable.

---

## Podman

Podman Compose works with minor differences:

```bash
podman compose up -d

# Named volumes are managed by podman:
podman volume ls
podman volume inspect prima_pagina_data
```

If using rootless Podman, ports below 1024 require `sysctl net.ipv4.ip_unprivileged_port_start=80`.
