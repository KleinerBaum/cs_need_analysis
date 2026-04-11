# wizard_pages/04_role_tasks.py
from __future__ import annotations

import re
from typing import Any

import streamlit as st

from constants import SSKey
from esco_client import EscoClient, EscoClientError
from llm_client import generate_requirement_gap_suggestions
from schemas import JobAdExtract, QuestionPlan
from state import get_active_model, get_answers, get_esco_occupation_selected
from ui_components import (
    has_meaningful_value,
    render_error_banner,
    render_question_step,
)
from wizard_pages.base import WizardContext, WizardPage, nav_buttons


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

    suggestions = [{"label": label, "source": "ESCO"} for label in task_terms[:8]]

    if not suggestions and title:
        # Keep UI context transparent, but avoid fabricating unsupported task relations.
        return [], None

    return suggestions, None


def _build_task_suggestion_context(*, job: JobAdExtract) -> dict[str, list[str]]:
    jobspec_terms = _dedupe_task_terms(
        [*job.responsibilities, *job.deliverables, *job.success_metrics]
    )
    esco_titles = _dedupe_task_terms(
        [
            str(item.get("title") or "").strip()
            for item in st.session_state.get(SSKey.ESCO_SKILLS_SELECTED_MUST.value, [])
            if isinstance(item, dict)
        ]
        + [
            str(item.get("title") or "").strip()
            for item in st.session_state.get(SSKey.ESCO_SKILLS_SELECTED_NICE.value, [])
            if isinstance(item, dict)
        ]
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
                "importance": str(item.get("importance") or "").strip(),
                "rationale": str(item.get("rationale") or "").strip(),
                "evidence": str(item.get("evidence") or "").strip(),
            }
        )
        seen.add(normalized)
    return merged


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


def _safe_text(value: str | None) -> str:
    text = str(value or "").strip()
    return text if text else "Keine Details verfügbar."


def _render_role_task_source_columns(
    *,
    jobspec_suggested: list[dict[str, str]],
    esco_suggested: list[dict[str, str]],
    llm_suggested: list[dict[str, str]],
) -> None:
    st.markdown("### Aufgaben vergleichen & übernehmen")

    selected_raw = st.session_state.get(SSKey.ROLE_TASKS_SELECTED.value, [])
    selected_set = (
        {_normalize_task_term(str(item)) for item in selected_raw}
        if isinstance(selected_raw, list)
        else set()
    )

    board_items = [
        ("Aus Jobspec extrahiert", jobspec_suggested, "Jobspec"),
        ("ESCO", esco_suggested, "ESCO"),
        ("AI-Vorschläge", llm_suggested, "AI"),
    ]
    bulk_buffer: list[str] = []
    columns = st.columns(3, gap="small")

    for col, (title, entries, source) in zip(columns, board_items):
        with col:
            st.markdown(f"#### {title}")
            if not entries:
                if source == "ESCO":
                    st.caption(
                        "Keine zuverlässig ableitbaren Aufgaben aus Occupation-Details."
                    )
                else:
                    st.caption("Keine Vorschläge.")
                continue

            for idx, entry in enumerate(entries):
                label = str(entry.get("label") or "").strip()
                if not label:
                    continue
                normalized = _normalize_task_term(label)
                select_key = f"role_tasks.board.select.{source}.{idx}.{normalized}"
                add_key = f"role_tasks.board.add.{source}.{idx}.{normalized}"
                is_selected = st.checkbox(
                    label,
                    key=select_key,
                    value=normalized in selected_set,
                )
                if st.button("Hinzufügen", key=add_key):
                    added = _save_selected_task_suggestions([label])
                    if added > 0:
                        st.success("Aufgabe übernommen.")
                    else:
                        st.caption("Bereits übernommen.")
                if source == "AI":
                    with st.expander("Begründung / Evidence", expanded=False):
                        st.write(f"**Rationale:** {_safe_text(entry.get('rationale'))}")
                        st.write(f"**Evidence:** {_safe_text(entry.get('evidence'))}")
                if is_selected:
                    bulk_buffer.append(label)

    if st.button("Ausgewählte Aufgaben übernehmen", use_container_width=True):
        added_count = _save_selected_task_suggestions(bulk_buffer)
        if added_count > 0:
            st.success(f"{added_count} Aufgabe(n) übernommen.")
        else:
            st.info("Keine neuen Aufgaben übernommen.")


def render(ctx: WizardContext) -> None:
    st.header("Rolle & Aufgaben")
    render_error_banner()

    job_dict = st.session_state.get(SSKey.JOB_EXTRACT.value)
    plan_dict = st.session_state.get(SSKey.QUESTION_PLAN.value)

    if not job_dict or not plan_dict:
        st.warning("Bitte zuerst im Start-Schritt eine Analyse durchführen.")
        st.button("Zur Startseite", on_click=lambda: ctx.goto("landing"))
        nav_buttons(ctx, disable_next=True)
        return

    job = JobAdExtract.model_validate(job_dict)
    plan = QuestionPlan.model_validate(plan_dict)

    st.write(
        "Jetzt schärfen wir Scope, Verantwortlichkeiten, Deliverables, Erfolgskriterien und Stakeholder. "
        "Das ist der Kern für Briefing, Interviewleitfaden und Erwartungsmanagement."
    )

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

    with st.expander(
        "Aus Jobspec extrahiert (Responsibilities & Metrics)", expanded=True
    ):
        if responsibilities:
            st.write("**Responsibilities (Auszug):**")
            for r in responsibilities[:10]:
                st.write(f"- {r}")
        if deliverables:
            st.write("**Deliverables (Auszug):**")
            for d in deliverables[:10]:
                st.write(f"- {d}")
        if success_metrics:
            st.write("**Success Metrics (Auszug):**")
            for r in success_metrics[:10]:
                st.write(f"- {r}")
        if not responsibilities and not deliverables and not success_metrics:
            st.info(
                "Keine verlässlichen Werte erkannt. Details siehe Gaps/Assumptions."
            )

    selected_occupation = get_esco_occupation_selected()
    esco_suggestions: list[dict[str, str]] = []
    if selected_occupation and str(selected_occupation.get("uri") or "").strip():
        occupation_uri = str(selected_occupation.get("uri") or "").strip()
        esco_suggestions, esco_error = (
            _load_esco_task_suggestions_from_selected_occupation(occupation_uri)
        )
        if esco_error:
            st.caption(
                f"ESCO-Hinweis: Occupation-Details konnten nicht geladen werden ({esco_error})."
            )
    st.session_state[SSKey.ROLE_TASKS_ESCO_SUGGESTED.value] = esco_suggestions

    st.markdown("### AI-Vorschläge ergänzen")
    st.number_input(
        "Anzahl AI-Aufgaben-Vorschläge",
        min_value=1,
        max_value=12,
        key=SSKey.ROLE_TASKS_SUGGEST_COUNT.value,
    )

    if st.button("Aufgaben-Vorschläge generieren"):
        context = _build_task_suggestion_context(job=job)
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
                model=get_active_model(),
                language=str(st.session_state.get(SSKey.LANGUAGE.value, "de")),
                store=bool(st.session_state.get(SSKey.STORE_API_OUTPUT.value, False)),
            )

        merged_llm = _merge_llm_task_suggestions(
            llm_tasks=[item.model_dump(mode="json") for item in pack.tasks],
            blocked_labels=existing_tasks,
        )
        st.session_state[SSKey.ROLE_TASKS_LLM_SUGGESTED.value] = merged_llm
        st.success(f"{len(merged_llm)} neue AI-Aufgabe(n) vorgeschlagen.")

    llm_suggested_raw = st.session_state.get(SSKey.ROLE_TASKS_LLM_SUGGESTED.value, [])
    llm_suggested = llm_suggested_raw if isinstance(llm_suggested_raw, list) else []

    _render_role_task_source_columns(
        jobspec_suggested=jobspec_suggestions,
        esco_suggested=esco_suggestions,
        llm_suggested=llm_suggested,
    )

    step = next((s for s in plan.steps if s.step_key == "role_tasks"), None)
    if step is None or not step.questions:
        st.info(
            "Für diesen Abschnitt wurden keine spezifischen Fragen erzeugt. Du kannst trotzdem weitergehen."
        )
        nav_buttons(ctx)
        return

    render_question_step(step)
    nav_buttons(ctx)


PAGE = WizardPage(
    key="role_tasks",
    title_de="Rolle & Aufgaben",
    icon="🧭",
    render=render,
    requires_jobspec=True,
)
