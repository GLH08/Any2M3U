from __future__ import annotations
from typing import TypedDict, Iterable


class FileEntry(TypedDict):
    """A scanned file. Lifted to scanner.base.FileEntry in later tasks."""
    path: str
    size: int
    mtime: float
    etag: str | None


def _split_csv(s: str | None) -> list[str]:
    if not s:
        return []
    return [x.strip() for x in s.split(",") if x.strip()]


def _norm_ext(s: str) -> str:
    s = s.strip().lower()
    if s.startswith("."):
        s = s[1:]
    return s


def filter_entries(
    entries: Iterable[FileEntry],
    include_exts: str | None,
    exclude_keywords: str | None,
    include_paths: str | None,
) -> list[FileEntry]:
    """Apply include/exclude filters. Returns only entries that pass."""
    exts = [_norm_ext(x) for x in _split_csv(include_exts)]
    bad = [x.lower() for x in _split_csv(exclude_keywords)]
    prefixes = [x for x in _split_csv(include_paths)]

    out: list[FileEntry] = []
    for e in entries:
        p = e["path"]
        if exts:
            ext = p.rsplit(".", 1)[-1].lower() if "." in p else ""
            if ext not in exts:
                continue
        if bad:
            pl = p.lower()
            if any(k in pl for k in bad):
                continue
        if prefixes:
            if not any(p.startswith(pref) or p.startswith("/" + pref.lstrip("/")) for pref in prefixes):
                continue
        out.append(e)
    return out
