"""Pure helpers for rendering and editing job extract review data."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal, TypedDict

JOB_EXTRACT_DISPLAY_LABELS: dict[str, str] = {
    "job_title": "Jobtitel",
    "company_name": "Unternehmen",
    "brand_name": "Marke",
    "company_website": "Unternehmenswebsite",
    "language_guess": "Erkannte Sprache",
    "employment_type": "Beschäftigungsart",
    "contract_type": "Vertragsart",
    "seniority_level": "Senioritätslevel",
    "start_date": "Startdatum",
    "application_deadline": "Bewerbungsfrist",
    "job_ref_number": "Referenznummer",
    "department_name": "Abteilung",
    "reports_to": "Berichtet an",
    "location_city": "Ort",
    "location_country": "Land",
    "place_of_work": "Arbeitsort",
    "remote_policy": "Remote-Regelung",
    "travel_required": "Reisebereitschaft",
    "on_call": "Rufbereitschaft",
    "direct_reports_count": "Anzahl direkter Reports",
    "role_overview": "Rollenüberblick",
    "onboarding_notes": "Onboarding-Hinweise",
    "responsibilities": "Aufgaben",
    "deliverables": "Lieferergebnisse",
    "success_metrics": "Erfolgskriterien",
    "must_have_skills": "Muss-Skills",
    "nice_to_have_skills": "Kann-Skills",
    "soft_skills": "Soft Skills",
    "education": "Ausbildung",
    "education_requirements": "Ausbildung",
    "certifications": "Zertifikate / Qualifikationen",
    "languages": "Sprachen",
    "tech_stack": "Technische Anforderungen",
    "domain_expertise": "Branchenerfahrung",
    "salary_range": "Gehaltsrahmen",
    "benefits": "Benefits",
    "recruitment_steps": "Recruiting-Prozess",
    "contacts": "Kontakte",
    "steps": "Prozessschritte",
    "QuestionPlan": "Fragenplan",
}

JOB_EXTRACT_TAB_FIELDS: dict[str, tuple[str, ...]] = {
    "Basis": (
        "job_title",
        "company_name",
        "brand_name",
        "company_website",
        "language_guess",
        "employment_type",
        "contract_type",
        "seniority_level",
        "start_date",
        "application_deadline",
        "job_ref_number",
        "department_name",
        "reports_to",
    ),
    "Standort": (
        "location_city",
        "location_country",
        "place_of_work",
        "remote_policy",
        "travel_required",
        "on_call",
        "direct_reports_count",
    ),
    "Rolle": ("role_overview", "onboarding_notes"),
    "Skills & Benefits": (
        "responsibilities",
        "deliverables",
        "success_metrics",
        "must_have_skills",
        "nice_to_have_skills",
        "soft_skills",
        "education",
        "certifications",
        "languages",
        "tech_stack",
        "domain_expertise",
        "salary_range",
        "benefits",
    ),
    "Prozess": ("recruitment_steps", "contacts"),
}

JOB_EXTRACT_REVIEW_EMPTY_FIELDS: frozenset[str] = frozenset(
    {
        "job_title",
        "company_name",
        "location_city",
        "location_country",
        "place_of_work",
        "remote_policy",
        "employment_type",
        "contract_type",
        "seniority_level",
        "role_overview",
    }
)

JOB_EXTRACT_TAB_NOTE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Basis": (
        "job_title",
        "company",
        "brand",
        "contract",
        "employment",
        "language",
        "deadline",
        "reference",
        "department",
        "reports_to",
    ),
    "Standort": ("location", "place_of_work", "remote", "travel", "on call", "on_call"),
    "Rolle": ("role", "overview", "responsibility", "deliverable", "success"),
    "Skills & Benefits": (
        "skill",
        "education",
        "certificate",
        "language",
        "tech",
        "domain",
        "salary",
        "benefit",
    ),
    "Prozess": (
        "process",
        "recruit",
        "contact",
        "step",
        "interview",
        "start",
        "questionplan",
        "question_plan",
        "question plan",
    ),
}

JOB_EXTRACT_HYPOTHESIS_GROUP_LABELS: dict[str, str] = {
    "ready_to_accept": "Hochsicher übernehmen",
    "needs_confirmation": "Kurz bestätigen",
    "needs_clarification": "Aktiv klären",
}


class JobExtractHypothesisRow(TypedDict):
    field_name: str
    label: str
    value: Any
    display_value: str
    group_key: Literal[
        "ready_to_accept", "needs_confirmation", "needs_clarification"
    ]
    confidence: float | None
    needs_confirmation: bool
    evidence_snippet: str
    editable: bool


def normalize_display_text(value: object) -> str:
    text = str(value or "").strip()
    return text if text else "—"


def format_salary_range_value(value: Any) -> str:
    if value is None:
        return "—"
    if hasattr(value, "model_dump"):
        try:
            value = value.model_dump()
        except Exception:
            value = value
    if not isinstance(value, dict):
        return normalize_display_text(value)

    min_value = value.get("min")
    max_value = value.get("max")
    currency = str(value.get("currency") or "").strip()
    period = str(value.get("period") or "").strip()
    notes = str(value.get("notes") or "").strip()

    parts: list[str] = []
    if min_value is not None or max_value is not None:
        min_text = "—" if min_value is None else str(min_value)
        max_text = "—" if max_value is None else str(max_value)
        parts.append(f"{min_text} – {max_text}")
    if currency:
        parts.append(currency)
    if period:
        parts.append(f"/ {period}")
    if notes:
        parts.append(f"({notes})")
    return " ".join(parts) if parts else "—"


def format_recruitment_steps_value(value: Any) -> str:
    if not value:
        return "—"
    if not isinstance(value, list):
        return normalize_display_text(value)

    items: list[str] = []
    for entry in value:
        if hasattr(entry, "name"):
            step_name = str(getattr(entry, "name", "") or "").strip()
            step_details = str(getattr(entry, "details", "") or "").strip()
        elif isinstance(entry, dict):
            step_name = str(entry.get("name") or "").strip()
            step_details = str(entry.get("details") or "").strip()
        else:
            step_name = str(entry or "").strip()
            step_details = ""
        if not step_name:
            continue
        if step_details:
            items.append(f"{step_name} ({step_details})")
        else:
            items.append(step_name)
    if not items:
        return "—"
    preview = items[:3]
    suffix = f" +{len(items) - len(preview)} weitere" if len(items) > len(preview) else ""
    return " · ".join(preview) + suffix


def format_review_value(value: Any) -> str:
    if isinstance(value, list):
        items = [normalize_display_text(item) for item in value if has_meaningful_value(item)]
        return "\n".join(items) if items else ""
    if isinstance(value, dict):
        if {"min", "max", "currency", "period"} & set(value):
            return format_salary_range_value(value)
        return normalize_display_text(value)
    return "" if value is None else str(value).strip()


def is_simple_review_editable(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (str, int, float, bool)):
        return True
    if isinstance(value, list):
        return all(not isinstance(item, (dict, list)) for item in value)
    return False


def classify_job_extract_hypothesis(
    *,
    value: Any,
    confidence: float | None = None,
    needs_confirmation: bool = False,
) -> Literal["ready_to_accept", "needs_confirmation", "needs_clarification"]:
    if not has_meaningful_value(value):
        return "needs_clarification"
    if needs_confirmation:
        return "needs_confirmation"
    if confidence is None:
        return "needs_confirmation"
    if confidence >= 0.85:
        return "ready_to_accept"
    if confidence >= 0.55:
        return "needs_confirmation"
    return "needs_clarification"


def build_job_extract_hypothesis_groups(
    values: dict[str, Any],
    evidence_by_field: dict[str, Any] | None = None,
) -> dict[str, list[JobExtractHypothesisRow]]:
    grouped: dict[str, list[JobExtractHypothesisRow]] = {
        group_key: [] for group_key in JOB_EXTRACT_HYPOTHESIS_GROUP_LABELS
    }
    evidence_by_field = evidence_by_field or {}
    ordered_fields = [
        field
        for fields in JOB_EXTRACT_TAB_FIELDS.values()
        for field in fields
        if field in values
    ]
    seen: set[str] = set()
    for field_name in ordered_fields:
        if field_name in seen:
            continue
        seen.add(field_name)
        value = values.get(field_name)
        if (
            not has_meaningful_value(value)
            and field_name not in JOB_EXTRACT_REVIEW_EMPTY_FIELDS
        ):
            continue
        evidence = evidence_by_field.get(field_name)
        confidence: float | None = None
        needs_confirmation = False
        evidence_snippet = ""
        if isinstance(evidence, dict):
            try:
                confidence = max(0.0, min(1.0, float(evidence.get("confidence"))))
            except (TypeError, ValueError):
                confidence = None
            needs_confirmation = bool(evidence.get("needs_confirmation"))
            evidence_snippet = str(evidence.get("evidence_snippet") or "").strip()
        group_key = classify_job_extract_hypothesis(
            value=value,
            confidence=confidence,
            needs_confirmation=needs_confirmation,
        )
        grouped[group_key].append(
            {
                "field_name": field_name,
                "label": JOB_EXTRACT_DISPLAY_LABELS.get(field_name, field_name),
                "value": value,
                "display_value": format_review_value(value),
                "group_key": group_key,
                "confidence": confidence,
                "needs_confirmation": needs_confirmation,
                "evidence_snippet": evidence_snippet,
                "editable": is_simple_review_editable(value),
            }
        )
    return grouped


def classify_extract_note_tab(note: str) -> str:
    normalized = " ".join(str(note or "").strip().casefold().split())
    if not normalized:
        return "Basis"

    best_tab = "Basis"
    best_score = 0
    for tab_name, keywords in JOB_EXTRACT_TAB_NOTE_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in normalized)
        if score > best_score:
            best_tab = tab_name
            best_score = score
    return best_tab


def group_extract_notes_by_tab(
    notes: Sequence[str] | None,
) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {tab_name: [] for tab_name in JOB_EXTRACT_TAB_FIELDS}
    if not notes:
        return grouped

    seen: set[str] = set()
    for note in notes:
        normalized = " ".join(str(note or "").strip().split())
        if not normalized:
            continue
        dedupe_key = normalized.casefold()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        grouped[classify_extract_note_tab(normalized)].append(normalized)
    return grouped


def has_meaningful_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, float):
        return not value != value

    text = str(value).strip()
    if not text:
        return False
    lowered = text.lower()
    return lowered not in {"nan", "none", "null", "n/a", "na", "-", "—"}


def normalize_optional_string(value: Any) -> str | None:
    if not has_meaningful_value(value):
        return None
    text = str(value).strip()
    return text or None


def sanitize_display_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: sanitize_display_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [
            v
            for item in value
            for v in [sanitize_display_value(item)]
            if v is not None
        ]
    return value if has_meaningful_value(value) else None


def parse_optional_int(value: Any) -> int | None:
    normalized = normalize_optional_string(value)
    if normalized is None:
        return None
    try:
        return int(float(normalized))
    except ValueError:
        return None
