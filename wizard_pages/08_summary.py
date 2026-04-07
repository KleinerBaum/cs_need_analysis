# wizard_pages/08_summary.py
from __future__ import annotations

import io
import json
from typing import Any

import streamlit as st
import docx

from constants import SSKey
from llm_client import (
    OpenAICallError,
    TASK_GENERATE_VACANCY_BRIEF,
    generate_vacancy_brief,
    upgrade_vacancy_brief_critical_sections,
    resolve_model_for_task,
)
from schemas import JobAdExtract, VacancyBrief
from settings_openai import load_openai_settings
from state import (
    clear_error,
    get_answers,
    get_model_override,
    handle_unexpected_exception,
)
from ui_components import render_brief, render_error_banner, render_openai_error
from wizard_pages.base import WizardContext, WizardPage, nav_buttons


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _estimate_salary_baseline(job: JobAdExtract) -> float:
    if job.salary_range and job.salary_range.min and job.salary_range.max:
        return (job.salary_range.min + job.salary_range.max) / 2
    if job.salary_range and job.salary_range.max:
        return job.salary_range.max
    if job.salary_range and job.salary_range.min:
        return job.salary_range.min

    seniority = (job.seniority_level or "").lower()
    if "lead" in seniority or "principal" in seniority:
        return 105_000
    if "senior" in seniority:
        return 90_000
    if "junior" in seniority:
        return 60_000
    return 75_000


def _estimate_candidate_baseline(job: JobAdExtract) -> float:
    strictness_penalty = (
        len(job.must_have_skills) * 3
        + len(job.certifications) * 2
        + len(job.languages) * 2
    )
    baseline = 85 - strictness_penalty
    if job.remote_policy and "remote" in job.remote_policy.lower():
        baseline += 20
    if job.location_country:
        baseline += 5
    return max(8.0, float(baseline))


def _render_salary_forecast(job: JobAdExtract, answers: dict[str, Any]) -> None:
    import plotly.graph_objects as go

    st.subheader("Gehaltsprognose")
    st.caption(
        "Interaktive Szenario-Simulation: Wähle Anforderungen, gewichte deren Bedeutung und analysiere den Effekt auf Gehalt und Kandidatenpool."
    )

    scope_options = {
        "Lokal": {"salary": 1.00, "candidates": 1.0},
        "Deutschland": {"salary": 1.07, "candidates": 2.5},
        "Global": {"salary": 1.18, "candidates": 6.0},
    }
    scope = st.selectbox(
        "Suchraum",
        options=list(scope_options.keys()),
        index=1,
        help="Erweitert den Talentpool, kann aber die Gehaltserwartung erhöhen.",
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        remote_share = st.slider("Remote-Anteil (%)", 0, 100, 60, 5)
    with c2:
        requirement_strictness = st.slider("Anforderungs-Strenge (%)", 0, 100, 55, 5)
    with c3:
        employer_attractiveness = st.slider(
            "Arbeitgeber-Attraktivität (%)", 0, 100, 50, 5
        )

    influential_requirements = [
        "Suchraum",
        "Remote-Anteil",
        "Anforderungs-Strenge",
        "Arbeitgeber-Attraktivität",
        "Must-have Skills",
        "Interviewprozess",
    ]
    selected_requirements = st.multiselect(
        "Entscheidende Stellenanforderungen (Selektion)",
        options=influential_requirements,
        default=influential_requirements[:4],
        help="Nur selektierte Faktoren gehen in die Gewichtung der Prognose ein.",
    )
    if not selected_requirements:
        st.info("Bitte mindestens eine Stellenanforderung auswählen.")
        return

    st.markdown("**Gewichtung (Zuordnung & Priorisierung)**")
    weights_raw: dict[str, int] = {}
    cols = st.columns(min(3, len(selected_requirements)))
    for idx, requirement in enumerate(selected_requirements):
        with cols[idx % len(cols)]:
            weights_raw[requirement] = st.slider(
                f"Gewicht: {requirement}",
                min_value=0,
                max_value=100,
                value=50,
                key=f"cs.summary.weight.{requirement}",
            )

    total_weight = sum(weights_raw.values())
    if total_weight == 0:
        st.warning(
            "Die Summe der Gewichte ist 0. Bitte mindestens ein Gewicht > 0 setzen."
        )
        return
    weights = {key: value / total_weight for key, value in weights_raw.items()}

    base_salary = _estimate_salary_baseline(job)
    base_candidates = _estimate_candidate_baseline(job)
    must_have_count = max(1, len(job.must_have_skills))
    interview_steps = max(1, len(job.recruitment_steps))

    scenario_points: list[dict[str, float]] = []
    for level in range(0, 101, 10):
        requirement_factor = 1 + ((level - requirement_strictness) / 100.0) * 0.35
        remote_factor_candidates = 1 + (remote_share - 50) / 100.0 * 0.8
        remote_factor_salary = 1 + (remote_share - 50) / 100.0 * 0.12
        attraction_factor_candidates = 1 + (employer_attractiveness - 50) / 100.0 * 0.9
        attraction_factor_salary = 1 + (employer_attractiveness - 50) / 100.0 * 0.15

        factor_salary = (
            scope_options[scope]["salary"]
            * remote_factor_salary
            * requirement_factor
            * attraction_factor_salary
        )
        factor_candidates = (
            scope_options[scope]["candidates"]
            * remote_factor_candidates
            * (2 - requirement_factor)
            * attraction_factor_candidates
            * max(0.5, 1.25 - must_have_count * 0.06)
            * max(0.55, 1.15 - interview_steps * 0.08)
        )

        weighted_adjustment = 1.0
        for requirement, weight in weights.items():
            if requirement == "Suchraum":
                weighted_adjustment += (
                    weight * (scope_options[scope]["salary"] - 1) * 0.7
                )
            elif requirement == "Remote-Anteil":
                weighted_adjustment += weight * (remote_share - 50) / 100.0 * 0.3
            elif requirement == "Anforderungs-Strenge":
                weighted_adjustment += weight * (level - 50) / 100.0 * 0.4
            elif requirement == "Arbeitgeber-Attraktivität":
                weighted_adjustment += (
                    weight * (employer_attractiveness - 50) / 100.0 * 0.25
                )
            elif requirement == "Must-have Skills":
                weighted_adjustment += weight * (must_have_count - 4) * 0.03
            elif requirement == "Interviewprozess":
                weighted_adjustment -= weight * (interview_steps - 3) * 0.02

        predicted_salary = max(
            35_000.0, base_salary * factor_salary * weighted_adjustment
        )
        predicted_candidates = max(3.0, base_candidates * factor_candidates)

        scenario_points.append(
            {
                "strictness_level": float(level),
                "predicted_salary": round(predicted_salary, 0),
                "predicted_candidates": round(predicted_candidates, 1),
            }
        )

    st.write(
        {
            "basiswerte": {
                "gehalt_basis_jahr": round(base_salary, 0),
                "kandidaten_basis": round(base_candidates, 1),
                "must_have_skills": must_have_count,
                "interview_schritte": interview_steps,
                "antworten_im_wizard": len(answers),
            },
            "gewichtung_normalisiert": {k: round(v, 3) for k, v in weights.items()},
        }
    )

    strictness_levels = [p["strictness_level"] for p in scenario_points]
    salaries = [p["predicted_salary"] for p in scenario_points]

    fig_salary = go.Figure()
    fig_salary.add_trace(
        go.Scatter(
            x=strictness_levels,
            y=salaries,
            mode="lines+markers",
            name="Prognose Jahresgehalt",
        )
    )
    fig_salary.update_layout(
        title="Effekt der Anforderungs-Strenge auf Gehaltsprognose",
        xaxis_title="Anforderungs-Strenge (%)",
        yaxis_title="Jahresgehalt (geschätzt)",
        dragmode="select",
    )

    selection = st.plotly_chart(
        fig_salary,
        key="cs.summary.salary_forecast",
        width="stretch",
        on_select="rerun",
        selection_mode=("points", "box", "lasso"),
    )
    selected_indices = ((selection or {}).get("selection") or {}).get(
        "point_indices"
    ) or []
    selected_points = [
        point
        for index, point in enumerate(scenario_points)
        if index in selected_indices
    ]
    filtered_points = selected_points or scenario_points

    fig_candidates = go.Figure()
    fig_candidates.add_trace(
        go.Bar(
            x=[p["strictness_level"] for p in filtered_points],
            y=[p["predicted_candidates"] for p in filtered_points],
            name="Potenzielle Kandidat:innen",
        )
    )
    fig_candidates.update_layout(
        title="Crossfilter: Kandidatenpool für ausgewählte Gehalts-Szenarien",
        xaxis_title="Anforderungs-Strenge (%)",
        yaxis_title="Kandidaten (geschätzt)",
    )
    st.plotly_chart(fig_candidates, width="stretch")

    st.dataframe(filtered_points, width="stretch", hide_index=True)


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

    settings = load_openai_settings()
    session_override = get_model_override()
    resolved_brief_model = resolve_model_for_task(
        task_kind=TASK_GENERATE_VACANCY_BRIEF,
        session_override=session_override,
        settings=settings,
    )
    resolved_quality_model = (
        session_override.strip() if session_override else settings.high_reasoning_model
    )

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        do_brief = st.button(
            "Recruiting Brief generieren", type="primary", width="stretch"
        )
    with col2:
        do_quality_upgrade = st.button(
            "Qualitäts-Upgrade",
            width="stretch",
            help="Schärft nur kritische Abschnitte nach.",
        )
    with col3:
        st.caption(
            "Standard: vollständiger Draft mit MEDIUM_REASONING_MODEL. Optional: Qualitäts-Upgrade nur für kritische Abschnitte mit HIGH_REASONING_MODEL."
        )

    if do_brief:
        clear_error()
        store = bool(st.session_state.get(SSKey.STORE_API_OUTPUT.value, False))
        try:
            with st.spinner("Generiere Recruiting Brief…"):
                brief, usage = generate_vacancy_brief(
                    job,
                    answers,
                    model=resolved_brief_model,
                    store=store,
                )
            st.session_state[SSKey.BRIEF.value] = brief.model_dump()
            brief_cached = bool((usage or {}).get("cached"))
            st.session_state[SSKey.SUMMARY_CACHE_HIT.value] = brief_cached
            st.session_state[SSKey.SUMMARY_LAST_MODE.value] = "standard_draft"
            st.session_state[SSKey.SUMMARY_LAST_MODELS.value] = {
                "draft_model": resolved_brief_model
            }
            if brief_cached:
                st.info(
                    "Recruiting Brief aus Cache geladen (DE) / Recruiting brief loaded from cache (EN)."
                )
            with st.expander("API Usage (Debug)", expanded=False):
                st.write(
                    {
                        "resolved_models": {
                            "generate_vacancy_brief": resolved_brief_model
                        },
                        "mode": "standard_draft",
                        "usage": usage,
                    }
                )
        except OpenAICallError as e:
            render_openai_error(e)
        except Exception as exc:
            error_type = type(exc).__name__
            handle_unexpected_exception(
                step="summary.generate_brief",
                exc=exc,
                error_type=error_type,
                error_code="SUMMARY_BRIEF_GENERATION_UNEXPECTED",
            )
        st.rerun()

    brief_dict = st.session_state.get(SSKey.BRIEF.value)
    if do_quality_upgrade:
        if not brief_dict:
            st.warning("Bitte zuerst einen Recruiting Brief generieren.")
            nav_buttons(ctx, disable_next=True)
            return
        clear_error()
        store = bool(st.session_state.get(SSKey.STORE_API_OUTPUT.value, False))
        try:
            with st.spinner("Schärfe kritische Abschnitte nach…"):
                base_brief = VacancyBrief.model_validate(brief_dict)
                brief, usage = upgrade_vacancy_brief_critical_sections(
                    base_brief=base_brief,
                    job=job,
                    answers=answers,
                    model=resolved_quality_model,
                    store=store,
                )
            st.session_state[SSKey.BRIEF.value] = brief.model_dump()
            st.session_state[SSKey.SUMMARY_CACHE_HIT.value] = bool(
                (usage or {}).get("cached")
            )
            st.session_state[SSKey.SUMMARY_LAST_MODE.value] = "quality_upgrade_critical"
            st.session_state[SSKey.SUMMARY_LAST_MODELS.value] = {
                "draft_model": resolved_brief_model,
                "quality_model": resolved_quality_model,
            }
            with st.expander("API Usage (Debug)", expanded=False):
                st.write(
                    {
                        "resolved_models": {
                            "generate_vacancy_brief": resolved_brief_model,
                            "critical_upgrade": resolved_quality_model,
                        },
                        "mode": "quality_upgrade_critical",
                        "usage": usage,
                    }
                )
        except OpenAICallError as e:
            render_openai_error(e)
        except Exception as exc:
            error_type = type(exc).__name__
            handle_unexpected_exception(
                step="summary.quality_upgrade",
                exc=exc,
                error_type=error_type,
                error_code="SUMMARY_QUALITY_UPGRADE_UNEXPECTED",
            )
        st.rerun()

    if not brief_dict:
        st.info(
            "Noch kein Brief generiert. Beantworte die Fragen und klicke dann auf 'Recruiting Brief generieren'."
        )
        nav_buttons(ctx, disable_next=True)
        return

    brief = VacancyBrief.model_validate(brief_dict)
    if bool(st.session_state.get(SSKey.SUMMARY_CACHE_HIT.value, False)):
        st.caption("📦 Summary: aus Cache geladen (DE) / loaded from cache (EN).")
    last_mode = st.session_state.get(SSKey.SUMMARY_LAST_MODE.value) or "unknown"
    last_models = st.session_state.get(SSKey.SUMMARY_LAST_MODELS.value, {}) or {}
    st.caption(
        f"🧠 Modus: `{last_mode}` · Modelle: Draft=`{last_models.get('draft_model', resolved_brief_model)}`"
        + (
            f", Upgrade=`{last_models.get('quality_model')}`"
            if last_models.get("quality_model")
            else ""
        )
    )
    render_brief(brief)
    _render_salary_forecast(job, answers)

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
