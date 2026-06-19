"""Helpers for displaying field-level JobAdExtract evidence."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from constants import FactResolutionStatus, FactSourceType
from parsing import redact_pii
from schemas import JobAdExtract


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


def _provenance_status_label(
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
        return "Offen"
    if resolution_status == FactResolutionStatus.ASSUMED.value:
        return "Annahme"
    if source_type == FactSourceType.MANUAL.value:
        return "Eingabe"
    if (
        source_type == FactSourceType.JOBSPEC.value
        or "jobspec" in source_label.casefold()
    ):
        return "Jobspec"
    if source_type == FactSourceType.ESCO.value:
        return "ESCO"
    if source_type == FactSourceType.HOMEPAGE.value:
        return "Website"
    if source_type == FactSourceType.LLM.value:
        return "AI-Vorschlag"
    if confirmed is True or resolution_status == FactResolutionStatus.CONFIRMED.value:
        return "Eingabe"
    if resolution_status == FactResolutionStatus.INFERRED.value:
        return "Angereichert"
    if needs_confirmation:
        return "prüfen"
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
    status_label = _provenance_status_label(
        source_type=resolved_source_type,
        source_label=resolved_source_label,
        resolution_status=resolved_status,
        confirmed=resolved_confirmed,
        needs_confirmation=resolved_needs_confirmation,
    )

    resolved_confidence = _coerce_confidence(
        evidence_map.get("confidence") if "confidence" in evidence_map else confidence
    )
    parts = [status_label] if status_label else []
    if resolved_confidence is not None:
        parts.append(f"{resolved_confidence:.0%}")
    threshold = _coerce_confidence(confidence_threshold)
    if (
        resolved_status == FactResolutionStatus.CONFLICTED.value
        or resolved_needs_confirmation
        or (
            threshold is not None
            and resolved_confidence is not None
            and resolved_confidence < threshold
        )
    ) and "prüfen" not in parts:
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
        return f"Provenienz: {confidence} · {snippet}"
    if confidence:
        return f"Provenienz: {confidence}"
    if snippet:
        return f"Provenienz: {snippet}"
    return ""
