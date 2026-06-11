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


async def register_all() -> None:
    """Register a cron job for every enabled source that has a refresh_cron."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
        _scheduler.start()
    for job in list(_scheduler.get_jobs()):
        job.remove()
    sm = get_sessionmaker()
    async with sm() as s:
        rows = (await s.execute(
            select(Source).where(Source.enabled == 1)
        )).scalars().all()
        for src in rows:
            if not src.refresh_cron:
                continue
            try:
                trig = _parse_cron(src.refresh_cron)
            except Exception as e:
                log.warning("invalid cron for source %s: %s", src.id, e)
                continue
            _scheduler.add_job(scan, trig, args=[src.id],
                              id=f"scan-{src.id}", replace_existing=True)


def shutdown() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
