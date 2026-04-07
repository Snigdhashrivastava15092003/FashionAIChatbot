from __future__ import annotations

import re
from collections.abc import Iterable

from backend.models import ChatRequest, UserPreferences


KEYWORD_MAP = {
    "occasion": [
        "birthday party",
        "birthday",
        "wedding",
        "interview",
        "business casual",
        "office meeting",
        "office",
        "first date",
        "date night",
        "date",
        "vacation",
        "party",
        "formal event",
        "casual outing",
        "streetwear",
        "beach vacation",
    ],
    "season": ["summer", "winter", "autumn", "fall", "spring", "monsoon"],
    "weather": ["rainy", "warm", "hot", "cool", "cold", "humid", "windy"],
    "personality": ["classic", "minimal", "minimalist", "bold", "trendy", "romantic", "edgy", "creative", "polished", "elegant", "classy"],
    "color_preference": ["neutral", "monochrome", "pastel", "bright", "earthy", "dark", "black", "white", "navy", "beige", "red", "blue"],
    "style_preference": ["streetwear", "smart casual", "minimalist", "tailored", "elegant", "bold", "classic", "relaxed", "classy", "glam"],
    "place": ["office", "resort", "beach", "indoor", "outdoor", "campus", "city", "wedding venue", "restaurant", "club"],
    "fashion_issue": [
        "need comfort",
        "need breathable fabric",
        "need layering",
        "want to stand out",
        "too hot",
        "too cold",
        "need weather-ready layering",
        "want a slimmer look",
        "need easy movement",
    ],
}

BUDGET_TERMS = ["low", "medium", "mid-range", "high", "luxury", "budget", "affordable", "student budget"]
BUDGET_FLEX_TERMS = {"both are fine", "either is fine", "anything is fine", "any budget is fine", "whatever works", "either works", "both work", "any is fine"}
GREETING_TERMS = {"hi", "hello", "hey", "hey there", "good morning", "good afternoon", "good evening"}
THANKS_TERMS = {"thanks", "thank you", "perfect", "great", "nice", "cool", "awesome"}
STYLE_REQUEST_TERMS = {
    "outfit",
    "wear",
    "wedding",
    "office",
    "date",
    "vacation",
    "party",
    "style",
    "look",
    "recommend",
    "suggest",
    "dress",
    "clothes",
    "wardrobe",
    "casual",
    "formal",
    "streetwear",
    "birthday",
    "cheaper",
    "classy",
    "elegant",
    "bold",
    "minimal",
    "refine",
    "change",
    "instead",
    "more",
}

SLOT_QUESTIONS = {
    "occasion": "What occasion or event should I style this look for?",
    "budget": "What budget should I work within? Even a rough number like 3000 INR or under $100 is enough.",
    "style_preference": "What mood do you want for the outfit: elegant, bold, minimal, romantic, or something else?",
}


def _titleize(value: str) -> str:
    return " ".join(part.capitalize() for part in value.split())


def _history_user_messages(history: Iterable) -> list[str]:
    messages: list[str] = []
    for item in history:
        role = getattr(item, "role", None)
        content = getattr(item, "content", None)
        if role == "user" and isinstance(content, str) and content.strip():
            messages.append(content.strip())
    return messages


def _history_assistant_messages(history: Iterable) -> list[str]:
    messages: list[str] = []
    for item in history:
        role = getattr(item, "role", None)
        content = getattr(item, "content", None)
        if role == "assistant" and isinstance(content, str) and content.strip():
            messages.append(content.strip())
    return messages


def _last_assistant_message(history: Iterable) -> str:
    messages = _history_assistant_messages(history)
    return messages[-1] if messages else ""


def extract_budget_from_text(message: str, history: Iterable | None = None, pending_slot: str | None = None) -> str | None:
    lowered = message.lower().strip()
    last_assistant = _last_assistant_message(history or []).lower()

    if lowered in BUDGET_FLEX_TERMS and (pending_slot == "budget" or "budget" in last_assistant or "work within" in last_assistant):
        return "Flexible"

    currency_match = re.search(r"\b(?:under|around|about|budget|below|max)\s*(?:inr|rs\.?|usd|\$)?\s*(\d{2,6})\b", lowered)
    if currency_match:
        amount = currency_match.group(1)
        if "usd" in lowered or "$" in lowered:
            return f"Under ${amount}"
        if "inr" in lowered or "rs" in lowered:
            return f"Under INR {amount}"
        return f"Around {amount}"

    money_only_match = re.fullmatch(r"(?:rs\.?\s*)?(\d{2,6})(?:\s*(?:inr|usd|dollars?))?", lowered)
    if money_only_match:
        amount = money_only_match.group(1)
        if pending_slot == "budget" or "budget" in last_assistant or "work within" in last_assistant or "optimize" in last_assistant:
            if "usd" in lowered or "$" in lowered:
                return f"Under ${amount}"
            return f"Under INR {amount}"

    for term in BUDGET_TERMS:
        if term in lowered:
            return _titleize(term.replace("mid-range", "mid range"))
    return None


def is_greeting(message: str) -> bool:
    lowered = " ".join(message.lower().strip().split())
    return lowered in GREETING_TERMS


def is_thanks(message: str) -> bool:
    lowered = " ".join(message.lower().strip().split())
    return lowered in THANKS_TERMS


def looks_like_style_request(message: str) -> bool:
    lowered = message.lower()
    return any(term in lowered for term in STYLE_REQUEST_TERMS) or any(
        keyword in lowered for keywords in KEYWORD_MAP.values() for keyword in keywords
    )


def should_merge_history(request: ChatRequest, pending_slot: str | None = None) -> bool:
    message = request.message.strip()
    if not request.history:
        return False
    if is_greeting(message) or is_thanks(message):
        return False
    if extract_budget_from_text(message, request.history, pending_slot=pending_slot) and len(message.split()) <= 5:
        return True
    if looks_like_style_request(message):
        return False
    return len(message.split()) <= 7


def _combined_text(request: ChatRequest, pending_slot: str | None = None) -> str:
    parts = [request.message]
    if should_merge_history(request, pending_slot=pending_slot):
        history_messages = _history_user_messages(request.history)
        parts = history_messages[-4:] + [request.message]
    return " ".join(part for part in parts if part).strip()


def extract_preferences(request: ChatRequest, pending_slot: str | None = None) -> UserPreferences:
    message = _combined_text(request, pending_slot=pending_slot).lower()

    extracted: dict[str, str] = {
        "personality": request.personality or "Not specified",
        "budget": request.budget or extract_budget_from_text(request.message, request.history, pending_slot=pending_slot) or extract_budget_from_text(message, request.history, pending_slot=pending_slot) or "Not specified",
        "occasion": request.occasion or "Not specified",
        "place": request.place or "Not specified",
        "season": request.season or "Not specified",
        "weather": request.weather or "Not specified",
        "color_preference": request.color_preference or "Not specified",
        "style_preference": request.style_preference or "Not specified",
        "fashion_issue": request.fashion_issue or "Not specified",
    }

    for field_name, keywords in KEYWORD_MAP.items():
        if extracted[field_name] != "Not specified":
            continue
        for keyword in keywords:
            if keyword in message:
                extracted[field_name] = _titleize(keyword.replace("mid-range", "mid range"))
                break

    return UserPreferences(**extracted)


def next_missing_slot(preferences: UserPreferences) -> str | None:
    if preferences.occasion == "Not specified":
        return "occasion"
    if preferences.budget == "Not specified":
        return "budget"
    return None


def needs_clarification(preferences: UserPreferences) -> tuple[bool, str | None, str | None]:
    missing_slot = next_missing_slot(preferences)
    if not missing_slot:
        return False, None, None
    return True, SLOT_QUESTIONS[missing_slot], missing_slot
