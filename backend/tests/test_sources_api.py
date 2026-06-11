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
