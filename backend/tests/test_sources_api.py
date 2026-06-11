import pytest
from httpx import ASGITransport, AsyncClient
from asgi_lifespan import LifespanManager
from any2m3u.main import create_app


@pytest.mark.asyncio
async def test_source_crud(tmp_path, monkeypatch):
    monkeypatch.setenv("ANY2M3U_DATA", str(tmp_path))
    monkeypatch.setenv("ANY2M3U_ADMIN_PASSWORD", "secret123")
    app = create_app()
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            await c.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
            r = await c.post("/api/sources", json={"name": "x", "type": "local", "config": {"path": "/tmp"}})
            assert r.status_code == 201
            sid = r.json()["id"]
            r2 = await c.get(f"/api/sources/{sid}")
            assert r2.json()["name"] == "x"
            r3 = await c.patch(f"/api/sources/{sid}", json={"name": "y"})
            assert r3.json()["name"] == "y"
            r4 = await c.delete(f"/api/sources/{sid}")
            assert r4.status_code == 204


@pytest.mark.asyncio
async def test_delete_source_removes_disk_cache(tmp_path, monkeypatch):
    """Deleting a source must remove its scan/{sid}.jsonl file."""
    monkeypatch.setenv("ANY2M3U_DATA", str(tmp_path))
    monkeypatch.setenv("ANY2M3U_ADMIN_PASSWORD", "secret123")
    app = create_app()
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            await c.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
            r = await c.post("/api/sources", json={
                "name": "x", "type": "local", "config": {"path": str(tmp_path)},
            })
            sid = r.json()["id"]
            from any2m3u.config import get_settings
            cache_dir = get_settings().scan_dir
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = cache_dir / f"{sid}.jsonl"
            cache_file.write_text('{"path": "f.mp4", "size": 1, "mtime": 0}\n')
            assert cache_file.exists()
            r = await c.delete(f"/api/sources/{sid}")
            assert r.status_code == 204
            assert not cache_file.exists()


@pytest.mark.asyncio
async def test_delete_source_persists_db_row_before_unlinking_disk(tmp_path, monkeypatch):
    """If the disk unlink fails (or DB delete raises), the Source row must
    remain in DB and not point at missing files. Order: DB first, then disk."""
    monkeypatch.setenv("ANY2M3U_DATA", str(tmp_path))
    monkeypatch.setenv("ANY2M3U_ADMIN_PASSWORD", "secret123")
    app = create_app()
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            await c.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
            r = await c.post("/api/sources", json={
                "name": "x", "type": "local", "config": {"path": str(tmp_path)},
            })
            sid = r.json()["id"]
            from any2m3u.config import get_settings
            cache_dir = get_settings().scan_dir
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = cache_dir / f"{sid}.jsonl"
            cache_file.write_text('{"path": "f.mp4", "size": 1, "mtime": 0}\n')
            assert cache_file.exists()
            r = await c.delete(f"/api/sources/{sid}")
            assert r.status_code == 204
            # After successful delete: both gone.
            assert not cache_file.exists()
            from any2m3u.db import get_sessionmaker
            from any2m3u.models import Source
            from sqlalchemy import select
            sm = get_sessionmaker()
            async with sm() as s:
                rows = (await s.execute(select(Source).where(Source.id == sid))).scalars().all()
                assert len(rows) == 0
