"""SPA static fallback must not serve files outside web_dir."""
import pytest
from httpx import ASGITransport, AsyncClient
from asgi_lifespan import LifespanManager


@pytest.mark.asyncio
async def test_spa_fallback_blocks_path_traversal(tmp_path, monkeypatch):
    """Encoded ../ segments must NOT serve files outside web_dir."""
    monkeypatch.setenv("ANY2M3U_DATA", str(tmp_path))
    monkeypatch.setenv("ANY2M3U_ADMIN_PASSWORD", "secret123")
    from any2m3u.config import get_settings
    get_settings.cache_clear()
    s = get_settings()
    # Isolate web_dir to the tmpdir so the test never writes into the package
    # directory. The "secret" lives one level above web_dir, which is exactly
    # what the ../ traversal attempts to reach.
    web = tmp_path / "web"
    web.mkdir(parents=True, exist_ok=True)
    (web / "index.html").write_text("<html>ok</html>")
    secret = tmp_path / "secret.txt"          # == web.parent / "secret.txt"
    secret.write_text("TOP SECRET")
    monkeypatch.setattr(s, "web_dir", web)

    from any2m3u.main import create_app
    app = create_app()
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            for traversal in ["/..%2Fsecret.txt", "/%2e%2e/secret.txt", "/..%5Csecret.txt"]:
                r = await c.get(traversal)
                assert b"TOP SECRET" not in r.content, f"leaked via {traversal!r}"
            # Legitimate file still works.
            r = await c.get("/index.html")
            assert r.status_code == 200
            assert b"ok" in r.content
