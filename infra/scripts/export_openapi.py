"""Экспорт OpenAPI-схемы API в docs/api/openapi.json (без запуска сервера и подключения к БД)."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.main import create_app  # noqa: E402

out = ROOT / "docs" / "api" / "openapi.json"
out.parent.mkdir(parents=True, exist_ok=True)
schema = create_app(run_background=False).openapi()
out.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"written {out}: {len(schema['paths'])} paths")
