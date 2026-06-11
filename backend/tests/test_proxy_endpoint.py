"""End-to-end tests for the public /proxy endpoint.

These tests exercise the full FastAPI stack (router → deps → adapter)
against a real LocalAdapter, verifying:
  - 200 OK + full body when no Range header
  - 206 Partial Content + Content-Range + body slice when Range is sent
  - 401 for missing/invalid token
  - 404 for unknown entry id
"""
import json
import os
import pytest
from httpx import ASGITransport, AsyncClient
from asgi_lifespan import LifespanManager
from any2m3u.main import create_app


@pytest.fixture
async def app_with_local_source(tmp_path, monkeypatch):
    """Set up an app with a local source pre-scanned, return (app, token, entry_id)."""
    data = tmp_path / "data"; data.mkdir()
    media = tmp_path / "media"
    media.mkdir()
    (media / "video.mp4").write_bytes(b"0123456789" * 10)  # 100 bytes

    monkeypatch.setenv("ANY2M3U_DATA", str(data))
    monkeypatch.setenv("ANY2M3U_ADMIN_PASSWORD", "secret123")
    monkeypatch.setenv("ANY2M3U_BASE_URL", "http://test")

    app = create_app()
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            await c.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
            r = await c.post("/api/sources", json={
                "name": "m", "type": "local", "config": {"path": str(media)},
            })
            sid = r.json()["id"]
            rr = await c.post(f"/api/sources/{sid}/rules", json={
                "name": "all",
                "include_exts": "mp4",
                "tpl": "#EXTINF:-1,\n<base>/proxy?token=<t>&id=<eid>",
            })
            rid = rr.json()["id"]
            tr = await c.post("/api/tokens", json={"name": "test"})
            token = tr.json()["token"]
            await c.post(f"/api/sources/{sid}/scan")
            import asyncio
            for _ in range(60):
                sr = await c.get(f"/api/sources/{sid}/scan")
                if sr.json()["status"] == "success":
                    break
                await asyncio.sleep(0.05)
            yield c, token, rid
        # LifespanManager ends here; outer fixture cleans up


@pytest.mark.asyncio
async def test_proxy_full_body(app_with_local_source):
    c, token, rid = app_with_local_source
    r = await c.get(f"/m3u/rule/{rid}?token={token}")
    import re
    m = re.search(r"id=([a-f0-9]+)", r.text)
    assert m, f"no id in {r.text!r}"
    eid = m.group(1)
    pr = await c.get(f"/proxy?token={token}&id={eid}")
    assert pr.status_code == 200
    assert pr.content == b"0123456789" * 10
    assert pr.headers["accept-ranges"] == "bytes"
    assert pr.headers["content-length"] == "100"


@pytest.mark.asyncio
async def test_proxy_range(app_with_local_source):
    c, token, rid = app_with_local_source
    r = await c.get(f"/m3u/rule/{rid}?token={token}")
    import re
    eid = re.search(r"id=([a-f0-9]+)", r.text).group(1)
    pr = await c.get(f"/proxy?token={token}&id={eid}", headers={"Range": "bytes=10-19"})
    assert pr.status_code == 206
    assert pr.content == b"0123456789"
    assert pr.headers["content-range"] == "bytes 10-19/100"
    assert pr.headers["content-length"] == "10"


@pytest.mark.asyncio
async def test_proxy_suffix_range(app_with_local_source):
    c, token, rid = app_with_local_source
    r = await c.get(f"/m3u/rule/{rid}?token={token}")
    import re
    eid = re.search(r"id=([a-f0-9]+)", r.text).group(1)
    pr = await c.get(f"/proxy?token={token}&id={eid}", headers={"Range": "bytes=-5"})
    assert pr.status_code == 206
    assert pr.content == b"56789"
    assert pr.headers["content-range"] == "bytes 95-99/100"


@pytest.mark.asyncio
async def test_proxy_invalid_token(app_with_local_source):
    c, _token, _rid = app_with_local_source
    pr = await c.get("/proxy?token=nope&id=anything")
    assert pr.status_code == 401
    assert pr.headers.get("www-authenticate", "").lower().startswith("bearer")


@pytest.mark.asyncio
async def test_proxy_unknown_entry(app_with_local_source):
    c, token, _rid = app_with_local_source
    pr = await c.get(f"/proxy?token={token}&id=ffffffffffffffffffffffffffffffff")
    assert pr.status_code == 404
    assert pr.json()["detail"]["error"] == "not_found"


@pytest.mark.asyncio
async def test_proxy_range_fallback_returns_200_when_upstream_ignores_range(
    app_with_local_source, monkeypatch
):
    """When the upstream ignores Range and returns 200, the proxy must
    also return 200 with Content-Length=full size, not 206 with a
    mismatched Content-Range."""
    c, token, rid = app_with_local_source
    r = await c.get(f"/m3u/rule/{rid}?token={token}")
    import re
    eid = re.search(r"id=([a-f0-9]+)", r.text).group(1)

    # Monkey-patch LocalAdapter.open_range to simulate "upstream ignored Range"
    from any2m3u.scanner import local
    orig = local.LocalAdapter.open_range
    async def fake_open_range(self, path, start, end):
        # Simulate upstream returning 200: yield the whole file and tell the
        # proxy the range was not honored.
        _, full_iter = await orig(self, path, 0, None)
        return (False, full_iter)
    monkeypatch.setattr(local.LocalAdapter, "open_range", fake_open_range)

    pr = await c.get(f"/proxy?token={token}&id={eid}", headers={"Range": "bytes=10-19"})
    assert pr.status_code == 200  # NOT 206
    assert pr.content == b"0123456789" * 10
    assert "content-range" not in {k.lower() for k in pr.headers.keys()}
    assert pr.headers["content-length"] == "100"
