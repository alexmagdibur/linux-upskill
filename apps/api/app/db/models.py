"""Единая точка импорта моделей для Alembic и тестов."""

from app.modules.auth.models import AuthSession
from app.modules.courses.models import Course, Module
from app.modules.labs.models import Lab, LabVersion
from app.modules.progress.models import UserProgress, XpTransaction
from app.modules.sessions.models import IdempotencyKey, LabSession
from app.modules.users.models import User
from app.modules.validation.models import ValidationAttempt

__all__ = [
    "AuthSession",
    "Course",
    "IdempotencyKey",
    "Lab",
    "LabSession",
    "LabVersion",
    "Module",
    "User",
    "UserProgress",
    "ValidationAttempt",
    "XpTransaction",
]
