"""Клиент внутреннего API: worker не имеет доступа к БД, результаты отдаёт API по HTTP."""

from __future__ import annotations

import httpx

from .config import WorkerSettings


class ApiClient:
    def __init__(self, settings: WorkerSettings) -> None:
        self._http = httpx.AsyncClient(
            base_url=settings.api_internal_url.rstrip("/") + "/internal/v1",
            headers={"X-Internal-Token": settings.internal_token},
            timeout=httpx.Timeout(10.0),
        )

    async def provisioned(self, session_id: str, runtime_ref: str) -> bool:
        """False, если сессия уже не нуждается в окружении (остановлена/истекла)."""
        r = await self._http.post(f"/sessions/{session_id}/provisioned", json={"runtime_ref": runtime_ref})
        r.raise_for_status()
        return bool(r.json()["accepted"])

    async def provision_failed(self, session_id: str, error_code: str) -> None:
        r = await self._http.post(f"/sessions/{session_id}/failed", json={"error_code": error_code})
        r.raise_for_status()

    async def validation_result(self, attempt_id: str, results: dict[str, bool], error_code: str | None) -> None:
        r = await self._http.post(
            f"/validations/{attempt_id}/result", json={"results": results, "error_code": error_code}
        )
        r.raise_for_status()

    async def destroyed(self, session_id: str) -> None:
        r = await self._http.post(f"/sessions/{session_id}/destroyed")
        r.raise_for_status()

    async def active_runtimes(self) -> dict[str, str]:
        """session_id -> status для сессий, которым нужен runtime."""
        r = await self._http.get("/sessions/active")
        r.raise_for_status()
        return {item["session_id"]: item["status"] for item in r.json()["items"]}

    async def mark_runtime_missing(self, session_id: str) -> None:
        r = await self._http.post(f"/sessions/{session_id}/failed", json={"error_code": "RUNTIME_MISSING"})
        r.raise_for_status()

    async def aclose(self) -> None:
        await self._http.aclose()
