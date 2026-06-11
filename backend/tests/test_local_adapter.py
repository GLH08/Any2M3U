import sys

import pytest
from any2m3u.scanner.local import LocalAdapter


needs_symlink = pytest.mark.skipif(
    sys.platform == "win32",
    reason="symlinks require SeCreateSymbolicLinkPrivilege on Windows",
)


@pytest.mark.asyncio
async def test_list_basic(tmp_path):
    (tmp_path / "Movies").mkdir()
    (tmp_path / "Movies" / "a.mp4").write_bytes(b"x")
    (tmp_path / "Movies" / "b.mkv").write_bytes(b"y")
    (tmp_path / "Movies" / "note.txt").write_text("hi")
    a = LocalAdapter(str(tmp_path))
    paths = sorted([e["path"] async for e in a.list()])
    assert paths == ["Movies/a.mp4", "Movies/b.mkv", "Movies/note.txt"]


@pytest.mark.asyncio
async def test_list_skips_dotfiles(tmp_path):
    (tmp_path / ".hidden").mkdir()
    (tmp_path / ".hidden" / "x.mp4").write_bytes(b"x")
    (tmp_path / "visible.mp4").write_bytes(b"x")
    a = LocalAdapter(str(tmp_path))
    paths = [e["path"] async for e in a.list()]
    assert paths == ["visible.mp4"]


@needs_symlink
@pytest.mark.asyncio
async def test_list_skips_symlinks(tmp_path):
    target = tmp_path / "real.mp4"
    target.write_bytes(b"x")
    (tmp_path / "link.mp4").symlink_to(target)
    a = LocalAdapter(str(tmp_path))
    paths = [e["path"] async for e in a.list()]
    assert paths == ["real.mp4"]


@pytest.mark.asyncio
async def test_path_traversal_blocked(tmp_path):
    (tmp_path / "ok.mp4").write_bytes(b"x")
    a = LocalAdapter(str(tmp_path))
    with pytest.raises(PermissionError):
        _, gen = await a.open_range("../etc/passwd", 0, 10)
        async for _ in gen:
            pass


@pytest.mark.asyncio
async def test_open_range(tmp_path):
    f = tmp_path / "f.bin"
    f.write_bytes(b"0123456789")
    a = LocalAdapter(str(tmp_path))
    chunks = []
    supported, gen = await a.open_range("f.bin", 2, 5)
    assert supported is True
    async for c in gen:
        chunks.append(c)
    assert b"".join(chunks) == b"2345"


@pytest.mark.asyncio
async def test_list_propagates_worker_exception(tmp_path):
    """If the worker thread that drives the file walk raises, the async
    generator should re-raise — not silently produce a partial stream."""
    from unittest.mock import patch
    a = LocalAdapter(str(tmp_path))
    (tmp_path / "ok.mp4").write_bytes(b"x")

    def boom(start):
        raise OSError("simulated EIO")
        yield  # pragma: no cover

    with patch.object(a, "_iter", boom):
        gen = a.list()
        with pytest.raises(OSError, match="simulated EIO"):
            async for _ in gen:
                pass
