"""HTTP Range header parsing for the proxy endpoint.

Supports the common single-range forms:
  bytes=0-499       -> [0, 499]
  bytes=500-        -> [500, size-1]
  bytes=-500        -> suffix; last 500 bytes

Multi-range (bytes=0-100,200-300) is not supported; we return None and the
caller falls back to a full 200 response.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Range:
    start: int
    end: int        # inclusive
    length: int

    @property
    def header(self) -> str:
        return f"bytes={self.start}-{self.end}"


def parse_range(header: str, total_size: int) -> Range | None:
    if not header or not header.startswith("bytes="):
        return None
    spec = header[len("bytes="):].strip()
    if "," in spec:
        return None  # multi-range not supported
    if "-" not in spec:
        return None
    start_s, end_s = spec.split("-", 1)
    if start_s == "":
        # suffix form: last N bytes
        try:
            n = int(end_s)
        except ValueError:
            return None
        if n <= 0 or n > total_size:
            return None
        start = max(0, total_size - n)
        end = total_size - 1
    else:
        try:
            start = int(start_s)
        except ValueError:
            return None
        if end_s == "":
            end = total_size - 1
        else:
            try:
                end = int(end_s)
            except ValueError:
                return None
        if start < 0 or start >= total_size or end < start:
            return None
        end = min(end, total_size - 1)
    return Range(start=start, end=end, length=end - start + 1)
