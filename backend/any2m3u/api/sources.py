from __future__ import annotations
import json
import time
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..deps import current_user, db_session
from ..models import ScanCache, Source, User
from ..schemas import (
    DiagnoseRequest,
    DiagnoseResponse,
    ScanStatusResponse,
    SourceCreate,
    SourceOut,
    SourceTestResponse,
    SourceUpdate,
)
from ..scanner.engine import build_adapter, get_progress, scan
from ..scanner.base import UpstreamAuthError, UpstreamError
from ..scheduler import add_job_for_source, remove_job_for_source
from ..utils.dates import utcnow_iso

router = APIRouter(prefix="/api/sources", tags=["sources"])


def _to_out(s: Source) -> SourceOut:
    return SourceOut(
        id=s.id, name=s.name, type=s.type, config=json.loads(s.config_json),
        group_by_dir=bool(s.group_by_dir), refresh_cron=s.refresh_cron,
        enabled=bool(s.enabled), last_scan_at=s.last_scan_at,
        last_scan_status=s.last_scan_status, last_error=s.last_error,
        created_at=s.created_at,
    )


@router.get("", response_model=list[SourceOut])
async def list_sources(_: User = Depends(current_user), s: AsyncSession = Depends(db_session)):
    rows = (await s.execute(select(Source).order_by(Source.id))).scalars().all()
    return [_to_out(r) for r in rows]


@router.post("", response_model=SourceOut, status_code=201)
async def create_source(body: SourceCreate, _: User = Depends(current_user), s: AsyncSession = Depends(db_session)):
    src = Source(
        name=body.name, type=body.type, config_json=json.dumps(body.config),
        group_by_dir=1 if body.group_by_dir else 0,
        refresh_cron=body.refresh_cron, enabled=1 if body.enabled else 0,
        created_at=utcnow_iso(),
    )
    s.add(src); await s.commit(); await s.refresh(src)
    if src.enabled and src.refresh_cron:
        add_job_for_source(src.id, src.refresh_cron)
    return _to_out(src)


@router.get("/{sid}", response_model=SourceOut)
async def get_source(sid: int, _: User = Depends(current_user), s: AsyncSession = Depends(db_session)):
    src = await s.get(Source, sid)
    if not src: raise HTTPException(404, "not found")
    return _to_out(src)


@router.patch("/{sid}", response_model=SourceOut)
async def update_source(sid: int, body: SourceUpdate, _: User = Depends(current_user), s: AsyncSession = Depends(db_session)):
    src = await s.get(Source, sid)
    if not src: raise HTTPException(404, "not found")
    if body.name is not None: src.name = body.name
    if body.config is not None: src.config_json = json.dumps(body.config)
    if body.group_by_dir is not None: src.group_by_dir = 1 if body.group_by_dir else 0
    if body.refresh_cron is not None: src.refresh_cron = body.refresh_cron
    if body.enabled is not None: src.enabled = 1 if body.enabled else 0
    await s.commit(); await s.refresh(src)
    # Re-evaluate scheduler state for this source
    if src.enabled and src.refresh_cron:
        add_job_for_source(src.id, src.refresh_cron)
    else:
        remove_job_for_source(src.id)
    return _to_out(src)


@router.delete("/{sid}", status_code=204)
async def delete_source(sid: int, _: User = Depends(current_user), s: AsyncSession = Depends(db_session)):
    src = await s.get(Source, sid)
    if not src: raise HTTPException(404, "not found")
    remove_job_for_source(sid)
    from ..scanner.engine import remove_source_from_index
    remove_source_from_index(sid)
    await s.delete(src); await s.commit()


@router.post("/{sid}/test", response_model=SourceTestResponse)
async def test_source(sid: int, _: User = Depends(current_user), s: AsyncSession = Depends(db_session)):
    src = await s.get(Source, sid)
    if not src: raise HTTPException(404, "not found")
    start = time.time()
    adapter = None
    try:
        adapter = build_adapter(src)
        await adapter.ping()
        return SourceTestResponse(ok=True, latency_ms=int((time.time()-start)*1000))
    except UpstreamAuthError as e:
        return SourceTestResponse(ok=False, error=f"auth_failed: {e}", latency_ms=int((time.time()-start)*1000))
    except UpstreamError as e:
        return SourceTestResponse(ok=False, error=str(e), latency_ms=int((time.time()-start)*1000))
    except Exception as e:
        return SourceTestResponse(ok=False, error=repr(e), latency_ms=int((time.time()-start)*1000))
    finally:
        if adapter is not None:
            try: await adapter.aclose()
            except Exception: pass


@router.post("/{sid}/diagnose", response_model=DiagnoseResponse)
async def diagnose_source(sid: int, body: DiagnoseRequest | None = None, _: User = Depends(current_user), s: AsyncSession = Depends(db_session)):
    """Issue a single PROPFIND at the root_path and return raw request/response
    plus the parsed top-level entries. This helps users debug misconfigured
    WebDAV paths without running a full scan.
    """
    import httpx
    from ..scanner.webdav import WebDAVAdapter
    src = await s.get(Source, sid)
    if not src: raise HTTPException(404, "not found")
    if src.type != "webdav":
        return DiagnoseResponse(ok=False, error="diagnose only supported for webdav sources")
    cfg = json.loads(src.config_json)
    if body and body.config:
        cfg.update(body.config)  # allow one-off override
    start = time.time()
    a = WebDAVAdapter(cfg["url"], cfg["username"], cfg["password"],
                     root_path=cfg.get("root_path", "/"), verify_tls=cfg.get("verify_tls", True))
    try:
        client = await a._ensure_client()
        prefix = a.root_path.rstrip("/")
        url = f"{a.base_url}{prefix}/" if prefix else f"{a.base_url}/"
        request_info = {
            "method": "PROPFIND",
            "url": url,
            "headers": {"Depth": "0", "Authorization": "Basic <redacted>"},
        }
        try:
            r = await client.request("PROPFIND", url, headers={"Depth": "0"})
        except httpx.HTTPError as e:
            return DiagnoseResponse(ok=False, error=f"network error: {e}",
                                   latency_ms=int((time.time()-start)*1000),
                                   request=request_info)
        latency = int((time.time()-start)*1000)
        body_text = r.text[:8000] if r.text else ""
        parsed: list[dict] = []
        if r.status_code in (401, 403):
            return DiagnoseResponse(ok=False, error=f"auth failed (HTTP {r.status_code})",
                                   latency_ms=latency, request=request_info,
                                   response_status=r.status_code,
                                   response_headers=dict(r.headers),
                                   response_body=body_text)
        if r.status_code >= 400:
            return DiagnoseResponse(ok=False, error=f"HTTP {r.status_code}",
                                   latency_ms=latency, request=request_info,
                                   response_status=r.status_code,
                                   response_headers=dict(r.headers),
                                   response_body=body_text)
        # Now do a Depth:1 PROPFIND to see actual children
        r2 = await client.request("PROPFIND", url, headers={"Depth": "1"})
        body_text2 = r2.text[:8000] if r2.text else ""
        # Parse via the adapter's own parser
        try:
            import xml.etree.ElementTree as ET
            NS = {"d": "DAV:"}
            root_el = ET.fromstring(r2.content)
            files, subdirs = a._parse_responses(root_el, "")
            for f in files:
                parsed.append({"path": f["path"], "size": f["size"], "is_dir": False})
            for sd in subdirs:
                parsed.append({"path": sd, "size": 0, "is_dir": True})
        except Exception as e:
            parsed = [{"error": f"parse failed: {e}"}]
        return DiagnoseResponse(
            ok=True, latency_ms=latency, request=request_info,
            response_status=r2.status_code,
            response_headers=dict(r2.headers),
            response_body=body_text2, parsed_entries=parsed,
        )
    finally:
        await a.aclose()


@router.post("/{sid}/scan")
async def trigger_scan(sid: int, bg: BackgroundTasks, _: User = Depends(current_user), s: AsyncSession = Depends(db_session)):
    src = await s.get(Source, sid)
    if not src: raise HTTPException(404, "not found")
    if src.last_scan_status == "running":
        raise HTTPException(409, "scan already running")
    bg.add_task(scan, sid)
    return {"job_id": f"scan-{sid}-{int(time.time())}"}


@router.get("/{sid}/scan", response_model=ScanStatusResponse)
async def get_scan_status(sid: int, _: User = Depends(current_user), s: AsyncSession = Depends(db_session)):
    src = await s.get(Source, sid)
    if not src: raise HTTPException(404, "not found")
    cache = await s.get(ScanCache, sid)
    return ScanStatusResponse(
        status=src.last_scan_status or "idle",
        last_scan_at=src.last_scan_at,
        last_error=src.last_error,
        entry_count=cache.entry_count if cache else 0,
        total_bytes=cache.total_bytes if cache else 0,
        progress=get_progress(sid) if src.last_scan_status == "running" else (cache.entry_count if cache else 0),
    )
