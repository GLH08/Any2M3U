from __future__ import annotations
from functools import lru_cache
from pathlib import Path
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ANY2M3U_", env_file=None, extra="ignore")

    data_dir: Path = Field(
        default=Path("/data"),
        validation_alias=AliasChoices("data_dir", "ANY2M3U_DATA"),
    )
    web_dir: Path = Path(__file__).parent / "web"
    db_path: Path | None = None
    scan_dir: Path | None = None
    base_url: str = "http://localhost:8000"
    admin_password: str | None = None
    log_level: str = "INFO"
    bind: str = "0.0.0.0:8000"
    initial_password_file: str = "INITIAL_PASSWORD.txt"

    def model_post_init(self, _):
        self.data_dir = Path(self.data_dir)
        self.db_path = self.data_dir / "app.db"
        self.scan_dir = self.data_dir / "scan"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
