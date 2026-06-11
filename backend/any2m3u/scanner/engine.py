from __future__ import annotations
import asyncio
import hashlib
import json
import logging
import shutil
from pathlib import Path
from typing import Any
from sqlalchemy import select
from ..config import get_settings
from ..db import get_sessionmaker
from ..m3u.filters import FileEntry
from ..models import ScanCache, Source
from ..utils.dates import utcnow_iso
from .base import UpstreamError
from .local import LocalAdapter
from .webdav import WebDAVAdapter

log = logging.getLogger(__name__)

# In-memory state
_progress: dict[int, int] = {}
_index: dict[int, dict[str, FileEntry]] = {}
_sema = asyncio.Semaphore(1)

# Flat global map for O(1) proxy lookup by entry id.
# Populated on every successful scan and on load_all_indexes().
_eid_to_entry: dict[str, tuple[int, FileEntry]] = {}


def is_index_loaded(source_id: int) -> bool:
    return source_id in _index


def load_index(source_id: int) -> dict[str, FileEntry]:
    return _index.get(source_id, {})


def lookup_entry(eid: str) -> tuple[int, FileEntry] | None:
    """O(1) lookup of (source_id, entry) by entry id. Returns None if not found."""
    return _eid_to_entry.get(eid)


def _rebuild_global_index() -> None:
    """Recompute _eid_to_entry from the per-source _index dicts.

    Called after a scan completes and during load_all_indexes.
    """
    new_map: dict[str, tuple[int, FileEntry]] = {}
    for sid, idx in _index.items():
        for eid, entry in idx.items():
            new_map[eid] = (sid, entry)
    _eid_to_entry.clear()
    _eid_to_entry.update(new_map)


def get_progress(source_id: int) -> int:
    return _progress.get(source_id, 0)


def remove_source_from_index(source_id: int) -> None:
    """Drop a source's entries from both _index and _eid_to_entry."""
    _index.pop(source_id, None)
    _progress.pop(source_id, None)
    _rebuild_global_index()


def entry_id(source_id: int, path: str) -> str:
    return hashlib.sha1(f"{source_id}:{path}".encode("utf-8")).hexdigest()[:32]


def build_adapter(source: Source):
    """Construct the appropriate SourceAdapter for a Source row."""
    cfg = json.loads(source.config_json)
    if source.type == "local":
        return LocalAdapter(cfg["path"])
    if source.type == "webdav":
        return WebDAVAdapter(
            base_url=cfg["url"],
            username=cfg["username"],
            password=cfg["password"],
            root_path=cfg.get("root_path", "/"),
            verify_tls=cfg.get("verify_tls", True),
        )
    raise UpstreamError(f"Unknown source type: {source.type}")


async def _mark_status(source_id: int, status: str, error: str | None = None) -> None:
    sm = get_sessionmaker()
    async with sm() as s:
        src = await s.get(Source, source_id)
        if src is None:
            return
        src.last_scan_status = status
        if error is not None:
            src.last_error = error[:2000]
        if status in ("success", "failed"):
            src.last_scan_at = utcnow_iso()
        await s.commit()


async def scan(source_id: int) -> None:
    """Run a full scan for a single source, with a simple mutex and progress reporting."""
    async with _sema:
        await _mark_status(source_id, "running")
        sm = get_sessionmaker()

        settings = get_settings()
        scan_dir: Path = settings.scan_dir
        scan_dir.mkdir(parents=True, exist_ok=True)

        final_path = scan_dir / f"{source_id}.jsonl"
        tmp_path = final_path.with_suffix(".jsonl.tmp")

        # Disk pre-check
        try:
            usage = shutil.disk_usage(scan_dir)
            if usage.free < 10 * 1024 * 1024:
                raise UpstreamError("less than 10MB free in scan dir")
        except OSError as e:
            await _mark_status(source_id, "failed", f"disk check: {e}")
            return

        count = 0
        total = 0
        new_index: dict[str, FileEntry] = {}
        adapter = None
        try:
            async with sm() as s:
                src = await s.get(Source, source_id)
                if src is None:
                    return
                adapter = build_adapter(src)

            import aiofiles
            async with aiofiles.open(tmp_path, "w", encoding="utf-8") as f:
                async for entry in adapter.list():
                    eid = entry_id(source_id, entry["path"])
                    new_index[eid] = entry
                    await f.write(json.dumps(entry) + "\n")
                    count += 1
                    total += entry["size"]
                    if count % 200 == 0:
                        _progress[source_id] = count
            tmp_path.replace(final_path)
        except Exception as e:
            log.exception("scan failed for source %s", source_id)
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except OSError:
                pass
            await _mark_status(source_id, "failed", repr(e))
            return
        finally:
            if adapter is not None:
                try:
                    await adapter.aclose()
                except Exception:
                    pass

        _index[source_id] = new_index
        _progress[source_id] = count
        _rebuild_global_index()

        async with sm() as s:
            existing = await s.get(ScanCache, source_id)
            if existing is None:
                s.add(ScanCache(
                    source_id=source_id,
                    scanned_at=utcnow_iso(),
                    entry_count=count,
                    total_bytes=total,
                    entries_jsonl_path=str(final_path),
                ))
            else:
                existing.scanned_at = utcnow_iso()
                existing.entry_count = count
                existing.total_bytes = total
                existing.entries_jsonl_path = str(final_path)
            await s.commit()

        await _mark_status(source_id, "success")


async def load_all_indexes() -> None:
    """Rebuild in-memory indexes for all sources that have a scan cache."""
    sm = get_sessionmaker()
    async with sm() as s:
        rows = (await s.execute(select(ScanCache))).scalars().all()
        for r in rows:
            p = Path(r.entries_jsonl_path)
            if not p.exists():
                continue
            idx: dict[str, FileEntry] = {}
            try:
                with p.open("r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            e = json.loads(line)
                            eid = entry_id(r.source_id, e["path"])
                            idx[eid] = e
                        except (ValueError, KeyError) as exc:
                            log.warning("skipping corrupt cache line in %s: %s", p, exc)
                            continue
                _index[r.source_id] = idx
            except OSError:
                continue
    _rebuild_global_index()


async def cleanup_tmp_files() -> None:
    """Remove leftover *.jsonl.tmp from previous crashes."""
    settings = get_settings()
    scan_dir: Path = settings.scan_dir
    if not scan_dir.exists():
        return
    for p in scan_dir.glob("*.jsonl.tmp"):
        try:
            p.unlink()
        except OSError:
            pass
