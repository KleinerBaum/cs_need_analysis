"""Helpers for displaying field-level JobAdExtract evidence."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

from constants import FactResolutionStatus, FactSourceType
from parsing import redact_pii
from schemas import JobAdExtract

_SOURCE_LABELS: Final[dict[str, str]] = {
    FactSourceType.MANUAL.value: "Eingabe",
    FactSourceType.JOBSPEC.value: "Jobspec",
    FactSourceType.HOMEPAGE.value: "Website",
    FactSourceType.ESCO.value: "ESCO",
    FactSourceType.LLM.value: "AI",
}
_DETECTED_SOURCE_TYPES: Final[frozenset[str]] = frozenset(
    {FactSourceType.JOBSPEC.value, FactSourceType.HOMEPAGE.value}
)
_SUGGESTED_SOURCE_TYPES: Final[frozenset[str]] = frozenset(
    {FactSourceType.ESCO.value, FactSourceType.LLM.value}
)


def job_extract_field_evidence_by_name(job: JobAdExtract) -> dict[str, Any]:
    evidence_by_field: dict[str, Any] = {}
    for raw_entry in getattr(job, "field_evidence", []) or []:
        if hasattr(raw_entry, "model_dump"):
            entry = raw_entry.model_dump(mode="json")
        else:
            entry = raw_entry if isinstance(raw_entry, dict) else {}
        field_name = str(entry.get("field_name") or "").strip()
        if field_name:
            evidence_by_field[field_name] = entry
    return evidence_by_field


def format_field_evidence_confidence(evidence: Any) -> str:
    if not isinstance(evidence, Mapping):
        return ""
    try:
        confidence = max(0.0, min(1.0, float(evidence.get("confidence"))))
    except (TypeError, ValueError):
        return ""
    suffix = " · prüfen" if bool(evidence.get("needs_confirmation")) else ""
    return f"{confidence:.0%}{suffix}"


def _coerce_confidence(value: Any) -> float | None:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return None


def canonical_source_label(source_type: str = "", source_label: str = "") -> str:
    """Return the short source label used in user-facing trust copy."""

    normalized_type = str(source_type or "").strip()
    if normalized_type in _SOURCE_LABELS:
        return _SOURCE_LABELS[normalized_type]
    normalized_label = str(source_label or "").strip().casefold()
    if "jobspec" in normalized_label:
        return _SOURCE_LABELS[FactSourceType.JOBSPEC.value]
    if "website" in normalized_label or "homepage" in normalized_label:
        return _SOURCE_LABELS[FactSourceType.HOMEPAGE.value]
    if "esco" in normalized_label:
        return _SOURCE_LABELS[FactSourceType.ESCO.value]
    if normalized_label == "ai" or "ai-" in normalized_label or "llm" in normalized_label:
        return _SOURCE_LABELS[FactSourceType.LLM.value]
    if (
        "manual" in normalized_label
        or "antwort" in normalized_label
        or "eingabe" in normalized_label
    ):
        return _SOURCE_LABELS[FactSourceType.MANUAL.value]
    return ""


def _provenance_trust_label(
    *,
    source_type: str = "",
    source_label: str = "",
    resolution_status: str = "",
    confirmed: bool | None = None,
    needs_confirmation: bool = False,
) -> str:
    if resolution_status == FactResolutionStatus.CONFLICTED.value:
        return "Konflikt"
    if resolution_status == FactResolutionStatus.MISSING.value:
        return "Fehlt"
    if resolution_status == FactResolutionStatus.ASSUMED.value:
        return "Annahme"
    if confirmed is True or resolution_status == FactResolutionStatus.CONFIRMED.value:
        return "Bestätigt"
    if source_type == FactSourceType.MANUAL.value:
        return "Bestätigt"
    if resolution_status == FactResolutionStatus.INFERRED.value:
        if source_type in _SUGGESTED_SOURCE_TYPES:
            return "Vorschlag"
        return "Erkannt"
    if source_type in _DETECTED_SOURCE_TYPES:
        return "Erkannt"
    if source_type in _SUGGESTED_SOURCE_TYPES:
        return "Vorschlag"
    if needs_confirmation:
        return "Prüfen"
    if source_label:
        source = canonical_source_label(source_type, source_label)
        if source == _SOURCE_LABELS[FactSourceType.LLM.value]:
            return "Vorschlag"
        if source in {
            _SOURCE_LABELS[FactSourceType.JOBSPEC.value],
            _SOURCE_LABELS[FactSourceType.HOMEPAGE.value],
        }:
            return "Erkannt"
    return ""


def format_provenance_label(
    evidence: Any = None,
    *,
    source_type: str = "",
    source_label: str = "",
    resolution_status: str = "",
    confirmed: bool | None = None,
    confidence: Any = None,
    needs_confirmation: bool = False,
    confidence_threshold: float | None = None,
) -> str:
    """Return compact, non-sensitive provenance text for UI captions/tables."""

    evidence_map = evidence if isinstance(evidence, Mapping) else {}
    resolved_source_type = str(evidence_map.get("source_type") or source_type).strip()
    resolved_source_label = str(evidence_map.get("source_label") or source_label).strip()
    resolved_status = str(
        evidence_map.get("resolution_status") or resolution_status
    ).strip()
    resolved_confirmed = (
        bool(evidence_map.get("confirmed"))
        if "confirmed" in evidence_map
        else confirmed
    )
    resolved_needs_confirmation = bool(
        evidence_map.get("needs_confirmation", needs_confirmation)
    )
    status_label = _provenance_trust_label(
        source_type=resolved_source_type,
        source_label=resolved_source_label,
        resolution_status=resolved_status,
        confirmed=resolved_confirmed,
        needs_confirmation=resolved_needs_confirmation,
    )
    source_label_display = canonical_source_label(
        resolved_source_type,
        resolved_source_label,
    )

    resolved_confidence = _coerce_confidence(
        evidence_map.get("confidence") if "confidence" in evidence_map else confidence
    )
    parts = [status_label] if status_label else []
    if (
        source_label_display
        and source_label_display not in parts
        and resolved_status
        not in {
            FactResolutionStatus.CONFLICTED.value,
            FactResolutionStatus.MISSING.value,
            FactResolutionStatus.ASSUMED.value,
        }
    ):
        parts.append(source_label_display)
    if resolved_confidence is not None:
        parts.append(f"{resolved_confidence:.0%}")
    threshold = _coerce_confidence(confidence_threshold)
    needs_review = (
        resolved_status
        in {
            FactResolutionStatus.CONFLICTED.value,
            FactResolutionStatus.ASSUMED.value,
        }
        or resolved_needs_confirmation
        or (
            threshold is not None
            and resolved_confidence is not None
            and resolved_confidence < threshold
        )
    )
    if resolved_status == FactResolutionStatus.MISSING.value and "ergänzen" not in parts:
        parts.append("ergänzen")
    elif needs_review and "prüfen" not in parts:
        parts.append("prüfen")
    return " · ".join(part for part in parts if part)


def format_field_evidence_snippet(evidence: Any, *, max_chars: int = 160) -> str:
    if not isinstance(evidence, Mapping):
        return ""
    raw_snippet = str(evidence.get("evidence_snippet") or "").strip()
    if not raw_snippet:
        return ""
    snippet = " ".join(redact_pii(raw_snippet).split())
    if len(snippet) <= max_chars:
        return snippet
    return f"{snippet[: max_chars - 1].rstrip()}…"


def add_field_evidence_columns(
    rows: list[dict[str, Any]],
    evidence_by_field: Mapping[str, Any],
) -> list[dict[str, Any]]:
    if not any(evidence_by_field.get(str(row.get("field") or "")) for row in rows):
        return rows
    enriched_rows: list[dict[str, Any]] = []
    for row in rows:
        field = str(row.get("field") or "")
        evidence = evidence_by_field.get(field)
        enriched = dict(row)
        enriched["confidence"] = format_field_evidence_confidence(evidence)
        enriched["evidence"] = format_field_evidence_snippet(evidence)
        enriched_rows.append(enriched)
    return enriched_rows


def field_evidence_caption_text(
    field_name: str,
    evidence_by_field: Mapping[str, Any],
) -> str:
    evidence = evidence_by_field.get(field_name)
    provenance = format_provenance_label(
        evidence,
        source_type=FactSourceType.JOBSPEC.value,
        resolution_status=FactResolutionStatus.INFERRED.value,
    )
    confidence = provenance or format_field_evidence_confidence(evidence)
    snippet = format_field_evidence_snippet(evidence)
    if confidence and snippet:
        return f"Quelle & Beleg: {confidence} · {snippet}"
    if confidence:
        return f"Quelle: {confidence}"
    if snippet:
        return f"Beleg verfügbar: {snippet}"
    return ""
