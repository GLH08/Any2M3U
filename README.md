# Any2M3U

Turn WebDAV or local media libraries into IPTV-style M3U subscription feeds.

```
┌─────────────────┐  HTTP  ┌──────────────┐  PROPFIND/GET  ┌──────────┐
│  VLC / Kodi /   │ <───── │   Any2M3U    │ ─────────────> │  WebDAV  │
│  PotPlayer /    │        │  (FastAPI)   │                │  server  │
│  IINA / …       │ ──────>│              │ <───────────── │          │
└─────────────────┘ Range  └──────┬───────┘  Range 206     └──────────┘
                                   │
                                   │ scandir
                                   ▼
                            ┌──────────────┐
                            │  Local mount │
                            │  /media:ro   │
                            └──────────────┘
```

## Quick start

```bash
# 1. Build & start
docker compose up -d --build

# 2. Grab the initial admin password
docker compose logs -f any2m3u 2>&1 | grep "initial admin password"
# Or:  cat data/INITIAL_PASSWORD.txt

# 3. Open http://localhost:8000
#    - On first run the SPA will detect no logged-in user → /login
#    - Or set ANY2M3U_ADMIN_PASSWORD in docker-compose.yml before first start

# 4. Edit docker-compose.yml to mount your media, then:
docker compose restart
#      volumes:
#        - /your/media/path:/media:ro

# 5. (Recommended) Put host nginx in front for HTTPS.
#    See deploy/nginx.example.conf.
```

## Concepts

| Term | Meaning |
|---|---|
| **Source** | A media library to read from. WebDAV (HTTP Basic auth) or a local directory mounted into the container. |
| **Rule** | Filters + template + group title for a single M3U feed. One source → many rules → many M3U URLs. |
| **Pull token** | Long-lived secret used in the M3U URL and `/proxy` request. Independent from admin login. |
| **M3U URL** | Public endpoint like `https://host/m3u/rule/3?token=…`. Hand to any player. |
| **Proxy URL** | `https://host/proxy?token=…&id=…` — emitted inside the M3U; player pulls this. Range-aware. |

## API

### Management (cookie session)

| Method | Path | Purpose |
|---|---|---|
| GET/POST | `/api/auth/{login,logout,me,password}` | session lifecycle |
| GET/POST/PATCH/DELETE | `/api/sources[/{id}]` | source CRUD |
| POST | `/api/sources/{id}/test` | test connection (returns `{ok, error?, latency_ms}`) |
| POST | `/api/sources/{id}/scan` | trigger scan (background) |
| GET  | `/api/sources/{id}/scan` | scan status + progress |
| GET/POST | `/api/sources/{id}/rules[/{rid}]` | rule CRUD |
| PATCH/DELETE | `/api/rules/{rid}` | rule update / delete |
| GET/POST/DELETE | `/api/tokens[/{id}]` | pull-token CRUD |
| GET  | `/api/scan/status` | aggregate counts |
| GET  | `/api/health` | healthcheck |

### Public (token in `?token=` or `Authorization: Bearer`)

| Method | Path | Purpose |
|---|---|---|
| GET | `/m3u/rule/{rid}?token=…` | render M3U for one rule |
| GET | `/m3u/source/{sid}?token=…&group=Movies` | when `group_by_dir=1`, per-subdir M3U |
| GET | `/proxy?token=…&id=<entry_id>` | stream a file, Range-aware |

## M3U template placeholders

Default template:
```
#EXTINF:-1 group-title="<group>",<title>
<base>/proxy?token=<t>&id=<eid>
```

| Placeholder | Expands to |
|---|---|
| `<base>` | `ANY2M3U_BASE_URL` (e.g. `https://any2m3u.example.com`) |
| `<sid>` | numeric source id |
| `<group>` | rule's `group_title` (XML-escaped) |
| `<title>` | filename without extension (XML-escaped) |
| `<eid>` | stable 32-char sha1 of `source_id:path` |
| `<t>` | the pull token in use |
| `<logo>` | `<logo_dir>/<stem>.jpg`. Only useful if `logo_dir` is a **full URL prefix** (e.g. `https://cdn/posters`) — this service does **not** host logo images. If `logo_dir` is empty the entire `tvg-logo="…"` attribute is stripped. To use logos, add `tvg-logo="<logo>"` to a custom template and set `logo_dir` to your image host's URL prefix. |

## Cron refresh

Each source has an optional `refresh_cron` (5-field POSIX cron). When set and
the source is enabled, APScheduler triggers a scan on schedule. Format:

```
minute hour day-of-month month day-of-week
0 */6 * * *      # every 6 hours
*/30 * * * *     # every 30 minutes
```

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

```
any2m3u/
├── backend/                  # FastAPI app (uv-managed)
│   ├── any2m3u/
│   │   ├── main.py           # app factory + lifespan
│   │   ├── config.py         # pydantic-settings (env)
│   │   ├── db.py             # SQLAlchemy async engine
│   │   ├── models.py         # User, Source, Rule, PullToken, Session
│   │   ├── schemas.py        # pydantic request/response
│   │   ├── security.py       # argon2 + token gen
│   │   ├── deps.py           # FastAPI dependencies
│   │   ├── migrations/       # raw SQL migrations
│   │   ├── scanner/          # LocalAdapter, WebDAVAdapter, engine
│   │   ├── m3u/              # filter + render
│   │   ├── proxy/            # Range parser
│   │   ├── api/              # routers (auth, sources, rules, tokens, public)
│   │   └── scheduler.py      # APScheduler cron registration
│   └── tests/
├── frontend/                 # Vue 3 + Vite + Element Plus
│   └── src/
│       ├── views/            # Dashboard, Sources, SourceDetail, Rules, Tokens, Settings, Login
│       ├── components/       # SourceForm, RuleForm, ScanProgress
│       ├── stores/           # pinia auth store
│       └── api.ts            # axios instance
├── deploy/
│   └── nginx.example.conf    # host nginx template
├── docker-compose.yml
├── Dockerfile                # multi-stage: build Vue → run Python
└── docs/
    └── superpowers/
        ├── specs/2026-06-11-any2m3u-design.md
        └── plans/2026-06-11-any2m3u.md
```

## Troubleshooting

**"WebDAV auth failed" in scan log**
- Check username/password.
- If your server uses Digest auth, this build only supports Basic.

**Players can't seek the video**
- Host nginx must have `proxy_buffering off;` (see `deploy/nginx.example.conf`).
- Verify the player issued a `Range:` header (curl with `-H "Range: bytes=0-1"` to test).

**WebDAV PROPFIND returns 207 but no files**
- The server may not support `Depth: 1` PROPFIND; only some servers do.
- Some servers require `Authorization` only on certain verbs; this build sends it for all.

**Initial password file in `/data` is empty after first run**
- You pre-set `ANY2M3U_ADMIN_PASSWORD` env var; the file is only created when the env var is empty.

**Windows symlink-related scan errors**
- Local adapter skips symlinks (security); this is by design.

## Specs

- Design: `docs/superpowers/specs/2026-06-11-any2m3u-design.md`
- Plan:   `docs/superpowers/plans/2026-06-11-any2m3u.md`

## License

MIT — see [LICENSE](LICENSE).
