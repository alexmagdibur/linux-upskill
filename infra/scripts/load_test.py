"""Нагрузочная проверка: N одновременных лабораторий через настоящий API/worker/Docker.

    python infra/scripts/load_test.py [BASE_URL] [N]

Печатает фактические показатели: время готовности песочницы (P50/P95), интерактивная задержка (эхо клавиши
через WebSocket), поведение лимита ёмкости (N+1-й запрос) и отсутствие «утечек» контейнеров после остановки.
"""

import asyncio
import statistics
import subprocess
import sys
import time
import uuid

import httpx
import websockets

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 10
ORIGIN = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:5173"


def p95(values: list[float]) -> float:
    s = sorted(values)
    return s[min(len(s) - 1, int(round(0.95 * (len(s) - 1))))]


async def account() -> httpx.AsyncClient:
    c = httpx.AsyncClient(base_url=BASE, headers={"Origin": ORIGIN}, timeout=60)
    email = f"load-{uuid.uuid4().hex[:10]}@example.com"
    assert (await c.post("/api/v1/auth/register", json={"email": email, "password": "correct-horse-battery"})).status_code == 201
    assert (await c.post("/api/v1/auth/login", json={"email": email, "password": "correct-horse-battery"})).status_code == 200
    c.headers["X-CSRF-Token"] = c.cookies["upskill_csrf"]
    return c


async def one(c: httpx.AsyncClient, start_at: float) -> dict:
    r = await c.post("/api/v1/labs/linux-001/sessions", headers={"Idempotency-Key": str(uuid.uuid4())})
    if r.status_code != 202:
        return {"error": r.status_code, "body": r.text}
    sid = r.json()["session_id"]
    while True:
        s = (await c.get(f"/api/v1/sessions/{sid}")).json()
        if s["status"] != "PROVISIONING":
            break
        await asyncio.sleep(0.1)
    ready = time.time() - start_at
    if s["status"] != "READY":
        return {"error": s["status"], "sid": sid}
    ticket = (await c.post(f"/api/v1/sessions/{sid}/terminal-ticket")).json()["ticket"]
    cookie = "; ".join(f"{k}={v}" for k, v in c.cookies.items())
    lat: list[float] = []
    async with websockets.connect(
        BASE.replace("http", "ws") + f"/api/v1/sessions/{sid}/terminal?ticket={ticket}",
        origin=ORIGIN, additional_headers={"Cookie": cookie},
    ) as ws:
        await asyncio.sleep(0.5)
        for i in range(20):
            ch = bytes([ord("a") + i % 26])
            t0 = time.perf_counter()
            await ws.send(ch)
            while True:
                frame = await asyncio.wait_for(ws.recv(), 5)
                if isinstance(frame, bytes) and ch in frame:
                    break
            lat.append((time.perf_counter() - t0) * 1000)
            await asyncio.sleep(0.05)
    return {"sid": sid, "ready": ready, "lat": lat}


def container_count() -> int:
    out = subprocess.run(["docker", "ps", "-aq", "--filter", "label=upskill.managed=true"], capture_output=True, text=True)
    return len(out.stdout.split())


async def main() -> int:
    # по 2 лаборатории на пользователя (SANDBOX_PER_USER_LIMIT=2) — укладываемся в лимит регистраций с одного IP
    users = [await account() for _ in range((N + 1) // 2 + 1)]
    clients = [users[i // 2] for i in range(N)] + [users[-1]]
    t0 = time.time()
    results = await asyncio.gather(*[one(c, t0) for c in clients[:N]])
    errs = [r for r in results if "error" in r]
    ok = [r for r in results if "error" not in r]
    ready = [r["ready"] for r in ok]
    lat = [x for r in ok for x in r["lat"]]
    print(f"concurrent labs requested: {N}, ready: {len(ok)}, errors: {len(errs)} {errs[:2]}")
    if ready:
        print(f"time-to-READY  p50={statistics.median(ready):.2f}s  p95={p95(ready):.2f}s  max={max(ready):.2f}s")
        print(f"keystroke echo p50={statistics.median(lat):.1f}ms  p95={p95(lat):.1f}ms  (localhost, {len(lat)} samples)")
    print("containers while running:", container_count())

    # N+1-й запрос должен получить понятный отказ, а не полусессию
    extra = await clients[N].post("/api/v1/labs/linux-001/sessions")
    print("over-capacity request ->", extra.status_code, extra.json().get("error", {}).get("code"))

    stats = subprocess.run(
        ["docker", "stats", "--no-stream", "--format", "{{.Name}} cpu={{.CPUPerc}} mem={{.MemUsage}} pids={{.PIDs}}"],
        capture_output=True, text=True,
    ).stdout.strip().splitlines()
    print("sample docker stats:", *stats[:3], sep="\n  ")

    for c, r in zip(clients, results, strict=False):
        if "sid" in r:
            await c.delete(f"/api/v1/sessions/{r['sid']}")
    for _ in range(40):
        if container_count() == 0:
            break
        await asyncio.sleep(0.5)
    left = container_count()
    print("containers after stop:", left)
    for c in users:
        await c.aclose()
    good = len(ok) == N and extra.status_code == 503 and left == 0
    print("LOAD TEST", "OK" if good else "FAILED")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
