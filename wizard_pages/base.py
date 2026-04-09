"""Wizard base utilities (page model + navigation helpers)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Literal, Mapping, Sequence, TypedDict

import streamlit as st

from constants import SSKey, STEPS
from question_dependencies import should_show_question
from question_progress import compute_question_progress
from schemas import Question, QuestionPlan


@dataclass(frozen=True)
class WizardPage:
    key: str
    title_de: str
    icon: str
    render: Callable[["WizardContext"], None]
    requires_jobspec: bool = False

    @property
    def label(self) -> str:
        return f"{self.icon} {self.title_de}" if self.icon else self.title_de


@dataclass
class WizardContext:
    pages: List[WizardPage]

    def get_current_page_key(self) -> str:
        return st.session_state.get(SSKey.CURRENT_STEP.value, STEPS[0].key)

    def goto(self, key: str) -> None:
        set_current_step(key)

    def next(self) -> None:
        cur = self.get_current_page_key()
        keys = [p.key for p in self.pages]
        if cur in keys:
            i = keys.index(cur)
            if i < len(keys) - 1:
                self.goto(keys[i + 1])

    def prev(self) -> None:
        cur = self.get_current_page_key()
        keys = [p.key for p in self.pages]
        if cur in keys:
            i = keys.index(cur)
            if i > 0:
                self.goto(keys[i - 1])


StepStatus = Literal["complete", "partial", "not_started"]


class SidebarStepProgress(TypedDict):
    key: str
    status: StepStatus
    answered: int
    total: int


def _status_prefix(status: StepStatus) -> str:
    if status == "complete":
        return "✅"
    if status == "partial":
        return "🟡"
    return "⬜"


def set_current_step(key: str, *, sync_navigation: bool = True) -> None:
    st.session_state[SSKey.CURRENT_STEP.value] = key
    if sync_navigation:
        st.session_state[SSKey.NAV_SYNC_PENDING.value] = True


def _get_step_questions(plan: QuestionPlan | None, step_key: str) -> list[Question]:
    if plan is None:
        return []
    step = next((entry for entry in plan.steps if entry.step_key == step_key), None)
    if step is None:
        return []

    limits_raw = st.session_state.get(SSKey.QUESTION_LIMITS.value, {})
    step_limit: int | None = None
    if isinstance(limits_raw, dict):
        raw_limit = limits_raw.get(step_key)
        if isinstance(raw_limit, (int, float, str)):
            try:
                step_limit = int(raw_limit)
            except ValueError:
                step_limit = None

    questions = step.questions
    if step_limit is not None and step_limit > 0:
        questions = step.questions[:step_limit]
    return questions


def _compute_step_statuses(pages: Sequence[WizardPage]) -> list[SidebarStepProgress]:
    plan_dict = st.session_state.get(SSKey.QUESTION_PLAN.value)
    plan: QuestionPlan | None = None
    if isinstance(plan_dict, dict):
        try:
            plan = QuestionPlan.model_validate(plan_dict)
        except Exception:
            plan = None

    answers_raw = st.session_state.get(SSKey.ANSWERS.value, {})
    answers = answers_raw if isinstance(answers_raw, dict) else {}
    answer_meta_raw = st.session_state.get(SSKey.ANSWER_META.value, {})
    answer_meta = answer_meta_raw if isinstance(answer_meta_raw, dict) else {}
    has_job_extract = bool(st.session_state.get(SSKey.JOB_EXTRACT.value))
    has_brief = bool(st.session_state.get(SSKey.BRIEF.value))

    statuses: list[SidebarStepProgress] = []
    for page in pages:
        questions = _get_step_questions(plan, page.key)
        visible_questions = [
            question
            for question in questions
            if should_show_question(question, answers, answer_meta, page.key)
        ]
        progress = compute_question_progress(visible_questions, answers, answer_meta)
        answered = progress["answered"]
        total = progress["total"]

        status: StepStatus = "not_started"
        if total > 0:
            if answered == 0:
                status = "not_started"
            elif answered < total:
                status = "partial"
            else:
                status = "complete"
        elif page.key == "landing":
            status = "complete" if has_job_extract else "not_started"
        elif page.key == "jobad":
            source_text = st.session_state.get(SSKey.SOURCE_TEXT.value, "")
            has_source = isinstance(source_text, str) and bool(source_text.strip())
            if has_job_extract and plan is not None:
                status = "complete"
            elif has_source:
                status = "partial"
        elif page.key == "jobspec_review":
            if plan is not None:
                status = "complete"
            elif has_job_extract:
                status = "partial"
        elif page.key == "summary":
            if has_brief:
                status = "complete"
            elif any(value for value in answers.values()):
                status = "partial"

        statuses.append(
            {
                "key": page.key,
                "status": status,
                "answered": answered,
                "total": total,
            }
        )
    return statuses


def sidebar_navigation(ctx: WizardContext) -> WizardPage:
    pages = ctx.pages
    options = [p.key for p in pages]
    cur_key = ctx.get_current_page_key()
    if cur_key not in options:
        cur_key = options[0]
        set_current_step(cur_key)

    nav_key = SSKey.NAV_SELECTED.value
    nav_sync_pending = bool(st.session_state.get(SSKey.NAV_SYNC_PENDING.value, False))
    nav_selected = st.session_state.get(nav_key)
    if nav_sync_pending or nav_selected not in options:
        st.session_state[nav_key] = cur_key
        st.session_state[SSKey.NAV_SYNC_PENDING.value] = False

    step_statuses = _compute_step_statuses(pages)
    status_by_key = {entry["key"]: entry for entry in step_statuses}
    started_steps = sum(
        1 for entry in step_statuses if entry["status"] != "not_started"
    )
    total_steps = len(step_statuses)

    st.sidebar.markdown("### Wizard-Fortschritt")
    st.sidebar.caption(f"{started_steps}/{total_steps} Schritte bearbeitet")

    format_map: dict[str, str] = {}
    for page in pages:
        step_status = status_by_key.get(page.key)
        prefix = _status_prefix(step_status["status"]) if step_status else "⬜"
        progress_suffix = ""
        if step_status and step_status["total"] > 0:
            progress_suffix = f" · {step_status['answered']}/{step_status['total']}"
        format_map[page.key] = f"{prefix} {page.title_de}{progress_suffix}"

    def _format(k: str) -> str:
        return format_map.get(k, k)

    selected = st.sidebar.radio(
        "Wizard",
        options=options,
        key=nav_key,
        format_func=_format,
    )
    if selected != cur_key:
        set_current_step(selected, sync_navigation=False)
        st.rerun()

    current_page = next(p for p in pages if p.key == selected)
    return current_page


def nav_buttons(
    ctx: WizardContext, *, disable_next: bool = False, disable_prev: bool = False
) -> None:
    c1, c2, c3 = st.columns([1, 1, 3])
    with c1:
        back_clicked = st.button("← Zurück", disabled=disable_prev)
    with c2:
        next_clicked = st.button("Weiter →", disabled=disable_next)
    with c3:
        st.caption("Fortschritt wird automatisch in dieser Session gespeichert.")
    # rerun only in normal render flow; callbacks may be within disallowed rerun contexts
    if back_clicked:
        ctx.prev()
        st.rerun()
    if next_clicked:
        ctx.next()
        st.rerun()


LANDING_STYLE_TOKENS: dict[str, str] = {
    "card_radius": "14px",
    "section_spacing": "1.2rem 0 1.4rem 0",
    "muted_text_color": "rgba(220, 233, 255, 0.9)",
    "emphasis_border": "4px solid rgba(138, 184, 255, 0.95)",
    "emphasis_background": "linear-gradient(135deg, rgba(22, 58, 112, 0.56), rgba(14, 34, 67, 0.4))",
}


LANDING_SECTION_IDS: dict[str, str] = {
    "hero": "LANDING_HERO",
    "value_cards": "LANDING_VALUE_CARDS",
    "importance": "LANDING_IMPORTANCE",
    "flow": "LANDING_FLOW",
    "output": "LANDING_OUTPUT",
    "security": "LANDING_SECURITY",
}


LANDING_CTA_KEYS: dict[str, str] = {
    "start": "landing.start_intake",
    "consent": SSKey.CONTENT_SHARING_CONSENT.value,
    "debug": SSKey.DEBUG.value,
}


def render_landing_css(style_tokens: Mapping[str, str]) -> None:
    st.markdown(
        f"""
        <style>
            .landing-section {{
                margin: {style_tokens["section_spacing"]};
            }}

            .landing-hero {{
                background: linear-gradient(145deg, rgba(10, 27, 52, 0.9), rgba(8, 20, 40, 0.85));
                border: 1px solid rgba(167, 201, 255, 0.34);
                border-radius: 18px;
                padding: 1.6rem 1.45rem;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
            }}

            .landing-hero h1 {{
                margin: 0;
                font-size: clamp(1.6rem, 2.3vw, 2.45rem);
                line-height: 1.18;
                letter-spacing: 0.01em;
            }}

            .landing-hero-copy {{
                max-width: 66ch;
            }}

            .landing-subhead {{
                margin-top: 0.9rem;
                color: rgba(247, 249, 253, 0.95);
                line-height: 1.58;
                font-size: 1.05rem;
            }}

            .landing-card {{
                background: rgba(12, 27, 52, 0.78);
                border: 1px solid rgba(228, 236, 252, 0.2);
                border-radius: {style_tokens["card_radius"]};
                padding: 0.8rem 0.75rem;
                height: 100%;
            }}

            .landing-card h4 {{
                margin: 0 0 0.45rem 0;
                font-size: 1rem;
            }}

            .landing-card p {{
                margin: 0;
                color: rgba(245, 247, 251, 0.92);
                line-height: 1.5;
            }}

            .landing-emphasis {{
                background: {style_tokens["emphasis_background"]};
                border-left: {style_tokens["emphasis_border"]};
                border-radius: {style_tokens["card_radius"]};
                padding: 0.8rem 0.85rem 0.2rem 0.85rem;
                margin-bottom: 0.85rem;
            }}

            .landing-emphasis--subtle {{
                background: rgba(11, 26, 50, 0.42);
                border-left: 3px solid rgba(158, 189, 240, 0.45);
                padding-bottom: 0.65rem;
                margin-bottom: 0.65rem;
            }}

            .landing-problem-panel {{
                background: rgba(8, 19, 38, 0.28);
                border: 1px solid rgba(202, 219, 247, 0.16);
                border-radius: {style_tokens["card_radius"]};
                padding: 0.65rem 0.85rem;
            }}

            .landing-problem-list {{
                margin: 0.1rem 0 0 0;
                padding-left: 1rem;
                color: rgba(236, 243, 255, 0.88);
            }}

            .landing-problem-list li {{
                margin-bottom: 0.42rem;
                line-height: 1.35;
            }}

            .landing-problem-list strong {{
                color: rgba(244, 249, 255, 0.94);
            }}

            .landing-problem-caption {{
                color: rgba(214, 228, 252, 0.76);
                font-size: 0.84rem;
                margin-top: 0.45rem;
            }}

            .landing-flow-step {{
                background: rgba(9, 20, 42, 0.66);
                border: 1px solid rgba(227, 235, 251, 0.18);
                border-radius: 12px;
                padding: 0.75rem;
                min-height: 124px;
            }}

            .landing-list {{
                margin: 0.5rem 0 0 0;
                padding-left: 1.1rem;
            }}

            .landing-list li {{
                margin-bottom: 0.5rem;
                line-height: 1.45;
            }}

            .landing-caption {{
                color: {style_tokens["muted_text_color"]};
                font-size: 0.9rem;
                margin-top: 0.35rem;
            }}

            .landing-security-note {{
                background: rgba(8, 19, 40, 0.5);
                border: 1px solid rgba(225, 235, 252, 0.14);
                border-radius: {style_tokens["card_radius"]};
                padding: 0.8rem 0.95rem;
                color: rgba(229, 239, 255, 0.82);
                font-size: 0.9rem;
            }}

            @media (max-width: 900px) {{
                .landing-hero {{
                    padding: 1.2rem;
                }}

                .landing-hero-copy {{
                    max-width: 100%;
                }}

                .landing-flow-step {{
                    min-height: 0;
                }}
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero_section(
    ctx: WizardContext,
    *,
    section_id: str,
    headline: str,
    subhead: str,
    primary_cta: str,
    secondary_cta_hint: str,
    before_start_title: str = "",
    before_start_bullets: Sequence[str] = (),
    reassurance_line: str = "",
    extraction_helper_copy: str = "",
    next_step_line: str = "",
    post_cta_microcopy: str = "",
    value_cards: Sequence[tuple[str, str]],
    show_value_cards: bool = True,
    consent_given: bool,
    start_button_key: str,
    on_start: Callable[[], None],
    start_target: str,
) -> None:
    st.markdown(
        f'<section id="{section_id}" class="landing-section landing-hero">',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="landing-hero-copy">', unsafe_allow_html=True)
    st.markdown(f"<h1>{headline}</h1>", unsafe_allow_html=True)
    st.markdown(f'<p class="landing-subhead">{subhead}</p>', unsafe_allow_html=True)
    if st.button(
        primary_cta,
        key=start_button_key,
        type="primary",
        use_container_width=True,
        disabled=not consent_given,
    ):
        on_start()
        ctx.goto(start_target)
        st.rerun()
    st.markdown(
        f'<p class="landing-caption">{secondary_cta_hint}</p>',
        unsafe_allow_html=True,
    )
    if next_step_line:
        st.caption(next_step_line)
    has_more_details = any(
        [
            bool(before_start_title and before_start_bullets),
            bool(reassurance_line),
            bool(extraction_helper_copy),
            bool(post_cta_microcopy),
        ]
    )
    if has_more_details:
        with st.expander("Mehr erfahren", expanded=False):
            if before_start_title and before_start_bullets:
                st.markdown(f"#### {before_start_title}")
                st.markdown(
                    '<ul class="landing-list">'
                    + "".join(f"<li>{bullet}</li>" for bullet in before_start_bullets)
                    + "</ul>",
                    unsafe_allow_html=True,
                )
            if reassurance_line:
                st.caption(reassurance_line)
            if extraction_helper_copy:
                st.info(extraction_helper_copy, icon="ℹ️")
            if post_cta_microcopy:
                st.caption(post_cta_microcopy)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</section>", unsafe_allow_html=True)

    if show_value_cards and value_cards:
        st.markdown(
            f'<section id="{LANDING_SECTION_IDS["value_cards"]}" class="landing-section">',
            unsafe_allow_html=True,
        )
        st.markdown("### Wertbeitrag auf einen Blick")
        render_value_cards(value_cards=value_cards)
        st.markdown("</section>", unsafe_allow_html=True)


def render_value_cards(*, value_cards: Sequence[tuple[str, str]]) -> None:
    # Keep predictable 2-column rhythm to avoid narrow, uneven cards.
    for row_start in range(0, len(value_cards), 2):
        row_cols = st.columns(2, gap="small")
        for col, (title, body) in zip(row_cols, value_cards[row_start : row_start + 2]):
            with col:
                st.markdown(
                    f'<div class="landing-card"><h4>{title}</h4><p>{body}</p></div>',
                    unsafe_allow_html=True,
                )


def render_importance_section(
    *,
    section_id: str,
    title: str,
    intro: str,
    points: Sequence[tuple[str, str]],
    closer: str,
) -> None:
    st.markdown(
        f'<section id="{section_id}" class="landing-section">',
        unsafe_allow_html=True,
    )
    st.subheader(title)
    st.markdown(
        f'<div class="landing-emphasis landing-emphasis--subtle"><p>{intro}</p></div>',
        unsafe_allow_html=True,
    )
    list_items = "".join(
        f"<li><strong>{point_title}:</strong> {body}</li>"
        for point_title, body in points
    )
    st.markdown(
        f'<div class="landing-problem-panel"><ul class="landing-problem-list">{list_items}</ul></div>',
        unsafe_allow_html=True,
    )
    st.caption(closer)
    st.markdown("</section>", unsafe_allow_html=True)


def render_flow_steps(
    *, section_id: str, title: str, steps: Sequence[tuple[str, str]]
) -> None:
    st.markdown(
        f'<section id="{section_id}" class="landing-section">',
        unsafe_allow_html=True,
    )
    st.subheader(title)
    for row_start in range(0, len(steps), 2):
        flow_cols = st.columns(2, gap="small")
        for col, (step_title, body) in zip(flow_cols, steps[row_start : row_start + 2]):
            with col:
                st.markdown(
                    f'<div class="landing-flow-step"><h4>{step_title}</h4><p>{body}</p></div>',
                    unsafe_allow_html=True,
                )
    st.markdown("</section>", unsafe_allow_html=True)


def render_output_section(
    *, section_id: str, title: str, bullets: Sequence[str]
) -> None:
    st.markdown(
        f'<section id="{section_id}" class="landing-section">',
        unsafe_allow_html=True,
    )
    st.subheader(title)
    st.markdown('<div class="landing-card">', unsafe_allow_html=True)
    st.markdown(
        '<ul class="landing-list">'
        + "".join(f"<li>{bullet}</li>" for bullet in bullets)
        + "</ul>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</section>", unsafe_allow_html=True)


def render_security_note(*, section_id: str, title: str, body: str) -> None:
    st.markdown(
        f'<section id="{section_id}" class="landing-section">',
        unsafe_allow_html=True,
    )
    st.subheader(title)
    st.markdown(
        f'<div class="landing-security-note">{body}</div>', unsafe_allow_html=True
    )
    st.markdown("</section>", unsafe_allow_html=True)
