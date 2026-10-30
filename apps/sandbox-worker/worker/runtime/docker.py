"""DockerAdapter: жёстко ограниченные контейнеры без привилегий, сети и host-монтирований."""

from __future__ import annotations

import asyncio
import base64
import logging
import time
from typing import Any

import docker
from docker.errors import APIError, ImageNotFound, NotFound
from docker.types import Ulimit

from .base import (
    ImageRef,
    PTYStream,
    ResourceLimits,
    RuntimeAdapter,
    RuntimeError_,
    RuntimeInfo,
    ValidationContext,
)

log = logging.getLogger("worker.docker")

STUDENT_UID = 1000
LABEL_MANAGED = "upskill.managed"
LABEL_SESSION = "upskill.session_id"
LABEL_EXPIRES = "upskill.expires_at"
LABEL_CREATED = "upskill.created_at"
MAX_VALIDATOR_OUTPUT = 65536

BASE_ENV = {
    "HOME": "/home/student",
    "USER": "student",
    "LOGNAME": "student",
    "LANG": "C.UTF-8",
    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
}


class DockerPTY(PTYStream):
    def __init__(self, api: docker.APIClient, exec_id: str, sock: Any) -> None:
        self._api = api
        self._exec_id = exec_id
        self._raw = getattr(sock, "_sock", sock)
        self._sock = sock
        self._closed = False

    def read_blocking(self) -> bytes:
        try:
            return self._raw.recv(65536)
        except Exception:  # noqa: BLE001 — закрытый сокет (OSError, RuntimeError, pywintypes.error) = EOF
            return b""

    def write_blocking(self, data: bytes) -> None:
        if not self._closed:
            self._raw.sendall(data)

    def resize_blocking(self, cols: int, rows: int) -> None:
        try:
            self._api.exec_resize(self._exec_id, height=rows, width=cols)
        except APIError:
            pass

    def close(self) -> None:
        self._closed = True
        for obj in (self._raw, self._sock):
            try:
                obj.close()
            except Exception:  # noqa: BLE001
                pass


class DockerAdapter(RuntimeAdapter):
    def __init__(self) -> None:
        self._client = docker.from_env()
        self._terminals: dict[str, DockerPTY] = {}

    # ------------------------------------------------------------------ create
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
        try:
            await asyncio.to_thread(self._create_and_setup, name, session_id, image, limits, writable_dirs,
                                    setup_script, setup_timeout)
        except BaseException:
            await self.destroy(name)
            raise
        return name

    def _create_and_setup(
        self,
        name: str,
        session_id: str,
        image: ImageRef,
        limits: ResourceLimits,
        writable_dirs: list[str],
        setup_script: bytes,
        setup_timeout: int,
    ) -> None:
        try:
            img = self._client.images.get(image.image_id)
        except ImageNotFound as exc:
            raise RuntimeError_("IMAGE_MISSING", image.tag) from exc
        if img.id != image.image_id:
            raise RuntimeError_("IMAGE_MISMATCH", image.tag)

        tmpfs = {
            "/home/student": f"rw,exec,size={limits.home_size_mb}m,mode=0755,uid={STUDENT_UID},gid={STUDENT_UID},nosuid,nodev",
            "/tmp": f"rw,size={limits.tmp_size_mb}m,mode=1777,nosuid,nodev,noexec",
        }
        for d in writable_dirs:
            tmpfs[d] = f"rw,size=8m,mode=0755,uid={STUDENT_UID},gid={STUDENT_UID},nosuid,nodev,noexec"

        container = self._client.containers.create(
            image=image.image_id,
            command=["/usr/bin/sleep", "infinity"],
            name=name,
            hostname="upskill",
            user="student",
            working_dir="/home/student",
            environment=dict(BASE_ENV),
            read_only=True,
            tmpfs=tmpfs,
            network_mode="none",
            cap_drop=["ALL"],
            security_opt=["no-new-privileges"],
            privileged=False,
            ipc_mode="private",
            pids_limit=limits.pids,
            mem_limit=limits.memory,
            memswap_limit=limits.memory,
            nano_cpus=int(limits.cpu * 1_000_000_000),
            init=True,
            ulimits=[Ulimit(name="nofile", soft=1024, hard=1024), Ulimit(name="core", soft=0, hard=0)],
            log_config={"Type": "none"},
            labels={
                LABEL_MANAGED: "true",
                LABEL_SESSION: session_id,
                LABEL_CREATED: str(int(time.time())),
                LABEL_EXPIRES: str(int(time.time()) + limits.ttl_seconds + 120),
            },
        )
        container.start()

        code, out = self._run_script(container, setup_script, "student", "/home/student", setup_timeout)
        if code != 0:
            log.error("setup failed", extra={"session_id": session_id, "exit_code": code})
            raise RuntimeError_("SETUP_FAILED", (out or b"")[:500].decode(errors="replace"))

    # ---------------------------------------------------------------- terminal
    async def attach_terminal(self, runtime_ref: str) -> PTYStream:
        pty = await asyncio.to_thread(self._attach_sync, runtime_ref)
        self._terminals[runtime_ref] = pty
        return pty

    def _attach_sync(self, runtime_ref: str) -> DockerPTY:
        try:
            container = self._client.containers.get(runtime_ref)
        except NotFound as exc:
            raise RuntimeError_("RUNTIME_GONE") from exc
        api = self._client.api
        env = dict(BASE_ENV, TERM="xterm-256color", COLORTERM="truecolor")
        exec_id = api.exec_create(
            container.id,
            ["/bin/bash", "-l"],
            stdin=True,
            tty=True,
            user="student",
            workdir="/home/student",
            environment=env,
        )["Id"]
        sock = api.exec_start(exec_id, tty=True, socket=True)
        return DockerPTY(api, exec_id, sock)

    async def resize_terminal(self, runtime_ref: str, cols: int, rows: int) -> None:
        pty = self._terminals.get(runtime_ref)
        if pty:
            await asyncio.to_thread(pty.resize_blocking, cols, rows)

    # -------------------------------------------------------------- validation
    async def snapshot_or_inspect(
        self, runtime_ref: str, validator_script: bytes, timeout: int
    ) -> ValidationContext:
        return await asyncio.to_thread(self._validate_sync, runtime_ref, validator_script, timeout)

    def _validate_sync(self, runtime_ref: str, script: bytes, timeout: int) -> ValidationContext:
        try:
            container = self._client.containers.get(runtime_ref)
        except NotFound as exc:
            raise RuntimeError_("RUNTIME_GONE") from exc
        code, out = self._run_script(container, script, "validator", "/", timeout)
        return ValidationContext(
            stdout=(out or b"").decode(errors="replace"), exit_code=code, timed_out=code in (124, 137)
        )

    async def exercise(self, runtime_ref: str, script: bytes, timeout: int) -> ValidationContext:
        def _run() -> ValidationContext:
            try:
                container = self._client.containers.get(runtime_ref)
            except NotFound as exc:
                raise RuntimeError_("RUNTIME_GONE") from exc
            code, out = self._run_script(container, script, "student", "/home/student", timeout)
            return ValidationContext(out.decode(errors="replace"), code, code in (124, 137))

        return await asyncio.to_thread(_run)

    @staticmethod
    def _run_script(container: Any, script: bytes, user: str, workdir: str, timeout: int) -> tuple[int, bytes]:
        """Выполнить доверенный скрипт отдельным процессом под указанным пользователем.

        Скрипт передаётся через переменную окружения exec и исполняется через eval внутри
        обёртки: он не попадает ни в файловую систему, ни в argv (/proc/<pid>/cmdline), а
        /proc/<pid>/environ процесса другого uid недоступен пользователю student.
        """
        wrapper = (
            f"set -o pipefail; /usr/bin/timeout -k 2 {int(timeout)} /bin/bash -c "
            f"'eval \"$(printf %s \"$UPSKILL_SCRIPT\" | base64 -d)\"' 2>&1 | head -c {MAX_VALIDATOR_OUTPUT}"
        )
        env = {
            "PATH": BASE_ENV["PATH"],
            "LANG": "C.UTF-8",
            "HOME": "/home/student" if user == "student" else "/nonexistent",
            "UPSKILL_SCRIPT": base64.b64encode(script).decode(),
        }
        code, out = container.exec_run(["/bin/bash", "-c", wrapper], user=user, workdir=workdir, environment=env)
        return code, out or b""

    # ---------------------------------------------------------------- lifecycle
    async def destroy(self, runtime_ref: str) -> None:
        pty = self._terminals.pop(runtime_ref, None)
        if pty:
            pty.close()
        await asyncio.to_thread(self._destroy_sync, runtime_ref)

    def _destroy_sync(self, runtime_ref: str) -> None:
        try:
            self._client.containers.get(runtime_ref).remove(force=True, v=True)
        except NotFound:
            return
        except APIError as exc:
            if "already in progress" in str(exc) or exc.status_code == 409:
                return
            raise

    async def is_alive(self, runtime_ref: str) -> bool:
        def _check() -> bool:
            try:
                return self._client.containers.get(runtime_ref).status == "running"
            except NotFound:
                return False

        return await asyncio.to_thread(_check)

    async def list_runtimes(self) -> list[RuntimeInfo]:
        def _list() -> list[RuntimeInfo]:
            items = self._client.containers.list(all=True, filters={"label": f"{LABEL_MANAGED}=true"})
            return [
                RuntimeInfo(
                    runtime_ref=c.name,
                    session_id=c.labels.get(LABEL_SESSION, ""),
                    expires_at=float(c.labels.get(LABEL_EXPIRES, "0")),
                    created_at=float(c.labels.get(LABEL_CREATED, "0")),
                    running=c.status == "running",
                )
                for c in items
            ]

        return await asyncio.to_thread(_list)

    def close(self) -> None:
        for pty in self._terminals.values():
            pty.close()
        self._client.close()
