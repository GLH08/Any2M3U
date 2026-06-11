# Any2M3U High-Priority Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply five small, high-value reliability and correctness fixes to Any2M3U: hot-reloadable cron, O(1) eid lookup, streaming local scanner, unified datetime helpers, and password-change session invalidation.

**Architecture:** Backend-only changes; no API surface changes. Each fix is independent but we order them by dependency: utility first, then engine changes that consume it, then API endpoints that depend on engine, then auth.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 async, APScheduler, pytest, httpx, asgi_lifespan.

---

## File Structure

Files modified in this plan (all paths relative to `backend/`):

| File | Change |
|---|---|
| `any2m3u/utils/__init__.py` | **Create** — package marker |
| `any2m3u/utils/dates.py` | **Create** — `parse_utc()`, `utcnow_iso()` |
| `any2m3u/deps.py` | Use `parse_utc` |
| `any2m3u/api/auth.py` | Use `parse_utc`; invalidate other sessions on password change |
| `any2m3u/api/public.py` | Use `parse_utc`; use global eid map |
| `any2m3u/api/sources.py` | Use `parse_utc`; hot-reload cron on create/update/delete |
| `any2m3u/scheduler.py` | New `add_job_for_source()` / `remove_job_for_source()` |
| `any2m3u/scanner/engine.py` | Global `_eid_to_entry`; use `parse_utc` |
| `any2m3u/scanner/local.py` | `_walk` becomes a generator |
| `any2m3u/models.py` | Use `utcnow_iso` for `_now()` |
| `tests/test_auth.py` | Add session-invalidation test |
| `tests/test_scheduler.py` | **Create** — cron hot-reload test |
| `tests/test_scan_engine.py` | Verify global eid map after scan |
| `tests/test_proxy_endpoint.py` | Add test that the linear-lookup codepath still works (sanity) |

---

## Task 1: Add `parse_utc` / `utcnow_iso` utilities

**Files:**
- Create: `backend/any2m3u/utils/__init__.py`
- Create: `backend/any2m3u/utils/dates.py`

- [ ] **Step 1: Create the utils package**

Write `backend/any2m3u/utils/__init__.py` (empty file):

```python
```

- [ ] **Step 2: Write the failing test**

Write `backend/tests/test_dates.py`:

```python
from datetime import datetime, timezone, timedelta
from any2m3u.utils.dates import parse_utc, utcnow_iso


def test_utcnow_iso_is_aware_and_parseable():
    s = utcnow_iso()
    # round-trip: must parse back to the same instant
    parsed = parse_utc(s)
    assert parsed.tzinfo is not None
    assert parsed == datetime.fromisoformat(s)


def test_parse_utc_naive_input_is_treated_as_utc():
    """Old naive isoformat strings from before the timezone fix should still parse."""
    naive = (datetime.now(timezone.utc) - timedelta(days=10)).replace(tzinfo=None).isoformat()
    parsed = parse_utc(naive)
    assert parsed.tzinfo is timezone.utc
    # and it's still in the past
    assert parsed < datetime.now(timezone.utc)


def test_parse_utc_aware_input_unchanged():
    aware = datetime.now(timezone.utc).isoformat()
    parsed = parse_utc(aware)
    assert parsed.tzinfo is timezone.utc
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_dates.py -v`
Expected: `ModuleNotFoundError: No module named 'any2m3u.utils.dates'`

- [ ] **Step 4: Implement `dates.py`**

Write `backend/any2m3u/utils/dates.py`:

```python
from __future__ import annotations
from datetime import datetime, timezone


def parse_utc(s: str) -> datetime:
    """Parse a datetime stored as ISO format.

    Old records (pre-2026 fix) are naive; treat them as UTC. New records are
    timezone-aware. Always returns an aware datetime in UTC.
    """
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def utcnow_iso() -> str:
    """Return the current UTC time as an ISO 8601 string with timezone offset."""
    return datetime.now(timezone.utc).isoformat()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_dates.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add backend/any2m3u/utils backend/tests/test_dates.py
git commit -m "feat(utils): add parse_utc / utcnow_iso helpers"
```

---

## Task 2: Apply `parse_utc` across existing modules

**Files:**
- Modify: `backend/any2m3u/deps.py`
- Modify: `backend/any2m3u/api/auth.py`
- Modify: `backend/any2m3u/api/public.py`
- Modify: `backend/any2m3u/api/sources.py`
- Modify: `backend/any2m3u/scanner/engine.py`
- Modify: `backend/any2m3u/models.py`

- [ ] **Step 1: Update `models.py` `_now()`**

In `backend/any2m3u/models.py`, replace:

```python
def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
```

with:

```python
from .utils.dates import utcnow_iso

def _now() -> str:
    return utcnow_iso()
```

Remove `from datetime import datetime, timezone` if no other usage remains. (It may still be used for type hints — check first.)

- [ ] **Step 2: Update `deps.py`**

In `backend/any2m3u/deps.py`, replace:

```python
from datetime import datetime, timezone, timedelta
```

with:

```python
from datetime import timedelta
```

Replace the body of `current_user` that does the expiry check:

```python
    expires = datetime.fromisoformat(row.expires_at)
    # Handle old naive isoformat strings from before the utcnow→now(timezone.utc) fix
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="session expired")
```

with:

```python
    from .utils.dates import parse_utc, utcnow_iso
    if parse_utc(row.expires_at) < parse_utc(utcnow_iso()):
        raise HTTPException(status_code=401, detail="session expired")
```

Replace the sliding-renewal line:

```python
    row.expires_at = (datetime.now(timezone.utc) + SESSION_TTL).isoformat()
```

with:

```python
    row.expires_at = (parse_utc(utcnow_iso()) + SESSION_TTL).isoformat()
```

- [ ] **Step 3: Update `auth.py`**

In `backend/any2m3u/api/auth.py`, replace the `from datetime import datetime, timezone` import with `from datetime import timezone` (only used in `login` for `last_login_at`).

Replace the `me` endpoint body — drop the duplicated `_parse_expires` helper entirely. New body:

```python
@router.get("/me")
async def me(
    s: AsyncSession = Depends(db_session),
    session_id: str | None = Cookie(default=None, alias=COOKIE_NAME),
):
    """Return the logged-in user, or signal not-initialized / not-logged-in."""
    from ..utils.dates import parse_utc, utcnow_iso
    res = await s.execute(select(User).limit(1))
    if res.first() is None:
        raise HTTPException(status_code=404, detail={"code": "not_initialized"})

    if session_id:
        row = await s.get(DBSession, session_id)
        if row is not None and parse_utc(row.expires_at) >= parse_utc(utcnow_iso()):
            user = await s.get(User, row.user_id)
            if user is not None:
                row.expires_at = (parse_utc(utcnow_iso()) + SESSION_TTL).isoformat()
                await s.commit()
                return {"username": user.username, "last_login_at": user.last_login_at}

    raise HTTPException(status_code=401, detail="not logged in")
```

Delete the `_parse_expires` helper (lines 60-67).

In `login`, change `user.last_login_at = datetime.now(timezone.utc).isoformat()` to use the helper:

```python
    from ..utils.dates import utcnow_iso
    user.last_login_at = utcnow_iso()
```

(Remove the now-unused `from datetime import datetime, timezone` at the top.)

- [ ] **Step 4: Update `public.py`**

In `backend/any2m3u/api/public.py`, replace the `from datetime import datetime, timezone` import with `from ..utils.dates import parse_utc, utcnow_iso`.

Replace the token-expiry block in `_auth_pull`:

```python
        if row.expires_at:
            exp = datetime.fromisoformat(row.expires_at)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp < datetime.now(timezone.utc):
                raise HTTPException(status_code=401, detail="expired token",
                                    headers={"WWW-Authenticate": _BEARER_CHALLENGE})
        row.last_used_at = datetime.now(timezone.utc).isoformat()
```

with:

```python
        if row.expires_at and parse_utc(row.expires_at) < parse_utc(utcnow_iso()):
            raise HTTPException(status_code=401, detail="expired token",
                                headers={"WWW-Authenticate": _BEARER_CHALLENGE})
        row.last_used_at = utcnow_iso()
```

- [ ] **Step 5: Update `sources.py`**

In `backend/any2m3u/api/sources.py`, replace the `from datetime import datetime, timezone` import with `from ..utils.dates import utcnow_iso`.

Find every `datetime.now(timezone.utc).isoformat()` in this file and replace with `utcnow_iso()`.

- [ ] **Step 6: Update `engine.py`**

In `backend/any2m3u/scanner/engine.py`, replace the `from datetime import datetime, timezone` import with `from ..utils.dates import utcnow_iso`.

Find every `datetime.now(timezone.utc).isoformat()` in this file and replace with `utcnow_iso()`.

- [ ] **Step 7: Run the full test suite to confirm no regression**

Run: `cd backend && uv run pytest -v`
Expected: all 45+ existing tests pass (including the 3 new from Task 1).

- [ ] **Step 8: Commit**

```bash
git add backend/
git commit -m "refactor: replace ad-hoc datetime parsing with parse_utc/utcnow_iso"
```

---

## Task 3: LocalAdapter.list as a true generator

**Files:**
- Modify: `backend/any2m3u/scanner/local.py`

- [ ] **Step 1: Verify existing tests cover the contract**

The existing tests in `backend/tests/test_local_adapter.py` (test_list_basic, test_list_skips_dotfiles, test_list_skips_symlinks) iterate via `async for`. They'll keep passing as long as we preserve the generator semantics. No new test required — the change is to avoid building a list in memory.

- [ ] **Step 2: Refactor `_walk` to a generator**

In `backend/any2m3u/scanner/local.py`, replace `list` (the method):

```python
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
```

with:

```python
    async def list(self, path: str = "/") -> AsyncIterator[FileEntry]:
        start = self._resolve(path)
        async for entry in await asyncio.to_thread(self._iter, start):
            yield entry

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
```

Add `from typing import AsyncIterator, Iterator` at the top (replacing the existing `AsyncIterator` import which only had one type).

- [ ] **Step 3: Run the local-adapter tests**

Run: `cd backend && uv run pytest tests/test_local_adapter.py -v`
Expected: all pass (same behavior, just generator).

- [ ] **Step 4: Run the full test suite**

Run: `cd backend && uv run pytest -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/any2m3u/scanner/local.py
git commit -m "refactor(scanner): make LocalAdapter.list a true generator"
```

---

## Task 4: Global eid → (sid, entry) map for O(1) proxy lookup

**Files:**
- Modify: `backend/any2m3u/scanner/engine.py`
- Modify: `backend/any2m3u/api/public.py`
- Modify: `backend/tests/test_scan_engine.py`

- [ ] **Step 1: Add the global map to `engine.py`**

In `backend/any2m3u/scanner/engine.py`, add a module-level global next to `_index`:

```python
# Flat global map for O(1) proxy lookup by entry id.
# Populated on every successful scan and on load_all_indexes().
_eid_to_entry: dict[str, tuple[int, FileEntry]] = {}
```

Add accessor functions (place them next to `load_index`):

```python
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
```

- [ ] **Step 2: Maintain the map in `scan()` and `load_all_indexes()`**

In `scan()`, after the line:

```python
        _index[source_id] = new_index
        _progress[source_id] = count
```

add:

```python
        _rebuild_global_index()
```

In `load_all_indexes()`, after the loop populates `_index`, add at the end:

```python
    _rebuild_global_index()
```

- [ ] **Step 3: Update `public.py` to use the new lookup**

In `backend/any2m3u/api/public.py`, replace:

```python
from ..scanner.engine import build_adapter, entry_id, _index
```

with:

```python
from ..scanner.engine import build_adapter, entry_id, lookup_entry
```

In the `proxy` endpoint, replace:

```python
    found = None
    for sid, idx in _index.items():
        if id in idx:
            found = (sid, idx[id])
            break
    if found is None:
        raise HTTPException(404, detail={"error": "not_found"})
    sid, entry = found
```

with:

```python
    found = lookup_entry(id)
    if found is None:
        raise HTTPException(404, detail={"error": "not_found"})
    sid, entry = found
```

- [ ] **Step 4: Add a test that the global map is populated after a scan**

In `backend/tests/test_scan_engine.py`, add at the end:

```python
@pytest.mark.asyncio
async def test_global_eid_map_populated_after_scan(tmp_path):
    """lookup_entry() should return (sid, entry) after a successful scan."""
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
    now_iso = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
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
    # And the index is gone — unknown ids are None, not exceptions
    assert lookup_entry("deadbeef" * 8) is None
```

(Note: the conftest autouse fixture `engine._index.clear()` should also clear `_eid_to_entry`. Update conftest below in Step 5.)

- [ ] **Step 5: Update conftest to also clear `_eid_to_entry`**

In `backend/tests/conftest.py`, update the `_clear_scanner_state` fixture:

```python
@pytest.fixture(autouse=True)
def _clear_scanner_state():
    """Reset the scanner engine's in-memory indexes between tests."""
    from any2m3u.scanner import engine
    engine._index.clear()
    engine._progress.clear()
    if hasattr(engine, "_eid_to_entry"):
        engine._eid_to_entry.clear()
    yield
    engine._index.clear()
    engine._progress.clear()
    if hasattr(engine, "_eid_to_entry"):
        engine._eid_to_entry.clear()
```

- [ ] **Step 6: Run tests**

Run: `cd backend && uv run pytest -v`
Expected: all pass — including the 4 existing proxy tests and the new global-map test.

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "perf(proxy): O(1) eid lookup via global index map"
```

---

## Task 5: Cron hot-reload on source create/update/delete

**Files:**
- Modify: `backend/any2m3u/scheduler.py`
- Modify: `backend/any2m3u/api/sources.py`
- Create: `backend/tests/test_scheduler.py`

- [ ] **Step 1: Refactor `scheduler.py`**

In `backend/any2m3u/scheduler.py`, add two new functions and keep `register_all` (it remains useful for startup):

```python
from __future__ import annotations
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from .db import get_sessionmaker
from .models import Source
from .scanner.engine import scan
from .utils.dates import parse_utc

log = logging.getLogger(__name__)
_scheduler: AsyncIOScheduler | None = None


def _parse_cron(expr: str) -> CronTrigger:
    parts = expr.split()
    if len(parts) != 5:
        raise ValueError(f"cron must have 5 fields, got: {expr!r}")
    return CronTrigger(
        minute=parts[0], hour=parts[1], day=parts[2],
        month=parts[3], day_of_week=parts[4],
    )


def _ensure_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
        _scheduler.start()
    return _scheduler


def add_job_for_source(source_id: int, cron_expr: str) -> None:
    """Install (or replace) a cron job for the given source.

    If cron_expr is empty or invalid, any existing job for this source is
    removed and the call is a no-op.
    """
    sched = _ensure_scheduler()
    job_id = f"scan-{source_id}"
    if not cron_expr:
        if sched.get_job(job_id):
            sched.remove_job(job_id)
        return
    try:
        trig = _parse_cron(cron_expr)
    except Exception as e:
        log.warning("invalid cron for source %s (%r): %s", source_id, cron_expr, e)
        if sched.get_job(job_id):
            sched.remove_job(job_id)
        return
    sched.add_job(scan, trig, args=[source_id],
                  id=job_id, replace_existing=True)


def remove_job_for_source(source_id: int) -> None:
    sched = _ensure_scheduler()
    job_id = f"scan-{source_id}"
    if sched.get_job(job_id):
        sched.remove_job(job_id)


async def register_all() -> None:
    """Register a cron job for every enabled source that has a refresh_cron."""
    sm = get_sessionmaker()
    async with sm() as s:
        rows = (await s.execute(
            select(Source).where(Source.enabled == 1)
        )).scalars().all()
        for src in rows:
            if not src.refresh_cron:
                continue
            add_job_for_source(src.id, src.refresh_cron)


def shutdown() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
```

- [ ] **Step 2: Hook into source create/update/delete**

In `backend/any2m3u/api/sources.py`:

- Add the import: `from ..scheduler import add_job_for_source, remove_job_for_source`
- In `create_source` (after `await s.refresh(src)`): call `add_job_for_source(src.id, body.refresh_cron) if body.enabled else None`
- In `update_source`, after `await s.refresh(src)`: if `body.refresh_cron is not None or body.enabled is not None`, call `add_job_for_source(src.id, src.refresh_cron) if src.enabled else None` (re-evaluate the *current* row state)
- In `delete_source`, before `await s.delete(src)`: call `remove_job_for_source(sid)`

For `update_source`, the patch should look like:

```python
@router.patch("/{sid}", response_model=SourceOut)
async def update_source(sid: int, body: SourceUpdate, _: User = Depends(current_user), s: AsyncSession = Depends(db_session)):
    src = await s.get(Source, sid)
    if not src: raise HTTPException(404, "not found")
    if body.name is not None: src.name = body.name
    if body.config is not None: src.config_json = json.dumps(body.config)
    if body.group_by_dir is not None: src.group_by_dir = 1 if body.group_by_dir else 0
    if body.refresh_cron is not None: src.refresh_cron = body.refresh_cron
    if body.enabled is not None: src.enabled = 1 if body.enabled else 0
    await s.commit(); await s.refresh(src)
    # Re-evaluate scheduler state for this source
    if src.enabled and src.refresh_cron:
        add_job_for_source(src.id, src.refresh_cron)
    else:
        remove_job_for_source(src.id)
    return _to_out(src)
```

For `create_source`:

```python
@router.post("", response_model=SourceOut, status_code=201)
async def create_source(body: SourceCreate, _: User = Depends(current_user), s: AsyncSession = Depends(db_session)):
    src = Source(
        name=body.name, type=body.type, config_json=json.dumps(body.config),
        group_by_dir=1 if body.group_by_dir else 0,
        refresh_cron=body.refresh_cron, enabled=1 if body.enabled else 0,
        created_at=utcnow_iso(),
    )
    s.add(src); await s.commit(); await s.refresh(src)
    if src.enabled and src.refresh_cron:
        add_job_for_source(src.id, src.refresh_cron)
    return _to_out(src)
```

For `delete_source`:

```python
@router.delete("/{sid}", status_code=204)
async def delete_source(sid: int, _: User = Depends(current_user), s: AsyncSession = Depends(db_session)):
    src = await s.get(Source, sid)
    if not src: raise HTTPException(404, "not found")
    remove_job_for_source(sid)
    await s.delete(src); await s.commit()
```

- [ ] **Step 3: Add cron hot-reload test**

Create `backend/tests/test_scheduler.py`:

```python
import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from any2m3u.scheduler import (
    _ensure_scheduler, add_job_for_source, remove_job_for_source, shutdown,
)


@pytest.fixture(autouse=True)
def _reset_scheduler():
    shutdown()
    yield
    shutdown()


def test_add_job_then_remove():
    """A cron expression is registered; removal clears the job."""
    add_job_for_source(42, "0 * * * *")
    sched = _ensure_scheduler()
    assert sched.get_job("scan-42") is not None
    remove_job_for_source(42)
    assert sched.get_job("scan-42") is None


def test_empty_cron_removes_existing_job():
    """Passing an empty cron should remove the existing job, not add a new one."""
    add_job_for_source(43, "*/5 * * * *")
    sched = _ensure_scheduler()
    assert sched.get_job("scan-43") is not None
    add_job_for_source(43, "")
    assert sched.get_job("scan-43") is None


def test_invalid_cron_is_skipped():
    """An invalid cron expression logs and removes any existing job."""
    add_job_for_source(44, "0 * * * *")
    sched = _ensure_scheduler()
    assert sched.get_job("scan-44") is not None
    add_job_for_source(44, "not a cron")
    # the previous job should be removed; no new one added
    assert sched.get_job("scan-44") is None
```

- [ ] **Step 4: Run tests**

Run: `cd backend && uv run pytest -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/
git commit -m "feat(scheduler): hot-reload cron jobs on source create/update/delete"
```

---

## Task 6: Password change invalidates other sessions

**Files:**
- Modify: `backend/any2m3u/api/auth.py`
- Modify: `backend/tests/test_auth.py`

- [ ] **Step 1: Add the cleanup to `change_password`**

In `backend/any2m3u/api/auth.py`, change the signature of `change_password` to also receive the current `session_id` cookie, then delete all other Session rows for the user:

```python
@router.post("/password")
async def change_password(
    body: PasswordBody,
    user: User = Depends(current_user),
    s: AsyncSession = Depends(db_session),
    session_id: str | None = Cookie(default=None, alias=COOKIE_NAME),
):
    if not verify_password(body.old, user.password_hash):
        raise HTTPException(status_code=400, detail="wrong current password")
    if len(body.new) < 8:
        raise HTTPException(status_code=400, detail="password must be at least 8 chars")
    user.password_hash = hash_password(body.new)
    # Invalidate every other session for this user; keep the current one
    # so the user isn't logged out by their own password change.
    from sqlalchemy import delete, select
    stmt = delete(DBSession).where(
        DBSession.user_id == user.id,
        DBSession.id != session_id,
    )
    await s.execute(stmt)
    await s.commit()
    return {"ok": True}
```

- [ ] **Step 2: Add a regression test**

In `backend/tests/test_auth.py`, add at the end:

```python
@pytest.mark.asyncio
async def test_password_change_invalidates_other_sessions(tmp_path, monkeypatch):
    """Changing the password should kill all other sessions for the same user."""
    monkeypatch.setenv("ANY2M3U_DATA", str(tmp_path))
    monkeypatch.setenv("ANY2M3U_ADMIN_PASSWORD", "secret123")
    app = create_app()
    async with LifespanManager(app):
        # Two clients, both login as admin
        c1 = AsyncClient(transport=ASGITransport(app=app), base_url="http://t")
        c2 = AsyncClient(transport=ASGITransport(app=app), base_url="http://t")
        await c1.__aenter__()
        await c2.__aenter__()
        try:
            r1 = await c1.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
            assert r1.status_code == 200
            r2 = await c2.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
            assert r2.status_code == 200
            # Both /me work
            assert (await c1.get("/api/auth/me")).status_code == 200
            assert (await c2.get("/api/auth/me")).status_code == 200
            # c1 changes password
            cp = await c1.post("/api/auth/password", json={"old": "secret123", "new": "newpass99"})
            assert cp.status_code == 200
            # c1 (current) still works
            assert (await c1.get("/api/auth/me")).status_code == 200
            # c2 is invalidated
            assert (await c2.get("/api/auth/me")).status_code == 401
        finally:
            await c1.__aexit__(None, None, None)
            await c2.__aexit__(None, None, None)
```

- [ ] **Step 3: Run tests**

Run: `cd backend && uv run pytest -v`
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add backend/
git commit -m "fix(auth): invalidating other sessions on password change"
```

---

## Task 7: Final verification

- [ ] **Step 1: Run the full test suite**

Run: `cd backend && uv run pytest -v`
Expected: 50+ tests pass; 0 failures.

- [ ] **Step 2: Confirm no stray references**

Run: `cd backend && grep -rn "datetime.utcnow\|_parse_expires\|for sid, idx in _index" any2m3u/`
Expected: no matches (the `datetime.utcnow` migration and the linear proxy lookup are both gone).

- [ ] **Step 3: Commit any final cleanup (if needed)**

If step 2 found matches, fix them. Otherwise no commit.

- [ ] **Step 4: Push**

```bash
git push
```

---

## Self-Review

1. **Spec coverage:** Items #1 (cron hot-reload) → Task 5; #2 (ScanRegistry) → not in this plan (explicitly out of scope); #3 (eid map) → Task 4; #4 (parse_utc) → Tasks 1+2; #5 (LocalAdapter generator) → Task 3; #10 (password invalidation) → Task 6. All 5 in-scope items covered.

2. **Placeholder scan:** No "TBD" or vague "add validation" steps. Every code change shows the full code.

3. **Type consistency:** `lookup_entry`, `add_job_for_source`, `remove_job_for_source`, `parse_utc`, `utcnow_iso` are all defined before use. The conftest `hasattr` guard for `_eid_to_entry` handles the case where Task 4's test runs after Task 4 lands but a partial test run in between is still safe.
