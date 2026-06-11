from datetime import datetime, timezone, timedelta
from any2m3u.utils.dates import parse_utc, utcnow_iso


def test_utcnow_iso_is_aware_and_parseable():
    s = utcnow_iso()
    parsed = parse_utc(s)
    assert parsed.tzinfo is not None
    assert parsed == datetime.fromisoformat(s)


def test_parse_utc_naive_input_is_treated_as_utc():
    naive = (datetime.now(timezone.utc) - timedelta(days=10)).replace(tzinfo=None).isoformat()
    parsed = parse_utc(naive)
    assert parsed.tzinfo is timezone.utc
    assert parsed < datetime.now(timezone.utc)


def test_parse_utc_aware_input_unchanged():
    aware = datetime.now(timezone.utc).isoformat()
    parsed = parse_utc(aware)
    assert parsed.tzinfo is timezone.utc
