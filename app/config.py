from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./data/atcoder.db"
    atcoder_base_url: str = "https://atcoder.jp"
    atcoder_user_agent: str = "atcoder-participations/0.1 (contact: admin@example.com)"
    http_timeout_seconds: float = Field(default=15.0, gt=0)
    http_max_retries: int = Field(default=3, ge=1, le=10)
    http_request_interval_seconds: float = Field(default=1.0, ge=0)
    sync_interval_hours: int = Field(default=6, ge=1, le=168)
    enable_scheduler: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
