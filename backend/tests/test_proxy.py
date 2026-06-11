import re
import pytest
from any2m3u.proxy.stream import parse_range, Range


def test_parse_range_simple():
    r = parse_range("bytes=0-9", 100)
    assert r is not None
    assert r.start == 0 and r.end == 9 and r.length == 10


def test_parse_range_open_end():
    r = parse_range("bytes=50-", 100)
    assert r is not None
    assert r.start == 50 and r.end == 99 and r.length == 50


def test_parse_range_suffix():
    r = parse_range("bytes=-10", 100)
    assert r is not None
    assert r.start == 90 and r.end == 99 and r.length == 10


def test_parse_range_invalid():
    assert parse_range("junk", 100) is None
    assert parse_range("bytes=200-300", 100) is None  # out of bounds
    assert parse_range("", 100) is None
    assert parse_range("bytes=", 100) is None
    assert parse_range("bytes=0-100,200-300", 100) is None  # multi-range
    assert parse_range("bytes=abc-def", 100) is None
