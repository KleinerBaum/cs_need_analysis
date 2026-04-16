# wizard_pages/06_benefits.py
from __future__ import annotations
import streamlit as st

from constants import SSKey
from llm_client import TASK_GENERATE_ROLE_TASKS_SALARY_FORECAST, resolve_model_for_task
from schemas import JobAdExtract, QuestionStep
from settings_openai import load_openai_settings
from state import get_answers
from ui_layout import render_step_shell
from ui_components import (
    build_step_review_payload,
    has_answered_question_with_keywords,
    has_meaningful_value,
    render_compare_adopt_intro,
    render_compact_requirement_board,
    render_error_banner,
    render_question_step,
    render_recruiting_consistency_checklist,
    render_standard_step_review,
)
from wizard_pages.base import WizardContext, WizardPage, guard_job_and_plan, nav_buttons
from wizard_pages.salary_forecast_panel import render_benefits_salary_forecast_panel

_BENEFITS_SELECTED_COMPARE_KEY = "benefits.compare.selected"
_BENEFITS_AI_SUGGESTED_KEY = "benefits.ai_suggested"


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


def render(ctx: WizardContext) -> None:
    render_error_banner()

    preflight = guard_job_and_plan(ctx)
    if preflight is None:
        return

    job, plan = preflight

    step = next((s for s in plan.steps if s.step_key == "benefits"), None)

    def _render_extracted_slot() -> None:
        shown = False
        col_salary, col_benefits, col_remote = st.columns(3, gap="large")
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
            benefits = [b for b in job.benefits if has_meaningful_value(b)]
            if benefits:
                st.write("**Benefits (Auszug):**")
                for b in benefits[:12]:
                    st.write(f"- {b}")
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

    selected_benefits_for_forecast = _dedupe_benefit_terms(
        [
            str(item)
            for item in st.session_state.get(_BENEFITS_SELECTED_COMPARE_KEY, [])
            if has_meaningful_value(item)
        ]
        if isinstance(st.session_state.get(_BENEFITS_SELECTED_COMPARE_KEY, []), list)
        else []
    )

    def _render_source_comparison_slot() -> None:
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

        jobspec_suggested = [
            {"label": value, "source": "Jobspec"}
            for value in _dedupe_benefit_terms(
                [value.strip() for value in job.benefits if has_meaningful_value(value)]
            )
        ]

        contextual_suggested = [
            {"label": value, "source": "Kontext"}
            for value in _dedupe_benefit_terms(
                [
                    *_confirmed_values_for_keywords(
                        ("benefit", "perk", "zusatz", "budget")
                    ),
                    *_confirmed_values_for_keywords(
                        ("remote", "hybrid", "onsite", "homeoffice", "arbeitsmodell")
                    ),
                ]
            )
        ]
        ai_suggested_raw = st.session_state.get(_BENEFITS_AI_SUGGESTED_KEY, [])
        ai_suggested = (
            [
                {"label": str(item.get("label") or "").strip(), "source": "AI"}
                for item in ai_suggested_raw
                if isinstance(item, dict)
                and has_meaningful_value(str(item.get("label") or ""))
            ]
            if isinstance(ai_suggested_raw, list)
            else []
        )
        selected_raw = st.session_state.get(_BENEFITS_SELECTED_COMPARE_KEY, [])
        selected_labels = (
            [str(item).strip() for item in selected_raw if has_meaningful_value(item)]
            if isinstance(selected_raw, list)
            else []
        )

        render_compare_adopt_intro(
            adopt_target="Benefits",
            canonical_target=_BENEFITS_SELECTED_COMPARE_KEY,
            source_labels=("Jobspec", "Kontext", "AI")
            if ai_suggested
            else ("Jobspec", "Kontext"),
        )
        bulk_buffer = render_compact_requirement_board(
            title_jobspec="Aus Jobspec extrahiert",
            jobspec_items=jobspec_suggested,
            title_esco="Bereits bestätigt / Kontext",
            esco_items=contextual_suggested,
            title_llm="AI-Vorschläge",
            llm_items=ai_suggested,
            selected_labels=selected_labels,
            selection_state_key=f"{_BENEFITS_SELECTED_COMPARE_KEY}.bulk_buffer",
            key_prefix="benefits.board",
        )
        if st.button("Ausgewählte Benefits übernehmen", width="stretch"):
            merged = _dedupe_benefit_terms([*selected_labels, *bulk_buffer])
            st.session_state[_BENEFITS_SELECTED_COMPARE_KEY] = merged
            st.success(f"{len(merged)} Benefit(s) gespeichert.")

        confirmed_salary = _confirmed_values_for_keywords(
            ("gehalt", "salary", "vergütung", "compensation")
        )
        confirmed_benefits = _confirmed_values_for_keywords(
            ("benefit", "perk", "zusatz", "budget")
        )
        confirmed_remote = _confirmed_values_for_keywords(
            ("remote", "hybrid", "onsite", "homeoffice", "arbeitsmodell")
        )

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
        st.markdown("### Salary Forecast")
        benefits_for_forecast = selected_benefits_for_forecast or [
            value.strip() for value in job.benefits if has_meaningful_value(value)
        ]
        selected_benefits = benefits_for_forecast
        if benefits_for_forecast:
            st.caption(
                "Benefits für die Kalkulation auswählen. Nur ausgewählte Zeilen fließen in die Prognose ein."
            )
            source_rows = {
                "Einbeziehen": [True for _ in benefits_for_forecast],
                "Benefit": benefits_for_forecast,
            }
            edited_rows = st.data_editor(
                source_rows,
                hide_index=True,
                width="stretch",
                column_config={
                    "Einbeziehen": st.column_config.CheckboxColumn(
                        "Einbeziehen", help="Auswahl für Salary Forecast"
                    ),
                    "Benefit": st.column_config.TextColumn(
                        "Benefit", disabled=True, width="large"
                    ),
                },
                disabled=["Benefit"],
            )
            if isinstance(edited_rows, dict):
                selected_benefits = []
                include_values = edited_rows.get("Einbeziehen", [])
                benefit_values = edited_rows.get("Benefit", [])
                if isinstance(include_values, list) and isinstance(
                    benefit_values, list
                ):
                    for include, raw_value in zip(include_values, benefit_values):
                        value = str(raw_value or "").strip()
                        if include and has_meaningful_value(value):
                            selected_benefits.append(value)
            elif hasattr(edited_rows, "to_dict"):
                selected_benefits = []
                for row in edited_rows.to_dict("records"):
                    include = bool(row.get("Einbeziehen"))
                    value = str(row.get("Benefit") or "").strip()
                    if include and has_meaningful_value(value):
                        selected_benefits.append(value)
        else:
            st.caption(
                "Keine Benefits aus der Anzeige erkannt – Prognose wird ohne Benefit-Filter berechnet."
            )

        st.caption(f"Ausgewählte Benefits: {len(selected_benefits)}")
        answers = get_answers()
        settings = load_openai_settings()
        resolved_model = resolve_model_for_task(
            task_kind=TASK_GENERATE_ROLE_TASKS_SALARY_FORECAST,
            session_override=None,
            settings=settings,
        )
        render_benefits_salary_forecast_panel(
            job=job.model_copy(update={"benefits": selected_benefits}),
            selected_benefits=selected_benefits,
            answers=answers,
            model=resolved_model,
            language="de",
            store=bool(st.session_state.get(SSKey.STORE_API_OUTPUT.value, False)),
        )

    def _render_open_questions_slot() -> None:
        if step is None or not step.questions:
            st.info(
                "Für diesen Abschnitt wurden keine spezifischen Fragen erzeugt. Du kannst trotzdem weitergehen."
            )
            return
        render_question_step(step)

    def _render_review_slot() -> None:
        render_standard_step_review(step)
        _render_benefits_consistency_checklist(job=job, step=step)

    render_step_shell(
        title="Benefits & Rahmenbedingungen",
        subtitle=(
            "Hier geht es um das Gesamtpaket: Gehaltsband (falls möglich), "
            "Remote/Hybrid, Arbeitszeit, Benefits, Relocation, Learning Budget "
            "– inklusive der Dinge, die man im Recruiting unbedingt konsistent kommunizieren muss."
        ),
        outcome_text=(
            "Ein konsistentes Offer-Narrativ zu Compensation, Arbeitsmodell und Benefits, "
            "das intern und extern einheitlich kommuniziert werden kann."
        ),
        step=step,
        extracted_from_jobspec_slot=_render_extracted_slot,
        extracted_from_jobspec_label="Aus der Anzeige extrahierte Benefits & Rahmenbedingungen",
        extracted_from_jobspec_use_expander=False,
        source_comparison_slot=_render_source_comparison_slot,
        salary_forecast_slot=_render_salary_forecast_slot,
        open_questions_slot=_render_open_questions_slot,
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
