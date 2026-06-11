from __future__ import annotations
from datetime import datetime, timezone
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..deps import COOKIE_NAME, SESSION_TTL, create_session, current_user, db_session
from ..models import Session as DBSession, User
from ..security import hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginBody(BaseModel):
    username: str
    password: str


def _set_cookie(resp: Response, sid: str, secure: bool = False) -> None:
    resp.set_cookie(
        COOKIE_NAME, sid,
        httponly=True, samesite="lax", secure=secure,
        max_age=int(SESSION_TTL.total_seconds()), path="/",
    )


@router.get("/me")
async def me(s: AsyncSession = Depends(db_session)):
    """Return 404 with code=not_initialized if no users exist, else 401 if not logged in."""
    res = await s.execute(select(User).limit(1))
    if res.first() is None:
        raise HTTPException(status_code=404, detail={"code": "not_initialized"})
    raise HTTPException(status_code=401, detail="not logged in")


@router.post("/login")
async def login(body: LoginBody, request: Request, response: Response, s: AsyncSession = Depends(db_session)):
    user = (await s.execute(select(User).where(User.username == body.username))).scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")
    sid = await create_session(s, user.id, request.client.host if request.client else None)
    user.last_login_at = datetime.now(timezone.utc).isoformat()
    await s.commit()
    _set_cookie(response, sid)
    return {"username": user.username, "last_login_at": user.last_login_at}


@router.post("/logout", status_code=204)
async def logout(response: Response, session_id: str | None = Cookie(default=None, alias=COOKIE_NAME), s: AsyncSession = Depends(db_session)):
    if session_id:
        row = await s.get(DBSession, session_id)
        if row:
            await s.delete(row)
            await s.commit()
    response.delete_cookie(COOKIE_NAME, path="/")


class PasswordBody(BaseModel):
    old: str
    new: str


@router.post("/password")
async def change_password(body: PasswordBody, user: User = Depends(current_user), s: AsyncSession = Depends(db_session)):
    if not verify_password(body.old, user.password_hash):
        raise HTTPException(status_code=400, detail="wrong current password")
    if len(body.new) < 8:
        raise HTTPException(status_code=400, detail="password must be at least 8 chars")
    user.password_hash = hash_password(body.new)
    await s.commit()
    return {"ok": True}
