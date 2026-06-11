import pytest
from any2m3u.db import init_db
from sqlalchemy import text


@pytest.mark.asyncio
async def test_init_db_creates_tables(tmp_path):
    await init_db(tmp_path)
    # verify by opening a new connection
    from sqlalchemy.ext.asyncio import create_async_engine
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_path/'app.db'}")
    async with eng.begin() as conn:
        r = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"))
        names = [row[0] for row in r]
    assert "users" in names
    assert "sources" in names
    assert "rules" in names
    assert "pull_tokens" in names
    assert "sessions" in names
    assert "scan_cache" in names


@pytest.mark.asyncio
async def test_init_db_idempotent(tmp_path):
    await init_db(tmp_path)
    await init_db(tmp_path)  # should not raise
