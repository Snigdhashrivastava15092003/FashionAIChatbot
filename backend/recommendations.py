from __future__ import annotations

from backend.models import ChatRequest, ChatResponse
from backend.services.dataset_service import retrieve_recommendations
from backend.services.llm_service import generate_llm_recommendation, is_llm_enabled
from backend.services.recommendation_service import build_dataset_recommendation, build_dataset_reply
from backend.utils.parsing import extract_preferences


def generate_chat_response(request: ChatRequest) -> ChatResponse:
    preferences = extract_preferences(request)
    matches = retrieve_recommendations(preferences, request.message, limit=5)
    dataset_recommendation = build_dataset_recommendation(preferences, matches)

    recommendation = dataset_recommendation
    source = "dataset-fallback"
    warnings: list[str] = []

    if is_llm_enabled():
        try:
            recommendation = generate_llm_recommendation(request.message, preferences, matches)
            source = "llm"
        except Exception as exc:
            warnings.append(str(exc))
            warnings.append("Using dataset-grounded fallback recommendation logic.")
    else:
        warnings.append("GOOGLE_API_KEY is not configured. Using dataset-grounded fallback recommendation logic.")

    return ChatResponse(
        reply=build_dataset_reply(dataset_recommendation),
        recommendation=recommendation,
        preferences=preferences,
        retrieved_items=matches,
        source=source,
        warnings=warnings,
    )
