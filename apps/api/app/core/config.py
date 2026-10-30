from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[4]
DEV_SECRET = "dev-only-secret-change-me-0123456789abcdef"
DEV_INTERNAL = "dev-internal-token-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    env: str = "dev"  # dev | test | prod
    database_url: str = "postgresql+asyncpg://upskill:upskill@127.0.0.1:15432/upskill"
    redis_url: str = "redis://127.0.0.1:6379/0"
    app_secret: str = DEV_SECRET
    public_origin: str = "http://localhost:5173"
    extra_origins: str = ""  # через запятую
    internal_token: str = DEV_INTERNAL
    worker_url: str = "http://127.0.0.1:8100"
    content_dir: Path = ROOT / "content"

    cookie_secure: bool = False
    access_ttl_seconds: int = 15 * 60
    refresh_ttl_seconds: int = 14 * 24 * 3600
    trust_proxy: bool = False

    sandbox_runtime: str = "docker"  # docker | disabled
    sandbox_max_concurrent: int = 10
    sandbox_per_user_limit: int = 2
    sandbox_ttl_seconds: int = 1800
    sandbox_idle_seconds: int = 600
    sandbox_cpu_limit: float = 0.5
    sandbox_memory_limit: str = "256m"
    provisioning_timeout_seconds: int = 120
    validating_timeout_seconds: int = 90

    terminal_ticket_ttl_seconds: int = Field(default=30, le=30)
    rate_limit_enabled: bool = True
    sweeper_interval_seconds: int = 10
    log_level: str = "INFO"

    @property
    def allowed_origins(self) -> set[str]:
        extra = {o.strip() for o in self.extra_origins.split(",") if o.strip()}
        return {self.public_origin.rstrip("/"), *extra}

    @model_validator(mode="after")
    def _prod_guards(self) -> Settings:
        if self.env == "prod":
            if self.app_secret == DEV_SECRET or len(self.app_secret) < 32:
                raise ValueError("APP_SECRET должен быть уникальным и не короче 32 символов в prod")
            if self.internal_token == DEV_INTERNAL:
                raise ValueError("INTERNAL_TOKEN должен быть задан в prod")
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE=true обязателен в prod (HTTPS/WSS)")
        return self


_current: Settings | None = None


def set_settings(settings: Settings | None) -> None:
    """Приложение регистрирует свои настройки: единый источник для зависимостей, лимитера и WebSocket."""
    global _current
    _current = settings


@lru_cache
def _default_settings() -> Settings:
    return Settings()


def get_settings() -> Settings:
    return _current or _default_settings()
