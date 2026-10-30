"""Генератор content/labs/* и course.yaml из учебной программы и компактных спецификаций.

    python infra/scripts/labgen/parse_program.py     # Linux_upskill_200_Detailed_Learning_Program.md -> content/program/lessons.json
    python infra/scripts/labgen/generate.py          # lessons.json + specs_*.py -> content/labs/*, content/courses/*

Результат — обычные файлы в репозитории (источник правды); генератор нужен для массового создания и единообразия.
Уроки без спецификации (VM/несколько узлов) получают манифест `availability: requires_*` без исполняемой части.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
import specs_admin  # noqa: E402
import specs_basics  # noqa: E402
import specs_incidents  # noqa: E402
import specs_program_a  # noqa: E402
import specs_program_b  # noqa: E402
import specs_program_c  # noqa: E402
import specs_vm_1  # noqa: E402
import specs_vm_2  # noqa: E402
import specs_vm_3  # noqa: E402
import specs_vm_4  # noqa: E402
import specs_vm_5  # noqa: E402
import specs_vm_6  # noqa: E402
import specs_vm_7  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
LABS = ROOT / "content" / "labs"
LESSONS = ROOT / "content" / "program" / "lessons.json"
PREAMBLE = 'chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }\n'

STAGES = {
    "Этап 1. Новичок": ("stage-1-novice", "beginner", 50, "Терминал, файлы, справка, потоки и простые права."),
    "Этап 2. Джун": ("stage-2-junior", "junior", 100, "Самостоятельная работа с файлами, текстом, правами, процессами и первичной диагностикой."),
    "Этап 3. Мидл": ("stage-3-middle", "middle", 150, "Эксплуатация сервисов, разбор сбоев, автоматизация и восстановление."),
    "Этап 4. Синьор": ("stage-4-senior", "senior", 200, "Межслойные причины, надёжные изменения, аварийное восстановление и postmortem."),
}
MODE = {"L": "learn", "P": "practice", "I": "incident", "C": "practice"}
MINUTES = {"L": 10, "P": 15, "I": 20, "C": 30}
AVAILABILITY = {"V": "requires_vm", "N": "requires_cluster", "D": "requires_vm_container_runtime"}
# Уроки, которые нельзя выполнить без настоящей виртуальной машины (своё ядро, загрузка, блочные устройства,
# ядерные журналы/аудит/perf/eBPF): исключены из курса. См. docs/architecture/vm-labs.md.
REMOVED = {
    41, 42, 43, 44, 45, 47, 48,          # загрузка и ядро
    58, 62, 191,                         # ядерный журнал OOM, синхронизация и смена системных часов
    65, 66, 67, 68, 69, 70, 71, 72,      # диски, разделы, LVM, RAID
    74, 78, 79,                          # квоты, ext4/xfs, повреждение ФС
    87, 189,                             # swap, задержки диска
    157, 159, 163, 167,                  # perf, eBPF, SELinux/AppArmor, kernel audit
}
REASON = {
    "V": "Сценарий этого задания (давление на ядро и диск, профилирование, нагрузочные метрики) не удалось воспроизвести на учебной "
         "машине детерминированно: проверка была бы нестабильной. Запуск отключён; описание и критерий сохранены.",
    "N": "Сценарий этого задания (поведение узлов под нагрузкой) не удалось воспроизвести на учебной машине детерминированно: "
         "проверка была бы нестабильной. Запуск отключён; описание и критерий сохранены.",
    "D": "Задание требует контейнерный runtime (Docker/podman) внутри учебной машины. Для этого нужно включить вложенные контейнеры "
         "(security.nesting), что ослабляет изоляцию, поэтому по умолчанию это отключено. Описание и критерий сохранены.",
}


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.lstrip("\n") if path.suffix == ".sh" else text, encoding="utf-8", newline="\n")


def dump(data: object) -> str:
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=110)


def metadata(lesson: dict) -> dict:
    followups = {}
    for key, label in (("quick_return", "Быстрый возврат"), ("mixed_return", "Смешанный возврат"), ("review", "Повторение")):
        if lesson.get(key):
            followups[label] = lesson[key]
    meta = {
        "lesson": lesson["lesson"], "stage": lesson["stage"], "topic": lesson["topic"],
        "task_type": lesson["type"], "environment": lesson["env"],
    }
    for key in ("theory", "prediction", "criterion"):
        if lesson.get(key):
            meta[key] = lesson[key]
    if followups:
        meta["followups"] = followups
    return meta


def short_title(lesson: dict) -> str:
    first = lesson["practice"].split(". ")[0].rstrip(".")
    first = first[:1].upper() + first[1:]
    return first if len(first) <= 90 else first[:87].rsplit(" ", 1)[0] + "…"


MANUAL_REASON = (
    "Результат задания — свободный письменный документ (проект, план, разбор). Автоматическая проверка такого результата "
    "была бы недостоверной, поэтому задание описано, но запуск отключён; критерий успеха сохранён для самопроверки."
)


def availability_of(lesson: dict) -> dict:
    if lesson["type"] == "C":
        return {"availability": "manual_review", "unavailable_reason": MANUAL_REASON}
    return {"availability": AVAILABILITY[lesson["env"]], "unavailable_reason": REASON[lesson["env"]]}


def unavailable_manifest(lesson: dict) -> dict:
    stage = STAGES[lesson["stage"]]
    title = f"{lesson['topic']}: {short_title(lesson)}"
    return {
        "schema_version": 1, "id": lesson["id"].lower(), "version": 1, "title": title, "mode": MODE[lesson["type"]],
        "difficulty": stage[1], "estimated_minutes": MINUTES[lesson["type"]],
        "description": short_title(lesson), "skills": [lesson["topic"]], "objectives": [lesson["criterion"]],
        "task": f"**Задание.** {lesson['practice']}\n\n**Критерий успеха.** {lesson['criterion']}\n",
        **metadata(lesson),
        **availability_of(lesson),
        "reward": {"base_xp": stage[2] + (50 if lesson["type"] in ("I", "C") else 0)},
    }


def available_manifest(spec: dict, lesson: dict) -> dict:
    stage = STAGES[lesson["stage"]]
    lxd = spec.get("runtime_type") == "lxd"  # учебная машина (LXD, systemd, root внутри) вместо Docker-песочницы
    runtime = {"type": "lxd" if lxd else "container", "image": "ubuntu-systemd" if lxd else "ubuntu-basic", "timeout_seconds": 1800}
    if spec.get("writable_dirs") and not lxd:
        runtime["writable_dirs"] = spec["writable_dirs"]
    validation: dict = {"type": "script", "script": "checks/validate.sh", "timeout_seconds": spec.get("validate_timeout", 15)}
    if spec.get("exercise"):
        validation["exercise_script"] = "checks/exercise.sh"
    if spec.get("reboot"):
        validation["reboot_before_validate"] = True
    if spec.get("exercise_timeout"):
        validation["exercise_timeout_seconds"] = spec["exercise_timeout"]
    validation["checks"] = [
        {"id": cid, "title": title, "pass_message": ok, "fail_message": fail} for cid, title, ok, fail in spec["checks"]
    ]
    return {
        "schema_version": 1, "id": spec["id"], "version": spec.get("version", 2), "title": spec["title"],
        "mode": spec.get("mode", MODE[lesson["type"]]), "difficulty": spec.get("difficulty", stage[1]),
        "estimated_minutes": spec.get("minutes", MINUTES[lesson["type"]]),
        "description": spec.get("description", short_title(lesson)), "skills": spec.get("skills", [lesson["topic"]]),
        "objectives": spec.get("objectives", [lesson["criterion"]]), "task": spec["task"],
        **metadata(lesson),
        "runtime": runtime, "setup": {"script": "setup/prepare.sh"}, "validation": validation,
        "reward": {"base_xp": spec.get("xp", stage[2] + (50 if lesson["type"] in ("I", "C") else 0))},
    }


def write_available(spec: dict, lesson: dict) -> None:
    d = LABS / spec["id"]
    write(d / "manifest.yaml", dump(available_manifest(spec, lesson)))
    write(d / "setup" / "prepare.sh", spec["setup"])
    write(d / "checks" / "validate.sh", PREAMBLE + spec["validate"].lstrip("\n"))
    if spec.get("exercise"):
        write(d / "checks" / "exercise.sh", spec["exercise"])
    write(d / "hints" / "hints.yaml", dump(spec["hints"]))
    write(d / "README.md",
          f"# {spec['id']} — {spec['title']}\n\nУрок {lesson['lesson']} · {lesson['stage']} · {lesson['topic']}.\n\n"
          f"## Тесты\n\n- `tests/solution.sh` — эталонное решение (проходит);\n- `tests/wrong.sh` — типичная ошибка (не проходит);\n"
          f"- `tests/alt_*.sh` — альтернативные способы решения (проходят).\n")
    write(d / "tests" / "solution.sh", spec["solution"])
    write(d / "tests" / "wrong.sh", spec["wrong"])
    for name, script in spec.get("alt", {}).items():
        write(d / "tests" / f"{name}.sh", script)


def main() -> None:
    lessons = json.loads(LESSONS.read_text(encoding="utf-8"))
    specs = {s["id"]: s for mod in (specs_basics, specs_admin, specs_incidents, specs_program_a, specs_program_b, specs_program_c, specs_vm_1, specs_vm_2, specs_vm_3, specs_vm_4, specs_vm_5, specs_vm_6, specs_vm_7)
             for s in mod.SPECS}
    unknown = set(specs) - {x["id"].lower() for x in lessons}
    assert not unknown, f"спецификации без урока в программе: {unknown}"

    modules: dict[str, list[str]] = {name: [] for name in STAGES}
    stats = {"available": 0, "described_only": 0, "removed": 0}
    missing: list[str] = []
    number = 0
    for lesson in sorted(lessons, key=lambda x: x["lesson"]):
        lab_id = lesson["id"].lower()
        if lab_id.startswith("ld-") and int(lab_id[3:]) in REMOVED:
            shutil.rmtree(LABS / lab_id, ignore_errors=True)
            stats["removed"] += 1
            continue
        number += 1
        lesson = {**lesson, "lesson": number}  # сквозная нумерация без дыр после исключений
        if lesson["env"] == "C" and lab_id not in specs and not (LABS / lab_id / "setup").is_dir():
            missing.append(lab_id)  # контейнерное задание без спецификации — не публикуем «пустышку»
            continue
        modules[lesson["stage"]].append(lab_id)
        if lab_id in specs:
            write_available(specs[lab_id], lesson)
            stats["available"] += 1
        elif (LABS / lab_id / "setup").is_dir():  # вручную написанная лаборатория (linux-001): только добавляем метаданные
            path = LABS / lab_id / "manifest.yaml"
            m = yaml.safe_load(path.read_text(encoding="utf-8"))
            m.update(metadata(lesson))
            m["version"] = max(m.get("version", 1), 2)
            write(path, dump(m))
            stats["available"] += 1
        else:
            write(LABS / lab_id / "manifest.yaml", dump(unavailable_manifest(lesson)))
            stats["described_only"] += 1

    course = {
        "slug": "linux-upskill",
        "title": "Linux Upskill: от командной строки к диагностике",
        "description": f"Практический курс из {number} заданий: Learn → Practice → Incident. Реальные команды в изолированной песочнице, "
                       "независимая проверка результата; задания, требующие VM или нескольких узлов, описаны, но пока недоступны.",
        "modules": [
            {"slug": STAGES[name][0], "title": name, "description": STAGES[name][3], "labs": labs}
            for name, labs in modules.items()
        ],
    }
    write(ROOT / "content" / "courses" / "linux-upskill" / "course.yaml", dump(course))
    print(stats, {k: len(v) for k, v in modules.items()})
    if missing:
        print(f"ВНИМАНИЕ: нет спецификаций для {len(missing)} контейнерных уроков: {missing}")


if __name__ == "__main__":
    main()
