"""Разбор Linux_upskill_200_Detailed_Learning_Program.md в структурированный JSON (content/program/lessons.json).

    python infra/scripts/labgen/parse_program.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "Linux_upskill_200_Detailed_Learning_Program.md"
OUT = ROOT / "content" / "program" / "lessons.json"

FIELDS = {
    "Теория": "theory",
    "Перед терминалом": "prediction",
    "Практика": "practice",
    "Критерий успеха": "criterion",
    "Повторение": "review",
    "Быстрый возврат": "quick_return",
    "Смешанный возврат": "mixed_return",
}
FIELD_RE = re.compile(r"^\*\*([^*]+?)\.\*\*\s*(.*)$")


def parse() -> list[dict]:
    lines = SRC.read_text(encoding="utf-8").split("\n")
    lessons: list[dict] = []
    stage = topic = ""
    cur: dict | None = None
    field: str | None = None
    for line in lines:
        if line.startswith("## Этап"):
            stage = line[3:].strip()
            continue
        if line.startswith("### "):
            topic = line[4:].strip()
            continue
        m = re.match(r"#### Урок (\d+) · (\S+) · (.+)", line)
        if m:
            cur = {"lesson": int(m[1]), "id": m[2], "title": m[3].strip(), "stage": stage, "topic": topic, "extra": {}}
            lessons.append(cur)
            field = None
            continue
        if cur is None:
            continue
        if "Тип:" in line and "type" not in cur:
            e = re.search(r"Тип: (\w) · Среда: (\w)", line)
            cur["type"], cur["env"] = (e[1], e[2]) if e else ("P", "C")
            cur["mvp_ready"] = "🟢" in line
            link = re.search(r"\(([^)]*content/labs[^)]*)\)", line)
            cur["mvp_link"] = link[1] if link else None
            field = None
            continue
        fm = FIELD_RE.match(line)
        if fm:
            name = fm[1].strip()
            key = FIELDS.get(name)
            if key is None:
                cur["extra"][name] = fm[2].strip()
                field = f"extra:{name}"
            else:
                cur[key] = fm[2].strip()
                field = key
            continue
        if line.strip() and field and not line.startswith("---"):
            if field.startswith("extra:"):
                k = field[6:]
                cur["extra"][k] = (cur["extra"][k] + " " + line.strip()).strip()
            else:
                cur[field] = (cur.get(field, "") + " " + line.strip()).strip()
    return lessons


if __name__ == "__main__":
    data = parse()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(len(data), "lessons ->", OUT)
