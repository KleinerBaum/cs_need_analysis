# ui_fact_review.py
"""Question fact-review and step-review UI helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from enum import Enum
from html import escape
from typing import Any, Dict

import streamlit as st

from safe_html import render_static_html
from constants import (
    AnswerType,
    FactKey,
    FactResolutionStatus,
    FactSourceType,
    SSKey,
    WIDGET_KEY_PREFIX,
)
from job_extract_review_helpers import has_meaningful_value
from question_dependencies import should_show_question
from question_progress import (
    build_answered_lookup,
    compute_question_progress,
    is_answered,
    resolve_question_job_extract_value,
)
from schemas import JobAdExtract, Question, QuestionStep
from state import get_answer_meta, get_answers
from step_payload import StepReviewPayload, build_step_payload_from_state
from step_status import StepStatusPayload
from ui_badges import build_provenance_badge
from ui_inputs import (
    _coerce_language_requirements,
    _coerce_multi_select_values,
    _coerce_single_select_value,
    _group_questions,
    _is_language_requirement_question,
    _render_questions_two_columns,
)

REVIEW_WIDGET_KEY_PREFIX = f"{WIDGET_KEY_PREFIX}review."


class ReviewRenderMode(str, Enum):
    COMPACT = "compact"
    DIRECT_ANSWERS = "direct_answers"
    FULL = "full"


class ReviewRenderContext(str, Enum):
    STEP_FORM = "step_form"
    SUMMARY_READINESS = "summary_readiness"

def resolve_standard_review_mode(
    *,
    context: ReviewRenderContext,
    ui_mode: str | None = None,
    debug_enabled: bool | None = None,
) -> ReviewRenderMode:
    """Resolve canonical review rendering mode from UI mode/debug + context."""

    normalized_ui_mode = str(
        ui_mode if ui_mode is not None else st.session_state.get(SSKey.UI_MODE.value, "standard")
    ).strip().lower()
    is_debug = (
        bool(debug_enabled)
        if debug_enabled is not None
        else bool(st.session_state.get(SSKey.DEBUG.value, False))
    )
    if normalized_ui_mode == "expert" or is_debug:
        return ReviewRenderMode.FULL
    if context is ReviewRenderContext.STEP_FORM:
        return ReviewRenderMode.COMPACT
    return ReviewRenderMode.DIRECT_ANSWERS


def _resolve_review_render_mode(
    render_mode: ReviewRenderMode | None,
) -> ReviewRenderMode:
    return render_mode or ReviewRenderMode.DIRECT_ANSWERS


def build_step_review_payload(step: QuestionStep | None) -> StepReviewPayload:
    return build_step_payload_from_state(
        step,
        session_state=st.session_state,
        answers=get_answers(),
        answer_meta=get_answer_meta(),
        visibility_predicate=should_show_question,
    )["review_payload"]


def render_standard_step_review(
    step: QuestionStep | None,
    render_mode: ReviewRenderMode | None = None,
) -> None:
    if step is None or not step.questions:
        return
    review_payload = build_step_review_payload(step)
    render_step_review_card(
        step=step,
        visible_questions=review_payload["visible_questions"],
        answers=review_payload["answers"],
        answer_meta=review_payload["answer_meta"],
        answered_lookup=review_payload["answered_lookup"],
        step_status=review_payload["step_status"],
        job_extract=review_payload["job_extract"],
        intake_facts=review_payload["intake_facts"],
        intake_fact_evidence=review_payload["intake_fact_evidence"],
        confidence_threshold=review_payload["confidence_threshold"],
        render_mode=_resolve_review_render_mode(render_mode),
    )


def render_recruiting_consistency_checklist(
    *,
    title: str,
    checks: Sequence[tuple[str, bool]],
    caption: str = "Kurzcheck vor dem Weitergehen",
) -> None:
    """Render a concise, state-derived readiness checklist for recruiting consistency."""

    compact_checks = [
        (label.strip(), is_ok) for label, is_ok in checks if label.strip()
    ]
    if not compact_checks:
        return

    st.markdown(f"#### {title}")
    st.caption(caption)
    for label, is_ok in compact_checks:
        token = "✅" if is_ok else "⬜"
        st.write(f"- {token} {label}")


def has_answered_question_with_keywords(
    *,
    questions: Sequence[Question],
    answered_lookup: dict[str, bool],
    keywords: Sequence[str],
) -> bool:
    """Return True if a visible question matching any keyword is answered."""

    normalized_keywords = tuple(
        keyword.strip().casefold() for keyword in keywords if keyword.strip()
    )
    if not normalized_keywords:
        return False

    for question in questions:
        question_label = question.label.strip().casefold()
        if not question_label:
            continue
        if any(keyword in question_label for keyword in normalized_keywords):
            if answered_lookup.get(question.id, False):
                return True
    return False
def _question_fact_key(question: Question) -> FactKey | None:
    for raw_key in (getattr(question, "fact_key", None), question.target_path):
        if not isinstance(raw_key, str):
            continue
        try:
            return FactKey(raw_key.strip())
        except ValueError:
            continue
    return None


def _question_fact_evidence(
    question: Question,
    intake_fact_evidence: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    fact_key = _question_fact_key(question)
    if fact_key is None or not isinstance(intake_fact_evidence, Mapping):
        return {}
    evidence_raw = intake_fact_evidence.get(fact_key.value)
    return evidence_raw if isinstance(evidence_raw, Mapping) else {}


def _question_answer_provenance_label(
    question: Question,
    *,
    user_answered: bool,
    from_job_extract: bool,
    intake_fact_evidence: Mapping[str, Any] | None,
    confidence_threshold: float | None,
) -> str:
    if user_answered:
        return build_provenance_badge(
            source_type=FactSourceType.MANUAL.value,
            resolution_status=FactResolutionStatus.CONFIRMED.value,
            confirmed=True,
        ).label
    evidence = _question_fact_evidence(question, intake_fact_evidence)
    if evidence:
        return build_provenance_badge(
            evidence,
            confidence_threshold=confidence_threshold,
        ).label
    if from_job_extract:
        return build_provenance_badge(
            source_type=FactSourceType.JOBSPEC.value,
            resolution_status=FactResolutionStatus.INFERRED.value,
        ).label
    return ""


def _question_open_provenance_label(
    question: Question,
    *,
    intake_fact_evidence: Mapping[str, Any] | None,
    confidence_threshold: float | None,
) -> str:
    evidence = _question_fact_evidence(question, intake_fact_evidence)
    if not evidence:
        return ""
    status = str(evidence.get("resolution_status") or "").strip()
    try:
        confidence = float(evidence.get("confidence"))
    except (TypeError, ValueError):
        confidence = None
    has_low_confidence = (
        confidence_threshold is not None
        and confidence is not None
        and confidence < confidence_threshold
    )
    if status != FactResolutionStatus.CONFLICTED.value and not has_low_confidence:
        return ""
    return build_provenance_badge(
        evidence,
        confidence_threshold=confidence_threshold,
    ).label


def render_step_review_card(
    step: QuestionStep,
    visible_questions: list[Question],
    answers: Dict[str, Any],
    answer_meta: dict[str, Any],
    answered_lookup: dict[str, bool] | None = None,
    step_status: StepStatusPayload | None = None,
    render_mode: ReviewRenderMode | None = None,
    job_extract: JobAdExtract | None = None,
    intake_facts: Mapping[str, Any] | None = None,
    intake_fact_evidence: Mapping[str, Any] | None = None,
    confidence_threshold: float | None = None,
) -> None:
    resolved_render_mode = _resolve_review_render_mode(render_mode)
    missing_essentials_display_max = 4
    max_inline_unanswered = 2
    if not visible_questions:
        with st.container(border=True):
            render_static_html(
                '<div class="cs-review-card-title"><strong>Antworten prüfen</strong></div>',
                streamlit_module=st,
            )
            st.caption("Keine sichtbaren Fragen in diesem Schritt.")
            st.caption(
                "Hinweis: Abhängigkeiten oder aktueller Umfang können Detailfragen ausblenden."
            )
        return

    grouped_questions = _group_questions(step, visible_questions)
    group_payload: list[
        tuple[
            int,
            str,
            dict[str, int],
            list[tuple[str, str, str]],
            list[Question],
            bool,
        ]
    ] = []
    missing_essential_ids = (
        list(step_status.get("missing_essential_ids", [])) if step_status else []
    )
    missing_essential_labels = (
        list(step_status.get("missing_essentials", [])) if step_status else []
    )
    label_by_question_id = {question.id: question.label for question in visible_questions}
    fallback_labels = [
        label_by_question_id[question_id]
        for question_id in missing_essential_ids
        if question_id in label_by_question_id
    ]
    if not missing_essential_labels:
        missing_essential_labels = fallback_labels
    missing_essential_labels_display = (
        missing_essential_labels or fallback_labels
    )[:missing_essentials_display_max]
    additional_missing_essentials = max(
        len(missing_essential_ids) - len(missing_essential_labels_display), 0
    )
    incomplete_group_titles: list[str] = []
    missing_essential_id_set = set(missing_essential_ids)

    resolved_lookup = answered_lookup or build_answered_lookup(
        visible_questions,
        answers,
        answer_meta,
        job_extract=job_extract,
        intake_facts=intake_facts,
        intake_fact_evidence=intake_fact_evidence,
        confidence_threshold=confidence_threshold,
    )
    total_groups = len(grouped_questions)
    complete_groups = 0
    total_unanswered = 0

    for group_title, group_questions in grouped_questions:
        answered_items: list[tuple[str, str, str]] = []
        unanswered_questions: list[Question] = []
        group_missing_essential = False
        progress = compute_question_progress(
            group_questions,
            answers,
            answer_meta,
            answered_lookup=resolved_lookup,
        )
        group_complete = progress["total"] > 0 and progress["answered"] == progress["total"]
        for question in group_questions:
            if not resolved_lookup.get(question.id, False):
                unanswered_questions.append(question)
                total_unanswered += 1
                if question.id in missing_essential_id_set:
                    group_missing_essential = True
                continue
            value = answers.get(question.id)
            source_label = question.label
            user_answered = is_answered(
                question,
                value,
                answer_meta.get(question.id),
            )
            from_job_extract = False
            if not user_answered:
                extracted_value = resolve_question_job_extract_value(
                    question,
                    job_extract,
                    intake_facts=intake_facts,
                    intake_fact_evidence=intake_fact_evidence,
                    confidence_threshold=confidence_threshold,
                )
                if has_meaningful_value(extracted_value):
                    value = extracted_value
                    source_label = f"{question.label} (Jobspec)"
                    from_job_extract = True
            formatted = _format_answer_for_review(question, value)
            if formatted:
                answered_items.append(
                    (
                        source_label,
                        formatted,
                        _question_answer_provenance_label(
                            question,
                            user_answered=user_answered,
                            from_job_extract=from_job_extract,
                            intake_fact_evidence=intake_fact_evidence,
                            confidence_threshold=confidence_threshold,
                        ),
                    )
                )
        if group_complete:
            complete_groups += 1

        if progress["required_unanswered"] > 0:
            group_missing_essential = True

        sort_bucket = 0 if group_missing_essential else (2 if group_complete else 1)
        group_payload.append(
            (
                sort_bucket,
                group_title,
                progress,
                answered_items,
                unanswered_questions,
                group_complete,
            )
        )
        if group_missing_essential:
            incomplete_group_titles.append(group_title)

    with st.container(border=True):
        render_static_html(
            '<div class="cs-review-card-title"><strong>Antworten prüfen</strong></div>',
            streamlit_module=st,
        )
        if step_status is not None:
            answered = int(step_status.get("answered", 0))
            total = int(step_status.get("total", 0))
            essentials_answered = int(step_status.get("essentials_answered", 0))
            essentials_total = int(step_status.get("essentials_total", 0))
            col1, col2, col3 = st.columns(3)
            with col1:
                st.caption(
                    f"{'✅' if answered == total and total > 0 else '•'} "
                    f"Beantwortet {answered}/{total}"
                )
            with col2:
                st.caption(
                    f"{'✅' if essentials_answered == essentials_total and essentials_total > 0 else '⚠️'} "
                    f"Pflichtangaben {essentials_answered}/{essentials_total}"
                )
            with col3:
                if total_groups > 0:
                    incomplete_groups = max(total_groups - complete_groups, 0)
                    st.caption(
                        f"{'✅' if incomplete_groups == 0 else '⚠️'} "
                        f"Gruppen {complete_groups} vollständig · {incomplete_groups} offen"
                    )
                else:
                    st.caption("• Keine Gruppen")
        else:
            answered = sum(1 for is_answered in resolved_lookup.values() if is_answered)
            total = len(visible_questions)
            st.caption(f"• Beantwortet {answered}/{total}")

        if missing_essential_id_set:
            with st.container(border=True):
                st.markdown("##### ⚠️ Pflichtangaben offen")
                essential_items = "".join(
                    f"<li>{escape(label)}</li>"
                    for label in missing_essential_labels_display
                )
                render_static_html(
                    f'<ul class="cs-review-essential-list">{essential_items}</ul>',
                    streamlit_module=st,
                )
                if additional_missing_essentials > 0:
                    st.caption(f"+{additional_missing_essentials} weitere")
                missing_groups = ", ".join(dict.fromkeys(incomplete_group_titles))
                st.caption(
                    f"Betroffene Gruppen: {missing_groups or 'Keine Gruppenzuordnung'}"
                )

        if not group_payload and not missing_essential_id_set:
            st.caption("Noch keine sichtbaren Antworten vorhanden.")
            return

        render_inline_inputs = False
        if resolved_render_mode is ReviewRenderMode.DIRECT_ANSWERS:
            render_inline_inputs = _can_render_inline_answer_inputs() and (
                bool(missing_essential_id_set)
                or (0 < total_unanswered <= max_inline_unanswered)
            )
        elif resolved_render_mode is ReviewRenderMode.FULL:
            render_inline_inputs = _can_render_inline_answer_inputs()

        if (
            resolved_render_mode is ReviewRenderMode.DIRECT_ANSWERS
            and not render_inline_inputs
            and total_unanswered > 0
        ):
            st.caption(
                f"{total_unanswered} offene Frage(n) – Details und direkte Eingabe im Bereich „Details je Bereich“."
            )

        if resolved_render_mode is ReviewRenderMode.COMPACT:
            return

        with st.expander("Details je Bereich", expanded=False):
            for (
                _,
                group_title,
                progress,
                answered_items,
                unanswered_questions,
                group_complete,
            ) in sorted(
                group_payload, key=lambda item: (item[0], item[1].casefold())
            ):
                status_chip = "✅ vollständig" if group_complete else "⚠️ offen"
                with st.container(border=True):
                    col_title, col_chip, col_ratio = st.columns([5, 2, 2], gap="small")
                    with col_title:
                        st.markdown(f"**{group_title}**")
                    with col_chip:
                        st.caption(status_chip)
                    with col_ratio:
                        st.caption(f"{progress['answered']}/{progress['total']}")

                    if answered_items:
                        for label, formatted_value, provenance in answered_items:
                            suffix = f" · {provenance}" if provenance else ""
                            st.caption(f"{label}: {formatted_value}{suffix}")
                    elif not group_complete:
                        st.caption("Noch keine bestätigten Antworten in dieser Gruppe.")

                    if unanswered_questions:
                        open_provenance = [
                            (
                                question.label,
                                _question_open_provenance_label(
                                    question,
                                    intake_fact_evidence=intake_fact_evidence,
                                    confidence_threshold=confidence_threshold,
                                ),
                            )
                            for question in unanswered_questions
                        ]
                        open_provenance = [
                            (label, provenance)
                            for label, provenance in open_provenance
                            if provenance
                        ]
                        if open_provenance:
                            preview = " · ".join(
                                f"{label}: {provenance}"
                                for label, provenance in open_provenance[:3]
                            )
                            remaining = len(open_provenance) - 3
                            suffix = f" · +{remaining} weitere" if remaining > 0 else ""
                            st.caption(f"Zu prüfen: {preview}{suffix}")
                        if render_inline_inputs:
                            st.markdown("**Offene Fragen direkt beantworten**")
                            _render_questions_two_columns(
                                unanswered_questions,
                                answers,
                                widget_key_prefix=REVIEW_WIDGET_KEY_PREFIX,
                            )
                        else:
                            if resolved_render_mode is ReviewRenderMode.FULL:
                                st.caption(
                                    f"{len(unanswered_questions)} offene Frage(n) in dieser Gruppe."
                                )


def _can_render_inline_answer_inputs() -> bool:
    required_methods = (
        "columns",
        "container",
        "date_input",
        "multiselect",
        "number_input",
        "radio",
        "selectbox",
        "slider",
        "text_area",
        "text_input",
        "toggle",
    )
    return all(callable(getattr(st, method, None)) for method in required_methods)
def _collect_incomplete_group_titles(
    grouped_questions: list[tuple[str, list[Question]]],
    answers: Dict[str, Any],
    answer_meta: dict[str, Any],
    answered_lookup: dict[str, bool],
) -> list[str]:
    incomplete_groups: list[str] = []
    for group_title, group_questions in grouped_questions:
        progress = compute_question_progress(
            group_questions,
            answers,
            answer_meta,
            answered_lookup=answered_lookup,
        )
        if progress["required_unanswered"] > 0:
            incomplete_groups.append(group_title)
    return incomplete_groups


def _format_answer_for_review(question: Question, value: Any) -> str:
    if _is_language_requirement_question(question):
        requirements = _coerce_language_requirements(value)
        formatted = [f"{item.language} ({item.level})" for item in requirements]
        return ", ".join(formatted)

    if question.answer_type == AnswerType.BOOLEAN:
        return "Ja" if bool(value) else "Nein"
    if question.answer_type == AnswerType.MULTI_SELECT:
        values = _coerce_multi_select_values(value)
        return ", ".join(values)
    if question.answer_type == AnswerType.SINGLE_SELECT:
        selected = _coerce_single_select_value(value)
        return selected or ""
    if question.answer_type == AnswerType.LONG_TEXT:
        text = str(value or "").strip()
        return _truncate_for_review(text, limit=140)
    if question.answer_type == AnswerType.SHORT_TEXT:
        return _truncate_for_review(str(value or "").strip(), limit=90)
    if question.answer_type == AnswerType.NUMBER:
        return str(value) if value is not None else ""
    if question.answer_type == AnswerType.DATE:
        return str(value or "")

    if isinstance(value, list):
        return ", ".join(
            str(item).strip() for item in value if has_meaningful_value(item)
        )
    if isinstance(value, str):
        return _truncate_for_review(value.strip(), limit=90)
    return str(value) if has_meaningful_value(value) else ""


def _truncate_for_review(text: str, *, limit: int) -> str:
    if len(text) <= limit:
        return text
    return f"{text[: max(limit - 1, 1)].rstrip()}…"
