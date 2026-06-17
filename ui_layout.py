"""Reusable page layout shells for wizard steps."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import Any, Literal

import streamlit as st

from components.design_system import render_process_progress, render_step_header
from constants import (
    COMPLETION_STATE_BADGE_TEXT,
    COMPLETION_STATE_NOT_STARTED,
    JOBSPEC_ASSUMPTION_ANSWER_ID_PREFIX,
    JOBSPEC_NOTE_ROUTE_KEYWORDS,
    JOBSPEC_NOTE_ROUTE_STEP_KEYS,
    NON_INTAKE_STEP_KEYS,
    SSKey,
    STEPS,
    STEP_KEY_BENEFITS,
    STEP_KEY_COMPANY,
    STEP_KEY_LANDING,
    STEP_KEY_SUMMARY,
    UI_PREFERENCE_CONFIDENCE_THRESHOLD,
)
from question_limits import (
    select_questions_for_step_scope,
    select_questions_for_step_scope_from_plan,
)
from question_dependencies import should_show_question
from schemas import JobAdExtract, Question, QuestionPlan, QuestionStep
from step_status import StepStatusPayload, build_step_status_payload
from state import get_answer_meta, get_answers, mark_answer_touched, set_answer


def _load_question_plan_from_state() -> QuestionPlan | None:
    plan_dict = st.session_state.get(SSKey.QUESTION_PLAN.value)
    if not isinstance(plan_dict, dict):
        return None
    try:
        return QuestionPlan.model_validate(plan_dict)
    except Exception:
        return None


def _read_progress_confidence_threshold() -> float | None:
    preferences_raw = st.session_state.get(SSKey.UI_PREFERENCES.value, {})
    if not isinstance(preferences_raw, dict):
        return None
    try:
        return max(
            0.0,
            min(1.0, float(preferences_raw.get(UI_PREFERENCE_CONFIDENCE_THRESHOLD))),
        )
    except (TypeError, ValueError):
        return None


def _get_step_questions_from_plan(
    plan: QuestionPlan | None,
    step_key: str,
    *,
    answers: dict[str, object],
    answer_meta: dict[str, object],
    job_extract: JobAdExtract | None,
    intake_facts: dict[str, object],
    intake_fact_evidence: dict[str, object],
    confidence_threshold: float | None,
) -> list[Question]:
    limits_raw = st.session_state.get(SSKey.QUESTION_LIMITS.value, {})
    return select_questions_for_step_scope_from_plan(
        plan,
        step_key,
        question_limits=limits_raw if isinstance(limits_raw, dict) else None,
        answers=answers,
        answer_meta=answer_meta,
        job_extract=job_extract,
        intake_facts=intake_facts,
        intake_fact_evidence=intake_fact_evidence,
        confidence_threshold=confidence_threshold,
    )


def _process_progress_status(
    *,
    step_key: str,
    title_de: str,
    questions: list[Question],
    answers: dict[str, object],
    answer_meta: dict[str, object],
    job_extract: JobAdExtract | None,
    intake_facts: dict[str, object],
    intake_fact_evidence: dict[str, object],
    confidence_threshold: float | None,
) -> tuple[str, str]:
    status = build_step_status_payload(
        step=QuestionStep(step_key=step_key, title_de=title_de, questions=questions),
        answers=answers,
        answer_meta=answer_meta,
        should_show_question=should_show_question,
        step_key=step_key,
        job_extract=job_extract,
        intake_facts=intake_facts,
        intake_fact_evidence=intake_fact_evidence,
        confidence_threshold=confidence_threshold,
    )
    if status["total"] > 0:
        return status["completion_state"], f"{status['answered']}/{status['total']}"

    if step_key == STEP_KEY_SUMMARY:
        has_brief = bool(st.session_state.get(SSKey.BRIEF.value))
        if has_brief:
            return "complete", ""
        if any(value for value in answers.values()):
            return "partial", ""
    return "not_started", ""


def render_intake_process_progress(current_step_key: str) -> None:
    process_steps = [step for step in STEPS if step.key != STEP_KEY_LANDING]
    process_keys = [step.key for step in process_steps]
    if current_step_key not in process_keys:
        return

    plan = _load_question_plan_from_state()
    answers = get_answers()
    answer_meta = get_answer_meta()
    job_extract = _load_job_extract_from_state()
    intake_facts_raw = st.session_state.get(SSKey.INTAKE_FACTS.value)
    intake_facts = intake_facts_raw if isinstance(intake_facts_raw, dict) else {}
    intake_fact_evidence_raw = st.session_state.get(SSKey.INTAKE_FACT_EVIDENCE.value)
    intake_fact_evidence = (
        intake_fact_evidence_raw if isinstance(intake_fact_evidence_raw, dict) else {}
    )
    confidence_threshold = _read_progress_confidence_threshold()
    items: list[dict[str, object]] = []
    for step in process_steps:
        questions = _get_step_questions_from_plan(
            plan,
            step.key,
            answers=answers,
            answer_meta=answer_meta,
            job_extract=job_extract,
            intake_facts=intake_facts,
            intake_fact_evidence=intake_fact_evidence,
            confidence_threshold=confidence_threshold,
        )
        status, count = _process_progress_status(
            step_key=step.key,
            title_de=step.title_de,
            questions=questions,
            answers=answers,
            answer_meta=answer_meta,
            job_extract=job_extract,
            intake_facts=intake_facts,
            intake_fact_evidence=intake_fact_evidence,
            confidence_threshold=confidence_threshold,
        )
        title = f"{step.title_de}: {count} beantwortet" if count else step.title_de
        items.append(
            {
                "label": step.title_de,
                "status": status,
                "count": count,
                "current": step.key == current_step_key,
                "title": title,
            }
        )
    if items and process_keys[0] == STEP_KEY_COMPANY:
        render_process_progress(items)




def responsive_two_columns(*, gap: str = "large") -> tuple:
    """Render 2 columns on desktop and 1 column on mobile/tablet user agents."""
    user_agent = str(st.context.headers.get("User-Agent", "")).casefold()
    is_mobile_or_tablet = any(
        marker in user_agent
        for marker in (
            "iphone",
            "android",
            "ipad",
            "mobile",
            "tablet",
        )
    )
    if is_mobile_or_tablet:
        return (st.container(), st.container())
    return tuple(st.columns(2, gap=gap))


def responsive_three_columns(*, gap: str = "large") -> tuple:
    """Render 3 columns on wide desktop, 2 on narrow desktop, and 1 on mobile/tablet."""
    user_agent = str(st.context.headers.get("User-Agent", "")).casefold()
    is_mobile_or_tablet = any(
        marker in user_agent
        for marker in (
            "iphone",
            "android",
            "ipad",
            "mobile",
            "tablet",
        )
    )
    if is_mobile_or_tablet:
        return (st.container(), st.container(), st.container())

    viewport_header = (
        st.context.headers.get("Sec-CH-Viewport-Width")
        or st.context.headers.get("Viewport-Width")
        or ""
    )
    viewport_width: int | None = None
    try:
        cleaned = str(viewport_header).split(",", 1)[0].strip()
        if cleaned:
            viewport_width = int(cleaned)
    except (TypeError, ValueError):
        viewport_width = None

    if viewport_width is not None and viewport_width < 1280:
        col_left, col_right = st.columns(2, gap=gap)
        return (col_left, col_right, st.container())
    return tuple(st.columns(3, gap=gap))


def _status_badge_text(completion_state: str) -> str:
    return COMPLETION_STATE_BADGE_TEXT.get(
        completion_state, COMPLETION_STATE_BADGE_TEXT[COMPLETION_STATE_NOT_STARTED]
    )


def _truncate_missing_essentials(
    missing_essentials: list[str], max_items: int = 4
) -> str:
    compact_items = [item.strip() for item in missing_essentials if item.strip()]
    shown_items = compact_items[:max_items]
    if not shown_items:
        return ""
    suffix = " …" if len(compact_items) > len(shown_items) else ""
    return ", ".join(shown_items) + suffix


def _render_step_status(status: StepStatusPayload | None) -> None:
    if status is None:
        st.caption("⬜ Offen")
        st.caption("0/0 beantwortet")
        return

    badge_text = _status_badge_text(status["completion_state"])
    st.caption(badge_text)
    st.caption(f"{status['answered']}/{status['total']} beantwortet")
    missing_summary = _truncate_missing_essentials(status["missing_essentials"])
    if missing_summary:
        st.caption(f"Fehlt (essentiell): {missing_summary}")


def _render_step_section_heading(label: str) -> None:
    if not str(label or "").strip():
        return
    st.markdown(
        f'<div class="cs-step-section-heading">{label}</div>',
        unsafe_allow_html=True,
    )


def _normalize_jobspec_note(note: Any) -> str:
    return " ".join(str(note or "").strip().split())


def _dedupe_jobspec_notes(notes: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for note in notes:
        normalized = _normalize_jobspec_note(note)
        if not normalized:
            continue
        dedupe_key = normalized.casefold()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        deduped.append(normalized)
    return deduped


def resolve_jobspec_note_step(note: str) -> str | None:
    normalized = _normalize_jobspec_note(note).casefold()
    if not normalized:
        return None

    best_step_key: str | None = None
    best_score = 0
    for step_key in JOBSPEC_NOTE_ROUTE_STEP_KEYS:
        keywords = JOBSPEC_NOTE_ROUTE_KEYWORDS.get(step_key, ())
        score = sum(1 for keyword in keywords if keyword.casefold() in normalized)
        if step_key == STEP_KEY_BENEFITS and any(
            keyword in normalized
            for keyword in ("salary", "gehalt", "vergütung", "compensation")
        ):
            score += 2
        if score > best_score:
            best_step_key = step_key
            best_score = score
    return best_step_key


def _jobspec_notes_for_step(notes: list[str], *, step_key: str) -> list[str]:
    return _dedupe_jobspec_notes(
        [note for note in notes if resolve_jobspec_note_step(note) == step_key]
    )


def _load_job_extract_from_state() -> JobAdExtract | None:
    raw_job = st.session_state.get(SSKey.JOB_EXTRACT.value)
    if not isinstance(raw_job, dict):
        return None
    try:
        return JobAdExtract.model_validate(raw_job)
    except Exception:
        return None


def _render_jobspec_note_block(title: str, notes: list[str], *, tone: str) -> None:
    cleaned = _dedupe_jobspec_notes(notes)
    if not cleaned:
        return
    body = "\n".join(f"- {note}" for note in cleaned)
    if tone == "warning":
        st.warning(f"**{title}**\n\n{body}")
    else:
        st.info(f"**{title}**\n\n{body}")


def _jobspec_assumption_answer_id(*, step_key: str, note: str) -> str:
    note_hash = hashlib.sha1(
        _normalize_jobspec_note(note).casefold().encode("utf-8")
    ).hexdigest()[:12]
    return f"{JOBSPEC_ASSUMPTION_ANSWER_ID_PREFIX}{step_key}.{note_hash}"


def _coerce_assumption_answer(raw_value: Any) -> dict[str, str]:
    if not isinstance(raw_value, dict):
        return {"status": "", "correction": ""}
    status = str(raw_value.get("status") or "").strip()
    if status not in {"confirmed", "rejected"}:
        status = ""
    return {
        "status": status,
        "correction": str(raw_value.get("correction") or "").strip(),
    }


def _render_assumption_decision(*, step_key: str, note: str) -> None:
    answer_id = _jobspec_assumption_answer_id(step_key=step_key, note=note)
    answers = get_answers()
    previous_value = _coerce_assumption_answer(answers.get(answer_id))
    status_by_label = {
        "Bestätigt": "confirmed",
        "Ablehnen & korrigieren": "rejected",
    }
    label_by_status = {value: label for label, value in status_by_label.items()}
    current_label = label_by_status.get(previous_value["status"])
    options = tuple(status_by_label)
    widget_key = f"cs.jobspec.assumption.{step_key}.{answer_id.rsplit('.', 1)[-1]}"

    if hasattr(st, "segmented_control"):
        selected_label = st.segmented_control(
            "Annahme prüfen",
            options=options,
            default=current_label,
            key=widget_key,
        )
    else:
        selected_label = st.radio(
            "Annahme prüfen",
            options=options,
            index=options.index(current_label) if current_label in options else None,
            horizontal=True,
            key=widget_key,
        )

    if selected_label not in status_by_label:
        return

    status = status_by_label[str(selected_label)]
    correction = previous_value["correction"]
    if status == "rejected":
        correction = st.text_area(
            "Korrektur",
            value=correction,
            key=f"{widget_key}.correction",
            height=90,
            placeholder="Korrekte Annahme oder Klarstellung eintragen",
        ).strip()

    current_value = {"status": status, "correction": correction}
    mark_answer_touched(answer_id, previous_value, current_value)
    set_answer(answer_id, current_value)


def render_jobspec_step_notes(step_key: str | None) -> None:
    if not step_key or step_key in NON_INTAKE_STEP_KEYS:
        return
    if step_key not in JOBSPEC_NOTE_ROUTE_STEP_KEYS:
        return

    job = _load_job_extract_from_state()
    if job is None:
        return

    gaps = _jobspec_notes_for_step(list(job.gaps), step_key=step_key)
    assumptions = _jobspec_notes_for_step(list(job.assumptions), step_key=step_key)
    if not gaps and not assumptions:
        return

    _render_jobspec_note_block(
        "Fehlende oder unklare Angaben",
        gaps,
        tone="warning",
    )
    if not assumptions:
        return

    _render_jobspec_note_block("Annahmen", assumptions, tone="info")
    for note in assumptions:
        st.write(f"**{note}**")
        _render_assumption_decision(step_key=step_key, note=note)


def render_step_shell(
    *,
    title: str,
    subtitle: str,
    outcome_text: str | None = None,
    outcome_slot: Callable[[], None] | None = None,
    step: QuestionStep | None = None,
    extracted_from_jobspec_slot: Callable[[], None] | None = None,
    extracted_from_jobspec_label: str = "Aus Jobspec extrahiert",
    extracted_from_jobspec_use_expander: bool = True,
    source_comparison_slot: Callable[[], None] | None = None,
    salary_forecast_slot: Callable[[], None] | None = None,
    open_questions_slot: Callable[[], None] | None = None,
    main_content_slot: Callable[[], None] | None = None,
    review_slot: Callable[[], None] | None = None,
    after_review_slot: Callable[[], None] | None = None,
    post_review_slot: Callable[[], None] | None = None,
    footer_slot: Callable[[], None] | None = None,
    status_position: Literal["header", "before_footer"] = "header",
) -> None:
    answers = get_answers()
    answer_meta = get_answer_meta()
    job_extract = _load_job_extract_from_state()
    intake_facts_raw = st.session_state.get(SSKey.INTAKE_FACTS.value)
    intake_facts = intake_facts_raw if isinstance(intake_facts_raw, dict) else {}
    intake_fact_evidence_raw = st.session_state.get(SSKey.INTAKE_FACT_EVIDENCE.value)
    intake_fact_evidence = (
        intake_fact_evidence_raw if isinstance(intake_fact_evidence_raw, dict) else {}
    )
    confidence_threshold = _read_progress_confidence_threshold()
    status_step = step
    if step is not None:
        limits_raw = st.session_state.get(SSKey.QUESTION_LIMITS.value, {})
        status_questions = select_questions_for_step_scope(
            step.questions,
            step_key=step.step_key,
            question_limits=limits_raw if isinstance(limits_raw, dict) else None,
            answers=answers,
            answer_meta=answer_meta,
            job_extract=job_extract,
            intake_facts=intake_facts,
            intake_fact_evidence=intake_fact_evidence,
            confidence_threshold=confidence_threshold,
        )
        status_step = QuestionStep(
            step_key=step.step_key,
            title_de=step.title_de,
            description_de=step.description_de,
            questions=status_questions,
        )
    status = build_step_status_payload(
        step=status_step,
        answers=answers,
        answer_meta=answer_meta,
        should_show_question=should_show_question,
        step_key=step.step_key if step is not None else None,
        job_extract=job_extract,
        intake_facts=intake_facts,
        intake_fact_evidence=intake_fact_evidence,
        confidence_threshold=confidence_threshold,
    )
    header_meta: list[tuple[str, str, str]] = []
    if status_position == "header":
        badge_text = (
            _status_badge_text(status["completion_state"]) if status is not None else "⬜ Offen"
        )
        answered_text = (
            f"{status['answered']}/{status['total']} beantwortet" if status is not None else "0/0 beantwortet"
        )
        header_meta.append(("📌", "Status", badge_text))
        header_meta.append(("📊", "Fortschritt", answered_text))
        if status is not None:
            missing_summary = _truncate_missing_essentials(status["missing_essentials"])
            if missing_summary:
                header_meta.append(("⚠️", "Fehlt (essentiell)", missing_summary))

    render_step_header(title, subtitle, outcome=outcome_text, meta_items=header_meta)
    if outcome_slot is not None:
        outcome_slot()

    if extracted_from_jobspec_slot is not None:
        _render_step_section_heading(extracted_from_jobspec_label)
        extracted_from_jobspec_slot()
        render_jobspec_step_notes(step.step_key if step is not None else None)

    uses_new_slots = any(
        slot is not None
        for slot in (
            source_comparison_slot,
            salary_forecast_slot,
            open_questions_slot,
        )
    )
    if uses_new_slots:
        if source_comparison_slot is not None:
            source_comparison_slot()
        if salary_forecast_slot is not None:
            salary_forecast_slot()
        if open_questions_slot is not None:
            open_questions_slot()
    elif main_content_slot is not None:
        main_content_slot()
    if review_slot is not None:
        review_slot()
    if after_review_slot is not None:
        after_review_slot()
    if post_review_slot is not None:
        post_review_slot()

    if status_position == "before_footer":
        _render_step_status(status)

    if footer_slot is not None:
        st.divider()
        footer_slot()
