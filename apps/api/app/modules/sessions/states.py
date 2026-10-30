"""Конечный автомат сессии (раздел 7 ТЗ). Чистая логика без I/O."""

from __future__ import annotations

CREATED = "CREATED"
PROVISIONING = "PROVISIONING"
READY = "READY"
RUNNING = "RUNNING"
VALIDATING = "VALIDATING"
COMPLETED = "COMPLETED"
FAILED = "FAILED"
STOPPING = "STOPPING"
STOPPED = "STOPPED"
EXPIRED = "EXPIRED"

ACTIVE = frozenset({CREATED, PROVISIONING, READY, RUNNING, VALIDATING})
# статусы, при которых может существовать runtime (учитываются в лимитах)
RUNTIME_HOLDING = ACTIVE | {STOPPING}
TERMINAL = frozenset({COMPLETED, FAILED, STOPPED, EXPIRED})
TERMINAL_USABLE = frozenset({READY, RUNNING})

TRANSITIONS: dict[str, frozenset[str]] = {
    CREATED: frozenset({PROVISIONING, FAILED, STOPPING, EXPIRED}),
    PROVISIONING: frozenset({READY, FAILED, STOPPING, EXPIRED}),
    # READY -> VALIDATING допускается: пользователь может нажать «Проверить», не успев подключить терминал
    READY: frozenset({RUNNING, VALIDATING, FAILED, STOPPING, EXPIRED}),
    RUNNING: frozenset({VALIDATING, FAILED, STOPPING, EXPIRED}),
    VALIDATING: frozenset({RUNNING, COMPLETED, FAILED, STOPPING, EXPIRED}),
    STOPPING: frozenset({STOPPED}),
    COMPLETED: frozenset(),
    FAILED: frozenset(),
    STOPPED: frozenset(),
    EXPIRED: frozenset(),
}


def can_transition(src: str, dst: str) -> bool:
    return dst in TRANSITIONS.get(src, frozenset())


def sources_for(dst: str) -> frozenset[str]:
    return frozenset(s for s, targets in TRANSITIONS.items() if dst in targets)
