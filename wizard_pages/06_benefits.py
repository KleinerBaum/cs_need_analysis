# wizard_pages/06_benefits.py
from __future__ import annotations
import logging
from html import escape
from typing import Any

import streamlit as st

from constants import (
    FactKey,
    SSKey,
    STEP_KEY_BENEFITS,
    STEP_SECTION_EXTRACTED_FROM_JOBSPEC,
    STEP_SECTION_OPEN_QUESTIONS,
    STEP_SECTION_REVIEW,
    STEP_SECTION_SALARY_FORECAST,
    STEP_SECTION_SOURCE_COMPARISON,
)
from intake_facts import (
    get_intake_fact_evidence_state,
    get_intake_fact_state,
    write_intake_fact_by_legacy_field,
)
from offer_decision import build_offer_decision_context
from llm_client import (
    TASK_GENERATE_BENEFIT_SUGGESTIONS,
    TASK_GENERATE_ROLE_TASKS_SALARY_FORECAST,
    generate_benefit_suggestions,
    resolve_model_for_task,
)
from schemas import JobAdExtract, QuestionStep
from safe_html import render_static_html
from settings_openai import load_openai_settings
from state import get_answers, get_esco_semantic_context
from summary_exports import build_live_artifact_preview_payload
from step_sections import build_step_shell_section_kwargs
from ui_layout import (
    LazySectionConfig,
    default_focus_drilldown_open,
    default_primary_workspace_open,
    is_focus_design_enabled,
    render_step_shell,
    responsive_three_columns,
    responsive_two_columns,
)
from ui_components import (
    build_step_review_payload,
    has_answered_question_with_keywords,
    has_meaningful_value,
    render_error_banner,
    render_live_artifact_preview_panel,
    render_question_step,
    render_recruiting_consistency_checklist,
    render_source_pill_selection,
    ReviewRenderContext,
    resolve_standard_review_mode,
    render_standard_step_review,
)
from wizard_pages.base import (
    WizardContext,
    WizardPage,
    guard_job_and_plan,
    nav_buttons,
    resolve_dynamic_step_copy,
)
from wizard_pages.fact_inputs import (
    compact_text,
    fact_value,
    persist_compact_object,
    render_multiselect_fact,
    render_select_fact,
    section_container,
)
from wizard_pages.salary_forecast_panel import render_benefits_salary_forecast_panel

LOGGER = logging.getLogger(__name__)

_LEGACY_BENEFITS_SELECTED_COMPARE_KEY = "benefits.compare.selected"
_LEGACY_BENEFITS_AI_SUGGESTED_KEY = "benefits.ai_suggested"
_YES_NO_UNKNOWN_LABELS = {
    "unknown": "Noch unklar",
    "yes": "Ja",
    "no": "Nein",
}
_PERIOD_LABELS = {
    "yearly": "pro Jahr",
    "monthly": "pro Monat",
    "hourly": "pro Stunde",
    "one_time": "einmalig",
}
_START_FLEXIBILITY_LABELS = {
    "fixed": "Fix",
    "plus_minus_2_weeks": "+/- 2 Wochen",
    "plus_minus_1_month": "+/- 1 Monat",
    "flexible": "Flexibel",
    "unknown": "Noch unklar",
}


def _render_benefits_consistency_checklist(
    *,
    job: JobAdExtract,
    step: QuestionStep | None,
) -> None:
    review_payload = build_step_review_payload(step)
    visible_questions = review_payload["visible_questions"]
    answered_lookup = review_payload["answered_lookup"]
    step_status = review_payload["step_status"]

    salary_extracted = bool(
        job.salary_range and (job.salary_range.min or job.salary_range.max)
    )
    benefits_extracted = any(has_meaningful_value(item) for item in job.benefits)
    remote_extracted = has_meaningful_value(job.remote_policy)

    checks = [
        (
            "Gehalt ist intern abgestimmt.",
            salary_extracted
            or has_answered_question_with_keywords(
                questions=visible_questions,
                answered_lookup=answered_lookup,
                keywords=("gehalt", "salary", "vergütung", "compensation"),
            ),
        ),
        (
            "Arbeitsmodell ist abgestimmt.",
            remote_extracted
            or has_answered_question_with_keywords(
                questions=visible_questions,
                answered_lookup=answered_lookup,
                keywords=("remote", "hybrid", "onsite", "homeoffice", "arbeitsmodell"),
            ),
        ),
        (
            "Benefits sind priorisiert.",
            benefits_extracted
            or has_answered_question_with_keywords(
                questions=visible_questions,
                answered_lookup=answered_lookup,
                keywords=("benefit", "perk", "zusatz", "budget"),
            ),
        ),
        (
            "Wichtige Rückfragen sind beantwortet.",
            step_status["essentials_total"] == 0
            or step_status["essentials_answered"] == step_status["essentials_total"],
        ),
    ]

    render_recruiting_consistency_checklist(
        title="Kurzcheck",
        checks=checks,
        caption="Passt das Angebot für interne Abstimmung und externe Kommunikation?",
    )


def _normalize_answer_value(value: object) -> str:
    if isinstance(value, list):
        parts = [str(item).strip() for item in value if has_meaningful_value(item)]
        return ", ".join(parts)
    return str(value or "").strip()


def _normalize_benefit_term(term: str) -> str:
    return " ".join(str(term or "").strip().casefold().split())


def _dedupe_benefit_terms(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = str(value or "").strip()
        normalized = _normalize_benefit_term(cleaned)
        if not normalized or normalized in seen:
            continue
        deduped.append(cleaned)
        seen.add(normalized)
    return deduped


def _read_selected_texts(state_key: SSKey) -> list[str]:
    raw = st.session_state.get(state_key.value, [])
    return (
        _dedupe_benefit_terms([str(item) for item in raw])
        if isinstance(raw, list)
        else []
    )


def _benefit_labels_from_suggestions(raw_items: object) -> list[str]:
    if not isinstance(raw_items, list):
        return []
    labels: list[str] = []
    for item in raw_items:
        if isinstance(item, dict):
            label = str(item.get("label") or "").strip()
        else:
            label = str(item or "").strip()
        if label:
            labels.append(label)
    return _dedupe_benefit_terms(labels)


def _migrate_legacy_benefit_state() -> None:
    selected = st.session_state.get(SSKey.BENEFITS_SELECTED.value, [])
    legacy_selected = st.session_state.get(_LEGACY_BENEFITS_SELECTED_COMPARE_KEY, [])
    if (
        not selected
        and isinstance(legacy_selected, list)
        and _benefit_labels_from_suggestions(legacy_selected)
    ):
        st.session_state[SSKey.BENEFITS_SELECTED.value] = (
            _benefit_labels_from_suggestions(legacy_selected)
        )
    st.session_state.pop(_LEGACY_BENEFITS_SELECTED_COMPARE_KEY, None)

    llm_suggested = st.session_state.get(SSKey.BENEFITS_LLM_SUGGESTED.value, [])
    legacy_ai = st.session_state.get(_LEGACY_BENEFITS_AI_SUGGESTED_KEY, [])
    if not llm_suggested and isinstance(legacy_ai, list):
        migrated = [
            {
                "label": label,
                "source_hint": "llm",
                "rationale": "Aus Legacy Benefits-Vorschlägen übernommen.",
                "evidence": "",
                "importance": "medium",
            }
            for label in _benefit_labels_from_suggestions(legacy_ai)
        ]
        if migrated:
            st.session_state[SSKey.BENEFITS_LLM_SUGGESTED.value] = migrated
    st.session_state.pop(_LEGACY_BENEFITS_AI_SUGGESTED_KEY, None)


def _read_selected_benefits() -> list[str]:
    raw = st.session_state.get(SSKey.BENEFITS_SELECTED.value, [])
    if not isinstance(raw, list):
        return []
    return _dedupe_benefit_terms(
        [str(item).strip() for item in raw if has_meaningful_value(item)]
    )


def _sync_selected_benefit_intake_facts() -> None:
    write_intake_fact_by_legacy_field(
        st.session_state,
        "benefits",
        _read_selected_benefits(),
    )


def _suggestion_dicts_from_labels(labels: list[str], *, source: str) -> list[dict[str, str]]:
    return [{"label": label, "source": source} for label in labels if label.strip()]


def _salary_period_label(period: object) -> str:
    return _PERIOD_LABELS.get(compact_text(period), compact_text(period))


def _format_salary_range(job: JobAdExtract) -> str:
    salary_range = job.salary_range
    if not salary_range:
        return ""

    salary_min = getattr(salary_range, "min", None)
    salary_max = getattr(salary_range, "max", None)
    if not has_meaningful_value(salary_min) and not has_meaningful_value(salary_max):
        return ""

    if has_meaningful_value(salary_min) and has_meaningful_value(salary_max):
        amount = f"{salary_min} - {salary_max}"
    elif has_meaningful_value(salary_min):
        amount = f"ab {salary_min}"
    else:
        amount = f"bis {salary_max}"

    details = [
        compact_text(getattr(salary_range, "currency", "")),
        _salary_period_label(getattr(salary_range, "period", "")),
    ]
    suffix = " ".join(item for item in details if item)
    return f"{amount} {suffix}".strip()


def _render_compact_value_block(
    *,
    title: str,
    value: str,
    empty: str = "Noch offen",
    note: str = "",
) -> None:
    st.markdown(f"**{title}**")
    if value:
        st.write(value)
        if note:
            st.caption(note)
        return
    st.caption(empty)


def _as_compact_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [compact_text(item) for item in value if compact_text(item)]


def _render_outcome_list(
    *,
    title: str,
    items: list[str],
    empty: str,
) -> None:
    with section_container(border=True):
        st.markdown(f"**{title}**")
        if not items:
            st.caption(empty)
            return
        for item in items[:5]:
            st.write(f"- {item}")
        if len(items) > 5:
            st.caption(f"+ {len(items) - 5} weitere")


def _render_label_list(
    labels: list[str],
    *,
    limit: int = 8,
    empty: str = "Noch keine Benefits ausgewählt.",
) -> None:
    if not labels:
        st.caption(empty)
        return
    shown_labels = labels[:limit]
    chip_html = "".join(
        (
            '<span class="cs-benefit-chip" '
            f'title="{escape(label, quote=True)}">{escape(label[:72])}'
            f'{"…" if len(label) > 72 else ""}</span>'
        )
        for label in shown_labels
    )
    render_static_html(
        f"""
        <div class="cs-benefit-chip-row">{chip_html}</div>
        <style>
        .cs-benefit-chip-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.35rem;
            margin: 0.25rem 0 0.35rem;
        }}
        .cs-benefit-chip {{
            display: inline-flex;
            max-width: min(100%, 26rem);
            padding: 0.22rem 0.55rem;
            border-radius: 999px;
            border: 1px solid var(--cs-border-soft);
            background: var(--cs-surface-muted);
            color: var(--cs-text);
            font-size: 0.82rem;
            line-height: 1.35;
            overflow-wrap: anywhere;
        }}
        </style>
        """,
        streamlit_module=st,
    )
    remaining = len(labels) - limit
    if remaining > 0:
        st.caption(f"+ {remaining} weitere")


def _answers_with_benefit_context(*, region_context: str) -> dict[str, Any]:
    answers = dict(get_answers())
    region = region_context.strip()
    if region:
        answers["benefit_generation_context"] = {
            "region": region,
            "instruction": "Berücksichtige regionale Benefits und Rahmenbedingungen.",
        }
    return answers


def _generate_ai_benefit_suggestions(
    *,
    job: JobAdExtract,
    existing_benefits: list[str],
    target_benefit_count: int,
    region_context: str,
) -> list[dict[str, Any]] | None:
    settings = load_openai_settings()
    suggestion_model = resolve_model_for_task(
        task_kind=TASK_GENERATE_BENEFIT_SUGGESTIONS,
        session_override=None,
        settings=settings,
    )
    try:
        suggestion_pack, _usage = generate_benefit_suggestions(
            job=job,
            answers=_answers_with_benefit_context(region_context=region_context),
            existing_benefits=existing_benefits,
            target_benefit_count=target_benefit_count,
            model=suggestion_model,
            language=str(st.session_state.get(SSKey.LANGUAGE.value, "de")),
            store=bool(st.session_state.get(SSKey.STORE_API_OUTPUT.value, False)),
        )
    except Exception:
        LOGGER.exception("Benefit suggestions could not be generated.")
        st.warning(
            "Vorschläge konnten nicht erzeugt werden. Wähle Benefits aus Anzeige/Antworten oder erfasse Angebotsbestandteile unten manuell."
        )
        return None

    blocked = {_normalize_benefit_term(label) for label in existing_benefits}
    merged_llm: list[dict[str, Any]] = []
    seen: set[str] = set(blocked)
    for item in suggestion_pack.benefits:
        label = item.label.strip()
        normalized = _normalize_benefit_term(label)
        if not normalized or normalized in seen:
            continue
        merged_llm.append(item.model_dump(mode="json"))
        seen.add(normalized)
    st.session_state[SSKey.BENEFITS_LLM_SUGGESTED.value] = merged_llm
    return merged_llm


def _render_variable_pay_block() -> None:
    current_raw = fact_value(FactKey.BENEFITS_VARIABLE_PAY, {})
    current = current_raw if isinstance(current_raw, dict) else {}
    eligible_raw = current.get("eligible")
    if isinstance(eligible_raw, bool):
        eligible_current = "yes" if eligible_raw else "no"
    else:
        eligible_current = compact_text(eligible_raw)
    if eligible_current not in _YES_NO_UNKNOWN_LABELS:
        eligible_current = "unknown"
    col_eligible, col_min, col_max = responsive_three_columns(gap="large")
    with col_eligible:
        eligible = st.selectbox(
            "Variable Vergütung?",
            options=tuple(_YES_NO_UNKNOWN_LABELS),
            index=tuple(_YES_NO_UNKNOWN_LABELS).index(eligible_current),
            format_func=lambda value: _YES_NO_UNKNOWN_LABELS.get(value, value),
            key=f"fact_input.{FactKey.BENEFITS_VARIABLE_PAY.value}.eligible",
        )
    with col_min:
        ote_min = st.number_input(
            "OTE von",
            min_value=0.0,
            value=float(current.get("ote_min") or 0),
            step=1000.0,
            key=f"fact_input.{FactKey.BENEFITS_VARIABLE_PAY.value}.ote_min",
        )
    with col_max:
        ote_max = st.number_input(
            "OTE bis",
            min_value=0.0,
            value=float(current.get("ote_max") or 0),
            step=1000.0,
            key=f"fact_input.{FactKey.BENEFITS_VARIABLE_PAY.value}.ote_max",
        )
    if ote_min and ote_max and ote_min > ote_max:
        st.error("OTE von darf nicht höher als OTE bis sein. Bitte Betrag korrigieren.")
    col_currency, col_period = responsive_two_columns(gap="large")
    with col_currency:
        currency = st.text_input(
            "Währung",
            value=compact_text(current.get("currency") or "EUR"),
            key=f"fact_input.{FactKey.BENEFITS_VARIABLE_PAY.value}.currency",
        )
    with col_period:
        period = st.selectbox(
            "Zeitraum",
            options=("yearly", "monthly", "hourly", "one_time"),
            index=("yearly", "monthly", "hourly", "one_time").index(
                compact_text(current.get("period"))
                if compact_text(current.get("period")) in {"yearly", "monthly", "hourly", "one_time"}
                else "yearly"
            ),
            format_func=lambda value: _PERIOD_LABELS.get(value, value),
            key=f"fact_input.{FactKey.BENEFITS_VARIABLE_PAY.value}.period",
        )
    bonus_logic = st.text_area(
        "Bonuslogik",
        value=str(current.get("bonus_logic") or ""),
        height=80,
        key=f"fact_input.{FactKey.BENEFITS_VARIABLE_PAY.value}.bonus_logic",
    )
    persist_compact_object(
        FactKey.BENEFITS_VARIABLE_PAY,
        {
            "eligible": eligible == "yes" if eligible != "unknown" else None,
            "ote_min": ote_min or None,
            "ote_max": ote_max or None,
            "currency": currency,
            "period": period,
            "bonus_logic": bonus_logic,
        },
    )


def _render_shift_compensation_block() -> None:
    current_raw = fact_value(FactKey.BENEFITS_SHIFT_COMPENSATION, {})
    current = current_raw if isinstance(current_raw, dict) else {}
    col_rotation, col_extra = responsive_two_columns(gap="large")
    with col_rotation:
        rotation = st.text_input(
            "Rotation",
            value=compact_text(current.get("rotation")),
            placeholder="z. B. alle 6 Wochen, keine",
            key=f"fact_input.{FactKey.BENEFITS_SHIFT_COMPENSATION.value}.rotation",
        )
    with col_extra:
        compensation = st.text_input(
            "Ausgleich / Zuschläge",
            value=compact_text(current.get("compensation")),
            key=f"fact_input.{FactKey.BENEFITS_SHIFT_COMPENSATION.value}.compensation",
        )
    notes = st.text_area(
        "Besondere Zeiten",
        value=str(current.get("notes") or ""),
        height=80,
        key=f"fact_input.{FactKey.BENEFITS_SHIFT_COMPENSATION.value}.notes",
    )
    persist_compact_object(
        FactKey.BENEFITS_SHIFT_COMPENSATION,
        {
            "rotation": rotation,
            "compensation": compensation,
            "notes": notes,
        },
    )


def _render_start_flexibility_block(job: JobAdExtract) -> None:
    current_raw = fact_value(FactKey.TIMELINE_START_FLEXIBILITY, {})
    current = current_raw if isinstance(current_raw, dict) else {}
    col_target, col_flex = responsive_two_columns(gap="large")
    with col_target:
        target_start = st.text_input(
            "Starttermin",
            value=compact_text(current.get("target_start") or job.start_date or ""),
            placeholder="YYYY-MM-DD oder freier Zeitraum",
            key=f"fact_input.{FactKey.TIMELINE_START_FLEXIBILITY.value}.target",
        )
    with col_flex:
        flexibility = st.selectbox(
            "Flexibilität",
            options=("fixed", "plus_minus_2_weeks", "plus_minus_1_month", "flexible", "unknown"),
            index=("fixed", "plus_minus_2_weeks", "plus_minus_1_month", "flexible", "unknown").index(
                compact_text(current.get("flexibility"))
                if compact_text(current.get("flexibility")) in {"fixed", "plus_minus_2_weeks", "plus_minus_1_month", "flexible", "unknown"}
                else "unknown"
            ),
            format_func=lambda value: _START_FLEXIBILITY_LABELS.get(value, value),
            key=f"fact_input.{FactKey.TIMELINE_START_FLEXIBILITY.value}.flexibility",
        )
    notice_period = st.text_input(
        "Kündigungsfristen / Einschränkungen",
        value=compact_text(current.get("notice_period")),
        key=f"fact_input.{FactKey.TIMELINE_START_FLEXIBILITY.value}.notice",
    )
    persist_compact_object(
        FactKey.TIMELINE_START_FLEXIBILITY,
        {
            "target_start": target_start,
            "flexibility": flexibility,
            "notice_period": notice_period,
        },
    )


def _offer_outcome_items(
    *,
    job: JobAdExtract,
    selected_benefits: list[str],
) -> tuple[list[str], list[str], list[str]]:
    salary_text = _format_salary_range(job)
    remote_text = compact_text(job.remote_policy)
    variable_pay_raw = fact_value(FactKey.BENEFITS_VARIABLE_PAY, {})
    variable_pay = variable_pay_raw if isinstance(variable_pay_raw, dict) else {}
    shift_raw = fact_value(FactKey.BENEFITS_SHIFT_COMPENSATION, {})
    shift = shift_raw if isinstance(shift_raw, dict) else {}
    start_raw = fact_value(FactKey.TIMELINE_START_FLEXIBILITY, {})
    start = start_raw if isinstance(start_raw, dict) else {}
    collective = _as_compact_list(
        fact_value(FactKey.BENEFITS_COLLECTIVE_AGREEMENT_CONTEXT, [])
    )
    offer_components = _as_compact_list(
        fact_value(FactKey.BENEFITS_OFFER_COMPONENTS, [])
    )
    work_auth = compact_text(fact_value(FactKey.LEGAL_WORK_AUTHORIZATION_SUPPORT, ""))

    candidate_value = list(selected_benefits[:4])
    if salary_text:
        candidate_value.append(f"Vergütung: {salary_text}")
    if remote_text:
        candidate_value.append(f"Arbeitsmodell: {remote_text}")
    if offer_components:
        candidate_value.append(
            f"Zusätzliche Bausteine: {', '.join(offer_components[:3])}"
        )

    fixed_terms: list[str] = []
    negotiable_or_early: list[str] = []
    if salary_text:
        fixed_terms.append(f"Gehaltsrahmen: {salary_text}")
    else:
        negotiable_or_early.append("Gehaltsrahmen früh klären")
    if remote_text:
        fixed_terms.append(f"Arbeitsmodell: {remote_text}")
    else:
        negotiable_or_early.append("Remote-/Hybrid-Regelung früh klären")
    if collective and "Keine bekannt" not in collective:
        fixed_terms.append(f"Rahmenvorgaben: {', '.join(collective[:3])}")

    eligible = variable_pay.get("eligible")
    if eligible is True:
        ote_parts = [
            compact_text(variable_pay.get("ote_min")),
            compact_text(variable_pay.get("ote_max")),
            compact_text(variable_pay.get("currency")),
        ]
        ote_text = " ".join(part for part in ote_parts if part)
        fixed_terms.append(
            f"Variable Vergütung vorgesehen{': ' + ote_text if ote_text else ''}"
        )
    elif eligible is None:
        negotiable_or_early.append("Variable Vergütung bestätigen oder ausschließen")

    start_flexibility = compact_text(start.get("flexibility"))
    target_start = compact_text(start.get("target_start"))
    if start_flexibility == "fixed" and target_start:
        fixed_terms.append(f"Starttermin: {target_start}")
    elif start_flexibility and start_flexibility != "unknown":
        flexibility_label = _START_FLEXIBILITY_LABELS.get(
            start_flexibility,
            start_flexibility,
        )
        negotiable_or_early.append(
            f"Startflexibilität: {flexibility_label}"
        )
    else:
        negotiable_or_early.append("Starttermin und Flexibilität früh klären")

    shift_compensation = compact_text(shift.get("compensation"))
    if shift_compensation:
        fixed_terms.append(f"Ausgleich/Zuschläge: {shift_compensation}")
    if offer_components:
        negotiable_or_early.append(
            f"Verhandelbare Angebotsbausteine: {', '.join(offer_components[:4])}"
        )
    if work_auth in {"unknown", ""}:
        negotiable_or_early.append("Visa-/Arbeitserlaubnis-Support früh klären")
    elif work_auth == "yes":
        fixed_terms.append("Arbeitserlaubnis-Support möglich")
    elif work_auth == "no":
        fixed_terms.append("Kein Arbeitserlaubnis-Support vorgesehen")

    early_candidate_info = [
        item
        for item in negotiable_or_early
        if "früh klären" in item or "bestätigen" in item
    ]
    if not early_candidate_info and negotiable_or_early:
        early_candidate_info = negotiable_or_early[:3]
    if not early_candidate_info and fixed_terms:
        early_candidate_info = fixed_terms[:3]

    return candidate_value, fixed_terms, negotiable_or_early + early_candidate_info


def _render_offer_outcome_preview(
    *,
    job: JobAdExtract,
    selected_benefits: list[str],
) -> None:
    offer_decision = build_offer_decision_context(
        job=job,
        selected_benefits=selected_benefits,
        intake_facts=get_intake_fact_state(st.session_state),
        intake_fact_evidence=get_intake_fact_evidence_state(st.session_state),
        salary_forecast=st.session_state.get(SSKey.SALARY_FORECAST_LAST_RESULT.value, {}),
        salary_fingerprints=st.session_state.get(
            SSKey.SALARY_FORECAST_INPUT_FINGERPRINT.value,
            {},
        ),
    )
    candidate_value = list(offer_decision.get("candidate_value", []))
    fixed_terms = list(offer_decision.get("fixed_terms", []))
    negotiable_terms = list(offer_decision.get("negotiable_terms", []))
    early_info = list(offer_decision.get("early_candidate_info", []))
    salary_caveat = compact_text(offer_decision.get("salary_caveat"))
    st.markdown("#### Angebotswirkung")
    st.caption(
        "Macht sichtbar, warum die Rolle attraktiv ist, was fix ist und welche "
        "Informationen Kandidat:innen früh brauchen."
    )
    col_value, col_fixed = responsive_two_columns(gap="large")
    with col_value:
        _render_outcome_list(
            title="Candidate Value",
            items=candidate_value,
            empty="Noch kein klares Nutzenargument ausgewählt.",
        )
    with col_fixed:
        _render_outcome_list(
            title="Fixe Zusagen",
            items=fixed_terms,
            empty="Noch keine verbindlichen Angebotsbestandteile markiert.",
        )
    col_negotiable, col_early = responsive_two_columns(gap="large")
    with col_negotiable:
        _render_outcome_list(
            title="Verhandelbar",
            items=negotiable_terms,
            empty="Keine verhandelbaren Angebotsbestandteile erkannt.",
        )
    with col_early:
        _render_outcome_list(
            title="Früh kommunizieren",
            items=early_info,
            empty="Keine Verhandlungs- oder frühen Klärpunkte erkannt.",
        )
    with section_container(border=True):
        st.markdown("**Salary Caveat**")
        st.caption(
            salary_caveat
            or "Gehaltsprognose ist Orientierung und ersetzt keine Vergütungsprüfung."
        )
    st.caption(
        "Exportwirkung: Diese Auswahl steuert Stellenanzeige, Recruiting Brief, "
        "HR-/Fachbereich-Sheets, Search-Kriterien und die Benefit-Gewichtung der "
        "Gehaltsprognose."
    )


def _render_structured_offer_constraints(job: JobAdExtract) -> None:
    def _render_fields() -> None:
        st.caption(
            "Nur ausfüllen, wenn diese Punkte die Zusage, Verhandlung oder frühe "
            "Candidate-Kommunikation beeinflussen."
        )
        st.markdown("#### Variable Vergütung")
        _render_variable_pay_block()
        st.markdown("#### Arbeitszeit und Ausgleich")
        _render_shift_compensation_block()
        st.markdown("#### Vertrag und Start")
        render_multiselect_fact(
            FactKey.BENEFITS_COLLECTIVE_AGREEMENT_CONTEXT,
            "Tarif, Betriebsrat oder Vorgaben",
            options=[
                "Tarifbindung",
                "Betriebsrat",
                "TVöD/TV-L",
                "Branchentarif",
                "Betriebsvereinbarung",
                "Keine bekannt",
                "Sonstiges",
            ],
        )
        render_select_fact(
            FactKey.LEGAL_WORK_AUTHORIZATION_SUPPORT,
            "Visa-Support möglich?",
            options=("unknown", "yes", "no"),
            default="unknown",
            labels=_YES_NO_UNKNOWN_LABELS,
        )
        render_multiselect_fact(
            FactKey.BENEFITS_OFFER_COMPONENTS,
            "Weitere Angebotsbausteine",
            options=[
                "Equipment",
                "Homeoffice-Kosten",
                "Relocation",
                "Firmenwagen",
                "Jobticket",
                "Weiterbildungsbudget",
                "Sign-on Bonus",
                "Sonstiges",
            ],
        )
        _render_start_flexibility_block(job)

    expander = getattr(st, "expander", None)
    if callable(expander):
        with expander("Weitere Rahmenbedingungen", expanded=False):
            _render_fields()
        return
    st.markdown("#### Weitere Rahmenbedingungen")
    _render_fields()


def _can_render_structured_offer_inputs() -> bool:
    return all(
        callable(getattr(st, name, None))
        for name in ("multiselect", "number_input", "selectbox", "text_area", "text_input")
    )


def render(ctx: WizardContext) -> None:
    render_error_banner()

    preflight = guard_job_and_plan(ctx)
    if preflight is None:
        return

    job, plan = preflight

    step = next((s for s in plan.steps if s.step_key == "benefits"), None)
    _migrate_legacy_benefit_state()
    _sync_selected_benefit_intake_facts()
    jobspec_benefit_terms = _dedupe_benefit_terms(
        [value.strip() for value in job.benefits if has_meaningful_value(value)]
    )
    jobspec_suggestions = _suggestion_dicts_from_labels(
        jobspec_benefit_terms, source="Jobspec"
    )
    st.session_state[SSKey.BENEFITS_JOBSPEC_SUGGESTED.value] = jobspec_suggestions
    source_counts: dict[str, int] = {"Jobspec": 0, "ESCO / Kontext": 0, "AI": 0}

    def _render_extracted_slot() -> None:
        salary_text = _format_salary_range(job)
        salary_note = ""
        if job.salary_range and has_meaningful_value(job.salary_range.notes):
            salary_note = f"Notiz: {job.salary_range.notes}"

        col_salary, col_work_model, col_benefits = responsive_three_columns(gap="large")
        with col_salary:
            _render_compact_value_block(
                title="Gehalt",
                value=salary_text,
                note=salary_note,
            )
        with col_work_model:
            _render_compact_value_block(
                title="Arbeitsmodell",
                value=str(job.remote_policy or "").strip(),
            )
        with col_benefits:
            st.markdown(f"**Benefits ({len(jobspec_benefit_terms)})**")
            _render_label_list(
                jobspec_benefit_terms,
                limit=6,
                empty="Noch nicht erkannt.",
            )

    def _render_source_comparison_slot() -> None:
        nonlocal source_counts
        review_payload = build_step_review_payload(step)
        visible_questions = review_payload["visible_questions"]
        answers = review_payload["answers"]
        answered_lookup = review_payload["answered_lookup"]

        def _confirmed_values_for_keywords(keywords: tuple[str, ...]) -> list[str]:
            values: list[str] = []
            for question in visible_questions:
                question_label = question.label.strip().casefold()
                if not question_label or not answered_lookup.get(question.id, False):
                    continue
                if not any(keyword in question_label for keyword in keywords):
                    continue
                formatted = _normalize_answer_value(answers.get(question.id))
                if formatted:
                    values.append(f"{question.label}: {formatted}")
            return values

        contextual_suggested = [
            {"label": value, "source": "Kontext"}
            for value in _dedupe_benefit_terms(
                [
                    *_confirmed_values_for_keywords(
                        ("benefit", "perk", "zusatz", "budget")
                    ),
                ]
            )
        ]
        selected_labels = _read_selected_benefits()

        st.markdown("### Candidate-Angebot schärfen")
        st.caption(
            "Wähle Nutzenargumente und Rahmenbedingungen, die später in Anzeige, "
            "Briefing, Vertrag und Prognose verwendet werden."
        )

        semantic_context = get_esco_semantic_context()
        selected_occupation = semantic_context.primary_anchor
        if (
            semantic_context.can_use_semantic_exports
            and selected_occupation is not None
            and selected_occupation.title
        ):
            st.caption(f"Rollenbezug: {selected_occupation.title}")

        def _existing_benefits_for_generation() -> list[str]:
            return _dedupe_benefit_terms(
                [
                    *jobspec_benefit_terms,
                    *_benefit_labels_from_suggestions(contextual_suggested),
                    *_benefit_labels_from_suggestions(
                        st.session_state.get(SSKey.BENEFITS_LLM_SUGGESTED.value, [])
                    ),
                    *_read_selected_benefits(),
                ]
            )

        if not bool(
            st.session_state.get(SSKey.BENEFITS_AI_INITIAL_GENERATED.value, False)
        ):
            st.session_state[SSKey.BENEFITS_AI_INITIAL_GENERATED.value] = True
            existing_benefits = _dedupe_benefit_terms(
                [
                    *jobspec_benefit_terms,
                    *_benefit_labels_from_suggestions(contextual_suggested),
                    *selected_labels,
                ]
            )
            with st.spinner("Erstelle Vorschläge …"):
                _generate_ai_benefit_suggestions(
                    job=job,
                    existing_benefits=existing_benefits,
                    target_benefit_count=int(
                        st.session_state.get(SSKey.BENEFITS_SUGGEST_COUNT.value, 5)
                    ),
                    region_context=str(
                        st.session_state.get(SSKey.BENEFITS_REGION_CONTEXT.value, "")
                    ),
                )

        ai_suggested_raw = st.session_state.get(SSKey.BENEFITS_LLM_SUGGESTED.value, [])
        ai_labels = _benefit_labels_from_suggestions(ai_suggested_raw)

        def _render_ai_controls() -> None:
            st.divider()
            st.caption("Vorschläge anpassen")
            st.text_input(
                "Region",
                key=SSKey.BENEFITS_REGION_CONTEXT.value,
                placeholder="z. B. Berlin, NRW, DACH",
            )
            count_col, action_col = st.columns([1, 2], gap="small")
            with count_col:
                st.number_input(
                    "Anzahl",
                    min_value=1,
                    max_value=8,
                    step=1,
                    key=SSKey.BENEFITS_SUGGEST_COUNT.value,
                )
            with action_col:
                st.caption(" ")
                generate_clicked = st.button(
                    "Weitere Vorschläge",
                    key=SSKey.BENEFITS_AI_GENERATE_CLICKED.value,
                    width="stretch",
                )
            if not generate_clicked:
                return
            with st.spinner("Erstelle Vorschläge …"):
                merged_llm = _generate_ai_benefit_suggestions(
                    job=job,
                    existing_benefits=_existing_benefits_for_generation(),
                    target_benefit_count=int(
                        st.session_state.get(SSKey.BENEFITS_SUGGEST_COUNT.value, 5)
                    ),
                    region_context=str(
                        st.session_state.get(SSKey.BENEFITS_REGION_CONTEXT.value, "")
                    ),
                )
            if merged_llm is None:
                return
            if hasattr(st, "rerun"):
                st.rerun()
            if merged_llm:
                st.success(f"Neue Vorschläge hinzugefügt: {len(merged_llm)}")
            else:
                st.info("Keine neuen Vorschläge gefunden.")

        selection_result = render_source_pill_selection(
            columns=[
                {
                    "title": "Anzeige",
                    "source_key": "Jobspec",
                    "options": jobspec_benefit_terms,
                    "state_key": SSKey.BENEFITS_JOBSPEC_PILLS.value,
                    "show_provenance": False,
                    "empty_caption": "Keine Benefits aus der Anzeige erkannt. Erfasse Angebotsbestandteile unten manuell.",
                },
                {
                    "title": "Antworten",
                    "source_key": "ESCO / Kontext",
                    "options": _benefit_labels_from_suggestions(contextual_suggested),
                    "state_key": SSKey.BENEFITS_CONTEXT_PILLS.value,
                    "show_provenance": False,
                    "empty_caption": "Noch keine passenden Antworten. Kläre Benefits in den offenen Fragen oder unten manuell.",
                },
                {
                    "title": "Vorschläge",
                    "source_key": "AI",
                    "options": ai_labels,
                    "state_key": SSKey.BENEFITS_AI_PILLS.value,
                    "footer": _render_ai_controls,
                    "show_provenance": False,
                    "empty_caption": "Noch keine AI-Vorschläge. Nutze Weitere Vorschläge oder erfasse Benefits manuell.",
                },
            ],
            selected_labels=selected_labels,
            selected_state_key=SSKey.BENEFITS_SELECTED.value,
            key_prefix="benefits.sources",
        )
        source_counts = selection_result["source_counts"]
        _sync_selected_benefit_intake_facts()
        st.session_state[SSKey.BENEFITS_SELECTED_BULK_BUFFER.value] = (
            selection_result["selected_labels"]
        )
        st.markdown("#### Sichtbare Benefits")
        _render_label_list(selection_result["selected_labels"], limit=10)

        if _can_render_structured_offer_inputs():
            _render_structured_offer_constraints(job)
        _render_offer_outcome_preview(
            job=job,
            selected_benefits=selection_result["selected_labels"],
        )
        render_live_artifact_preview_panel(
            key="benefits",
            default_open=default_focus_drilldown_open(classic_default_open=True),
            streamlit_module=st,
            preview_builder=lambda: build_live_artifact_preview_payload(
                job=job,
                answers=get_answers(),
                selected_role_tasks=_read_selected_texts(SSKey.ROLE_TASKS_SELECTED),
                selected_skills=_read_selected_texts(SSKey.SKILLS_SELECTED),
                selected_benefits=selection_result["selected_labels"],
                offer_positioning=build_offer_decision_context(
                    job=job,
                    selected_benefits=selection_result["selected_labels"],
                    intake_facts=get_intake_fact_state(st.session_state),
                    intake_fact_evidence=get_intake_fact_evidence_state(
                        st.session_state
                    ),
                    salary_forecast=st.session_state.get(
                        SSKey.SALARY_FORECAST_LAST_RESULT.value,
                        {},
                    ),
                    salary_fingerprints=st.session_state.get(
                        SSKey.SALARY_FORECAST_INPUT_FINGERPRINT.value,
                        {},
                    ),
                ),
            ),
        )

    def _render_salary_forecast_slot() -> None:
        selected_benefits_for_forecast = _dedupe_benefit_terms(
            [
                str(item)
                for item in st.session_state.get(SSKey.BENEFITS_SELECTED.value, [])
                if has_meaningful_value(item)
            ]
            if isinstance(st.session_state.get(SSKey.BENEFITS_SELECTED.value, []), list)
            else []
        )
        benefits_for_forecast = selected_benefits_for_forecast or jobspec_benefit_terms
        if not benefits_for_forecast:
            st.caption(
                "Noch keine Benefits ausgewählt. Die Prognose läuft ohne Benefit-Einfluss."
            )
        answers = get_answers()
        settings = load_openai_settings()
        resolved_model = resolve_model_for_task(
            task_kind=TASK_GENERATE_ROLE_TASKS_SALARY_FORECAST,
            session_override=None,
            settings=settings,
        )
        try:
            render_benefits_salary_forecast_panel(
                job=job.model_copy(update={"benefits": benefits_for_forecast}),
                benefit_candidates=benefits_for_forecast,
                answers=answers,
                model=resolved_model,
                language="de",
                store=bool(st.session_state.get(SSKey.STORE_API_OUTPUT.value, False)),
                source_counts=source_counts,
            )
        except AttributeError as exc:
            LOGGER.warning(
                "Salary forecast rendering unavailable: expected SalaryForecastResult with quality field (%s).",
                exc,
            )
            st.warning(
                "Die Gehaltsprognose ist vorübergehend nicht verfügbar. Fülle Benefits weiter aus; du kannst ohne Prognose fortfahren."
            )

    def _render_open_questions_slot() -> None:
        st.markdown("#### Offene Klärungen")
        st.caption(
            "Klärt, was für Angebot, Verhandlung und frühe "
            "Candidate-Kommunikation noch fehlt."
        )
        if step is None or not step.questions:
            st.info(
                "Für diesen Abschnitt wurden keine spezifischen Fragen erzeugt. Du kannst trotzdem weitergehen."
            )
            return
        render_question_step(step)

    def _render_review_slot() -> None:
        st.markdown("#### Prüfung")
        st.caption(
            "Prüft, ob Attraktivität, fixe Zusagen und offene "
            "Verhandlungspunkte zusammenpassen."
        )
        render_standard_step_review(
            step,
            render_mode=resolve_standard_review_mode(context=ReviewRenderContext.STEP_FORM),
        )
        _render_benefits_consistency_checklist(job=job, step=step)

    section_kwargs = build_step_shell_section_kwargs(
        step_key=STEP_KEY_BENEFITS,
        renderers={
            STEP_SECTION_EXTRACTED_FROM_JOBSPEC: _render_extracted_slot,
            STEP_SECTION_SOURCE_COMPARISON: _render_source_comparison_slot,
            STEP_SECTION_SALARY_FORECAST: _render_salary_forecast_slot,
            STEP_SECTION_OPEN_QUESTIONS: _render_open_questions_slot,
            STEP_SECTION_REVIEW: _render_review_slot,
        },
    )

    step_copy = resolve_dynamic_step_copy(STEP_KEY_BENEFITS, job=job)
    lazy_section_configs = {
        "source_comparison_slot": LazySectionConfig(
            label="Candidate-Angebot",
            caption=(
                "Öffnet Benefits, fixe Zusagen, Verhandlungspunkte und "
                "Exportwirkung."
            ),
            button_label="Angebot schärfen",
            default_open=default_primary_workspace_open(),
        ),
        "salary_forecast_slot": LazySectionConfig(
            label="Gehaltsprognose",
            caption="Lädt die Prognose erst auf Anforderung.",
            button_label="Gehaltsprognose laden",
            default_open=False,
        ),
    }
    if is_focus_design_enabled():
        lazy_section_configs.update(
            {
                "extracted_from_jobspec_slot": LazySectionConfig(
                    label="Aus Jobspec extrahiert",
                    caption=(
                        "Zeigt erkannte Gehalts-, Arbeitsmodell- und "
                        "Benefit-Signale."
                    ),
                    button_label="Jobspec-Snapshot öffnen",
                    default_open=default_focus_drilldown_open(
                        classic_default_open=True
                    ),
                ),
                "open_questions_slot": LazySectionConfig(
                    label="Offene Klärungen",
                    caption=(
                        "Klärt, was für Angebot, Verhandlung und frühe "
                        "Candidate-Kommunikation noch fehlt."
                    ),
                    button_label="Offene Klärungen öffnen",
                    default_open=default_focus_drilldown_open(
                        classic_default_open=True
                    ),
                ),
                "review_slot": LazySectionConfig(
                    label="Prüfung",
                    caption=(
                        "Prüft, ob Attraktivität, fixe Zusagen und offene "
                        "Verhandlungspunkte zusammenpassen."
                    ),
                    button_label="Prüfung öffnen",
                    default_open=default_focus_drilldown_open(
                        classic_default_open=True
                    ),
                ),
            }
        )
    render_step_shell(
        title=step_copy.headline,
        subtitle=step_copy.subheadline,
        outcome_text=step_copy.value_line,
        step=step,
        lazy_section_configs=lazy_section_configs,
        **section_kwargs,
        footer_slot=lambda: nav_buttons(ctx),
    )


PAGE = WizardPage(
    key="benefits",
    title_de="Benefits & Rahmenbedingungen",
    icon="🎁",
    render=render,
    requires_jobspec=True,
)
