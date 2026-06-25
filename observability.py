"""Privacy-safe operational logging helpers."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("need_analysis")

_FINE_TUNED_MODEL_PREFIX = "ft:"


def _safe_model_name(model: str | None) -> str:
    candidate = (model or "").strip()
    if not candidate:
        return "unknown"
    if candidate.startswith(_FINE_TUNED_MODEL_PREFIX):
        return "fine_tuned_model"
    return candidate[:80]


def _optional_int(value: int | float | str | None) -> int | None:
    if value is None:
        return None
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return None


def _optional_float(value: int | float | str | None) -> float | None:
    if value is None:
        return None
    try:
        return max(0.0, round(float(value), 6))
    except (TypeError, ValueError):
        return None


def log_model_call(
    task_kind: str | None,
    model: str | None,
    latency_ms: int | float | str | None,
    prompt_tokens: int | float | str | None = None,
    completion_tokens: int | float | str | None = None,
    cache_hit: bool | None = None,
    *,
    endpoint: str | None = None,
    estimated_cost_usd: int | float | str | None = None,
    status: str = "ok",
) -> dict[str, Any]:
    """Log one LLM call without prompts, raw payloads, URLs, names, or secrets."""

    payload: dict[str, Any] = {
        "task_kind": (task_kind or "structured_output")[:80],
        "model": _safe_model_name(model),
        "latency_ms": _optional_int(latency_ms),
        "prompt_tokens": _optional_int(prompt_tokens),
        "completion_tokens": _optional_int(completion_tokens),
        "cache_hit": bool(cache_hit) if cache_hit is not None else None,
        "endpoint": (endpoint or "unknown")[:80],
        "estimated_cost_usd": _optional_float(estimated_cost_usd),
        "status": (status or "ok")[:40],
    }
    logger.info(
        "model_call task=%s model=%s latency_ms=%s prompt_tokens=%s "
        "completion_tokens=%s cache_hit=%s endpoint=%s estimated_cost_usd=%s "
        "status=%s",
        payload["task_kind"],
        payload["model"],
        payload["latency_ms"],
        payload["prompt_tokens"],
        payload["completion_tokens"],
        payload["cache_hit"],
        payload["endpoint"],
        payload["estimated_cost_usd"],
        payload["status"],
    )
    return payload
