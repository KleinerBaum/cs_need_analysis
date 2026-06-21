# ui_inputs.py
"""Question input and lightweight UI input helpers."""

from __future__ import annotations

import re
from datetime import date
from collections.abc import Mapping, Sequence
from html import escape
from typing import Any, Dict, Literal, Optional, TypedDict

import streamlit as st

from safe_html import render_static_html
from constants import (
    AnswerType,
    QUESTION_IMPACT_TARGET_BRIEF,
    QUESTION_IMPACT_TARGET_EXPORT,
    QUESTION_IMPACT_TARGET_INTERVIEW,
    QUESTION_IMPACT_TARGET_SALARY,
    QUESTION_IMPACT_TARGET_SKILLS,
    QUESTION_GROUP_DISPLAY_LABELS_DE,
    SSKey,
    WIDGET_KEY_PREFIX,
)
from job_extract_review_helpers import has_meaningful_value
from question_dependencies import should_show_question
from question_progress import compute_question_progress
from schemas import (
    LanguageRequirement,
    Question,
    QuestionOption,
    QuestionStep,
    question_option_label_map,
)
from state import (
    get_answer_meta,
    get_answers,
    mark_answer_touched,
    set_answer,
)
from step_payload import build_step_payload_from_state

PILLS_GRID_COLUMNS = 3
QUESTION_PROVENANCE_TEXT_MAX_CHARS = 180
SECTION_PROVENANCE_TEXT_MAX_CHARS = 140
QUESTION_IMPACT_LABELS: dict[str, str] = {
    QUESTION_IMPACT_TARGET_BRIEF: "Brief",
    QUESTION_IMPACT_TARGET_SALARY: "Salary",
    QUESTION_IMPACT_TARGET_SKILLS: "Skills",
    QUESTION_IMPACT_TARGET_INTERVIEW: "Interview",
    QUESTION_IMPACT_TARGET_EXPORT: "Export",
}
QUESTION_ACQUISITION_COST_LABELS: dict[str, str] = {
    "low": "geringer Aufwand",
    "medium": "mittlerer Aufwand",
    "high": "hoher Aufwand",
}
QUESTION_PROVENANCE_SOURCE_LABELS: dict[str, str] = {
    "ESCO context": "ESCO",
    "Occupation context": "Kontext",
    "Base intake plan": "Offen",
}
QUESTION_ADJUSTMENT_LABELS: dict[str, str] = {
    "selected by occupation overlay": "Kontext-Overlay",
    "demoted by relevance filter": "Relevanzfilter",
}

def inject_pills_grid_css() -> None:
    _render_html_block(
        f"""
        <style>
        div[data-testid="stPills"] div[role="group"],
        div[data-testid="stPills"] div[role="radiogroup"] {{
            display: grid;
            grid-template-columns: repeat({PILLS_GRID_COLUMNS}, minmax(0, 1fr));
            gap: 0.5rem;
        }}
        div[data-testid="stPills"] div[role="group"] label,
        div[data-testid="stPills"] div[role="radiogroup"] label {{
            width: 100%;
        }}
        div[data-testid="stPills"] div[role="group"] label > div,
        div[data-testid="stPills"] div[role="radiogroup"] label > div {{
            width: 100%;
            justify-content: flex-start;
            white-space: normal;
        }}
        @media (max-width: 720px) {{
            div[data-testid="stPills"] div[role="group"],
            div[data-testid="stPills"] div[role="radiogroup"] {{
                grid-template-columns: 1fr;
            }}
        }}
        </style>
        """
    )


def _inject_esco_single_select_pills_css() -> None:
    inject_pills_grid_css()


def _render_html_block(html: str) -> None:
    render_html = getattr(st, "html", None)
    if callable(render_html):
        render_html(html)
        return
    render_static_html(html, streamlit_module=st)


class QuestionProvenanceDisplay(TypedDict):
    sources: list[str]
    why: str
    impacts: list[str]
    adjustments: list[str]
    effort: str
    info_gain: str


QuestionInputResult = tuple[str, Any, Any]

def _dedupe_labels(values: Sequence[str]) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()
    for raw_value in values:
        label = str(raw_value or "").strip()
        key = label.casefold()
        if not label or key in seen:
            continue
        labels.append(label)
        seen.add(key)
    return labels


def _safe_question_provenance_text(
    value: object,
    *,
    max_chars: int = QUESTION_PROVENANCE_TEXT_MAX_CHARS,
) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        return ""
    redacted = re.sub(r"(?i)\b(sk-[A-Za-z0-9_-]{8,})\b", "[redacted-secret]", text)
    redacted = re.sub(
        r"(?i)\bbearer\s+[A-Za-z0-9._-]+",
        "Bearer [redacted]",
        redacted,
    )
    redacted = re.sub(
        r"(?i)\b(api[_-]?key|token|secret|password)\s*[:=]\s*\S+",
        r"\1=[redacted]",
        redacted,
    )
    redacted = re.sub(r"https?://\S+", "[redacted-url]", redacted)
    redacted = re.sub(r"\buri:[A-Za-z0-9:._/\-]+\b", "[redacted-reference]", redacted)
    redacted = re.sub(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        "[redacted-contact]",
        redacted,
        flags=re.I,
    )
    redacted = re.sub(
        r"(?<!\w)(?:\+?\d[\d\s()./-]{7,}\d)(?!\w)",
        "[redacted-contact]",
        redacted,
    )
    if len(redacted) <= max_chars:
        return redacted
    return f"{redacted[: max_chars - 3].rstrip()}..."


def _load_question_flow_provenance_payload(
    provenance: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    if isinstance(provenance, Mapping):
        return provenance
    raw_provenance = st.session_state.get(SSKey.QUESTION_FLOW_PROVENANCE.value, {})
    return raw_provenance if isinstance(raw_provenance, Mapping) else {}


def _provenance_string_list(
    provenance: Mapping[str, Any],
    key: str,
) -> list[str]:
    raw_values = provenance.get(key)
    if not isinstance(raw_values, list):
        return []
    return [str(item).strip() for item in raw_values if str(item).strip()]


def _question_has_source_uris(
    question: Question,
    provenance: Mapping[str, Any],
) -> bool:
    source_uris = provenance.get("source_uris_by_question_id")
    return isinstance(source_uris, Mapping) and question.id in source_uris


def _question_source_labels(
    question: Question,
    provenance: Mapping[str, Any],
) -> list[str]:
    injected_ids = set(_provenance_string_list(provenance, "injected_question_ids"))
    source_labels: list[str] = []
    question_id = str(question.id or "")
    if _question_has_source_uris(question, provenance) or question_id.startswith(
        "ctx_esco_"
    ):
        source_labels.append("ESCO context")
    if question.id in injected_ids or question_id.startswith("ctx_"):
        source_labels.append("Occupation context")
    if not source_labels:
        source_labels.append("Base intake plan")
    return _dedupe_labels(source_labels)


def _compact_question_source_label(label: str) -> str:
    return QUESTION_PROVENANCE_SOURCE_LABELS.get(label, label)


def _compact_question_adjustment_label(label: str) -> str:
    return QUESTION_ADJUSTMENT_LABELS.get(label, label)


def _question_adjustment_labels(
    question: Question,
    provenance: Mapping[str, Any],
) -> list[str]:
    labels: list[str] = []
    injected_ids = set(_provenance_string_list(provenance, "injected_question_ids"))
    demoted_ids = set(_provenance_string_list(provenance, "demoted_question_ids"))
    if question.id in injected_ids:
        labels.append("selected by occupation overlay")
    if question.id in demoted_ids:
        labels.append("demoted by relevance filter")
    return labels


def _question_impact_labels(question: Question) -> list[str]:
    labels = [
        QUESTION_IMPACT_LABELS.get(str(target or "").strip().lower(), "")
        for target in question.impact_targets
    ]
    cleaned = _dedupe_labels([label for label in labels if label])
    return cleaned or ["Vacancy workflow"]


def _fallback_question_why(question: Question) -> str:
    if question.required:
        return "Required for step readiness and handoff completeness."
    if question.fact_key:
        return "Collects a canonical vacancy fact for downstream artifacts."
    if question.group_key:
        group_label = str(question.group_key).replace("_", " ").strip().lower()
        if group_label:
            return f"Completes the {group_label} section."
    return "Keeps the vacancy intake complete."


def _build_question_provenance_display(
    question: Question,
    provenance: Mapping[str, Any] | None = None,
) -> QuestionProvenanceDisplay:
    provenance_payload = _load_question_flow_provenance_payload(provenance)
    info_gain = ""
    if question.info_gain_score is not None:
        info_gain = f"{round(float(question.info_gain_score) * 100)}% Info-Gain"
    return {
        "sources": _question_source_labels(question, provenance_payload),
        "why": _safe_question_provenance_text(
            question.rationale or _fallback_question_why(question)
        ),
        "impacts": _question_impact_labels(question),
        "adjustments": _question_adjustment_labels(question, provenance_payload),
        "effort": QUESTION_ACQUISITION_COST_LABELS.get(
            str(question.acquisition_cost or "").strip().lower(),
            "",
        ),
        "info_gain": info_gain,
    }


def _join_provenance_labels(labels: Sequence[str], *, max_items: int = 3) -> str:
    cleaned = _dedupe_labels(labels)
    if not cleaned:
        return "not specified"
    if len(cleaned) <= max_items:
        return ", ".join(cleaned)
    return f"{', '.join(cleaned[:max_items])} +{len(cleaned) - max_items} more"


def _join_compact_question_provenance_labels(
    labels: Sequence[str],
    *,
    max_items: int = 3,
) -> str:
    return _join_provenance_labels(
        [_compact_question_source_label(label) for label in labels],
        max_items=max_items,
    )


def _format_question_provenance_caption(
    display: QuestionProvenanceDisplay,
    *,
    max_why_chars: int = QUESTION_PROVENANCE_TEXT_MAX_CHARS,
) -> str:
    why = _safe_question_provenance_text(display["why"], max_chars=max_why_chars)
    source = _join_compact_question_provenance_labels(display["sources"])
    impact = _join_provenance_labels(display["impacts"])
    if not why:
        return f"Herkunft: {source} · Für: {impact}"
    return f"Herkunft: {source} · Warum: {why} · Für: {impact}"


def _build_section_provenance_display(
    *,
    section_title: str,
    questions: Sequence[Question],
    provenance: Mapping[str, Any] | None = None,
) -> QuestionProvenanceDisplay:
    question_displays = [
        _build_question_provenance_display(question, provenance)
        for question in questions
    ]
    sources = _dedupe_labels(
        [source for display in question_displays for source in display["sources"]]
    )
    impacts = _dedupe_labels(
        [impact for display in question_displays for impact in display["impacts"]]
    )
    adjustments = _dedupe_labels(
        [
            adjustment
            for display in question_displays
            for adjustment in display["adjustments"]
        ]
    )
    rationales = _dedupe_labels(
        [display["why"] for display in question_displays if display["why"]]
    )
    if len(rationales) == 1:
        why = rationales[0]
    elif rationales:
        why = f"{rationales[0]} (+{len(rationales) - 1} more reasons)"
    else:
        why = f"Groups related questions for {section_title}."
    return {
        "sources": sources or ["Base intake plan"],
        "why": _safe_question_provenance_text(
            why, max_chars=SECTION_PROVENANCE_TEXT_MAX_CHARS
        ),
        "impacts": impacts or ["Vacancy workflow"],
        "adjustments": adjustments,
        "effort": "",
        "info_gain": "",
    }


def _render_section_provenance(
    *,
    section_title: str,
    questions: Sequence[Question],
    ui_mode: str,
    provenance: Mapping[str, Any] | None,
) -> None:
    del section_title, questions, ui_mode, provenance
    return


def _render_question_provenance(
    question: Question,
    *,
    ui_mode: str,
    provenance: Mapping[str, Any] | None,
) -> None:
    del question, ui_mode, provenance
    return


def _question_widget_help(
    question: Question,
    *,
    provenance: Mapping[str, Any] | None,
) -> str | None:
    parts: list[str] = []
    if question.help:
        parts.append(str(question.help).strip())
    ui_mode = str(st.session_state.get(SSKey.UI_MODE.value, "standard")).strip().lower()
    show_provenance = ui_mode == "expert" or bool(
        st.session_state.get(SSKey.DEBUG.value, False)
    )
    if show_provenance:
        provenance_text = _format_question_provenance_caption(
            _build_question_provenance_display(question, provenance),
            max_why_chars=120,
        )
        if provenance_text:
            parts.append(f"Provenienz: {provenance_text}")
    return "\n\n".join(part for part in parts if part) or None
_OTHER_OPTION = "Sonstiges"
_OTHER_PREFIX = f"{_OTHER_OPTION}: "
_LANGUAGE_OPTIONS = [
    "Deutsch",
    "Englisch",
    "Französisch",
    "Spanisch",
    "Italienisch",
    "Niederländisch",
    "Polnisch",
    "Portugiesisch",
]
_CEFR_OPTIONS = ["A1", "A2", "B1", "B2", "C1", "C2"]


def _question_option_entries(question: Question) -> list[tuple[str, str]]:
    label_map = question_option_label_map(question)
    entries: list[tuple[str, str]] = []
    used_labels: set[str] = set()
    for raw_option in question.options or []:
        if isinstance(raw_option, QuestionOption):
            option_value = raw_option.value.strip()
        else:
            option_value = str(raw_option).strip()
        if not option_value:
            continue
        option_label = label_map.get(option_value, option_value).strip() or option_value
        deduped_label = option_label
        if deduped_label in used_labels:
            deduped_label = f"{option_label} ({option_value})"
        used_labels.add(deduped_label)
        entries.append((option_value, deduped_label))
    return entries


def _set_session_flag_true(flag_key: str) -> None:
    st.session_state[flag_key] = True
def _get_step_group_rules(step_key: str) -> list[tuple[str, tuple[str, ...]]]:
    """Return ordered grouping rules per step for question rendering."""
    rules: dict[str, list[tuple[str, tuple[str, ...]]]] = {
        "company": [
            (
                "Unternehmenskontext & Business",
                (
                    "unterneh",
                    "company",
                    "markt",
                    "business",
                    "produkt",
                    "mission",
                    "strategie",
                ),
            ),
            (
                "Setup, Zusammenarbeit & Rahmen",
                (
                    "team",
                    "stakeholder",
                    "schnittstelle",
                    "zusammenarbeit",
                    "remote",
                    "standort",
                    "rahmen",
                ),
            ),
        ],
        "team": [
            (
                "Teamstruktur & Verantwortungen",
                (
                    "team",
                    "lead",
                    "reports",
                    "verantwort",
                    "rolle",
                    "hierarchie",
                    "organ",
                ),
            ),
            (
                "Arbeitsweise & Zusammenarbeit",
                (
                    "arbeits",
                    "hybrid",
                    "remote",
                    "schnittstelle",
                    "kommunikation",
                    "prozesse",
                    "kultur",
                ),
            ),
        ],
        "role_tasks": [
            (
                "Rollen-Detailfragen",
                (
                    "rolle",
                    "role",
                    "scope",
                    "position",
                    "mission",
                ),
            ),
            (
                "Verantwortung & Scope",
                (
                    "aufgabe",
                    "scope",
                    "deliver",
                    "projekt",
                    "verantwort",
                    "ergebnis",
                ),
            ),
            (
                "Erfolgskriterien",
                (
                    "erfolg",
                    "kpi",
                    "ziel",
                    "ok",
                    "outcome",
                    "messbar",
                    "impact",
                ),
            ),
            (
                "Zusammenarbeit",
                (
                    "stakeholder",
                    "zusammenarbeit",
                    "schnittstelle",
                    "entscheidung",
                    "prior",
                    "kommunikation",
                ),
            ),
        ],
        "skills": [
            (
                "Muss-Kriterien",
                (
                    "must",
                    "pflicht",
                    "skill",
                    "kompetenz",
                    "anforder",
                ),
            ),
            (
                "Nice-to-have",
                (
                    "nice",
                    "optional",
                    "plus",
                    "lernen",
                    "potenzial",
                    "entwicklung",
                    "soft",
                ),
            ),
            (
                "Tech-Stack & Tools",
                (
                    "tech",
                    "tool",
                    "stack",
                    "framework",
                    "programmiersprache",
                    "software",
                ),
            ),
            (
                "Sprachen & Zertifikate",
                (
                    "sprache",
                    "language",
                    "zert",
                    "cert",
                    "erfahrung",
                ),
            ),
        ],
        "benefits": [
            (
                "Arbeitsmodell & Vergütung",
                (
                    "gehalt",
                    "salary",
                    "bonus",
                    "vertrag",
                    "arbeitszeit",
                    "stunden",
                    "kondition",
                ),
            ),
            (
                "Benefits-Präferenzen",
                (
                    "benefit",
                    "remote",
                    "hybrid",
                    "urlaub",
                    "learning",
                    "relocation",
                    "flex",
                ),
            ),
            (
                "Rahmenbedingungen",
                (
                    "rahmen",
                    "beding",
                    "reise",
                    "onsite",
                    "arbeitsort",
                    "start",
                    "verfügbarkeit",
                ),
            ),
        ],
        "interview": [
            (
                "Interne Ansprechpartner & Prozesssteuerung",
                (
                    "ansprech",
                    "hiring manager",
                    "recruit",
                    "intern",
                    "entscheidung",
                    "freigabe",
                    "prozess",
                ),
            ),
            (
                "Kandidaten-Inputs & Deliverables",
                (
                    "cv",
                    "lebenslauf",
                    "portfolio",
                    "gehalt",
                    "case",
                    "unterlage",
                    "deliver",
                ),
            ),
            (
                "Bewerbungsschritte, Timeline & Kommunikation",
                (
                    "schritt",
                    "interview",
                    "timeline",
                    "stufe",
                    "feedback",
                    "termin",
                    "kommunikation",
                ),
            ),
        ],
    }
    return rules.get(step_key, [])


def _matches_keywords(question: Question, keywords: Sequence[str]) -> bool:
    haystack = " ".join(
        [
            (question.id or ""),
            (question.label or ""),
            (question.help or ""),
            (question.rationale or ""),
        ]
    ).lower()
    return any(keyword.lower() in haystack for keyword in keywords)


def _question_group_title(group_key: str) -> str:
    key = str(group_key or "").strip()
    if not key:
        return "Weitere Fragen"
    configured = QUESTION_GROUP_DISPLAY_LABELS_DE.get(key)
    if configured:
        return configured
    return key.replace("_", " ").title()


def _group_questions(
    step: QuestionStep, questions: list[Question]
) -> list[tuple[str, list[Question]]]:
    explicit_groups: dict[str, list[Question]] = {}
    explicit_order: list[str] = []
    heuristic_candidates: list[Question] = []
    for question in questions:
        if question.group_key:
            key = question.group_key.strip()
            if key:
                if key not in explicit_groups:
                    explicit_groups[key] = []
                    explicit_order.append(key)
                explicit_groups[key].append(question)
                continue
        heuristic_candidates.append(question)

    grouped: list[tuple[str, list[Question]]] = []
    for key in explicit_order:
        grouped.append((_question_group_title(key), explicit_groups[key]))

    remaining = heuristic_candidates[:]
    for group_title, keywords in _get_step_group_rules(step.step_key):
        matched = [q for q in remaining if _matches_keywords(q, keywords)]
        if matched:
            grouped.append((group_title, matched))
            remaining = [q for q in remaining if q not in matched]
    if remaining:
        grouped.append(("Weitere Fragen", remaining))
    return grouped


def _render_questions_two_columns(
    questions: list[Question],
    answers: Dict[str, Any],
    *,
    widget_key_prefix: str = WIDGET_KEY_PREFIX,
    persist: bool = True,
    ui_mode: str = "standard",
    provenance: Mapping[str, Any] | None = None,
    context_mode: Literal["default", "compact"] = "default",
) -> list[QuestionInputResult]:
    results: list[QuestionInputResult] = []
    col_left, col_right = st.columns(2, gap="large")
    for index, question in enumerate(questions):
        target_col = col_left if index % 2 == 0 else col_right
        with target_col:
            results.append(
                _render_question(
                    question,
                    answers,
                    widget_key_prefix=widget_key_prefix,
                    persist=persist,
                    ui_mode=ui_mode,
                    provenance=provenance,
                    context_mode=context_mode,
                )
            )
    return results


def _split_core_and_detail_questions(
    questions: list[Question],
) -> tuple[list[Question], list[Question]]:
    max_core_questions = 4
    if not questions:
        return [], []

    core_questions: list[Question] = []
    essential_questions = [
        question
        for question in questions
        if question.priority == "core" or question.required
    ]

    for question in essential_questions:
        if question in core_questions:
            continue
        core_questions.append(question)
        if len(core_questions) >= max_core_questions:
            break

    for question in questions:
        if len(core_questions) >= max_core_questions:
            break
        if question in core_questions:
            continue
        core_questions.append(question)

    detail_questions = [
        question for question in questions if question not in core_questions
    ]
    return core_questions, detail_questions


def render_question_step(
    step: QuestionStep,
    *,
    context_mode: Literal["default", "compact"] = "default",
    form_key_suffix: str | None = None,
) -> None:
    answers = get_answers()
    answer_meta = get_answer_meta()
    ui_mode_raw = st.session_state.get(SSKey.UI_MODE.value, "standard")
    ui_mode = str(ui_mode_raw).strip().lower()
    if ui_mode not in {"quick", "standard", "expert"}:
        ui_mode = "standard"
        st.session_state[SSKey.UI_MODE.value] = ui_mode

    if step.description_de:
        st.caption(step.description_de)

    all_questions = _sort_questions_for_progressive_disclosure(step.questions)
    step_payload = build_step_payload_from_state(
        step,
        questions=all_questions,
        session_state=st.session_state,
        answers=answers,
        answer_meta=answer_meta,
        visibility_predicate=should_show_question,
    )
    visible_questions = step_payload["visible_questions"]
    hidden_questions_count = step_payload["hidden_questions_count"]
    dependency_hidden_count = step_payload["dependency_hidden_questions_count"]
    adaptive_hidden_count = step_payload["adaptive_hidden_questions_count"]
    answered_lookup = step_payload["answered_lookup"]
    hidden_scope_caption = _question_hidden_scope_caption(
        dependency_hidden_count=dependency_hidden_count,
        adaptive_hidden_count=adaptive_hidden_count,
    )

    if not visible_questions:
        st.info(
            "Aktuell sind keine Fragen sichtbar. Prüfe vorherige Antworten oder fahre mit dem nächsten Schritt fort."
        )
        if hidden_questions_count > 0 and hidden_scope_caption:
            st.caption(hidden_scope_caption)
        return

    if hidden_scope_caption:
        st.caption(hidden_scope_caption)

    grouped_questions = _group_questions(step, visible_questions)
    flow_provenance = _load_question_flow_provenance_payload()
    if _can_render_question_step_form(visible_questions):
        with st.form(
            _question_step_form_key(step.step_key, suffix=form_key_suffix),
            clear_on_submit=False,
        ):
            pending_inputs = _render_grouped_question_inputs(
                grouped_questions,
                answers,
                answer_meta=answer_meta,
                answered_lookup=answered_lookup,
                persist=False,
                ui_mode=ui_mode,
                provenance=flow_provenance,
                context_mode=context_mode,
            )
            submitted = st.form_submit_button(
                "Antworten übernehmen",
                type="primary",
                width="stretch",
            )
        if submitted:
            _persist_question_inputs(pending_inputs)
            _rerun_after_question_form_submit()
    else:
        _render_grouped_question_inputs(
            grouped_questions,
            answers,
            answer_meta=answer_meta,
            answered_lookup=answered_lookup,
            persist=True,
            ui_mode=ui_mode,
            provenance=flow_provenance,
            context_mode=context_mode,
        )

    return


def _render_grouped_question_inputs(
    grouped_questions: list[tuple[str, list[Question]]],
    answers: Dict[str, Any],
    *,
    answer_meta: dict[str, Any],
    answered_lookup: dict[str, bool],
    persist: bool,
    ui_mode: str = "standard",
    provenance: Mapping[str, Any] | None = None,
    context_mode: Literal["default", "compact"] = "default",
) -> list[QuestionInputResult]:
    pending_inputs: list[QuestionInputResult] = []
    for group_title, group_questions in grouped_questions:
        progress = compute_question_progress(
            group_questions,
            answers,
            answer_meta,
            answered_lookup=answered_lookup,
        )
        with st.container(border=True):
            render_static_html(
                """
                <div class="cs-question-group-title">
                    <strong>{group_title}</strong>
                    <span class="cs-question-group-meta">{answered}/{total} beantwortet</span>
                </div>
                """.format(
                    group_title=escape(group_title),
                    answered=progress["answered"],
                    total=progress["total"],
                ),
                streamlit_module=st,
            )
            if context_mode != "compact" or ui_mode == "expert":
                _render_section_provenance(
                    section_title=group_title,
                    questions=group_questions,
                    ui_mode=ui_mode,
                    provenance=provenance,
                )
            if progress["required_unanswered"] > 0:
                st.caption(f"{progress['required_unanswered']} offen")
            pending_inputs.extend(
                _render_questions_two_columns(
                    group_questions,
                    answers,
                    persist=persist,
                    ui_mode=ui_mode,
                    provenance=provenance,
                    context_mode=context_mode,
                )
            )
    return pending_inputs


def _question_count_label(count: int) -> str:
    return f"{count} Detailfrage" if count == 1 else f"{count} Detailfragen"


def _question_count_verb(count: int, *, singular: str, plural: str) -> str:
    return singular if count == 1 else plural


def _question_hidden_scope_caption(
    *,
    dependency_hidden_count: int,
    adaptive_hidden_count: int,
) -> str | None:
    dependency_hidden_count = max(int(dependency_hidden_count), 0)
    adaptive_hidden_count = max(int(adaptive_hidden_count), 0)
    dependency_part = ""
    adaptive_part = ""
    if dependency_hidden_count:
        dependency_verb = _question_count_verb(
            dependency_hidden_count,
            singular="erscheint",
            plural="erscheinen",
        )
        dependency_part = (
            f"{_question_count_label(dependency_hidden_count)} {dependency_verb}, "
            "sobald die vorausgesetzten Antworten passen"
        )
    if adaptive_hidden_count:
        adaptive_verb = _question_count_verb(
            adaptive_hidden_count,
            singular="ist",
            plural="sind",
        )
        adaptive_part = (
            f"{_question_count_label(adaptive_hidden_count)} {adaptive_verb} "
            "im aktuellen Umfang zurückgestellt, weil bereits belastbare Angaben "
            "vorliegen oder wichtigere offene Fragen zuerst erscheinen"
        )
    if dependency_part and adaptive_part:
        return f"{dependency_part}; {adaptive_part}."
    if dependency_part:
        return f"{dependency_part}."
    if adaptive_part:
        return f"{adaptive_part}."
    return None


def _can_render_question_step_form(questions: list[Question]) -> bool:
    return (
        not any(_is_language_requirement_question(question) for question in questions)
        and callable(getattr(st, "form", None))
        and callable(getattr(st, "form_submit_button", None))
    )


def _question_step_form_key(step_key: str, *, suffix: str | None = None) -> str:
    base_key = f"{WIDGET_KEY_PREFIX}step_form.{step_key}"
    normalized_suffix = str(suffix or "").strip()
    if not normalized_suffix:
        return base_key
    return f"{base_key}.{normalized_suffix}"


def _persist_question_inputs(inputs: list[QuestionInputResult]) -> None:
    for question_id, previous_value, value in inputs:
        _persist_question_answer(question_id, previous_value, value)


def _persist_question_answer(question_id: str, previous_value: Any, value: Any) -> None:
    mark_answer_touched(question_id, previous_value, value)
    set_answer(question_id, value)


def _rerun_after_question_form_submit() -> None:
    rerun = getattr(st, "rerun", None)
    if callable(rerun):
        rerun()
        return
    success = getattr(st, "success", None)
    if callable(success):
        success("Antworten übernommen.")


def _sort_questions_for_progressive_disclosure(
    questions: list[Question],
) -> list[Question]:
    priority_rank = {"core": 0, "standard": 1, "detail": 2}
    return sorted(
        questions,
        key=lambda question: (
            priority_rank.get(question.priority or "", 1),
            question.id,
        ),
    )
def _get_ui_preferences() -> dict[str, Any]:
    raw_ui_preferences = st.session_state.get(SSKey.UI_PREFERENCES.value, {})
    if isinstance(raw_ui_preferences, dict):
        return raw_ui_preferences
    return {}


def _get_global_details_expanded_default(*, ui_mode: str) -> bool:
    ui_preferences = _get_ui_preferences()
    configured = ui_preferences.get("details_expanded_default")
    if isinstance(configured, bool):
        return configured
    return ui_mode == "expert"


def _get_step_compact_preference(*, step_key: str, fallback_compact: bool) -> bool:
    ui_preferences = _get_ui_preferences()
    raw_step_compact = ui_preferences.get("step_compact", {})
    step_compact = raw_step_compact if isinstance(raw_step_compact, dict) else {}
    configured = step_compact.get(step_key)
    if isinstance(configured, bool):
        return configured
    return fallback_compact


def _set_step_compact_preference(*, step_key: str, compact: bool) -> None:
    ui_preferences = dict(_get_ui_preferences())
    raw_step_compact = ui_preferences.get("step_compact", {})
    step_compact = raw_step_compact if isinstance(raw_step_compact, dict) else {}
    updated_step_compact = dict(step_compact)
    updated_step_compact[step_key] = compact
    ui_preferences["step_compact"] = updated_step_compact
    st.session_state[SSKey.UI_PREFERENCES.value] = ui_preferences


def _ensure_step_group_state(
    step_key: str,
    grouped_questions: list[tuple[str, list[Question]]],
    *,
    default_open: bool,
) -> None:
    raw_open_groups = st.session_state.get(SSKey.OPEN_GROUPS.value, {})
    open_groups = raw_open_groups if isinstance(raw_open_groups, dict) else {}
    step_groups_raw = open_groups.get(step_key, {})
    step_groups = step_groups_raw if isinstance(step_groups_raw, dict) else {}

    changed = False
    for group_title, _ in grouped_questions:
        if group_title not in step_groups:
            step_groups[group_title] = default_open
            changed = True

    if changed:
        open_groups = dict(open_groups)
        open_groups[step_key] = step_groups
        st.session_state[SSKey.OPEN_GROUPS.value] = open_groups


def _is_group_open(step_key: str, group_title: str, *, default_open: bool) -> bool:
    raw_open_groups = st.session_state.get(SSKey.OPEN_GROUPS.value, {})
    if not isinstance(raw_open_groups, dict):
        return default_open
    step_groups = raw_open_groups.get(step_key, {})
    if not isinstance(step_groups, dict):
        return default_open
    value = step_groups.get(group_title)
    if isinstance(value, bool):
        return value
    return default_open


def _set_step_group_open_state(
    step_key: str,
    grouped_questions: list[tuple[str, list[Question]]],
    *,
    is_open: bool,
) -> None:
    raw_open_groups = st.session_state.get(SSKey.OPEN_GROUPS.value, {})
    open_groups = raw_open_groups if isinstance(raw_open_groups, dict) else {}
    step_groups_raw = open_groups.get(step_key, {})
    step_groups = step_groups_raw if isinstance(step_groups_raw, dict) else {}
    updated_groups = dict(step_groups)
    for group_title, _ in grouped_questions:
        updated_groups[group_title] = is_open

    open_groups = dict(open_groups)
    open_groups[step_key] = updated_groups
    st.session_state[SSKey.OPEN_GROUPS.value] = open_groups


def _render_question(
    q: Question,
    answers: Dict[str, Any],
    *,
    widget_key_prefix: str = WIDGET_KEY_PREFIX,
    persist: bool = True,
    ui_mode: str = "standard",
    provenance: Mapping[str, Any] | None = None,
    context_mode: Literal["default", "compact"] = "default",
) -> QuestionInputResult:
    key = widget_key_prefix + q.id
    inferred_default = _infer_default_value(q)
    previous_value = answers.get(q.id, inferred_default)
    current_value = previous_value
    value: Any = None
    validation_error: str | None = None

    # Helper text for required fields
    label = q.label + (" *" if q.required else "")
    is_language_question = _is_language_requirement_question(q)
    widget_help = _question_widget_help(q, provenance=provenance)

    with st.container(border=True):
        if is_language_question:
            value = _render_language_requirement_question(
                question=q,
                current_value=current_value,
                key=key,
                label=label,
            )
        elif q.answer_type == AnswerType.SHORT_TEXT:
            value = st.text_input(
                label,
                value=str(current_value or ""),
                help=widget_help,
                key=key,
                placeholder=q.help or "Kurzantwort eingeben",
            )
        elif q.answer_type == AnswerType.LONG_TEXT:
            value = st.text_area(
                label,
                value=str(current_value or ""),
                help=widget_help,
                key=key,
                height=140,
                placeholder=q.help or "Details ergänzen …",
            )
        elif q.answer_type == AnswerType.SINGLE_SELECT:
            option_entries = _question_option_entries(q)
            options = [value for value, _ in option_entries]
            label_by_value = {value: label for value, label in option_entries}
            value_by_label = {label: value for value, label in option_entries}
            current_value = _coerce_single_select_value(current_value)
            other_text_default = _extract_other_text(current_value)
            if other_text_default and _OTHER_OPTION not in options:
                options = [*options, _OTHER_OPTION]
                label_by_value[_OTHER_OPTION] = _OTHER_OPTION
                value_by_label[_OTHER_OPTION] = _OTHER_OPTION
            if other_text_default and current_value not in options:
                current_value = _OTHER_OPTION
            if current_value and current_value not in options:
                options = [str(current_value)] + options
                label_by_value[str(current_value)] = str(current_value)
                value_by_label[str(current_value)] = str(current_value)
            display_options = [label_by_value.get(item, item) for item in options]
            if not q.required:
                display_options = ["— Bitte wählen —", *display_options]
            selected_value = str(current_value) if current_value is not None else None
            selected_label = (
                label_by_value.get(selected_value, selected_value)
                if selected_value is not None
                else None
            )
            default_index = (
                display_options.index(selected_label)
                if selected_label in display_options
                else (0 if display_options else None)
            )
            if hasattr(st, "segmented_control") and 2 <= len(display_options) <= 5:
                value = st.segmented_control(
                    label,
                    options=display_options,
                    default=display_options[default_index]
                    if default_index is not None
                    else None,
                    key=key,
                    help=widget_help,
                )
            elif len(display_options) <= 4:
                value = st.radio(
                    label,
                    options=display_options,
                    index=default_index if default_index is not None else 0,
                    horizontal=True,
                    help=widget_help,
                    key=key,
                )
            else:
                value = st.selectbox(
                    label,
                    options=display_options,
                    index=default_index if default_index is not None else 0,
                    help=widget_help,
                    key=key,
                )
            if value == "— Bitte wählen —":
                value = None
            elif value is not None:
                value = value_by_label.get(value, value)
            if value == _OTHER_OPTION:
                other_text = st.text_input(
                    "Bitte spezifizieren",
                    value=other_text_default,
                    key=f"{key}::other",
                    placeholder="Bitte präzisieren …",
                ).strip()
                value = f"{_OTHER_PREFIX}{other_text}" if other_text else _OTHER_OPTION
        elif q.answer_type == AnswerType.MULTI_SELECT:
            option_entries = _question_option_entries(q)
            options = [item[0] for item in option_entries]
            label_by_value = {value: label for value, label in option_entries}
            value_by_label = {label: value for value, label in option_entries}
            cur_list = _coerce_multi_select_values(current_value)
            cur_list, other_text_default = _strip_other_from_multiselect(cur_list)
            if other_text_default and _OTHER_OPTION not in options:
                options = [*options, _OTHER_OPTION]
                label_by_value[_OTHER_OPTION] = _OTHER_OPTION
                value_by_label[_OTHER_OPTION] = _OTHER_OPTION
            for v in cur_list:
                if v not in options:
                    options = [v] + options
                    label_by_value[v] = v
                    value_by_label[v] = v
            display_options = [label_by_value.get(item, item) for item in options]
            default_values = [
                label_by_value.get(v, v) for v in cur_list if v in options
            ]
            if hasattr(st, "pills") and options:
                inject_pills_grid_css()
                value = (
                    st.pills(
                        label,
                        options=display_options,
                        default=default_values,
                        selection_mode="multi",
                        key=key,
                        help=widget_help,
                    )
                    or []
                )
            else:
                value = st.multiselect(
                    label,
                    options=display_options,
                    default=default_values,
                    help=widget_help,
                    key=key,
                )
            value = [value_by_label.get(item, item) for item in (value or [])]
            if _OTHER_OPTION in value:
                other_text = st.text_input(
                    "Bitte spezifizieren",
                    value=other_text_default,
                    key=f"{key}::other",
                    placeholder="Bitte präzisieren …",
                ).strip()
                value = [v for v in value if v != _OTHER_OPTION]
                value.append(
                    f"{_OTHER_PREFIX}{other_text}" if other_text else _OTHER_OPTION
                )
        elif q.answer_type == AnswerType.NUMBER:
            value, validation_error = _render_number_question(
                question=q,
                key=key,
                label=label,
                help_text=widget_help,
                current_value=current_value,
            )
        elif q.answer_type == AnswerType.BOOLEAN:
            value = st.toggle(
                label,
                value=bool(current_value) if current_value is not None else False,
                help=widget_help,
                key=key,
            )
        elif q.answer_type == AnswerType.DATE:
            d: Optional[date] = None
            if isinstance(current_value, date):
                d = current_value
            elif isinstance(current_value, str) and current_value:
                try:
                    d = date.fromisoformat(current_value)
                except Exception:
                    d = None
            picked_date = st.date_input(label, value=d, help=widget_help, key=key)
            value = picked_date.isoformat() if picked_date else None
        else:
            value = st.text_input(
                label, value=str(current_value or ""), help=widget_help, key=key
            )

        if context_mode != "compact":
            _render_question_provenance(q, ui_mode=ui_mode, provenance=provenance)
        if validation_error:
            st.error(validation_error)

    if persist:
        _persist_question_answer(q.id, previous_value, value)

    if st.session_state.get(SSKey.DEBUG.value) and q.rationale:
        st.caption(f"Rationale: {_safe_question_provenance_text(q.rationale)}")
    return q.id, previous_value, value


def _render_number_question(
    *,
    question: Question,
    key: str,
    label: str,
    help_text: str | None,
    current_value: Any,
) -> tuple[float | int, str | None]:
    min_value, max_value, step_value = _resolve_number_constraints(question)
    force_slider = False
    if _is_percentage_number_question(question):
        min_value, max_value, step_value = 0.0, 100.0, 5.0
        force_slider = True
    if min_value > max_value:
        fallback_value = min_value
        return fallback_value, (
            "Ungültige Zahlen-Konfiguration (min > max). Bitte Fragebogen prüfen. "
            "Invalid numeric configuration (min > max). Please review the question plan."
        )

    numeric_value, parse_error = _coerce_number_value(current_value)
    if numeric_value is None:
        numeric_value = min_value

    bounded_value = min(max(numeric_value, min_value), max_value)
    validation_error: str | None = None
    if parse_error:
        value_text = f"{bounded_value:g}"
        validation_error = (
            "Gehalt konnte nicht eindeutig gelesen werden. "
            f"Verwendeter Wert: {value_text}. "
            "Bitte prüfen Sie, ob Jahresgehalt, Monatsgehalt oder Gehaltsrange gemeint ist."
        )
    elif numeric_value != bounded_value:
        validation_error = (
            f"Wert muss zwischen {min_value:g} und {max_value:g} liegen. "
            f"Value must be between {min_value:g} and {max_value:g}."
        )

    integer_scale = all(
        float(x).is_integer() for x in (min_value, max_value, step_value)
    )
    if integer_scale:
        min_int = int(min_value)
        max_int = int(max_value)
        step_int = max(1, int(step_value))
        current_int = int(round(bounded_value))
        if force_slider or (max_int - min_int <= 200 and step_int == 1):
            return (
                st.slider(
                    label,
                    min_value=min_int,
                    max_value=max_int,
                    value=current_int,
                    step=step_int,
                    help=help_text,
                    key=key,
                ),
                validation_error,
            )
        return (
            st.number_input(
                label,
                min_value=min_int,
                max_value=max_int,
                value=current_int,
                step=step_int,
                help=help_text,
                key=key,
            ),
            validation_error,
        )

    step_float = float(step_value)
    current_float = float(bounded_value)
    return (
        st.number_input(
            label,
            min_value=float(min_value),
            max_value=float(max_value),
            value=current_float,
            step=step_float,
            help=help_text,
            key=key,
            format="%.2f",
        ),
        validation_error,
    )


def _coerce_number_value(value: Any) -> tuple[float | None, bool]:
    try:
        if value is None or value == "":
            return None, False
        return float(value), False
    except Exception:
        return None, True


def _resolve_number_constraints(question: Question) -> tuple[float, float, float]:
    if question.min_value is not None and question.max_value is not None:
        min_value = float(question.min_value)
        max_value = float(question.max_value)
    else:
        inferred_min, inferred_max = _parse_scale_bounds(
            f"{question.label} {question.help or ''}"
        )
        if inferred_min is not None and inferred_max is not None:
            min_value = float(inferred_min)
            max_value = float(inferred_max)
        else:
            min_value = 0.0
            max_value = 100.0

    step_value = float(question.step_value) if question.step_value else 1.0
    if step_value <= 0:
        step_value = 1.0
    return min_value, max_value, step_value


def _is_percentage_number_question(question: Question) -> bool:
    if question.answer_type != AnswerType.NUMBER:
        return False
    haystack = " ".join(
        (
            question.id or "",
            question.label or "",
            question.help or "",
            question.target_path or "",
            question.rationale or "",
        )
    ).lower()
    return "%" in haystack or "prozent" in haystack or "percent" in haystack


def _infer_default_value(q: Question) -> Any:
    if q.default is not None:
        return q.default
    if q.answer_type == AnswerType.SINGLE_SELECT:
        options = [value for value, _ in _question_option_entries(q)]
        return options[0] if options else None
    if q.answer_type == AnswerType.MULTI_SELECT:
        return []
    if q.answer_type == AnswerType.BOOLEAN:
        return False
    if q.answer_type == AnswerType.NUMBER:
        min_value, max_value, _ = _resolve_number_constraints(q)
        return (
            int((min_value + max_value) / 2)
            if float(min_value).is_integer() and float(max_value).is_integer()
            else (min_value + max_value) / 2
        )
    return None


def _is_language_requirement_question(question: Question) -> bool:
    haystack = " ".join(
        [
            question.id or "",
            question.label or "",
            question.help or "",
            question.target_path or "",
        ]
    ).lower()
    return any(term in haystack for term in ("sprache", "sprachen", "language", "cefr"))


def _coerce_language_requirements(value: Any) -> list[LanguageRequirement]:
    if isinstance(value, str):
        text = value.strip()
        if text:
            return [LanguageRequirement(language=text, level="B2")]
        return []

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        normalized: list[LanguageRequirement] = []
        for entry in value:
            if isinstance(entry, dict):
                raw_language = str(entry.get("language", "")).strip()
                raw_level = str(entry.get("level", "")).strip().upper()
                if not raw_language:
                    continue
                if raw_level not in _CEFR_OPTIONS:
                    raw_level = "B2"
                normalized.append(
                    LanguageRequirement(language=raw_language, level=raw_level)  # type: ignore[arg-type]
                )
                continue
            if isinstance(entry, str) and has_meaningful_value(entry):
                normalized.append(
                    LanguageRequirement(language=entry.strip(), level="B2")
                )
        return normalized
    return []


def _render_language_requirement_question(
    *,
    question: Question,
    current_value: Any,
    key: str,
    label: str,
) -> list[dict[str, str]]:
    rows_state_key = f"{key}::rows"
    if rows_state_key not in st.session_state:
        st.session_state[rows_state_key] = [
            item.model_dump() for item in _coerce_language_requirements(current_value)
        ] or [LanguageRequirement(language="Deutsch", level="B2").model_dump()]

    st.markdown(label)
    if question.help:
        st.caption(question.help)

    rows_raw = st.session_state.get(rows_state_key, [])
    rows = rows_raw if isinstance(rows_raw, list) else []

    new_rows: list[dict[str, str]] = []
    for index, row in enumerate(rows):
        row_data = row if isinstance(row, dict) else {}
        language = str(row_data.get("language", "Deutsch")).strip() or "Deutsch"
        level = str(row_data.get("level", "B2")).strip().upper() or "B2"
        if language not in _LANGUAGE_OPTIONS:
            language = _LANGUAGE_OPTIONS[0]
        if level not in _CEFR_OPTIONS:
            level = "B2"

        col_lang, col_level, col_remove = st.columns([2.2, 1.2, 0.8], gap="small")
        with col_lang:
            selected_language = st.selectbox(
                "Sprache",
                options=_LANGUAGE_OPTIONS,
                index=_LANGUAGE_OPTIONS.index(language),
                key=f"{key}::language::{index}",
                label_visibility="collapsed",
            )
        with col_level:
            selected_level = st.selectbox(
                "Level",
                options=_CEFR_OPTIONS,
                index=_CEFR_OPTIONS.index(level),
                key=f"{key}::level::{index}",
                label_visibility="collapsed",
            )
        with col_remove:
            remove_clicked = st.button(
                "Entfernen",
                key=f"{key}::remove::{index}",
                disabled=len(rows) <= 1,
                width="stretch",
            )
        if remove_clicked:
            continue
        new_rows.append(
            LanguageRequirement(
                language=selected_language,
                level=selected_level,  # type: ignore[arg-type]
            ).model_dump()
        )

    if st.button("Weitere Sprache hinzufügen", key=f"{key}::add"):
        new_rows.append(
            LanguageRequirement(language="Deutsch", level="B2").model_dump()
        )

    st.session_state[rows_state_key] = new_rows or [
        LanguageRequirement(language="Deutsch", level="B2").model_dump()
    ]
    return list(st.session_state[rows_state_key])


def _coerce_single_select_value(value: Any) -> str | None:
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in value:
            if isinstance(item, str) and has_meaningful_value(item):
                return item.strip()
    return None


def _coerce_multi_select_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if has_meaningful_value(value) else []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        cleaned = item.strip()
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return result


def _extract_other_text(value: str | None) -> str:
    if not isinstance(value, str):
        return ""
    if not value.startswith(_OTHER_PREFIX):
        return ""
    return value.removeprefix(_OTHER_PREFIX).strip()


def _strip_other_from_multiselect(values: list[str]) -> tuple[list[str], str]:
    cleaned_values: list[str] = []
    other_text = ""
    for entry in values:
        if entry.startswith(_OTHER_PREFIX):
            other_text = entry.removeprefix(_OTHER_PREFIX).strip()
            continue
        cleaned_values.append(entry)
    return cleaned_values, other_text


def _parse_scale_bounds(text: str) -> tuple[int | None, int | None]:
    match = re.search(r"(\d+)\s*[-–]\s*(\d+)", text)
    if not match:
        return None, None
    lower = int(match.group(1))
    upper = int(match.group(2))
    if lower > upper:
        lower, upper = upper, lower
    if upper - lower > 20:
        return None, None
    return lower, upper
