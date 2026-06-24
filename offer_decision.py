"""Pure helpers for offer positioning and salary-decision safety."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from constants import FactKey, FactResolutionStatus
from schemas import JobAdExtract


_EMPTY_VALUES = {"", "unknown", "unklar", "nicht angegeben", "none", "null"}
_FORECAST_EXPECTED_STEP = "benefits"


def compact_offer_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def dedupe_offer_items(values: Sequence[Any], *, limit: int | None = None) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = compact_offer_text(value)
        key = text.casefold()
        if not text or key in seen:
            continue
        output.append(text)
        seen.add(key)
        if limit is not None and len(output) >= limit:
            break
    return output


def _is_meaningful(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().casefold() not in _EMPTY_VALUES
    if isinstance(value, Mapping):
        return any(_is_meaningful(item) for item in value.values())
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return any(_is_meaningful(item) for item in value)
    return True


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _as_text_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if compact_offer_text(value) else []
    if not isinstance(value, Sequence) or isinstance(value, bytes):
        return []
    return dedupe_offer_items(value)


def _job_salary_mapping(job: JobAdExtract) -> dict[str, Any]:
    salary_range = getattr(job, "salary_range", None)
    if salary_range is None:
        return {}
    if hasattr(salary_range, "model_dump"):
        return salary_range.model_dump(mode="json", exclude_none=True)
    if isinstance(salary_range, Mapping):
        return dict(salary_range)
    return {}


def _salary_value_source(
    *,
    job: JobAdExtract,
    intake_facts: Mapping[str, Any],
) -> tuple[Mapping[str, Any], str]:
    fact_value = intake_facts.get(FactKey.BENEFITS_SALARY_RANGE.value)
    if isinstance(fact_value, Mapping) and _is_meaningful(fact_value):
        return fact_value, "intake_fact"
    job_value = _job_salary_mapping(job)
    if _is_meaningful(job_value):
        return job_value, "job_extract"
    return {}, ""


def salary_range_has_numeric_claim(value: Any) -> bool:
    salary = _as_mapping(value)
    return _is_meaningful(salary.get("min")) or _is_meaningful(salary.get("max"))


def format_offer_salary_range(value: Any) -> str:
    salary = _as_mapping(value)
    minimum = compact_offer_text(salary.get("min"))
    maximum = compact_offer_text(salary.get("max"))
    if minimum and maximum:
        amount = f"{minimum} - {maximum}"
    elif minimum:
        amount = f"ab {minimum}"
    elif maximum:
        amount = f"bis {maximum}"
    else:
        return ""
    suffix = " ".join(
        part
        for part in (
            compact_offer_text(salary.get("currency")),
            compact_offer_text(salary.get("period")),
        )
        if part
    )
    return f"{amount} {suffix}".strip()


def _salary_notes(value: Any, job: JobAdExtract) -> str:
    salary = _as_mapping(value)
    notes = compact_offer_text(salary.get("notes"))
    if notes:
        return notes
    return compact_offer_text(_job_salary_mapping(job).get("notes"))


def _salary_resolution_status(
    intake_fact_evidence: Mapping[str, Any],
) -> str:
    evidence = _as_mapping(intake_fact_evidence.get(FactKey.BENEFITS_SALARY_RANGE.value))
    return compact_offer_text(evidence.get("resolution_status")).casefold()


def _is_confirmed_salary_range(
    *,
    value: Any,
    source: str,
    intake_fact_evidence: Mapping[str, Any],
) -> bool:
    if not salary_range_has_numeric_claim(value):
        return False
    if source != "intake_fact":
        return False
    return _salary_resolution_status(intake_fact_evidence) == FactResolutionStatus.CONFIRMED.value


def _forecast_state(
    *,
    salary_forecast: Mapping[str, Any],
    salary_fingerprints: Mapping[str, Any],
    expected_step_key: str,
) -> tuple[str, str]:
    if not salary_forecast or not _is_meaningful(salary_forecast.get("forecast")):
        return "missing", ""

    step_key = compact_offer_text(salary_forecast.get("step_key"))
    fingerprint = compact_offer_text(salary_forecast.get("input_fingerprint"))
    comparison_step = step_key or expected_step_key
    expected_fingerprint = compact_offer_text(salary_fingerprints.get(comparison_step))

    if step_key and step_key != expected_step_key:
        return "stale", step_key
    if fingerprint and expected_fingerprint and fingerprint != expected_fingerprint:
        return "stale", step_key
    if step_key == expected_step_key and fingerprint and expected_fingerprint:
        return "current", step_key
    if step_key == expected_step_key:
        return "unknown", step_key
    return "unknown", step_key


def _forecast_caveat(
    *,
    salary_claim_status: str,
    forecast_state: str,
    salary_notes: str,
) -> str:
    base = (
        "Gehaltsprognose ist eine interne Orientierung und ersetzt keine "
        "Vergütungs-, Rechts- oder Compliance-Prüfung."
    )
    if salary_claim_status == "notes_only":
        return (
            f"{base} Aus einem qualitativen Hinweis wie "
            f"„{salary_notes}“ wird kein numerischer Gehaltsrahmen abgeleitet."
        )
    if salary_claim_status == "unconfirmed_range":
        return f"{base} Numerische Gehaltsangaben vor Veröffentlichung bestätigen."
    if forecast_state == "stale":
        return f"{base} Die gespeicherte Prognose vor finaler Nutzung aktualisieren."
    if forecast_state == "missing":
        return f"{base} Noch keine aktuelle Prognose im Benefits-Schritt vorhanden."
    return base


def _work_model_text(
    *,
    job: JobAdExtract,
    intake_facts: Mapping[str, Any],
) -> str:
    for value in (
        intake_facts.get(FactKey.COMPANY_WORK_ARRANGEMENT.value),
        intake_facts.get(FactKey.COMPANY_REMOTE_POLICY.value),
        getattr(job, "remote_policy", ""),
    ):
        text = compact_offer_text(value)
        if text:
            return text
    return ""


def _start_payload(intake_facts: Mapping[str, Any]) -> Mapping[str, Any]:
    return _as_mapping(intake_facts.get(FactKey.TIMELINE_START_FLEXIBILITY.value))


def _variable_pay_payload(intake_facts: Mapping[str, Any]) -> Mapping[str, Any]:
    return _as_mapping(intake_facts.get(FactKey.BENEFITS_VARIABLE_PAY.value))


def build_offer_decision_context(
    *,
    job: JobAdExtract,
    selected_benefits: Sequence[str] | None = None,
    intake_facts: Mapping[str, Any] | None = None,
    intake_fact_evidence: Mapping[str, Any] | None = None,
    salary_forecast: Mapping[str, Any] | None = None,
    salary_fingerprints: Mapping[str, Any] | None = None,
    expected_forecast_step_key: str = _FORECAST_EXPECTED_STEP,
) -> dict[str, Any]:
    """Build deterministic offer decisions without inventing compensation."""

    facts = intake_facts or {}
    evidence = intake_fact_evidence or {}
    forecast = salary_forecast or {}
    fingerprints = salary_fingerprints or {}

    salary_value, salary_source = _salary_value_source(job=job, intake_facts=facts)
    salary_text = format_offer_salary_range(salary_value)
    salary_notes = _salary_notes(salary_value, job)
    has_numeric_salary_claim = bool(salary_text)
    explicit_salary_range_confirmed = _is_confirmed_salary_range(
        value=salary_value,
        source=salary_source,
        intake_fact_evidence=evidence,
    )
    if explicit_salary_range_confirmed:
        salary_claim_status = "confirmed_range"
    elif has_numeric_salary_claim:
        salary_claim_status = "unconfirmed_range"
    elif salary_notes:
        salary_claim_status = "notes_only"
    else:
        salary_claim_status = "missing"

    forecast_state, forecast_step = _forecast_state(
        salary_forecast=forecast,
        salary_fingerprints=fingerprints,
        expected_step_key=expected_forecast_step_key,
    )

    selected = dedupe_offer_items(selected_benefits or [], limit=12)
    jobspec_benefits = dedupe_offer_items(getattr(job, "benefits", []) or [], limit=12)
    visible_benefits = dedupe_offer_items([*selected, *jobspec_benefits], limit=12)
    offer_components = _as_text_list(facts.get(FactKey.BENEFITS_OFFER_COMPONENTS.value))
    collective_context = _as_text_list(
        facts.get(FactKey.BENEFITS_COLLECTIVE_AGREEMENT_CONTEXT.value)
    )
    compliance_context = _as_text_list(
        facts.get(FactKey.COMPANY_COMPLIANCE_CONTEXT.value)
    )
    non_negotiables = _as_text_list(facts.get(FactKey.COMPANY_NON_NEGOTIABLES.value))
    work_auth = compact_offer_text(
        facts.get(FactKey.LEGAL_WORK_AUTHORIZATION_SUPPORT.value)
    ).casefold()
    work_model = _work_model_text(job=job, intake_facts=facts)
    start = _start_payload(facts)
    variable_pay = _variable_pay_payload(facts)

    candidate_value = dedupe_offer_items(
        [
            *visible_benefits[:6],
            f"Arbeitsmodell: {work_model}" if work_model else "",
            *offer_components[:3],
        ],
        limit=8,
    )
    fixed_terms: list[str] = []
    negotiable_terms: list[str] = []
    early_candidate_info: list[str] = []

    if explicit_salary_range_confirmed:
        fixed_terms.append(f"Gehaltsrahmen: {salary_text}")
        candidate_value = dedupe_offer_items(
            [*candidate_value, f"Vergütung: {salary_text}"],
            limit=8,
        )
    elif has_numeric_salary_claim:
        early_candidate_info.append(
            f"Gehaltsrahmen vor Veröffentlichung bestätigen: {salary_text}"
        )
    elif salary_notes:
        early_candidate_info.append(f"Vergütungshinweis prüfen: {salary_notes}")
    else:
        early_candidate_info.append("Gehaltsrahmen früh klären")

    if work_model:
        fixed_terms.append(f"Arbeitsmodell: {work_model}")
    else:
        early_candidate_info.append("Arbeitsmodell früh klären")

    if collective_context and "Keine bekannt" not in collective_context:
        fixed_terms.append("Rahmenvorgaben: " + ", ".join(collective_context[:4]))
    if compliance_context:
        fixed_terms.append("Compliance-Kontext: " + ", ".join(compliance_context[:3]))
    if non_negotiables:
        fixed_terms.append("Nicht verhandelbar: " + ", ".join(non_negotiables[:3]))

    eligible = variable_pay.get("eligible")
    if eligible is True:
        ote_text = format_offer_salary_range(
            {
                "min": variable_pay.get("ote_min"),
                "max": variable_pay.get("ote_max"),
                "currency": variable_pay.get("currency"),
                "period": variable_pay.get("period"),
            }
        )
        fixed_terms.append(
            f"Variable Vergütung vorgesehen{': ' + ote_text if ote_text else ''}"
        )
    elif eligible is False:
        fixed_terms.append("Keine variable Vergütung vorgesehen")
    else:
        early_candidate_info.append("Variable Vergütung bestätigen oder ausschließen")

    target_start = compact_offer_text(start.get("target_start"))
    flexibility = compact_offer_text(start.get("flexibility")).casefold()
    if flexibility == "fixed" and target_start:
        fixed_terms.append(f"Starttermin: {target_start}")
    elif flexibility and flexibility != "unknown":
        negotiable_terms.append(f"Startflexibilität: {flexibility}")
    else:
        early_candidate_info.append("Starttermin und Flexibilität früh klären")

    if work_auth == "yes":
        fixed_terms.append("Arbeitserlaubnis-Support möglich")
    elif work_auth == "no":
        fixed_terms.append("Kein Arbeitserlaubnis-Support vorgesehen")
    else:
        early_candidate_info.append("Visa-/Arbeitserlaubnis-Support früh klären")

    negotiable_terms.extend(
        f"Angebotsbaustein: {item}" for item in offer_components[:6]
    )

    missing_assumptions: list[str] = []
    if not compact_offer_text(job.job_title):
        missing_assumptions.append("Rolle/Jobtitel für Prognose")
    if not compact_offer_text(job.location_country or job.location_city):
        missing_assumptions.append("Standort oder Zielregion")
    if not compact_offer_text(job.seniority_level):
        missing_assumptions.append("Seniority/Erfahrungsniveau")
    if not job.must_have_skills:
        missing_assumptions.append("Must-have-Skills")
    if not visible_benefits:
        missing_assumptions.append("Candidate Value / Benefits")
    if forecast_state in {"missing", "stale", "unknown"}:
        missing_assumptions.append("Aktuelle Gehaltsprognose im Benefits-Schritt")
    if has_numeric_salary_claim and not explicit_salary_range_confirmed:
        missing_assumptions.append("Bestätigter numerischer Gehaltsrahmen")

    salary_decision = {
        "salary_claim_status": salary_claim_status,
        "has_numeric_salary_claim": has_numeric_salary_claim,
        "explicit_salary_range_confirmed": explicit_salary_range_confirmed,
        "salary_text": salary_text,
        "salary_notes": salary_notes,
        "salary_source": salary_source,
        "forecast_present": bool(forecast_state != "missing"),
        "forecast_state": forecast_state,
        "forecast_step_key": forecast_step,
        "forecast_is_stale": forecast_state == "stale",
        "orientation_only": True,
        "salary_caveat": _forecast_caveat(
            salary_claim_status=salary_claim_status,
            forecast_state=forecast_state,
            salary_notes=salary_notes,
        ),
    }

    result = {
        "candidate_value": candidate_value,
        "fixed_terms": dedupe_offer_items(fixed_terms, limit=10),
        "negotiable_terms": dedupe_offer_items(negotiable_terms, limit=10),
        "early_candidate_info": dedupe_offer_items(early_candidate_info, limit=10),
        "salary_decision": {
            key: value
            for key, value in salary_decision.items()
            if value not in ("", None, [])
        },
        "salary_caveat": salary_decision["salary_caveat"],
        "missing_assumptions": dedupe_offer_items(missing_assumptions, limit=12),
        "constraints": {
            "work_model": work_model,
            "collective_context": collective_context,
            "compliance_context": compliance_context,
            "non_negotiables": non_negotiables,
            "work_authorization_support": work_auth,
            "start": dict(start) if start else {},
        },
        "artifact_impact": [
            "job_ad",
            "brief",
            "interview_hr",
            "interview_fach",
            "boolean_search",
            "salary_forecast",
        ],
    }
    return {
        key: value
        for key, value in result.items()
        if _is_meaningful(value) or key in {"salary_decision", "salary_caveat"}
    }


def salary_claim_blocker_codes(offer_positioning: Mapping[str, Any]) -> list[str]:
    salary_decision = _as_mapping(offer_positioning.get("salary_decision"))
    if not bool(salary_decision.get("has_numeric_salary_claim")):
        return []
    blockers: list[str] = []
    if not bool(salary_decision.get("explicit_salary_range_confirmed")):
        blockers.append("unconfirmed_numeric_salary")
    if bool(salary_decision.get("forecast_is_stale")):
        blockers.append("stale_salary_forecast")
    return blockers


def forecast_assumption_warnings(
    offer_positioning: Mapping[str, Any],
) -> list[str]:
    raw = offer_positioning.get("missing_assumptions")
    return _as_text_list(raw)[:6]
