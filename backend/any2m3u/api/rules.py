from __future__ import annotations
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..deps import current_user, db_session
from ..models import Rule, Source, User
from ..schemas import RuleCreate, RuleOut, RuleUpdate

router = APIRouter(tags=["rules"])


def _to_out(r: Rule) -> RuleOut:
    return RuleOut(
        id=r.id, source_id=r.source_id, name=r.name,
        include_exts=r.include_exts, exclude_keywords=r.exclude_keywords,
        include_paths=r.include_paths, group_title=r.group_title,
        tpl=r.tpl, logo_dir=r.logo_dir, enabled=bool(r.enabled),
        created_at=r.created_at,
    )


@router.get("/api/sources/{sid}/rules", response_model=list[RuleOut])
async def list_rules(sid: int, _: User = Depends(current_user), s: AsyncSession = Depends(db_session)):
    rows = (await s.execute(select(Rule).where(Rule.source_id == sid).order_by(Rule.id))).scalars().all()
    return [_to_out(r) for r in rows]


@router.post("/api/sources/{sid}/rules", response_model=RuleOut, status_code=201)
async def create_rule(sid: int, body: RuleCreate, _: User = Depends(current_user), s: AsyncSession = Depends(db_session)):
    src = await s.get(Source, sid)
    if not src: raise HTTPException(404, "source not found")
    r = Rule(
        source_id=sid, name=body.name, include_exts=body.include_exts,
        exclude_keywords=body.exclude_keywords, include_paths=body.include_paths,
        group_title=body.group_title, tpl=body.tpl, logo_dir=body.logo_dir,
        enabled=1 if body.enabled else 0,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    s.add(r); await s.commit(); await s.refresh(r)
    return _to_out(r)


@router.patch("/api/rules/{rid}", response_model=RuleOut)
async def update_rule(rid: int, body: RuleUpdate, _: User = Depends(current_user), s: AsyncSession = Depends(db_session)):
    r = await s.get(Rule, rid)
    if not r: raise HTTPException(404, "not found")
    for fld in ("name", "include_exts", "exclude_keywords", "include_paths",
                "group_title", "tpl", "logo_dir"):
        v = getattr(body, fld)
        if v is not None: setattr(r, fld, v)
    if body.enabled is not None: r.enabled = 1 if body.enabled else 0
    await s.commit(); await s.refresh(r)
    return _to_out(r)


@router.delete("/api/rules/{rid}", status_code=204)
async def delete_rule(rid: int, _: User = Depends(current_user), s: AsyncSession = Depends(db_session)):
    r = await s.get(Rule, rid)
    if not r: raise HTTPException(404, "not found")
    await s.delete(r); await s.commit()
