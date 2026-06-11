import httpx
import pytest
from any2m3u.scanner.webdav import WebDAVAdapter
from any2m3u.scanner.base import UpstreamAuthError


@pytest.mark.asyncio
async def test_list_basic(httpx_mock):
    def callback(request):
        if request.headers.get("Depth") != "1":
            return httpx.Response(400)
        body = b"""<?xml version='1.0' encoding='utf-8'?>
<d:multistatus xmlns:d='DAV:'>
  <d:response>
    <d:href>/Media/Movies/</d:href>
    <d:propstat><d:prop><d:resourcetype><d:collection/></d:resourcetype></d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat>
  </d:response>
  <d:response>
    <d:href>/Media/Movies/a.mp4</d:href>
    <d:propstat>
      <d:prop>
        <d:resourcetype/>
        <d:getcontentlength>1234</d:getcontentlength>
        <d:getlastmodified>Mon, 01 Jan 2024 00:00:00 GMT</d:getlastmodified>
        <d:getetag>"abc"</d:getetag>
      </d:prop>
      <d:status>HTTP/1.1 200 OK</d:status>
    </d:propstat>
  </d:response>
</d:multistatus>"""
        return httpx.Response(207, content=body, headers={"Content-Type": "application/xml"})

    httpx_mock.add_callback(callback, method="PROPFIND", is_reusable=True)
    a = WebDAVAdapter("https://dav.example.com", "u", "p", root_path="/Media")
    paths = sorted([e["path"] async for e in a.list()])
    assert paths == ["Movies/a.mp4"]


@pytest.mark.asyncio
async def test_auth_failure(httpx_mock):
    httpx_mock.add_response(401)
    a = WebDAVAdapter("https://dav.example.com", "u", "p", root_path="/Media")
    with pytest.raises(UpstreamAuthError):
        async for _ in a.list():
            pass


@pytest.mark.asyncio
async def test_open_range_passthrough(httpx_mock):
    httpx_mock.add_response(
        206,
        content=b"part",
        headers={"Content-Range": "bytes 0-3/10", "Accept-Ranges": "bytes", "Content-Length": "4"},
    )
    a = WebDAVAdapter("https://dav.example.com", "u", "p", root_path="/Media")
    chunks = []
    async for c in a.open_range("Movies/a.mp4", 0, 3):
        chunks.append(c)
    assert b"".join(chunks) == b"part"
