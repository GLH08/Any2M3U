from pathlib import Path

import pytest


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """Override ANY2M3U_DATA to a tempdir for the duration of a test."""
    d = tmp_path / "data"
    d.mkdir()
    return d


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """Reset the lru_cache on get_settings so env-var changes take effect per test."""
    from any2m3u.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _clear_scanner_state():
    """Reset the scanner engine's in-memory indexes between tests."""
    from any2m3u.scanner import engine
    engine._index.clear()
    engine._progress.clear()
    yield
    engine._index.clear()
    engine._progress.clear()
