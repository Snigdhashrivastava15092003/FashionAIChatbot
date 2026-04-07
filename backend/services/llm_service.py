from __future__ import annotations

import json
import logging
import re
import time

from google import genai

from backend.config import settings
from backend.models import FashionRecommendation, RecommendationRecord, UserPreferences
from backend.services.prompt_manager import build_prompt

logger = logging.getLogger("fashion_ai.llm")


class LLMServiceError(RuntimeError):
    def __init__(self, user_message: str, *, retry_after_seconds: int | None = None) -> None:
        super().__init__(user_message)
        self.retry_after_seconds = retry_after_seconds


EXPECTED_ARRAY_FIELDS = {
    "main_outfit_items",
    "layering",
    "footwear",
    "accessories",
    "color_palette",
    "styling_tips",
    "optional_alternatives",
}

EXPECTED_STRING_FIELDS = {
    "recommendation_title",
    "summary",
    "occasion_match",
    "personality_match",
    "budget_fit",
    "confidence_summary",
}

_NEXT_ALLOWED_LLM_ATTEMPT_AT = 0.0


def is_llm_enabled() -> bool:
    return bool(settings.google_api_key)


def is_llm_temporarily_blocked() -> tuple[bool, int | None]:
    remaining = int(max(0, _NEXT_ALLOWED_LLM_ATTEMPT_AT - time.time()))
    if remaining > 0:
        return True, remaining
    return False, None


def _set_llm_cooldown(seconds: int | None) -> None:
    global _NEXT_ALLOWED_LLM_ATTEMPT_AT
    cooldown = max(seconds or settings.llm_cooldown_seconds, settings.llm_cooldown_seconds)
    _NEXT_ALLOWED_LLM_ATTEMPT_AT = time.time() + cooldown


def _get_client() -> genai.Client:
    return genai.Client(api_key=settings.google_api_key)


def _extract_json_object(text: str) -> dict | None:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.replace("json", "", 1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def normalize_llm_error(exc: Exception) -> LLMServiceError:
    message = " ".join(str(exc).split())
    lowered = message.lower()
    retry_match = re.search(r"retry in ([0-9]+(?:\.[0-9]+)?)s", lowered)
    retry_after_seconds = int(float(retry_match.group(1))) if retry_match else None

    if "resource_exhausted" in lowered or "quota exceeded" in lowered:
        detail = "Gemini quota is exhausted right now, so Fashion AI is using dataset-grounded recommendations instead."
        if retry_after_seconds is not None:
            detail += f" Try again in about {retry_after_seconds} seconds."
        return LLMServiceError(detail, retry_after_seconds=retry_after_seconds)

    if "rate limit" in lowered or "too many requests" in lowered:
        detail = "Gemini is rate-limiting requests right now, so Fashion AI switched to dataset-grounded recommendations."
        if retry_after_seconds is not None:
            detail += f" Try again in about {retry_after_seconds} seconds."
        return LLMServiceError(detail, retry_after_seconds=retry_after_seconds)

    if "api key" in lowered or "permission" in lowered or "unauthorized" in lowered:
        return LLMServiceError(
            "Gemini is not available with the current API configuration, so Fashion AI is using dataset-grounded recommendations instead."
        )

    return LLMServiceError("Gemini is temporarily unavailable, so Fashion AI is using dataset-grounded recommendations instead.")


def _coerce_payload(payload: dict) -> FashionRecommendation:
    normalized: dict[str, object] = {}
    for key in EXPECTED_STRING_FIELDS:
        normalized[key] = str(payload.get(key, "")).strip()
    for key in EXPECTED_ARRAY_FIELDS:
        value = payload.get(key, [])
        if isinstance(value, list):
            normalized[key] = [str(item).strip() for item in value if str(item).strip()]
        elif value:
            normalized[key] = [str(value).strip()]
        else:
            normalized[key] = []
    return FashionRecommendation(**normalized)


def generate_llm_recommendation(
    user_message: str,
    preferences: UserPreferences,
    matches: list[RecommendationRecord],
    history: list[dict[str, str]],
) -> FashionRecommendation:
    blocked, remaining = is_llm_temporarily_blocked()
    if blocked:
        raise LLMServiceError(
            f"Gemini is cooling down after a recent quota limit, so Fashion AI is using dataset-grounded recommendations instead. Try again in about {remaining} seconds.",
            retry_after_seconds=remaining,
        )

    client = _get_client()
    prompt = build_prompt(user_message=user_message, preferences=preferences, matches=matches, history=history)

    model_name = settings.google_model
    if model_name.startswith("models/"):
        model_name = model_name[len("models/"):]

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                temperature=0.4,
                response_mime_type="application/json",
            ),
        )
    except Exception as exc:
        normalized = normalize_llm_error(exc)
        if normalized.retry_after_seconds is not None or "quota" in str(normalized).lower() or "rate-limit" in str(normalized).lower() or "rate limit" in str(normalized).lower():
            _set_llm_cooldown(normalized.retry_after_seconds)
        raise normalized from exc

    response_text = response.text or ""
    logger.info("LLM raw response length: %d chars", len(response_text))
    payload = _extract_json_object(response_text)
    if not payload:
        raise LLMServiceError("Gemini returned an unreadable response, so Fashion AI used dataset-grounded recommendations instead.")
    return _coerce_payload(payload)
