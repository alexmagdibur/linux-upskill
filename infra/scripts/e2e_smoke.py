"""Реальный end-to-end сценарий без моков: регистрация -> запуск лаборатории -> PTY по WebSocket -> проверка -> XP.

Требует запущенных API, worker, PostgreSQL, Redis и Docker:  python infra/scripts/e2e_smoke.py [BASE_URL] [ORIGIN]
"""

import asyncio
import json
import sys
import time
import uuid

import httpx
import websockets

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
ORIGIN = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:5173"


async def main() -> int:
    email = f"smoke-{uuid.uuid4().hex[:8]}@example.com"
    async with httpx.AsyncClient(base_url=BASE, headers={"Origin": ORIGIN}, timeout=30) as c:
        r = await c.post("/api/v1/auth/register", json={"email": email, "password": "correct-horse-battery"})
        assert r.status_code == 201, r.text
        r = await c.post("/api/v1/auth/login", json={"email": email, "password": "correct-horse-battery"})
        assert r.status_code == 200, r.text
        c.headers["X-CSRF-Token"] = c.cookies["upskill_csrf"]

        labs = (await c.get("/api/v1/labs")).json()
        print("catalog:", labs["total"], "labs")

        t0 = time.time()
        r = await c.post("/api/v1/labs/linux-001/sessions", headers={"Idempotency-Key": str(uuid.uuid4())})
        assert r.status_code == 202, r.text
        sid = r.json()["session_id"]
        while True:
            s = (await c.get(f"/api/v1/sessions/{sid}")).json()
            if s["status"] not in ("PROVISIONING", "CREATED"):
                break
            await asyncio.sleep(0.3)
        assert s["status"] == "READY", s
        print(f"provisioned in {time.time() - t0:.1f}s ->", s["status"])

        ticket = (await c.post(f"/api/v1/sessions/{sid}/terminal-ticket")).json()["ticket"]
        cookie = "; ".join(f"{k}={v}" for k, v in c.cookies.items())
        ws_url = BASE.replace("http", "ws") + f"/api/v1/sessions/{sid}/terminal?ticket={ticket}"
        async with websockets.connect(ws_url, origin=ORIGIN, additional_headers={"Cookie": cookie}) as ws:
            await ws.send(json.dumps({"type": "resize", "cols": 120, "rows": 30}))
            await ws.send(b"cd ~/lab/src/app && pwd > ~/lab/answer.txt && mkdir ~/lab/notes && echo DONE$((20+22))\n")
            buf = b""
            deadline = time.time() + 10
            while b"DONE42" not in buf.split(b"echo DONE")[-1] and time.time() < deadline:
                buf += await asyncio.wait_for(ws.recv(), 5) if True else b""
            assert b"DONE42" in buf, buf
            print("terminal: real shell answered")

        r = await c.post(f"/api/v1/sessions/{sid}/validate")
        assert r.status_code == 202, r.text
        attempt = r.json()["attempt_id"]
        for _ in range(60):
            v = (await c.get(f"/api/v1/sessions/{sid}/validations/{attempt}")).json()
            if v["status"] != "PENDING":
                break
            await asyncio.sleep(0.5)
        print("validation:", json.dumps(v, ensure_ascii=False))
        assert v["passed"] is True and v["xp_awarded"] == 50, v

        me = (await c.get("/api/v1/users/me")).json()
        print("xp:", me["total_xp"])
        assert me["total_xp"] == 50
        s = (await c.get(f"/api/v1/sessions/{sid}")).json()
        print("final session status:", s["status"])
        assert s["status"] == "COMPLETED"
    print("E2E OK")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
