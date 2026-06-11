from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from ..deps import current_user, db_session
from ..models import ScanCache, Source, User

router = APIRouter(prefix="/api/scan", tags=["scan"])


@router.get("/status")
async def global_status(_: User = Depends(current_user), s: AsyncSession = Depends(db_session)):
    total = (await s.execute(select(func.count()).select_from(Source))).scalar_one()
    scanning = (await s.execute(
        select(func.count()).select_from(Source).where(Source.last_scan_status == "running")
    )).scalar_one()
    last_pass = (await s.execute(select(func.max(ScanCache.scanned_at)))).scalar_one()
    return {"sources_total": total, "sources_scanning": scanning, "last_full_pass_at": last_pass}
