# Any2M3U

Turn WebDAV or local media libraries into IPTV-style M3U subscription feeds.

## Quick start

```bash
# 1. Build & start
docker compose up -d --build

# 2. Tail logs to grab the initial admin password
docker compose logs -f any2m3u | grep "initial admin password"
# Or read the file: cat data/INITIAL_PASSWORD.txt

# 3. Open http://localhost:8000 in your browser
#    - On first run you'll be prompted to set a new password.
#    - Or set ANY2M3U_ADMIN_PASSWORD in docker-compose.yml before first start.

# 4. Edit docker-compose.yml to mount your media:
#      - /your/media/path:/media:ro
#    Then: docker compose restart

# 5. (Recommended) Put host nginx in front for HTTPS.
#    See deploy/nginx.example.conf.
```

## How it works

- Each "Source" points at a WebDAV server or a local directory.
- Each "Rule" defines filters (extensions, keywords, paths) and a group
  title, and produces a M3U URL.
- Players (VLC, IINA, PotPlayer, Kodi...) subscribe to the M3U URL.
- When a file is requested, Any2M3U streams it through `/proxy` with full
  HTTP Range support — WebDAV sources are transparently reachable.
- Scheduled refreshes (cron per source) keep entries up to date.

## Development

```bash
# Backend
cd backend
uv sync --extra dev
uv run pytest -v

# Frontend
cd frontend
npm install
npm run dev   # Vite dev server with proxy to :8000
```

## Project layout

See `docs/superpowers/specs/2026-06-11-any2m3u-design.md` for the design,
and `docs/superpowers/plans/2026-06-11-any2m3u.md` for the implementation plan.
