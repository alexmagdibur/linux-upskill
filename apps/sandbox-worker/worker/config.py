from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    redis_url: str = "redis://127.0.0.1:6379/0"
    api_internal_url: str = "http://localhost:8000"
    internal_token: str = Field(default="dev-internal-token-change-me")
    content_dir: Path = ROOT / "content"

    sandbox_runtime: str = "docker"  # docker | disabled
    sandbox_max_concurrent: int = 10
    sandbox_ttl_seconds: int = 1800
    sandbox_cpu_limit: float = 0.5
    sandbox_memory_limit: str = "256m"
    sandbox_pids_limit: int = 128
    sandbox_home_size_mb: int = 48
    sandbox_tmp_size_mb: int = 16
    sandbox_max_output_bytes: int = 64 * 1024 * 1024
    sandbox_scrollback_bytes: int = 128 * 1024

    worker_host: str = "127.0.0.1"
    worker_port: int = 8100
    worker_consumer_name: str = "worker-1"
    job_max_attempts: int = 3
    reconcile_interval_seconds: int = 20
    log_level: str = "INFO"


def get_settings() -> WorkerSettings:
    return WorkerSettings()
