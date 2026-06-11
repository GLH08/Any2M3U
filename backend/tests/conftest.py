import asyncio
import os
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """Override ANY2M3U_DATA to a tempdir for the duration of a test."""
    d = tmp_path / "data"
    d.mkdir()
    return d
