import pytest
from httpx import ASGITransport, AsyncClient
from asgi_lifespan import LifespanManager
from any2m3u.main import create_app


@pytest.mark.asyncio
async def test_first_run_setup_required(tmp_path, monkeypatch):
    """When admin creation is suppressed (e.g. test mode without password env),
    /me should signal not_initialized. With ANY2M3U_ADMIN_PASSWORD set, admin
    is created during lifespan and /me returns 401."""
    monkeypatch.setenv("ANY2M3U_DATA", str(tmp_path))
    app = create_app()
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/api/auth/me")
            # Admin was bootstrapped with a random password; logged out, so 401.
            assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_logout(tmp_path, monkeypatch):
    monkeypatch.setenv("ANY2M3U_DATA", str(tmp_path))
    monkeypatch.setenv("ANY2M3U_ADMIN_PASSWORD", "secret123")
    app = create_app()
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
            assert r.status_code == 200
            assert "any2m3u_sid" in c.cookies
            r3 = await c.post("/api/auth/logout")
            assert r3.status_code == 204
            assert "any2m3u_sid" not in c.cookies
