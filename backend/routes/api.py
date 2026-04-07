from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from backend.models import ChatRequest, ChatResponse, HealthResponse, ModelStatusResponse, PreferenceOptionsResponse, TrainLstmResponse
from backend.services.chat_service import generate_chat_response
from backend.services.dataset_service import dataset_ready, preference_options
from backend.services.llm_service import is_llm_enabled
from backend.services.lstm_service import lstm_available, lstm_trained, model_status_message, train_lstm_classifier
from backend.services.vector_store_service import vector_store_status

logger = logging.getLogger("fashion_ai.routes")
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    vector_ready, vector_backend = vector_store_status()
    return HealthResponse(
        status="ok",
        dataset_loaded=dataset_ready(),
        llm_enabled=is_llm_enabled(),
        vector_store_ready=vector_ready,
        vector_backend=vector_backend,
        lstm_ready=lstm_available() and lstm_trained(),
    )


@router.get("/preferences", response_model=PreferenceOptionsResponse)
async def preferences() -> PreferenceOptionsResponse:
    try:
        return preference_options()
    except Exception as exc:
        logger.exception("Preferences route failed")
        raise HTTPException(status_code=500, detail="Could not load preference options.") from exc


@router.get("/model-status", response_model=ModelStatusResponse)
async def model_status() -> ModelStatusResponse:
    vector_ready, vector_backend = vector_store_status()
    return ModelStatusResponse(
        llm_enabled=is_llm_enabled(),
        vector_store_ready=vector_ready,
        vector_backend=vector_backend,
        lstm_available=lstm_available(),
        lstm_trained=lstm_trained(),
        lstm_message=model_status_message(),
    )


@router.post("/train-lstm", response_model=TrainLstmResponse)
async def train_lstm() -> TrainLstmResponse:
    try:
        return train_lstm_classifier()
    except Exception as exc:
        logger.exception("LSTM training failed")
        raise HTTPException(status_code=500, detail="The LSTM classifier could not be trained.") from exc


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        return generate_chat_response(request)
    except Exception as exc:
        logger.exception("Chat route failed")
        raise HTTPException(status_code=500, detail="The chatbot could not generate a response.") from exc


@router.post("/recommend", response_model=ChatResponse)
async def recommend(request: ChatRequest) -> ChatResponse:
    try:
        return generate_chat_response(request)
    except Exception as exc:
        logger.exception("Recommend route failed")
        raise HTTPException(status_code=500, detail="The recommendation engine could not generate a response.") from exc
