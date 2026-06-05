# wizard_pages/06_benefits.py
from __future__ import annotations
import logging
import streamlit as st

from constants import SSKey
from llm_client import (
    TASK_GENERATE_BENEFIT_SUGGESTIONS,
    TASK_GENERATE_ROLE_TASKS_SALARY_FORECAST,
    generate_benefit_suggestions,
    resolve_model_for_task,
)
from schemas import JobAdExtract, QuestionStep
from settings_openai import load_openai_settings
from state import get_answers, get_esco_semantic_context
from ui_layout import render_step_shell, responsive_three_columns
from ui_components import (
    build_step_review_payload,
    has_answered_question_with_keywords,
    has_meaningful_value,
    render_compare_adopt_intro,
    render_compact_requirement_board,
    render_error_banner,
    render_question_step,
    render_recruiting_consistency_checklist,
    ReviewRenderContext,
    resolve_standard_review_mode,
    render_standard_step_review,
)
from wizard_pages.base import WizardContext, WizardPage, guard_job_and_plan, nav_buttons
from wizard_pages.salary_forecast_panel import render_benefits_salary_forecast_panel

LOGGER = logging.getLogger(__name__)

_LEGACY_BENEFITS_SELECTED_COMPARE_KEY = "benefits.compare.selected"
_LEGACY_BENEFITS_AI_SUGGESTED_KEY = "benefits.ai_suggested"


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


def _suggestion_dicts_from_labels(labels: list[str], *, source: str) -> list[dict[str, str]]:
    return [{"label": label, "source": source} for label in labels if label.strip()]


def render(ctx: WizardContext) -> None:
    render_error_banner()

    preflight = guard_job_and_plan(ctx)
    if preflight is None:
        return

    job, plan = preflight

    step = next((s for s in plan.steps if s.step_key == "benefits"), None)
    _migrate_legacy_benefit_state()
    jobspec_benefit_terms = _dedupe_benefit_terms(
        [value.strip() for value in job.benefits if has_meaningful_value(value)]
    )
    jobspec_suggestions = _suggestion_dicts_from_labels(
        jobspec_benefit_terms, source="Jobspec"
    )
    st.session_state[SSKey.BENEFITS_JOBSPEC_SUGGESTED.value] = jobspec_suggestions

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
        ai_suggested_raw = st.session_state.get(SSKey.BENEFITS_LLM_SUGGESTED.value, [])
        ai_suggested = (
            [
                {
                    "label": str(item.get("label") or "").strip(),
                    "source": "AI",
                    "source_hint": str(item.get("source_hint") or "llm").strip(),
                    "rationale": str(item.get("rationale") or "").strip(),
                    "evidence": str(item.get("evidence") or "").strip(),
                    "importance": str(item.get("importance") or "").strip(),
                }
                for item in ai_suggested_raw
                if isinstance(item, dict)
                and has_meaningful_value(str(item.get("label") or ""))
            ]
            if isinstance(ai_suggested_raw, list)
            else []
        )

        selected_labels = _read_selected_benefits()

        st.markdown("### Erkannte und ausgewählte Benefits")
        st.caption(
            "Gewählte Benefits werden in Folgeartefakten und in der Gehaltsprognose berücksichtigt."
        )
        st.caption(f"{len(selected_labels)} ausgewählt")
        if selected_labels:
            st.markdown(" ".join(f"`{label}`" for label in selected_labels))
        else:
            st.caption("Noch keine Benefits ausgewählt.")

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
            source_labels=("Jobspec", "Kontext", "AI"),
        )
        st.number_input(
            "Anzahl AI-Benefit-Vorschläge",
            min_value=1,
            max_value=8,
            step=1,
            key=SSKey.BENEFITS_SUGGEST_COUNT.value,
        )
        if st.button(
            "AI-Benefit-Vorschläge generieren",
            key=SSKey.BENEFITS_AI_GENERATE_CLICKED.value,
        ):
            existing_benefits = _dedupe_benefit_terms(
                [
                    *jobspec_benefit_terms,
                    *_benefit_labels_from_suggestions(contextual_suggested),
                    *selected_labels,
                ]
            )
            settings = load_openai_settings()
            suggestion_model = resolve_model_for_task(
                task_kind=TASK_GENERATE_BENEFIT_SUGGESTIONS,
                session_override=None,
                settings=settings,
            )
            with st.spinner("Generiere Benefit-Vorschläge …"):
                try:
                    suggestion_pack, _usage = generate_benefit_suggestions(
                        job=job,
                        answers=get_answers(),
                        existing_benefits=existing_benefits,
                        target_benefit_count=int(
                            st.session_state.get(SSKey.BENEFITS_SUGGEST_COUNT.value, 5)
                        ),
                        model=suggestion_model,
                        language=str(
                            st.session_state.get(SSKey.LANGUAGE.value, "de")
                        ),
                        store=bool(
                            st.session_state.get(SSKey.STORE_API_OUTPUT.value, False)
                        ),
                    )
                except Exception:
                    LOGGER.exception("Benefit suggestions could not be generated.")
                    st.warning("AI-Benefit-Vorschläge konnten nicht erzeugt werden.")
                else:
                    blocked = {
                        _normalize_benefit_term(label) for label in existing_benefits
                    }
                    merged_llm: list[dict[str, str]] = []
                    seen: set[str] = set(blocked)
                    for item in suggestion_pack.benefits:
                        label = item.label.strip()
                        normalized = _normalize_benefit_term(label)
                        if not normalized or normalized in seen:
                            continue
                        merged_llm.append(item.model_dump(mode="json"))
                        seen.add(normalized)
                    st.session_state[SSKey.BENEFITS_LLM_SUGGESTED.value] = merged_llm
                    if merged_llm:
                        st.success(f"{len(merged_llm)} AI-Benefit(s) übernommen.")
                    else:
                        st.info("Keine zusätzlichen AI-Benefits gefunden.")

        ai_suggested_raw = st.session_state.get(SSKey.BENEFITS_LLM_SUGGESTED.value, [])
        ai_suggested = (
            [
                {
                    "label": str(item.get("label") or "").strip(),
                    "source": "AI",
                    "source_hint": str(item.get("source_hint") or "llm").strip(),
                    "rationale": str(item.get("rationale") or "").strip(),
                    "evidence": str(item.get("evidence") or "").strip(),
                    "importance": str(item.get("importance") or "").strip(),
                }
                for item in ai_suggested_raw
                if isinstance(item, dict)
                and has_meaningful_value(str(item.get("label") or ""))
            ]
            if isinstance(ai_suggested_raw, list)
            else []
        )
        bulk_buffer = render_compact_requirement_board(
            title_jobspec="Aus Jobspec extrahiert",
            jobspec_items=jobspec_suggestions,
            title_esco="Bereits bestätigt / Kontext",
            esco_items=contextual_suggested,
            title_llm="AI-Vorschläge",
            llm_items=ai_suggested,
            selected_labels=selected_labels,
            selection_state_key=SSKey.BENEFITS_SELECTED_BULK_BUFFER.value,
            key_prefix="benefits.board",
        )
        if st.button("Ausgewählte Benefits übernehmen", width="stretch"):
            merged = _dedupe_benefit_terms([*selected_labels, *bulk_buffer])
            st.session_state[SSKey.BENEFITS_SELECTED.value] = merged
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
