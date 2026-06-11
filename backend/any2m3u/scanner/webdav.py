from __future__ import annotations
import logging
import posixpath
import xml.etree.ElementTree as ET
from typing import AsyncIterator
from urllib.parse import urlparse, unquote
import httpx
from ..m3u.filters import FileEntry
from .base import UpstreamAuthError, UpstreamError

log = logging.getLogger(__name__)
NS = {"d": "DAV:"}


class WebDAVAdapter:
    """WebDAV source adapter.

    - Uses PROPFIND Depth:1 to enumerate.
    - Forwards Range headers; downstream consumer must pass through 206/Content-Range.
    - Single shared httpx.AsyncClient per adapter instance.
    """

    def __init__(self, base_url: str, username: str, password: str, root_path: str = "/", verify_tls: bool = True):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.root_path = "/" + root_path.strip("/") if root_path and root_path != "/" else ""
        self.verify_tls = verify_tls
        self._client: httpx.AsyncClient | None = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                auth=(self.username, self.password),
                verify=self.verify_tls,
                timeout=httpx.Timeout(30.0, connect=10.0),
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
            )
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _file_url(self, rel_path: str) -> str:
        """Build URL for a file path relative to source root."""
        rel = posixpath.normpath(rel_path).lstrip("/")
        prefix = self.root_path.rstrip("/")
        if prefix == "/":
            prefix = ""
        if rel:
            return f"{self.base_url}{prefix}/{rel}"
        return f"{self.base_url}{prefix}/" if prefix else f"{self.base_url}/"

    def _dir_url(self, rel_path: str) -> str:
        if not rel_path.startswith("/"):
            rel_path = "/" + rel_path
        if not rel_path.endswith("/"):
            rel_path += "/"
        prefix = self.root_path.rstrip("/")
        if prefix == "/":
            prefix = ""
        return f"{self.base_url}{prefix}{rel_path}"

    def _strip_root(self, href: str) -> str:
        path = urlparse(href).path
        path = unquote(path)
        prefix = self.root_path.rstrip("/")
        if prefix and prefix != "/" and path.startswith(prefix):
            path = path[len(prefix):]
        return path.lstrip("/")

    async def _propfind(self, rel_dir: str) -> ET.Element:
        """Issue a single PROPFIND at depth 1; return parsed XML."""
        client = await self._ensure_client()
        url = self._dir_url(rel_dir)
        try:
            r = await client.request("PROPFIND", url, headers={"Depth": "1"})
        except httpx.HTTPError as e:
            raise UpstreamError(str(e))
        if r.status_code in (401, 403):
            raise UpstreamAuthError(f"WebDAV auth failed: {r.status_code}")
        if r.status_code >= 400:
            raise UpstreamError(f"WebDAV PROPFIND failed: {r.status_code}")
        try:
            return ET.fromstring(r.content)
        except ET.ParseError as e:
            raise UpstreamError(f"PROPFIND parse error: {e}")

    def _parse_responses(self, root_el: ET.Element, rel_dir: str) -> tuple[list[FileEntry], list[str]]:
        """Parse a Depth:1 PROPFIND response, returning (files, subdirs) DIRECTLY under rel_dir.

        Logic: a response href whose first segment is rel_dir (or whose path
        equals rel_dir when rel_dir is empty) is a direct child. Anything
        deeper is ignored at this level (we'll get it via BFS recursion).

        For rel_dir = "" (root), we treat the FIRST path segment of href as
        the direct child; this is the standard WebDAV behavior. We then
        record the subdir's full path under root_path for later PROPFIND.
        """
        prefix = rel_dir.strip("/")
        files: list[FileEntry] = []
        subdirs: list[str] = []
        for resp in root_el.findall("d:response", NS):
            href = resp.findtext("d:href", default="", namespaces=NS)
            rel = self._strip_root(href).rstrip("/")
            if not rel:
                continue
            # Skip the directory itself
            if prefix and rel == prefix:
                continue
            # Determine the first segment (direct child name) and the tail
            if prefix:
                if not rel.startswith(prefix + "/"):
                    continue
                tail = rel[len(prefix) + 1:]
            else:
                tail = rel
            if "/" not in tail:
                # Direct child
                child_name = tail
            else:
                # Deeper than direct child — its first segment IS a direct subdir of `prefix`
                child_name = tail.split("/", 1)[0]
                # Treat as subdir of prefix (rel = prefix + child_name)
                if prefix:
                    child_path = prefix + "/" + child_name
                else:
                    child_path = child_name
                if child_path not in subdirs and child_path != prefix:
                    subdirs.append(child_path)
                continue

            is_dir = resp.find(".//d:resourcetype/d:collection", NS) is not None
            if is_dir:
                if prefix:
                    subdirs.append(prefix + "/" + child_name)
                else:
                    subdirs.append(child_name)
                continue

            size_s = resp.findtext(".//d:getcontentlength", default="0", namespaces=NS)
            lm = resp.findtext(".//d:getlastmodified", default="", namespaces=NS)
            etag = resp.findtext(".//d:getetag", default=None, namespaces=NS)
            size = int(size_s) if size_s.isdigit() else 0
            mtime = 0.0
            if lm:
                from email.utils import parsedate_to_datetime
                try:
                    mtime = parsedate_to_datetime(lm).timestamp()
                except Exception:
                    mtime = 0.0
            files.append(FileEntry(path=rel, size=size, mtime=mtime, etag=etag))
        return files, subdirs

    async def list(self, path: str = "/") -> AsyncIterator[FileEntry]:
        """Breadth-first enumeration. Yields all files; recurses into subdirs.

        Auth errors (401/403) raise immediately; per-subdir transient errors
        are logged and skipped.
        """
        queue: list[str] = [path.strip("/") or ""]
        seen: set[str] = set()
        auth_failed = False
        while queue:
            rel_dir = queue.pop(0)
            if rel_dir in seen:
                continue
            seen.add(rel_dir)
            try:
                root_el = await self._propfind(rel_dir)
            except UpstreamAuthError:
                # propagate immediately
                raise
            except UpstreamError as e:
                log.warning("PROPFIND failed for %s: %s", rel_dir, e)
                continue
            files, subdirs = self._parse_responses(root_el, rel_dir)
            for f in files:
                yield f
            for sd in subdirs:
                if sd not in seen:
                    queue.append(sd)

    async def open_range(self, path: str, start: int, end: int | None) -> AsyncIterator[bytes]:
        client = await self._ensure_client()
        url = self._file_url(path)
        rng = f"bytes={start}-{end}" if end is not None else f"bytes={start}-"
        try:
            async with client.stream("GET", url, headers={"Range": rng}) as r:
                if r.status_code in (401, 403):
                    raise UpstreamAuthError(f"upstream {r.status_code}")
                if r.status_code >= 400:
                    raise UpstreamError(f"upstream {r.status_code}")
                async for chunk in r.aiter_bytes(chunk_size=64 * 1024):
                    yield chunk
        except httpx.HTTPError as e:
            raise UpstreamError(str(e))

    async def open_full(self, path: str) -> AsyncIterator[bytes]:
        client = await self._ensure_client()
        url = self._file_url(path)
        try:
            async with client.stream("GET", url) as r:
                if r.status_code in (401, 403):
                    raise UpstreamAuthError(f"upstream {r.status_code}")
                if r.status_code >= 400:
                    raise UpstreamError(f"upstream {r.status_code}")
                async for chunk in r.aiter_bytes(chunk_size=64 * 1024):
                    yield chunk
        except httpx.HTTPError as e:
            raise UpstreamError(str(e))

    async def ping(self) -> None:
        client = await self._ensure_client()
        prefix = self.root_path.rstrip("/")
        url = f"{self.base_url}{prefix}/" if prefix else f"{self.base_url}/"
        try:
            r = await client.request("PROPFIND", url, headers={"Depth": "0"})
            if r.status_code in (401, 403):
                raise UpstreamAuthError("auth failed")
            if r.status_code >= 400:
                raise UpstreamError(f"HTTP {r.status_code}")
        except httpx.HTTPError as e:
            raise UpstreamError(str(e))
