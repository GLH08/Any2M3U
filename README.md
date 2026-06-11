# Any2M3U

Turn WebDAV or local media libraries into IPTV-style M3U subscription feeds.

## Quick start

```bash
# 1. Build
docker compose build

# 2. Configure media mount (edit docker-compose.yml: /path/to/your/media)
# 3. Start
docker compose up -d

# 4. Visit http://localhost:8000 — set admin password on first run.
# 5. (Recommended) Put host nginx in front for HTTPS — see deploy/nginx.example.conf.
```

See `docs/superpowers/specs/2026-06-11-any2m3u-design.md` for the design.
