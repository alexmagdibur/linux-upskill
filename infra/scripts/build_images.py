"""Собирает образы песочниц и фиксирует их content-addressed ID в content/images.lock.json."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IMAGES = {"ubuntu-basic": ("upskill/ubuntu-basic:1", ROOT / "sandbox-images" / "ubuntu-basic")}


def main() -> int:
    lock = {}
    for name, (tag, ctx) in IMAGES.items():
        subprocess.run(["docker", "build", "-t", tag, str(ctx)], check=True)
        image_id = subprocess.run(
            ["docker", "image", "inspect", tag, "--format", "{{.Id}}"], check=True, capture_output=True, text=True
        ).stdout.strip()
        lock[name] = {"tag": tag, "id": image_id}
    out = ROOT / "content" / "images.lock.json"
    out.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    print(f"written {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
