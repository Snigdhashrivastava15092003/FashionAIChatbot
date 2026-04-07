from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from backend.config import settings
from backend.models import RecommendationRecord, UserPreferences
from backend.services.dataset_service import build_query_text, load_dataset, row_to_record

try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    faiss = None


class VectorStore:
    def __init__(self, vectorizer: TfidfVectorizer, reducer: TruncatedSVD | None, matrix: np.ndarray, backend: str) -> None:
        self.vectorizer = vectorizer
        self.reducer = reducer
        self.matrix = matrix.astype("float32")
        self.backend = backend
        self.index = None
        if self.backend == "faiss":
            index = faiss.IndexFlatIP(self.matrix.shape[1])
            index.add(self.matrix)
            self.index = index

    def transform_query(self, query: str) -> np.ndarray:
        query_matrix = self.vectorizer.transform([query])
        if self.reducer is not None:
            query_matrix = self.reducer.transform(query_matrix)
        else:
            query_matrix = query_matrix.toarray()
        query_dense = np.asarray(query_matrix, dtype="float32")
        norms = np.linalg.norm(query_dense, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return query_dense / norms

    def search(self, query: str, limit: int = 5) -> list[tuple[int, float]]:
        query_dense = self.transform_query(query)
        if self.backend == "faiss" and self.index is not None:
            scores, indices = self.index.search(query_dense, limit)
            return [(int(index), float(score)) for index, score in zip(indices[0], scores[0], strict=False) if index >= 0]

        similarities = cosine_similarity(query_dense, self.matrix)[0]
        top_indices = similarities.argsort()[::-1][:limit]
        return [(int(index), float(similarities[index])) for index in top_indices]


@lru_cache(maxsize=1)
def get_vector_store() -> VectorStore:
    frame = load_dataset()
    cache_path = Path(settings.vector_cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    dataset_mtime = Path(settings.dataset_path).stat().st_mtime

    if cache_path.exists():
        try:
            cached = joblib.load(cache_path)
            if cached.get("dataset_mtime") == dataset_mtime:
                return VectorStore(
                    vectorizer=cached["vectorizer"],
                    reducer=cached["reducer"],
                    matrix=cached["matrix"],
                    backend="faiss" if faiss is not None else "cosine",
                )
        except Exception:
            pass

    vectorizer = TfidfVectorizer(stop_words="english", max_features=5000, ngram_range=(1, 2))
    sparse_matrix = vectorizer.fit_transform(frame["retrieval_text"].tolist())

    reducer = None
    dense_matrix = sparse_matrix.toarray()
    if sparse_matrix.shape[1] > 128:
        reducer = TruncatedSVD(n_components=128, random_state=42)
        dense_matrix = reducer.fit_transform(sparse_matrix)

    dense_matrix = np.asarray(dense_matrix, dtype="float32")
    norms = np.linalg.norm(dense_matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    dense_matrix = dense_matrix / norms

    joblib.dump(
        {
            "dataset_mtime": dataset_mtime,
            "vectorizer": vectorizer,
            "reducer": reducer,
            "matrix": dense_matrix,
        },
        cache_path,
    )

    return VectorStore(vectorizer=vectorizer, reducer=reducer, matrix=dense_matrix, backend="faiss" if faiss is not None else "cosine")


def vector_store_status() -> tuple[bool, str]:
    try:
        store = get_vector_store()
        return True, store.backend
    except Exception:
        return False, "unavailable"


def retrieve_recommendations(preferences: UserPreferences, message: str, limit: int = 5) -> list[RecommendationRecord]:
    frame = load_dataset()
    store = get_vector_store()
    query = build_query_text(preferences, message)
    results = store.search(query=query, limit=limit)
    records: list[RecommendationRecord] = []
    for index, score in results:
        if index < 0 or index >= len(frame.index):
            continue
        row = frame.iloc[index]
        records.append(row_to_record(row, retrieval_score=score))
    return records
