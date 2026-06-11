import json
import os
import pytest
from datetime import datetime, timezone
from any2m3u.db import init_db, get_sessionmaker
from any2m3u.models import Source
from any2m3u.scanner.engine import scan, load_index, is_index_loaded


@pytest.mark.asyncio
async def test_scan_local_source(tmp_path):
    data = tmp_path / "data"; data.mkdir()
    (tmp_path / "media").mkdir()
    (tmp_path / "media" / "a.mp4").write_bytes(b"x" * 10)
    (tmp_path / "media" / "b.mkv").write_bytes(b"y" * 20)

    # Force the settings cache to read our tempdir (conftest clears the cache
    # only around the test, not before get_settings() is first read).
    os.environ["ANY2M3U_DATA"] = str(data)
    from any2m3u.config import get_settings
    get_settings.cache_clear()

    await init_db(data)
    sm = get_sessionmaker()
    now = datetime.now(timezone.utc).isoformat()
    async with sm() as s:
        src = Source(name="m", type="local", config_json=json.dumps({"path": str(tmp_path / "media")}), created_at=now)
        s.add(src)
        await s.commit()
        await s.refresh(src)
        sid = src.id

    await scan(sid)
    cache_path = data / "scan" / f"{sid}.jsonl"
    assert cache_path.exists()
    lines = cache_path.read_text().strip().split("\n")
    assert len(lines) == 2
    assert is_index_loaded(sid)
    entries = load_index(sid)
    assert sum(e["size"] for e in entries.values()) == 30


@pytest.mark.asyncio
async def test_scan_keeps_old_on_failure(tmp_path):
    data = tmp_path / "data"; data.mkdir()
    os.environ["ANY2M3U_DATA"] = str(data)
    from any2m3u.config import get_settings
    get_settings.cache_clear()

    await init_db(data)
    sm = get_sessionmaker()
    now = datetime.now(timezone.utc).isoformat()
    # path that does not exist
    async with sm() as s:
        src = Source(name="x", type="local", config_json=json.dumps({"path": str(tmp_path / "missing")}), created_at=now)
        s.add(src); await s.commit(); await s.refresh(src)
        sid = src.id

    await scan(sid)
    async with sm() as s:
        src = (await s.get(Source, sid))
        assert src.last_scan_status == "failed"
        assert not (data / "scan" / f"{sid}.jsonl").exists()


@pytest.mark.asyncio
async def test_global_eid_map_populated_after_scan(tmp_path):
    """lookup_entry() should return (sid, entry) after a successful scan."""
    from datetime import datetime, timezone
    from any2m3u.scanner.engine import lookup_entry, entry_id
    data = tmp_path / "data"; data.mkdir()
    media = tmp_path / "media"
    media.mkdir()
    (media / "f.mp4").write_bytes(b"x")
    os.environ["ANY2M3U_DATA"] = str(data)
    from any2m3u.config import get_settings
    get_settings.cache_clear()
    await init_db(data)
    sm = get_sessionmaker()
    now_iso = datetime.now(timezone.utc).isoformat()
    async with sm() as s:
        src = Source(name="m", type="local",
                     config_json=json.dumps({"path": str(media)}), created_at=now_iso)
        s.add(src); await s.commit(); await s.refresh(src)
        sid = src.id

    await scan(sid)
    eid = entry_id(sid, "f.mp4")
    found = lookup_entry(eid)
    assert found is not None
    assert found[0] == sid
    assert found[1]["path"] == "f.mp4"
    # unknown ids return None, not exceptions
    assert lookup_entry("deadbeef" * 8) is None
