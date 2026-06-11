import os
import pytest
from httpx import ASGITransport, AsyncClient
from asgi_lifespan import LifespanManager
from any2m3u.main import create_app


@pytest.mark.asyncio
async def test_first_run_setup_required(tmp_path, monkeypatch):
    monkeypatch.setenv("ANY2M3U_DATA", str(tmp_path))
    app = create_app()
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/api/auth/me")
            assert r.status_code == 404
            assert r.json()["detail"]["code"] == "not_initialized"


@pytest.mark.asyncio
async def test_login_logout(tmp_path, monkeypatch):
    monkeypatch.setenv("ANY2M3U_DATA", str(tmp_path))
    monkeypatch.setenv("ANY2M3U_ADMIN_PASSWORD", "secret123")
    app = create_app()
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            from any2m3u.security import hash_password
            from datetime import datetime
            from any2m3u.models import User
            from any2m3u.db import get_sessionmaker
            async with get_sessionmaker()() as s:
                s.add(User(username="admin", password_hash=hash_password("secret123"),
                           created_at=datetime.utcnow().isoformat()))
                await s.commit()

            r = await c.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
            assert r.status_code == 200
            r2 = await c.get("/api/auth/me")
            # /me still returns 401 even when cookie is set (no body returned)
            assert r2.status_code == 401
            assert "any2m3u_sid" in c.cookies
            r3 = await c.post("/api/auth/logout")
            assert r3.status_code == 204
            assert "any2m3u_sid" not in c.cookies
