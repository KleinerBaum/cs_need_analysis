"""Pure helpers for Summary artifact identifiers and labels."""

from __future__ import annotations

from typing import Any

from constants import SUMMARY_ARTIFACT_IDS, SUMMARY_ARTIFACT_LEGACY_ALIASES
from ux_copy_contract import artifact_label, summary_ui_copy


ACTION_ID_TO_CANONICAL_ARTIFACT_ID: dict[str, str] = {
    **SUMMARY_ARTIFACT_LEGACY_ALIASES,
    **{artifact_id: artifact_id for artifact_id in SUMMARY_ARTIFACT_IDS},
}

BRIEF_PIPELINE_STATUS_BY_STATE: dict[str, tuple[str, str]] = {
    "current": ("current", "current"),
    "stale": ("stale", "stale"),
    "missing": ("open", "missing"),
    "invalid": ("blocked", "invalid"),
    "blocked": ("blocked", "blocked"),
}


def to_canonical_artifact_id(raw_id: Any) -> str:
    if not isinstance(raw_id, str):
        return ""
    normalized = raw_id.strip()
    if not normalized:
        return ""
    if normalized in ACTION_ID_TO_CANONICAL_ARTIFACT_ID:
        return ACTION_ID_TO_CANONICAL_ARTIFACT_ID[normalized]
    return ACTION_ID_TO_CANONICAL_ARTIFACT_ID.get(normalized.casefold(), "")


def artifact_display_label(artifact_id: Any, *, language: str | None = None) -> str:
    if not isinstance(artifact_id, str):
        return ""
    normalized = artifact_id.strip()
    if not normalized:
        return ""
    return artifact_label(normalized, language=language)


def brief_pipeline_status_for_state(
    state: str,
    *,
    language: str | None = None,
) -> tuple[str, str]:
    status, label_key = BRIEF_PIPELINE_STATUS_BY_STATE.get(state, ("open", "open"))
    return status, summary_ui_copy(f"artifact_status.{label_key}", language=language)
