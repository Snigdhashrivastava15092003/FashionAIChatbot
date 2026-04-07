from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=1200)
    timestamp: str | None = None

    @field_validator("content")
    @classmethod
    def clean_content(cls, value: str) -> str:
        return " ".join(value.strip().split())


class UserPreferences(BaseModel):
    personality: str = "Not specified"
    budget: str = "Not specified"
    occasion: str = "Not specified"
    place: str = "Not specified"
    season: str = "Not specified"
    weather: str = "Not specified"
    color_preference: str = "Not specified"
    style_preference: str = "Not specified"
    fashion_issue: str = "Not specified"


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=700)
    history: list[ChatMessage] = Field(default_factory=list)
    session_id: str | None = None
    personality: str | None = None
    budget: str | None = None
    occasion: str | None = None
    place: str | None = None
    season: str | None = None
    weather: str | None = None
    color_preference: str | None = None
    style_preference: str | None = None
    fashion_issue: str | None = None

    @field_validator("message")
    @classmethod
    def clean_message(cls, value: str) -> str:
        return " ".join(value.strip().split())


class RecommendationRecord(BaseModel):
    record_id: int
    recommended_outfit_title: str
    occasion: str
    personality: str
    budget_category: str
    season: str
    weather: str
    location_type: str
    color_preference: str
    fashion_issue: str
    topwear: str
    bottomwear: str
    outerwear: str
    footwear: str
    accessories: str
    color_palette: str
    preferred_fabric: str
    pattern: str
    style_vibe: str
    styling_notes: str
    recommendation_reason: str
    confidence_score: float
    retrieval_score: float


class FashionRecommendation(BaseModel):
    recommendation_title: str
    summary: str
    occasion_match: str
    personality_match: str
    budget_fit: str
    main_outfit_items: list[str] = Field(default_factory=list)
    layering: list[str] = Field(default_factory=list)
    footwear: list[str] = Field(default_factory=list)
    accessories: list[str] = Field(default_factory=list)
    color_palette: list[str] = Field(default_factory=list)
    styling_tips: list[str] = Field(default_factory=list)
    optional_alternatives: list[str] = Field(default_factory=list)
    confidence_summary: str


class ChatResponse(BaseModel):
    reply: str
    recommendation: FashionRecommendation | None = None
    preferences: UserPreferences
    retrieved_items: list[RecommendationRecord] = Field(default_factory=list)
    source: Literal["llm", "dataset-fallback", "clarification", "conversation"]
    warnings: list[str] = Field(default_factory=list)
    needs_clarification: bool = False
    clarification_question: str | None = None
    session_id: str
    pending_slot: str | None = None
    known_slots: list[str] = Field(default_factory=list)


class PreferenceOptionsResponse(BaseModel):
    personalities: list[str]
    budgets: list[str]
    occasions: list[str]
    places: list[str]
    seasons: list[str]
    weather: list[str]
    colors: list[str]
    style_vibes: list[str]
    concerns: list[str]


class HealthResponse(BaseModel):
    status: str
    dataset_loaded: bool
    llm_enabled: bool
    vector_store_ready: bool
    vector_backend: str
    lstm_ready: bool


class ModelStatusResponse(BaseModel):
    llm_enabled: bool
    vector_store_ready: bool
    vector_backend: str
    lstm_available: bool
    lstm_trained: bool
    lstm_message: str


class TrainLstmResponse(BaseModel):
    status: str
    message: str
    trained_samples: int = 0
