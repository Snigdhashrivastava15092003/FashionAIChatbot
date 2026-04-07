from __future__ import annotations

import json
from pathlib import Path

from backend.config import settings
from backend.models import TrainLstmResponse
from backend.services.dataset_service import load_dataset

try:
    from tensorflow.keras.callbacks import EarlyStopping
    from tensorflow.keras.layers import LSTM, Dense, Embedding
    from tensorflow.keras.models import Sequential, load_model
    from tensorflow.keras.preprocessing.sequence import pad_sequences
    from tensorflow.keras.preprocessing.text import Tokenizer
    from tensorflow.keras.utils import to_categorical
except Exception:  # pragma: no cover - optional dependency
    EarlyStopping = None
    LSTM = None
    Dense = None
    Embedding = None
    Sequential = None
    load_model = None
    pad_sequences = None
    Tokenizer = None
    to_categorical = None


MAX_WORDS = 5000
MAX_LEN = 24


def lstm_available() -> bool:
    return all(item is not None for item in [Sequential, LSTM, Embedding, Dense, Tokenizer, pad_sequences, to_categorical])


def lstm_trained() -> bool:
    return Path(settings.lstm_model_path).exists() and Path(settings.lstm_metadata_path).exists()


def model_status_message() -> str:
    if not lstm_available():
        return "TensorFlow is not installed, so the optional LSTM classifier is disabled."
    if not lstm_trained():
        return "The optional LSTM classifier is available but has not been trained yet."
    return "The optional LSTM classifier is trained and ready."


def train_lstm_classifier() -> TrainLstmResponse:
    if not lstm_available():
        return TrainLstmResponse(status="skipped", message="TensorFlow is not installed, so LSTM training is unavailable.")

    frame = load_dataset()
    texts = (frame["occasion"] + " " + frame["personality"] + " " + frame["style_vibe"] + " " + frame["styling_notes"]).tolist()
    labels = sorted(frame["occasion"].astype(str).unique().tolist())
    label_to_index = {label: idx for idx, label in enumerate(labels)}
    y = [label_to_index[str(label)] for label in frame["occasion"].tolist()]

    tokenizer = Tokenizer(num_words=MAX_WORDS, oov_token="<unk>")
    tokenizer.fit_on_texts(texts)
    sequences = tokenizer.texts_to_sequences(texts)
    x = pad_sequences(sequences, maxlen=MAX_LEN, padding="post", truncating="post")
    y_encoded = to_categorical(y, num_classes=len(labels))

    model = Sequential(
        [
            Embedding(MAX_WORDS, 32, input_length=MAX_LEN),
            LSTM(32),
            Dense(len(labels), activation="softmax"),
        ]
    )
    model.compile(optimizer="adam", loss="categorical_crossentropy", metrics=["accuracy"])
    model.fit(
        x,
        y_encoded,
        epochs=2,
        batch_size=64,
        verbose=0,
        callbacks=[EarlyStopping(monitor="loss", patience=1, restore_best_weights=True)],
    )

    Path(settings.lstm_model_path).parent.mkdir(parents=True, exist_ok=True)
    model.save(settings.lstm_model_path)
    Path(settings.lstm_metadata_path).write_text(
        json.dumps(
            {
                "max_words": MAX_WORDS,
                "max_len": MAX_LEN,
                "labels": labels,
                "tokenizer_json": tokenizer.to_json(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return TrainLstmResponse(
        status="trained",
        message="The optional LSTM occasion classifier has been trained.",
        trained_samples=len(texts),
    )
