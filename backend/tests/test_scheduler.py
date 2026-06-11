import pytest
from any2m3u.scheduler import (
    _ensure_scheduler, _scheduler, add_job_for_source, remove_job_for_source,
)


@pytest.fixture(autouse=True)
async def _reset_scheduler():
    """Reset the global scheduler before and after each test.

    The scheduler is bound to the test's event loop, so the teardown must run
    inside the same loop. We also clear the module-global so the next test
    starts with a clean slate.
    """
    yield
    sched = _scheduler
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
    # the previous job should be removed; no new one added
    assert sched.get_job("scan-44") is None
