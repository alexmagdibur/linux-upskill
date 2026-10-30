"""Сквозной сценарий для задания на учебной машине (LXD): API → worker → LXD-хост → PTY по WebSocket → проверка → XP.

    python infra/scripts/e2e_vm_smoke.py [BASE_URL] [ORIGIN]

Проходит ld-051 («служба в цикле restart»): ученик читает причину, правит unit через sudo, проверка засчитывает.
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
LAB = "ld-051"


async def read_until(ws, needle: bytes, timeout: float = 30) -> bytes:
    buf = b""
    end = time.time() + timeout
    while needle not in buf and time.time() < end:
        frame = await asyncio.wait_for(ws.recv(), timeout)
        if isinstance(frame, bytes):
            buf += frame
    assert needle in buf, buf[-400:]
    return buf


async def main() -> int:
    email = f"vm-smoke-{uuid.uuid4().hex[:8]}@example.com"
    async with httpx.AsyncClient(base_url=BASE, headers={"Origin": ORIGIN}, timeout=60) as c:
        assert (await c.post("/api/v1/auth/register", json={"email": email, "password": "correct-horse-battery"})).status_code == 201
        assert (await c.post("/api/v1/auth/login", json={"email": email, "password": "correct-horse-battery"})).status_code == 200
        c.headers["X-CSRF-Token"] = c.cookies["upskill_csrf"]

        t0 = time.time()
        r = await c.post(f"/api/v1/labs/{LAB}/sessions", headers={"Idempotency-Key": str(uuid.uuid4())})
        assert r.status_code == 202, r.text
        sid = r.json()["session_id"]
        while True:
            s = (await c.get(f"/api/v1/sessions/{sid}")).json()
            if s["status"] not in ("PROVISIONING", "CREATED"):
                break
            await asyncio.sleep(0.5)
        assert s["status"] == "READY", s
        print(f"учебная машина готова за {time.time() - t0:.1f}s")

        # до исправления проверка не проходит
        r = await c.post(f"/api/v1/sessions/{sid}/validate")
        attempt = r.json()["attempt_id"]
        for _ in range(120):
            v = (await c.get(f"/api/v1/sessions/{sid}/validations/{attempt}")).json()
            if v["status"] != "PENDING":
                break
            await asyncio.sleep(0.5)
        assert v["passed"] is False, v
        print("до исправления: проверка не пройдена (ожидаемо)")

        ticket = (await c.post(f"/api/v1/sessions/{sid}/terminal-ticket")).json()["ticket"]
        cookie = "; ".join(f"{k}={v}" for k, v in c.cookies.items())
        async with websockets.connect(
            BASE.replace("http", "ws") + f"/api/v1/sessions/{sid}/terminal?ticket={ticket}",
            origin=ORIGIN, additional_headers={"Cookie": cookie},
        ) as ws:
            await ws.send(json.dumps({"type": "resize", "cols": 120, "rows": 30}))
            await ws.send(b"id -un; systemctl show -p WorkingDirectory --value labapp; echo MARK$((6*7))\n")
            out = await read_until(ws, b"MARK42")
            assert b"student" in out and b"/opt/labapp/current" in out, out[-300:]
            print("терминал: настоящий shell внутри машины, видна причина (WorkingDirectory=/opt/labapp/current)")
            await ws.send(
                b"sudo sed -i 's#^WorkingDirectory=.*#WorkingDirectory=/opt/labapp/releases/1#' /etc/systemd/system/labapp.service"
                b" && sudo systemctl daemon-reload && sudo systemctl restart labapp && sleep 7 && systemctl is-active labapp; echo FIX$((1+1))\n"
            )
            out = await read_until(ws, b"FIX2", timeout=40)
            assert b"active" in out, out[-300:]

        r = await c.post(f"/api/v1/sessions/{sid}/validate")
        attempt = r.json()["attempt_id"]
        for _ in range(120):
            v = (await c.get(f"/api/v1/sessions/{sid}/validations/{attempt}")).json()
            if v["status"] != "PENDING":
                break
            await asyncio.sleep(0.5)
        print("после исправления:", json.dumps({k: v[k] for k in ("passed", "score", "xp_awarded")}))
        assert v["passed"] is True and v["xp_awarded"] > 0, v
        s = (await c.get(f"/api/v1/sessions/{sid}")).json()
        assert s["status"] == "COMPLETED", s
    print("E2E VM OK")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
