from __future__ import annotations
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from .db import get_sessionmaker
from .models import Source
from .scanner.engine import scan

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
