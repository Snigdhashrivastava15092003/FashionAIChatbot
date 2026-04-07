from __future__ import annotations

import json
from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate

from backend.models import RecommendationRecord, UserPreferences

PROMPT_PATH = Path("backend/prompts/system_prompt.txt")

OUTPUT_KEYS = {
    "recommendation_title": "string",
    "summary": "string",
    "occasion_match": "string",
    "personality_match": "string",
    "budget_fit": "string",
    "main_outfit_items": ["string"],
    "layering": ["string"],
    "footwear": ["string"],
    "accessories": ["string"],
    "color_palette": ["string"],
    "styling_tips": ["string"],
    "optional_alternatives": ["string"],
    "confidence_summary": "string",
}


def get_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8").strip()


def serialize_examples(matches: list[RecommendationRecord]) -> str:
    payload = [
        {
            "title": item.recommended_outfit_title,
            "occasion": item.occasion,
            "personality": item.personality,
            "budget": item.budget_category,
            "place": item.location_type,
            "weather": item.weather,
            "colors": item.color_palette,
            "vibe": item.style_vibe,
            "notes": item.styling_notes,
            "reason": item.recommendation_reason,
            "score": round(item.retrieval_score, 4),
        }
        for item in matches
    ]
    return json.dumps(payload, indent=2)


def build_prompt(user_message: str, preferences: UserPreferences, matches: list[RecommendationRecord], history: list[dict[str, str]]) -> str:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "{system_prompt}"),
            (
                "human",
                """
Create a polished outfit recommendation for the user.

Latest user message:
{user_message}

Conversation history:
{history_json}

Known user preferences:
{preferences_json}

Retrieved dataset examples:
{examples_json}

Return only JSON with this schema:
{output_schema}

Generation guidance:
- Treat the known preferences as already confirmed.
- Do not ask additional questions.
- If occasion and budget are known, give a full recommendation now.
- Keep the recommendation stylish, practical, and budget-aware.
- Make the summary feel conversational and premium, not robotic.
- Include alternatives only when they add value.
""".strip(),
            ),
        ]
    )
    return prompt.format(
        system_prompt=get_system_prompt(),
        user_message=user_message,
        history_json=json.dumps(history, indent=2),
        preferences_json=preferences.model_dump_json(indent=2),
        examples_json=serialize_examples(matches),
        output_schema=json.dumps(OUTPUT_KEYS, indent=2),
    )
