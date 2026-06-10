"""Privacy-safe session event helpers for lightweight intake observability."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Mapping, MutableMapping

from constants import SSKey, UsageEventType

MAX_USAGE_EVENTS = 200
_MAX_METADATA_VALUE_LENGTH = 120
_SENSITIVE_METADATA_KEY_PARTS = (
    "api_key",
    "secret",
    "token",
    "password",
    "credential",
    "email",
    "phone",
    "name",
    "url",
    "text",
    "prompt",
    "payload",
    "content",
)


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
            "metadata": _sanitize_metadata(metadata or {}),
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


def _sanitize_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for raw_key, raw_value in metadata.items():
        key = str(raw_key or "").strip()
        if not key or _is_sensitive_metadata_key(key):
            continue
        value = _sanitize_metadata_value(raw_value)
        if value is not None:
            sanitized[key] = value
    return sanitized


def _is_sensitive_metadata_key(key: str) -> bool:
    normalized = key.casefold()
    return any(part in normalized for part in _SENSITIVE_METADATA_KEY_PARTS)


def _sanitize_metadata_value(value: Any) -> str | int | float | bool | None:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return value
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        if len(cleaned) > _MAX_METADATA_VALUE_LENGTH:
            return f"{cleaned[: _MAX_METADATA_VALUE_LENGTH - 1].rstrip()}…"
        return cleaned
    return str(type(value).__name__)
