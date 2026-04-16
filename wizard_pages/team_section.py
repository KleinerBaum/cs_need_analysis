from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import streamlit as st

from constants import AnswerType, SSKey
from esco_client import EscoClient, EscoClientError
from schemas import Question, QuestionStep
from state import get_answers, has_confirmed_esco_anchor, mark_answer_touched, set_answer
from ui_components import (
    has_meaningful_value,
    render_error_banner,
    render_esco_explainability,
    render_question_step,
)
from wizard_pages.base import WizardContext


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
            "Zusammenarbeit",
            ("team", "cross-functional", "cross functional", "collaborat", "cooperat"),
        ),
        (
            "communication",
            "Communication",
            "Zusammenarbeit",
            ("communicat", "present", "explain", "report", "facilitat"),
        ),
        (
            "stakeholder",
            "Stakeholder interaction",
            "Stakeholder",
            ("stakeholder", "client", "customer", "partner", "supplier", "interface"),
        ),
        (
            "leadership",
            "Leadership / coordination",
            "Leadership",
            ("lead", "mentor", "coordinate", "supervis", "manage", "organis"),
        ),
        (
            "language",
            "Language-related requirements",
            "Rahmenbedingungen",
            ("language", "multilingual", "bilingual", "translation", "lingu"),
        ),
        (
            "digital_collaboration",
            "Digital collaboration signals",
            "Rahmenbedingungen",
            ("digital", "remote", "virtual", "online", "platform", "software", "tool"),
        ),
    ]

    themes: list[dict[str, Any]] = []
    snippets = list(_walk_text_values(occupation_payload))[:120]
    for key, label, group, keywords in theme_rules:
        if not any(keyword in corpus for keyword in keywords):
            continue
        matched = [
            snippet
            for snippet in snippets
            if any(keyword in snippet.casefold() for keyword in keywords)
        ][:2]
        themes.append({"key": key, "label": label, "group": group, "evidence": matched})
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


def render_role_context_enrichment(
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

    st.caption("Markierte Pillen gelten als ausgewählt.")
    grouped_themes: dict[str, list[dict[str, Any]]] = {}
    for theme in themes:
        group = str(theme.get("group") or "Allgemein").strip() or "Allgemein"
        grouped_themes.setdefault(group, []).append(theme)

    selected_theme_labels: list[str] = []
    selected_theme_details: list[str] = []
    for group_name, group_themes in grouped_themes.items():
        st.markdown(f"**{group_name}**")
        labels = [
            str(theme.get("label") or "").strip()
            for theme in group_themes
            if has_meaningful_value(str(theme.get("label") or ""))
        ]
        if hasattr(st, "pills"):
            selected_labels = (
                st.pills(
                    f"Pillen · {group_name}",
                    options=labels,
                    selection_mode="multi",
                    key=f"team.esco.pills.{group_name.casefold().replace(' ', '_')}",
                )
                or []
            )
        else:
            selected_labels = st.multiselect(
                f"Auswahl · {group_name}",
                options=labels,
                key=f"team.esco.multiselect.{group_name.casefold().replace(' ', '_')}",
            )
        selected_theme_labels.extend(selected_labels)
        for theme in group_themes:
            label = str(theme.get("label") or "").strip()
            if label not in selected_labels:
                continue
            evidence = (
                theme.get("evidence") if isinstance(theme.get("evidence"), list) else []
            )
            if evidence:
                selected_theme_details.append(f"{label} · Signal: {evidence[0]}")

    if st.button(
        "Ausgewählte Vorschläge als confirmed selection übernehmen",
        key="team.esco.adopt.selected",
        type="primary",
        width="stretch",
    ):
        if not selected_theme_labels:
            st.info("Bitte zuerst mindestens eine Pille markieren.")
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

    if selected_theme_details:
        st.caption("Ausgewählte Evidenz-Signale:")
        for detail in selected_theme_details:
            st.write(f"- {detail}")

    st.write("**Zone 2 · Confirmed input**")
    current_notes = _read_confirmed_team_notes(step)
    if current_notes:
        st.caption(
            "Bestätigte Inhalte in der kanonischen Team-Antwort (Downstream für Summary/Export)."
        )
        st.text_area(
            "Bestätigte Team-Notiz",
            value=current_notes,
            height=180,
            disabled=True,
            key="team.esco.confirmed.preview",
        )
    else:
        st.info(
            "Noch keine bestätigte Team-Notiz vorhanden. Übernommene Vorschläge "
            "werden hier sichtbar."
        )


def render_team_questions_with_optional_esco_context(
    *,
    step: QuestionStep | None,
    ctx: WizardContext,
    show_error_banner: bool,
) -> None:
    if show_error_banner:
        render_error_banner()

    show_esco_context = has_confirmed_esco_anchor()
    if step is None or not step.questions:
        st.info(
            "Für diesen Abschnitt wurden keine spezifischen Fragen erzeugt. Du kannst trotzdem weitergehen."
        )
        if show_esco_context:
            render_role_context_enrichment(step=step, ctx=ctx)
        return

    render_question_step(step)
    if show_esco_context:
        render_role_context_enrichment(step=step, ctx=ctx)
