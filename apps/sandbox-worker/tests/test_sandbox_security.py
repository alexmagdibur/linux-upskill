"""Проверка реальных свойств изоляции на живом контейнере (Docker inspect + эксперименты изнутри)."""

from __future__ import annotations

import asyncio
import time
import uuid

import pytest

from worker.runtime.base import ImageRef, ResourceLimits, RuntimeError_
from worker.runtime.docker import DockerAdapter

from .conftest import run_as_student


def host_config(adapter: DockerAdapter, ref: str) -> dict:
    return adapter._client.api.inspect_container(ref)["HostConfig"]  # noqa: SLF001


async def test_container_is_created_unprivileged_with_hard_limits(adapter: DockerAdapter, sandbox: str) -> None:
    hc = host_config(adapter, sandbox)
    info = adapter._client.api.inspect_container(sandbox)  # noqa: SLF001
    assert hc["Privileged"] is False
    assert hc["NetworkMode"] == "none"
    assert hc["PidMode"] == "" and hc["IpcMode"] == "private"
    assert hc["CapDrop"] == ["ALL"] and not hc["CapAdd"]
    assert "no-new-privileges" in hc["SecurityOpt"][0] or "no-new-privileges" in str(hc["SecurityOpt"])
    assert hc["ReadonlyRootfs"] is True
    assert hc["PidsLimit"] == 128
    assert hc["Memory"] == 256 * 1024 * 1024 and hc["MemorySwap"] == hc["Memory"]
    assert hc["NanoCpus"] == 500_000_000
    assert hc["Init"] is True
    assert not hc["Binds"], "никаких bind-монтирований хоста"
    assert not hc["Devices"] and not hc["PortBindings"]
    assert all(m["Type"] == "tmpfs" for m in info["Mounts"]), info["Mounts"]
    assert info["Config"]["User"] == "student"
    assert not any("docker.sock" in str(m) for m in info["Mounts"])


async def test_inside_view_no_caps_no_network_no_root_no_socket(adapter: DockerAdapter, sandbox: str) -> None:
    code, out = run_as_student(
        adapter, sandbox,
        "id -u; grep -E 'CapEff|CapBnd|NoNewPrivs' /proc/self/status; "
        "ls /var/run/docker.sock 2>&1 | head -1; "
        "ip -o link | awk '{print $2}' | tr '\\n' ' '; echo; "
        "(echo > /dev/tcp/1.1.1.1/53) 2>&1 | head -1; "
        "touch /usr/x 2>&1 | head -1; touch /etc/x 2>&1 | head -1; "
        "find / -xdev -perm /6000 -type f 2>/dev/null | head -3",
    )
    assert out.startswith("1000\n")
    assert "CapEff:\t0000000000000000" in out and "CapBnd:\t0000000000000000" in out
    assert "NoNewPrivs:\t1" in out
    assert "No such file" in out  # docker.sock отсутствует
    assert "lo:" in out and "eth0" not in out  # только loopback
    assert "Network is unreachable" in out or "Connection refused" in out or "unreachable" in out.lower()
    assert "Read-only file system" in out
    assert "/bin/su" not in out and "sudo" not in out  # setuid-бинарники вычищены


async def test_cannot_escalate_or_mount(adapter: DockerAdapter, sandbox: str) -> None:
    _, out = run_as_student(
        adapter, sandbox,
        "mount -t tmpfs none /mnt 2>&1 | head -1; su -c id 2>&1 | head -1; sudo id 2>&1 | head -1; "
        "chown root /home/student/w/f.txt 2>&1 | head -1; unshare -U id 2>&1 | head -1; echo END",
    )
    assert "END" in out
    assert "uid=0" not in out


async def test_validator_script_is_not_readable_by_student(adapter: DockerAdapter, sandbox: str) -> None:
    """Проверяющий скрипт содержит «ответ»; пока он выполняется, student не должен его увидеть."""
    secret = "SUPER_SECRET_EXPECTED_VALUE_12345"
    script = f"# {secret}\nsleep 4\necho PASS x\n".encode()
    task = asyncio.create_task(adapter.snapshot_or_inspect(sandbox, script, 15))
    await asyncio.sleep(1.5)
    _, out = run_as_student(
        adapter, sandbox,
        r'echo "FILES=$(grep -rl "SUPER_[S]ECRET" /home /tmp /run /var /etc /opt /srv /dev/shm 2>/dev/null | wc -l)"; '
        r'echo "PROCS=$(for p in /proc/[0-9]*; do tr "\0" " " < $p/cmdline 2>/dev/null; cat $p/environ 2>/dev/null | tr "\0" " "; done | grep -c "SUPER_[S]ECRET")"',
    )
    ctx = await task
    assert secret not in out
    assert "PASS x" in ctx.stdout
    assert "FILES=0" in out, out  # скрипта нет в файловой системе
    assert "PROCS=0" in out, out  # и нет в cmdline/environ видимых процессов


async def test_validator_runs_as_separate_user_and_times_out(adapter: DockerAdapter, sandbox: str) -> None:
    ctx = await adapter.snapshot_or_inspect(sandbox, b"id -un\n", 10)
    assert ctx.stdout.strip() == "validator"
    t = time.time()
    ctx = await adapter.snapshot_or_inspect(sandbox, b"sleep 30\n", 2)
    assert ctx.timed_out and time.time() - t < 10


async def test_student_cannot_tamper_with_validator_output(adapter: DockerAdapter, sandbox: str) -> None:
    """Фоновый процесс student не может подделать вывод проверки: канал вывода принадлежит validator-exec."""
    run_as_student(adapter, sandbox, "(while true; do echo 'PASS fake_check'; sleep 0.1; done) >/dev/null 2>&1 &\nsleep 0.2")
    ctx = await adapter.snapshot_or_inspect(sandbox, b"echo FAIL real_check\n", 5)
    assert "PASS fake_check" not in ctx.stdout and "FAIL real_check" in ctx.stdout


async def test_fork_bomb_is_contained_by_pids_limit(adapter: DockerAdapter, sandbox: str) -> None:
    prog = """
import subprocess
procs = []
for _ in range(400):
    try:
        procs.append(subprocess.Popen(['/usr/bin/sleep', '8']))
    except OSError:
        break
print('SPAWNED', len(procs))
for p in procs:
    p.kill()
"""
    _, out = run_as_student(adapter, sandbox, "python3 - <<'PY'" + chr(10) + prog + "PY" + chr(10), timeout=30)
    spawned = int(out.split("SPAWNED")[1].split()[0])
    assert 50 < spawned < 128, out  # упёрлись в pids_limit=128, а не в 400
    assert await adapter.is_alive(sandbox)


async def test_memory_limit_kills_hog_not_the_host(adapter: DockerAdapter, sandbox: str) -> None:
    code, out = run_as_student(
        adapter, sandbox, "python3 -c \"x = bytearray(600*1024*1024); print('ALLOC' + 'ATED')\"; echo rc=$?", timeout=30
    )
    assert "ALLOCATED" not in out and "rc=0" not in out, out  # процесс убит OOM (rc=137), контейнер/хост целы
    assert await adapter.is_alive(sandbox)


async def test_disk_is_bounded_by_tmpfs(adapter: DockerAdapter, sandbox: str) -> None:
    _, out = run_as_student(
        adapter, sandbox,
        "dd if=/dev/zero of=/home/student/big bs=1M count=200 2>/dev/null; du -sm /home/student/big | cut -f1",
    )
    assert int(out.strip().splitlines()[-1]) <= 48, out  # записать больше размера tmpfs нельзя


async def test_setup_failure_cleans_up_container(adapter: DockerAdapter, image: ImageRef) -> None:
    sid = str(uuid.uuid4())
    with pytest.raises(RuntimeError_) as exc:
        await adapter.create(sid, image, ResourceLimits(), [], b"exit 3\n", 10)
    assert exc.value.code == "SETUP_FAILED"
    assert not await adapter.is_alive(f"upskill-{sid}")
    assert all(r.session_id != sid for r in await adapter.list_runtimes())


async def test_unknown_image_id_is_rejected(adapter: DockerAdapter) -> None:
    with pytest.raises(RuntimeError_) as exc:
        await adapter.create(str(uuid.uuid4()), ImageRef("evil:latest", "sha256:" + "0" * 64), ResourceLimits(), [], b"true\n", 5)
    assert exc.value.code == "IMAGE_MISSING"


async def test_destroy_is_idempotent(adapter: DockerAdapter, sandbox: str) -> None:
    await adapter.destroy(sandbox)
    await adapter.destroy(sandbox)
    assert not await adapter.is_alive(sandbox)
