"""Reusable page layout shells for wizard steps."""

from __future__ import annotations

import base64
import hashlib
import json
from time import perf_counter
from collections.abc import Callable
from collections.abc import Mapping
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import quote

import streamlit as st

from components.design_system import (
    build_step_section_heading_html,
    render_process_progress,
    render_step_header,
)
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
    STEP_KEY_INTRO,
    STEP_KEY_LANDING,
    STEP_KEY_SUMMARY,
    STEP_SECTION_SLOT_NAMES,
    UI_PREFERENCE_DETAILS_EXPANDED_DEFAULT,
    WIZARD_STEP_QUERY_PARAM,
)
from schemas import QuestionPlan, QuestionStep
from step_payload import (
    StepPayload,
    build_step_payload,
    build_step_payload_from_state,
    load_intake_fact_evidence_from_state,
    load_intake_facts_from_state,
    load_job_extract_from_state,
    read_confidence_threshold_from_state,
    read_question_limits_from_state,
)
from step_sections import section_status_summary
from step_status import StepStatusPayload
from state import get_answer_meta, get_answers, mark_answer_touched, set_answer
from safe_html import escape_html_text, render_static_html
from usage_events import record_enrichment_timed


def _load_question_plan_from_state() -> QuestionPlan | None:
    plan_dict = st.session_state.get(SSKey.QUESTION_PLAN.value)
    if not isinstance(plan_dict, dict):
        return None
    try:
        return QuestionPlan.model_validate(plan_dict)
    except Exception:
        return None


_PROCESS_PROGRESS_STATUS_LABELS: dict[str, str] = {
    "complete": "Fertig",
    "partial": "In Arbeit",
    "not_started": "Offen",
}

_PROCESS_PROGRESS_DETAIL_LABELS: dict[str, str] = {
    STEP_KEY_INTRO: "Kontext",
    STEP_KEY_LANDING: "Quelle & Analyse",
    STEP_KEY_SUMMARY: "Review & Export",
}


def _wizard_step_href(step_key: str) -> str:
    return f"?{WIZARD_STEP_QUERY_PARAM}={quote(step_key, safe='')}"


def _process_progress_status_from_payload(
    *,
    step_key: str,
    payload: StepPayload,
    answers: dict[str, object],
) -> tuple[str, str]:
    status = payload["step_status"]
    if status["total"] > 0:
        return status["completion_state"], f"{status['answered']}/{status['total']}"

    if step_key == STEP_KEY_INTRO:
        return "complete", ""

    if step_key == STEP_KEY_LANDING:
        has_job_extract = bool(st.session_state.get(SSKey.JOB_EXTRACT.value))
        has_question_plan = bool(st.session_state.get(SSKey.QUESTION_PLAN.value))
        source_text = str(st.session_state.get(SSKey.SOURCE_TEXT.value) or "").strip()
        if has_job_extract and has_question_plan:
            return "complete", ""
        if has_job_extract or has_question_plan or source_text:
            return "partial", ""
        return "not_started", ""

    if step_key == STEP_KEY_SUMMARY:
        has_brief = bool(st.session_state.get(SSKey.BRIEF.value))
        if has_brief:
            return "complete", ""
        if any(value for value in answers.values()):
            return "partial", ""
    return "not_started", ""


def render_intake_process_progress(current_step_key: str) -> None:
    process_steps = list(STEPS)
    process_keys = [step.key for step in process_steps]
    if current_step_key not in process_keys:
        return

    plan = _load_question_plan_from_state()
    answers = get_answers()
    answer_meta = get_answer_meta()
    question_limits = read_question_limits_from_state(st.session_state)
    job_extract = load_job_extract_from_state(st.session_state)
    intake_facts = load_intake_facts_from_state(st.session_state)
    intake_fact_evidence = load_intake_fact_evidence_from_state(st.session_state)
    confidence_threshold = read_confidence_threshold_from_state(st.session_state)
    items: list[dict[str, object]] = []
    step_total = len(process_steps)
    for index, step in enumerate(process_steps, start=1):
        plan_step = (
            next((entry for entry in plan.steps if entry.step_key == step.key), None)
            if plan is not None
            else None
        )
        payload = build_step_payload(
            step=plan_step
            or QuestionStep(step_key=step.key, title_de=step.title_de, questions=[]),
            answers=answers,
            answer_meta=answer_meta,
            question_limits=question_limits,
            job_extract=job_extract,
            intake_facts=intake_facts,
            intake_fact_evidence=intake_fact_evidence,
            confidence_threshold=confidence_threshold,
        )
        status, count = _process_progress_status_from_payload(
            step_key=step.key,
            payload=payload,
            answers=answers,
        )
        status_label = _PROCESS_PROGRESS_STATUS_LABELS.get(status, "Offen")
        detail = count or _PROCESS_PROGRESS_DETAIL_LABELS.get(step.key, "")
        if count:
            title = f"{step.title_de}: {count} beantwortet"
        elif detail:
            title = f"{step.title_de}: {status_label}, {detail}"
        else:
            title = f"{step.title_de}: {status_label}"
        items.append(
            {
                "key": step.key,
                "label": step.title_de,
                "icon": step.icon,
                "status": status,
                "status_label": status_label,
                "count": count,
                "detail": detail,
                "current": step.key == current_step_key,
                "title": title,
                "href": _wizard_step_href(step.key),
                "step_index": index,
                "step_total": step_total,
            }
        )
    if items:
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
    heading_html = build_step_section_heading_html(label)
    if not heading_html:
        return
    render_static_html(
        heading_html,
        streamlit_module=st,
    )


@dataclass(frozen=True)
class LazySectionConfig:
    """Config for expensive step sections that should render only after reveal."""

    label: str
    caption: str
    button_label: str = "Anzeigen / laden"
    default_open: bool = False


def default_lazy_source_section_open() -> bool:
    preferences_raw = st.session_state.get(SSKey.UI_PREFERENCES.value, {})
    preferences = preferences_raw if isinstance(preferences_raw, dict) else {}
    configured = preferences.get(UI_PREFERENCE_DETAILS_EXPANDED_DEFAULT)
    if isinstance(configured, bool):
        return configured

    ui_mode = str(st.session_state.get(SSKey.UI_MODE.value, "")).strip().lower()
    return ui_mode == "expert"


def _lazy_section_state_key(*, step_key: str, slot_name: str) -> str:
    normalized_step_key = str(step_key or "unknown").strip() or "unknown"
    normalized_slot_name = str(slot_name or "slot").strip() or "slot"
    return f"cs.lazy_section.{normalized_step_key}.{normalized_slot_name}.revealed"


def _deep_link_target_for_step(step_key: str) -> dict[str, str]:
    raw_target = st.session_state.get(SSKey.NAV_DEEP_LINK_TARGET.value, {})
    if not isinstance(raw_target, Mapping):
        return {}
    target_step = str(raw_target.get("target_step") or "").strip()
    if not target_step or target_step != step_key:
        return {}
    return {
        "target_step": target_step,
        "target_section": str(raw_target.get("target_section") or "").strip(),
        "target_fact_key": str(raw_target.get("target_fact_key") or "").strip(),
        "target_question_id": str(raw_target.get("target_question_id") or "").strip(),
        "label": str(raw_target.get("label") or "").strip(),
        "source": str(raw_target.get("source") or "").strip(),
    }


def _deep_link_slot_name(target: Mapping[str, str]) -> str:
    target_section = str(target.get("target_section") or "").strip()
    if not target_section:
        return ""
    return str(STEP_SECTION_SLOT_NAMES.get(target_section, "") or "")


def _deep_link_anchor_id(*, step_key: str, slot_name: str) -> str:
    safe_step = "".join(
        char if char.isalnum() or char in {"-", "_"} else "-"
        for char in str(step_key or "step").strip()
    )
    safe_slot = "".join(
        char if char.isalnum() or char in {"-", "_"} else "-"
        for char in str(slot_name or "section").strip()
    )
    return f"cs-step-section-{safe_step}-{safe_slot}"


def _clear_deep_link_target() -> None:
    st.session_state[SSKey.NAV_DEEP_LINK_TARGET.value] = {}


def _render_deep_link_focus_notice(target: Mapping[str, str]) -> None:
    label = str(target.get("label") or "").strip()
    message = "Sprungziel aus der Zusammenfassung."
    if label:
        message = f"{message} Bitte prüfe: {label}"
    st.info(message)


def _render_deep_link_anchor(anchor_id: str) -> None:
    render_static_html(
        f'<div id="{escape_html_text(anchor_id, quote=True)}" class="cs-deep-link-anchor"></div>',
        streamlit_module=st,
    )


def _scroll_to_deep_link_anchor(anchor_id: str) -> None:
    scroll_script = f"""
        <script>
        const anchorId = {json.dumps(anchor_id)};
        const scrollToAnchor = () => {{
            try {{
                const targetWindow = window.parent || window;
                const doc = targetWindow.document || document;
                const anchor = doc.getElementById(anchorId);
                if (anchor && typeof anchor.scrollIntoView === "function") {{
                    anchor.scrollIntoView({{ behavior: "smooth", block: "start" }});
                }}
            }} catch (error) {{
                const anchor = document.getElementById(anchorId);
                if (anchor && typeof anchor.scrollIntoView === "function") {{
                    anchor.scrollIntoView({{ behavior: "smooth", block: "start" }});
                }}
            }}
        }};
        scrollToAnchor();
        if (typeof window.requestAnimationFrame === "function") {{
            window.requestAnimationFrame(scrollToAnchor);
        }}
        window.setTimeout(scrollToAnchor, 50);
        window.setTimeout(scrollToAnchor, 200);
        window.setTimeout(scrollToAnchor, 500);
        </script>
    """
    iframe = getattr(st, "iframe", None)
    if callable(iframe):
        encoded_html = base64.b64encode(scroll_script.encode("utf-8")).decode("ascii")
        iframe(f"data:text/html;base64,{encoded_html}", height=1)
        return
    render_static_html(scroll_script, streamlit_module=st)


def render_lazy_section(
    *,
    step_key: str,
    slot_name: str,
    config: LazySectionConfig,
    render_slot: Callable[[], None],
) -> None:
    state_key = _lazy_section_state_key(step_key=step_key, slot_name=slot_name)
    if state_key not in st.session_state and config.default_open:
        st.session_state[state_key] = True

    _render_step_section_heading(config.label)
    revealed = bool(st.session_state.get(state_key, False))
    if not revealed:
        if config.caption:
            st.caption(config.caption)
        if st.button(
            config.button_label,
            key=f"{state_key}.button",
            width="stretch",
        ):
            st.session_state[state_key] = True
            revealed = True

    if revealed:
        render_slot()


def perf_fragment_pilot_enabled() -> bool:
    """Return whether the internal fragment pilot can run in this session."""
    return bool(st.session_state.get(SSKey.PERF_FRAGMENT_PILOT_ENABLED.value, False)) and callable(
        getattr(st, "fragment", None)
    )


def render_timed_panel(
    *,
    step_key: str,
    panel_id: str,
    render_slot: Callable[[], None],
    fragment_enabled: bool = False,
) -> None:
    """Render a panel and record non-sensitive render timing metadata."""
    started_at = perf_counter()
    status = "success"
    try:
        render_slot()
    except Exception:
        status = "error"
        raise
    finally:
        record_enrichment_timed(
            st.session_state,
            stage="render_panel",
            path=f"{step_key}.{panel_id}",
            duration_ms=round((perf_counter() - started_at) * 1000),
            status=status,
            fragment_enabled=fragment_enabled,
        )


def render_fragment_pilot_panel(
    *,
    step_key: str,
    panel_id: str,
    render_slot: Callable[[], None],
) -> None:
    """Render a self-contained panel through ``st.fragment`` when enabled."""
    use_fragment = perf_fragment_pilot_enabled()

    def _render_panel() -> None:
        render_timed_panel(
            step_key=step_key,
            panel_id=panel_id,
            render_slot=render_slot,
            fragment_enabled=use_fragment,
        )

    if not use_fragment:
        _render_panel()
        return

    fragment = getattr(st, "fragment")
    fragment(_render_panel)()


StepShellSlotName = Literal[
    "extracted_from_jobspec_slot",
    "main_content_slot",
    "source_comparison_slot",
    "salary_forecast_slot",
    "open_questions_slot",
    "review_slot",
]


def render_grouped_step_section(
    *,
    label: str,
    caption: str = "",
    render_slot: Callable[[], None],
    expanded: bool = True,
) -> None:
    """Render a named step section with a consistent compact wrapper."""
    if expanded:
        _render_step_section_heading(label)
        if caption:
            st.caption(caption)
        render_slot()
        return

    expander = getattr(st, "expander", None)
    if callable(expander):
        with expander(label, expanded=False):
            if caption:
                st.caption(caption)
            render_slot()
        return

    _render_step_section_heading(label)
    if caption:
        st.caption(caption)
    render_slot()


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

    job = load_job_extract_from_state(st.session_state)
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
    lazy_section_configs: Mapping[str, LazySectionConfig] | None = None,
    section_order: Sequence[StepShellSlotName] | None = None,
) -> None:
    current_step_key = step.step_key if step is not None else ""
    answers = get_answers()
    answer_meta = get_answer_meta()
    step_payload = build_step_payload_from_state(
        step,
        session_state=st.session_state,
        answers=answers,
        answer_meta=answer_meta,
    )
    status = step_payload["step_status"]
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
        complete_sections, total_sections = section_status_summary(
            step_payload["section_statuses"]
        )
        if total_sections:
            header_meta.append(
                ("🧩", "Abschnitte", f"{complete_sections}/{total_sections} geklärt")
            )

    render_step_header(title, subtitle, outcome=outcome_text, meta_items=header_meta)
    if outcome_slot is not None:
        outcome_slot()

    deep_link_target = _deep_link_target_for_step(current_step_key)
    deep_link_slot = _deep_link_slot_name(deep_link_target)
    deep_link_rendered = False
    if deep_link_slot and (lazy_section_configs or {}).get(deep_link_slot) is not None:
        st.session_state[
            _lazy_section_state_key(
                step_key=current_step_key,
                slot_name=deep_link_slot,
            )
        ] = True
    if deep_link_target and not deep_link_slot:
        _render_deep_link_focus_notice(deep_link_target)
        _clear_deep_link_target()
        deep_link_rendered = True

    def _render_extracted_section() -> None:
        if extracted_from_jobspec_slot is None:
            return
        if extracted_from_jobspec_label:
            _render_step_section_heading(extracted_from_jobspec_label)
        extracted_from_jobspec_slot()
        render_jobspec_step_notes(step.step_key if step is not None else None)

    def _render_source_section() -> None:
        if source_comparison_slot is None:
            return
        config = (lazy_section_configs or {}).get("source_comparison_slot")
        if config is not None:
            render_lazy_section(
                step_key=step.step_key if step is not None else "",
                slot_name="source_comparison_slot",
                config=config,
                render_slot=source_comparison_slot,
            )
        else:
            source_comparison_slot()

    def _render_salary_section() -> None:
        if salary_forecast_slot is None:
            return
        config = (lazy_section_configs or {}).get("salary_forecast_slot")
        if config is not None:
            render_lazy_section(
                step_key=step.step_key if step is not None else "",
                slot_name="salary_forecast_slot",
                config=config,
                render_slot=salary_forecast_slot,
            )
        else:
            salary_forecast_slot()

    section_renderers: dict[str, Callable[[], None]] = {
        "extracted_from_jobspec_slot": _render_extracted_section,
        "main_content_slot": main_content_slot or (lambda: None),
        "source_comparison_slot": _render_source_section,
        "salary_forecast_slot": _render_salary_section,
        "open_questions_slot": open_questions_slot or (lambda: None),
        "review_slot": review_slot or (lambda: None),
    }
    has_registered_slots = any(
        slot is not None
        for slot in (
            extracted_from_jobspec_slot,
            main_content_slot,
            source_comparison_slot,
            salary_forecast_slot,
            open_questions_slot,
            review_slot,
        )
    )
    def _render_section_with_deep_link_focus(slot_name: str) -> None:
        nonlocal deep_link_rendered
        is_target_slot = bool(
            deep_link_target and deep_link_slot and str(slot_name) == deep_link_slot
        )
        if is_target_slot:
            anchor_id = _deep_link_anchor_id(
                step_key=current_step_key,
                slot_name=str(slot_name),
            )
            _render_deep_link_anchor(anchor_id)
            _render_deep_link_focus_notice(deep_link_target)
            _scroll_to_deep_link_anchor(anchor_id)
        section_renderers[str(slot_name)]()
        if is_target_slot:
            _clear_deep_link_target()
            deep_link_rendered = True

    if has_registered_slots:
        default_order: tuple[StepShellSlotName, ...] = (
            "extracted_from_jobspec_slot",
            "main_content_slot",
            "source_comparison_slot",
            "salary_forecast_slot",
            "open_questions_slot",
            "review_slot",
        )
        resolved_order = tuple(section_order or default_order)
        for slot_name in resolved_order:
            if slot_name == "extracted_from_jobspec_slot" and extracted_from_jobspec_slot is None:
                continue
            if slot_name == "main_content_slot" and main_content_slot is None:
                continue
            if slot_name == "source_comparison_slot" and source_comparison_slot is None:
                continue
            if slot_name == "salary_forecast_slot" and salary_forecast_slot is None:
                continue
            if slot_name == "open_questions_slot" and open_questions_slot is None:
                continue
            if slot_name == "review_slot" and review_slot is None:
                continue
            _render_section_with_deep_link_focus(str(slot_name))
    if deep_link_target and not deep_link_rendered:
        _clear_deep_link_target()
    if after_review_slot is not None:
        after_review_slot()
    if post_review_slot is not None:
        post_review_slot()

    if status_position == "before_footer":
        _render_step_status(status)

    if footer_slot is not None:
        st.divider()
        footer_slot()
