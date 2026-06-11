import pytest
from httpx import ASGITransport, AsyncClient
from asgi_lifespan import LifespanManager
from any2m3u.main import create_app


@pytest.mark.asyncio
async def test_token_create_and_revoke(tmp_path, monkeypatch):
    monkeypatch.setenv("ANY2M3U_DATA", str(tmp_path))
    monkeypatch.setenv("ANY2M3U_ADMIN_PASSWORD", "secret123")
    app = create_app()
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            await c.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
            r = await c.post("/api/tokens", json={"name": "tv"})
            assert r.status_code == 201
            tid = r.json()["id"]
            token = r.json()["token"]
            assert len(token) >= 32
            r2 = await c.get("/api/tokens")
            assert len(r2.json()) == 1
            r3 = await c.delete(f"/api/tokens/{tid}")
            assert r3.status_code == 204
            r4 = await c.get("/api/tokens")
            assert r4.json()[0]["revoked"] is True
