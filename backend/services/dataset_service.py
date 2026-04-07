from __future__ import annotations

import math
import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

from backend.config import settings
from backend.models import PreferenceOptionsResponse, RecommendationRecord, UserPreferences

DATA_COLUMNS = [
    "record_id",
    "gender_focus",
    "age_group",
    "personality",
    "budget_category",
    "estimated_total_budget_usd",
    "occasion",
    "season",
    "weather",
    "location_type",
    "fit_preference",
    "color_preference",
    "fashion_issue",
    "recommended_outfit_title",
    "topwear",
    "bottomwear",
    "outerwear",
    "footwear",
    "accessories",
    "color_palette",
    "preferred_fabric",
    "pattern",
    "style_vibe",
    "styling_notes",
    "recommendation_reason",
    "confidence_score",
]

TEXT_COLUMNS = [column for column in DATA_COLUMNS if column not in {"record_id", "age_group", "estimated_total_budget_usd", "confidence_score"}]


def normalize_text(value: object) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    return text


def _budget_bucket(raw_budget: object, estimated_budget: object) -> str:
    text = normalize_text(raw_budget).title()
    if text in {"Low", "Medium", "High", "Luxury"}:
        return text

    try:
        amount = float(estimated_budget)
    except (TypeError, ValueError):
        amount = math.nan

    if not math.isnan(amount):
        if amount <= 100:
            return "Low"
        if amount <= 250:
            return "Medium"
        if amount <= 500:
            return "High"
        return "Luxury"

    return text or "Unknown"


@lru_cache(maxsize=1)
def load_dataset() -> pd.DataFrame:
    dataset_path = Path(settings.dataset_path)
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found at {dataset_path}")

    frame = pd.read_csv(dataset_path)
    missing = [column for column in DATA_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Dataset is missing required columns: {', '.join(missing)}")

    frame = frame[DATA_COLUMNS].copy().fillna("")
    for column in TEXT_COLUMNS:
        frame[column] = frame[column].map(normalize_text)

    frame["budget_bucket"] = [
        _budget_bucket(row["budget_category"], row["estimated_total_budget_usd"])
        for _, row in frame.iterrows()
    ]
    frame["occasion_normalized"] = frame["occasion"].str.lower()
    frame["personality_normalized"] = frame["personality"].str.lower()
    frame["style_vibe_normalized"] = frame["style_vibe"].str.lower()
    frame["retrieval_text"] = (
        frame["recommended_outfit_title"]
        + " "
        + frame["occasion"]
        + " "
        + frame["personality"]
        + " "
        + frame["budget_bucket"]
        + " "
        + frame["season"]
        + " "
        + frame["weather"]
        + " "
        + frame["location_type"]
        + " "
        + frame["color_preference"]
        + " "
        + frame["fashion_issue"]
        + " "
        + frame["style_vibe"]
        + " "
        + frame["preferred_fabric"]
        + " "
        + frame["pattern"]
        + " "
        + frame["styling_notes"]
        + " "
        + frame["recommendation_reason"]
    ).str.lower()
    return frame


def row_to_record(row: pd.Series, retrieval_score: float) -> RecommendationRecord:
    return RecommendationRecord(
        record_id=int(row["record_id"]),
        recommended_outfit_title=str(row["recommended_outfit_title"]),
        occasion=str(row["occasion"]),
        personality=str(row["personality"]),
        budget_category=str(row["budget_bucket"]),
        season=str(row["season"]),
        weather=str(row["weather"]),
        location_type=str(row["location_type"]),
        color_preference=str(row["color_preference"]),
        fashion_issue=str(row["fashion_issue"]),
        topwear=str(row["topwear"]),
        bottomwear=str(row["bottomwear"]),
        outerwear=str(row["outerwear"]),
        footwear=str(row["footwear"]),
        accessories=str(row["accessories"]),
        color_palette=str(row["color_palette"]),
        preferred_fabric=str(row["preferred_fabric"]),
        pattern=str(row["pattern"]),
        style_vibe=str(row["style_vibe"]),
        styling_notes=str(row["styling_notes"]),
        recommendation_reason=str(row["recommendation_reason"]),
        confidence_score=float(row["confidence_score"] or 0.0),
        retrieval_score=retrieval_score,
    )


def dataset_ready() -> bool:
    try:
        load_dataset()
        return True
    except Exception:
        return False


def preference_options() -> PreferenceOptionsResponse:
    frame = load_dataset()

    def top_values(column: str, limit: int = 12) -> list[str]:
        values = [str(item) for item in frame[column].value_counts().head(limit).index.tolist() if str(item).strip()]
        return values

    return PreferenceOptionsResponse(
        personalities=top_values("personality"),
        budgets=top_values("budget_bucket", limit=8),
        occasions=top_values("occasion"),
        places=top_values("location_type"),
        seasons=top_values("season", limit=6),
        weather=top_values("weather", limit=8),
        colors=top_values("color_preference", limit=10),
        style_vibes=top_values("style_vibe", limit=10),
        concerns=top_values("fashion_issue", limit=10),
    )


def build_query_text(preferences: UserPreferences, message: str) -> str:
    parts = [
        message,
        preferences.personality,
        preferences.budget,
        preferences.occasion,
        preferences.place,
        preferences.season,
        preferences.weather,
        preferences.color_preference,
        preferences.style_preference,
        preferences.fashion_issue,
    ]
    return " ".join(part for part in parts if part and part != "Not specified")
