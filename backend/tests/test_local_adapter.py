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
        async for _ in a.open_range("../etc/passwd", 0, 10):
            pass


@pytest.mark.asyncio
async def test_open_range(tmp_path):
    f = tmp_path / "f.bin"
    f.write_bytes(b"0123456789")
    a = LocalAdapter(str(tmp_path))
    chunks = []
    async for c in a.open_range("f.bin", 2, 5):
        chunks.append(c)
    assert b"".join(chunks) == b"2345"
