# Any2M3U — Design Spec

**Date:** 2026-06-11
**Status:** Draft (pending user approval)
**Author:** Brainstorming session

## 1. Purpose

Any2M3U turns media libraries stored on WebDAV servers or local directories
into IPTV-style M3U subscription feeds. A user adds one or more "sources",
defines "rules" (filters + grouping), and gets back one or more M3U URLs to
paste into players such as IINA, PotPlayer, VLC, or Kodi. When the
underlying media changes, the user re-runs a scan (or waits for a scheduled
refresh) and the M3U updates.

A small web UI lets the user manage sources, rules, pull tokens, and trigger
scans. The whole app is designed to run as a single Docker container on a
home server, fronted by a host-installed nginx that handles TLS termination.

## 2. Scope & Non-Goals

**In scope**
- Sources: WebDAV (HTTP Basic auth) and local directories mounted into the
  container.
- Range-aware HTTP reverse proxy so WebDAV content is reachable from the
  public internet.
- Filter rules (extension/path/keyword) and per-rule M3U templates.
- Group-by-directory as an additional way to expose multiple M3U URLs.
- One administrator account; long-lived pull tokens for M3U/proxy access.
- Vue 3 SPA for management; FastAPI serves the static build.
- Single-container Docker Compose deployment; example nginx config for the
  host.

**Out of scope**
- Multiple user accounts, role-based access control, audit logging.
- EPG / XMLTV generation.
- Transcoding (ffmpeg is present in the image as a stub, unused in v1).
- High-availability, multi-replica, CDN-friendly caching.
- Authentication methods other than password (no OAuth, no LDAP, no SSO).
- Non-M3U playlist formats.

## 3. User Stories

1. *Add a WebDAV source.* I paste a URL, username, password, and an optional
   root path, click "Test connection", and the UI confirms it works.
2. *Add a local source.* I mount a host directory into the container, name
   it, and pick the in-container path.
3. *Scan a source.* I click "Scan now" and a progress indicator shows the
   scan running; when it finishes, the UI shows entry count and total size.
4. *Define a rule.* I pick a source, choose extensions and exclusions, and
   give the rule a name; the UI shows the M3U URL I'd hand to a player.
5. *Generate M3U.* I paste the M3U URL into VLC; it lists every matching
   file from every rule's source, with logo and group-title.
6. *Stream through the proxy.* I click an entry in VLC; the player pulls
   the file from the Any2M3U proxy, which forwards it (Range-aware) from
   WebDAV or the local filesystem.
7. *Issue a pull token.* I create a token called "Living Room TV", copy
   the M3U URL with the token in the query string, and put it on the TV.
   I can revoke the token later.
8. *Scheduled refresh.* I set a cron expression on a source; the M3U
   updates automatically.

## 4. Architecture

### 4.1 Topology

```
   ┌──────────────────┐
   │ Host nginx       │   TLS termination
   │ (any2m3u.conf)   │
   └────────┬─────────┘
            │ http://127.0.0.1:8000
   ┌────────▼──────────────────────────────────────────┐
   │ Docker container: any2m3u                         │
   │   ┌────────────────────────────────────────┐     │
   │   │ FastAPI (uvicorn, single worker)        │     │
   │   │   /api/*        management API          │     │
   │   │   /assets/*     Vue 3 SPA static        │     │
   │   │   /m3u/*        public M3U (token)      │     │
   │   │   /proxy        public stream (token)   │     │
   │   └────────────────────────────────────────┘     │
   │   ┌────────────────────────────────────────┐     │
   │   │ APScheduler: per-source cron refresh   │     │
   │   └────────────────────────────────────────┘     │
   │   ┌────────────────────────────────────────┐     │
   │   │ SQLite at /data/app.db                 │     │
   │   │ Scan cache at /data/scan/<id>.jsonl    │     │
   │   └────────────────────────────────────────┘     │
   └───────────────────────────────────────────────────┘
            │ HTTPS / PROPFIND / GET
   ┌────────▼──────────┐
   │ Upstream WebDAV   │  (Nextcloud, Alist, etc.)
   └───────────────────┘
```

### 4.2 Directory layout

```
any2m3u/
├── docker-compose.yml
├── Dockerfile
├── README.md
├── deploy/
│   └── nginx.example.conf
├── docs/
│   └── superpowers/specs/2026-06-11-any2m3u-design.md
├── backend/
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── any2m3u/                 # main package
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app factory
│   │   ├── config.py            # env + path config
│   │   ├── db.py                # engine, session, init
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── schemas.py           # pydantic request/response
│   │   ├── security.py          # password hashing, sessions, tokens
│   │   ├── deps.py              # FastAPI dependencies
│   │   ├── migrations/
│   │   │   ├── 0001_init.sql
│   │   │   └── _runner.py
│   │   ├── scanner/
│   │   │   ├── base.py          # SourceAdapter, FileEntry
│   │   │   ├── webdav.py
│   │   │   ├── local.py
│   │   │   └── engine.py        # scan orchestration
│   │   ├── m3u/
│   │   │   ├── renderer.py
│   │   │   └── filters.py
│   │   ├── proxy/
│   │   │   └── stream.py
│   │   ├── api/
│   │   │   ├── auth.py
│   │   │   ├── sources.py
│   │   │   ├── rules.py
│   │   │   ├── tokens.py
│   │   │   ├── scan.py
│   │   │   └── public.py
│   │   └── scheduler.py
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_filters.py
│   │   ├── test_m3u.py
│   │   ├── test_models.py
│   │   ├── test_local_adapter.py
│   │   ├── test_webdav_adapter.py
│   │   ├── test_proxy.py
│   │   ├── test_auth.py
│   │   └── test_e2e.py
│   └── data/                    # mounted as /data in container
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   ├── src/
│   │   ├── main.ts
│   │   ├── App.vue
│   │   ├── router.ts
│   │   ├── api.ts
│   │   ├── stores/
│   │   │   ├── auth.ts
│   │   │   └── ui.ts
│   │   ├── components/
│   │   │   ├── SourceForm.vue
│   │   │   ├── RuleForm.vue
│   │   │   ├── TokenCard.vue
│   │   │   └── ScanProgress.vue
│   │   └── views/
│   │       ├── Login.vue
│   │       ├── Setup.vue
│   │       ├── Dashboard.vue
│   │       ├── Sources.vue
│   │       ├── SourceDetail.vue
│   │       ├── Rules.vue
│   │       ├── Tokens.vue
│   │       └── Settings.vue
│   └── public/
```

### 4.3 Data volumes

| Container path | Host path (default) | Purpose |
|---|---|---|
| `/data` | `./data` | SQLite + `/data/scan/*.jsonl` + `INITIAL_PASSWORD.txt` |
| `/media` | `/path/to/your/media:ro` | Local media sources (read-only) |

## 5. Data Model (SQLite)

```sql
-- users: single row in v1, table left in place for future multi-user
CREATE TABLE users (
    id              INTEGER PRIMARY KEY,
    username        TEXT UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    last_login_at   TEXT
);

-- sources: one media source (WebDAV or local)
CREATE TABLE sources (
    id                INTEGER PRIMARY KEY,
    name              TEXT NOT NULL,
    type              TEXT NOT NULL CHECK(type IN ('webdav','local')),
    config_json       TEXT NOT NULL,            -- type-specific config
    group_by_dir      INTEGER NOT NULL DEFAULT 0,
    refresh_cron      TEXT,                     -- NULL = manual only
    enabled           INTEGER NOT NULL DEFAULT 1,
    last_scan_at      TEXT,
    last_scan_status  TEXT,                     -- success|failed|running
    last_error        TEXT,
    created_at        TEXT NOT NULL
);

-- scan_cache: latest successful scan for each source
CREATE TABLE scan_cache (
    source_id           INTEGER PRIMARY KEY REFERENCES sources(id) ON DELETE CASCADE,
    scanned_at          TEXT NOT NULL,
    entry_count         INTEGER NOT NULL,
    total_bytes         INTEGER NOT NULL,
    entries_jsonl_path  TEXT NOT NULL
);

-- rules: filter + template, one source to many rules
CREATE TABLE rules (
    id                INTEGER PRIMARY KEY,
    source_id         INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    name              TEXT NOT NULL,
    include_exts      TEXT,                     -- csv, NULL/'' = all
    exclude_keywords  TEXT,                     -- csv, case-insensitive
    include_paths     TEXT,                     -- csv path prefixes
    group_title       TEXT NOT NULL DEFAULT '',
    tpl               TEXT NOT NULL,
    logo_dir          TEXT NOT NULL DEFAULT '',
    enabled           INTEGER NOT NULL DEFAULT 1,
    created_at        TEXT NOT NULL
);

-- pull_tokens: long-lived tokens for /m3u and /proxy
CREATE TABLE pull_tokens (
    id            INTEGER PRIMARY KEY,
    name          TEXT NOT NULL,
    token         TEXT UNIQUE NOT NULL,         -- 32+ bytes url-safe
    created_at    TEXT NOT NULL,
    last_used_at  TEXT,
    expires_at    TEXT,                         -- NULL = never
    revoked       INTEGER NOT NULL DEFAULT 0
);

-- sessions: opaque cookie store for management UI
CREATE TABLE sessions (
    id            TEXT PRIMARY KEY,             -- 32-byte random
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at    TEXT NOT NULL,
    expires_at    TEXT NOT NULL,
    ip            TEXT
);
```

### 5.1 Source config payloads

**WebDAV**
```json
{
  "url": "https://dav.example.com",
  "username": "alice",
  "password": "secret",
  "root_path": "/Media",
  "verify_tls": true
}
```

**Local**
```json
{ "path": "/media" }
```

### 5.2 M3U template

The default template (per-rule, configurable):

```
#EXTINF:-1 tvg-logo="<base_url>/logo/<source_id>/<logo_subpath>.jpg" group-title="<group_title>",<title>
<base_url>/proxy?token=<token>&id=<entry_id>
```

- `<title>` = the file's relative path inside the source, extension stripped.
- `<logo_subpath>` = filename without extension (we look for `.jpg`, `.png`
  in the same directory; first match wins).
- `<entry_id>` = stable hash of `source_id:path`.

## 6. API Surface

### 6.1 Management API — prefix `/api`, session cookie required

| Method | Path | Body / Returns |
|---|---|---|
| GET  | `/api/health` | `{ok: true}` (also used by docker healthcheck; no auth) |
| POST | `/api/auth/login` | `{username, password}` → Set-Cookie |
| POST | `/api/auth/logout` | 204 |
| GET  | `/api/auth/me` | `{username, last_login_at}` |
| POST | `/api/auth/password` | `{old, new}` |
| GET  | `/api/sources` | `[{id, name, type, ...}]` |
| POST | `/api/sources` | create |
| GET  | `/api/sources/{id}` | detail |
| PATCH | `/api/sources/{id}` | update |
| DELETE | `/api/sources/{id}` | delete (cascade to rules + scan_cache) |
| POST | `/api/sources/{id}/test` | `{ok, error?, latency_ms}` |
| POST | `/api/sources/{id}/scan` | `{job_id}` (async) |
| GET  | `/api/sources/{id}/scan` | `{status, progress, last_error, scanned_at, entry_count}` |
| GET  | `/api/sources/{id}/rules` | list rules for source |
| POST | `/api/sources/{id}/rules` | create |
| PATCH | `/api/rules/{id}` | update |
| DELETE | `/api/rules/{id}` | delete |
| GET  | `/api/sources/{id}/m3u` | preview the M3U body (no token, used in UI) |
| GET  | `/api/tokens` | list (token value redacted) |
| POST | `/api/tokens` | `{name, expires_at?}` → returns `token` **once** |
| DELETE | `/api/tokens/{id}` | revoke |
| GET  | `/api/scan/status` | aggregate `{sources_total, sources_scanning, last_full_pass_at}` |

### 6.2 Public endpoints — token required (query `?token=` or `Authorization: Bearer`)

| Method | Path | Notes |
|---|---|---|
| GET | `/m3u/rule/{rule_id}?token=…` | Render M3U for one rule |
| GET | `/m3u/source/{source_id}?token=…&group=<dir>` | When `group_by_dir=1`; `group` is the subdirectory name (required; returns 400 if missing) |
| GET | `/proxy?token=…&id=<entry_id>` | Stream a single file, Range-aware |

### 6.3 Auth model

- **Sessions**: opaque 32-byte cookie (`any2m3u_sid`), HttpOnly, SameSite=Lax,
  Secure (when behind HTTPS). Server-side `sessions` table; default TTL
  30 days, sliding.
- **Pull tokens**: 32 random bytes, urlsafe base64. Stored as-is in DB
  (high-entropy = no need to hash). Bearer accepted on `/m3u/*` and
  `/proxy`. Revocation is a flag check.
- **CSRF**: management API uses SameSite=Lax cookies + `X-Requested-With`
  header (the SPA always sends it). No double-submit tokens.

## 7. Scanner

### 7.1 SourceAdapter protocol

```python
class FileEntry(TypedDict):
    path: str          # relative to source root, posix separator
    size: int
    mtime: float       # unix epoch
    etag: str | None   # WebDAV only; None for local

class SourceAdapter(Protocol):
    def list(self, path: str = "/") -> AsyncIterator[FileEntry]: ...
    def open_range(self, path: str, start: int, end: int | None) -> AsyncIterator[bytes]: ...
    def open_full(self, path: str) -> AsyncIterator[bytes]: ...
    def stat(self, path: str) -> FileEntry: ...
    async def ping(self) -> None: ...
```

### 7.2 WebDAV adapter (`scanner/webdav.py`)

- Single shared `httpx.AsyncClient` per process. Defaults
  `max_keepalive_connections=10`, `max_connections=20`, `timeout=30s`.
- **Listing**: `PROPFIND Depth: 1`. Parse `<response>` entries; recurse into
  directories. URL-encode path segments. Skip non-`{DAV:}collection` items.
- **Range stream**: forward `Range` header to upstream; pass through 206,
  `Content-Range`, `Content-Length`, `Accept-Ranges: bytes`. Stream
  via `client.stream`.
- **Auth failures (401/403)**: adapter raises `UpstreamAuthError`; scan is
  marked failed, old cache preserved.
- **TLS**: when `verify_tls=False`, log a single warning and skip
  verification.

### 7.3 Local adapter (`scanner/local.py`)

- Recursion via `asyncio.to_thread(os.scandir)`.
- Default skip: dotfiles, symlinks. Configurable per source if needed
  (out of v1 scope: not exposed in UI).
- Range: `aiofiles.open(path, 'rb')` + `seek` + chunked read (64 KiB).
- **Path safety**: `os.path.realpath` then assert resolved path is under
  the configured root; reject traversal.

### 7.4 Scan engine (`scanner/engine.py`)

```
async def scan(source_id):
    source = load(source_id)
    mark_running(source_id)
    try:
        adapter = build(source.type, source.config)
        tmp = /data/scan/<id>.jsonl.tmp
        count, total = 0, 0
        async with aiofiles.open(tmp, 'w') as f:
            async for entry in adapter.list():
                await f.write(json.dumps(entry) + '\n')
                count += 1; total += entry['size']
        os.replace(tmp, /data/scan/<id>.jsonl)
        upsert_scan_cache(source_id, count, total)
        mark_success(source_id)
    except Exception as e:
        mark_failed(source_id, repr(e))
        # keep old cache in place
```

- Concurrency: `asyncio.Semaphore(1)` for v1. Sufficient for personal use.
- Progress: a 60-second-TTL in-memory counter updated every 1000 entries.
  Returned by `GET /api/sources/{id}/scan`.
- Triggers:
  - Manual: `POST /api/sources/{id}/scan`.
  - Scheduled: APScheduler with one cron per source, in-process. Survives
    only as long as the container; container restart = rescheduling from
    DB on startup.
- Crash recovery: any `*.jsonl.tmp` left behind at startup is removed.

## 8. M3U rendering

- For each rule, open `/data/scan/<source_id>.jsonl` and stream-parse.
- Apply filters (extension allow-list, keyword block-list, path prefix
  allow-list) in order.
- For each surviving entry, build an `#EXTINF` line from the template,
  then the proxy URL.
- If no logo image (`.jpg`/`.png`) exists next to the file, omit the
  `tvg-logo` attribute entirely (do not emit an empty value).
- `Content-Type: text/plain; charset=utf-8`. No `Content-Disposition`; the
  player just reads the body.
- Special values in `tvg-logo` and `group-title` are XML-escaped (any
  `&`, `<`, `>`, `"`).

## 9. Proxy

- Parse `Range: bytes=START-END?` into `(start, end)`. Missing/empty end
  means "to EOF".
- Look up `entry_id` → `(source, path, size)` from `scan_cache` + index
  file (a small in-memory `dict[str, FileEntry]` rebuilt on every
  successful scan; reads from the new `jsonl` after `os.replace`).
- If `Range` is set: forward to adapter as `open_range`.
- Otherwise: `open_full`, return 200 with `Content-Length`.
- Headers always set: `Accept-Ranges: bytes`, `Content-Type` guessed from
  extension (fallback `application/octet-stream`).
- Client disconnect: the upstream `stream()` iterator is cancelled (its
  context manager closes the HTTP response).
- If the upstream declines Range (returns 200 when we asked for 206):
  downgrade to a 200 response, drop `Accept-Ranges`, log a single
  warning for that source (it is silently retried with Range next time).

## 10. Error handling summary

| Scenario | Behavior |
|---|---|
| WebDAV 401/403 | Source `last_error="auth_failed"`, scan failed, UI highlights |
| WebDAV 5xx / timeout | Scan failed; old cache preserved |
| Proxy 404 | 404 + `{error: "not_found"}` |
| Proxy upstream 401/403 | 502 + `{error: "upstream_auth"}` |
| Proxy upstream 200 to Range request | Return 200, drop `Accept-Ranges`, log warn |
| Invalid/expired/revoked token | 401 + `WWW-Authenticate: Bearer realm="any2m3u"` |
| SQLite contention | `WAL` mode + `busy_timeout=5000` |
| Disk full | `scan()` fast-fails with clear message before writing |
| Container crash mid-scan | `*.jsonl.tmp` deleted on startup |
| Path traversal in local source | Adapter raises; scan failed |

## 11. Configuration & startup

Environment variables (all prefixed `ANY2M3U_`):

| Variable | Default | Notes |
|---|---|---|
| `ANY2M3U_DATA` | `/data` | DB + scan cache dir |
| `ANY2M3U_WEB` | (package default) | SPA static dir |
| `ANY2M3U_BASE_URL` | `http://localhost:8000` | Used to build M3U/proxy URLs |
| `ANY2M3U_ADMIN_PASSWORD` | unset | If set on first run, used as initial password |
| `ANY2M3U_LOG_LEVEL` | `INFO` | Standard `logging` levels |
| `ANY2M3U_BIND` | `0.0.0.0:8000` | uvicorn bind |

**First-run sequence**
1. If `/data/app.db` missing, run migrations and create `app.db`.
2. If `users` table empty:
   - If `ANY2M3U_ADMIN_PASSWORD` is set, hash and insert.
   - Else: generate a 24-char random password, write to
     `/data/INITIAL_PASSWORD.txt` (mode 0600), and log it.
3. Start uvicorn. The Setup view in the UI checks for first-run state
   via `GET /api/auth/me` (returns 404 `not_initialized`) and forces a
   password change before exposing the rest of the app.

## 12. Frontend

- Vue 3 + Vite + TypeScript + Element Plus.
- Pinia for state, vue-router for routing.
- Single axios instance; intercepts attach `X-Requested-With` and redirect
  to `/setup` or `/login` on 401/403/404-`not_initialized`.
- Pages: Login, Setup (first run), Dashboard (status overview), Sources,
  SourceDetail (with rule list + scan button), Rules, Tokens, Settings.
- All long text is English; the design is i18n-friendly (key-only calls
  in components) but v1 ships English-only.

## 13. Testing strategy

| Layer | Test file | Notes |
|---|---|---|
| Filter rules | `tests/test_filters.py` | Pure functions over `FileEntry` lists |
| M3U renderer | `tests/test_m3u.py` | Template, escaping, empty source |
| Models / DB | `tests/test_models.py` | In-memory SQLite, unique constraints |
| Local adapter | `tests/test_local_adapter.py` | `tmp_path`, symlink, traversal |
| WebDAV adapter | `tests/test_webdav_adapter.py` | `pytest-httpx` mock transport |
| Proxy | `tests/test_proxy.py` | ASGI test client, Range behavior |
| Auth | `tests/test_auth.py` | Cookie TTL, token revocation |
| E2E | `tests/test_e2e.py` | Add local source → scan → fetch M3U → pull proxy |

Coverage targets (soft): `filters`, `m3u`, `proxy` ≥ 80 %; rest opportunistic.

## 14. Deployment

### 14.1 Dockerfile (multi-stage)

```dockerfile
# stage 1: build frontend
FROM node:20-alpine AS frontend
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# stage 2: backend
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg ca-certificates curl && rm -rf /var/lib/apt/lists/*
COPY backend/pyproject.toml backend/uv.lock* ./
RUN pip install --no-cache-dir uv && uv sync --frozen
COPY backend/ .
COPY --from=frontend /web/dist /app/any2m3u/web
ENV ANY2M3U_DATA=/data \
    ANY2M3U_WEB=/app/any2m3u/web
EXPOSE 8000
CMD ["uv", "run", "any2m3u"]
```

`ffmpeg` is included for future transcoding hooks; v1 does not call it.

### 14.2 docker-compose.yml

```yaml
services:
  any2m3u:
    build: .
    image: any2m3u:latest
    container_name: any2m3u
    restart: unless-stopped
    ports:
      - "127.0.0.1:8000:8000"   # loopback only; nginx in front
    volumes:
      - ./data:/data
      - /path/to/your/media:/media:ro
    environment:
      - ANY2M3U_ADMIN_PASSWORD=
      - ANY2M3U_BASE_URL=https://your.domain
      - ANY2M3U_LOG_LEVEL=INFO
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 5s
      retries: 3
```

### 14.3 Host nginx template (`deploy/nginx.example.conf`)

```nginx
server {
    listen 443 ssl http2;
    server_name your.domain;

    ssl_certificate     /etc/letsencrypt/live/your.domain/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your.domain/privkey.pem;

    client_max_body_size 1m;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Required for range/seek behavior to pass through
        proxy_buffering off;
        proxy_request_buffering off;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
}
```

## 15. Open questions / future work

- Multi-user support — schema already accommodates it, UI does not.
- EPG / XMLTV — out of scope.
- Per-source bandwidth throttling — out of scope.
- Cache eviction (LRU) when `/data/scan` grows large — out of scope; assume
  home-scale (~10 sources × ~10k files).
