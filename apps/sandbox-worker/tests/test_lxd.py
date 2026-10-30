"""LXDAdapter на реальной VM: изоляция сети, лимиты, PTY, очистка. Пропускаются, если LXD-хост не настроен/недоступен."""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from upskill_content import load_image_lock

from worker.config import WorkerSettings
from worker.runtime.base import ImageRef, ResourceLimits, RuntimeError_
from worker.runtime.lxd import LXDAdapter, net_name

from .conftest import CONTENT


def _settings() -> WorkerSettings:
    return WorkerSettings()


def _lxd_adapter() -> LXDAdapter | None:
    s = _settings()
    if not s.lxd_ssh_host:
        return None
    return LXDAdapter(s.lxd_ssh_host, s.lxd_ssh_user, s.lxd_ssh_key, s.lxd_ssh_port)


def _reachable() -> bool:
    a = _lxd_adapter()
    if a is None:
        return False
    try:
        rc, _ = a._run("lxc version", timeout=15)  # noqa: SLF001
        return rc == 0
    except Exception:  # noqa: BLE001
        return False


pytestmark = pytest.mark.skipif(not _reachable(), reason="LXD-хост (LXD_SSH_HOST) не настроен или недоступен")


@pytest.fixture(scope="module")
def lxd() -> LXDAdapter:
    a = _lxd_adapter()
    assert a is not None
    return a


@pytest.fixture(scope="module")
def image() -> ImageRef:
    e = load_image_lock(CONTENT)["ubuntu-systemd"]
    return ImageRef(e["tag"], e["id"])


async def new_machine(lxd: LXDAdapter, image: ImageRef, setup: bytes = b"true\n") -> tuple[str, str]:
    sid = str(uuid.uuid4())
    ref = await lxd.create(sid, image, ResourceLimits(ttl_seconds=600), [], setup, 30)
    return sid, ref


@pytest_asyncio.fixture
async def machine(lxd: LXDAdapter, image: ImageRef) -> AsyncIterator[tuple[str, str]]:
    sid, ref = await new_machine(lxd, image, b"echo seeded > /home/student/seed.txt; chown student:student /home/student/seed.txt\n")
    yield sid, ref
    await lxd.destroy(ref)


async def as_student(lxd: LXDAdapter, ref: str, script: str, timeout: int = 20) -> str:
    return (await lxd.exercise(ref, script.encode(), timeout)).stdout


async def as_root(lxd: LXDAdapter, ref: str, script: str, timeout: int = 20) -> str:
    return (await lxd.snapshot_or_inspect(ref, script.encode(), timeout)).stdout


async def test_machine_boots_real_systemd_and_runs_setup(lxd: LXDAdapter, machine: tuple[str, str]) -> None:
    _, ref = machine
    out = await as_student(lxd, ref, "echo state=$(systemctl is-system-running); echo uid=$(id -u); cat ~/seed.txt; hostname")
    assert "state=running" in out or "state=degraded" in out
    assert "uid=1000" in out and "seeded" in out and "upskill" in out
    assert await lxd.is_alive(ref) and await lxd.exists(ref)


async def test_root_inside_is_unprivileged_on_host(lxd: LXDAdapter, machine: tuple[str, str]) -> None:
    sid, ref = machine
    out = await as_student(lxd, ref, "sudo -n id -u; cat /proc/self/uid_map; ls /dev/kvm 2>&1 | head -1; ls /var/snap 2>&1 | head -1")
    lines = out.splitlines()
    assert lines[0] == "0"  # root внутри машины (для учебных задач)...
    assert "4294967295" not in out  # ...но user namespace не «0 → 0 на всё»: на хосте это обычный подчинённый uid
    assert "No such file" in out
    # на хосте контейнер непривилегированный, без nesting
    rc, cfg = lxd._run(f"lxc config show {ref} --expanded", timeout=20)  # noqa: SLF001
    text = cfg.decode()
    assert "security.privileged" in text and "security.privileged: \"true\"" not in text
    assert "security.nesting: \"true\"" not in text and "raw.lxc" not in text
    assert "limits.memory: 512MiB" in text and "limits.processes" in text


async def test_network_is_isolated_between_sessions_and_from_host(lxd: LXDAdapter, image: ImageRef) -> None:
    sid_a, a = await new_machine(lxd, image)
    sid_b, b = await new_machine(lxd, image)
    try:
        ip_b = (await as_root(lxd, b, "hostname -I | awk '{print $1}'")).strip()
        gw = (await as_root(lxd, a, "ip route | awk '/default/{print $3}'")).strip()
        assert ip_b and gw
        probes = {
            "other_session": f"ping -c1 -W2 {ip_b}",
            "gateway_ping": f"ping -c1 -W2 {gw}",
            "gateway_ssh": f"timeout 3 bash -c 'echo > /dev/tcp/{gw}/22'",
            "vm_lan_ip": f"ping -c1 -W2 {_settings().lxd_ssh_host}",
            "vmware_gw": "ping -c1 -W2 192.168.92.1",
            "internet": "ping -c1 -W2 1.1.1.1",
            "dns": "timeout 4 getent hosts ubuntu.com",
        }
        script = "\n".join(f"{cmd} >/dev/null 2>&1 && echo {k}=REACHABLE || echo {k}=blocked" for k, cmd in probes.items())
        out = await as_root(lxd, a, script, timeout=40)
        for k in probes:
            assert f"{k}=blocked" in out, out
        # внутри одной сессии (одна сеть) машины видят друг друга — нужно для многоузловых заданий
        sid_c, c = await new_machine(lxd, image)
        await lxd.destroy(c)
        assert net_name(sid_a) != net_name(sid_b)
    finally:
        await lxd.destroy(a)
        await lxd.destroy(b)


async def test_runaway_processes_and_memory_are_contained(lxd: LXDAdapter, machine: tuple[str, str]) -> None:
    _, ref = machine
    out = await as_student(
        lxd, ref,
        "python3 - <<'EOT'\nimport subprocess\nprocs=[]\nfor _ in range(2000):\n    try: procs.append(subprocess.Popen(['sleep','5']))\n"
        "    except OSError: break\nprint('SPAWNED', len(procs))\nfor p in procs: p.kill()\nEOT\n",
        timeout=40,
    )
    spawned = int(out.split("SPAWNED")[1].split()[0])
    assert 50 < spawned < 700, out  # упёрлись в limits.processes=512, а не в 2000
    out = await as_student(lxd, ref, "python3 -c \"x = bytearray(900*1024*1024); print('ALLOC'+'ATED')\"; echo rc=$?", timeout=40)
    assert "ALLOCATED" not in out and "rc=0" not in out, out  # OOM внутри машины, а не на VM
    assert await lxd.is_alive(ref)


async def test_terminal_is_a_real_pty_with_resize(lxd: LXDAdapter, machine: tuple[str, str]) -> None:
    _, ref = machine
    pty = await lxd.attach_terminal(ref)
    try:
        await asyncio.to_thread(pty.resize_blocking, 100, 30)
        await asyncio.to_thread(pty.write_blocking, b"echo START; id -un; stty size; echo END$((6*7))\n")
        buf = b""
        end = time.time() + 20
        while b"END42" not in buf.split(b"echo END")[-1] and time.time() < end:
            buf += await asyncio.to_thread(pty.read_blocking)
        text = buf.decode(errors="replace")
        assert "student" in text and "END42" in text
        assert "30 100" in text  # размер окна дошёл до PTY внутри машины
    finally:
        pty.close()


async def test_validator_script_is_not_stored_in_the_machine(lxd: LXDAdapter, machine: tuple[str, str]) -> None:
    _, ref = machine
    secret = "SUPER_SECRET_LXD_EXPECTED_VALUE"
    task = asyncio.create_task(lxd.snapshot_or_inspect(ref, f"# {secret}\nsleep 4\necho PASS x\n".encode(), 15))
    await asyncio.sleep(2)
    out = await as_student(
        lxd, ref,
        r'echo "FILES=$(grep -rl "SUPER_[S]ECRET_LXD" /home /tmp /etc /var /opt /srv /root 2>/dev/null | wc -l)"; '
        r'echo "ARGV=$(for p in /proc/[0-9]*; do tr "\0" " " < $p/cmdline 2>/dev/null; done | grep -c "SUPER_[S]ECRET_LXD")"',
    )
    ctx = await task
    assert "PASS x" in ctx.stdout and secret not in out
    assert "FILES=0" in out and "ARGV=0" in out, out  # в файлах и в argv видимых процессов скрипта нет


async def test_destroy_removes_machine_and_its_network(lxd: LXDAdapter, image: ImageRef) -> None:
    sid, ref = await new_machine(lxd, image)
    net = net_name(sid)
    assert net in (await asyncio.to_thread(lxd._run, "lxc network list --format csv"))[1].decode()  # noqa: SLF001
    await lxd.destroy(ref)
    await lxd.destroy(ref)  # идемпотентно
    assert not await lxd.exists(ref)
    assert net not in (await asyncio.to_thread(lxd._run, "lxc network list --format csv"))[1].decode()  # noqa: SLF001


async def test_failed_setup_leaves_nothing_behind(lxd: LXDAdapter, image: ImageRef) -> None:
    sid = str(uuid.uuid4())
    with pytest.raises(RuntimeError_) as exc:
        await lxd.create(sid, image, ResourceLimits(), [], b"exit 3\n", 20)
    assert exc.value.code == "SETUP_FAILED"
    assert not await lxd.exists(f"upskill-{sid}")
    assert net_name(sid) not in (await asyncio.to_thread(lxd._run, "lxc network list --format csv"))[1].decode()  # noqa: SLF001


async def test_runtimes_are_listed_and_orphan_networks_are_collected(lxd: LXDAdapter, machine: tuple[str, str]) -> None:
    sid, ref = machine
    found = [r for r in await lxd.list_runtimes() if r.session_id == sid]
    assert len(found) == 1 and found[0].runtime_ref == ref and found[0].running and found[0].expires_at > time.time()
    await asyncio.to_thread(lxd._run, "lxc network create labdeadbeef ipv4.address=auto ipv4.nat=false ipv4.routing=false")  # noqa: SLF001
    assert await lxd.gc_networks() >= 1
    names = (await asyncio.to_thread(lxd._run, "lxc network list --format csv"))[1].decode()  # noqa: SLF001
    assert "labdeadbeef" not in names


async def test_unknown_image_and_malicious_names_are_rejected(lxd: LXDAdapter) -> None:
    with pytest.raises(RuntimeError_) as exc:
        await lxd.create(str(uuid.uuid4()), ImageRef("evil", "sha256:" + "0" * 64), ResourceLimits(), [], b"true\n", 5)
    assert exc.value.code == "IMAGE_MISSING"
    with pytest.raises(RuntimeError_):
        await lxd.create(str(uuid.uuid4()), ImageRef("evil", "sha256:abc; rm -rf /"), ResourceLimits(), [], b"true\n", 5)
    for bad in ("upskill-x; reboot", "../../etc", "upskill-" + "g" * 36, ""):
        with pytest.raises(RuntimeError_):
            await lxd.attach_terminal(bad)
        assert not await lxd.is_alive(bad)
        await lxd.destroy(bad)  # молча игнорируется, ничего не исполняется на хосте


async def test_no_leftover_machines_or_networks_after_suite(lxd: LXDAdapter) -> None:
    rc, out = await asyncio.to_thread(lxd._run, "lxc list --format json")  # noqa: SLF001
    left = [i["name"] for i in json.loads(out.decode()) if i.get("config", {}).get("user.upskill.managed") == "true"]
    assert not left, left
