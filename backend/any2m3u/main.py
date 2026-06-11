from __future__ import annotations
import logging
import secrets
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI
from sqlalchemy import select
from .api import auth as auth_api
from .api import sources as sources_api
from .api import rules as rules_api
from .api import tokens as tokens_api
from .api import scan as scan_api
from .config import get_settings
from .db import get_sessionmaker, init_db
from .models import User
from .security import hash_password

log = logging.getLogger(__name__)


async def _bootstrap_admin() -> None:
    """If no admin user exists, create one. Honors ANY2M3U_ADMIN_PASSWORD
    or generates a random one printed to logs and INITIAL_PASSWORD.txt."""
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
            created_at=datetime.utcnow().isoformat(),
        ))
        await sess.commit()


@asynccontextmanager
async def _lifespan(app: FastAPI):
    s = get_settings()
    await init_db(s.data_dir)
    await _bootstrap_admin()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Any2M3U", lifespan=_lifespan)
    app.include_router(auth_api.router)
    app.include_router(sources_api.router)
    app.include_router(rules_api.router)
    app.include_router(tokens_api.router)
    app.include_router(scan_api.router)

    @app.get("/api/health")
    async def health():
        return {"ok": True}

    return app
