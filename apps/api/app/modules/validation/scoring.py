"""Оценивание: Score = 100 * sum(weight_i * passed_i) / sum(weight_i); зачёт — все required проверки пройдены."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any


def compute_score(checks: list[dict[str, Any]], results: dict[str, bool]) -> tuple[Decimal, bool, list[dict[str, Any]]]:
    total = sum(Decimal(str(c["weight"])) for c in checks)
    got = Decimal(0)
    passed_all_required = True
    public: list[dict[str, Any]] = []
    for c in checks:
        ok = bool(results.get(c["id"], False))
        if ok:
            got += Decimal(str(c["weight"]))
        elif c.get("required", True):
            passed_all_required = False
        public.append({"id": c["id"], "passed": ok, "message": c["pass_message"] if ok else c["fail_message"]})
    score = (Decimal(100) * got / total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if total else Decimal(0)
    return score, passed_all_required, public
