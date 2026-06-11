from __future__ import annotations
import json
import mimetypes
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..config import get_settings
from ..db import get_sessionmaker
from ..m3u.filters import FileEntry, filter_entries
from ..m3u.renderer import render_m3u
from ..models import PullToken, Rule, ScanCache, Source
from ..proxy.stream import parse_range
from ..scanner.engine import build_adapter, entry_id, _index
from ..utils.dates import parse_utc, utcnow_iso

router = APIRouter(tags=["public"])

_BEARER_CHALLENGE = 'Bearer realm="any2m3u"'


async def _auth_pull(token: str | None, auth_header: str | None) -> PullToken:
    candidate = token
    if not candidate and auth_header and auth_header.lower().startswith("bearer "):
        candidate = auth_header.split(" ", 1)[1]
    if not candidate:
        raise HTTPException(status_code=401, detail="missing token",
                            headers={"WWW-Authenticate": _BEARER_CHALLENGE})
    sm = get_sessionmaker()
    async with sm() as s:
        row = (await s.execute(select(PullToken).where(PullToken.token == candidate))).scalar_one_or_none()
        if row is None or row.revoked:
            raise HTTPException(status_code=401, detail="invalid token",
                                headers={"WWW-Authenticate": _BEARER_CHALLENGE})
        if row.expires_at and parse_utc(row.expires_at) < parse_utc(utcnow_iso()):
            raise HTTPException(status_code=401, detail="expired token",
                                headers={"WWW-Authenticate": _BEARER_CHALLENGE})
        row.last_used_at = utcnow_iso()
        await s.commit()
        return row


def _load_entries(jsonl_path: str) -> list[FileEntry]:
    out: list[FileEntry] = []
    p = Path(jsonl_path)
    if not p.exists():
        return out
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


@router.get("/m3u/rule/{rid}")
async def m3u_for_rule(rid: int, request: Request, token: str | None = Query(default=None)):
    pt = await _auth_pull(token, request.headers.get("Authorization"))
    sm = get_sessionmaker()
    async with sm() as s:
        rule = await s.get(Rule, rid)
        if rule is None:
            raise HTTPException(404, "rule not found")
        cache = await s.get(ScanCache, rule.source_id)
        if cache is None:
            raise HTTPException(409, "source not yet scanned")
    entries = _load_entries(cache.entries_jsonl_path)
    eids = [entry_id(rule.source_id, e["path"]) for e in entries]
    filtered = filter_entries(entries, rule.include_exts, rule.exclude_keywords, rule.include_paths)
    keep = {e["path"] for e in filtered}
    filtered_eids = [eid for path, eid in zip((e["path"] for e in entries), eids) if path in keep]

    def logo_lookup(entry: FileEntry) -> str | None:
        """Return a relative path under rule.logo_dir if logo_dir is set.

        Format: <logo_dir>/<stem>.<ext>  (ext is .jpg then .png).
        """
        if not rule.logo_dir:
            return None
        stem = entry["path"].rsplit("/", 1)[-1].rsplit(".", 1)[0]
        # We don't know the actual filesystem; just emit a relative path.
        # The actual <ext> choice is the consumer's responsibility if it
        # wants to fetch a logo; we emit .jpg as default.
        return f"{rule.logo_dir.rstrip('/')}/{stem}.jpg"

    settings = get_settings()
    text = render_m3u(
        entries=filtered,
        entry_ids=filtered_eids,
        group_title=rule.group_title,
        logo_lookup=logo_lookup,
        tpl=rule.tpl,
        base_url=settings.base_url,
        source_id=rule.source_id,
        token=pt.token,
    )
    return Response(content=text, media_type="text/plain; charset=utf-8")


@router.get("/m3u/source/{sid}")
async def m3u_for_source_group(
    sid: int,
    request: Request,
    group: str | None = Query(default=None),
    token: str | None = Query(default=None),
):
    pt = await _auth_pull(token, request.headers.get("Authorization"))
    if not group:
        raise HTTPException(400, "group query parameter is required")
    sm = get_sessionmaker()
    async with sm() as s:
        src = await s.get(Source, sid)
        if not src:
            raise HTTPException(404, "source not found")
        if not src.group_by_dir:
            raise HTTPException(400, "source does not have group_by_dir enabled")
        cache = await s.get(ScanCache, sid)
        if cache is None:
            raise HTTPException(409, "source not yet scanned")
    entries = _load_entries(cache.entries_jsonl_path)
    prefix = group.strip("/") + "/"
    sub = [e for e in entries if e["path"].startswith(prefix)]
    eids = [entry_id(sid, e["path"]) for e in sub]
    settings = get_settings()
    text = render_m3u(
        entries=sub,
        entry_ids=eids,
        group_title=group,
        logo_lookup=lambda e: None,
        tpl=(
            "#EXTINF:-1 group-title=\"<group>\",<title>\n"
            "<base>/proxy?token=<t>&id=<eid>"
        ),
        base_url=settings.base_url,
        source_id=sid,
        token=pt.token,
    )
    return Response(content=text, media_type="text/plain; charset=utf-8")


@router.get("/proxy")
async def proxy(
    request: Request,
    id: str = Query(...),
    token: str | None = Query(default=None),
):
    pt = await _auth_pull(token, request.headers.get("Authorization"))
    found = None
    for sid, idx in _index.items():
        if id in idx:
            found = (sid, idx[id])
            break
    if found is None:
        raise HTTPException(404, detail={"error": "not_found"})
    sid, entry = found
    sm = get_sessionmaker()
    async with sm() as s:
        src = await s.get(Source, sid)
    if src is None:
        raise HTTPException(404, detail={"error": "not_found"})

    cfg = json.loads(src.config_json)
    size = entry["size"]
    range_header = request.headers.get("range") or request.headers.get("Range")
    rng = parse_range(range_header, size) if range_header else None
    ctype, _ = mimetypes.guess_type(entry["path"])
    if not ctype:
        ctype = "application/octet-stream"

    adapter = build_adapter(src)
    if rng is None:
        async def gen_full():
            try:
                async for chunk in adapter.open_full(entry["path"]):
                    yield chunk
            finally:
                try: await adapter.aclose()
                except Exception: pass
        return StreamingResponse(gen_full(), status_code=200, media_type=ctype, headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(size),
        })

    async def gen_range():
        try:
            async for chunk in adapter.open_range(entry["path"], rng.start, rng.end):
                yield chunk
        finally:
            try: await adapter.aclose()
            except Exception: pass
    return StreamingResponse(gen_range(), status_code=206, media_type=ctype, headers={
        "Accept-Ranges": "bytes",
        "Content-Range": f"bytes {rng.start}-{rng.end}/{size}",
        "Content-Length": str(rng.length),
    })
