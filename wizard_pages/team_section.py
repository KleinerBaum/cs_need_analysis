from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

import streamlit as st

from constants import AnswerType, SSKey
from esco_client import EscoClient, EscoClientError
from schemas import Question, QuestionStep
from state import get_answers, get_esco_semantic_context, mark_answer_touched, set_answer
from ui_components import (
    has_meaningful_value,
    render_error_banner,
    render_question_step,
)
from wizard_pages.base import WizardContext

ROLE_CONTEXT_TITLE = "#### Rollenprofil mit ESCO-Kontext ergänzen"
ROLE_CONTEXT_BUTTON_LABEL = "Ausgewählten Kontext übernehmen"
ROLE_CONTEXT_EMPTY_SELECTION = "Bitte zuerst mindestens einen Kontext auswählen."
ROLE_CONTEXT_NO_THEMES = "Kein belastbarer ESCO-Kontext für diese Rolle gefunden."
ROLE_CONTEXT_UI_TEXTS: tuple[str, ...] = (
    ROLE_CONTEXT_TITLE,
    ROLE_CONTEXT_BUTTON_LABEL,
    ROLE_CONTEXT_EMPTY_SELECTION,
    ROLE_CONTEXT_NO_THEMES,
)


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
            "Zusammenarbeit / Kommunikation",
            "Zusammenarbeit & Kommunikation",
            ("team", "cross-functional", "cross functional", "collaborat", "cooperat"),
        ),
        (
            "communication",
            "Austausch mit Stakeholdern",
            "Zusammenarbeit & Kommunikation",
            ("communicat", "present", "explain", "report", "facilitat"),
        ),
        (
            "stakeholder",
            "Abstimmung mit Kunden / Stakeholdern",
            "Zusammenarbeit & Kommunikation",
            ("stakeholder", "client", "customer", "partner", "supplier", "interface"),
        ),
        (
            "leadership",
            "Führung / Koordination",
            "Führung & Koordination",
            ("lead", "mentor", "coordinate", "supervis", "manage", "organis"),
        ),
        (
            "language",
            "Sprachanforderungen",
            "Arbeitsumfeld & Rahmenbedingungen",
            ("language", "multilingual", "bilingual", "translation", "lingu"),
        ),
        (
            "digital_collaboration",
            "Digitales / hybrides Arbeiten",
            "Arbeitsumfeld & Rahmenbedingungen",
            ("digital", "remote", "virtual", "online", "platform", "software", "tool"),
        ),
    ]

    themes: list[dict[str, Any]] = []
    seen_labels: set[tuple[str, str]] = set()
    snippets = list(_walk_text_values(occupation_payload))[:120]
    for key, label, group, keywords in theme_rules:
        if not any(keyword in corpus for keyword in keywords):
            continue
        matched = [
            snippet
            for snippet in snippets
            if any(keyword in snippet.casefold() for keyword in keywords)
        ][:2]
        dedupe_key = (group.casefold(), label.casefold())
        if dedupe_key in seen_labels:
            continue
        seen_labels.add(dedupe_key)
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
    *,
    step: QuestionStep | None,
    ctx: WizardContext,
    adopt_context_callback: Callable[[str], bool] | None = None,
) -> None:
    st.markdown(ROLE_CONTEXT_TITLE)

    semantic_context = get_esco_semantic_context()
    occupation_uri = (
        semantic_context.primary_anchor.uri
        if semantic_context.primary_anchor is not None
        else ""
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
        st.info(ROLE_CONTEXT_NO_THEMES)
        return

    grouped_themes: dict[str, list[dict[str, Any]]] = {}
    for theme in themes:
        group = str(theme.get("group") or "Allgemein").strip() or "Allgemein"
        grouped_themes.setdefault(group, []).append(theme)

    selected_theme_labels: list[str] = []
    ordered_groups = [
        "Zusammenarbeit & Kommunikation",
        "Führung & Koordination",
        "Arbeitsumfeld & Rahmenbedingungen",
    ]
    for group_name in ordered_groups:
        group_themes = grouped_themes.get(group_name, [])
        if not group_themes:
            continue
        st.markdown(f"**{group_name}**")
        labels = []
        for theme in group_themes:
            label = str(theme.get("label") or "").strip()
            if has_meaningful_value(label) and label not in labels:
                labels.append(label)
        if not labels:
            continue
        if hasattr(st, "pills"):
            selected_labels = (
                st.pills(
                    group_name,
                    options=labels,
                    selection_mode="multi",
                    label_visibility="collapsed",
                    key=f"team.esco.pills.{group_name.casefold().replace(' ', '_')}",
                )
                or []
            )
        else:
            selected_labels = st.multiselect(
                group_name,
                options=labels,
                label_visibility="collapsed",
                key=f"team.esco.multiselect.{group_name.casefold().replace(' ', '_')}",
            )
        selected_theme_labels.extend(
            label for label in selected_labels if label not in selected_theme_labels
        )

    if st.button(
        ROLE_CONTEXT_BUTTON_LABEL,
        key="team.esco.adopt.selected",
        type="primary",
        width="stretch",
    ):
        if not selected_theme_labels:
            st.info(ROLE_CONTEXT_EMPTY_SELECTION)
        else:
            adopted_count = 0
            for label in selected_theme_labels:
                context_line = f"ESCO-Kontext: {label}"
                adopted = (
                    adopt_context_callback(context_line)
                    if adopt_context_callback is not None
                    else _append_context_to_team_notes(
                        step=step,
                        context_line=context_line,
                    )
                )
                if adopted:
                    adopted_count += 1
            if adopted_count:
                st.success(f"{adopted_count} Kontextwert(e) übernommen.")
            else:
                st.info("Keine geeignete Team-Notizfrage zum Übernehmen gefunden.")

    current_notes = (
        ""
        if adopt_context_callback is not None
        else _read_confirmed_team_notes(step)
    )
    if current_notes:
        st.caption("Übernommener Kontext ist in der Team-Notiz gespeichert.")


def render_team_questions_with_optional_esco_context(
    *,
    step: QuestionStep | None,
    ctx: WizardContext,
    show_error_banner: bool,
) -> None:
    if show_error_banner:
        render_error_banner()

    show_esco_context = get_esco_semantic_context().can_use_task_suggestions
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
