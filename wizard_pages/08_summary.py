# wizard_pages/08_summary.py
from __future__ import annotations

import io
import json

import streamlit as st
import docx

from constants import SSKey
from llm_client import (
    OpenAICallError,
    TASK_GENERATE_VACANCY_BRIEF,
    generate_vacancy_brief,
    resolve_model_for_task,
)
from schemas import JobAdExtract, VacancyBrief
from settings_openai import load_openai_settings
from state import clear_error, get_answers, get_model_override, set_error
from ui_components import render_brief, render_error_banner, render_openai_error
from wizard_pages.base import WizardContext, WizardPage, nav_buttons


def _brief_to_markdown(brief: VacancyBrief) -> str:
    lines = []
    lines.append(
        f"# Recruiting Brief – {brief.structured_data.get('job_extract', {}).get('job_title', '')}".strip()
    )
    lines.append("")
    lines.append(f"**One-liner:** {brief.one_liner}")
    lines.append("")
    lines.append("## Hiring Context")
    lines.append(brief.hiring_context)
    lines.append("")
    lines.append("## Role Summary")
    lines.append(brief.role_summary)
    lines.append("")
    lines.append("## Top Responsibilities")
    lines.extend([f"- {x}" for x in brief.top_responsibilities])
    lines.append("")
    lines.append("## Must-have")
    lines.extend([f"- {x}" for x in brief.must_have])
    lines.append("")
    lines.append("## Nice-to-have")
    lines.extend([f"- {x}" for x in brief.nice_to_have])
    lines.append("")
    lines.append("## Dealbreakers")
    lines.extend([f"- {x}" for x in brief.dealbreakers])
    lines.append("")
    lines.append("## Interview Plan")
    lines.extend([f"- {x}" for x in brief.interview_plan])
    lines.append("")
    lines.append("## Evaluation Rubric")
    lines.extend([f"- {x}" for x in brief.evaluation_rubric])
    lines.append("")
    lines.append("## Risks / Open Questions")
    lines.extend([f"- {x}" for x in brief.risks_open_questions])
    lines.append("")
    lines.append("## Job Ad Draft (DE)")
    lines.append(brief.job_ad_draft)
    lines.append("")
    return "\n".join(lines)


def _brief_to_docx_bytes(brief: VacancyBrief) -> bytes:
    d = docx.Document()
    d.add_heading("Recruiting Brief", level=1)
    d.add_paragraph(f"One-liner: {brief.one_liner}")

    d.add_heading("Hiring Context", level=2)
    d.add_paragraph(brief.hiring_context)

    d.add_heading("Role Summary", level=2)
    d.add_paragraph(brief.role_summary)

    d.add_heading("Top Responsibilities", level=2)
    for x in brief.top_responsibilities:
        d.add_paragraph(x, style="List Bullet")

    d.add_heading("Must-have", level=2)
    for x in brief.must_have:
        d.add_paragraph(x, style="List Bullet")

    d.add_heading("Nice-to-have", level=2)
    for x in brief.nice_to_have:
        d.add_paragraph(x, style="List Bullet")

    d.add_heading("Interview Plan", level=2)
    for x in brief.interview_plan:
        d.add_paragraph(x, style="List Bullet")

    d.add_heading("Risks / Open Questions", level=2)
    for x in brief.risks_open_questions:
        d.add_paragraph(x, style="List Bullet")

    d.add_heading("Job Ad Draft (DE)", level=2)
    d.add_paragraph(brief.job_ad_draft)

    bio = io.BytesIO()
    d.save(bio)
    return bio.getvalue()


def render(ctx: WizardContext) -> None:
    st.header("Zusammenfassung")
    render_error_banner()

    job_dict = st.session_state.get(SSKey.JOB_EXTRACT.value)
    plan_dict = st.session_state.get(SSKey.QUESTION_PLAN.value)

    if not job_dict or not plan_dict:
        st.warning(
            "Bitte zuerst im Schritt 'Jobspec / Jobad' eine Analyse durchführen."
        )
        st.button("Zur Jobspec-Seite", on_click=lambda: ctx.goto("jobad"))
        nav_buttons(ctx, disable_next=True)
        return

    job = JobAdExtract.model_validate(job_dict)
    answers = get_answers()

    st.write(
        "Hier erzeugst du den finalen Recruiting Brief und kannst ihn exportieren (JSON / Markdown / DOCX)."
    )

    col1, col2 = st.columns([1, 2])
    with col1:
        do_brief = st.button(
            "Recruiting Brief generieren", type="primary", use_container_width=True
        )
    with col2:
        st.caption(
            "Der Brief kombiniert Jobspec-Extraktion + deine Antworten. Offene Punkte werden transparent gemacht."
        )

    if do_brief:
        clear_error()
        session_override = get_model_override()
        store = bool(st.session_state.get(SSKey.STORE_API_OUTPUT.value, False))
        settings = load_openai_settings()
        resolved_brief_model = resolve_model_for_task(
            task_kind=TASK_GENERATE_VACANCY_BRIEF,
            session_override=session_override,
            settings=settings,
        )
        try:
            with st.spinner("Generiere Recruiting Brief…"):
                brief, usage = generate_vacancy_brief(
                    job,
                    answers,
                    model=resolved_brief_model,
                    store=store,
                )
            st.session_state[SSKey.BRIEF.value] = brief.model_dump()
            with st.expander("API Usage (Debug)", expanded=False):
                st.write(
                    {
                        "resolved_models": {
                            "generate_vacancy_brief": resolved_brief_model
                        },
                        "usage": usage,
                    }
                )
        except OpenAICallError as e:
            render_openai_error(e)
        except Exception:
            set_error("Unerwarteter Fehler (DE) / Unexpected error (EN).")
        st.rerun()

    brief_dict = st.session_state.get(SSKey.BRIEF.value)
    if not brief_dict:
        st.info(
            "Noch kein Brief generiert. Beantworte die Fragen und klicke dann auf 'Recruiting Brief generieren'."
        )
        nav_buttons(ctx, disable_next=True)
        return

    brief = VacancyBrief.model_validate(brief_dict)
    render_brief(brief)

    st.subheader("Export")
    md = _brief_to_markdown(brief)
    json_bytes = json.dumps(brief.structured_data, indent=2, ensure_ascii=False).encode(
        "utf-8"
    )
    docx_bytes = _brief_to_docx_bytes(brief)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button(
            "Download JSON",
            data=json_bytes,
            file_name="vacancy_brief.json",
            mime="application/json",
        )
    with c2:
        st.download_button(
            "Download Markdown",
            data=md.encode("utf-8"),
            file_name="vacancy_brief.md",
            mime="text/markdown",
        )
    with c3:
        st.download_button(
            "Download DOCX",
            data=docx_bytes,
            file_name="vacancy_brief.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    nav_buttons(ctx, disable_next=True)


PAGE = WizardPage(
    key="summary",
    title_de="Zusammenfassung",
    icon="✅",
    render=render,
    requires_jobspec=True,
)
