"""LXDAdapter: учебные «машины» (системные контейнеры LXD с настоящим systemd) на отдельной VM-хосте.

Worker управляет хостом по SSH (paramiko, вход по ключу, host key проверяется по known_hosts):
  * на каждую сессию создаётся своя изолированная сеть `lab<8hex>` (без NAT, без маршрутизации, без DNS);
    правила `inet upskill_lab` на хосте (infra/lxd/host-setup.sh) закрывают от неё хост, LAN и интернет;
  * машина создаётся из образа по fingerprint (allowlist в images.lock.json), непривилегированная, с лимитами профиля;
  * терминал — SSH-канал с PTY, внутри `lxc exec ... bash -l` от имени student;
  * доверенные скрипты (setup / exercise / validate) передаются через stdin отдельного канала, а не файлом.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
import shlex
import threading
import time
from pathlib import Path
from typing import Any

import paramiko

from .base import (
    ImageRef,
    PTYStream,
    ResourceLimits,
    RuntimeAdapter,
    RuntimeError_,
    RuntimeInfo,
    ValidationContext,
)

log = logging.getLogger("worker.lxd")

PROFILE = "upskill-lab"
MAX_OUTPUT = 65536
_NAME_RE = re.compile(r"^upskill-[0-9a-f-]{36}$")
_NET_RE = re.compile(r"^lab[0-9a-f]{8}$")
STUDENT_ENV = {
    "HOME": "/home/student",
    "USER": "student",
    "LOGNAME": "student",
    "LANG": "C.UTF-8",
    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
}


def net_name(session_id: str) -> str:
    return "lab" + session_id.replace("-", "")[:8]


class SSHPTY(PTYStream):
    def __init__(self, chan: paramiko.Channel) -> None:
        self._chan = chan

    def read_blocking(self) -> bytes:
        try:
            return self._chan.recv(65536)
        except Exception:  # noqa: BLE001 — закрытый канал = EOF
            return b""

    def write_blocking(self, data: bytes) -> None:
        if not self._chan.closed:
            self._chan.sendall(data)

    def resize_blocking(self, cols: int, rows: int) -> None:
        try:
            self._chan.resize_pty(width=cols, height=rows)
        except Exception:  # noqa: BLE001
            pass

    def close(self) -> None:
        try:
            self._chan.close()
        except Exception:  # noqa: BLE001
            pass


class LXDAdapter(RuntimeAdapter):
    def __init__(self, host: str, user: str, key_path: str | None = None, port: int = 22) -> None:
        self._host, self._user, self._port = host, user, port
        self._key = key_path or os.path.join(os.path.expanduser("~"), ".ssh", "id_ed25519")
        self._client: paramiko.SSHClient | None = None
        self._lock = threading.Lock()
        self._terminals: dict[str, SSHPTY] = {}

    # ------------------------------------------------------------------- ssh
    def _connected(self) -> paramiko.SSHClient:
        with self._lock:
            c = self._client
            if c is not None:
                t = c.get_transport()
                if t is not None and t.is_active():
                    return c
            c = paramiko.SSHClient()
            c.load_system_host_keys()
            c.set_missing_host_key_policy(paramiko.RejectPolicy())  # неизвестный хост — отказ, а не доверие «по умолчанию»
            c.connect(
                self._host, port=self._port, username=self._user, key_filename=self._key,
                look_for_keys=False, allow_agent=False, timeout=10, banner_timeout=15, auth_timeout=15,
            )
            transport = c.get_transport()
            assert transport is not None
            transport.set_keepalive(30)
            self._client = c
            return c

    def _open(self) -> paramiko.Channel:
        transport = self._connected().get_transport()
        assert transport is not None
        return transport.open_session()

    def _run(self, command: str, timeout: float = 60, stdin: bytes | None = None) -> tuple[int, bytes]:
        chan = self._open()
        chan.settimeout(timeout)
        chan.exec_command(command)
        if stdin is not None:
            chan.sendall(stdin)
        chan.shutdown_write()
        out = bytearray()
        deadline = time.monotonic() + timeout
        while True:
            try:
                data = chan.recv(65536)
            except TimeoutError:
                chan.close()
                return 124, bytes(out)
            if not data:
                break
            out += data
            if len(out) > 4 * 1024 * 1024 or time.monotonic() > deadline:
                chan.close()
                return 124, bytes(out)
        return chan.recv_exit_status(), bytes(out)

    async def _arun(self, command: str, timeout: float = 60, stdin: bytes | None = None) -> tuple[int, bytes]:
        return await asyncio.to_thread(self._run, command, timeout, stdin)

    # ---------------------------------------------------------------- create
    async def create(
        self,
        session_id: str,
        image: ImageRef,
        limits: ResourceLimits,
        writable_dirs: list[str],
        setup_script: bytes,
        setup_timeout: int,
    ) -> str:
        name = f"upskill-{session_id}"
        if not _NAME_RE.match(name):
            raise RuntimeError_("BAD_SESSION")
        net = net_name(session_id)
        fp = image.image_id.removeprefix("sha256:")
        if not re.fullmatch(r"[0-9a-f]{64}", fp):
            raise RuntimeError_("IMAGE_MISMATCH", image.tag)
        rc, _ = await self._arun(f"lxc image info {fp} >/dev/null 2>&1")
        if rc != 0:
            raise RuntimeError_("IMAGE_MISSING", image.tag)
        now = int(time.time())
        try:
            # параллельное создание сетей иногда конфликтует по автоподсети: повторяем с паузой
            for attempt in range(3):
                rc, out = await self._arun(
                    f"lxc network create {net} ipv4.address=auto ipv4.nat=false ipv4.routing=false ipv4.dhcp=true "
                    f"ipv6.address=none dns.mode=none"
                )
                if rc == 0:
                    break
                await self._arun(f"lxc network delete {net} </dev/null >/dev/null 2>&1")
                await asyncio.sleep(1 + attempt)
            if rc != 0:
                raise RuntimeError_("LXD_NETWORK_FAILED", out.decode(errors="replace")[:300])
            for _ in range(3):  # под нагрузкой запуск иногда обрывается: чистим следы и повторяем
                rc, out = await self._arun(
                    f"lxc launch {fp} {name} -p {PROFILE} --network {net} "
                    f"-c user.upskill.managed=true -c user.upskill.session_id={session_id} -c user.upskill.network={net} "
                    f"-c user.upskill.created_at={now} -c user.upskill.expires_at={now + limits.ttl_seconds + 120}",
                    timeout=120,
                )
                if rc == 0:
                    break
                await self._arun(f"lxc delete -f {name} </dev/null >/dev/null 2>&1")
                await asyncio.sleep(2)
            if rc != 0:
                raise RuntimeError_("LXD_LAUNCH_FAILED", out.decode(errors="replace")[-300:])
            await self._wait_booted(name)
            if setup_script.strip():
                code, output = await self._exec_script(name, setup_script, user="root", timeout=setup_timeout)
                if code != 0:
                    tail = output.decode(errors="replace")[-300:]
                    log.error("setup failed", extra={"session_id": session_id, "exit_code": code, "output": tail})
                    raise RuntimeError_("SETUP_FAILED", output.decode(errors="replace")[:500])
        except BaseException:
            await self.destroy(name)
            raise
        return name

    async def _wait_booted(self, name: str, timeout: float = 60) -> None:
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            rc, out = await self._arun(f"lxc exec {name} -- systemctl is-system-running", timeout=15)
            if out.decode().strip() in ("running", "degraded"):
                return
            await asyncio.sleep(0.3)
        raise RuntimeError_("BOOT_TIMEOUT")

    # --------------------------------------------------------------- scripts
    async def _exec_script(self, name: str, script: bytes, *, user: str, timeout: int) -> tuple[int, bytes]:
        uid = 1000 if user == "student" else 0
        env = STUDENT_ENV if user == "student" else {"HOME": "/root", "LANG": "C.UTF-8", "PATH": STUDENT_ENV["PATH"]}
        env_args = " ".join(f"--env {k}={shlex.quote(v)}" for k, v in env.items())
        cwd = "/home/student" if user == "student" else "/root"
        inner = (
            f"set -o pipefail; /usr/bin/timeout -k 2 {int(timeout)} /bin/bash -c 'eval \"$(base64 -d)\"' 2>&1 "
            f"| head -c {MAX_OUTPUT}"
        )
        cmd = f"lxc exec {name} --user {uid} --group {uid} --cwd {cwd} {env_args} -- /bin/bash -c {shlex.quote(inner)}"
        # скрипт идёт через stdin отдельного канала: ни в файловой системе машины, ни в argv её процессов
        return await self._arun(cmd, timeout=timeout + 20, stdin=base64.b64encode(script))

    async def snapshot_or_inspect(self, runtime_ref: str, validator_script: bytes, timeout: int) -> ValidationContext:
        self._check(runtime_ref)
        code, out = await self._exec_script(runtime_ref, validator_script, user="root", timeout=timeout)
        return ValidationContext(out.decode(errors="replace"), code, code in (124, 137))

    async def exercise(self, runtime_ref: str, script: bytes, timeout: int) -> ValidationContext:
        self._check(runtime_ref)
        code, out = await self._exec_script(runtime_ref, script, user="student", timeout=timeout)
        return ValidationContext(out.decode(errors="replace"), code, code in (124, 137))

    async def reboot(self, runtime_ref: str) -> None:
        self._check(runtime_ref)
        pty = self._terminals.pop(runtime_ref, None)
        if pty:
            pty.close()  # shell ученика завершится вместе с машиной
        rc, out = await self._arun(f"lxc restart {runtime_ref} --timeout 20", timeout=60)
        if rc != 0:
            raise RuntimeError_("REBOOT_FAILED", out.decode(errors="replace")[:200])
        await self._wait_booted(runtime_ref, timeout=60)

    # -------------------------------------------------------------- terminal
    async def attach_terminal(self, runtime_ref: str) -> PTYStream:
        self._check(runtime_ref)
        pty = await asyncio.to_thread(self._attach_sync, runtime_ref)
        self._terminals[runtime_ref] = pty
        return pty

    def _attach_sync(self, name: str) -> SSHPTY:
        env_args = " ".join(f"--env {k}={shlex.quote(v)}" for k, v in {**STUDENT_ENV, "TERM": "xterm-256color"}.items())
        chan = self._open()
        chan.get_pty(term="xterm-256color", width=80, height=24)
        chan.exec_command(f"lxc exec {name} --user 1000 --group 1000 --cwd /home/student {env_args} -- /bin/bash -l")
        return SSHPTY(chan)

    async def resize_terminal(self, runtime_ref: str, cols: int, rows: int) -> None:
        pty = self._terminals.get(runtime_ref)
        if pty:
            await asyncio.to_thread(pty.resize_blocking, cols, rows)

    # ------------------------------------------------------------- lifecycle
    @staticmethod
    def _check(name: str) -> None:
        if not _NAME_RE.match(name):
            raise RuntimeError_("BAD_RUNTIME_REF")

    async def destroy(self, runtime_ref: str) -> None:
        if not _NAME_RE.match(runtime_ref):
            return
        pty = self._terminals.pop(runtime_ref, None)
        if pty:
            pty.close()
        net = net_name(runtime_ref.removeprefix("upskill-"))
        await self._arun(f"lxc delete -f {runtime_ref}", timeout=60)  # идемпотентно: «не найдено» — не ошибка
        await self._arun(f"lxc network delete {net}", timeout=30)

    async def is_alive(self, runtime_ref: str) -> bool:
        if not _NAME_RE.match(runtime_ref):
            return False
        rc, out = await self._arun(f"lxc list {runtime_ref} -c s --format csv", timeout=20)
        return rc == 0 and out.decode().strip() == "RUNNING"

    async def exists(self, runtime_ref: str) -> bool:
        if not _NAME_RE.match(runtime_ref):
            return False
        rc, out = await self._arun(f"lxc list {runtime_ref} -c n --format csv", timeout=20)
        return rc == 0 and runtime_ref in out.decode().split()

    async def list_runtimes(self) -> list[RuntimeInfo]:
        rc, out = await self._arun("lxc list --format json", timeout=30)
        if rc != 0:
            raise RuntimeError_("LXD_UNAVAILABLE", out.decode(errors="replace")[:200])
        items: list[dict[str, Any]] = json.loads(out.decode() or "[]")
        result = []
        for it in items:
            cfg = it.get("config", {})
            if cfg.get("user.upskill.managed") != "true":
                continue
            result.append(
                RuntimeInfo(
                    runtime_ref=it["name"],
                    session_id=cfg.get("user.upskill.session_id", ""),
                    expires_at=float(cfg.get("user.upskill.expires_at", "0")),
                    created_at=float(cfg.get("user.upskill.created_at", "0")),
                    running=it.get("status") == "Running",
                )
            )
        return result

    async def gc_networks(self) -> int:
        """Удалить учебные сети `lab*`, в которых не осталось машин (после сбоев worker)."""
        rc, out = await self._arun("lxc network list --format json", timeout=30)
        if rc != 0:
            return 0
        removed = 0
        for n in json.loads(out.decode() or "[]"):
            if _NET_RE.match(n["name"]) and not n.get("used_by"):
                code, _ = await self._arun(f"lxc network delete {n['name']}", timeout=30)
                removed += code == 0
        return removed

    def close(self) -> None:
        for pty in self._terminals.values():
            pty.close()
        if self._client is not None:
            self._client.close()


def default_key_path() -> str:
    return str(Path.home() / ".ssh" / "id_ed25519")
