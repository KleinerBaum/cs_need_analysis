"""Helpers for displaying field-level JobAdExtract evidence."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

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
    confidence = format_field_evidence_confidence(evidence)
    snippet = format_field_evidence_snippet(evidence)
    if confidence and snippet:
        return f"Evidence: {confidence} · {snippet}"
    if confidence:
        return f"Evidence: {confidence}"
    if snippet:
        return f"Evidence: {snippet}"
    return ""
