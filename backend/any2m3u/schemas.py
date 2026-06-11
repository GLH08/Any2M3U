from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, field_validator


class WebDAVConfig(BaseModel):
    url: str
    username: str
    password: str
    root_path: str = "/"
    verify_tls: bool = True


class LocalConfig(BaseModel):
    path: str


class SourceCreate(BaseModel):
    name: str
    type: Literal["webdav", "local"]
    config: dict
    group_by_dir: bool = False
    refresh_cron: Optional[str] = None
    enabled: bool = True

    @field_validator("config")
    @classmethod
    def _v(cls, v, info):
        t = info.data.get("type")
        if t == "webdav":
            WebDAVConfig(**v)
        elif t == "local":
            LocalConfig(**v)
        return v


class SourceUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[dict] = None
    group_by_dir: Optional[bool] = None
    refresh_cron: Optional[str] = None
    enabled: Optional[bool] = None


class SourceOut(BaseModel):
    id: int
    name: str
    type: str
    config: dict
    group_by_dir: bool
    refresh_cron: Optional[str]
    enabled: bool
    last_scan_at: Optional[str]
    last_scan_status: Optional[str]
    last_error: Optional[str]
    created_at: str


class RuleCreate(BaseModel):
    name: str
    include_exts: Optional[str] = None
    exclude_keywords: Optional[str] = None
    include_paths: Optional[str] = None
    group_title: str = ""
    tpl: str
    logo_dir: str = ""
    enabled: bool = True


class RuleUpdate(BaseModel):
    name: Optional[str] = None
    include_exts: Optional[str] = None
    exclude_keywords: Optional[str] = None
    include_paths: Optional[str] = None
    group_title: Optional[str] = None
    tpl: Optional[str] = None
    logo_dir: Optional[str] = None
    enabled: Optional[bool] = None


class RuleOut(BaseModel):
    id: int
    source_id: int
    name: str
    include_exts: Optional[str]
    exclude_keywords: Optional[str]
    include_paths: Optional[str]
    group_title: str
    tpl: str
    logo_dir: str
    enabled: bool
    created_at: str


class TokenCreate(BaseModel):
    name: str
    expires_at: Optional[str] = None


class TokenCreated(BaseModel):
    id: int
    name: str
    token: str
    expires_at: Optional[str]


class TokenOut(BaseModel):
    id: int
    name: str
    created_at: str
    last_used_at: Optional[str]
    expires_at: Optional[str]
    revoked: bool


class ScanTriggerResponse(BaseModel):
    job_id: str


class ScanStatusResponse(BaseModel):
    status: str
    last_scan_at: Optional[str]
    last_error: Optional[str]
    entry_count: int
    total_bytes: int
    progress: int


class SourceTestResponse(BaseModel):
    ok: bool
    error: Optional[str] = None
    latency_ms: int = 0


class DiagnoseRequest(BaseModel):
    """Optional override of the stored config; if absent, uses the saved one."""
    config: Optional[dict] = None


class DiagnoseResponse(BaseModel):
    ok: bool
    latency_ms: int = 0
    error: Optional[str] = None
    request: Optional[dict] = None       # {method, url, headers} actually sent
    response_status: Optional[int] = None
    response_headers: Optional[dict] = None
    response_body: Optional[str] = None  # raw XML/text (truncated)
    parsed_entries: list[dict] = []      # top-level files found in this PROPFIND
