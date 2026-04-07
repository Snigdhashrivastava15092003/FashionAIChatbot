from __future__ import annotations

from backend.services.dataset_service import compute_trend_summary


def fetch_trends() -> dict[str, list[dict[str, str | int]]]:
    return compute_trend_summary()
