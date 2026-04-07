from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from uuid import uuid4

from backend.models import ChatMessage, UserPreferences


@dataclass
class SessionMemory:
    session_id: str
    preferences: UserPreferences = field(default_factory=UserPreferences)
    pending_slot: str | None = None
    turns: list[ChatMessage] = field(default_factory=list)
    last_recommendation_title: str | None = None


_STORE: dict[str, SessionMemory] = {}
_LOCK = Lock()


def get_or_create_session(session_id: str | None) -> SessionMemory:
    resolved = session_id or str(uuid4())
    with _LOCK:
        memory = _STORE.get(resolved)
        if memory is None:
            memory = SessionMemory(session_id=resolved)
            _STORE[resolved] = memory
    return memory


def merge_preferences(base: UserPreferences, incoming: UserPreferences) -> UserPreferences:
    payload = base.model_dump()
    for key, value in incoming.model_dump().items():
        if value != "Not specified":
            payload[key] = value
    return UserPreferences(**payload)


def known_slots(preferences: UserPreferences) -> list[str]:
    return [key for key, value in preferences.model_dump().items() if value != "Not specified"]


def remember_turns(memory: SessionMemory, history: list[ChatMessage]) -> None:
    if not history:
        return
    recent = history[-12:]
    memory.turns = recent
