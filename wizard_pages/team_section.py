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
    render_question_step,
)
from wizard_pages.base import WizardContext

ROLE_CONTEXT_TITLE = "#### Rollenprofil mit ESCO-Hinweisen ergänzen"
ROLE_CONTEXT_HELP = (
    "Wählen Sie nur Hinweise aus, die für diese konkrete Stelle relevant sind. "
    "Übernommene Hinweise werden in der Team-Notiz gespeichert."
)
ROLE_CONTEXT_BUTTON_LABEL = "Ausgewählte Hinweise übernehmen"
ROLE_CONTEXT_EMPTY_SELECTION = "Bitte zuerst mindestens einen Hinweis auswählen."
ROLE_CONTEXT_NO_THEMES = "Keine belastbaren ESCO-Hinweise für diese Rolle gefunden."
ROLE_CONTEXT_QUALITY_PREFIX = "Trefferqualität: "
ROLE_CONTEXT_REASON_PREFIX = "Warum vorgeschlagen: "
ROLE_CONTEXT_UI_TEXTS: tuple[str, ...] = (
    ROLE_CONTEXT_TITLE,
    ROLE_CONTEXT_HELP,
    ROLE_CONTEXT_BUTTON_LABEL,
    ROLE_CONTEXT_EMPTY_SELECTION,
    ROLE_CONTEXT_NO_THEMES,
    ROLE_CONTEXT_QUALITY_PREFIX,
    ROLE_CONTEXT_REASON_PREFIX,
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


def _esco_quality_label(raw_confidence: object) -> str:
    normalized = str(raw_confidence or "").strip().lower()
    mapping = {"low": "niedrig", "medium": "mittel", "high": "hoch"}
    return mapping.get(normalized, "nicht geladen")


def _esco_reason_labels(provenance: object) -> list[str]:
    if not isinstance(provenance, list):
        return []
    mapping = {
        "synonym/hidden-term match": "ähnlicher Begriff",
        "manually selected by user": "manuell gewählt",
        "exact label match": "exakte Bezeichnung",
    }
    resolved: list[str] = []
    for item in provenance:
        key = str(item or "").strip().lower()
        label = mapping.get(key)
        if label and label not in resolved:
            resolved.append(label)
    return resolved


def render_role_context_enrichment(
    *, step: QuestionStep | None, ctx: WizardContext
) -> None:
    st.markdown(ROLE_CONTEXT_TITLE)
    st.caption(ROLE_CONTEXT_HELP)

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
        st.info(ROLE_CONTEXT_NO_THEMES)
        return

    match_confidence = str(
        st.session_state.get(SSKey.ESCO_MATCH_CONFIDENCE.value) or ""
    ).strip()
    match_provenance_raw = st.session_state.get(SSKey.ESCO_MATCH_PROVENANCE.value)
    st.caption(f"{ROLE_CONTEXT_QUALITY_PREFIX}{_esco_quality_label(match_confidence)}")
    reason_labels = _esco_reason_labels(match_provenance_raw)
    if reason_labels:
        st.caption(f"{ROLE_CONTEXT_REASON_PREFIX}{' / '.join(reason_labels)}")

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
                    f"Hinweise · {group_name}",
                    options=labels,
                    selection_mode="multi",
                    key=f"team.esco.pills.{group_name.casefold().replace(' ', '_')}",
                )
                or []
            )
        else:
            selected_labels = st.multiselect(
                f"Hinweise · {group_name}",
                options=labels,
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
                adopted = _append_context_to_team_notes(
                    step=step,
                    context_line=f"ESCO-Hinweis: {label}",
                )
                if adopted:
                    adopted_count += 1
            if adopted_count:
                st.success(f"{adopted_count} Hinweis(e) übernommen.")
            else:
                st.info("Keine geeignete Team-Notizfrage zum Übernehmen gefunden.")

    current_notes = _read_confirmed_team_notes(step)
    if current_notes:
        st.caption("Übernommene Hinweise sind in der Team-Notiz gespeichert.")


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
