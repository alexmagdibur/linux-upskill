"""Готовит VM-хост для учебных LXD-машин и фиксирует образ в content/images.lock.json.

    python infra/scripts/build_lxd_image.py upskilllab@192.168.92.131 [--skip-build]

Выполняет по SSH (вход по ключу): infra/lxd/host-setup.sh (firewall + профиль) и build-base.sh (образ `upskill-ubuntu-systemd`),
затем записывает fingerprint образа в images.lock.json (`runtime: lxd`).
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "content" / "images.lock.json"
ALIAS = "upskill-ubuntu-systemd"


def ssh(target: str, *args: str) -> str:
    out = subprocess.run(["ssh", "-o", "BatchMode=yes", target, *args], check=True, capture_output=True, text=True)
    return out.stdout


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    target, skip = sys.argv[1], "--skip-build" in sys.argv
    for script in ("host-setup.sh", "build-base.sh"):
        if script == "build-base.sh" and skip:
            continue
        subprocess.run(["scp", "-q", "-o", "BatchMode=yes", str(ROOT / "infra" / "lxd" / script), f"{target}:/tmp/{script}"], check=True)
        print(ssh(target, f"sudo bash /tmp/{script}")[-400:])
    fp = ssh(target, f"lxc image info {ALIAS} | awk '/^Fingerprint:/{{print $2}}'").strip()
    assert len(fp) == 64, f"неожиданный fingerprint: {fp!r}"
    lock = json.loads(LOCK.read_text(encoding="utf-8")) if LOCK.exists() else {}
    lock["ubuntu-systemd"] = {"tag": ALIAS, "id": f"sha256:{fp}", "runtime": "lxd"}
    LOCK.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    print("lock updated:", lock["ubuntu-systemd"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
