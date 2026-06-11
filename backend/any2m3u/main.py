from __future__ import annotations
import logging
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from .api import auth as auth_api
from .api import sources as sources_api
from .api import rules as rules_api
from .api import tokens as tokens_api
from .api import scan as scan_api
from .api import public as public_api
from .config import get_settings
from .db import get_sessionmaker, init_db
from .models import User
from .scheduler import register_all, shutdown as sched_shutdown
from .scanner.engine import cleanup_tmp_files, load_all_indexes
from .security import hash_password

log = logging.getLogger(__name__)


async def _bootstrap_admin() -> None:
    sm = get_sessionmaker()
    async with sm() as s:
        existing = (await s.execute(select(User).limit(1))).first()
    if existing is not None:
        return
    s = get_settings()
    pw = s.admin_password
    if not pw:
        pw = secrets.token_urlsafe(18)
        try:
            p = s.data_dir / s.initial_password_file
            p.write_text(pw + "\n", encoding="utf-8")
            try: p.chmod(0o600)
            except Exception: pass
        except OSError as e:
            log.warning("could not write initial password file: %s", e)
        log.warning("=" * 60)
        log.warning("Any2M3U initial admin password: %s", pw)
        log.warning("=" * 60)
    async with sm() as sess:
        sess.add(User(
            username="admin",
            password_hash=hash_password(pw),
            created_at=datetime.now(timezone.utc).isoformat(),
        ))
        await sess.commit()


@asynccontextmanager
async def _lifespan(app: FastAPI):
    s = get_settings()
    await init_db(s.data_dir)
    await _bootstrap_admin()
    await cleanup_tmp_files()
    await load_all_indexes()
    try:
        await register_all()
    except Exception as e:
        log.warning("scheduler init failed: %s", e)
    yield
    sched_shutdown()


def create_app() -> FastAPI:
    s = get_settings()
    logging.basicConfig(level=getattr(logging, s.log_level.upper(), logging.INFO))
    app = FastAPI(title="Any2M3U", lifespan=_lifespan)
    app.include_router(auth_api.router)
    app.include_router(sources_api.router)
    app.include_router(rules_api.router)
    app.include_router(tokens_api.router)
    app.include_router(scan_api.router)
    app.include_router(public_api.router)

    @app.get("/api/health")
    async def health():
        return {"ok": True}

    # Serve SPA static files (built Vue dist)
    if s.web_dir.exists():
        app.mount("/", StaticFiles(directory=str(s.web_dir), html=True), name="web")
    else:
        log.warning("=" * 60)
        log.warning("Web UI directory not found: %s", s.web_dir)
        log.warning("The API will work, but the management UI is not available.")
        log.warning("Build the frontend: cd frontend && npm install && npm run build")
        log.warning("=" * 60)

        @app.get("/", include_in_schema=False)
        async def no_ui_index():
            return HTMLResponse(
                f"<html><body style='font-family:sans-serif;max-width:640px;margin:48px auto;padding:0 16px'>"
                f"<h1>Any2M3U — API only</h1>"
                f"<p>The management UI has not been built. The API is working.</p>"
                f"<p>To build the UI:</p>"
                f"<pre>cd frontend &amp;&amp; npm install &amp;&amp; npm run build</pre>"
                f"<p>Expected web dir: <code>{s.web_dir}</code></p>"
                f"<p>Health: <a href='/api/health'>/api/health</a></p>"
                f"</body></html>",
                status_code=503,
            )
    return app


if __name__ == "__main__":
    import uvicorn
    host, _, port = s.bind.partition(":")
    uvicorn.run(create_app(), host=host or "0.0.0.0", port=int(port or 8000))
