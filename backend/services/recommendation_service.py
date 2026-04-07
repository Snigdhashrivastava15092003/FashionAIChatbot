from __future__ import annotations

from backend.models import FashionRecommendation, RecommendationRecord, UserPreferences


def _split_values(value: str, *, split_hyphen: bool = False) -> list[str]:
    normalized = value.replace("/", ",")
    if split_hyphen:
        normalized = normalized.replace("-", ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


def _main_items(match: RecommendationRecord) -> list[str]:
    items = []
    for value in [match.topwear, match.bottomwear, match.outerwear]:
        items.extend(_split_values(value))
    return items[:5]


def build_dataset_recommendation(
    preferences: UserPreferences,
    matches: list[RecommendationRecord],
) -> FashionRecommendation:
    if not matches:
        return FashionRecommendation(
            recommendation_title="Flexible Signature Look",
            summary="A versatile foundation outfit designed to stay polished across multiple everyday occasions.",
            occasion_match="This neutral recommendation stays adaptable across semi-formal and everyday settings.",
            personality_match="The styling keeps a clean, balanced silhouette so it can be adapted to the personality direction you prefer.",
            budget_fit="The pieces can be sourced across multiple price points depending on your budget.",
            main_outfit_items=["Tailored top", "Clean trousers or midi skirt"],
            layering=["Light blazer or cardigan"],
            footwear=["Minimal loafers or low heels"],
            accessories=["Structured bag", "Simple jewelry"],
            color_palette=["Black", "Ivory", "Taupe"],
            styling_tips=[
                "Anchor the outfit with one structured piece and one softer texture.",
                "Keep accessories refined so the look stays polished.",
            ],
            optional_alternatives=["Swap the blazer for a knit layer if comfort matters more than formality."],
            confidence_summary="This fallback recommendation was generated without a close dataset retrieval match.",
        )

    primary = matches[0]
    alternative_titles = []
    for item in matches[1:5]:
        if item.recommended_outfit_title != primary.recommended_outfit_title and item.recommended_outfit_title not in alternative_titles:
            alternative_titles.append(item.recommended_outfit_title)
    budget_text = preferences.budget if preferences.budget != "Not specified" else primary.budget_category

    return FashionRecommendation(
        recommendation_title=primary.recommended_outfit_title,
        summary=f"A {primary.style_vibe} outfit direction built around {primary.occasion.lower()} with practical styling choices.",
        occasion_match=primary.recommendation_reason,
        personality_match=f"This leans into a {primary.personality.lower()} fashion direction with {primary.pattern.lower()} detailing and {primary.preferred_fabric.lower()} texture.",
        budget_fit=f"This recommendation is anchored to a {budget_text.lower()} budget target and aligned with similar dataset examples.",
        main_outfit_items=_main_items(primary),
        layering=_split_values(primary.outerwear),
        footwear=_split_values(primary.footwear),
        accessories=_split_values(primary.accessories),
        color_palette=_split_values(primary.color_palette, split_hyphen=True),
        styling_tips=[
            primary.styling_notes,
            f"Use the {primary.color_palette.lower()} palette to keep the outfit cohesive.",
            "Balance one tailored element with one relaxed element to keep the look modern and wearable.",
        ],
        optional_alternatives=alternative_titles,
        confidence_summary=(
            f"Top dataset match confidence {primary.confidence_score:.2f}; retrieval score {primary.retrieval_score:.2f}."
        ),
    )


def build_stylist_reply(recommendation: FashionRecommendation, preferences: UserPreferences) -> str:
    topwear = recommendation.main_outfit_items[0] if recommendation.main_outfit_items else "a polished top"
    footwear = recommendation.footwear[0] if recommendation.footwear else "refined shoes"
    color_theme = ", ".join(recommendation.color_palette[:3]).lower() if recommendation.color_palette else "a clean neutral palette"
    occasion = preferences.occasion.lower() if preferences.occasion != "Not specified" else "your event"
    budget = preferences.budget if preferences.budget != "Not specified" else "your target budget"
    return (
        f"For {occasion}, I would go with the {recommendation.recommendation_title}. Start with {topwear.lower()} and finish with {footwear.lower()}. "
        f"Keep the palette around {color_theme}, which helps the outfit feel polished without pushing past {budget.lower()}. "
        f"If you want, I can also refine this into a bolder, softer, cheaper, or more minimal version."
    )
