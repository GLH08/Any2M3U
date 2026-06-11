"""_bootstrap_admin must be idempotent under concurrent workers."""
import asyncio
import pytest
from any2m3u.main import _bootstrap_admin
from any2m3u.db import init_db, get_sessionmaker
from any2m3u.models import User
from sqlalchemy import select


@pytest.mark.asyncio
async def test_bootstrap_admin_idempotent_under_concurrent_calls(tmp_path, monkeypatch):
    monkeypatch.setenv("ANY2M3U_DATA", str(tmp_path))
    monkeypatch.setenv("ANY2M3U_ADMIN_PASSWORD", "secret123")
    from any2m3u.config import get_settings
    get_settings.cache_clear()
    await init_db(tmp_path)

    # Two concurrent bootstraps. The second must NOT crash with IntegrityError.
    await asyncio.gather(_bootstrap_admin(), _bootstrap_admin())

    sm = get_sessionmaker()
    async with sm() as s:
        users = (await s.execute(select(User))).scalars().all()
        assert len(users) == 1
        assert users[0].username == "admin"
