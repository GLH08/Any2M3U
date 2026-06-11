from __future__ import annotations
import asyncio
import os
import posixpath
import queue
from pathlib import Path
from typing import AsyncIterator, Iterator
from ..m3u.filters import FileEntry
from .base import UpstreamError


_SENTINEL: object = object()


class LocalAdapter:
    """Reads a local directory as a SourceAdapter. Path-traversal safe."""

    def __init__(self, root: str):
        self.root = Path(root).resolve()
        if not self.root.exists():
            raise UpstreamError(f"Local root does not exist: {self.root}")
        if not self.root.is_dir():
            raise UpstreamError(f"Local root is not a directory: {self.root}")

    def _resolve(self, path: str) -> Path:
        """Normalize and resolve; reject anything that escapes the root."""
        norm = posixpath.normpath(path).lstrip("/")
        full = (self.root / norm).resolve()
        try:
            full.relative_to(self.root)
        except ValueError:
            raise PermissionError(f"Path escapes root: {path}")
        return full

    async def list(self, path: str = "/") -> AsyncIterator[FileEntry]:
        start = self._resolve(path)
        q: queue.Queue[FileEntry | object] = queue.Queue()
        loop = asyncio.get_running_loop()

        def _pump() -> None:
            err: BaseException | None = None
            try:
                for entry in self._iter(start):
                    loop.call_soon_threadsafe(q.put, entry)
            except BaseException as e:  # noqa: BLE001
                err = e
            finally:
                loop.call_soon_threadsafe(
                    q.put, err if err is not None else _SENTINEL
                )

        loop.run_in_executor(None, _pump)
        while True:
            item = await loop.run_in_executor(None, q.get)
            if item is _SENTINEL:
                return
            if isinstance(item, BaseException):
                raise item
            yield item  # type: ignore[misc]

    def _iter(self, start: Path) -> Iterator[FileEntry]:
        """Walk `start` and yield FileEntry rows lazily.

        Yielding per file keeps memory bounded even for trees with
        millions of entries; the consumer (scan engine) writes to JSONL
        as entries arrive.
        """
        for dirpath, dirnames, filenames in os.walk(start, followlinks=False):
            # Prune dotfile dirs and symlink dirs in-place
            dirnames[:] = [
                d for d in dirnames
                if not d.startswith(".") and not (Path(dirpath) / d).is_symlink()
            ]
            for fn in filenames:
                if fn.startswith("."):
                    continue
                p = Path(dirpath) / fn
                if p.is_symlink() or not p.is_file():
                    continue
                rel = p.relative_to(self.root).as_posix()
                try:
                    st = p.stat()
                except OSError:
                    continue
                yield FileEntry(path=rel, size=st.st_size, mtime=st.st_mtime)

    async def open_range(self, path: str, start: int, end: int | None) -> tuple[bool, AsyncIterator[bytes]]:
        """Return (range_supported, iterator). Local files always honor Range."""
        async def _gen() -> AsyncIterator[bytes]:
            full = self._resolve(path)
            if not full.is_file():
                raise FileNotFoundError(path)
            import aiofiles
            async with aiofiles.open(full, "rb") as f:
                await f.seek(start)
                remaining = (end - start + 1) if end is not None else None
                chunk = 64 * 1024
                while True:
                    if remaining is not None and remaining <= 0:
                        break
                    size = chunk if remaining is None else min(chunk, remaining)
                    data = await f.read(size)
                    if not data:
                        break
                    if remaining is not None:
                        remaining -= len(data)
                    yield data
        return (True, _gen())

    async def open_full(self, path: str) -> AsyncIterator[bytes]:
        _, gen = await self.open_range(path, 0, None)
        async for c in gen:
            yield c

    async def ping(self) -> None:
        if not self.root.exists():
            raise UpstreamError("root missing")

    async def aclose(self) -> None:
        # No persistent resources
        return
