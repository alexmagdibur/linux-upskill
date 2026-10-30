"""Генератор файлов content/labs/* из компактных спецификаций (specs_*.py).

    python infra/scripts/labgen/generate.py

Результат — обычные файлы в репозитории (manifest.yaml, setup, checks, hints, README, tests); сами файлы
являются источником правды, генератор нужен только для массового создания и единообразия.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
import specs_admin  # noqa: E402
import specs_basics  # noqa: E402
import specs_incidents  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
LABS = ROOT / "content" / "labs"
PREAMBLE = 'chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }\n'
MODULES = [
    ("linux-basics", "Linux Basics", "Файловая система, файлы, потоки, поиск, pipes, архивы и текстовые фильтры.",
     ["linux-001"]),
    ("administration", "Administration", "Права доступа, группы, окружение, процессы, диск и автоматизация.", []),
    ("incidents", "Incident Simulation", "Диагностика и устранение искусственно созданных неисправностей.", []),
]


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.lstrip("\n") if path.suffix == ".sh" else text, encoding="utf-8", newline="\n")


def main() -> None:
    mods = {m[0]: list(m[3]) for m in MODULES}
    for spec in [*specs_basics.SPECS, *specs_admin.SPECS, *specs_incidents.SPECS]:
        lab_id = spec["id"]
        d = LABS / lab_id
        runtime = {"type": "container", "image": "ubuntu-basic", "timeout_seconds": 1800}
        if spec.get("writable_dirs"):
            runtime["writable_dirs"] = spec["writable_dirs"]
        validation: dict = {"type": "script", "script": "checks/validate.sh", "timeout_seconds": 15}
        if spec.get("exercise"):
            validation["exercise_script"] = "checks/exercise.sh"
        validation["checks"] = [
            {"id": cid, "title": title, "pass_message": ok, "fail_message": fail}
            for cid, title, ok, fail in spec["checks"]
        ]
        manifest = {
            "schema_version": 1, "id": lab_id, "version": 1, "title": spec["title"], "mode": spec["mode"],
            "difficulty": spec["difficulty"], "estimated_minutes": spec["minutes"], "description": spec["description"],
            "skills": spec["skills"], "objectives": spec["objectives"], "task": spec["task"], "runtime": runtime,
            "setup": {"script": "setup/prepare.sh"}, "validation": validation, "reward": {"base_xp": spec["xp"]},
        }
        write(d / "manifest.yaml", yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False, width=110))
        write(d / "setup" / "prepare.sh", spec["setup"])
        write(d / "checks" / "validate.sh", PREAMBLE + spec["validate"].lstrip("\n"))
        if spec.get("exercise"):
            write(d / "checks" / "exercise.sh", spec["exercise"])
        write(d / "hints" / "hints.yaml", yaml.safe_dump(spec["hints"], allow_unicode=True, width=110))
        write(d / "README.md",
              f"# {lab_id} — {spec['title']}\n\n{spec['mode'].capitalize()}, {spec['difficulty']}, ~{spec['minutes']} мин, "
              f"{spec['xp']} XP.\n\n{spec['description']}\n\n## Тесты\n\n- `tests/solution.sh` — эталонное решение (должно проходить);\n"
              f"- `tests/wrong.sh` — типичная ошибка (не должно проходить);\n- `tests/alt_*.sh` — альтернативные способы решения (должны проходить).\n")
        write(d / "tests" / "solution.sh", spec["solution"])
        write(d / "tests" / "wrong.sh", spec["wrong"])
        for name, script in spec.get("alt", {}).items():
            write(d / "tests" / f"{name}.sh", script)
        mods[spec["module"]].append(lab_id)

    course = {
        "slug": "linux-upskill",
        "title": "Linux Upskill: от командной строки к диагностике",
        "description": "Практический курс: Learn → Practice → Incident. Реальные команды в изолированной Linux-песочнице и автоматическая проверка результата.",
        "modules": [{"slug": s, "title": t, "description": desc, "labs": mods[s]} for s, t, desc, _ in MODULES],
    }
    write(ROOT / "content" / "courses" / "linux-upskill" / "course.yaml",
          yaml.safe_dump(course, allow_unicode=True, sort_keys=False, width=110))
    print({k: len(v) for k, v in mods.items()})


if __name__ == "__main__":
    main()
