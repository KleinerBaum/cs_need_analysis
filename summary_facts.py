"""Pure helpers for Summary fact rows and value formatting."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from constants import AnswerType, FactKey
from schemas import Question, question_option_label_map


@dataclass(frozen=True)
class SummaryFactsRow:
    bereich: str
    feld: str
    wert: str
    quelle: str
    status: str

    def to_dict(self) -> dict[str, str]:
        return {
            "Bereich": self.bereich,
            "Feld": self.feld,
            "Wert": self.wert,
            "Quelle": self.quelle,
            "Status": self.status,
        }


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
        return " | ".join(str(item).strip() for item in value if str(item).strip())
    if isinstance(value, dict):
        parts = [
            f"{str(key).strip()}: {str(item).strip()}"
            for key, item in value.items()
            if str(key).strip() and not is_missing_value(item)
        ]
        return " | ".join(parts)
    return str(value or "").strip()


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
        source = str(evidence.get("source_label") or "Intake-Fakt").strip()
        return SummaryFactsRow(
            "Kernprofil",
            label,
            format_summary_fact_value(fact_value) or "Nicht angegeben",
            source,
            status_for_value(fact_value),
        )
    return SummaryFactsRow(
        "Kernprofil",
        label,
        format_summary_fact_value(fallback_value) or "Nicht angegeben",
        "Jobspec",
        status_for_value(fallback_value),
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
