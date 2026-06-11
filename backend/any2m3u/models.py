from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


def _now() -> str:
    return datetime.utcnow().isoformat()


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True)
    password_hash: Mapped[str] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String, default=_now)
    last_login_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class Source(Base):
    __tablename__ = "sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String)  # 'webdav' or 'local'
    config_json: Mapped[str] = mapped_column(Text)
    group_by_dir: Mapped[int] = mapped_column(Integer, default=0)
    refresh_cron: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    enabled: Mapped[int] = mapped_column(Integer, default=1)
    last_scan_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_scan_status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String, default=_now)

    rules: Mapped[list["Rule"]] = relationship(back_populates="source", cascade="all, delete-orphan")


class ScanCache(Base):
    __tablename__ = "scan_cache"
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), primary_key=True)
    scanned_at: Mapped[str] = mapped_column(String)
    entry_count: Mapped[int] = mapped_column(Integer)
    total_bytes: Mapped[int] = mapped_column(Integer)
    entries_jsonl_path: Mapped[str] = mapped_column(String)


class Rule(Base):
    __tablename__ = "rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String)
    include_exts: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    exclude_keywords: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    include_paths: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    group_title: Mapped[str] = mapped_column(String, default="")
    tpl: Mapped[str] = mapped_column(Text)
    logo_dir: Mapped[str] = mapped_column(String, default="")
    enabled: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[str] = mapped_column(String, default=_now)

    source: Mapped[Source] = relationship(back_populates="rules")


class PullToken(Base):
    __tablename__ = "pull_tokens"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)
    token: Mapped[str] = mapped_column(String, unique=True)
    created_at: Mapped[str] = mapped_column(String, default=_now)
    last_used_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    expires_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    revoked: Mapped[int] = mapped_column(Integer, default=0)


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[str] = mapped_column(String, default=_now)
    expires_at: Mapped[str] = mapped_column(String)
    ip: Mapped[Optional[str]] = mapped_column(String, nullable=True)
