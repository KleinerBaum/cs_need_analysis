# wizard_pages/03_team.py
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import streamlit as st

from constants import AnswerType, SSKey
from esco_client import EscoClient, EscoClientError
from schemas import JobAdExtract, Question, QuestionPlan, QuestionStep
from state import get_answers, mark_answer_touched, set_answer
from ui_components import (
    has_meaningful_value,
    render_error_banner,
    render_question_step,
)
from ui_layout import render_step_shell
from wizard_pages.base import WizardContext, WizardPage, nav_buttons


def _walk_text_values(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        cleaned = " ".join(value.split()).strip()
        if cleaned:
            yield cleaned
    elif isinstance(value, dict):
        for nested in value.values():
            yield from _walk_text_values(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_text_values(nested)


def _build_role_context_themes(
    occupation_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    corpus = " || ".join(_walk_text_values(occupation_payload)).casefold()
    if not corpus:
        return []

    theme_rules = [
        (
            "collaboration",
            "Collaboration",
            ("team", "cross-functional", "cross functional", "collaborat", "cooperat"),
        ),
        (
            "communication",
            "Communication",
            ("communicat", "present", "explain", "report", "facilitat"),
        ),
        (
            "stakeholder",
            "Stakeholder interaction",
            ("stakeholder", "client", "customer", "partner", "supplier", "interface"),
        ),
        (
            "leadership",
            "Leadership / coordination",
            ("lead", "mentor", "coordinate", "supervis", "manage", "organis"),
        ),
        (
            "language",
            "Language-related requirements",
            ("language", "multilingual", "bilingual", "translation", "lingu"),
        ),
        (
            "digital_collaboration",
            "Digital collaboration signals",
            ("digital", "remote", "virtual", "online", "platform", "software", "tool"),
        ),
    ]

    themes: list[dict[str, Any]] = []
    snippets = list(_walk_text_values(occupation_payload))[:120]
    for key, label, keywords in theme_rules:
        if not any(keyword in corpus for keyword in keywords):
            continue
        matched = [
            snippet
            for snippet in snippets
            if any(keyword in snippet.casefold() for keyword in keywords)
        ][:2]
        themes.append({"key": key, "label": label, "evidence": matched})
    return themes


def _resolve_team_notes_question(step: QuestionStep | None) -> Question | None:
    if step is None:
        return None
    for question in step.questions:
        if question.answer_type in {AnswerType.LONG_TEXT, AnswerType.SHORT_TEXT}:
            return question
    return None


def _append_context_to_team_notes(
    *, step: QuestionStep | None, context_line: str
) -> bool:
    target_question = _resolve_team_notes_question(step)
    if target_question is None:
        return False
    answers = get_answers()
    previous = answers.get(target_question.id)
    current = str(previous or "").strip()
    addition = context_line.strip()
    if not addition:
        return False
    if addition.casefold() in current.casefold():
        return True
    updated = f"{current}\n- {addition}".strip() if current else f"- {addition}"
    set_answer(target_question.id, updated)
    mark_answer_touched(target_question.id, previous, updated)
    return True


def _render_role_context_enrichment(*, step: QuestionStep | None) -> None:
    st.markdown("#### Role-context enrichment (ESCO)")
    st.caption(
        "Inferred context from ESCO occupation content. This is guidance for team collaboration topics, "
        "not a hard requirement source."
    )

    occupation = st.session_state.get(SSKey.ESCO_OCCUPATION_SELECTED.value)
    occupation_uri = (
        str(occupation.get("uri") or "").strip() if isinstance(occupation, dict) else ""
    )
    if not occupation_uri:
        st.info(
            "Kein ESCO-Occupation-Anker bestätigt. Ergänze ihn im Schritt „Identifizierte Informationen“."
        )
        return

    client = EscoClient()
    try:
        payload = client.resource_occupation(uri=occupation_uri)
    except EscoClientError as exc:
        st.warning(f"ESCO-Kontext aktuell nicht verfügbar: {exc}")
        return

    themes = _build_role_context_themes(payload)
    if not themes:
        st.info("Keine belastbaren transversal themes aus ESCO ableitbar.")
        return

    st.write("**Inferred collaboration context:**")
    for theme in themes:
        label = str(theme.get("label") or "").strip()
        evidence = (
            theme.get("evidence") if isinstance(theme.get("evidence"), list) else []
        )
        st.markdown(f"- **{label}** _(inferred)_")
        if evidence:
            st.caption(f"Signal: {evidence[0]}")
        adopt_label = f"Als Team-Notiz übernehmen · {label}"
        if st.button(adopt_label, key=f"team.esco.adopt.{theme.get('key')}"):
            adopted = _append_context_to_team_notes(
                step=step,
                context_line=f"ESCO context signal: {label}",
            )
            if adopted:
                st.success("Kontext in Team-Notiz übernommen.")
            else:
                st.info("Keine geeignete Team-Notizfrage zum Übernehmen gefunden.")


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
    step = next((s for s in plan.steps if s.step_key == "team"), None)

    def _render_extracted_slot() -> None:
        extracted_rows = [
            ("Department", job.department_name),
            ("Reports to", job.reports_to),
            ("Direct reports", job.direct_reports_count),
        ]
        shown = False
        for label, value in extracted_rows:
            if has_meaningful_value(value):
                st.write(f"**{label}:** {value}")
                shown = True
        if not shown:
            st.info(
                "Keine verlässlichen Werte erkannt. Details siehe Gaps/Assumptions."
            )

    def _render_main_slot() -> None:
        render_error_banner()
        st.write(
            "Hier geht es um Team-Setup, Schnittstellen, Arbeitsmodus (hybrid/remote), aktuelle Herausforderungen "
            "und warum diese Rolle für das Team wichtig ist."
        )
        if step is None or not step.questions:
            st.info(
                "Für diesen Abschnitt wurden keine spezifischen Fragen erzeugt. Du kannst trotzdem weitergehen."
            )
            _render_role_context_enrichment(step=step)
            return
        question_col, context_col = st.columns([2, 1], gap="large")
        with question_col:
            render_question_step(step)
        with context_col:
            _render_role_context_enrichment(step=step)

    render_step_shell(
        title="Team",
        subtitle="Teamkontext, Schnittstellen und Zusammenarbeit.",
        step=step,
        extracted_from_jobspec_slot=_render_extracted_slot,
        extracted_from_jobspec_label="Aus Jobspec extrahiert (Team/Org)",
        main_content_slot=_render_main_slot,
        footer_slot=lambda: nav_buttons(ctx),
    )


PAGE = WizardPage(
    key="team",
    title_de="Team",
    icon="👥",
    render=render,
    requires_jobspec=True,
)
