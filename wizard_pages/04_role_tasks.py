# wizard_pages/04_role_tasks.py
from __future__ import annotations

import re
from typing import Any

import streamlit as st

from constants import (
    FactKey,
    SSKey,
    STEP_KEY_ROLE_TASKS,
    STEP_SECTION_EXTRACTED_FROM_JOBSPEC,
    STEP_SECTION_OPEN_QUESTIONS,
    STEP_SECTION_REVIEW,
    STEP_SECTION_SALARY_FORECAST,
    STEP_SECTION_SOURCE_COMPARISON,
)
from esco_client import EscoClient, EscoClientError
from esco_rag import retrieve_esco_context_multi as retrieve_esco_context
from i18n import t
from llm_client import generate_requirement_gap_suggestions
from schemas import JobAdExtract, QuestionStep
from components.design_system import render_output_header
from summary_exports import build_live_artifact_preview_payload
from usage_events import record_enrichment_timed
from state import (
    get_active_model,
    get_answers,
    get_esco_semantic_context,
    sync_esco_shared_state,
)
from step_sections import (
    build_step_shell_section_kwargs,
    filter_open_questions_for_step,
)
from ui_components import (
    has_meaningful_value,
    render_source_pill_selection,
    render_compare_adopt_intro,
    render_esco_explainability,
    render_error_banner,
    render_live_artifact_preview_panel,
    render_question_step,
    ReviewRenderContext,
    resolve_standard_review_mode,
    render_standard_step_review,
)
from ui_layout import (
    LazySectionConfig,
    default_focus_drilldown_open,
    default_primary_workspace_open,
    is_focus_design_enabled,
    render_step_shell,
    responsive_three_columns,
)
from wizard_pages.base import (
    WizardContext,
    WizardPage,
    get_current_ui_mode,
    guard_job_and_plan,
    nav_buttons,
    resolve_dynamic_step_copy,
)
from wizard_pages.fact_inputs import (
    compact_text,
    fact_value,
    persist_compact_object,
    persist_fact,
    render_multiselect_fact,
    render_select_fact,
    section_container,
    render_text_area_fact,
    render_text_fact,
)
from wizard_pages.company_work_context import (
    render_non_negotiables_compliance_section,
    render_work_context_sections,
)
from wizard_pages.salary_forecast_panel import render_role_tasks_salary_forecast_panel


_RESPONSIBILITY_PRIORITY_LABELS = {
    "must": "Must",
    "core": "Core",
    "optional": "Optional",
}
_DECISION_SCOPE_LABELS = {
    "keine_eigenen_entscheidungen": "Keine eigenen Entscheidungen",
    "fachliche_empfehlungen": "Fachliche Empfehlungen",
    "eigenstaendige_fachentscheidungen": "Eigenständige Fachentscheidungen",
    "budget_personal_oder_prioritaeten": "Budget, Personal oder Prioritäten",
    "unklar": "Noch unklar",
}
_YES_NO_UNKNOWN_LABELS = {
    "unknown": "Noch unklar",
    "yes": "Ja",
    "no": "Nein",
}
_ROLE_PREVIEW_FACT_KEYS = (
    FactKey.ROLE_BUSINESS_OUTCOME_PRIMARY,
    FactKey.ROLE_DELIVERABLES,
    FactKey.ROLE_DAY1_RESPONSIBILITIES,
    FactKey.ROLE_EXPANSION_SCOPE,
    FactKey.ROLE_RESPONSIBILITIES_PRIORITIZED,
    FactKey.ROLE_SUCCESS_METRICS_TIMELINE,
    FactKey.ROLE_DECISION_SCOPE,
    FactKey.ROLE_YEAR1_SUCCESS_SIGNALS,
    FactKey.COMPANY_NON_NEGOTIABLES,
    FactKey.ROLE_TRAVEL_PROFILE,
)


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


def _read_selected_texts(state_key: SSKey) -> list[str]:
    raw = st.session_state.get(state_key.value, [])
    return (
        _dedupe_task_terms([str(item) for item in raw])
        if isinstance(raw, list)
        else []
    )


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
    job_title = getattr(job, "job_title", None) or getattr(job, "title", None)
    query_parts = _dedupe_task_terms(
        [part for part in [job_title, *job.responsibilities[:3], *job.deliverables[:3]] if has_meaningful_value(part)]
    )
    queries = [
        str(job_title or "").strip(),
        " | ".join(part for part in query_parts if has_meaningful_value(part)),
    ]
    if not any(query.strip() for query in queries):
        return []
    rag_result = retrieve_esco_context(queries, purpose="tasks", max_results=4)
    record_enrichment_timed(
        st.session_state,
        stage="esco_rag",
        path="role_tasks",
        duration_ms=getattr(rag_result, "duration_ms", None) or 0,
        status=getattr(rag_result, "reason", None) or "success",
        result_count=len(getattr(rag_result, "hits", ())),
    )
    hits = getattr(rag_result, "hits", ())
    if getattr(rag_result, "reason", None) is not None or not hits:
        return []
    context: list[dict[str, str]] = []
    for hit in hits[:4]:
        snippet = str(hit.snippet).strip()
        if not snippet:
            continue
        item = {
            "snippet": snippet[:320],
            "source_hint": "esco_rag",
            "source_title": str(getattr(hit, "source_title", None) or "").strip(),
            "source_file": str(getattr(hit, "source_file", None) or "").strip(),
            "concept_uri": str(getattr(hit, "concept_uri", None) or "").strip(),
        }
        score = getattr(hit, "score", None)
        if score is not None:
            item["score"] = f"{score:.3f}"
        context.append(item)
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
    source_counts: dict[str, int] | None = None,
) -> None:
    render_role_tasks_salary_forecast_panel(
        job=job,
        selected_tasks=selected_tasks,
        model=get_active_model(),
        language=str(st.session_state.get(SSKey.LANGUAGE.value, "de")),
        store=bool(st.session_state.get(SSKey.STORE_API_OUTPUT.value, False)),
        source_counts=source_counts,
    )


def _priority_by_label(raw_items: Any) -> dict[str, str]:
    items = raw_items if isinstance(raw_items, list) else []
    output: dict[str, str] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        label = compact_text(item.get("label"))
        priority = compact_text(item.get("priority")) or "core"
        if label:
            output[label] = priority if priority in _RESPONSIBILITY_PRIORITY_LABELS else "core"
    return output


def _render_compact_signal_list(title: str, items: list[str], *, limit: int = 5) -> None:
    st.markdown(f"#### {title}")
    if not items:
        st.caption("Keine Angabe erkannt.")
        return
    for item in items[:limit]:
        st.write(f"- {item}")
    remaining = items[limit:]
    if remaining:
        with st.expander(f"{len(remaining)} weitere anzeigen", expanded=False):
            for item in remaining:
                st.write(f"- {item}")


def _has_compact_payload(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_has_compact_payload(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_compact_payload(item) for item in value)
    return has_meaningful_value(value)


def _fact_text_items(value: Any) -> list[str]:
    if isinstance(value, list):
        return _dedupe_task_terms([str(item) for item in value])
    if isinstance(value, str):
        return _split_task_like_text(value)
    return []


def _build_role_preview_fact_payload() -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for fact_key in _ROLE_PREVIEW_FACT_KEYS:
        value = fact_value(fact_key, None)
        if _has_compact_payload(value):
            payload[fact_key.value] = value
    return payload


def _first_success_horizon_text(job: JobAdExtract) -> str:
    timeline_raw = fact_value(FactKey.ROLE_SUCCESS_METRICS_TIMELINE, {})
    timeline = timeline_raw if isinstance(timeline_raw, dict) else {}
    for key, label in (
        ("30_days", "30 Tage"),
        ("60_days", "60 Tage"),
        ("90_days", "90 Tage"),
        ("180_days", "180 Tage"),
    ):
        value = compact_text(timeline.get(key))
        if value:
            return f"{label}: {value}"
    year1 = compact_text(fact_value(FactKey.ROLE_YEAR1_SUCCESS_SIGNALS, ""))
    if year1:
        return f"12 Monate: {year1}"
    if job.success_metrics:
        return f"{len(job.success_metrics)} Erfolgskriterien aus Jobspec"
    return "Noch offen"


def _render_role_search_start_snapshot(
    *,
    job: JobAdExtract,
    selected_tasks: list[str],
) -> None:
    preview_facts = _build_role_preview_fact_payload()
    outcome = (
        compact_text(preview_facts.get(FactKey.ROLE_BUSINESS_OUTCOME_PRIMARY.value))
        or compact_text(job.role_overview)
        or "Noch offen"
    )
    outputs = _dedupe_task_terms(
        [
            *job.deliverables,
            *_fact_text_items(preview_facts.get(FactKey.ROLE_DELIVERABLES.value, [])),
        ]
    )
    non_negotiables = _fact_text_items(
        preview_facts.get(FactKey.COMPANY_NON_NEGOTIABLES.value, [])
    )
    with section_container(border=True):
        st.markdown("#### Suchstart-Check")
        st.caption(
            t(
                "Kurzer Live-Stand für Recruiter: Rollenauftrag, Ergebnis, erster "
                "Erfolgshorizont und harte Suchgrenzen."
            )
        )
        cols = st.columns(2, gap="large")
        items = (
            ("Rollenauftrag", outcome),
            (
                "Erwartete Ergebnisse",
                ", ".join(outputs[:3]) if outputs else "Noch offen",
            ),
            ("Erster Erfolg", _first_success_horizon_text(job)),
            (
                "Nicht verhandelbar",
                ", ".join(non_negotiables[:3]) if non_negotiables else "Noch offen",
            ),
        )
        for index, (label, value) in enumerate(items):
            col = cols[index % len(cols)]
            with col:
                st.markdown(f"**{label}**")
                st.write(value)
        if selected_tasks:
            st.caption(
                f"{len(selected_tasks)} ausgewählte Aufgaben prägen Brief, Job-Ad, "
                "Suchstrings und Interview-Evidenz."
            )


def _filtered_role_tasks_open_question_step(
    step: QuestionStep | None,
) -> QuestionStep | None:
    return filter_open_questions_for_step(step, step_key=STEP_KEY_ROLE_TASKS)


def _render_success_timeline() -> None:
    current_raw = fact_value(FactKey.ROLE_SUCCESS_METRICS_TIMELINE, {})
    current = current_raw if isinstance(current_raw, dict) else {}
    timeline: dict[str, str] = {}
    cols = responsive_three_columns(gap="large")
    milestones = (
        ("30_days", "Nach 30 Tagen"),
        ("60_days", "Nach 60 Tagen"),
        ("90_days", "Nach 90 Tagen"),
        ("180_days", "Nach 180 Tagen"),
    )
    for idx, (key, label) in enumerate(milestones):
        with cols[idx % len(cols)]:
            timeline[key] = st.text_area(
                label,
                value=str(current.get(key) or ""),
                height=80,
                key=f"fact_input.{FactKey.ROLE_SUCCESS_METRICS_TIMELINE.value}.{key}",
            ).strip()
    persist_compact_object(FactKey.ROLE_SUCCESS_METRICS_TIMELINE, timeline)


def _render_travel_profile() -> None:
    current_raw = fact_value(FactKey.ROLE_TRAVEL_PROFILE, {})
    current = current_raw if isinstance(current_raw, dict) else {}
    required = compact_text(current.get("required"))
    if required not in _YES_NO_UNKNOWN_LABELS:
        required = "unknown"
    col_required, col_percent, col_frequency = responsive_three_columns(gap="large")
    with col_required:
        required_value = st.selectbox(
            "Reisen erforderlich?",
            options=tuple(_YES_NO_UNKNOWN_LABELS),
            index=tuple(_YES_NO_UNKNOWN_LABELS).index(required),
            format_func=lambda value: _YES_NO_UNKNOWN_LABELS.get(value, value),
            key=f"fact_input.{FactKey.ROLE_TRAVEL_PROFILE.value}.required",
        )
    with col_percent:
        try:
            current_percent = float(current.get("percent") or 0)
        except (TypeError, ValueError):
            current_percent = 0.0
        percent = st.number_input(
            "Reiseanteil (%)",
            min_value=0.0,
            max_value=100.0,
            value=max(0.0, min(100.0, current_percent)),
            step=5.0,
            key=f"fact_input.{FactKey.ROLE_TRAVEL_PROFILE.value}.percent",
        )
    with col_frequency:
        frequency = st.text_input(
            "Frequenz",
            value=compact_text(current.get("frequency")),
            placeholder="z. B. monatlich, wöchentlich",
            key=f"fact_input.{FactKey.ROLE_TRAVEL_PROFILE.value}.frequency",
        )
    col_region, col_overnight, col_vehicle = responsive_three_columns(gap="large")
    with col_region:
        region = st.text_input(
            "Region",
            value=compact_text(current.get("region")),
            key=f"fact_input.{FactKey.ROLE_TRAVEL_PROFILE.value}.region",
        )
    with col_overnight:
        overnight = st.checkbox(
            "Übernachtungen möglich",
            value=bool(current.get("overnight_required")),
            key=f"fact_input.{FactKey.ROLE_TRAVEL_PROFILE.value}.overnight",
        )
    with col_vehicle:
        vehicle_policy = st.text_input(
            "Fahrzeugregelung",
            value=compact_text(current.get("vehicle_policy")),
            key=f"fact_input.{FactKey.ROLE_TRAVEL_PROFILE.value}.vehicle_policy",
        )
    driving_license_required = st.text_input(
        "Führerschein / Mobilitätsnachweis",
        value=compact_text(current.get("driving_license_required")),
        key=f"fact_input.{FactKey.ROLE_TRAVEL_PROFILE.value}.driving_license",
    )
    persist_compact_object(
        FactKey.ROLE_TRAVEL_PROFILE,
        {
            "required": required_value == "yes" if required_value != "unknown" else None,
            "percent": percent,
            "frequency": frequency,
            "region": region,
            "overnight_required": overnight,
            "driving_license_required": driving_license_required,
            "vehicle_policy": vehicle_policy,
        },
    )


def _render_structured_role_scope(
    job: JobAdExtract,
    candidate_tasks: list[str],
    *,
    selected_tasks: list[str],
) -> None:
    selected_task_options = _dedupe_task_terms(selected_tasks)
    task_options = _dedupe_task_terms([*selected_task_options, *candidate_tasks])
    existing_outputs = _fact_text_items(fact_value(FactKey.ROLE_DELIVERABLES, []))
    output_options = _dedupe_task_terms(
        [
            *existing_outputs,
            *job.deliverables,
            *selected_task_options,
            *candidate_tasks,
        ]
    )
    st.markdown("### Rollenauftrag vor Suchstart")
    st.caption(
        t(
            "Kläre, wofür die Rolle da ist, welche Ergebnisse entstehen müssen und "
            "welche Verantwortung Recruiter vor der Suche verstanden haben müssen."
        )
    )
    with section_container(border=True):
        render_text_fact(
            FactKey.ROLE_BUSINESS_OUTCOME_PRIMARY,
            "Wofür ist die Rolle da?",
            default=job.role_overview or "",
            placeholder="z. B. stabile Datenplattform, schnellere Kundenantworten",
        )
        col_outputs, col_day1, col_later = responsive_three_columns(gap="large")
        with col_outputs:
            render_multiselect_fact(
                FactKey.ROLE_DELIVERABLES,
                "Erwartete Ergebnisse",
                options=output_options
                or [
                    "Betriebsergebnis",
                    "Kundenlieferung",
                    "Reporting",
                    "Projektabschluss",
                    "Prozessverbesserung",
                    "Team Enablement",
                    "Sonstiges",
                ],
                default=job.deliverables,
            )
        with col_day1:
            render_multiselect_fact(
                FactKey.ROLE_DAY1_RESPONSIBILITIES,
                "Verantwortung ab Tag 1",
                options=task_options
                or [
                    "Kernbetrieb",
                    "Kundenkontakt",
                    "Reporting",
                    "Projektstart",
                    "Teamkoordination",
                    "Sonstiges",
                ],
            )
        with col_later:
            render_multiselect_fact(
                FactKey.ROLE_EXPANSION_SCOPE,
                "Später ausbaubar",
                options=task_options
                or [
                    "Automatisierung",
                    "Strategie",
                    "Mentoring",
                    "Reporting",
                    "Stakeholder-Ausbau",
                    "Tooling",
                    "Sonstiges",
                ],
            )
        existing_priorities = _priority_by_label(
            fact_value(FactKey.ROLE_RESPONSIBILITIES_PRIORITIZED, [])
        )
        prioritized: list[dict[str, str]] = []
        if task_options:
            with st.expander("Verantwortung priorisieren", expanded=False):
                st.caption(
                    "Must-Aufgaben sind Such- und Interviewanker. Optionales bleibt "
                    "nice-to-have und sollte den Search nicht verengen."
                )
                for idx, label in enumerate(task_options[:10]):
                    cols = st.columns([2, 1], gap="small")
                    with cols[0]:
                        st.caption(label)
                    with cols[1]:
                        priority = st.selectbox(
                            "Priorität",
                            options=tuple(_RESPONSIBILITY_PRIORITY_LABELS),
                            index=tuple(_RESPONSIBILITY_PRIORITY_LABELS).index(
                                existing_priorities.get(label, "core")
                                if existing_priorities.get(label, "core") in _RESPONSIBILITY_PRIORITY_LABELS
                                else "core"
                            ),
                            format_func=lambda value: _RESPONSIBILITY_PRIORITY_LABELS.get(value, value),
                            key=f"fact_input.{FactKey.ROLE_RESPONSIBILITIES_PRIORITIZED.value}.{idx}",
                        )
                    prioritized.append({"label": label, "priority": priority})
        persist_fact(FactKey.ROLE_RESPONSIBILITIES_PRIORITIZED, prioritized)

    st.markdown("### Erfolg & Verantwortung")
    with section_container(border=True):
        col_decision, col_success = st.columns([1, 2], gap="large")
        with col_decision:
            render_select_fact(
                FactKey.ROLE_DECISION_SCOPE,
                "Entscheidungsspielraum der Rolle",
                options=tuple(_DECISION_SCOPE_LABELS),
                default="unklar",
                labels=_DECISION_SCOPE_LABELS,
            )
        with col_success:
            render_text_area_fact(
                FactKey.ROLE_YEAR1_SUCCESS_SIGNALS,
                "Erfolg nach 12 Monaten / dauerhaft",
                default="\n".join(job.success_metrics[:3]),
                height=100,
            )
        with st.expander("Erster Erfolgshorizont (30 bis 180 Tage)", expanded=True):
            _render_success_timeline()

    st.markdown("### Suchstart-Guardrails")
    render_non_negotiables_compliance_section(
        heading="Nicht verhandelbar vor Suchstart",
        collapse_secondary_details=True,
    )
    _render_role_search_start_snapshot(job=job, selected_tasks=selected_task_options)

    travel_current = fact_value(FactKey.ROLE_TRAVEL_PROFILE, {})
    with st.expander(
        "Reiseprofil und Bereitschaft",
        expanded=_has_compact_payload(travel_current),
    ):
        _render_travel_profile()


def render(ctx: WizardContext) -> None:
    preflight = guard_job_and_plan(ctx)
    if preflight is None:
        return
    job, plan = preflight
    step = next((s for s in plan.steps if s.step_key == "role_tasks"), None)
    open_question_step = _filtered_role_tasks_open_question_step(step)

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
    source_counts: dict[str, int] = {"Jobspec": 0, "ESCO / Kontext": 0, "AI": 0}

    def _render_extracted_slot() -> None:
        render_output_header(
            "Erkannter Aufgabenstand",
            "Schneller Überblick aus der Anzeige. Details ergänzt du im nächsten Abschnitt.",
            meta_items=(
                ("📋", "Aufgaben", str(len(responsibilities))),
                ("🎯", "Ergebnisse", str(len(deliverables))),
                ("✓", "Erfolg", str(len(success_metrics))),
            ),
        )
        col_resp, col_deliv, col_metrics = responsive_three_columns(gap="large")
        with col_resp:
            _render_compact_signal_list("Aufgaben", responsibilities)
        with col_deliv:
            _render_compact_signal_list("Ergebnisse", deliverables)
        with col_metrics:
            _render_compact_signal_list("Erfolgskriterien", success_metrics)
        if not responsibilities and not deliverables and not success_metrics:
            st.info(
                "Keine belastbaren Aufgaben erkannt. Kläre die Rolle über die offenen Fragen."
            )
        expander = getattr(st, "expander", None)
        if callable(expander):
            with expander("Arbeitsmodell, Standort und Rahmen aus Jobspec", expanded=False):
                render_work_context_sections(
                    job,
                    include_non_negotiables_compliance=False,
                )
        else:
            render_work_context_sections(
                job,
                include_non_negotiables_compliance=False,
            )

    def _render_source_comparison_slot() -> None:
        nonlocal source_counts
        coverage = sync_esco_shared_state()
        semantic_context = get_esco_semantic_context()
        show_esco_sections = semantic_context.can_use_task_suggestions
        render_error_banner()

        selected_occupation = (
            semantic_context.primary_anchor.model_dump(mode="json")
            if semantic_context.primary_anchor is not None
            else None
        )
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
                occupation_title = (
                    str(selected_occupation.get("title") or "").strip()
                    if selected_occupation
                    else ""
                )
                if occupation_title:
                    st.caption(
                        "Vorschläge basieren auf dem bestätigten Referenzberuf: "
                        f"{occupation_title}."
                    )
                if get_current_ui_mode() == "expert":
                    render_esco_explainability(
                        labels=["derived from occupation relation"],
                        confidence="medium",
                        reason=(
                            "Aufgaben werden aus ESCO Occupation-Beschreibung "
                            "abgeleitet und sollten vor Übernahme kurz geprüft werden."
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
            source_labels=("Jobspec", "ESCO/Kontext", "AI"),
            render_explanatory_copy=False,
        )
        render_output_header(
            "Aufgaben auswählen",
            "Übernimm nur Aufgaben, die wirklich zur Rolle gehören.",
            meta_items=(
                ("📄", "Anzeige", str(len(jobspec_labels))),
                ("🧭", "Berufsprofil", str(len(esco_labels))),
                ("✦", "AI", str(len(ai_labels))),
            ),
        )
        ai_control_col, ai_action_col = st.columns([1, 2], gap="small")
        with ai_control_col:
            st.number_input(
                "Weitere Vorschläge",
                min_value=1,
                max_value=12,
                key=SSKey.ROLE_TASKS_SUGGEST_COUNT.value,
            )
        with ai_action_col:
            generate_ai = st.button("Vorschläge ergänzen", width="stretch")
        if generate_ai:
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

            with st.spinner("Ergänze passende Aufgaben …"):
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
        llm_after_labels = [
            str(item.get("label") or "").strip()
            for item in llm_after
            if isinstance(item, dict) and has_meaningful_value(item.get("label"))
        ]
        selection_result = render_source_pill_selection(
            columns=[
                {
                    "title": "Jobspec",
                    "source_key": "Jobspec",
                    "options": jobspec_labels,
                    "state_key": SSKey.ROLE_TASKS_JOBSPEC_PILLS.value,
                },
                {
                    "title": "ESCO / Kontext",
                    "source_key": "ESCO / Kontext",
                    "options": esco_labels,
                    "state_key": SSKey.ROLE_TASKS_ESCO_PILLS.value,
                },
                {
                    "title": "AI",
                    "source_key": "AI",
                    "options": llm_after_labels,
                    "state_key": SSKey.ROLE_TASKS_AI_PILLS.value,
                },
            ],
            selected_labels=selected,
            selected_state_key=SSKey.ROLE_TASKS_SELECTED.value,
            key_prefix="role_tasks.sources",
            empty_caption="Keine Vorschläge vorhanden.",
        )
        source_counts = selection_result["source_counts"]
        st.session_state[SSKey.ROLE_TASKS_SELECTED_BULK_BUFFER.value] = (
            selection_result["selected_labels"]
        )
        st.caption(f"{len(selection_result['selected_labels'])} Aufgaben ausgewählt")
        _render_structured_role_scope(
            job,
            _dedupe_task_terms(
                [
                    *selection_result["selected_labels"],
                    *jobspec_labels,
                    *esco_labels,
                    *llm_after_labels,
                ]
            ),
            selected_tasks=selection_result["selected_labels"],
        )
        render_live_artifact_preview_panel(
            key="role_tasks",
            default_open=default_focus_drilldown_open(classic_default_open=True),
            title="Warum das zählt",
            caption=(
                "Live aus den aktuellen Angaben: welche Signale später in Brief, "
                "Job-Ad, Suchstrings und Interview-Sheets landen. Keine "
                "Unterlagenerstellung."
            ),
            streamlit_module=st,
            preview_builder=lambda: build_live_artifact_preview_payload(
                job=job,
                answers=get_answers(),
                selected_role_tasks=selection_result["selected_labels"],
                selected_skills=_read_selected_texts(SSKey.SKILLS_SELECTED),
                selected_benefits=_read_selected_texts(SSKey.BENEFITS_SELECTED),
                intake_facts=_build_role_preview_fact_payload(),
            ),
        )

    def _render_salary_forecast_slot() -> None:
        selected_tasks_raw = st.session_state.get(SSKey.ROLE_TASKS_SELECTED.value, [])
        canonical_tasks = (
            _dedupe_task_terms([str(item) for item in selected_tasks_raw])
            if isinstance(selected_tasks_raw, list)
            else []
        )
        selected_count = len(canonical_tasks)

        st.markdown("#### Wirkung auf die Gehaltsprognose")
        st.caption(f"{selected_count} ausgewählte Aufgaben fließen in die Prognose ein.")
        if selected_count == 0:
            st.caption("Noch keine Aufgaben ausgewählt.")
        _render_role_tasks_salary_block(
            job=job,
            selected_tasks=canonical_tasks,
            source_counts=source_counts,
        )

    def _render_open_questions_slot() -> None:
        st.markdown("#### Offene Punkte")
        st.caption(
            "Nur die Fragen beantworten, die für ein klares Rollenbild noch fehlen."
        )
        if open_question_step is None or not open_question_step.questions:
            st.info(
                "Für diesen Abschnitt wurden keine spezifischen Fragen erzeugt. Du kannst trotzdem weitergehen."
            )
            return

        render_question_step(open_question_step, context_mode="compact")

    def _render_review_slot() -> None:
        st.markdown("#### Prüfung")
        st.caption(
            "Kurz prüfen, ob Aufgaben, Verantwortung und offene Punkte reichen."
        )
        render_standard_step_review(
            step,
            render_mode=resolve_standard_review_mode(
                context=ReviewRenderContext.STEP_FORM
            ),
        )

    section_kwargs = build_step_shell_section_kwargs(
        step_key=STEP_KEY_ROLE_TASKS,
        renderers={
            STEP_SECTION_EXTRACTED_FROM_JOBSPEC: _render_extracted_slot,
            STEP_SECTION_SOURCE_COMPARISON: _render_source_comparison_slot,
            STEP_SECTION_SALARY_FORECAST: _render_salary_forecast_slot,
            STEP_SECTION_OPEN_QUESTIONS: _render_open_questions_slot,
            STEP_SECTION_REVIEW: _render_review_slot,
        },
    )

    step_copy = resolve_dynamic_step_copy(STEP_KEY_ROLE_TASKS, job=job)
    lazy_section_configs = {
        "source_comparison_slot": LazySectionConfig(
            label="Aufgabenpool",
            caption=(
                "Anzeige, Berufsprofil und ergänzende Vorschläge in einer Auswahl."
            ),
            button_label="Aufgabenpool öffnen",
            default_open=default_primary_workspace_open(),
        ),
        "salary_forecast_slot": LazySectionConfig(
            label="Gehaltsprognose",
            caption=(
                "Zeigt bei Bedarf, wie die ausgewählten Aufgaben die Prognose beeinflussen."
            ),
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
                        "Zeigt die aus der Anzeige erkannten Aufgaben, Ergebnisse "
                        "und Erfolgskriterien."
                    ),
                    button_label="Jobspec-Snapshot öffnen",
                    default_open=default_focus_drilldown_open(
                        classic_default_open=True
                    ),
                ),
                "open_questions_slot": LazySectionConfig(
                    label="Offene Punkte",
                    caption=(
                        "Nur die Fragen beantworten, die für ein klares Rollenbild "
                        "noch fehlen."
                    ),
                    button_label="Offene Punkte öffnen",
                    default_open=default_focus_drilldown_open(
                        classic_default_open=True
                    ),
                ),
                "review_slot": LazySectionConfig(
                    label="Prüfung",
                    caption=(
                        "Kurz prüfen, ob Aufgaben, Verantwortung und offene Punkte "
                        "reichen."
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
        extracted_from_jobspec_use_expander=False,
        lazy_section_configs=lazy_section_configs,
        **section_kwargs,
        footer_slot=lambda: nav_buttons(ctx),
    )


PAGE = WizardPage(
    key="role_tasks",
    title_de="Rolle & Aufgaben",
    icon="🧭",
    render=render,
    requires_jobspec=True,
)
