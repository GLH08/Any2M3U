"""Scheduler: hot-reload cron jobs on source create/update/delete + orphan cleanup."""
import pytest
from any2m3u.scheduler import (
    _ensure_scheduler, add_job_for_source, remove_job_for_source,
    register_all, shutdown,
)


@pytest.fixture(autouse=True)
async def _reset_scheduler():
    yield
    sched = __import__("any2m3u.scheduler", fromlist=["_scheduler"])._scheduler
    if sched is not None and sched.running:
        try:
            sched.shutdown(wait=False)
        except Exception:
            pass
    import any2m3u.scheduler as _mod
    _mod._scheduler = None


@pytest.mark.asyncio
async def test_add_job_then_remove():
    """A cron expression is registered; removal clears the job."""
    add_job_for_source(42, "0 * * * *")
    sched = _ensure_scheduler()
    assert sched.get_job("scan-42") is not None
    remove_job_for_source(42)
    assert sched.get_job("scan-42") is None


@pytest.mark.asyncio
async def test_empty_cron_removes_existing_job():
    """Passing an empty cron should remove the existing job, not add a new one."""
    add_job_for_source(43, "*/5 * * * *")
    sched = _ensure_scheduler()
    assert sched.get_job("scan-43") is not None
    add_job_for_source(43, "")
    assert sched.get_job("scan-43") is None


@pytest.mark.asyncio
async def test_invalid_cron_is_skipped():
    """An invalid cron expression logs and removes any existing job."""
    add_job_for_source(44, "0 * * * *")
    sched = _ensure_scheduler()
    assert sched.get_job("scan-44") is not None
    add_job_for_source(44, "not a cron")
    assert sched.get_job("scan-44") is None


@pytest.mark.asyncio
async def test_register_all_removes_orphan_jobs(tmp_path, monkeypatch):
    """A job whose source no longer exists must be removed at startup."""
    monkeypatch.setenv("ANY2M3U_DATA", str(tmp_path))
    monkeypatch.setenv("ANY2M3U_ADMIN_PASSWORD", "secret123")
    from any2m3u.config import get_settings
    get_settings.cache_clear()
    from any2m3u.db import init_db
    await init_db(tmp_path)

    # Simulate a leftover job for a no-longer-existing source.
    add_job_for_source(999, "0 * * * *")
    sched = _ensure_scheduler()
    assert sched.get_job("scan-999") is not None

    # Empty DB: register_all must GC the orphan.
    await register_all()
    assert sched.get_job("scan-999") is None
