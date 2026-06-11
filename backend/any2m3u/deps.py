from __future__ import annotations
from datetime import datetime, timedelta
from fastapi import Cookie, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from .db import get_sessionmaker
from .models import User, Session as DBSession
from .security import new_session_id

COOKIE_NAME = "any2m3u_sid"
SESSION_TTL = timedelta(days=30)


async def db_session() -> AsyncSession:  # type: ignore[override]
    """FastAPI dependency: a per-request async DB session."""
    sm = get_sessionmaker()
    async with sm() as s:
        yield s


async def current_user(
    request: Request,
    sid: str | None = Cookie(default=None, alias=COOKIE_NAME),
    s: AsyncSession = Depends(db_session),
) -> User:
    if not sid:
        raise HTTPException(status_code=401, detail="no session")
    row = await s.get(DBSession, sid)
    if row is None:
        raise HTTPException(status_code=401, detail="invalid session")
    expires = datetime.fromisoformat(row.expires_at)
    if expires < datetime.utcnow():
        raise HTTPException(status_code=401, detail="session expired")
    user = await s.get(User, row.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="user gone")
    # sliding renewal
    row.expires_at = (datetime.utcnow() + SESSION_TTL).isoformat()
    await s.commit()
    request.state.user = user
    return user


async def create_session(s: AsyncSession, user_id: int, ip: str | None) -> str:
    sid = new_session_id()
    s.add(DBSession(
        id=sid,
        user_id=user_id,
        created_at=datetime.utcnow().isoformat(),
        expires_at=(datetime.utcnow() + SESSION_TTL).isoformat(),
        ip=ip,
    ))
    await s.commit()
    return sid
