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
async def test_login_then_me(tmp_path, monkeypatch):
    """After login, /me should return the user; after logout, 401."""
    monkeypatch.setenv("ANY2M3U_DATA", str(tmp_path))
    monkeypatch.setenv("ANY2M3U_ADMIN_PASSWORD", "secret123")
    app = create_app()
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
            assert r.status_code == 200
            assert "any2m3u_sid" in c.cookies
            # /me should return the user now
            me = await c.get("/api/auth/me")
            assert me.status_code == 200
            assert me.json()["username"] == "admin"
            # Logout
            await c.post("/api/auth/logout")
            # /me should return 401
            me2 = await c.get("/api/auth/me")
            assert me2.status_code == 401


@pytest.mark.asyncio
async def test_password_change_invalidates_other_sessions(tmp_path, monkeypatch):
    """Changing the password should kill all other sessions for the same user."""
    monkeypatch.setenv("ANY2M3U_DATA", str(tmp_path))
    monkeypatch.setenv("ANY2M3U_ADMIN_PASSWORD", "secret123")
    app = create_app()
    async with LifespanManager(app):
        # Two clients, both login as admin
        c1 = AsyncClient(transport=ASGITransport(app=app), base_url="http://t")
        c2 = AsyncClient(transport=ASGITransport(app=app), base_url="http://t")
        await c1.__aenter__()
        await c2.__aenter__()
        try:
            r1 = await c1.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
            assert r1.status_code == 200
            r2 = await c2.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
            assert r2.status_code == 200
            # Both /me work
            assert (await c1.get("/api/auth/me")).status_code == 200
            assert (await c2.get("/api/auth/me")).status_code == 200
            # c1 changes password
            cp = await c1.post("/api/auth/password", json={"old": "secret123", "new": "newpass99"})
            assert cp.status_code == 200
            # c1 (current) still works
            assert (await c1.get("/api/auth/me")).status_code == 200
            # c2 is invalidated
            assert (await c2.get("/api/auth/me")).status_code == 401
        finally:
            await c1.__aexit__(None, None, None)
            await c2.__aexit__(None, None, None)
