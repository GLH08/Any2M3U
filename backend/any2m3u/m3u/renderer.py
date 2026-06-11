from __future__ import annotations
import os
import re
import xml.sax.saxutils as su
from typing import Callable, Iterable
from .filters import FileEntry


def _title_from_path(path: str) -> str:
    """Filename without extension. e.g. 'Movies/A.mp4' -> 'A'."""
    base = os.path.basename(path)
    if "." in base:
        base = base.rsplit(".", 1)[0]
    return base


def _format_template(
    tpl: str,
    *,
    base: str,
    sid: int,
    group: str,
    title: str,
    eid: str,
    token: str,
    logo: str | None,
) -> str:
    """Substitute placeholders in the M3U template. Strip tvg-logo when logo is None."""
    group_esc = su.escape(group, {'"': "&quot;"})
    title_esc = su.escape(title, {'"': "&quot;"})
    logo_esc = su.escape(logo, {'"': "&quot;"}) if logo else None

    rendered = (
        tpl
        .replace("<base>", base)
        .replace("<sid>", str(sid))
        .replace("<group>", group_esc)
        .replace("<title>", title_esc)
        .replace("<eid>", eid)
        .replace("<t>", token)
    )
    if logo_esc is None:
        # Strip the entire tvg-logo="..." attribute from the EXTINF line
        rendered = re.sub(r'\s*tvg-logo="[^"]*"', "", rendered)
    else:
        rendered = rendered.replace("<logo>", logo_esc)
    return rendered


def render_m3u(
    entries: Iterable[FileEntry],
    entry_ids: list[str],
    group_title: str,
    logo_lookup: Callable[[FileEntry], str | None],
    tpl: str,
    base_url: str,
    source_id: int,
    token: str,
) -> str:
    """Render an M3U body from filtered entries."""
    lines = ["#EXTM3U"]
    for e, eid in zip(entries, entry_ids):
        logo_rel = logo_lookup(e)
        title = _title_from_path(e["path"])
        line = _format_template(
            tpl,
            base=base_url.rstrip("/"),
            sid=source_id,
            group=group_title or "",
            title=title,
            eid=eid,
            token=token,
            logo=logo_rel,
        )
        lines.append(line)
    return "\n".join(lines) + "\n"
