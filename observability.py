"""Privacy-safe operational logging helpers."""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("need_analysis")

_FINE_TUNED_MODEL_PREFIX = "ft:"
_SAFE_ENDPOINTS = frozenset(
    {"responses.parse", "chat.completions.parse", "session_state"}
)
_HOSTNAME_RE = re.compile(r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")


def _safe_model_name(model: str | None) -> str:
    candidate = (model or "").strip()
    if not candidate:
        return "unknown"
    if candidate.startswith(_FINE_TUNED_MODEL_PREFIX):
        return "fine_tuned_model"
    return candidate[:80]


def _is_hostname_like(value: str) -> bool:
    if "_" in value or not _HOSTNAME_RE.fullmatch(value):
        return False
    final_label = value.rsplit(".", 1)[-1]
    return len(final_label) >= 2 and final_label.isalpha()


def _safe_bucket(value: str | None, *, default: str = "unknown") -> str:
    candidate = (value or "").strip()
    if not candidate:
        return default
    casefolded = candidate.casefold()
    if casefolded.startswith(("http://", "https://", "www.", "sk-")):
        return "other"
    if any(part in candidate for part in ("@", "/", "\\")):
        return "other"
    if any(char.isspace() for char in candidate):
        return "other"
    if _is_hostname_like(candidate):
        return "other"
    return candidate[:80]


def _safe_endpoint(endpoint: str | None) -> str:
    candidate = (endpoint or "").strip()
    if candidate in _SAFE_ENDPOINTS:
        return candidate
    return _safe_bucket(candidate)


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
    cached_tokens: int | float | str | None = None,
    endpoint: str | None = None,
    estimated_cost_usd: int | float | str | None = None,
    status: str = "ok",
    retry_category: str | None = None,
    error_category: str | None = None,
) -> dict[str, Any]:
    """Log one LLM call without prompts, raw payloads, URLs, names, or secrets."""

    payload: dict[str, Any] = {
        "task_kind": _safe_bucket(task_kind, default="structured_output"),
        "model": _safe_model_name(model),
        "latency_ms": _optional_int(latency_ms),
        "prompt_tokens": _optional_int(prompt_tokens),
        "completion_tokens": _optional_int(completion_tokens),
        "cached_tokens": _optional_int(cached_tokens),
        "cache_hit": bool(cache_hit) if cache_hit is not None else None,
        "endpoint": _safe_endpoint(endpoint),
        "estimated_cost_usd": _optional_float(estimated_cost_usd),
        "status": _safe_bucket(status, default="ok")[:40],
        "retry_category": _safe_bucket(retry_category, default="none"),
        "error_category": _safe_bucket(error_category, default="none"),
    }
    logger.info(
        "model_call task=%s model=%s latency_ms=%s prompt_tokens=%s "
        "completion_tokens=%s cached_tokens=%s cache_hit=%s endpoint=%s "
        "estimated_cost_usd=%s status=%s retry_category=%s error_category=%s",
        payload["task_kind"],
        payload["model"],
        payload["latency_ms"],
        payload["prompt_tokens"],
        payload["completion_tokens"],
        payload["cached_tokens"],
        payload["cache_hit"],
        payload["endpoint"],
        payload["estimated_cost_usd"],
        payload["status"],
        payload["retry_category"],
        payload["error_category"],
    )
    return payload
