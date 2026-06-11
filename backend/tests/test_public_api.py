import asyncio
import os
import pytest
from httpx import ASGITransport, AsyncClient
from asgi_lifespan import LifespanManager
from any2m3u.main import create_app


@pytest.mark.asyncio
async def test_m3u_and_proxy(tmp_path, monkeypatch):
    monkeypatch.setenv("ANY2M3U_DATA", str(tmp_path))
    monkeypatch.setenv("ANY2M3U_ADMIN_PASSWORD", "secret123")
    monkeypatch.setenv("ANY2M3U_BASE_URL", "http://pub")
    media = tmp_path / "media"
    media.mkdir()
    (media / "a.mp4").write_bytes(b"0123456789")
    (media / "a.jpg").write_bytes(b"jpgdata")  # not in filter; just exists

    app = create_app()
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            await c.post("/api/auth/login", json={"username": "admin", "password": "secret123"})

            r = await c.post("/api/sources", json={
                "name": "m", "type": "local", "config": {"path": str(media)},
            })
            assert r.status_code == 201, r.text
            sid = r.json()["id"]

            rr = await c.post(f"/api/sources/{sid}/rules", json={
                "name": "all",
                "include_exts": "mp4",
                "tpl": "#EXTINF:-1 tvg-logo=\"<logo>\" group-title=\"<group>\",<title>\n<base>/proxy?token=<t>&id=<eid>",
                "group_title": "Movies",
            })
            assert rr.status_code == 201, rr.text
            rid = rr.json()["id"]

            tr = await c.post("/api/tokens", json={"name": "tv"})
            assert tr.status_code == 201
            token = tr.json()["token"]

            scan_resp = await c.post(f"/api/sources/{sid}/scan")
            assert scan_resp.status_code == 200

            # poll until done
            for _ in range(60):
                sr = await c.get(f"/api/sources/{sid}/scan")
                if sr.json()["status"] == "success":
                    break
                await asyncio.sleep(0.1)
            else:
                pytest.fail("scan never finished")

            m = await c.get(f"/m3u/rule/{rid}?token={token}")
            assert m.status_code == 200
            body = m.text
            assert "#EXTM3U" in body
            assert "a.mp4" not in body  # title strips extension
            assert 'group-title="Movies"' in body
            assert "http://pub/proxy?token=" in body

            import re
            ids = re.findall(r"id=([a-f0-9]+)", body)
            assert ids
            eid = ids[0]

            pr = await c.get(f"/proxy?token={token}&id={eid}")
            assert pr.status_code == 200
            assert pr.content == b"0123456789"

            prr = await c.get(f"/proxy?token={token}&id={eid}", headers={"Range": "bytes=2-5"})
            assert prr.status_code == 206
            assert prr.content == b"2345"
            assert prr.headers["content-range"] == "bytes 2-5/10"


@pytest.mark.asyncio
async def test_invalid_token(tmp_path, monkeypatch):
    monkeypatch.setenv("ANY2M3U_DATA", str(tmp_path))
    monkeypatch.setenv("ANY2M3U_ADMIN_PASSWORD", "secret123")
    app = create_app()
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/m3u/rule/1?token=nope")
            assert r.status_code == 401
            assert r.headers.get("www-authenticate", "").lower().startswith("bearer")
