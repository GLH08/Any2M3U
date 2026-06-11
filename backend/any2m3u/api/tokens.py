from __future__ import annotations
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..deps import current_user, db_session
from ..models import PullToken, User
from ..schemas import TokenCreate, TokenCreated, TokenOut
from ..security import new_pull_token

router = APIRouter(prefix="/api/tokens", tags=["tokens"])


def _to_out(t: PullToken) -> TokenOut:
    return TokenOut(
        id=t.id, name=t.name, created_at=t.created_at,
        last_used_at=t.last_used_at, expires_at=t.expires_at, revoked=bool(t.revoked),
    )


@router.get("", response_model=list[TokenOut])
async def list_tokens(_: User = Depends(current_user), s: AsyncSession = Depends(db_session)):
    rows = (await s.execute(select(PullToken).order_by(PullToken.id))).scalars().all()
    return [_to_out(r) for r in rows]


@router.post("", response_model=TokenCreated, status_code=201)
async def create_token(body: TokenCreate, _: User = Depends(current_user), s: AsyncSession = Depends(db_session)):
    tok = new_pull_token()
    t = PullToken(name=body.name, token=tok, expires_at=body.expires_at,
                  created_at=datetime.now(timezone.utc).isoformat())
    s.add(t); await s.commit(); await s.refresh(t)
    return TokenCreated(id=t.id, name=t.name, token=tok, expires_at=t.expires_at)


@router.delete("/{tid}", status_code=204)
async def revoke_token(tid: int, _: User = Depends(current_user), s: AsyncSession = Depends(db_session)):
    t = await s.get(PullToken, tid)
    if not t: raise HTTPException(404, "not found")
    t.revoked = 1
    await s.commit()
