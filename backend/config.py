from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

if os.getenv("GOOGLE_API_KEY") and os.getenv("GEMINI_API_KEY"):
    os.environ.pop("GEMINI_API_KEY", None)


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Fashion AI").strip() or "Fashion AI"
    api_prefix: str = os.getenv("API_PREFIX", "/api").strip() or "/api"
    dataset_path: str = os.getenv("DATASET_PATH", "fashion_ai_dataset_50000.csv").strip()
    google_api_key: str = os.getenv("GOOGLE_API_KEY", os.getenv("GEMINI_API_KEY", "")).strip()
    google_model: str = os.getenv("GOOGLE_MODEL", os.getenv("GENAI_MODEL", "models/gemini-2.0-flash")).strip()
    allowed_origins_raw: str = os.getenv(
        "ALLOWED_ORIGINS",
        "http://127.0.0.1:8000,http://localhost:8000",
    ).strip()
    vector_cache_path: str = os.getenv("VECTOR_CACHE_PATH", "trained_models/fashion_vector_index.joblib").strip()
    lstm_model_path: str = os.getenv("LSTM_MODEL_PATH", "trained_models/fashion_lstm.keras").strip()
    lstm_metadata_path: str = os.getenv("LSTM_METADATA_PATH", "trained_models/fashion_lstm_metadata.json").strip()
    llm_cooldown_seconds: int = int(os.getenv("LLM_COOLDOWN_SECONDS", "20").strip())

    @property
    def allowed_origins(self) -> list[str]:
        return [item.strip() for item in self.allowed_origins_raw.split(",") if item.strip()]

    @property
    def dataset_file(self) -> Path:
        return Path(self.dataset_path)

    @property
    def vector_cache_file(self) -> Path:
        return Path(self.vector_cache_path)

    @property
    def lstm_model_file(self) -> Path:
        return Path(self.lstm_model_path)

    @property
    def lstm_metadata_file(self) -> Path:
        return Path(self.lstm_metadata_path)


settings = Settings()
