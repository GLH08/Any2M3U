"""Integration test against a real in-process WebDAV-like HTTP server.

This is stronger than `pytest-httpx` mocks because it exercises the
real `httpx.AsyncClient` transport, real PROPFIND request generation,
and the WebDAV adapter's full parsing/loop.

The fake server is intentionally minimal — it implements only what the
adapter needs (PROPFIND with Depth:1, GET with optional Range).
"""
from __future__ import annotations

import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from xml.etree import ElementTree as ET
import pytest
import anyio
from any2m3u.scanner.webdav import WebDAVAdapter


class _WebDAVState:
    """In-memory filesystem of (path -> (size, content)) tuples."""

    def __init__(self):
        self.files: dict[str, tuple[int, bytes]] = {}

    def add(self, path: str, content: bytes) -> None:
        self.files[path] = (len(content), content)


def _format_propfind_response(state: _WebDAVState, base_path: str) -> bytes:
    """Build a multistatus XML for a Depth:1 PROPFIND at base_path.

    Hand-built string instead of ET (which would mangle the D: prefix).
    """
    base = base_path.split("?", 1)[0].rstrip("/")
    lines = ['<?xml version="1.0" encoding="utf-8"?>',
             '<D:multistatus xmlns:D="DAV:">']
    for path, (size, _content) in state.files.items():
        if base:
            prefix = base + "/"
            if not path.startswith(prefix):
                continue
            child = path[len(prefix):]
        else:
            child = path.lstrip("/")
        if "/" in child:
            continue
        href_path = base + "/" + child if base else "/" + child
        is_dir = size == 0
        rtype = '<D:collection/>' if is_dir else ''
        lines.append(f'  <D:response>')
        lines.append(f'    <D:href>{href_path}</D:href>')
        lines.append(f'    <D:propstat>')
        lines.append(f'      <D:prop>')
        lines.append(f'        <D:resourcetype>{rtype}</D:resourcetype>')
        lines.append(f'        <D:getcontentlength>{size}</D:getcontentlength>')
        lines.append(f'        <D:getlastmodified>Mon, 01 Jan 2024 00:00:00 GMT</D:getlastmodified>')
        lines.append(f'        <D:getetag>"x"</D:getetag>')
        lines.append(f'      </D:prop>')
        lines.append(f'      <D:status>HTTP/1.1 200 OK</D:status>')
        lines.append(f'    </D:propstat>')
        lines.append(f'  </D:response>')
    lines.append('</D:multistatus>')
    return "\n".join(lines).encode("utf-8")


class _Handler(BaseHTTPRequestHandler):
    state: _WebDAVState = _WebDAVState()
    auth_user: str = "u"
    auth_pass: str = "p"
    realm: str = "test"

    def log_message(self, *_a, **_kw):
        return  # quiet

    def _auth_ok(self) -> bool:
        h = self.headers.get("Authorization", "")
        if not h.startswith("Basic "):
            self._send_basic_challenge()
            return False
        import base64
        try:
            raw = base64.b64decode(h.split(" ", 1)[1]).decode()
            user, _, pw = raw.partition(":")
        except Exception:
            self._send_basic_challenge()
            return False
        if user == self.auth_user and pw == self.auth_pass:
            return True
        self._send_basic_challenge()
        return False

    def _send_basic_challenge(self):
        body = b"Unauthorized"
        self.send_response(401)
        self.send_header("WWW-Authenticate", f'Basic realm="{self.realm}"')
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(body)

    def do_PROPFIND(self):
        if not self._auth_ok():
            return
        path = self.path
        body = _format_propfind_response(self.state, path)
        self.send_response(207)
        self.send_header("Content-Type", "application/xml")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self._auth_ok():
            return
        # Strip query string
        path = self.path.split("?", 1)[0]
        if path not in self.state.files:
            self.send_error(404, "not found")
            return
        size, content = self.state.files[path]
        rng = self.headers.get("Range", "")
        if rng.startswith("bytes="):
            spec = rng[len("bytes="):]
            start_s, _, end_s = spec.partition("-")
            try:
                start = int(start_s)
            except ValueError:
                self.send_error(400, "bad range")
                return
            end = int(end_s) if end_s else size - 1
            end = min(end, size - 1)
            chunk = content[start:end + 1]
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(len(chunk)))
            self.send_header("Content-Type", "video/mp4")
            self.end_headers()
            self.wfile.write(chunk)
        else:
            self.send_response(200)
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(size))
            self.send_header("Content-Type", "video/mp4")
            self.end_headers()
            self.wfile.write(content)


class _WebDAVServer:
    def __init__(self):
        # Bind on ephemeral port
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)


@pytest.fixture
def webdav_server():
    state = _WebDAVState()
    # Bare paths (no scheme/host); the test server returns these in href
    # and the GET handler matches by path-without-query.
    state.add("/Media/Movies/a.mp4", b"a" * 100)
    state.add("/Media/Movies/b.mkv", b"b" * 200)
    state.add("/Media/Other/c.mp4", b"c" * 50)
    # Subdirs (size=0) so BFS can recurse into them
    state.add("/Media/Movies", b"")
    state.add("/Media/Other", b"")
    _Handler.state = state
    srv = _WebDAVServer()
    yield srv
    srv.stop()


@pytest.mark.asyncio
async def test_list_through_real_http(webdav_server):
    a = WebDAVAdapter(webdav_server.base_url, "u", "p", root_path="/Media")
    try:
        paths = sorted([e["path"] async for e in a.list()])
        assert paths == ["Movies/a.mp4", "Movies/b.mkv", "Other/c.mp4"]
    finally:
        await a.aclose()


@pytest.mark.asyncio
async def test_list_with_subdir_root_path(webdav_server):
    """User scenario: base_url is just host, root_path is the full WebDAV path
    (e.g. Nextcloud /dav/files/admin). Adapter must strip the root_path and
    treat only the suffix as relative."""
    a = WebDAVAdapter(webdav_server.base_url, "u", "p", root_path="/Media/Movies")
    try:
        paths = sorted([e["path"] async for e in a.list()])
        # Should find only files under Movies/
        assert paths == ["a.mp4", "b.mkv"]
    finally:
        await a.aclose()


@pytest.mark.asyncio
async def test_auth_failure_through_real_http(webdav_server):
    from any2m3u.scanner.base import UpstreamAuthError
    a = WebDAVAdapter(webdav_server.base_url, "wrong", "wrong", root_path="/Media")
    try:
        with pytest.raises(UpstreamAuthError):
            async for _ in a.list():
                pass
    finally:
        await a.aclose()


@pytest.mark.asyncio
async def test_range_through_real_http(webdav_server):
    a = WebDAVAdapter(webdav_server.base_url, "u", "p", root_path="/Media")
    try:
        # The adapter strips root, so files come back as "Movies/a.mp4"
        # But for open_range we pass the path that the adapter stored internally.
        # Look it up via the listing.
        paths = [e["path"] async for e in a.list()]
        target = next(p for p in paths if p.endswith("a.mp4"))
        chunks = []
        async for c in a.open_range(target, 10, 19):
            chunks.append(c)
        assert b"".join(chunks) == b"a" * 10
    finally:
        await a.aclose()
