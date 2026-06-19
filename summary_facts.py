"""Pure helpers for Summary fact rows and value formatting."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from constants import (
    FACT_REQUIREMENT_STAGE_DISPLAY_LABELS,
    FACT_SALARY_IMPACT_DISPLAY_LABELS,
    AnswerType,
    FactKey,
    FactRequirementStage,
    FactResolutionStatus,
    FactSalaryImpact,
    FactSourceType,
)
from job_extract_evidence import format_provenance_label
from schemas import Question, question_option_label_map


@dataclass(frozen=True)
class SummaryFactsRow:
    bereich: str
    feld: str
    wert: str
    quelle: str
    status: str
    resolution_status: str = ""
    step_key: str = ""
    fact_key: str = ""
    question_id: str = ""
    editable: bool = False
    value_type: str = "text"
    salary_impact: str = ""
    requirement_stage: str = ""
    website_enrichable: bool = False
    provenienz: str = ""

    def to_dict(self) -> dict[str, str]:
        row = {
            "Bereich": self.bereich,
            "Feld": self.feld,
            "Wert": self.wert,
            "Quelle": self.quelle,
            "Status": self.status,
        }
        return row


def summary_fact_row_to_table_dict(row: SummaryFactsRow) -> dict[str, str]:
    payload = row.to_dict()
    payload.update(
        {
            "Salary": display_salary_impact(row.salary_impact),
            "Pflichtigkeit": display_requirement_stage(row.requirement_stage),
            "Second Source": "Website-Review" if row.website_enrichable else "",
            "Provenienz": row.provenienz,
        }
    )
    return payload


def display_salary_impact(value: str | FactSalaryImpact) -> str:
    if isinstance(value, FactSalaryImpact):
        return FACT_SALARY_IMPACT_DISPLAY_LABELS[value]
    try:
        return FACT_SALARY_IMPACT_DISPLAY_LABELS[FactSalaryImpact(str(value))]
    except ValueError:
        return ""


def display_requirement_stage(value: str | FactRequirementStage) -> str:
    if isinstance(value, FactRequirementStage):
        return FACT_REQUIREMENT_STAGE_DISPLAY_LABELS[value]
    try:
        return FACT_REQUIREMENT_STAGE_DISPLAY_LABELS[FactRequirementStage(str(value))]
    except ValueError:
        return ""


def group_summary_fact_rows_by_area(
    rows: Sequence[SummaryFactsRow],
) -> list[tuple[str, list[SummaryFactsRow]]]:
    grouped_rows: dict[str, list[SummaryFactsRow]] = {}
    ordered_areas: list[str] = []
    for row in rows:
        area = str(row.bereich or "").strip() or "Sonstiges"
        if area not in grouped_rows:
            grouped_rows[area] = []
            ordered_areas.append(area)
        grouped_rows[area].append(row)
    return [(area, grouped_rows[area]) for area in ordered_areas]


def format_summary_answer_value(question: Question, value: Any) -> str:
    option_label_map = question_option_label_map(question)

    def _label_for(item: Any) -> str:
        item_str = str(item).strip()
        if not item_str:
            return ""
        return option_label_map.get(item_str, item_str)

    if question.answer_type == AnswerType.BOOLEAN:
        return "Ja" if bool(value) else "Nein"
    if question.answer_type == AnswerType.MULTI_SELECT:
        if isinstance(value, list):
            labels = [_label_for(item) for item in value]
            return ", ".join(label for label in labels if label)
        return ""
    if question.answer_type == AnswerType.SINGLE_SELECT:
        return _label_for(value)
    if question.answer_type in {
        AnswerType.LONG_TEXT,
        AnswerType.SHORT_TEXT,
        AnswerType.DATE,
    }:
        return str(value or "").strip()
    if question.answer_type == AnswerType.NUMBER:
        return str(value) if value is not None else ""

    if isinstance(value, list):
        return ", ".join(str(item).strip() for item in value if str(item).strip())
    return str(value or "").strip()


def is_missing_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set)):
        return len(value) == 0
    if isinstance(value, dict):
        return len(value) == 0
    return False


def has_partial_payload(value: Any) -> bool:
    if isinstance(value, dict):
        values = list(value.values())
        if not values:
            return False
        has_present = any(not is_missing_value(item) for item in values)
        has_missing = any(is_missing_value(item) for item in values)
        return has_present and has_missing
    if isinstance(value, list):
        if not value:
            return False
        has_present = any(not is_missing_value(item) for item in value)
        has_missing = any(is_missing_value(item) for item in value)
        return has_present and has_missing
    return False


def status_for_value(value: Any) -> str:
    if is_missing_value(value):
        return "Fehlend"
    if has_partial_payload(value):
        return "Teilweise"
    return "Vollständig"


def format_summary_fact_value(value: Any) -> str:
    if isinstance(value, list):
        return " | ".join(
            item
            for item in (_format_summary_collection_item(item) for item in value)
            if item
        )
    if isinstance(value, dict):
        return _format_summary_mapping(value)
    if isinstance(value, bool):
        return "Ja" if value else "Nein"
    if value is None:
        return ""
    return str(value).strip()


def _format_summary_collection_item(value: Any) -> str:
    if isinstance(value, Mapping):
        label = _mapping_primary_label(value)
        if label:
            return label
        return _format_summary_mapping(value)
    if isinstance(value, list):
        return format_summary_fact_value(value)
    if isinstance(value, bool):
        return "Ja" if value else "Nein"
    if value is None:
        return ""
    return str(value).strip()


def _mapping_primary_label(value: Mapping[str, Any]) -> str:
    for key in ("label", "title", "name", "value", "skill", "term"):
        raw = value.get(key)
        if not is_missing_value(raw):
            return str(raw).strip()
    language = value.get("language")
    level = value.get("level")
    if not is_missing_value(language):
        fragments = [str(language).strip()]
        if not is_missing_value(level):
            fragments.append(str(level).strip())
        return " ".join(fragments)
    return ""


def _format_summary_mapping(value: Mapping[str, Any]) -> str:
    preferred_order = (
        "min",
        "max",
        "currency",
        "period",
        "notes",
        "eligible",
        "ote_min",
        "ote_max",
        "bonus_logic",
    )
    ordered_keys = [
        key for key in preferred_order if key in value and not is_missing_value(value.get(key))
    ]
    ordered_keys.extend(
        key
        for key in value.keys()
        if key not in ordered_keys and not is_missing_value(value.get(key))
    )
    parts: list[str] = []
    for key in ordered_keys:
        item = value.get(key)
        if isinstance(item, Mapping):
            formatted = _format_summary_mapping(item)
        elif isinstance(item, list):
            formatted = format_summary_fact_value(item)
        else:
            formatted = str(item).strip()
        if not formatted:
            continue
        parts.append(f"{str(key).strip()}: {formatted}")
    return " | ".join(parts)


def summary_core_fact_row(
    *,
    label: str,
    fact_key: FactKey,
    fallback_value: Any,
    intake_facts: Mapping[str, Any],
    intake_fact_evidence: Mapping[str, Any],
) -> SummaryFactsRow:
    if fact_key.value in intake_facts:
        fact_value = intake_facts.get(fact_key.value)
        evidence_raw = intake_fact_evidence.get(fact_key.value)
        evidence = evidence_raw if isinstance(evidence_raw, Mapping) else {}
        source = source_label_with_secondary_evidence(evidence, "Intake-Fakt")
        resolution_status = str(
            evidence.get("resolution_status") or _default_resolution_status(evidence)
        ).strip()
        return SummaryFactsRow(
            "Kernprofil",
            label,
            format_summary_fact_value(fact_value) or "Nicht angegeben",
            source,
            status_for_value(fact_value),
            resolution_status,
            fact_key=fact_key.value,
            editable=True,
            provenienz=summary_provenance_label(
                evidence,
                fallback_source_type=FactSourceType.MANUAL.value,
                fallback_resolution_status=resolution_status,
            ),
        )
    fallback_status = (
        FactResolutionStatus.INFERRED.value
        if not is_missing_value(fallback_value)
        else FactResolutionStatus.MISSING.value
    )
    return SummaryFactsRow(
        "Kernprofil",
        label,
        format_summary_fact_value(fallback_value) or "Nicht angegeben",
        "Jobspec",
        status_for_value(fallback_value),
        fallback_status,
        fact_key=fact_key.value,
        editable=True,
        provenienz=summary_provenance_label(
            {},
            fallback_source_type=FactSourceType.JOBSPEC.value,
            fallback_resolution_status=fallback_status,
        ),
    )


def _default_resolution_status(evidence: Mapping[str, Any]) -> str:
    if bool(evidence.get("confirmed")):
        return FactResolutionStatus.CONFIRMED.value
    return FactResolutionStatus.INFERRED.value


def source_label_with_secondary_evidence(
    evidence: Mapping[str, Any],
    default_source: str,
) -> str:
    source = str(evidence.get("source_label") or default_source).strip()
    secondary_raw = evidence.get("secondary_evidence")
    secondary = secondary_raw if isinstance(secondary_raw, list) else []
    homepage_notes: list[str] = []
    for item_raw in secondary:
        item = item_raw if isinstance(item_raw, Mapping) else {}
        if item.get("source_type") != FactSourceType.HOMEPAGE.value:
            continue
        resolution_status = str(item.get("resolution_status") or "").strip()
        if resolution_status == FactResolutionStatus.CONFLICTED.value:
            label = "Homepage-Konflikt"
        elif bool(item.get("confirmed")):
            label = "Homepage bestätigt"
        else:
            label = "Homepage-Hinweis"
        if label not in homepage_notes:
            homepage_notes.append(label)
    if not homepage_notes:
        return source
    return f"{source} + {', '.join(homepage_notes)}"


def summary_provenance_label(
    evidence: Mapping[str, Any],
    *,
    fallback_source_type: str = "",
    fallback_source_label: str = "",
    fallback_resolution_status: str = "",
    confidence_threshold: float | None = None,
) -> str:
    return format_provenance_label(
        evidence,
        source_type=fallback_source_type,
        source_label=fallback_source_label,
        resolution_status=fallback_resolution_status,
        confidence_threshold=confidence_threshold,
    )


def status_for_classification_value(value: Any) -> str:
    if is_missing_value(value):
        return "Fehlend"
    return "Automatisch erkannt"


def status_for_answer_value(
    *, question: Question, raw_value: Any, formatted: str
) -> str:
    if is_missing_value(raw_value):
        return "Fehlend"
    if question.answer_type == AnswerType.MULTI_SELECT and isinstance(raw_value, list):
        normalized_items = [str(item).strip() for item in raw_value]
        non_empty_count = sum(1 for item in normalized_items if item)
        if non_empty_count == 0:
            return "Fehlend"
        if non_empty_count < len(normalized_items):
            return "Teilweise"
    if question.answer_type in {
        AnswerType.SHORT_TEXT,
        AnswerType.LONG_TEXT,
    } and isinstance(raw_value, dict):
        return "Teilweise" if has_partial_payload(raw_value) else "Vollständig"
    if not formatted:
        return "Teilweise"
    return "Teilweise" if has_partial_payload(raw_value) else "Vollständig"
