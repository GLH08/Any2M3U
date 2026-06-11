import pytest
from datetime import datetime, timezone
from any2m3u.db import init_db, get_sessionmaker
from any2m3u.models import User, Source, Rule, PullToken, ScanCache


@pytest.mark.asyncio
async def test_create_user(tmp_path):
    await init_db(tmp_path)
    sm = get_sessionmaker()
    async with sm() as s:
        u = User(username="admin", password_hash="x", created_at=datetime.now(timezone.utc).isoformat())
        s.add(u)
        await s.commit()
        await s.refresh(u)
        assert u.id is not None
        assert u.username == "admin"


@pytest.mark.asyncio
async def test_unique_username(tmp_path):
    await init_db(tmp_path)
    sm = get_sessionmaker()
    now = datetime.now(timezone.utc).isoformat()
    async with sm() as s:
        s.add(User(username="admin", password_hash="x", created_at=now))
        await s.commit()
    async with sm() as s:
        s.add(User(username="admin", password_hash="y", created_at=now))
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            await s.commit()


@pytest.mark.asyncio
async def test_source_rule_cascade(tmp_path):
    await init_db(tmp_path)
    sm = get_sessionmaker()
    now = datetime.now(timezone.utc).isoformat()
    async with sm() as s:
        src = Source(name="x", type="local", config_json="{}", created_at=now)
        s.add(src)
        await s.commit()
        await s.refresh(src)
        s.add(Rule(source_id=src.id, name="r1", tpl="", created_at=now))
        await s.commit()
    async with sm() as s:
        src = (await s.execute(__import__("sqlalchemy").select(Source))).scalar_one()
        await s.delete(src)
        await s.commit()
    async with sm() as s:
        from sqlalchemy import select, func
        n = (await s.execute(select(func.count()).select_from(Rule))).scalar_one()
        assert n == 0


@pytest.mark.asyncio
async def test_pull_token_unique(tmp_path):
    await init_db(tmp_path)
    sm = get_sessionmaker()
    now = datetime.now(timezone.utc).isoformat()
    async with sm() as s:
        s.add(PullToken(name="a", token="tok1", created_at=now))
        await s.commit()
    async with sm() as s:
        s.add(PullToken(name="b", token="tok1", created_at=now))
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            await s.commit()
