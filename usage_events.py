"""Privacy-safe session event helpers for lightweight intake observability."""

from __future__ import annotations

from datetime import UTC, datetime
import math
import re
from typing import Any, Mapping, MutableMapping

from constants import (
    FactKey,
    FactSourceType,
    SSKey,
    STEPS,
    SUMMARY_ARTIFACT_IDS,
    UsageEventType,
)

MAX_USAGE_EVENTS = 200
_MAX_METADATA_VALUE_LENGTH = 120
_UNSAFE_VALUE_BUCKET = "other"
_SAFE_STEP_KEYS = frozenset(step.key for step in STEPS)
_SAFE_ARTIFACT_IDS = frozenset(SUMMARY_ARTIFACT_IDS)
_SAFE_FACT_KEYS = frozenset(fact_key.value for fact_key in FactKey)
_SAFE_SOURCE_TYPES = frozenset(source_type.value for source_type in FactSourceType)
_SAFE_ENDPOINTS = frozenset({"responses.parse", "chat.completions.parse"})

_ALLOWED_METADATA_KEYS_BY_EVENT: dict[UsageEventType, frozenset[str]] = {
    UsageEventType.STEP_ENTERED: frozenset({"step_key"}),
    UsageEventType.STEP_SUBMITTED: frozenset({"step_key", "action"}),
    UsageEventType.FACT_CONFIRMED: frozenset({"fact_key", "source_type"}),
    UsageEventType.FACT_CORRECTED: frozenset({"fact_key", "source_type"}),
    UsageEventType.FACT_REJECTED: frozenset({"fact_key", "source_type"}),
    UsageEventType.FALLBACK_MODEL_USED: frozenset(
        {
            "task_kind",
            "requested_model",
            "final_model",
            "fallback_kind",
            "endpoint",
            "error_code",
        }
    ),
    UsageEventType.HOMEPAGE_FETCH_FAILED: frozenset({"topic_key", "error_type"}),
    UsageEventType.ENRICHMENT_TIMED: frozenset(
        {
            "stage",
            "path",
            "duration_ms",
            "status",
            "cache_hit",
            "fragment_enabled",
            "result_count",
            "error_type",
        }
    ),
    UsageEventType.ARTIFACT_GENERATED: frozenset(
        {"artifact_id", "cache_hit", "mode"}
    ),
    UsageEventType.EVALUATION_RUN_COMPLETED: frozenset(
        {
            "run_id",
            "scenario_count",
            "combination_count",
            "best_combination_id",
            "best_score",
            "passed_success_criteria",
        }
    ),
}
_BOOL_METADATA_KEYS = frozenset(
    {"cache_hit", "fragment_enabled", "passed_success_criteria"}
)
_INT_METADATA_KEYS = frozenset(
    {"duration_ms", "result_count", "scenario_count", "combination_count"}
)
_FLOAT_METADATA_KEYS = frozenset({"best_score"})
_CANONICAL_VALUE_SETS: dict[str, frozenset[str]] = {
    "artifact_id": _SAFE_ARTIFACT_IDS,
    "fact_key": _SAFE_FACT_KEYS,
    "source_type": _SAFE_SOURCE_TYPES,
    "step_key": _SAFE_STEP_KEYS,
}
_MODEL_METADATA_KEYS = frozenset({"requested_model", "final_model"})
_HOSTNAME_RE = re.compile(r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")


def get_usage_events(session_state: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return session usage events without mutating state."""

    raw_events = session_state.get(SSKey.USAGE_EVENTS.value)
    return list(raw_events) if isinstance(raw_events, list) else []


def reset_usage_events(session_state: MutableMapping[str, Any]) -> None:
    """Reset session usage events for a new vacancy."""

    session_state[SSKey.USAGE_EVENTS.value] = []


def append_usage_event(
    session_state: MutableMapping[str, Any],
    event_type: UsageEventType | str,
    *,
    metadata: Mapping[str, Any] | None = None,
    occurred_at: str | None = None,
) -> None:
    """Append one sanitized usage event to bounded session state."""

    resolved_event_type = _coerce_event_type(event_type)
    if resolved_event_type is None:
        return
    events = get_usage_events(session_state)
    events.append(
        {
            "event_type": resolved_event_type.value,
            "occurred_at": occurred_at or datetime.now(UTC).isoformat(),
            "metadata": _sanitize_metadata(resolved_event_type, metadata or {}),
        }
    )
    session_state[SSKey.USAGE_EVENTS.value] = events[-MAX_USAGE_EVENTS:]


def record_homepage_fetch_failed(
    session_state: MutableMapping[str, Any],
    *,
    topic_key: str,
    error_type: str,
) -> None:
    append_usage_event(
        session_state,
        UsageEventType.HOMEPAGE_FETCH_FAILED,
        metadata={
            "topic_key": topic_key,
            "error_type": error_type,
        },
    )


def record_enrichment_timed(
    session_state: MutableMapping[str, Any],
    *,
    stage: str,
    path: str,
    duration_ms: int,
    status: str = "success",
    cache_hit: bool | None = None,
    fragment_enabled: bool | None = None,
    result_count: int | None = None,
    error_type: str | None = None,
) -> None:
    metadata: dict[str, Any] = {
        "stage": stage,
        "path": path,
        "duration_ms": max(0, int(duration_ms)),
        "status": status,
    }
    if cache_hit is not None:
        metadata["cache_hit"] = cache_hit
    if fragment_enabled is not None:
        metadata["fragment_enabled"] = fragment_enabled
    if result_count is not None:
        metadata["result_count"] = max(0, int(result_count))
    if error_type:
        metadata["error_type"] = error_type
    append_usage_event(
        session_state,
        UsageEventType.ENRICHMENT_TIMED,
        metadata=metadata,
    )


def record_artifact_generated(
    session_state: MutableMapping[str, Any],
    *,
    artifact_id: str,
    cache_hit: bool | None = None,
    mode: str | None = None,
) -> None:
    metadata: dict[str, Any] = {"artifact_id": artifact_id}
    if cache_hit is not None:
        metadata["cache_hit"] = cache_hit
    if mode:
        metadata["mode"] = mode
    append_usage_event(
        session_state,
        UsageEventType.ARTIFACT_GENERATED,
        metadata=metadata,
    )


def record_evaluation_run_completed(
    session_state: MutableMapping[str, Any],
    *,
    run_id: str,
    scenario_count: int,
    combination_count: int,
    best_combination_id: str,
    best_score: float,
    passed_success_criteria: bool,
) -> None:
    append_usage_event(
        session_state,
        UsageEventType.EVALUATION_RUN_COMPLETED,
        metadata={
            "run_id": run_id,
            "scenario_count": max(0, int(scenario_count)),
            "combination_count": max(0, int(combination_count)),
            "best_combination_id": best_combination_id,
            "best_score": round(float(best_score), 3),
            "passed_success_criteria": passed_success_criteria,
        },
    )


def record_step_entered(
    session_state: MutableMapping[str, Any],
    *,
    step_key: str,
) -> None:
    append_usage_event(
        session_state,
        UsageEventType.STEP_ENTERED,
        metadata={"step_key": step_key},
    )


def record_step_submitted(
    session_state: MutableMapping[str, Any],
    *,
    step_key: str,
    action: str | None = None,
) -> None:
    metadata: dict[str, Any] = {"step_key": step_key}
    if action:
        metadata["action"] = action
    append_usage_event(
        session_state,
        UsageEventType.STEP_SUBMITTED,
        metadata=metadata,
    )


def record_fact_confirmed(
    session_state: MutableMapping[str, Any],
    *,
    fact_key: str,
    source_type: str | None = None,
) -> None:
    _record_fact_lifecycle_event(
        session_state,
        UsageEventType.FACT_CONFIRMED,
        fact_key=fact_key,
        source_type=source_type,
    )


def record_fact_corrected(
    session_state: MutableMapping[str, Any],
    *,
    fact_key: str,
    source_type: str | None = None,
) -> None:
    _record_fact_lifecycle_event(
        session_state,
        UsageEventType.FACT_CORRECTED,
        fact_key=fact_key,
        source_type=source_type,
    )


def record_fact_rejected(
    session_state: MutableMapping[str, Any],
    *,
    fact_key: str,
    source_type: str | None = None,
) -> None:
    _record_fact_lifecycle_event(
        session_state,
        UsageEventType.FACT_REJECTED,
        fact_key=fact_key,
        source_type=source_type,
    )


def record_fallback_model_used(
    session_state: MutableMapping[str, Any],
    *,
    task_kind: str,
    requested_model: str,
    final_model: str,
    fallback_kind: str,
    endpoint: str | None = None,
    error_code: str | None = None,
) -> None:
    metadata: dict[str, Any] = {
        "task_kind": task_kind,
        "requested_model": requested_model,
        "final_model": final_model,
        "fallback_kind": fallback_kind,
    }
    if endpoint:
        metadata["endpoint"] = endpoint
    if error_code:
        metadata["error_code"] = error_code
    append_usage_event(
        session_state,
        UsageEventType.FALLBACK_MODEL_USED,
        metadata=metadata,
    )


def _record_fact_lifecycle_event(
    session_state: MutableMapping[str, Any],
    event_type: UsageEventType,
    *,
    fact_key: str,
    source_type: str | None,
) -> None:
    metadata: dict[str, Any] = {"fact_key": fact_key}
    if source_type:
        metadata["source_type"] = source_type
    append_usage_event(
        session_state,
        event_type,
        metadata=metadata,
    )


def _coerce_event_type(raw_event_type: UsageEventType | str) -> UsageEventType | None:
    if isinstance(raw_event_type, UsageEventType):
        return raw_event_type
    try:
        return UsageEventType(str(raw_event_type))
    except ValueError:
        return None


def _sanitize_metadata(
    event_type: UsageEventType,
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    allowed_keys = _ALLOWED_METADATA_KEYS_BY_EVENT.get(event_type, frozenset())
    for raw_key, raw_value in metadata.items():
        key = str(raw_key or "").strip()
        if key not in allowed_keys:
            continue
        value = _sanitize_metadata_value(key, raw_value)
        if value is not None:
            sanitized[key] = value
    return sanitized


def _sanitize_metadata_value(
    key: str,
    value: Any,
) -> str | int | float | bool | None:
    if key in _BOOL_METADATA_KEYS:
        return value if isinstance(value, bool) else None
    if key in _INT_METADATA_KEYS:
        return _sanitize_metadata_int(value)
    if key in _FLOAT_METADATA_KEYS:
        return _sanitize_metadata_float(value)
    if key == "endpoint":
        return _sanitize_endpoint_value(value)
    if key in _MODEL_METADATA_KEYS:
        return _sanitize_model_value(value)
    allowed_values = _CANONICAL_VALUE_SETS.get(key)
    if allowed_values is not None:
        return _sanitize_canonical_value(value, allowed_values)
    return _sanitize_bucket_value(value)


def _sanitize_metadata_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return None


def _sanitize_metadata_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return round(number, 3)


def _sanitize_endpoint_value(value: Any) -> str | None:
    cleaned = _clean_metadata_string(value)
    if cleaned is None:
        return None
    if cleaned in _SAFE_ENDPOINTS:
        return cleaned
    return _UNSAFE_VALUE_BUCKET


def _sanitize_model_value(value: Any) -> str | None:
    cleaned = _clean_metadata_string(value)
    if cleaned is None:
        return None
    if cleaned.startswith("ft:"):
        return "fine_tuned_model"
    if _is_safe_bucket_string(cleaned):
        return cleaned
    return _UNSAFE_VALUE_BUCKET


def _sanitize_canonical_value(value: Any, allowed_values: frozenset[str]) -> str | None:
    cleaned = _clean_metadata_string(value)
    if cleaned is None:
        return None
    if cleaned in allowed_values:
        return cleaned
    return _UNSAFE_VALUE_BUCKET


def _sanitize_bucket_value(value: Any) -> str | None:
    cleaned = _clean_metadata_string(value)
    if cleaned is None:
        return None
    if _is_safe_bucket_string(cleaned):
        return cleaned
    return _UNSAFE_VALUE_BUCKET


def _clean_metadata_string(value: Any) -> str | None:
    if value is None or isinstance(value, bool | int | float):
        return None
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _is_safe_bucket_string(value: str) -> bool:
    if len(value) > _MAX_METADATA_VALUE_LENGTH:
        return False
    casefolded = value.casefold()
    if casefolded.startswith(("http://", "https://", "www.", "sk-")):
        return False
    if any(part in value for part in ("@", "/", "\\")):
        return False
    if any(char.isspace() for char in value):
        return False
    return not _is_hostname_like(value)


def _is_hostname_like(value: str) -> bool:
    if "_" in value or not _HOSTNAME_RE.fullmatch(value):
        return False
    final_label = value.rsplit(".", 1)[-1]
    return len(final_label) >= 2 and final_label.isalpha()
