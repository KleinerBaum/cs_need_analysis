"""Pure helpers for Summary artifact identifiers and labels."""

from __future__ import annotations

from typing import Any

from constants import SUMMARY_ARTIFACT_IDS, SUMMARY_ARTIFACT_LEGACY_ALIASES


ACTION_ID_TO_CANONICAL_ARTIFACT_ID: dict[str, str] = {
    **SUMMARY_ARTIFACT_LEGACY_ALIASES,
    **{artifact_id: artifact_id for artifact_id in SUMMARY_ARTIFACT_IDS},
}

ARTIFACT_DISPLAY_LABELS: dict[str, str] = {
    "job_ad": "Stellenanzeige",
    "interview_hr": "HR-Sheet",
    "interview_fach": "Fachbereich-Sheet",
    "boolean_search": "Suchstrings",
    "employment_contract": "Arbeitsvertrag",
    "brief": "Recruiting Brief",
}

BRIEF_PIPELINE_STATUS_BY_STATE: dict[str, tuple[str, str]] = {
    "current": ("current", "Aktuell"),
    "stale": ("stale", "Veraltet"),
    "missing": ("open", "Fehlt"),
    "invalid": ("blocked", "Ungültig"),
    "blocked": ("blocked", "Wartet"),
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


def artifact_display_label(artifact_id: Any) -> str:
    if not isinstance(artifact_id, str):
        return ""
    normalized = artifact_id.strip()
    if not normalized:
        return ""
    return ARTIFACT_DISPLAY_LABELS.get(normalized, normalized)


def brief_pipeline_status_for_state(state: str) -> tuple[str, str]:
    return BRIEF_PIPELINE_STATUS_BY_STATE.get(state, ("open", "Offen"))
