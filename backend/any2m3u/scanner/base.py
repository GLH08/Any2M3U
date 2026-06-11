from __future__ import annotations
from typing import AsyncIterator, Protocol
from ..m3u.filters import FileEntry  # re-export for scanner consumers


class UpstreamError(Exception):
    """Generic upstream/network failure."""


class UpstreamAuthError(UpstreamError):
    """Upstream rejected our credentials (401/403)."""


class UpstreamRangeNotSupported(UpstreamError):
    """Upstream responded with 405/406/501 to a Range request.

    The caller should retry without Range (and serve 200 with full Content-Length)
    or surface a 4xx to the client.
    """


class SourceAdapter(Protocol):
    """All source adapters must implement this contract."""
    def list(self, path: str = "/") -> AsyncIterator[FileEntry]: ...
    def open_range(self, path: str, start: int, end: int | None) -> AsyncIterator[bytes]: ...
    def open_full(self, path: str) -> AsyncIterator[bytes]: ...
    async def ping(self) -> None: ...
    async def aclose(self) -> None: ...
