# wizard_pages/08_summary.py
from __future__ import annotations

import io
import json
import textwrap
from collections import defaultdict
from typing import Callable
from typing import Any, TypedDict

import streamlit as st
import docx

from constants import SSKey
from llm_client import (
    JobAdGenerationResult,
    OpenAICallError,
    TASK_GENERATE_JOB_AD,
    TASK_GENERATE_VACANCY_BRIEF,
    generate_custom_job_ad,
    generate_vacancy_brief,
    upgrade_vacancy_brief_critical_sections,
    resolve_model_for_task,
)
from schemas import JobAdExtract, LanguageRequirement, VacancyBrief
from settings_openai import load_openai_settings
from state import (
    clear_error,
    get_answers,
    get_model_override,
    handle_unexpected_exception,
)
from ui_components import render_brief, render_error_banner, render_openai_error
from usage_utils import usage_has_cache_hit
from wizard_pages.base import WizardContext, WizardPage, nav_buttons

SUPPORTED_LOGO_MIME_TYPES: dict[str, str] = {
    "image/png": "PNG",
    "image/jpeg": "JPEG",
}

STYLEGUIDE_TEMPLATE_BLOCKS: dict[str, str] = {
    "Tonalität: professionell & nahbar": (
        "Tonalität: Professionell, klar und nahbar. Aktiv formulieren, keine Buzzword-"
        "Überladung."
    ),
    "Ansprache: Du-Form": "Ansprache: Durchgängig in Du-Form formulieren.",
    "Ansprache: Sie-Form": "Ansprache: Durchgängig in Sie-Form formulieren.",
    "Länge: kompakt": (
        "Länge: Kompakt halten (ca. 350–500 Wörter), Fokus auf Aufgaben, Must-haves und"
        " konkrete Benefits."
    ),
    "CTA-Stärke: deutlich": (
        "CTA: Klare Handlungsaufforderung mit einfacher Bewerbung (z. B. in 2 Minuten, "
        "ohne Anschreiben)."
    ),
    "Diversity-Hinweis inklusiv": (
        "Diversity: Inklusive und diskriminierungsfreie Sprache nutzen; Bewerbungen "
        "unabhängig von Geschlecht, Herkunft, Alter, Behinderung, Religion oder sexueller "
        "Identität willkommen heißen."
    ),
}

CHANGE_REQUEST_TEMPLATE_BLOCKS: dict[str, str] = {
    "Tonalität schärfen": (
        "Bitte die Tonalität etwas zugespitzter und gleichzeitig authentisch gestalten "
        "(weniger generisch, mehr konkreter Mehrwert)."
    ),
    "Du/Sie umstellen": (
        "Bitte die Ansprache konsistent auf die gewünschte Form umstellen "
        "(Du/Sie vollständig vereinheitlichen)."
    ),
    "Länge kürzen": (
        "Bitte die Anzeige um ca. 20–30 % kürzen und Wiederholungen entfernen, ohne "
        "Informationsverlust bei Aufgaben und Anforderungen."
    ),
    "CTA verstärken": (
        "Bitte den CTA sichtbarer und motivierender formulieren; Bewerbungsweg und "
        "nächsten Schritt klar benennen."
    ),
    "Diversity-Formulierung ergänzen": (
        "Bitte Diversity- und Inklusionshinweis sichtbarer platzieren und gendergerechte, "
        "inklusive Sprache konsequent verwenden."
    ),
}


class SummaryAction(TypedDict):
    id: str
    title: str
    description: str
    cta_label: str
    requires: tuple[SSKey, ...]
    generator_fn: Callable[[], None] | None
    result_key: SSKey
    input_hints: tuple[str, ...]


def _widget_key(base_key: SSKey, suffix: str | None = None) -> str:
    if not suffix:
        return base_key.value
    return f"{base_key.value}.{suffix}"


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


def _append_template_blocks(
    *,
    text_key: SSKey,
    selection_key: SSKey,
    selected_blocks: list[str],
    available_blocks: dict[str, str],
) -> None:
    previous_blocks_raw = st.session_state.get(selection_key.value, [])
    previous_blocks = (
        previous_blocks_raw if isinstance(previous_blocks_raw, list) else []
    )
    newly_selected_blocks = [
        block for block in selected_blocks if block not in previous_blocks
    ]

    if newly_selected_blocks:
        current_text = str(st.session_state.get(text_key.value, "") or "").strip()
        template_fragments: list[str] = []
        for block in newly_selected_blocks:
            template = available_blocks.get(block, "").strip()
            if template and template not in current_text:
                template_fragments.append(template)
        if template_fragments:
            merged_templates = "\n\n".join(template_fragments)
            st.session_state[text_key.value] = (
                f"{current_text}\n\n{merged_templates}"
                if current_text
                else merged_templates
            )

    st.session_state[selection_key.value] = selected_blocks


def _render_template_toggles(
    *,
    title: str,
    text_key: SSKey,
    selection_key: SSKey,
    template_blocks: dict[str, str],
    widget_prefix: str,
) -> None:
    st.caption(title)
    columns = st.columns(2)
    selected_blocks: list[str] = []
    prior_selected = st.session_state.get(selection_key.value, [])
    preselected = prior_selected if isinstance(prior_selected, list) else []

    for index, label in enumerate(template_blocks):
        col = columns[index % len(columns)]
        widget_key = f"{widget_prefix}.{index}"
        with col:
            checked = st.checkbox(
                label,
                value=label in preselected,
                key=widget_key,
            )
        if checked:
            selected_blocks.append(label)

    _append_template_blocks(
        text_key=text_key,
        selection_key=selection_key,
        selected_blocks=selected_blocks,
        available_blocks=template_blocks,
    )


def _build_salary_forecast_snapshot(
    job: JobAdExtract, answers: dict[str, Any]
) -> dict[str, float | int | str]:
    base_salary = _estimate_salary_baseline(job)
    must_have_count = len(job.must_have_skills)
    interview_steps = len(job.recruitment_steps)
    answers_count = len(answers)

    salary_multiplier = 1.0
    if must_have_count > 6:
        salary_multiplier += 0.07
    elif must_have_count > 3:
        salary_multiplier += 0.04

    seniority = (job.seniority_level or "").lower()
    if "lead" in seniority or "principal" in seniority:
        salary_multiplier += 0.12
    elif "senior" in seniority:
        salary_multiplier += 0.06
    elif "junior" in seniority:
        salary_multiplier -= 0.08

    remote_policy = (job.remote_policy or "").lower()
    if "remote" in remote_policy:
        salary_multiplier += 0.03
    if interview_steps >= 5:
        salary_multiplier += 0.02

    forecast_central = max(35_000.0, base_salary * salary_multiplier)
    spread_factor = 0.08 + min(0.14, max(0.0, (8 - min(answers_count, 8)) * 0.015))
    forecast_min = max(35_000.0, forecast_central * (1 - spread_factor))
    forecast_max = forecast_central * (1 + spread_factor)

    confidence = min(
        100,
        max(
            35,
            35
            + min(40, answers_count * 4)
            + (10 if bool(job.salary_range) else 0)
            + min(10, must_have_count),
        ),
    )

    return {
        "forecast_min": round(forecast_min, 0),
        "forecast_central": round(forecast_central, 0),
        "forecast_max": round(forecast_max, 0),
        "confidence": int(confidence),
        "answers_count": answers_count,
        "must_have_count": must_have_count,
        "interview_steps": interview_steps,
        "location": (job.location_country or "Nicht angegeben"),
        "currency": (job.salary_range.currency if job.salary_range else None) or "EUR",
    }


def _render_sidebar_salary_forecast(job: JobAdExtract, answers: dict[str, Any]) -> None:
    forecast = _build_salary_forecast_snapshot(job=job, answers=answers)

    st.sidebar.markdown("### 💶 Gehaltsvorcast")
    st.sidebar.caption("Kompakte Prognose auf Basis der bisher erfassten Stelleninfos.")
    st.sidebar.metric(
        "Prognose (Jahr, Mitte)",
        f"{int(forecast['forecast_central']):,} {forecast['currency']}".replace(
            ",", "."
        ),
    )
    st.sidebar.write(
        f"**Bandbreite:** {int(forecast['forecast_min']):,} – {int(forecast['forecast_max']):,} {forecast['currency']}".replace(
            ",", "."
        )
    )
    st.sidebar.progress(
        int(forecast["confidence"]),
        text=f"Prognose-Sicherheit: {forecast['confidence']}%",
    )
    st.sidebar.caption(
        "Treiber: "
        f"{forecast['must_have_count']} Must-haves · "
        f"{forecast['interview_steps']} Interview-Schritte · "
        f"{forecast['answers_count']} beantwortete Wizard-Felder · "
        f"Standort: {forecast['location']}"
    )
    with st.sidebar.expander("Annahmen", expanded=False):
        st.write(
            "- Prognose ist indikativ und ersetzt kein externes Markt-Benchmarking.\n"
            "- Höhere Anforderungsdichte und Seniorität erhöhen die Gehaltsmitte.\n"
            "- Mehr vollständige Angaben erhöhen die Prognose-Sicherheit."
        )


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
    left_col_1, left_col_2, left_col_3, criteria_col = st.columns(4)

    with criteria_col:
        st.markdown("**Szenario-Kriterien**")
        scope = st.selectbox(
            "Suchraum",
            options=list(scope_options.keys()),
            index=1,
            help="Erweitert den Talentpool, kann aber die Gehaltserwartung erhöhen.",
        )
        remote_share = st.slider("Remote-Anteil (%)", 0, 100, 60, 5)
        requirement_strictness = st.slider("Anforderungs-Strenge (%)", 0, 100, 55, 5)
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
        for requirement in selected_requirements:
            weights_raw[requirement] = st.slider(
                f"Gewicht: {requirement}",
                min_value=0,
                max_value=100,
                value=50,
                key=_widget_key(SSKey.SUMMARY_WEIGHT_WIDGET_PREFIX, requirement),
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

    basiswerte = {
        "gehalt_basis_jahr": round(base_salary, 0),
        "kandidaten_basis": round(base_candidates, 1),
        "must_have_skills": must_have_count,
        "interview_schritte": interview_steps,
        "antworten_im_wizard": len(answers),
    }

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

    with left_col_1:
        selection = st.plotly_chart(
            fig_salary,
            key=SSKey.SUMMARY_SALARY_FORECAST_WIDGET.value,
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
    with left_col_2:
        st.plotly_chart(fig_candidates, width="stretch")
    with left_col_3:
        st.dataframe(filtered_points, width="stretch", hide_index=True)
        with st.expander("Basiswerte & normalisierte Gewichte", expanded=False):
            st.write(
                {
                    "basiswerte": basiswerte,
                    "gewichtung_normalisiert": {
                        k: round(v, 3) for k, v in weights.items()
                    },
                }
            )


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


def _build_selection_rows(
    job: JobAdExtract, answers: dict[str, Any]
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    def _format_language_requirement(raw_value: Any) -> str:
        if not isinstance(raw_value, dict):
            return ""
        try:
            parsed = LanguageRequirement.model_validate(raw_value)
        except Exception:
            return ""
        return f"{parsed.language} ({parsed.level})"

    def add_row(
        category: str, field: str, value: str, source: str, critical: bool
    ) -> None:
        cleaned = (value or "").strip()
        if not cleaned:
            return
        rows.append(
            {
                "Kategorie": category,
                "Feld": field,
                "Wert": cleaned,
                "Quelle": source,
                "Kritisch": "Ja" if critical else "Nein",
            }
        )

    add_row("Basis", "Titel", job.job_title or "", "Jobspec", True)
    add_row("Basis", "Unternehmen", job.company_name or "", "Jobspec", True)
    add_row("Basis", "Brand", job.brand_name or "", "Jobspec", False)
    add_row("Basis", "Anstellungsart", job.employment_type or "", "Jobspec", True)
    add_row("Basis", "Vertragsart", job.contract_type or "", "Jobspec", True)
    add_row("Standort", "Ort", job.location_city or "", "Jobspec", True)
    add_row("Standort", "Land", job.location_country or "", "Jobspec", True)
    add_row("Standort", "Remote", job.remote_policy or "", "Jobspec", False)
    add_row("Rolle", "Kurzbeschreibung", job.role_overview or "", "Jobspec", True)
    for value in job.must_have_skills:
        add_row("Skills", "Must-have", value, "Jobspec", True)
    for value in job.nice_to_have_skills:
        add_row("Skills", "Nice-to-have", value, "Jobspec", False)
    for value in job.benefits:
        add_row("Benefits", "Benefit", value, "Jobspec", False)
    for contact in job.contacts:
        add_row("Kontakt", "Ansprechpartner", contact.name or "", "Jobspec", True)
        add_row("Kontakt", "Kontaktrolle", contact.role or "", "Jobspec", False)
        add_row("Kontakt", "Kontakt E-Mail", contact.email or "", "Jobspec", True)

    for answer_key, raw in answers.items():
        if raw is None:
            continue
        formatted_single_language = _format_language_requirement(raw)
        if formatted_single_language:
            add_row(
                "Manager-Input",
                answer_key,
                formatted_single_language,
                "Antwort",
                False,
            )
            continue
        if isinstance(raw, list):
            for value in raw:
                formatted_language = _format_language_requirement(value)
                if formatted_language:
                    add_row(
                        "Manager-Input",
                        answer_key,
                        formatted_language,
                        "Antwort",
                        False,
                    )
                    continue
                add_row("Manager-Input", answer_key, str(value), "Antwort", False)
            continue
        add_row("Manager-Input", answer_key, str(raw), "Antwort", False)

    return rows


def _collect_critical_gaps(job: JobAdExtract, rows: list[dict[str, str]]) -> list[str]:
    gaps = list(job.gaps)
    present_fields = {(row["Kategorie"], row["Feld"]) for row in rows}
    must_have_checks = [
        ("Basis", "Titel", "Fehlender Stellentitel"),
        ("Kontakt", "Kontakt E-Mail", "Fehlende Bewerbermail-Anschrift"),
        ("Kontakt", "Ansprechpartner", "Fehlende Ansprechpartner-Angabe"),
    ]
    for category, field_name, msg in must_have_checks:
        if (category, field_name) not in present_fields:
            gaps.append(msg)
    return sorted(set(gaps))


def _render_pills_multiselect(label: str, options: list[str], key: str) -> list[str]:
    if hasattr(st, "pills"):
        return st.pills(label, options=options, selection_mode="multi", key=key) or []
    return st.multiselect(label, options=options, default=options, key=key)


def _render_selection_matrix(
    *,
    job: JobAdExtract,
    answers: dict[str, Any],
) -> tuple[dict[str, list[str]], list[str]]:
    rows = _build_selection_rows(job, answers)
    st.subheader("Datenmatrix für Stellenanzeigen-Generierung")
    st.dataframe(rows, width="stretch", hide_index=True)

    grouped: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        grouped[f"{row['Kategorie']} · {row['Feld']}"].append(row["Wert"])

    st.markdown("**Auswahl (Multi-Select Pills pro Feld)**")
    selected: dict[str, list[str]] = {}
    for group_key in sorted(grouped.keys()):
        distinct_values = sorted(set(grouped[group_key]))
        picks = _render_pills_multiselect(
            f"{group_key}",
            options=distinct_values,
            key=_widget_key(SSKey.SUMMARY_SELECTION_PICK_WIDGET_PREFIX, group_key),
        )
        if picks:
            selected[group_key] = picks

    gaps = _collect_critical_gaps(job, rows)
    st.subheader("Kritische/fehlende Informationen")
    if gaps:
        for gap in gaps:
            st.warning(gap)
    else:
        st.success("Keine kritischen Lücken erkannt.")

    return selected, gaps


def _job_ad_to_docx_bytes(job_ad: JobAdGenerationResult, styleguide: str) -> bytes:
    d = docx.Document()
    logo_payload = st.session_state.get(SSKey.SUMMARY_LOGO.value)
    _add_logo_to_docx(document=d, logo_payload=logo_payload)
    d.add_heading(job_ad.headline or "Stellenanzeige", level=1)
    d.add_paragraph(job_ad.job_ad_text)
    d.add_heading("Zielgruppe", level=2)
    for item in job_ad.target_group:
        d.add_paragraph(item, style="List Bullet")
    d.add_heading("AGG-Checkliste", level=2)
    for item in job_ad.agg_checklist:
        d.add_paragraph(item, style="List Bullet")
    if styleguide.strip():
        d.add_heading("Styleguide", level=2)
        d.add_paragraph(styleguide)
    bio = io.BytesIO()
    d.save(bio)
    return bio.getvalue()


def _job_ad_to_pdf_bytes(
    job_ad: JobAdGenerationResult, styleguide: str
) -> bytes | None:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.pdfgen import canvas
    except Exception:
        return None

    bio = io.BytesIO()
    pdf = canvas.Canvas(bio, pagesize=A4)
    width, height = A4
    y = height - 2 * cm

    def write_line(line: str, *, is_title: bool = False) -> None:
        nonlocal y
        if y < 2 * cm:
            pdf.showPage()
            y = height - 2 * cm
        pdf.setFont(
            "Helvetica-Bold" if is_title else "Helvetica", 14 if is_title else 10
        )
        pdf.drawString(2 * cm, y, line[:110])
        y -= 0.65 * cm if is_title else 0.5 * cm

    write_line(job_ad.headline or "Stellenanzeige", is_title=True)
    for paragraph in job_ad.job_ad_text.split("\n"):
        for line in textwrap.wrap(paragraph, width=100) or [""]:
            write_line(line)
    write_line("Zielgruppe", is_title=True)
    for item in job_ad.target_group:
        write_line(f"- {item}")
    write_line("AGG-Checkliste", is_title=True)
    for item in job_ad.agg_checklist:
        write_line(f"- {item}")
    if styleguide.strip():
        write_line("Styleguide", is_title=True)
        for line in textwrap.wrap(styleguide, width=100):
            write_line(line)
    pdf.save()
    return bio.getvalue()


def _brief_to_docx_bytes(brief: VacancyBrief) -> bytes:
    d = docx.Document()
    logo_payload = st.session_state.get(SSKey.SUMMARY_LOGO.value)
    _add_logo_to_docx(document=d, logo_payload=logo_payload)
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


def _normalize_logo_payload(uploaded_logo: Any) -> dict[str, Any] | None:
    if uploaded_logo is None:
        return None
    mime_type = str(getattr(uploaded_logo, "type", "") or "").lower().strip()
    if mime_type not in SUPPORTED_LOGO_MIME_TYPES:
        return None
    raw_bytes = uploaded_logo.getvalue()
    if not raw_bytes:
        return None
    return {
        "name": str(getattr(uploaded_logo, "name", "") or "logo"),
        "mime_type": mime_type,
        "bytes": raw_bytes,
    }


def _add_logo_to_docx(document: Any, logo_payload: Any) -> bool:
    if not isinstance(logo_payload, dict):
        return False
    logo_bytes = logo_payload.get("bytes")
    if not isinstance(logo_bytes, (bytes, bytearray)):
        return False
    image_stream = io.BytesIO(bytes(logo_bytes))
    image_stream.seek(0)
    try:
        document.add_picture(image_stream, width=docx.shared.Cm(4.0))
    except Exception:
        return False
    return True


def _render_summary_hero(job: JobAdExtract, answers: dict[str, Any]) -> None:
    st.header("Zusammenfassung")
    st.subheader("Finaler Check & nächste Schritte")
    st.caption(
        "Verdichte alle Inputs in einen belastbaren Recruiting Brief und entscheide dann, "
        "welches Artefakt du als Nächstes erzeugen möchtest."
    )
    st.info(
        f"Value Proposition: {len(answers)} strukturierte Antworten + Jobspec = "
        "konsistente, exportierbare Hiring-Artefakte ohne Medienbruch."
    )
    st.write(
        f"**Rolle im Fokus:** {job.job_title or 'Nicht angegeben'} · "
        f"**Unternehmen:** {job.company_name or 'Nicht angegeben'}"
    )


def _render_summary_snapshot(
    job: JobAdExtract, answers: dict[str, Any], brief: VacancyBrief | None
) -> None:
    st.markdown("### Kompaktüberblick")
    salary_range = "Nicht angegeben"
    if job.salary_range and (job.salary_range.min or job.salary_range.max):
        minimum = _safe_int(job.salary_range.min)
        maximum = _safe_int(job.salary_range.max)
        currency = job.salary_range.currency or "EUR"
        if minimum and maximum:
            salary_range = f"{minimum:,} – {maximum:,} {currency}".replace(",", ".")
        else:
            value = maximum or minimum
            salary_range = f"ab {value:,} {currency}".replace(",", ".")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Must-have Skills", len(job.must_have_skills))
    with col2:
        st.metric("Interview-Schritte", len(job.recruitment_steps))
    with col3:
        st.metric("Wizard-Antworten", len(answers))
    with col4:
        st.metric("Kritische Gaps", len(job.gaps))

    fact_col1, fact_col2 = st.columns(2)
    with fact_col1:
        st.markdown("**Standort & Setup**")
        st.write(
            f"{job.location_city or 'Ort offen'}, {job.location_country or 'Land offen'}"
        )
        st.caption(f"Remote: {job.remote_policy or 'Nicht angegeben'}")
    with fact_col2:
        st.markdown("**Kompensation (falls vorhanden)**")
        st.write(salary_range)
        st.caption(f"Brief-Status: {'Vorhanden' if brief else 'Noch nicht generiert'}")


def _has_required_state(requirements: tuple[SSKey, ...]) -> bool:
    for required_key in requirements:
        if not st.session_state.get(required_key.value):
            return False
    return True


def _render_action_card(action: SummaryAction) -> bool:
    has_result = bool(st.session_state.get(action["result_key"].value))
    requirements_ok = _has_required_state(action["requires"])
    status_label = "✅ aktuell" if has_result else "🕒 noch nicht generiert"
    with st.container(border=True):
        st.markdown(f"**{action['title']}**")
        st.caption(action["description"])
        st.caption(f"Status: {status_label}")
        if action["input_hints"]:
            st.markdown("**Inputs**")
            for input_hint in action["input_hints"]:
                st.write(f"- {input_hint}")
        if not requirements_ok:
            st.warning("Voraussetzungen fehlen – Aktion aktuell nicht verfügbar.")
            return False
        if action["generator_fn"] is None:
            st.button(
                f"{action['cta_label']} (Platzhalter)",
                disabled=True,
                width="stretch",
                key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, action["id"]),
            )
            return False
        return st.button(
            action["cta_label"],
            width="stretch",
            type="primary",
            key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, action["id"]),
        )


def render(ctx: WizardContext) -> None:
    render_error_banner()

    job_dict = st.session_state.get(SSKey.JOB_EXTRACT.value)
    plan_dict = st.session_state.get(SSKey.QUESTION_PLAN.value)

    if not job_dict or not plan_dict:
        st.warning("Bitte zuerst im Start-Schritt eine Analyse durchführen.")
        st.button("Zur Startseite", on_click=lambda: ctx.goto("landing"))
        nav_buttons(ctx, disable_next=True)
        return

    job = JobAdExtract.model_validate(job_dict)
    answers = get_answers()
    _render_sidebar_salary_forecast(job=job, answers=answers)
    brief_dict = st.session_state.get(SSKey.BRIEF.value)
    brief_for_snapshot = (
        VacancyBrief.model_validate(brief_dict)
        if isinstance(brief_dict, dict)
        else None
    )

    _render_summary_hero(job=job, answers=answers)
    _render_summary_snapshot(job=job, answers=answers, brief=brief_for_snapshot)

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
    resolved_job_ad_model = resolve_model_for_task(
        task_kind=TASK_GENERATE_JOB_AD,
        session_override=session_override,
        settings=settings,
    )

    def _generate_recruiting_brief() -> None:
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
            brief_cached = usage_has_cache_hit(usage)
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

    def _generate_job_ad() -> None:
        clear_error()
        selected_values = st.session_state.get(SSKey.SUMMARY_SELECTIONS.value, {})
        styleguide = str(st.session_state.get(SSKey.SUMMARY_STYLEGUIDE_TEXT.value, ""))
        change_request = str(
            st.session_state.get(SSKey.SUMMARY_CHANGE_REQUEST_TEXT.value, "")
        )
        logo_payload = st.session_state.get(SSKey.SUMMARY_LOGO.value)
        try:
            with st.spinner("Generiere zielgruppen-optimierte Stellenanzeige …"):
                result, usage = generate_custom_job_ad(
                    job=job,
                    answers=answers,
                    selected_values=selected_values,
                    style_guide=styleguide,
                    change_request=change_request,
                    model=resolved_job_ad_model,
                    store=bool(
                        st.session_state.get(SSKey.STORE_API_OUTPUT.value, False)
                    ),
                )
            payload = result.model_dump(mode="json")
            payload["styleguide"] = styleguide
            payload["logo_filename"] = (
                logo_payload.get("name") if isinstance(logo_payload, dict) else None
            )
            st.session_state[SSKey.JOB_AD_DRAFT_CUSTOM.value] = payload
            st.session_state[SSKey.JOB_AD_LAST_USAGE.value] = usage or {}
        except OpenAICallError as e:
            render_openai_error(e)
        except Exception as exc:
            handle_unexpected_exception(
                step="summary.job_ad_generation",
                exc=exc,
                error_type=type(exc).__name__,
                error_code="SUMMARY_JOB_AD_GENERATION_UNEXPECTED",
            )

    st.markdown("### Action Hub")
    st.caption(
        "Einheitliche Aktionskarten für Erzeugung, Qualitätssicherung und Folgeartefakte."
    )
    action_registry: list[SummaryAction] = [
        {
            "id": "recruiting_brief",
            "title": "Recruiting Brief",
            "description": (
                "Verdichtet Jobspec + Wizard-Antworten in einen strukturierten Brief "
                "als Ausgangsbasis für Hiring und Kommunikation."
            ),
            "cta_label": "Recruiting Brief generieren",
            "requires": (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN),
            "generator_fn": _generate_recruiting_brief,
            "result_key": SSKey.BRIEF,
            "input_hints": (
                "Extrahierte Jobspec-Daten",
                "Strukturierte Wizard-Antworten",
                f"Draft-Modell: {resolved_brief_model}",
            ),
        },
        {
            "id": "job_ad_generator",
            "title": "Job-Ad-Generator",
            "description": (
                "Generiert oder verbessert eine zielgruppenorientierte Stellenanzeige "
                "inkl. AGG-Checkliste auf Basis selektierter Inputs."
            ),
            "cta_label": "Stellenanzeige generieren/verbessern",
            "requires": (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN),
            "generator_fn": _generate_job_ad,
            "result_key": SSKey.JOB_AD_DRAFT_CUSTOM,
            "input_hints": (
                "Selection Matrix (optional)",
                "Styleguide + Change Request",
                f"Job-Ad-Modell: {resolved_job_ad_model}",
            ),
        },
        {
            "id": "interview_hr_sheet",
            "title": "Interview-Vorbereitungssheet (HR)",
            "description": "Platzhalter für strukturiertes HR-Interviewbriefing.",
            "cta_label": "HR-Sheet erstellen",
            "requires": (SSKey.BRIEF,),
            "generator_fn": None,
            "result_key": SSKey.INTERVIEW_PREP_HR,
            "input_hints": ("Recruiting Brief", "Kritische Must-haves"),
        },
        {
            "id": "interview_fach_sheet",
            "title": "Interview-Vorbereitungssheet (Fachbereich)",
            "description": "Platzhalter für fachliche Interviewleitfäden und Bewertung.",
            "cta_label": "Fachbereich-Sheet erstellen",
            "requires": (SSKey.BRIEF,),
            "generator_fn": None,
            "result_key": SSKey.INTERVIEW_PREP_FACH,
            "input_hints": ("Recruiting Brief", "Top Responsibilities"),
        },
        {
            "id": "boolean_search",
            "title": "Boolean Search String",
            "description": "Platzhalter für sourcing-fähige Suchstrings je Kanal.",
            "cta_label": "Boolean String erstellen",
            "requires": (SSKey.BRIEF,),
            "generator_fn": None,
            "result_key": SSKey.BOOLEAN_SEARCH_STRING,
            "input_hints": ("Must-have + Nice-to-have Skills", "Synonyme"),
        },
        {
            "id": "employment_contract",
            "title": "Arbeitsvertrag",
            "description": "Platzhalter für Vertragsentwurf aus den Kernparametern.",
            "cta_label": "Arbeitsvertrag erstellen",
            "requires": (SSKey.BRIEF,),
            "generator_fn": None,
            "result_key": SSKey.EMPLOYMENT_CONTRACT_DRAFT,
            "input_hints": ("Rolle, Seniorität, Standort", "Vertragsart + Konditionen"),
        },
    ]
    card_columns = st.columns(2)
    for index, action in enumerate(action_registry):
        with card_columns[index % 2]:
            triggered = _render_action_card(action)
            if triggered and action["generator_fn"]:
                action["generator_fn"]()
                st.rerun()

    st.markdown("### Qualitäts-Upgrade")
    st.caption(
        "Schärft nur kritische Abschnitte im bestehenden Brief (High-Reasoning-Modell)."
    )
    do_quality_upgrade = st.button("Qualitäts-Upgrade", width="stretch")
    st.caption(
        f"Aktive Modelle: Draft=`{resolved_brief_model}` · Upgrade=`{resolved_quality_model}`"
    )

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
            st.session_state[SSKey.SUMMARY_CACHE_HIT.value] = usage_has_cache_hit(usage)
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

    main_tab, advanced_tab = st.tabs(["Brief & Export", "Advanced Studio"])

    with main_tab:
        render_brief(brief)
        st.subheader("Export")
        md = _brief_to_markdown(brief)
        json_bytes = json.dumps(
            brief.structured_data, indent=2, ensure_ascii=False
        ).encode("utf-8")
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

    with advanced_tab:
        with st.expander("Salary Forecast", expanded=False):
            _render_salary_forecast(job, answers)

        with st.expander("Selection Matrix", expanded=False):
            selected_values, critical_gaps = _render_selection_matrix(
                job=job, answers=answers
            )
            st.session_state[SSKey.SUMMARY_SELECTIONS.value] = selected_values

        with st.expander("Job-Ad-Editor", expanded=False):
            st.subheader("Smarte Stellenanzeigen-Generierung")
            logo_file = st.file_uploader(
                "Logo-Upload (optional)",
                type=["png", "jpg", "jpeg", "svg"],
                help="Das Logo wird als Metadatum gespeichert und kann im Exportprozess weiterverwendet werden.",
                key=SSKey.SUMMARY_LOGO_UPLOAD_WIDGET.value,
            )
            normalized_logo = _normalize_logo_payload(logo_file)
            st.session_state[SSKey.SUMMARY_LOGO.value] = normalized_logo
            if logo_file is not None and normalized_logo is None:
                st.warning(
                    "Logo-Format wird für Exporte nicht unterstützt. Bitte PNG oder JPG/JPEG verwenden."
                )
            if normalized_logo:
                st.image(
                    normalized_logo["bytes"],
                    caption=f"Verwendetes Firmenlogo: {normalized_logo.get('name', 'logo')}",
                    width=180,
                )

            styleguide_slot = st.empty()
            _render_template_toggles(
                title="Bausteine (Styleguide-Beschleuniger)",
                text_key=SSKey.SUMMARY_STYLEGUIDE_TEXT,
                selection_key=SSKey.SUMMARY_STYLEGUIDE_BLOCKS,
                template_blocks=STYLEGUIDE_TEMPLATE_BLOCKS,
                widget_prefix=SSKey.SUMMARY_STYLEGUIDE_BLOCK_WIDGET_PREFIX.value,
            )
            styleguide = styleguide_slot.text_area(
                "Styleguide des Arbeitgebers",
                placeholder="z. B. Tonalität, Wording, No-Gos, Corporate Language, Du/Sie, Diversity-Hinweise …",
                key=SSKey.SUMMARY_STYLEGUIDE_TEXT.value,
            )
            styleguide = str(
                st.session_state.get(SSKey.SUMMARY_STYLEGUIDE_TEXT.value, styleguide)
            )

            change_request_slot = st.empty()
            _render_template_toggles(
                title="Bausteine (Change-Request-Beschleuniger)",
                text_key=SSKey.SUMMARY_CHANGE_REQUEST_TEXT,
                selection_key=SSKey.SUMMARY_CHANGE_REQUEST_BLOCKS,
                template_blocks=CHANGE_REQUEST_TEMPLATE_BLOCKS,
                widget_prefix=SSKey.SUMMARY_CHANGE_REQUEST_BLOCK_WIDGET_PREFIX.value,
            )
            change_request_slot.text_area(
                "Anpassungswünsche (für Iterationen)",
                placeholder="z. B. stärker auf Senior-Profile fokussieren, CTA kürzen, Benefits konkretisieren …",
                key=SSKey.SUMMARY_CHANGE_REQUEST_TEXT.value,
            )
            critical_gaps = _collect_critical_gaps(
                job,
                _build_selection_rows(job, answers),
            )
            if critical_gaps:
                st.info(
                    "Hinweis: Kritische Lücken werden in der AGG-Checkliste markiert und nicht halluziniert."
                )

            st.caption(
                "Die Generierung wird im Action Hub ausgelöst. Hier kannst du Inputs vorbereiten und Ergebnisse prüfen."
            )

            custom_job_ad_raw = st.session_state.get(SSKey.JOB_AD_DRAFT_CUSTOM.value)
            if isinstance(custom_job_ad_raw, dict):
                custom_job_ad = JobAdGenerationResult.model_validate(
                    {
                        "headline": custom_job_ad_raw.get("headline", ""),
                        "target_group": custom_job_ad_raw.get("target_group", []),
                        "agg_checklist": custom_job_ad_raw.get("agg_checklist", []),
                        "job_ad_text": custom_job_ad_raw.get("job_ad_text", ""),
                    }
                )
                st.markdown(f"### {custom_job_ad.headline}")
                st.write(custom_job_ad.job_ad_text)
                st.markdown("**Zielgruppe**")
                for group in custom_job_ad.target_group:
                    st.write(f"- {group}")
                st.markdown("**AGG-Checkliste**")
                for item in custom_job_ad.agg_checklist:
                    st.write(f"- {item}")

                custom_docx = _job_ad_to_docx_bytes(
                    custom_job_ad, str(custom_job_ad_raw.get("styleguide", ""))
                )
                custom_pdf = _job_ad_to_pdf_bytes(
                    custom_job_ad, str(custom_job_ad_raw.get("styleguide", ""))
                )
                x1, x2 = st.columns(2)
                with x1:
                    st.download_button(
                        "Download Stellenanzeige (DOCX)",
                        data=custom_docx,
                        file_name="stellenanzeige.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                with x2:
                    if custom_pdf is None:
                        st.caption("PDF-Export benötigt reportlab (nicht verfügbar).")
                    else:
                        st.download_button(
                            "Download Stellenanzeige (PDF)",
                            data=custom_pdf,
                            file_name="stellenanzeige.pdf",
                            mime="application/pdf",
                        )

    nav_buttons(ctx, disable_next=True)


PAGE = WizardPage(
    key="summary",
    title_de="Zusammenfassung",
    icon="✅",
    render=render,
    requires_jobspec=True,
)
