import os
import pytest
from any2m3u.config import Settings, get_settings


def test_default_settings(monkeypatch, tmp_path):
    get_settings.cache_clear()
    monkeypatch.setenv("ANY2M3U_DATA", str(tmp_path))
    s = get_settings()
    assert s.data_dir == tmp_path
    assert s.db_path == tmp_path / "app.db"
    assert s.scan_dir == tmp_path / "scan"
    assert s.admin_password is None


def test_admin_password_from_env(monkeypatch, tmp_path):
    get_settings.cache_clear()
    monkeypatch.setenv("ANY2M3U_DATA", str(tmp_path))
    monkeypatch.setenv("ANY2M3U_ADMIN_PASSWORD", "secret")
    s = get_settings()
    assert s.admin_password == "secret"
