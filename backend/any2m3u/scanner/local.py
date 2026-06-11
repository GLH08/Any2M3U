from __future__ import annotations
import asyncio
import os
import posixpath
from pathlib import Path
from typing import AsyncIterator
from ..m3u.filters import FileEntry
from .base import UpstreamError


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
        for entry in await asyncio.to_thread(self._walk, start):
            yield entry

    def _walk(self, start: Path) -> list[FileEntry]:
        results: list[FileEntry] = []
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
                results.append(FileEntry(path=rel, size=st.st_size, mtime=st.st_mtime))
        return results

    async def open_range(self, path: str, start: int, end: int | None) -> AsyncIterator[bytes]:
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

    async def open_full(self, path: str) -> AsyncIterator[bytes]:
        async for c in self.open_range(path, 0, None):
            yield c

    async def ping(self) -> None:
        if not self.root.exists():
            raise UpstreamError("root missing")

    async def aclose(self) -> None:
        # No persistent resources
        return
