from __future__ import annotations

from backend.models import ChatRequest, ChatResponse, ChatMessage, UserPreferences
from backend.services.llm_service import generate_llm_recommendation, is_llm_enabled, is_llm_temporarily_blocked
from backend.services.recommendation_service import build_dataset_recommendation, build_stylist_reply
from backend.services.session_service import get_or_create_session, known_slots, merge_preferences, remember_turns
from backend.services.vector_store_service import retrieve_recommendations
from backend.utils.parsing import extract_preferences, is_greeting, is_thanks, looks_like_style_request, needs_clarification


def _history_payload(history: list[ChatMessage]) -> list[dict[str, str | None]]:
    return [item.model_dump() for item in history[-10:]]


def _empty_preferences() -> UserPreferences:
    return UserPreferences()


def _conversation_response(session_id: str, reply: str, preferences: UserPreferences, pending_slot: str | None = None) -> ChatResponse:
    return ChatResponse(
        reply=reply,
        recommendation=None,
        preferences=preferences,
        retrieved_items=[],
        source="conversation",
        warnings=[],
        needs_clarification=False,
        clarification_question=None,
        session_id=session_id,
        pending_slot=pending_slot,
        known_slots=known_slots(preferences),
    )


def _clarification_response(session_id: str, preferences: UserPreferences, question: str, pending_slot: str) -> ChatResponse:
    return ChatResponse(
        reply=question,
        recommendation=None,
        preferences=preferences,
        retrieved_items=[],
        source="clarification",
        warnings=[],
        needs_clarification=True,
        clarification_question=question,
        session_id=session_id,
        pending_slot=pending_slot,
        known_slots=known_slots(preferences),
    )


def generate_chat_response(request: ChatRequest) -> ChatResponse:
    session = get_or_create_session(request.session_id)
    remember_turns(session, request.history)
    message = request.message.strip()

    if is_greeting(message):
        if session.preferences.occasion != "Not specified" or session.preferences.budget != "Not specified":
            reply = (
                f"Hi again. I still have your {session.preferences.occasion.lower() if session.preferences.occasion != 'Not specified' else 'look'} in mind"
                f" with a budget of {session.preferences.budget.lower() if session.preferences.budget != 'Not specified' else 'not specified yet'}. "
                "Tell me what you want to refine next, or give me a fresh occasion and budget."
            )
        else:
            reply = "Hi, I can help you build a look or refine one you already have. Tell me the occasion, budget, and the style mood you want."
        return _conversation_response(session.session_id, reply, session.preferences, pending_slot=session.pending_slot)

    if is_thanks(message):
        return _conversation_response(
            session.session_id,
            "Glad to help. If you want, I can refine the outfit by color palette, footwear, layering, or budget.",
            session.preferences,
            pending_slot=session.pending_slot,
        )

    extracted = extract_preferences(request, pending_slot=session.pending_slot)
    preferences = merge_preferences(session.preferences, extracted)

    active_session = any(value != "Not specified" for value in session.preferences.model_dump().values())
    if not looks_like_style_request(message) and not active_session and all(
        value == "Not specified" for value in preferences.model_dump().values()
    ):
        return _conversation_response(
            session.session_id,
            "I can help with outfit planning, styling tweaks, and occasion-based recommendations. Tell me where you're going and what budget I should work within.",
            preferences,
            pending_slot=session.pending_slot,
        )

    clarification_needed, question, missing_slot = needs_clarification(preferences)
    session.preferences = preferences

    if clarification_needed and missing_slot is not None:
        session.pending_slot = missing_slot
        return _clarification_response(session.session_id, preferences, question or "Tell me a bit more.", missing_slot)

    session.pending_slot = None
    retrieval_query = " ".join(
        part for part in [message, preferences.occasion, preferences.budget, preferences.style_preference, preferences.color_preference] if part and part != "Not specified"
    )
    matches = retrieve_recommendations(preferences, retrieval_query or message, limit=5)
    dataset_recommendation = build_dataset_recommendation(preferences, matches)
    recommendation = dataset_recommendation
    source = "dataset-fallback"
    warnings: list[str] = []

    blocked, remaining = is_llm_temporarily_blocked()
    if blocked:
        warnings.append(
            f"Gemini is temporarily cooling down after a quota limit, so Fashion AI is staying in dataset mode for about {remaining} more seconds."
        )
    elif is_llm_enabled():
        try:
            recommendation = generate_llm_recommendation(
                user_message=message,
                preferences=preferences,
                matches=matches,
                history=_history_payload(request.history),
            )
            source = "llm"
        except Exception as exc:
            warnings.append(str(exc))
    else:
        warnings.append("GOOGLE_API_KEY is not configured. Using dataset-grounded recommendations.")

    if source == "dataset-fallback":
        warnings.append("Using dataset-grounded fallback recommendation logic.")

    session.last_recommendation_title = recommendation.recommendation_title
    return ChatResponse(
        reply=build_stylist_reply(recommendation, preferences),
        recommendation=recommendation,
        preferences=preferences,
        retrieved_items=matches,
        source=source,
        warnings=warnings,
        needs_clarification=False,
        clarification_question=None,
        session_id=session.session_id,
        pending_slot=None,
        known_slots=known_slots(preferences),
    )
