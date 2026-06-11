from __future__ import annotations
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from .migrations._runner import apply as apply_migrations


class Base(DeclarativeBase):
    pass


_engine = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


async def init_db(data_dir: Path) -> None:
    """Initialize the database (create files, apply migrations, set up engine)."""
    global _engine, _sessionmaker
    data_dir.mkdir(parents=True, exist_ok=True)
    apply_migrations(data_dir)
    db_path = data_dir / "app.db"
    _engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        echo=False,
        connect_args={"check_same_thread": False, "timeout": 5.0},
    )
    _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    # enable WAL
    from sqlalchemy import text
    async with _engine.begin() as conn:
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.execute(text("PRAGMA busy_timeout=5000"))
        await conn.execute(text("PRAGMA foreign_keys=ON"))


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    if _sessionmaker is None:
        raise RuntimeError("DB not initialized; call init_db() first")
    return _sessionmaker


async def get_db() -> AsyncSession:  # type: ignore[override]
    """FastAPI dependency."""
    sm = get_sessionmaker()
    async with sm() as session:
        yield session
