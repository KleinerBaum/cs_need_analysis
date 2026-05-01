# wizard_pages/04_role_tasks.py
from __future__ import annotations

import re
from typing import Any

import streamlit as st

from constants import SSKey
from esco_client import EscoClient, EscoClientError
from esco_rag import retrieve_esco_context
from llm_client import generate_requirement_gap_suggestions
from schemas import JobAdExtract
from components.design_system import render_output_header
from state import (
    get_active_model,
    get_answers,
    get_esco_occupation_selected,
    has_confirmed_esco_anchor,
    sync_esco_shared_state,
)
from ui_components import (
    has_meaningful_value,
    render_multi_select_pills,
    render_compare_adopt_intro,
    render_esco_explainability,
    render_error_banner,
    render_question_step,
    ReviewRenderContext,
    resolve_standard_review_mode,
    render_standard_step_review,
)
from ui_layout import render_step_shell, responsive_three_columns
from wizard_pages.base import WizardContext, WizardPage, guard_job_and_plan, nav_buttons
from wizard_pages.salary_forecast_panel import render_role_tasks_salary_forecast_panel


def _normalize_task_term(term: str) -> str:
    return " ".join(term.strip().casefold().split())


def _dedupe_task_terms(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not has_meaningful_value(value):
            continue
        label = str(value).strip()
        normalized = _normalize_task_term(label)
        if not normalized or normalized in seen:
            continue
        deduped.append(label)
        seen.add(normalized)
    return deduped


def _split_task_like_text(value: str) -> list[str]:
    compact = re.sub(r"\s+", " ", value or "").strip()
    if not compact:
        return []
    parts = re.split(r"[.;•\n]+", compact)
    return [part.strip(" -") for part in parts if has_meaningful_value(part)]


def _load_esco_task_suggestions_from_selected_occupation(
    occupation_uri: str,
) -> tuple[list[dict[str, str]], str | None]:
    client = EscoClient()
    try:
        payload = client.resource_occupation(uri=occupation_uri)
    except EscoClientError as exc:
        return [], str(exc)

    if not isinstance(payload, dict):
        return [], None

    title = str(
        payload.get("preferredLabel")
        or payload.get("title")
        or payload.get("label")
        or ""
    ).strip()

    description_like_parts: list[str] = []
    for key in ("description", "scopeNote", "definition"):
        raw = payload.get(key)
        if isinstance(raw, str):
            description_like_parts.append(raw)
        elif isinstance(raw, dict):
            for nested in raw.values():
                if isinstance(nested, str):
                    description_like_parts.append(nested)

    task_terms = _dedupe_task_terms(
        [
            part
            for text in description_like_parts
            for part in _split_task_like_text(text)
            if len(part.strip()) >= 12
        ]
    )

    suggestions = [
        {
            "label": label,
            "source": "ESCO",
            "rationale": "derived from occupation relation",
            "importance": "medium",
        }
        for label in task_terms[:8]
    ]

    if not suggestions and title:
        # Keep UI context transparent, but avoid fabricating unsupported task relations.
        return [], None

    return suggestions, None


def _build_task_suggestion_context(
    *, job: JobAdExtract, include_esco_titles: bool
) -> dict[str, list[str]]:
    coverage = sync_esco_shared_state()
    jobspec_terms = _dedupe_task_terms(
        [*job.responsibilities, *job.deliverables, *job.success_metrics]
    )
    esco_titles = (
        _dedupe_task_terms(
            [
                str(item.get("title") or "").strip()
                for item in coverage.confirmed_essential_skills
            ]
            + [
                str(item.get("title") or "").strip()
                for item in coverage.confirmed_optional_skills
            ]
        )
        if include_esco_titles
        else []
    )
    selected_raw = st.session_state.get(SSKey.ROLE_TASKS_SELECTED.value, [])
    selected_terms = (
        _dedupe_task_terms([str(item) for item in selected_raw])
        if isinstance(selected_raw, list)
        else []
    )
    return {
        "jobspec_terms": jobspec_terms,
        "esco_skill_titles": esco_titles,
        "selected_terms": selected_terms,
    }


def _merge_llm_task_suggestions(
    *,
    llm_tasks: list[dict[str, Any]],
    blocked_labels: list[str],
) -> list[dict[str, str]]:
    seen = {
        _normalize_task_term(label)
        for label in blocked_labels
        if has_meaningful_value(label)
    }
    merged: list[dict[str, str]] = []
    for item in llm_tasks:
        label = str(item.get("label") or "").strip()
        normalized = _normalize_task_term(label)
        if not normalized or normalized in seen:
            continue
        merged.append(
            {
                "label": label,
                "source": "AI",
                "source_hint": str(item.get("source_hint") or "llm").strip() or "llm",
                "source_file": str(item.get("source_file") or "").strip(),
                "concept_uri": str(item.get("concept_uri") or "").strip(),
                "importance": str(item.get("importance") or "").strip(),
                "rationale": str(item.get("rationale") or "").strip(),
                "evidence": str(item.get("evidence") or "").strip(),
            }
        )
        seen.add(normalized)
    return merged


def _build_task_rag_context(job: JobAdExtract) -> list[dict[str, str]]:
    job_title = getattr(job, "job_title", None)
    query_parts = _dedupe_task_terms(
        [part for part in [job_title, *job.responsibilities[:3], *job.deliverables[:3]] if has_meaningful_value(part)]
    )
    query = " | ".join(part for part in query_parts if has_meaningful_value(part))
    if not query:
        return []
    rag_result = retrieve_esco_context(query, purpose="tasks", max_results=4)
    if rag_result.reason is not None or not rag_result.hits:
        return []
    context: list[dict[str, str]] = []
    for hit in rag_result.hits[:4]:
        snippet = str(hit.snippet).strip()
        if not snippet:
            continue
        context.append(
            {
                "snippet": snippet[:320],
                "source_hint": "esco_rag",
                "source_title": str(hit.source_title or "").strip(),
                "source_file": str(hit.source_file or "").strip(),
                "concept_uri": str(getattr(hit, "uri", "") or "").strip(),
            }
        )
    return context


def _save_selected_task_suggestions(labels: list[str]) -> int:
    existing_raw = st.session_state.get(SSKey.ROLE_TASKS_SELECTED.value, [])
    existing = (
        [str(item).strip() for item in existing_raw if has_meaningful_value(str(item))]
        if isinstance(existing_raw, list)
        else []
    )
    merged = list(existing)
    seen = {_normalize_task_term(item) for item in existing}
    added = 0
    for label in labels:
        normalized = _normalize_task_term(label)
        if not normalized or normalized in seen:
            continue
        merged.append(label.strip())
        seen.add(normalized)
        added += 1
    st.session_state[SSKey.ROLE_TASKS_SELECTED.value] = merged
    return added


def _render_role_tasks_salary_block(
    *,
    job: JobAdExtract,
    selected_tasks: list[str],
) -> None:
    render_role_tasks_salary_forecast_panel(
        job=job,
        selected_tasks=selected_tasks,
        model=get_active_model(),
        language=str(st.session_state.get(SSKey.LANGUAGE.value, "de")),
        store=bool(st.session_state.get(SSKey.STORE_API_OUTPUT.value, False)),
    )


def render(ctx: WizardContext) -> None:
    preflight = guard_job_and_plan(ctx)
    if preflight is None:
        return
    job, plan = preflight
    step = next((s for s in plan.steps if s.step_key == "role_tasks"), None)

    responsibilities = [r for r in job.responsibilities if has_meaningful_value(r)]
    deliverables = [r for r in job.deliverables if has_meaningful_value(r)]
    success_metrics = [r for r in job.success_metrics if has_meaningful_value(r)]

    jobspec_terms = _dedupe_task_terms(
        [*responsibilities, *deliverables, *success_metrics]
    )
    jobspec_suggestions = [
        {"label": label, "source": "Jobspec"} for label in jobspec_terms
    ]
    st.session_state[SSKey.ROLE_TASKS_JOBSPEC_SUGGESTED.value] = jobspec_suggestions

    def _render_extracted_slot() -> None:
        col_resp, col_deliv, col_metrics = responsive_three_columns(gap="large")
        if responsibilities:
            with col_resp:
                st.write("**Responsibilities (Auszug):**")
                for r in responsibilities[:10]:
                    st.write(f"- {r}")
        if deliverables:
            with col_deliv:
                st.write("**Deliverables (Auszug):**")
                for d in deliverables[:10]:
                    st.write(f"- {d}")
        if success_metrics:
            with col_metrics:
                st.write("**Success Metrics (Auszug):**")
                for r in success_metrics[:10]:
                    st.write(f"- {r}")
        if not responsibilities and not deliverables and not success_metrics:
            st.info(
                "Keine verlässlichen Werte erkannt. Details siehe Gaps/Assumptions."
            )

    def _render_source_comparison_slot() -> None:
        coverage = sync_esco_shared_state()
        show_esco_sections = has_confirmed_esco_anchor()
        render_error_banner()

        selected_occupation = get_esco_occupation_selected()
        esco_suggestions: list[dict[str, str]] = []
        occupation_uri = (
            (
                coverage.selected_occupation_uri
                or (
                    str(selected_occupation.get("uri") or "").strip()
                    if selected_occupation
                    else ""
                )
            )
            if show_esco_sections
            else ""
        )
        if show_esco_sections and occupation_uri:
            esco_suggestions, esco_error = (
                _load_esco_task_suggestions_from_selected_occupation(occupation_uri)
            )
            if esco_error:
                st.caption(
                    f"ESCO-Hinweis: Occupation-Details konnten nicht geladen werden ({esco_error})."
                )
            elif esco_suggestions:
                render_esco_explainability(
                    labels=["derived from occupation relation"],
                    confidence="medium",
                    reason=(
                        "Aufgaben werden aus ESCO Occupation-Beschreibung abgeleitet "
                        "und sollten vor Übernahme kurz geprüft werden."
                    ),
                    caption_prefix="Task Suggestion Explainability",
        )
        st.session_state[SSKey.ROLE_TASKS_ESCO_SUGGESTED.value] = esco_suggestions

        llm_suggested_raw = st.session_state.get(SSKey.ROLE_TASKS_LLM_SUGGESTED.value, [])
        llm_suggested = llm_suggested_raw if isinstance(llm_suggested_raw, list) else []
        jobspec_labels = [str(item.get("label") or "").strip() for item in jobspec_suggestions if has_meaningful_value(item.get("label"))]
        ai_labels = [str(item.get("label") or "").strip() for item in llm_suggested if has_meaningful_value(item.get("label"))]
        esco_labels = [str(item.get("label") or "").strip() for item in esco_suggestions if has_meaningful_value(item.get("label"))]
        selected_raw = st.session_state.get(SSKey.ROLE_TASKS_SELECTED.value, [])
        selected = _dedupe_task_terms([str(item) for item in selected_raw]) if isinstance(selected_raw, list) else []

        render_compare_adopt_intro(
            adopt_target="Aufgaben",
            canonical_target="SSKey.ROLE_TASKS_SELECTED",
            source_labels=("Jobspec", "AI")
            if not show_esco_sections
            else ("Jobspec", "ESCO", "AI"),
        )
        render_output_header(
            "Aufgaben auswählen",
            "Wählen Sie die Aufgaben aus, die im Recruiting-Brief, in der Gehaltsprognose und in Folgeartefakten verwendet werden sollen.",
        )
        col_jobspec, col_ai, col_esco = responsive_three_columns(gap="large")
        with col_jobspec:
            st.markdown("#### Aus der Anzeige extrahiert")
            render_multi_select_pills(
                " ",
                options=jobspec_labels,
                key="role_tasks.jobspec.pills",
                default=[
                    item
                    for item in selected
                    if _normalize_task_term(item)
                    in {_normalize_task_term(v) for v in jobspec_labels}
                ],
            )
        with col_ai:
            st.markdown("#### AI-Vorschläge")
            st.number_input(
                "Anzahl Vorschläge",
                min_value=1,
                max_value=12,
                key=SSKey.ROLE_TASKS_SUGGEST_COUNT.value,
            )
            if st.button("AI-Vorschläge ergänzen"):
                context = _build_task_suggestion_context(
                    job=job,
                    include_esco_titles=show_esco_sections,
                )
                existing_tasks = _dedupe_task_terms(
                    [
                        *context["jobspec_terms"],
                        *[str(item.get("label") or "") for item in esco_suggestions],
                        *context["selected_terms"],
                    ]
                )
                target_task_count = int(
                    st.session_state.get(SSKey.ROLE_TASKS_SUGGEST_COUNT.value, 5)
                )

                with st.spinner("Generiere Aufgaben-Vorschläge …"):
                    pack, _usage = generate_requirement_gap_suggestions(
                        job=job,
                        answers=get_answers(),
                        existing_skills=[],
                        existing_tasks=existing_tasks,
                        esco_skill_titles=context["esco_skill_titles"],
                        target_skill_count=0,
                        target_task_count=target_task_count,
                        task_rag_context=_build_task_rag_context(job),
                        model=get_active_model(),
                        language=str(st.session_state.get(SSKey.LANGUAGE.value, "de")),
                        store=bool(
                            st.session_state.get(SSKey.STORE_API_OUTPUT.value, False)
                        ),
                    )

                merged_llm = _merge_llm_task_suggestions(
                    llm_tasks=[item.model_dump(mode="json") for item in pack.tasks],
                    blocked_labels=existing_tasks,
                )
                st.session_state[SSKey.ROLE_TASKS_LLM_SUGGESTED.value] = merged_llm
            llm_after = st.session_state.get(SSKey.ROLE_TASKS_LLM_SUGGESTED.value, [])
            llm_after_labels = [str(item.get("label") or "").strip() for item in llm_after if isinstance(item, dict) and has_meaningful_value(item.get("label"))]
            render_multi_select_pills(
                "  ",
                options=llm_after_labels,
                key="role_tasks.ai.pills",
                default=[
                    item
                    for item in selected
                    if _normalize_task_term(item)
                    in {_normalize_task_term(v) for v in llm_after_labels}
                ],
            )
        with col_esco:
            st.markdown("#### ESCO")
            render_multi_select_pills(
                "   ",
                options=esco_labels,
                key="role_tasks.esco.pills",
                default=[
                    item
                    for item in selected
                    if _normalize_task_term(item)
                    in {_normalize_task_term(v) for v in esco_labels}
                ],
            )

        selected_jobspec = st.session_state.get("role_tasks.jobspec.pills", []) or []
        selected_ai = st.session_state.get("role_tasks.ai.pills", []) or []
        selected_esco = st.session_state.get("role_tasks.esco.pills", []) or []
        st.session_state[f"{SSKey.ROLE_TASKS_SELECTED.value}.bulk_buffer"] = _dedupe_task_terms([*selected_jobspec, *selected_ai, *selected_esco])
        if st.button("Ausgewählte Aufgaben übernehmen", width="stretch"):
            _save_selected_task_suggestions(st.session_state[f"{SSKey.ROLE_TASKS_SELECTED.value}.bulk_buffer"])
        selected_now = st.session_state.get(SSKey.ROLE_TASKS_SELECTED.value, [])
        st.caption(f"Übernommen: {len(selected_now) if isinstance(selected_now, list) else 0} Aufgaben")

    def _render_salary_forecast_slot() -> None:
        selected_tasks = st.session_state.get(SSKey.ROLE_TASKS_SELECTED.value, [])
        canonical_tasks = (
            _dedupe_task_terms([str(item) for item in selected_tasks])
            if isinstance(selected_tasks, list)
            else []
        )

        st.markdown("#### Auswirkung auf Prognose")
        st.caption(
            "Die ausgewählten Aufgaben beeinflussen die Gehaltsprognose. "
            "Details und Szenarien findest du im aufklappbaren Bereich."
        )
        with st.expander("Auswirkung auf Gehaltsprognose", expanded=False):
            _render_role_tasks_salary_block(
                job=job,
                selected_tasks=canonical_tasks,
            )

    def _render_decision_and_salary_slot() -> None:
        _render_source_comparison_slot()
        _render_salary_forecast_slot()

    def _render_open_questions_slot() -> None:
        if step is None or not step.questions:
            st.info(
                "Für diesen Abschnitt wurden keine spezifischen Fragen erzeugt. Du kannst trotzdem weitergehen."
            )
            return

        render_question_step(step)

    render_step_shell(
        title="Rolle & Aufgaben",
        subtitle="Scope, Verantwortlichkeiten und Erfolgskriterien der Rolle.",
        outcome_text=(
            "Ein belastbarer Rollen-Scope mit priorisierten Aufgaben und klaren Erfolgskriterien "
            "als Basis für Briefing und Interviewleitfaden."
        ),
        step=step,
        extracted_from_jobspec_slot=_render_extracted_slot,
        extracted_from_jobspec_label="Aus der Anzeige extrahierte Rollen & Aufgaben",
        extracted_from_jobspec_use_expander=False,
        open_questions_slot=_render_open_questions_slot,
        review_slot=lambda: render_standard_step_review(
            step,
            render_mode=resolve_standard_review_mode(context=ReviewRenderContext.STEP_FORM),
        ),
        after_review_slot=_render_decision_and_salary_slot,
        footer_slot=lambda: nav_buttons(ctx),
    )


PAGE = WizardPage(
    key="role_tasks",
    title_de="Rolle & Aufgaben",
    icon="🧭",
    render=render,
    requires_jobspec=True,
)
