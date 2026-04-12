# wizard_pages/03_team.py
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import streamlit as st

from constants import AnswerType, SSKey
from esco_client import EscoClient, EscoClientError
from schemas import Question, QuestionStep
from state import (
    get_answers,
    has_confirmed_esco_anchor,
    mark_answer_touched,
    set_answer,
)
from ui_components import (
    has_meaningful_value,
    render_esco_explainability,
    render_error_banner,
    render_question_step,
    render_standard_step_review,
)
from ui_layout import render_step_shell
from wizard_pages.base import WizardContext, WizardPage, guard_job_and_plan, nav_buttons


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


def _read_confirmed_team_notes(step: QuestionStep | None) -> str:
    target_question = _resolve_team_notes_question(step)
    if target_question is None:
        return ""
    answers = get_answers()
    return str(answers.get(target_question.id) or "").strip()


def _suggestion_state_key(theme_key: str) -> str:
    return f"team.esco.suggestion.selected.{theme_key}"


def _render_role_context_enrichment(
    *, step: QuestionStep | None, ctx: WizardContext
) -> None:
    st.markdown("#### Role-context enrichment (ESCO)")
    st.caption(
        "Die linke Zone enthält ausschließlich inferred suggestion/context (nicht "
        "nutzungsbestätigt). Erst nach Übernahme landet Inhalt als confirmed selection "
        "in der Team-Notiz."
    )

    occupation = st.session_state.get(SSKey.ESCO_OCCUPATION_SELECTED.value)
    occupation_uri = (
        str(occupation.get("uri") or "").strip() if isinstance(occupation, dict) else ""
    )
    if not occupation_uri:
        st.info(
            "Kein ESCO-Occupation-Anker bestätigt. Gehe zu „Start → Phase C: Semantischen Anker bestätigen“."
        )
        st.button(
            "Zu Start → Phase C",
            key="team.goto_start_phase_c",
            on_click=lambda: ctx.goto("landing"),
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

    inferred_col, confirmed_col = st.columns(2, gap="medium")

    with inferred_col:
        st.write("**Zone 1 · Vorschläge (inferred)**")
        match_confidence = str(
            st.session_state.get(SSKey.ESCO_MATCH_CONFIDENCE.value) or ""
        ).strip()
        match_reason = st.session_state.get(SSKey.ESCO_MATCH_REASON.value)
        match_provenance_raw = st.session_state.get(SSKey.ESCO_MATCH_PROVENANCE.value)
        match_provenance = (
            [str(item) for item in match_provenance_raw if str(item).strip()]
            if isinstance(match_provenance_raw, list)
            else []
        )
        if match_confidence or match_reason or match_provenance:
            render_esco_explainability(
                labels=match_provenance,
                confidence=match_confidence,
                reason=str(match_reason).strip() if match_reason else None,
                caption_prefix="ESCO Occupation match",
            )

        st.caption(
            "Diese Hinweise sind abgeleitet und gelten nicht als bestätigte Fakten."
        )

        selected_theme_labels: list[str] = []
        for theme in themes:
            theme_key = str(theme.get("key") or "").strip()
            label = str(theme.get("label") or "").strip()
            evidence = (
                theme.get("evidence") if isinstance(theme.get("evidence"), list) else []
            )
            if not theme_key or not label:
                continue
            st.markdown(f"- **{label}**")
            if evidence:
                st.caption(f"Signal: {evidence[0]}")
            selected = st.checkbox(
                f"Für Übernahme markieren · {label}",
                key=_suggestion_state_key(theme_key),
            )
            if selected:
                selected_theme_labels.append(label)

        if st.button(
            "Ausgewählte Vorschläge als confirmed selection übernehmen",
            key="team.esco.adopt.selected",
            type="primary",
        ):
            if not selected_theme_labels:
                st.info("Bitte zuerst mindestens einen Vorschlag markieren.")
            else:
                adopted_count = 0
                for label in selected_theme_labels:
                    adopted = _append_context_to_team_notes(
                        step=step,
                        context_line=f"Confirmed selection (ESCO suggestion): {label}",
                    )
                    if adopted:
                        adopted_count += 1
                if adopted_count:
                    st.success(
                        f"{adopted_count} Vorschlag/Vorschläge als confirmed selection übernommen."
                    )
                else:
                    st.info("Keine geeignete Team-Notizfrage zum Übernehmen gefunden.")

    with confirmed_col:
        st.write("**Zone 2 · Confirmed input**")
        current_notes = _read_confirmed_team_notes(step)
        if current_notes:
            st.caption(
                "Bestätigte Inhalte in der kanonischen Team-Antwort (Downstream für Summary/Export)."
            )
            st.text_area(
                "Bestätigte Team-Notiz",
                value=current_notes,
                height=220,
                disabled=True,
                key="team.esco.confirmed.preview",
            )
        else:
            st.info(
                "Noch keine bestätigte Team-Notiz vorhanden. Übernommene Vorschläge "
                "werden hier sichtbar."
            )


def render(ctx: WizardContext) -> None:
    preflight = guard_job_and_plan(ctx)
    if preflight is None:
        return
    job, plan = preflight
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
        show_esco_context = has_confirmed_esco_anchor()
        if step is None or not step.questions:
            st.info(
                "Für diesen Abschnitt wurden keine spezifischen Fragen erzeugt. Du kannst trotzdem weitergehen."
            )
            if show_esco_context:
                _render_role_context_enrichment(step=step, ctx=ctx)
            return
        if not show_esco_context:
            render_question_step(step)
            return
        question_col, context_col = st.columns([2, 1], gap="large")
        with question_col:
            render_question_step(step)
        with context_col:
            _render_role_context_enrichment(step=step, ctx=ctx)

    render_step_shell(
        title="Team",
        subtitle="Teamkontext, Schnittstellen und Zusammenarbeit.",
        outcome_text=(
            "Ein abgestimmtes Bild von Team-Setup, Interfaces und Arbeitsweise, "
            "damit die Rolle im echten Kontext bewertet werden kann."
        ),
        step=step,
        extracted_from_jobspec_slot=_render_extracted_slot,
        extracted_from_jobspec_label="Aus Jobspec extrahiert (Team/Org)",
        main_content_slot=_render_main_slot,
        review_slot=lambda: render_standard_step_review(step),
        footer_slot=lambda: nav_buttons(ctx),
    )


PAGE = WizardPage(
    key="team",
    title_de="Team",
    icon="👥",
    render=render,
    requires_jobspec=True,
)
