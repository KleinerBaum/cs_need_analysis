from __future__ import annotations

from typing import Any

import streamlit as st

from constants import SSKey
from esco_client import EscoClient, EscoClientError
from schemas import EscoConceptRef, EscoSuggestionItem, JobAdExtract, QuestionPlan
from ui_components import (
    _render_question_limits_editor,
    render_error_banner,
    render_job_extract_overview,
)
from wizard_pages.base import WizardContext, WizardPage, nav_buttons

_NO_OCCUPATION_OPTION = "Keine passende Occupation"


def _extract_occupation_candidates(payload: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen_uris: set[str] = set()

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            uri_raw = node.get("uri")
            title_raw = (
                node.get("title")
                or node.get("preferredLabel")
                or node.get("label")
                or node.get("name")
            )
            type_raw = str(node.get("type") or "occupation").strip().lower()
            score_raw = node.get("score")
            if isinstance(uri_raw, str) and isinstance(title_raw, str):
                uri = uri_raw.strip()
                title = title_raw.strip()
                if uri and title and type_raw == "occupation" and uri not in seen_uris:
                    score: float | None = None
                    if isinstance(score_raw, (int, float)):
                        score = float(score_raw)
                    candidates.append(
                        {
                            "uri": uri,
                            "title": title,
                            "type": "occupation",
                            "score": score,
                        }
                    )
                    seen_uris.add(uri)
            for value in node.values():
                _walk(value)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(payload)
    validated: list[dict[str, Any]] = []
    for item in candidates:
        try:
            validated.append(EscoSuggestionItem.model_validate(item).model_dump())
        except Exception:
            continue
    return validated


def _build_esco_query(job: JobAdExtract) -> str:
    title = (job.job_title or "").strip()
    if not title:
        return ""
    context_parts = [job.seniority_level, job.department_name, job.location_city]
    context = ", ".join(part.strip() for part in context_parts if part and part.strip())
    if not context:
        return title
    return f"{title} ({context})"


def _render_esco_occupation_block(job: JobAdExtract) -> None:
    st.markdown("### ESCO Occupation")
    query_text = _build_esco_query(job)
    if not query_text:
        st.info("Kein Jobtitel vorhanden. ESCO-Zuordnung aktuell nicht möglich.")
        st.session_state[SSKey.ESCO_OCCUPATION_CANDIDATES.value] = []
        st.session_state[SSKey.ESCO_OCCUPATION_SELECTED.value] = None
        return

    st.caption(f"Suche mit: `{query_text}`")
    client = EscoClient()
    candidates: list[dict[str, Any]] = []
    try:
        suggest_payload = client.suggest2(text=query_text, type="occupation", limit=8)
        candidates = _extract_occupation_candidates(suggest_payload)
        if len(candidates) < 3:
            search_payload = client.search(text=query_text, type="occupation", limit=8)
            for item in _extract_occupation_candidates(search_payload):
                if all(
                    existing.get("uri") != item.get("uri") for existing in candidates
                ):
                    candidates.append(item)
    except EscoClientError as exc:
        st.warning(f"ESCO-Suche nicht verfügbar: {exc}")
        candidates = []

    st.session_state[SSKey.ESCO_OCCUPATION_CANDIDATES.value] = candidates

    options: list[str] = [_NO_OCCUPATION_OPTION] + [
        str(item.get("title", "—")) for item in candidates
    ]
    stored_selection = st.session_state.get(SSKey.ESCO_OCCUPATION_SELECTED.value)
    selected_title = _NO_OCCUPATION_OPTION
    if isinstance(stored_selection, dict):
        selected_title = str(stored_selection.get("title") or _NO_OCCUPATION_OPTION)
    selected_index = options.index(selected_title) if selected_title in options else 0
    selected_label = st.selectbox(
        "Passende ESCO Occupation wählen",
        options=options,
        index=selected_index,
        key=f"{SSKey.ESCO_OCCUPATION_SELECTED.value}.picker",
        help="Falls nichts passt, bitte explizit 'Keine passende Occupation' wählen.",
    )

    if selected_label == _NO_OCCUPATION_OPTION:
        st.session_state[SSKey.ESCO_OCCUPATION_SELECTED.value] = None
        st.info(
            "Keine ESCO Occupation ausgewählt. Der Flow bleibt trotzdem fortsetzbar."
        )
        return

    selected_candidate = next(
        (
            candidate
            for candidate in candidates
            if str(candidate.get("title")) == selected_label
        ),
        None,
    )
    if not selected_candidate:
        st.session_state[SSKey.ESCO_OCCUPATION_SELECTED.value] = None
        return
    try:
        st.session_state[SSKey.ESCO_OCCUPATION_SELECTED.value] = (
            EscoConceptRef.model_validate(selected_candidate).model_dump()
        )
    except Exception:
        st.session_state[SSKey.ESCO_OCCUPATION_SELECTED.value] = None
        st.warning("Die ESCO-Auswahl konnte nicht validiert werden.")


def render(ctx: WizardContext) -> None:
    job_dict = st.session_state.get(SSKey.JOB_EXTRACT.value)
    plan_dict = st.session_state.get(SSKey.QUESTION_PLAN.value)

    if not job_dict or not plan_dict:
        st.warning("Bitte zuerst im Start-Schritt eine Analyse durchführen.")
        st.button("Zur Startseite", on_click=lambda: ctx.goto("landing"))
        nav_buttons(ctx, disable_next=True)
        return

    job = JobAdExtract.model_validate(job_dict)
    plan = QuestionPlan.model_validate(plan_dict)

    st.header("Jobspec-Übersicht")
    st.caption(
        "Hier prüfst und ergänzt du die extrahierten Inhalte, Gaps und Assumptions, "
        "bevor du in den Schritt 'Unternehmen' wechselst."
    )
    render_error_banner()

    st.markdown(f"**Jobtitel:** {job.job_title or '—'}")
    _render_esco_occupation_block(job)

    with st.sidebar:
        with st.expander("Fragen pro Step", expanded=False):
            _render_question_limits_editor(plan, compact=True)

    render_job_extract_overview(job, plan=plan, show_question_limits=False)

    st.info(
        f"QuestionPlan geladen: {sum(len(s.questions) for s in plan.steps)} Fragen in "
        f"{len(plan.steps)} Steps."
    )
    nav_buttons(ctx)


PAGE = WizardPage(
    key="jobspec_review",
    title_de="Jobspec-Übersicht",
    icon="🧾",
    render=render,
    requires_jobspec=True,
)
