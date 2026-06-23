"""Helpers for displaying field-level JobAdExtract evidence."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

from constants import FactResolutionStatus, FactSourceType
from parsing import redact_pii
from schemas import JobAdExtract

_DEFAULT_TRUST_LANGUAGE: Final[str] = "de"
_SUPPORTED_TRUST_LANGUAGES: Final[frozenset[str]] = frozenset({"de", "en"})
_SOURCE_LABELS: Final[dict[str, dict[str, str]]] = {
    "de": {
        FactSourceType.MANUAL.value: "Eingabe",
        FactSourceType.JOBSPEC.value: "Jobspec",
        FactSourceType.HOMEPAGE.value: "Website",
        FactSourceType.ESCO.value: "ESCO",
        FactSourceType.LLM.value: "AI",
    },
    "en": {
        FactSourceType.MANUAL.value: "Input",
        FactSourceType.JOBSPEC.value: "Jobspec",
        FactSourceType.HOMEPAGE.value: "Website",
        FactSourceType.ESCO.value: "ESCO",
        FactSourceType.LLM.value: "AI",
    },
}
_TRUST_COPY: Final[dict[str, dict[str, tuple[str, str]]]] = {
    "de": {
        "confirmed": ("Bestätigt", "nutzen"),
        "detected": ("Erkannt", "prüfen"),
        "suggested": ("Vorschlag", "auswählen"),
        "assumed": ("Annahme", "prüfen"),
        "conflicted": ("Konflikt", "klären"),
        "missing": ("Fehlt", "ergänzen"),
        "fallback": ("Fallback", "prüfen"),
        "cached": ("Cache", "genutzt"),
        "source": ("Quelle", "ansehen"),
        "evidence": ("Beleg", "ansehen"),
        "source_evidence": ("Quelle & Beleg", "ansehen"),
        "review": ("Prüfen", ""),
    },
    "en": {
        "confirmed": ("Confirmed", "use"),
        "detected": ("Detected", "review"),
        "suggested": ("Suggested", "select"),
        "assumed": ("Assumed", "review"),
        "conflicted": ("Conflict", "resolve"),
        "missing": ("Missing", "add"),
        "fallback": ("Fallback", "review"),
        "cached": ("Cache", "reused"),
        "source": ("Source", "view"),
        "evidence": ("Evidence", "view"),
        "source_evidence": ("Source & evidence", "view"),
        "review": ("Review", ""),
    },
}
_DETECTED_SOURCE_TYPES: Final[frozenset[str]] = frozenset(
    {FactSourceType.JOBSPEC.value, FactSourceType.HOMEPAGE.value}
)
_SUGGESTED_SOURCE_TYPES: Final[frozenset[str]] = frozenset(
    {FactSourceType.ESCO.value, FactSourceType.LLM.value}
)


@dataclass(frozen=True)
class TrustCopy:
    """Resolved short trust copy derived from existing fact/source semantics."""

    key: str
    label: str
    action: str
    source_label: str = ""
    has_source: bool = False
    has_evidence: bool = False
    cached: bool = False

    @property
    def compact(self) -> str:
        return format_trust_copy(self)


def _trust_language(language: str | None) -> str:
    normalized = str(language or _DEFAULT_TRUST_LANGUAGE).strip().lower()
    return normalized if normalized in _SUPPORTED_TRUST_LANGUAGES else _DEFAULT_TRUST_LANGUAGE


def _trust_copy_for_key(key: str, *, language: str | None = None) -> tuple[str, str]:
    trust_language = _trust_language(language)
    return _TRUST_COPY[trust_language].get(key, ("", ""))


def format_trust_copy(copy: TrustCopy) -> str:
    """Return a compact label/action pair, e.g. ``Erkannt · prüfen``."""

    parts = [copy.label, copy.action]
    return " · ".join(part for part in parts if part)


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


def canonical_source_label(
    source_type: str = "",
    source_label: str = "",
    *,
    language: str | None = None,
) -> str:
    """Return the short source label used in user-facing trust copy."""

    source_labels = _SOURCE_LABELS[_trust_language(language)]
    normalized_type = str(source_type or "").strip()
    if normalized_type in source_labels:
        return source_labels[normalized_type]
    normalized_label = str(source_label or "").strip().casefold()
    if "jobspec" in normalized_label:
        return source_labels[FactSourceType.JOBSPEC.value]
    if "website" in normalized_label or "homepage" in normalized_label:
        return source_labels[FactSourceType.HOMEPAGE.value]
    if "esco" in normalized_label:
        return source_labels[FactSourceType.ESCO.value]
    if normalized_label == "ai" or "ai-" in normalized_label or "llm" in normalized_label:
        return source_labels[FactSourceType.LLM.value]
    if (
        "manual" in normalized_label
        or "input" in normalized_label
        or "antwort" in normalized_label
        or "eingabe" in normalized_label
    ):
        return source_labels[FactSourceType.MANUAL.value]
    return ""


def _provenance_trust_key(
    *,
    source_type: str = "",
    source_label: str = "",
    resolution_status: str = "",
    confirmed: bool | None = None,
    needs_confirmation: bool = False,
) -> str:
    if resolution_status == FactResolutionStatus.CONFLICTED.value:
        return "conflicted"
    if resolution_status == FactResolutionStatus.MISSING.value:
        return "missing"
    if resolution_status == FactResolutionStatus.ASSUMED.value:
        return "assumed"
    if confirmed is True or resolution_status == FactResolutionStatus.CONFIRMED.value:
        return "confirmed"
    if source_type == FactSourceType.MANUAL.value:
        return "confirmed"
    if resolution_status == FactResolutionStatus.INFERRED.value:
        if source_type in _SUGGESTED_SOURCE_TYPES:
            return "suggested"
        return "detected"
    if source_type in _DETECTED_SOURCE_TYPES:
        return "detected"
    if source_type in _SUGGESTED_SOURCE_TYPES:
        return "suggested"
    if needs_confirmation:
        return "review"
    if source_label:
        source = canonical_source_label(source_type, source_label)
        default_source_labels = _SOURCE_LABELS[_DEFAULT_TRUST_LANGUAGE]
        if source == default_source_labels[FactSourceType.LLM.value]:
            return "suggested"
        if source in {
            default_source_labels[FactSourceType.JOBSPEC.value],
            default_source_labels[FactSourceType.HOMEPAGE.value],
        }:
            return "detected"
    return ""


def resolve_trust_copy(
    evidence: Any = None,
    *,
    copy_key: str = "",
    source_type: str = "",
    source_label: str = "",
    resolution_status: str = "",
    confirmed: bool | None = None,
    needs_confirmation: bool = False,
    cached: bool = False,
    has_source: bool | None = None,
    has_evidence: bool | None = None,
    language: str | None = None,
) -> TrustCopy:
    """Resolve short trust copy from current fact/source semantics."""

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
    source_label_display = canonical_source_label(
        resolved_source_type,
        resolved_source_label,
        language=language,
    )
    resolved_has_source = (
        bool(has_source)
        if has_source is not None
        else bool(source_label_display or resolved_source_label or resolved_source_type)
    )
    resolved_has_evidence = (
        bool(has_evidence)
        if has_evidence is not None
        else bool(str(evidence_map.get("evidence_snippet") or "").strip())
    )

    trust_key = str(copy_key or "").strip()
    if not trust_key:
        trust_key = _provenance_trust_key(
            source_type=resolved_source_type,
            source_label=resolved_source_label,
            resolution_status=resolved_status,
            confirmed=resolved_confirmed,
            needs_confirmation=resolved_needs_confirmation,
        )
    if not trust_key and cached:
        trust_key = "cached"
    if not trust_key and resolved_has_source and resolved_has_evidence:
        trust_key = "source_evidence"
    elif not trust_key and resolved_has_evidence:
        trust_key = "evidence"
    elif not trust_key and resolved_has_source:
        trust_key = "source"

    label, action = _trust_copy_for_key(trust_key, language=language)
    return TrustCopy(
        key=trust_key,
        label=label,
        action=action,
        source_label=source_label_display,
        has_source=resolved_has_source,
        has_evidence=resolved_has_evidence,
        cached=cached,
    )


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
    language: str | None = None,
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
    resolved_confidence = _coerce_confidence(
        evidence_map.get("confidence") if "confidence" in evidence_map else confidence
    )
    threshold = _coerce_confidence(confidence_threshold)
    has_low_confidence = (
        threshold is not None
        and resolved_confidence is not None
        and resolved_confidence < threshold
    )
    trust_copy = resolve_trust_copy(
        evidence_map,
        source_type=resolved_source_type,
        source_label=resolved_source_label,
        resolution_status=resolved_status,
        confirmed=resolved_confirmed,
        needs_confirmation=resolved_needs_confirmation,
        language=language,
    )
    if not trust_copy.key and has_low_confidence:
        trust_copy = resolve_trust_copy(copy_key="review", language=language)
    status_label = format_trust_copy(trust_copy)
    source_label_display = canonical_source_label(
        resolved_source_type,
        resolved_source_label,
        language=language,
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
    *,
    language: str | None = None,
) -> str:
    evidence = evidence_by_field.get(field_name)
    provenance = format_provenance_label(
        evidence,
        source_type=FactSourceType.JOBSPEC.value,
        resolution_status=FactResolutionStatus.INFERRED.value,
        language=language,
    )
    confidence = provenance or format_field_evidence_confidence(evidence)
    snippet = format_field_evidence_snippet(evidence)
    if confidence and snippet:
        source_evidence_label = format_trust_copy(
            resolve_trust_copy(copy_key="source_evidence", language=language)
        )
        return f"{source_evidence_label}: {confidence} · {snippet}"
    if confidence:
        source_label = format_trust_copy(
            resolve_trust_copy(copy_key="source", language=language)
        )
        return f"{source_label}: {confidence}"
    if snippet:
        evidence_label = format_trust_copy(
            resolve_trust_copy(copy_key="evidence", language=language)
        )
        return f"{evidence_label}: {snippet}"
    return ""
