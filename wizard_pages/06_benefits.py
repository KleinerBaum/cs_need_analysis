# wizard_pages/06_benefits.py
from __future__ import annotations
import logging
from typing import Any

import streamlit as st

from constants import FactKey, SSKey
from intake_facts import write_intake_fact_by_legacy_field
from llm_client import (
    TASK_GENERATE_BENEFIT_SUGGESTIONS,
    TASK_GENERATE_ROLE_TASKS_SALARY_FORECAST,
    generate_benefit_suggestions,
    resolve_model_for_task,
)
from schemas import JobAdExtract, QuestionStep
from settings_openai import load_openai_settings
from state import get_answers, get_esco_semantic_context
from ui_layout import (
    LazySectionConfig,
    default_lazy_source_section_open,
    render_step_shell,
    responsive_three_columns,
    responsive_two_columns,
)
from ui_components import (
    build_step_review_payload,
    has_answered_question_with_keywords,
    has_meaningful_value,
    render_compare_adopt_intro,
    render_error_banner,
    render_question_step,
    render_recruiting_consistency_checklist,
    render_source_pill_selection,
    ReviewRenderContext,
    resolve_standard_review_mode,
    render_standard_step_review,
)
from wizard_pages.base import WizardContext, WizardPage, guard_job_and_plan, nav_buttons
from wizard_pages.fact_inputs import (
    compact_text,
    fact_value,
    persist_compact_object,
    persist_fact,
    render_multiselect_fact,
    render_select_fact,
    section_container,
    render_text_area_fact,
    split_lines,
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
            "Vergütungsrahmen ist intern abgestimmt und kommunizierbar.",
            salary_extracted
            or has_answered_question_with_keywords(
                questions=visible_questions,
                answered_lookup=answered_lookup,
                keywords=("gehalt", "salary", "vergütung", "compensation"),
            ),
        ),
        (
            "Arbeitsmodell (Remote/Hybrid/Onsite) ist abgestimmt.",
            remote_extracted
            or has_answered_question_with_keywords(
                questions=visible_questions,
                answered_lookup=answered_lookup,
                keywords=("remote", "hybrid", "onsite", "homeoffice", "arbeitsmodell"),
            ),
        ),
        (
            "Benefits sind priorisiert und einheitlich benennbar.",
            benefits_extracted
            or has_answered_question_with_keywords(
                questions=visible_questions,
                answered_lookup=answered_lookup,
                keywords=("benefit", "perk", "zusatz", "budget"),
            ),
        ),
        (
            "Essenzielle Rückfragen für dieses Paket sind beantwortet.",
            step_status["essentials_total"] == 0
            or step_status["essentials_answered"] == step_status["essentials_total"],
        ),
    ]

    render_recruiting_consistency_checklist(
        title="Recruiting-Konsistenzcheck",
        checks=checks,
        caption="Kurzcheck: Ist das Offer-Paket intern abgestimmt und extern klar kommunizierbar?",
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
        st.warning("AI-Benefit-Vorschläge konnten nicht erzeugt werden.")
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
    eligible_current = compact_text(current.get("eligible"))
    if eligible_current not in _YES_NO_UNKNOWN_LABELS:
        eligible_current = "unknown"
    col_eligible, col_min, col_max = responsive_three_columns(gap="large")
    with col_eligible:
        eligible = st.selectbox(
            "Variable Vergütung möglich?",
            options=tuple(_YES_NO_UNKNOWN_LABELS),
            index=tuple(_YES_NO_UNKNOWN_LABELS).index(eligible_current),
            format_func=lambda value: _YES_NO_UNKNOWN_LABELS.get(value, value),
            key=f"fact_input.{FactKey.BENEFITS_VARIABLE_PAY.value}.eligible",
        )
    with col_min:
        ote_min = st.number_input(
            "OTE min",
            min_value=0.0,
            value=float(current.get("ote_min") or 0),
            step=1000.0,
            key=f"fact_input.{FactKey.BENEFITS_VARIABLE_PAY.value}.ote_min",
        )
    with col_max:
        ote_max = st.number_input(
            "OTE max",
            min_value=0.0,
            value=float(current.get("ote_max") or 0),
            step=1000.0,
            key=f"fact_input.{FactKey.BENEFITS_VARIABLE_PAY.value}.ote_max",
        )
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
            key=f"fact_input.{FactKey.BENEFITS_VARIABLE_PAY.value}.period",
        )
    bonus_logic = st.text_area(
        "Bonuslogik / Zielsystem",
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
            "Schicht-/Rufbereitschaftsrotation",
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
        "Nacht-/Wochenend-/Sonderregelungen",
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
            "Ziel-Starttermin",
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
            key=f"fact_input.{FactKey.TIMELINE_START_FLEXIBILITY.value}.flexibility",
        )
    notice_period = st.text_input(
        "Notice-Period-Fenster / Einschränkungen",
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


def _render_structured_offer_constraints(job: JobAdExtract) -> None:
    st.markdown("### Compensation & Constraints")
    st.caption(
        "Diese Angaben trennen Offer-Bestandteile von harten Beschäftigungs- und Vertragslogiken."
    )
    with section_container(border=True):
        st.markdown("#### Variable Vergütung")
        _render_variable_pay_block()
    with section_container(border=True):
        st.markdown("#### Arbeitszeit, Schicht und Ausgleich")
        _render_shift_compensation_block()
    with section_container(border=True):
        st.markdown("#### Vertrags- und Offer-Komponenten")
        render_multiselect_fact(
            FactKey.BENEFITS_COLLECTIVE_AGREEMENT_CONTEXT,
            "Tarifbindung, Betriebsrat oder branchenspezifische Vorgaben",
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
            "Ist Visa-/Work-Permit-Sponsoring möglich?",
            options=("unknown", "yes", "no"),
            default="unknown",
            labels=_YES_NO_UNKNOWN_LABELS,
        )
        render_multiselect_fact(
            FactKey.BENEFITS_OFFER_COMPONENTS,
            "Welche zusätzlichen Offer-Komponenten sind relevant?",
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
        shown = False
        col_salary, col_benefits, col_remote = responsive_three_columns(gap="large")
        with col_salary:
            if job.salary_range:
                min_salary = job.salary_range.min
                max_salary = job.salary_range.max
                if has_meaningful_value(min_salary) or has_meaningful_value(max_salary):
                    st.write(
                        f"**Salary:** {min_salary} – {max_salary} {job.salary_range.currency or ''} ({job.salary_range.period or ''})"
                    )
                    shown = True
                if has_meaningful_value(job.salary_range.notes):
                    st.write(f"**Notes:** {job.salary_range.notes}")
                    shown = True
        with col_benefits:
            if jobspec_benefit_terms:
                st.write("**Benefits (Auszug):**")
                for benefit in jobspec_benefit_terms[:12]:
                    st.write(f"- {benefit}")
                shown = True
        with col_remote:
            if has_meaningful_value(job.remote_policy):
                st.write("**Arbeitsmodell (Auszug):**")
                st.write(f"- {job.remote_policy}")
                shown = True
        if not shown:
            st.info(
                "Keine verlässlichen Werte erkannt. Details siehe Gaps/Assumptions."
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

        st.markdown("### Erkannte und ausgewählte Benefits")
        st.caption(
            "Gewählte Benefits werden in Folgeartefakten und in der Gehaltsprognose berücksichtigt."
        )

        semantic_context = get_esco_semantic_context()
        selected_occupation = semantic_context.primary_anchor
        if (
            semantic_context.can_use_semantic_exports
            and selected_occupation is not None
            and selected_occupation.title
        ):
            st.caption(
                "ESCO-Kontext: "
                f"{selected_occupation.title} hilft bei der Plausibilisierung, "
                "liefert aber keine kanonische Benefit-Taxonomie."
            )

        render_compare_adopt_intro(
            adopt_target="Benefits",
            canonical_target="SSKey.BENEFITS_SELECTED",
            source_labels=("Jobspec", "ESCO/Kontext", "AI"),
        )

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
            with st.spinner("Generiere Benefit-Vorschläge …"):
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
            st.caption("Einflussfaktoren")
            st.text_input(
                "Region für lokale Benefits",
                key=SSKey.BENEFITS_REGION_CONTEXT.value,
                placeholder="z. B. Berlin, NRW, DACH",
            )
            count_col, action_col = st.columns([1, 2], gap="small")
            with count_col:
                st.number_input(
                    "Wie viele Benefit-Vorschläge möchtest du sehen?",
                    min_value=1,
                    max_value=8,
                    step=1,
                    key=SSKey.BENEFITS_SUGGEST_COUNT.value,
                )
            with action_col:
                st.caption(" ")
                generate_clicked = st.button(
                    "Benefit-Vorschläge generieren",
                    key=SSKey.BENEFITS_AI_GENERATE_CLICKED.value,
                    width="stretch",
                )
            if not generate_clicked:
                return
            with st.spinner("Generiere Benefit-Vorschläge …"):
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
                st.success(f"{len(merged_llm)} AI-Benefit(s) übernommen.")
            else:
                st.info("Keine zusätzlichen AI-Benefits gefunden.")

        selection_result = render_source_pill_selection(
            columns=[
                {
                    "title": "Aus der Anzeige extrahiert",
                    "source_key": "Jobspec",
                    "options": jobspec_benefit_terms,
                    "state_key": SSKey.BENEFITS_JOBSPEC_PILLS.value,
                },
                {
                    "title": "ESCO / Kontext",
                    "source_key": "ESCO / Kontext",
                    "options": _benefit_labels_from_suggestions(contextual_suggested),
                    "state_key": SSKey.BENEFITS_CONTEXT_PILLS.value,
                },
                {
                    "title": "AI-Vorschläge",
                    "source_key": "AI",
                    "options": ai_labels,
                    "state_key": SSKey.BENEFITS_AI_PILLS.value,
                    "footer": _render_ai_controls,
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
        st.caption(
            f"Ausgewählt: {len(selection_result['selected_labels'])} Benefit(s)"
        )
        if selection_result["selected_labels"]:
            st.markdown(
                " ".join(f"`{label}`" for label in selection_result["selected_labels"])
            )
        else:
            st.caption("Noch keine Benefits ausgewählt.")

        if _can_render_structured_offer_inputs():
            _render_structured_offer_constraints(job)

        confirmed_salary = _confirmed_values_for_keywords(
            ("gehalt", "salary", "vergütung", "compensation")
        )
        confirmed_benefits = _confirmed_values_for_keywords(
            ("benefit", "perk", "zusatz", "budget")
        )
        confirmed_remote = _confirmed_values_for_keywords(
            ("remote", "hybrid", "onsite", "homeoffice", "arbeitsmodell")
        )

        st.markdown("#### Details zu Einflussfaktoren")
        salary_col, benefits_col, remote_col = st.columns(3, gap="large")
        for column, title, confirmed in (
            (salary_col, "Vergütung", confirmed_salary),
            (benefits_col, "Benefits", confirmed_benefits),
            (remote_col, "Arbeitsmodell", confirmed_remote),
        ):
            with column:
                st.markdown(f"**{title}**")
                st.caption("Bereits bestätigt")
                if confirmed:
                    for item in confirmed[:8]:
                        st.write(f"- {item}")
                else:
                    st.caption("—")

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
                "Keine Benefits aus der Anzeige erkannt – Prognose wird ohne Benefit-Filter berechnet."
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
                "Die Gehaltsprognose ist vorübergehend nicht verfügbar. Bitte versuche es in Kürze erneut."
            )

    def _render_open_questions_slot() -> None:
        if step is None or not step.questions:
            st.info(
                "Für diesen Abschnitt wurden keine spezifischen Fragen erzeugt. Du kannst trotzdem weitergehen."
            )
            return
        render_question_step(step)

    def _render_review_slot() -> None:
        render_standard_step_review(
            step,
            render_mode=resolve_standard_review_mode(context=ReviewRenderContext.STEP_FORM),
        )
        _render_benefits_consistency_checklist(job=job, step=step)

    render_step_shell(
        title="Angebot und Rahmenbedingungen schärfen",
        subtitle=(
            "Hier definierst du, wie attraktiv und zugleich realistisch das Gesamtpaket "
            "kommuniziert werden kann: Gehalt, Arbeitsmodell, Benefits und alle Faktoren, "
            "die intern sauber abgestimmt sein müssen."
        ),
        outcome_text=(
            "Ein konsistentes Offer-Narrativ zu Compensation, Arbeitsmodell und Benefits, "
            "das intern und extern einheitlich kommuniziert werden kann."
        ),
        step=step,
        source_comparison_slot=_render_source_comparison_slot,
        salary_forecast_slot=_render_salary_forecast_slot,
        open_questions_slot=_render_open_questions_slot,
        lazy_section_configs={
            "source_comparison_slot": LazySectionConfig(
                label="Quellenabgleich",
                caption=(
                    "Lädt Jobspec-, Kontext- und AI-Benefit-Vorschläge erst, "
                    "wenn du diesen Abgleich öffnest."
                ),
                button_label="Quellenabgleich anzeigen",
                default_open=default_lazy_source_section_open(),
            ),
            "salary_forecast_slot": LazySectionConfig(
                label="Gehaltsprognose",
                caption=(
                    "Berechnet die Auswirkung der ausgewählten Benefits erst auf "
                    "Anforderung."
                ),
                button_label="Gehaltsprognose laden",
                default_open=False,
            ),
        },
        review_slot=_render_review_slot,
        footer_slot=lambda: nav_buttons(ctx),
    )


PAGE = WizardPage(
    key="benefits",
    title_de="Benefits & Rahmenbedingungen",
    icon="🎁",
    render=render,
    requires_jobspec=True,
)
