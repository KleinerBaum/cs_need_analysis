# wizard_pages/08_summary.py
from __future__ import annotations

import io
import json
import re
import textwrap
import csv
from collections import defaultdict
from typing import Callable
from typing import Any, TypedDict

import streamlit as st
import docx

from constants import AnswerType, SSKey
from llm_client import (
    TASK_GENERATE_EMPLOYMENT_CONTRACT,
    JobAdGenerationResult,
    OpenAICallError,
    TASK_GENERATE_BOOLEAN_SEARCH,
    TASK_GENERATE_INTERVIEW_SHEET_HM,
    TASK_GENERATE_INTERVIEW_SHEET_HR,
    TASK_GENERATE_JOB_AD,
    TASK_GENERATE_VACANCY_BRIEF,
    generate_boolean_search_pack,
    generate_custom_job_ad,
    generate_employment_contract_draft,
    generate_interview_sheet_hm,
    generate_interview_sheet_hr,
    generate_vacancy_brief,
    resolve_model_for_task,
)
from salary.engine import compute_salary_forecast
from salary.scenarios import (
    SALARY_SCENARIO_BASE,
    SALARY_SCENARIO_COST_FOCUS,
    SALARY_SCENARIO_MARKET_UPSIDE,
    SALARY_SCENARIO_OPTIONS,
    map_salary_scenario_to_overrides,
)
from salary.types import SalaryScenarioOverrides
from schemas import (
    BooleanSearchPack,
    EscoConceptRef,
    EscoMappingReport,
    EmploymentContractDraft,
    InterviewPrepSheetHiringManager,
    InterviewPrepSheetHR,
    JobAdExtract,
    LanguageRequirement,
    Question,
    QuestionPlan,
    VacancyBrief,
)
from settings_openai import load_openai_settings
from state import (
    clear_error,
    get_esco_occupation_selected,
    get_answers,
    get_model_override,
    handle_unexpected_exception,
)
from ui_components import (
    render_boolean_search_pack,
    render_brief,
    render_employment_contract_draft,
    render_error_banner,
    render_interview_prep_fach,
    render_interview_prep_hr,
    render_openai_error,
)
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
    input_renderer: Callable[[], None] | None


def _normalize_list_item(value: str) -> str:
    cleaned = re.sub(r"^[\-•*\d\.)\s]+", "", value).strip()
    return cleaned


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in values:
        normalized = item.strip()
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


def _sanitize_generated_job_ad(
    job_ad: JobAdGenerationResult,
) -> tuple[JobAdGenerationResult, list[str]]:
    body_lines: list[str] = []
    extracted_target_group: list[str] = []
    extracted_checklist: list[str] = []
    extracted_notes: list[str] = []

    section = "body"
    for raw_line in job_ad.job_ad_text.splitlines():
        line = raw_line.strip()
        if not line:
            if section == "body":
                body_lines.append("")
            continue

        lowered = line.rstrip(":").strip().casefold()
        if lowered == "zielgruppe":
            section = "target_group"
            continue
        if lowered in {"agg-checkliste", "agg checkliste"}:
            section = "agg_checklist"
            continue

        if line.casefold().startswith("hinweis:"):
            extracted_notes.append(line.split(":", 1)[1].strip())
            continue

        normalized_item = _normalize_list_item(line)
        if section == "target_group":
            if normalized_item:
                extracted_target_group.append(normalized_item)
            continue
        if section == "agg_checklist":
            if normalized_item:
                extracted_checklist.append(normalized_item)
            continue

        body_lines.append(raw_line.rstrip())

    while body_lines and not body_lines[-1].strip():
        body_lines.pop()

    normalized_job_ad = JobAdGenerationResult(
        headline=job_ad.headline.strip(),
        target_group=_dedupe_preserve_order(
            [*job_ad.target_group, *extracted_target_group]
        ),
        agg_checklist=_dedupe_preserve_order(
            [*job_ad.agg_checklist, *extracted_checklist]
        ),
        job_ad_text="\n".join(body_lines).strip(),
    )
    return normalized_job_ad, _dedupe_preserve_order(extracted_notes)


def _estimate_text_area_height(text: str) -> int:
    lines = max(1, len(text.splitlines()))
    return min(520, max(160, 40 + lines * 22))


def _widget_key(base_key: SSKey, suffix: str | None = None) -> str:
    if not suffix:
        return base_key.value
    return f"{base_key.value}.{suffix}"


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


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
    job: JobAdExtract,
    answers: dict[str, Any],
    *,
    scenario_name: str = "base",
    scenario_overrides: SalaryScenarioOverrides | None = None,
) -> dict[str, Any]:
    overrides = scenario_overrides or SalaryScenarioOverrides()
    forecast = compute_salary_forecast(
        job_extract=job,
        answers=answers,
        scenario_overrides=overrides,
    )
    full_result = forecast.model_dump(mode="json")
    return {
        **full_result,
        "scenario": scenario_name,
        "inputs": {
            "skills_add": st.session_state.get(
                SSKey.SALARY_SCENARIO_SKILLS_ADD.value, []
            ),
            "skills_remove": st.session_state.get(
                SSKey.SALARY_SCENARIO_SKILLS_REMOVE.value, []
            ),
            "location_override": st.session_state.get(
                SSKey.SALARY_SCENARIO_LOCATION_OVERRIDE.value, ""
            ),
            "radius_km": _safe_int(
                st.session_state.get(SSKey.SALARY_SCENARIO_RADIUS_KM.value, 50)
            ),
        },
        "forecast": forecast.forecast.model_dump(mode="json"),
        "forecast_result": full_result,
    }


def _parse_skill_tokens(raw: str) -> list[str]:
    values = [token.strip() for token in raw.split(",")]
    return _dedupe_preserve_order([token for token in values if token])


def _apply_salary_scenario_inputs(job: JobAdExtract) -> JobAdExtract:
    skills_add_raw = st.text_input(
        "Skills hinzufügen (CSV)",
        key=_widget_key(SSKey.SALARY_SCENARIO_SKILLS_ADD, "input"),
        help="Kommagetrennte Skill-Liste, die temporär zur Szenario-Simulation addiert wird.",
    )
    skills_remove_raw = st.text_input(
        "Skills entfernen (CSV)",
        key=_widget_key(SSKey.SALARY_SCENARIO_SKILLS_REMOVE, "input"),
        help="Kommagetrennte Skill-Liste, die temporär aus den Must-haves entfernt wird.",
    )
    location_override = st.text_input(
        "Standort-Override",
        key=SSKey.SALARY_SCENARIO_LOCATION_OVERRIDE.value,
        help="Optionaler Standort für diese Szenario-Berechnung.",
    ).strip()
    st.number_input(
        "Suchradius (km)",
        min_value=0,
        max_value=500,
        step=5,
        key=SSKey.SALARY_SCENARIO_RADIUS_KM.value,
        help="Dokumentationswert für Szenario-Analysen. Die aktuelle Engine nutzt diesen Wert nicht als Rechenfaktor.",
    )

    skills_add = _parse_skill_tokens(skills_add_raw)
    skills_remove = _parse_skill_tokens(skills_remove_raw)
    st.session_state[SSKey.SALARY_SCENARIO_SKILLS_ADD.value] = skills_add
    st.session_state[SSKey.SALARY_SCENARIO_SKILLS_REMOVE.value] = skills_remove

    current_skills = _dedupe_preserve_order([*job.must_have_skills, *skills_add])
    remove_set = {item.casefold() for item in skills_remove}
    filtered_skills = [
        skill for skill in current_skills if skill.casefold() not in remove_set
    ]
    return job.model_copy(
        update={
            "must_have_skills": filtered_skills,
            "location_country": location_override or job.location_country,
        }
    )


def _render_salary_forecast(job: JobAdExtract, answers: dict[str, Any]) -> None:
    st.subheader("Gehaltsprognose")
    st.caption(
        "Szenario-Simulation auf Basis der Salary-Engine. Die UI sammelt nur fachliche Eingaben, die Berechnung erfolgt vollständig in der Domain-Engine."
    )

    controls_col, result_col = st.columns((1, 2))

    with controls_col:
        st.markdown("**Szenario**")
        selected_scenario = st.radio(
            "Szenario",
            options=SALARY_SCENARIO_OPTIONS,
            format_func=lambda value: {
                SALARY_SCENARIO_BASE: "Baseline",
                SALARY_SCENARIO_MARKET_UPSIDE: "Marktaufschwung",
                SALARY_SCENARIO_COST_FOCUS: "Kostenfokus",
            }[value],
            key=SSKey.SALARY_FORECAST_SELECTED_SCENARIO.value,
        )
        forecast_job = _apply_salary_scenario_inputs(job)
    scenario_overrides = map_salary_scenario_to_overrides(selected_scenario)
    forecast = compute_salary_forecast(
        job_extract=forecast_job,
        answers=answers,
        scenario_overrides=scenario_overrides,
    )
    st.session_state[SSKey.SALARY_FORECAST_LAST_RESULT.value] = (
        _build_salary_forecast_snapshot(
            forecast_job,
            answers,
            scenario_name=selected_scenario,
            scenario_overrides=scenario_overrides,
        )
    )

    with result_col:
        p10, p50, p90 = st.columns(3)
        p10.metric(
            f"p10 ({forecast.period})",
            f"{int(forecast.forecast.p10):,} {forecast.currency}".replace(",", "."),
        )
        p50.metric(
            f"p50 ({forecast.period})",
            f"{int(forecast.forecast.p50):,} {forecast.currency}".replace(",", "."),
        )
        p90.metric(
            f"p90 ({forecast.period})",
            f"{int(forecast.forecast.p90):,} {forecast.currency}".replace(",", "."),
        )

        quality_percent = int(round(forecast.quality.value * 100))
        st.progress(
            quality_percent,
            text=f"Quality ({forecast.quality.kind}): {quality_percent}%",
        )
        if forecast.quality.signals:
            st.caption("Quality-Signale: " + " · ".join(forecast.quality.signals))

        st.markdown("**Drivers**")
        st.dataframe(
            [
                {
                    "key": driver.key,
                    "label": driver.label,
                    "direction": driver.direction,
                    "impact": driver.impact,
                    "detail": driver.detail,
                }
                for driver in forecast.drivers
            ],
            hide_index=True,
            width="stretch",
        )

        with st.expander("Berechnungsdetails", expanded=False):
            st.write(
                {
                    "szenario": selected_scenario,
                    "eingaben": st.session_state[
                        SSKey.SALARY_FORECAST_LAST_RESULT.value
                    ]["inputs"],
                    "prognose": forecast.forecast.model_dump(),
                    "qualität": forecast.quality.model_dump(),
                }
            )


def _brief_to_markdown(brief: VacancyBrief) -> str:
    structured_data = brief.structured_data.model_dump(mode="json")
    lines = []
    lines.append(
        f"# Recruiting Brief – {structured_data.get('job_extract', {}).get('job_title', '')}".strip()
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


def _to_esco_export_concepts(raw_items: Any) -> list[dict[str, str]]:
    if not isinstance(raw_items, list):
        return []
    concepts: list[dict[str, str]] = []
    for item in raw_items:
        try:
            parsed = EscoConceptRef.model_validate(item)
        except Exception:
            continue
        concepts.append({"uri": parsed.uri, "label": parsed.title})
    return concepts


def _normalize_skill_term(value: str) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _extract_skills_step_raw_terms(job_extract_payload: Any) -> list[str]:
    if not isinstance(job_extract_payload, dict):
        return []

    raw_terms: list[str] = []
    for key in ("must_have_skills", "nice_to_have_skills"):
        values = job_extract_payload.get(key, [])
        if not isinstance(values, list):
            continue
        for value in values:
            term = str(value or "").strip()
            if term:
                raw_terms.append(term)

    deduped_terms: list[str] = []
    seen: set[str] = set()
    for term in raw_terms:
        normalized = _normalize_skill_term(term)
        if not normalized or normalized in seen:
            continue
        deduped_terms.append(term)
        seen.add(normalized)
    return deduped_terms


def _build_esco_mapping_report_rows() -> list[dict[str, str]]:
    report_payload = st.session_state.get(SSKey.ESCO_SKILLS_MAPPING_REPORT.value, {})
    try:
        report = EscoMappingReport.model_validate(report_payload)
    except Exception:
        report = EscoMappingReport(
            mapped_count=0, unmapped_terms=[], collisions=[], notes=[]
        )

    chosen_must = _to_esco_export_concepts(
        st.session_state.get(SSKey.ESCO_SKILLS_SELECTED_MUST.value, [])
    )
    chosen_nice = _to_esco_export_concepts(
        st.session_state.get(SSKey.ESCO_SKILLS_SELECTED_NICE.value, [])
    )
    chosen_concepts = chosen_must + chosen_nice

    by_label: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for concept in chosen_concepts:
        by_label[_normalize_skill_term(concept.get("label", ""))].append(concept)

    raw_terms = _extract_skills_step_raw_terms(
        st.session_state.get(SSKey.JOB_EXTRACT.value, {})
    )

    rows: list[dict[str, str]] = []
    linked_uris: set[str] = set()
    normalized_unmapped = {
        _normalize_skill_term(term): term for term in report.unmapped_terms
    }
    for raw_term in raw_terms:
        label_matches = by_label.get(_normalize_skill_term(raw_term), [])
        if label_matches:
            for concept in label_matches:
                chosen_uri = concept.get("uri", "").strip()
                if chosen_uri:
                    linked_uris.add(chosen_uri)
                rows.append(
                    {
                        "raw_term": raw_term,
                        "chosen_uri": chosen_uri,
                        "chosen_label": concept.get("label", "").strip(),
                        "match_method": "label_exact",
                        "notes": "",
                    }
                )
        elif _normalize_skill_term(raw_term) in normalized_unmapped:
            rows.append(
                {
                    "raw_term": raw_term,
                    "chosen_uri": "",
                    "chosen_label": "",
                    "match_method": "unmapped",
                    "notes": "",
                }
            )

    for concept in chosen_concepts:
        chosen_uri = concept.get("uri", "").strip()
        if not chosen_uri or chosen_uri in linked_uris:
            continue
        rows.append(
            {
                "raw_term": "",
                "chosen_uri": chosen_uri,
                "chosen_label": concept.get("label", "").strip(),
                "match_method": "manual_selection",
                "notes": "",
            }
        )

    for term in report.collisions:
        rows.append(
            {
                "raw_term": str(term or "").strip(),
                "chosen_uri": "",
                "chosen_label": "",
                "match_method": "collision",
                "notes": "",
            }
        )
    for note in report.notes:
        rows.append(
            {
                "raw_term": "",
                "chosen_uri": "",
                "chosen_label": "",
                "match_method": "report_note",
                "notes": str(note or "").strip(),
            }
        )

    return sorted(
        rows,
        key=lambda row: (
            row["raw_term"].casefold(),
            row["chosen_uri"].casefold(),
            row["chosen_label"].casefold(),
            row["match_method"].casefold(),
            row["notes"].casefold(),
        ),
    )


def _build_esco_mapping_report_csv(rows: list[dict[str, str]]) -> bytes:
    fieldnames = ["raw_term", "chosen_uri", "chosen_label", "match_method", "notes"]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({name: row.get(name, "") for name in fieldnames})
    return buffer.getvalue().encode("utf-8")


def _build_structured_export_payload(brief: VacancyBrief) -> dict[str, Any]:
    payload = dict(brief.structured_data.model_dump(mode="json", exclude_none=True))
    selected_occupation = get_esco_occupation_selected()
    if isinstance(selected_occupation, dict):
        try:
            parsed_occupation = EscoConceptRef.model_validate(selected_occupation)
        except Exception:
            pass
        else:
            payload["esco_occupations"] = [
                {"uri": parsed_occupation.uri, "label": parsed_occupation.title}
            ]

    must_skills = _to_esco_export_concepts(
        st.session_state.get(SSKey.ESCO_SKILLS_SELECTED_MUST.value, [])
    )
    if must_skills:
        payload["esco_skills_must"] = must_skills

    nice_skills = _to_esco_export_concepts(
        st.session_state.get(SSKey.ESCO_SKILLS_SELECTED_NICE.value, [])
    )
    if nice_skills:
        payload["esco_skills_nice"] = nice_skills

    esco_config = st.session_state.get(SSKey.ESCO_CONFIG.value, {})
    if isinstance(esco_config, dict):
        selected_version = str(esco_config.get("selected_version") or "").strip()
        if selected_version:
            payload["esco_version"] = selected_version

    title_variants_raw = st.session_state.get(
        SSKey.ESCO_OCCUPATION_TITLE_VARIANTS.value
    )
    if isinstance(title_variants_raw, dict):
        variants_uri = str(title_variants_raw.get("uri") or "").strip()
        recommended_titles_raw = title_variants_raw.get("recommended_titles", {})
        if (
            isinstance(selected_occupation, dict)
            and variants_uri == str(selected_occupation.get("uri") or "").strip()
            and isinstance(recommended_titles_raw, dict)
        ):
            recommended_titles: dict[str, list[str]] = {}
            for language, labels_raw in recommended_titles_raw.items():
                if not isinstance(language, str) or not isinstance(labels_raw, list):
                    continue
                labels = [
                    str(label).strip()
                    for label in labels_raw
                    if isinstance(label, str) and str(label).strip()
                ]
                if labels:
                    recommended_titles[language] = labels
            if recommended_titles:
                payload["recommended_titles"] = recommended_titles
    return payload


def _boolean_search_pack_to_markdown(pack: BooleanSearchPack) -> str:
    def _as_bullets(values: list[str], *, code: bool = False) -> list[str]:
        if not values:
            return ["- —"]
        if code:
            return [f"- `{value}`" for value in values]
        return [f"- {value}" for value in values]

    lines = [
        "# Boolean Search Pack",
        "",
        f"**Role Title:** {pack.role_title}",
        "",
        "## Must-have Terms",
        *_as_bullets(pack.must_have_terms),
        "",
        "## Seniority Terms",
        *_as_bullets(pack.seniority_terms),
        "",
        "## Exclusion Terms",
        *_as_bullets(pack.exclusion_terms),
        "",
        "## Target Locations",
        *_as_bullets(pack.target_locations),
        "",
    ]
    for channel_label, channel in (
        ("Google", pack.google),
        ("LinkedIn", pack.linkedin),
        ("XING", pack.xing),
    ):
        lines.extend(
            [
                f"## {channel_label}",
                "",
                "### Broad",
                *_as_bullets(channel.broad, code=True),
                "",
                "### Focused",
                *_as_bullets(channel.focused, code=True),
                "",
                "### Fallback",
                *_as_bullets(channel.fallback, code=True),
                "",
            ]
        )
    lines.extend(
        [
            "## Channel Limitations",
            *_as_bullets(pack.channel_limitations),
            "",
            "## Usage Notes",
            *_as_bullets(pack.usage_notes),
            "",
        ]
    )
    return "\n".join(lines)


def _build_selection_rows(
    job: JobAdExtract, answers: dict[str, Any]
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    selected_occupation = get_esco_occupation_selected()

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
    add_row(
        "Basis",
        "ESCO Occupation",
        (selected_occupation or {}).get("title", ""),
        "ESCO",
        False,
    )
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


def _interview_prep_hr_to_docx_bytes(sheet: InterviewPrepSheetHR) -> bytes:
    d = docx.Document()
    d.add_heading("Interview Sheet (HR)", level=1)
    d.add_paragraph(f"Rolle: {sheet.role_title}")
    d.add_paragraph(f"Interview-Stage: {sheet.interview_stage}")
    d.add_paragraph(f"Dauer: {sheet.duration_minutes} Minuten")

    d.add_heading("Opening Script", level=2)
    d.add_paragraph(sheet.opening_script)

    d.add_heading("Frageblöcke", level=2)
    for block in sheet.question_blocks:
        d.add_heading(block.title, level=3)
        d.add_paragraph(f"Ziel: {block.objective}")
        if block.questions:
            d.add_paragraph("Fragen:")
            for question in block.questions:
                d.add_paragraph(question, style="List Bullet")
        if block.follow_up_prompts:
            d.add_paragraph("Follow-ups:")
            for prompt in block.follow_up_prompts:
                d.add_paragraph(prompt, style="List Bullet")

    d.add_heading("Knockout-Kriterien", level=2)
    for knockout_criterion in sheet.knockout_criteria:
        d.add_paragraph(knockout_criterion, style="List Bullet")

    d.add_heading("Bewertungsrubrik", level=2)
    for rubric_criterion in sheet.evaluation_rubric:
        d.add_heading(rubric_criterion.title, level=3)
        d.add_paragraph(rubric_criterion.description)
        d.add_paragraph(f"Gewichtung: {rubric_criterion.weight_percent} %")
        if rubric_criterion.score_scale:
            d.add_paragraph(f"Skala: {' | '.join(rubric_criterion.score_scale)}")
        if rubric_criterion.evidence_examples:
            d.add_paragraph("Evidenz-Beispiele:")
            for evidence in rubric_criterion.evidence_examples:
                d.add_paragraph(evidence, style="List Bullet")

    d.add_heading("Finale Empfehlung", level=2)
    for option in sheet.final_recommendation_options:
        d.add_paragraph(option, style="List Bullet")

    bio = io.BytesIO()
    d.save(bio)
    return bio.getvalue()


def _interview_prep_fach_to_docx_bytes(
    sheet: InterviewPrepSheetHiringManager,
) -> bytes:
    d = docx.Document()
    d.add_heading("Interview Sheet (Fachbereich)", level=1)
    d.add_paragraph(f"Rolle: {sheet.role_title}")
    d.add_paragraph(f"Interview-Stage: {sheet.interview_stage}")
    d.add_paragraph(f"Dauer: {sheet.duration_minutes} Minuten")

    d.add_heading("Kompetenzen validieren", level=2)
    for competency in sheet.competencies_to_validate:
        d.add_paragraph(competency, style="List Bullet")

    d.add_heading("Frageblöcke", level=2)
    for block in sheet.question_blocks:
        d.add_heading(block.title, level=3)
        d.add_paragraph(f"Ziel: {block.objective}")
        if block.questions:
            d.add_paragraph("Fragen:")
            for question in block.questions:
                d.add_paragraph(question, style="List Bullet")
        if block.follow_up_prompts:
            d.add_paragraph("Follow-ups:")
            for follow_up in block.follow_up_prompts:
                d.add_paragraph(follow_up, style="List Bullet")

    d.add_heading("Technical Deep Dive", level=2)
    for topic in sheet.technical_deep_dive_topics:
        d.add_paragraph(topic, style="List Bullet")

    d.add_heading("Case/Task Prompt", level=2)
    d.add_paragraph(sheet.case_or_task_prompt or "Kein Case/Task hinterlegt.")

    d.add_heading("Bewertungsrubrik", level=2)
    for criterion in sheet.evaluation_rubric:
        d.add_heading(criterion.title, level=3)
        d.add_paragraph(criterion.description)
        d.add_paragraph(f"Gewichtung: {criterion.weight_percent} %")
        if criterion.score_scale:
            d.add_paragraph(f"Skala: {' | '.join(criterion.score_scale)}")
        if criterion.evidence_examples:
            d.add_paragraph("Evidenz-Beispiele:")
            for evidence in criterion.evidence_examples:
                d.add_paragraph(evidence, style="List Bullet")

    d.add_heading("Debrief-Fragen", level=2)
    for question in sheet.debrief_questions:
        d.add_paragraph(question, style="List Bullet")

    bio = io.BytesIO()
    d.save(bio)
    return bio.getvalue()


def _employment_contract_to_docx_bytes(draft: EmploymentContractDraft) -> bytes:
    d = docx.Document()
    d.add_heading("Arbeitsvertrag (Template Draft)", level=1)
    d.add_paragraph(
        "Hinweis: Diese Vorlage ist kein finaler Vertrag und keine Rechtsberatung."
    )
    d.add_paragraph(f"Jurisdiction: {draft.jurisdiction}")
    d.add_paragraph(f"Rolle: {draft.role_title}")
    d.add_paragraph(f"Employment Type: {draft.employment_type}")
    d.add_paragraph(f"Contract Type: {draft.contract_type}")
    d.add_paragraph(f"Start Date: {draft.start_date or '—'}")
    d.add_paragraph(
        "Probation (Monate): "
        + (str(draft.probation_period_months) if draft.probation_period_months else "—")
    )
    salary = draft.salary
    d.add_paragraph(
        "Salary: "
        f"{salary.min if salary.min is not None else '—'} - "
        f"{salary.max if salary.max is not None else '—'} "
        f"{salary.currency or ''} / {salary.period or ''}".strip()
    )
    if salary.notes:
        d.add_paragraph(f"Salary Notes: {salary.notes}")
    d.add_paragraph(
        "Working Hours / Week: "
        + (str(draft.working_hours_per_week) if draft.working_hours_per_week else "—")
    )
    d.add_paragraph(
        "Vacation Days / Year: "
        + (str(draft.vacation_days_per_year) if draft.vacation_days_per_year else "—")
    )
    d.add_paragraph(f"Place of Work: {draft.place_of_work or '—'}")
    d.add_paragraph(f"Notice Period: {draft.notice_period or '—'}")

    d.add_heading("Missing Inputs", level=2)
    if draft.missing_inputs:
        for missing_input in draft.missing_inputs:
            d.add_paragraph(missing_input, style="List Bullet")
    else:
        d.add_paragraph("Keine fehlenden Inputs markiert.")

    d.add_heading("Clauses", level=2)
    if draft.clauses:
        for clause in draft.clauses:
            d.add_heading(clause.title, level=3)
            d.add_paragraph(clause.clause_text)
            d.add_paragraph(f"Pflichtklausel: {'Ja' if clause.required else 'Nein'}")
            if clause.legal_note:
                d.add_paragraph(f"Legal Note: {clause.legal_note}")
    else:
        d.add_paragraph("Keine Klauseln hinterlegt.")

    d.add_heading("Signature Requirements", level=2)
    for requirement in draft.signature_requirements:
        d.add_paragraph(requirement, style="List Bullet")

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
    plan_raw = st.session_state.get(SSKey.QUESTION_PLAN.value)
    try:
        plan = (
            QuestionPlan.model_validate(plan_raw)
            if isinstance(plan_raw, dict)
            else None
        )
    except Exception:
        plan = None

    table = _build_summary_compact_table(
        job=job, answers=answers, plan=plan, brief=brief
    )
    st.dataframe(table, width="stretch", hide_index=True)


def _build_country_readiness_items(job: JobAdExtract) -> list[tuple[str, str, bool]]:
    nace_lookup_raw = st.session_state.get(SSKey.EURES_NACE_TO_ESCO.value, {})
    nace_lookup = nace_lookup_raw if isinstance(nace_lookup_raw, dict) else {}
    selected_nace_code = str(
        st.session_state.get(SSKey.COMPANY_NACE_CODE.value, "") or ""
    ).strip()
    mapped_esco_uri = (
        str(nace_lookup.get(selected_nace_code, "") or "") if selected_nace_code else ""
    )
    selected_occupation = get_esco_occupation_selected()
    return [
        (
            "Land vorhanden",
            job.location_country or "Nicht angegeben",
            bool(job.location_country),
        ),
        (
            "ESCO Occupation gesetzt",
            "Ja" if selected_occupation else "Nein",
            bool(selected_occupation),
        ),
        (
            "NACE-Code gesetzt",
            selected_nace_code or "Nicht gesetzt",
            bool(selected_nace_code),
        ),
        (
            "NACE → ESCO gemappt",
            mapped_esco_uri or "Nicht verfügbar",
            bool(mapped_esco_uri),
        ),
    ]


def _render_country_readiness_block(job: JobAdExtract) -> None:
    st.markdown("### Country Readiness (informativ)")
    st.caption(
        "Dieser Block ist rein informativ und blockiert den Wizard nicht. "
        "Er zeigt, ob zentrale Länderkontext-Daten für spätere EURES/ESCO-Prozesse vorliegen."
    )
    readiness_items = _build_country_readiness_items(job)
    for label, value, ready in readiness_items:
        icon = "✅" if ready else "ℹ️"
        st.write(f"{icon} **{label}:** {value}")


def _format_summary_answer_value(question: Question, value: Any) -> str:
    if question.answer_type == AnswerType.BOOLEAN:
        return "Ja" if bool(value) else "Nein"
    if question.answer_type == AnswerType.MULTI_SELECT:
        if isinstance(value, list):
            return ", ".join(str(item).strip() for item in value if str(item).strip())
        return ""
    if question.answer_type == AnswerType.SINGLE_SELECT:
        return str(value or "").strip()
    if question.answer_type in {
        AnswerType.LONG_TEXT,
        AnswerType.SHORT_TEXT,
        AnswerType.DATE,
    }:
        return str(value or "").strip()
    if question.answer_type == AnswerType.NUMBER:
        return str(value) if value is not None else ""

    if isinstance(value, list):
        return ", ".join(str(item).strip() for item in value if str(item).strip())
    return str(value or "").strip()


def _build_summary_compact_table(
    *,
    job: JobAdExtract,
    answers: dict[str, Any],
    plan: QuestionPlan | None,
    brief: VacancyBrief | None,
) -> list[dict[str, str]]:
    jobspec_items: list[str] = []
    if job.job_title:
        jobspec_items.append(f"Titel: {job.job_title}")
    if job.company_name:
        jobspec_items.append(f"Unternehmen: {job.company_name}")
    if job.location_city or job.location_country:
        jobspec_items.append(
            f"Standort: {job.location_city or 'Ort offen'}, {job.location_country or 'Land offen'}"
        )
    if job.remote_policy:
        jobspec_items.append(f"Remote: {job.remote_policy}")
    if job.contract_type:
        jobspec_items.append(f"Vertragsart: {job.contract_type}")
    if job.employment_type:
        jobspec_items.append(f"Anstellungsart: {job.employment_type}")
    if job.must_have_skills:
        jobspec_items.append("Must-have: " + ", ".join(job.must_have_skills[:4]))
    if job.recruitment_steps:
        jobspec_items.append(
            "Interview: "
            + ", ".join(step.name for step in job.recruitment_steps[:3] if step.name)
        )
    jobspec_items.append(
        f"Brief-Status: {'Vorhanden' if brief is not None else 'Noch nicht generiert'}"
    )

    step_payload: list[tuple[str, list[str]]] = [("Jobspec-Übersicht", jobspec_items)]
    if plan is not None:
        for step in plan.steps:
            if step.step_key in {"landing", "jobspec_review", "summary"}:
                continue
            answered_items: list[str] = []
            for question in step.questions:
                raw_value = answers.get(question.id)
                if raw_value in (None, "", []):
                    continue
                formatted = _format_summary_answer_value(question, raw_value)
                if not formatted:
                    continue
                answered_items.append(f"{question.label}: {formatted}")
            step_payload.append((step.title_de, answered_items or ["Keine Eingaben"]))

    max_rows = max((len(items) for _, items in step_payload), default=1)
    rows: list[dict[str, str]] = []
    for index in range(max_rows):
        row: dict[str, str] = {}
        for title, items in step_payload:
            row[title] = items[index] if index < len(items) else ""
        rows.append(row)
    return rows


def _has_required_state(requirements: tuple[SSKey, ...]) -> bool:
    for required_key in requirements:
        if not st.session_state.get(required_key.value):
            return False
    return True


def _is_summary_entry() -> bool:
    last_rendered_step = st.session_state.get(SSKey.LAST_RENDERED_STEP.value)
    return last_rendered_step != "summary"


def _render_action_card(action: SummaryAction) -> bool:
    has_result = bool(st.session_state.get(action["result_key"].value))
    requirements_ok = _has_required_state(action["requires"])
    status_label = "✅ aktuell" if has_result else "🕒 noch nicht generiert"
    with st.container(border=True):
        st.markdown(f"**{action['title']}**")
        st.caption(action["description"])
        st.caption(f"Status: {status_label}")
        input_renderer = action.get("input_renderer")
        if input_renderer is not None:
            input_renderer()
        elif action["input_hints"]:
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


def _build_action_registry(
    *,
    resolved_brief_model: str,
    resolved_job_ad_model: str,
    resolved_hr_sheet_model: str,
    resolved_fach_sheet_model: str,
    resolved_boolean_search_model: str,
    resolved_employment_contract_model: str,
    render_job_ad_inputs: Callable[[], None] | None = None,
    generate_recruiting_brief: Callable[[], None],
    generate_job_ad: Callable[[], None],
    generate_interview_prep_hr: Callable[[], None],
    generate_interview_prep_fach: Callable[[], None],
    generate_boolean_search: Callable[[], None],
    generate_employment_contract: Callable[[], None],
) -> list[SummaryAction]:
    return [
        {
            "id": "recruiting_brief",
            "title": "Recruiting Brief",
            "description": (
                "Verdichtet Jobspec + Wizard-Antworten in einen strukturierten Brief "
                "als Ausgangsbasis für Hiring und Kommunikation."
            ),
            "cta_label": "Recruiting Brief generieren",
            "requires": (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN),
            "generator_fn": generate_recruiting_brief,
            "result_key": SSKey.BRIEF,
            "input_hints": (
                "Extrahierte Jobspec-Daten",
                "Strukturierte Wizard-Antworten",
                f"Draft-Modell: {resolved_brief_model}",
            ),
            "input_renderer": None,
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
            "generator_fn": generate_job_ad,
            "result_key": SSKey.JOB_AD_DRAFT_CUSTOM,
            "input_hints": (),
            "input_renderer": render_job_ad_inputs,
        },
        {
            "id": "interview_hr_sheet",
            "title": "Interview-Vorbereitungssheet (HR)",
            "description": (
                "Strukturiertes HR-Interviewblatt mit Leitfaden, Knockout-Kriterien "
                "und objektiver Bewertungsrubrik."
            ),
            "cta_label": "HR-Sheet erstellen",
            "requires": (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN),
            "generator_fn": generate_interview_prep_hr,
            "result_key": SSKey.INTERVIEW_PREP_HR,
            "input_hints": (
                "Recruiting Brief (optional, wird bei Bedarf automatisch erzeugt)",
                "Kritische Must-haves",
                f"HR-Sheet-Modell: {resolved_hr_sheet_model}",
            ),
            "input_renderer": None,
        },
        {
            "id": "interview_fach_sheet",
            "title": "Interview-Vorbereitungssheet (Fachbereich)",
            "description": (
                "Fachliches Interviewblatt mit Kompetenzvalidierung, Technical Deep Dive "
                "und strukturierter Bewertung."
            ),
            "cta_label": "Fachbereich-Sheet erstellen",
            "requires": (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN),
            "generator_fn": generate_interview_prep_fach,
            "result_key": SSKey.INTERVIEW_PREP_FACH,
            "input_hints": (
                "Recruiting Brief (optional, wird bei Bedarf automatisch erzeugt)",
                "Must-have + Top Responsibilities",
                f"Fachbereich-Sheet-Modell: {resolved_fach_sheet_model}",
            ),
            "input_renderer": None,
        },
        {
            "id": "boolean_search",
            "title": "Boolean Search String",
            "description": (
                "Erstellt kanal-spezifische Boolean-Queries (Google, LinkedIn, XING) "
                "inkl. Broad/Focused/Fallback-Varianten."
            ),
            "cta_label": "Boolean String erstellen",
            "requires": (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN),
            "generator_fn": generate_boolean_search,
            "result_key": SSKey.BOOLEAN_SEARCH_STRING,
            "input_hints": (
                "Recruiting Brief (optional, wird bei Bedarf automatisch erzeugt)",
                "Must-have + Nice-to-have Skills",
                f"Boolean-Modell: {resolved_boolean_search_model}",
            ),
            "input_renderer": None,
        },
        {
            "id": "employment_contract",
            "title": "Arbeitsvertrag",
            "description": (
                "Generiert einen Arbeitsvertrags-Template-Draft mit Platzhaltern, "
                "fehlenden Inputs und klauselbasierter Review-Struktur."
            ),
            "cta_label": "Arbeitsvertrag erstellen",
            "requires": (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN),
            "generator_fn": generate_employment_contract,
            "result_key": SSKey.EMPLOYMENT_CONTRACT_DRAFT,
            "input_hints": (
                "Recruiting Brief (optional, wird bei Bedarf automatisch erzeugt)",
                "Vertragsart + Konditionen",
                f"Contract-Modell: {resolved_employment_contract_model}",
            ),
            "input_renderer": None,
        },
    ]


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
    brief_dict = st.session_state.get(SSKey.BRIEF.value)
    brief_for_snapshot = (
        VacancyBrief.model_validate(brief_dict)
        if isinstance(brief_dict, dict)
        else None
    )

    _render_summary_hero(job=job, answers=answers)
    selected_occupation = get_esco_occupation_selected()
    if selected_occupation:
        st.caption(
            f"ESCO Occupation aus Jobspec-Review: {selected_occupation.get('title', '—')}"
        )
    else:
        st.caption("ESCO Occupation: Keine passende Occupation ausgewählt.")
    _render_summary_snapshot(job=job, answers=answers, brief=brief_for_snapshot)
    _render_country_readiness_block(job)

    settings = load_openai_settings()
    session_override = get_model_override()
    resolved_brief_model = resolve_model_for_task(
        task_kind=TASK_GENERATE_VACANCY_BRIEF,
        session_override=session_override,
        settings=settings,
    )
    resolved_job_ad_model = resolve_model_for_task(
        task_kind=TASK_GENERATE_JOB_AD,
        session_override=session_override,
        settings=settings,
    )
    resolved_hr_sheet_model = resolve_model_for_task(
        task_kind=TASK_GENERATE_INTERVIEW_SHEET_HR,
        session_override=session_override,
        settings=settings,
    )
    resolved_fach_sheet_model = resolve_model_for_task(
        task_kind=TASK_GENERATE_INTERVIEW_SHEET_HM,
        session_override=session_override,
        settings=settings,
    )
    resolved_boolean_search_model = resolve_model_for_task(
        task_kind=TASK_GENERATE_BOOLEAN_SEARCH,
        session_override=session_override,
        settings=settings,
    )
    resolved_employment_contract_model = resolve_model_for_task(
        task_kind=TASK_GENERATE_EMPLOYMENT_CONTRACT,
        session_override=session_override,
        settings=settings,
    )

    def _run_generate_recruiting_brief(
        *,
        mode: str = "standard_draft",
        spinner_text: str = "Generiere Recruiting Brief…",
        error_step: str = "summary.generate_brief",
    ) -> bool:
        clear_error()
        store = bool(st.session_state.get(SSKey.STORE_API_OUTPUT.value, False))
        try:
            with st.spinner(spinner_text):
                brief, usage = generate_vacancy_brief(
                    job,
                    answers,
                    model=resolved_brief_model,
                    store=store,
                )
            st.session_state[SSKey.BRIEF.value] = brief.model_dump()
            brief_cached = usage_has_cache_hit(usage)
            st.session_state[SSKey.SUMMARY_CACHE_HIT.value] = brief_cached
            st.session_state[SSKey.SUMMARY_LAST_MODE.value] = mode
            st.session_state[SSKey.SUMMARY_LAST_MODELS.value] = {
                "draft_model": resolved_brief_model
            }
            if brief_cached:
                st.info(
                    "Recruiting Brief aus Cache geladen (DE) / Recruiting brief loaded from cache (EN)."
                )
            return True
        except OpenAICallError as e:
            render_openai_error(e)
            return False
        except Exception as exc:
            error_type = type(exc).__name__
            handle_unexpected_exception(
                step=error_step,
                exc=exc,
                error_type=error_type,
                error_code="SUMMARY_BRIEF_GENERATION_UNEXPECTED",
            )
            return False

    def _generate_recruiting_brief() -> None:
        _run_generate_recruiting_brief()

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
            normalized_result, extracted_notes = _sanitize_generated_job_ad(result)
            payload = normalized_result.model_dump(mode="json")
            payload["generation_notes"] = extracted_notes
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

    def _resolve_brief_for_follow_up_action() -> VacancyBrief | None:
        brief_payload = st.session_state.get(SSKey.BRIEF.value)
        if isinstance(brief_payload, dict):
            try:
                return VacancyBrief.model_validate(brief_payload)
            except Exception:
                st.warning(
                    "Recruiting Brief ist ungültig. Es wird automatisch ein neuer Brief erzeugt."
                )

        store = bool(st.session_state.get(SSKey.STORE_API_OUTPUT.value, False))
        try:
            with st.spinner("Erzeuge Recruiting Brief als Grundlage…"):
                generated_brief, usage = generate_vacancy_brief(
                    job,
                    answers,
                    model=resolved_brief_model,
                    store=store,
                )
            st.session_state[SSKey.BRIEF.value] = generated_brief.model_dump()
            st.session_state[SSKey.SUMMARY_CACHE_HIT.value] = usage_has_cache_hit(usage)
            st.session_state[SSKey.SUMMARY_LAST_MODE.value] = "auto_draft_for_follow_up"
            st.session_state[SSKey.SUMMARY_LAST_MODELS.value] = {
                "draft_model": resolved_brief_model
            }
            return generated_brief
        except OpenAICallError as e:
            render_openai_error(e)
            return None
        except Exception as exc:
            handle_unexpected_exception(
                step="summary.auto_generate_brief_for_follow_up",
                exc=exc,
                error_type=type(exc).__name__,
                error_code="SUMMARY_AUTO_BRIEF_GENERATION_UNEXPECTED",
            )
            return None

    def _generate_interview_prep_hr() -> None:
        clear_error()
        brief_model = _resolve_brief_for_follow_up_action()
        if brief_model is None:
            return
        try:
            store = bool(st.session_state.get(SSKey.STORE_API_OUTPUT.value, False))
            with st.spinner("Generiere Interview-Sheet (HR)…"):
                sheet, usage = generate_interview_sheet_hr(
                    brief=brief_model,
                    model=resolved_hr_sheet_model,
                    store=store,
                )
            st.session_state[SSKey.INTERVIEW_PREP_HR.value] = sheet.model_dump(
                mode="json"
            )
            st.session_state[SSKey.INTERVIEW_PREP_HR_LAST_USAGE.value] = usage or {}
            st.session_state[SSKey.INTERVIEW_PREP_HR_CACHE_HIT.value] = (
                usage_has_cache_hit(usage)
            )
            st.session_state[SSKey.INTERVIEW_PREP_HR_LAST_MODE.value] = "from_brief"
            st.session_state[SSKey.INTERVIEW_PREP_HR_LAST_MODELS.value] = {
                "draft_model": resolved_hr_sheet_model
            }
        except OpenAICallError as e:
            render_openai_error(e)
        except Exception as exc:
            handle_unexpected_exception(
                step="summary.interview_prep_hr_generation",
                exc=exc,
                error_type=type(exc).__name__,
                error_code="SUMMARY_INTERVIEW_PREP_HR_GENERATION_UNEXPECTED",
            )

    def _generate_interview_prep_fach() -> None:
        clear_error()
        brief_model = _resolve_brief_for_follow_up_action()
        if brief_model is None:
            return
        try:
            store = bool(st.session_state.get(SSKey.STORE_API_OUTPUT.value, False))
            with st.spinner("Generiere Interview-Sheet (Fachbereich)…"):
                sheet, usage = generate_interview_sheet_hm(
                    brief=brief_model,
                    model=resolved_fach_sheet_model,
                    store=store,
                )
            st.session_state[SSKey.INTERVIEW_PREP_FACH.value] = sheet.model_dump(
                mode="json"
            )
            st.session_state[SSKey.INTERVIEW_PREP_FACH_LAST_USAGE.value] = usage or {}
            st.session_state[SSKey.INTERVIEW_PREP_FACH_CACHE_HIT.value] = (
                usage_has_cache_hit(usage)
            )
            st.session_state[SSKey.INTERVIEW_PREP_FACH_LAST_MODE.value] = "from_brief"
            st.session_state[SSKey.INTERVIEW_PREP_FACH_LAST_MODELS.value] = {
                "draft_model": resolved_fach_sheet_model
            }
        except OpenAICallError as e:
            render_openai_error(e)
        except Exception as exc:
            handle_unexpected_exception(
                step="summary.interview_prep_fach_generation",
                exc=exc,
                error_type=type(exc).__name__,
                error_code="SUMMARY_INTERVIEW_PREP_FACH_GENERATION_UNEXPECTED",
            )

    def _generate_boolean_search_pack() -> None:
        clear_error()
        brief_model = _resolve_brief_for_follow_up_action()
        if brief_model is None:
            return
        try:
            store = bool(st.session_state.get(SSKey.STORE_API_OUTPUT.value, False))
            with st.spinner("Generiere Boolean Search Pack…"):
                pack, usage = generate_boolean_search_pack(
                    brief=brief_model,
                    model=resolved_boolean_search_model,
                    store=store,
                )
            st.session_state[SSKey.BOOLEAN_SEARCH_STRING.value] = pack.model_dump(
                mode="json"
            )
            st.session_state[SSKey.BOOLEAN_SEARCH_LAST_USAGE.value] = usage or {}
            st.session_state[SSKey.BOOLEAN_SEARCH_CACHE_HIT.value] = (
                usage_has_cache_hit(usage)
            )
            st.session_state[SSKey.BOOLEAN_SEARCH_LAST_MODE.value] = "from_brief"
            st.session_state[SSKey.BOOLEAN_SEARCH_LAST_MODELS.value] = {
                "draft_model": resolved_boolean_search_model
            }
        except OpenAICallError as e:
            render_openai_error(e)
        except Exception as exc:
            handle_unexpected_exception(
                step="summary.boolean_search_generation",
                exc=exc,
                error_type=type(exc).__name__,
                error_code="SUMMARY_BOOLEAN_SEARCH_GENERATION_UNEXPECTED",
            )

    def _generate_employment_contract() -> None:
        clear_error()
        brief_model = _resolve_brief_for_follow_up_action()
        if brief_model is None:
            return
        try:
            store = bool(st.session_state.get(SSKey.STORE_API_OUTPUT.value, False))
            with st.spinner("Generiere Arbeitsvertrags-Template…"):
                draft, usage = generate_employment_contract_draft(
                    brief=brief_model,
                    model=resolved_employment_contract_model,
                    store=store,
                )
            st.session_state[SSKey.EMPLOYMENT_CONTRACT_DRAFT.value] = draft.model_dump(
                mode="json"
            )
            st.session_state[SSKey.EMPLOYMENT_CONTRACT_LAST_USAGE.value] = usage or {}
            st.session_state[SSKey.EMPLOYMENT_CONTRACT_CACHE_HIT.value] = (
                usage_has_cache_hit(usage)
            )
            st.session_state[SSKey.EMPLOYMENT_CONTRACT_LAST_MODE.value] = "from_brief"
            st.session_state[SSKey.EMPLOYMENT_CONTRACT_LAST_MODELS.value] = {
                "draft_model": resolved_employment_contract_model
            }
        except OpenAICallError as e:
            render_openai_error(e)
        except Exception as exc:
            handle_unexpected_exception(
                step="summary.employment_contract_generation",
                exc=exc,
                error_type=type(exc).__name__,
                error_code="SUMMARY_EMPLOYMENT_CONTRACT_GENERATION_UNEXPECTED",
            )

    if _is_summary_entry():
        _run_generate_recruiting_brief(
            mode="auto_refresh_on_summary_entry",
            spinner_text="Aktualisiere Recruiting Brief für Summary-Entry…",
            error_step="summary.auto_refresh_on_entry",
        )

    def _render_job_ad_action_hub_inputs() -> None:
        st.markdown("**Selection Matrix (optional)**")
        selected_values, _ = _render_selection_matrix(job=job, answers=answers)
        st.session_state[SSKey.SUMMARY_SELECTIONS.value] = selected_values

        st.markdown("**Job-Ad-Editor**")
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

        styleguide_key = SSKey.SUMMARY_STYLEGUIDE_TEXT.value
        if styleguide_key not in st.session_state:
            st.session_state[styleguide_key] = ""

        styleguide_slot = st.empty()
        _render_template_toggles(
            title="Bausteine (Styleguide-Beschleuniger)",
            text_key=SSKey.SUMMARY_STYLEGUIDE_TEXT,
            selection_key=SSKey.SUMMARY_STYLEGUIDE_BLOCKS,
            template_blocks=STYLEGUIDE_TEMPLATE_BLOCKS,
            widget_prefix=SSKey.SUMMARY_STYLEGUIDE_BLOCK_WIDGET_PREFIX.value,
        )
        _ = styleguide_slot.text_area(
            "Styleguide des Arbeitgebers",
            placeholder="z. B. Tonalität, Wording, No-Gos, Corporate Language, Du/Sie, Diversity-Hinweise …",
            key=styleguide_key,
        )

        change_request_key = SSKey.SUMMARY_CHANGE_REQUEST_TEXT.value
        if change_request_key not in st.session_state:
            st.session_state[change_request_key] = ""

        change_request_slot = st.empty()
        _render_template_toggles(
            title="Bausteine (Change-Request-Beschleuniger)",
            text_key=SSKey.SUMMARY_CHANGE_REQUEST_TEXT,
            selection_key=SSKey.SUMMARY_CHANGE_REQUEST_BLOCKS,
            template_blocks=CHANGE_REQUEST_TEMPLATE_BLOCKS,
            widget_prefix=SSKey.SUMMARY_CHANGE_REQUEST_BLOCK_WIDGET_PREFIX.value,
        )
        _ = change_request_slot.text_area(
            "Anpassungswünsche (für Iterationen)",
            placeholder="z. B. stärker auf Senior-Profile fokussieren, CTA kürzen, Benefits konkretisieren …",
            key=change_request_key,
        )
        critical_gaps = _collect_critical_gaps(
            job,
            _build_selection_rows(job, answers),
        )
        if critical_gaps:
            st.info(
                "Hinweis: Kritische Lücken werden in der AGG-Checkliste markiert und nicht halluziniert."
            )
        st.caption(f"Job-Ad-Modell: `{resolved_job_ad_model}`")

    st.markdown("### Action Hub")
    st.caption(
        "Einheitliche Aktionskarten für Erzeugung, Qualitätssicherung und Folgeartefakte."
    )
    action_registry = _build_action_registry(
        resolved_brief_model=resolved_brief_model,
        resolved_job_ad_model=resolved_job_ad_model,
        resolved_hr_sheet_model=resolved_hr_sheet_model,
        resolved_fach_sheet_model=resolved_fach_sheet_model,
        resolved_boolean_search_model=resolved_boolean_search_model,
        resolved_employment_contract_model=resolved_employment_contract_model,
        render_job_ad_inputs=_render_job_ad_action_hub_inputs,
        generate_recruiting_brief=_generate_recruiting_brief,
        generate_job_ad=_generate_job_ad,
        generate_interview_prep_hr=_generate_interview_prep_hr,
        generate_interview_prep_fach=_generate_interview_prep_fach,
        generate_boolean_search=_generate_boolean_search_pack,
        generate_employment_contract=_generate_employment_contract,
    )
    card_columns = st.columns(2)
    for index, action in enumerate(action_registry):
        with card_columns[index % 2]:
            triggered = _render_action_card(action)
            if triggered and action["generator_fn"]:
                action["generator_fn"]()
                st.rerun()

    brief_dict = st.session_state.get(SSKey.BRIEF.value)
    if not brief_dict:
        st.info(
            "Noch kein Recruiting Brief verfügbar. Prüfe die Eingaben und versuche es erneut."
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
    )

    main_tab, advanced_tab = st.tabs(["Brief & Export", "Advanced Studio"])

    with main_tab:
        render_brief(brief)
        hr_sheet_payload = st.session_state.get(SSKey.INTERVIEW_PREP_HR.value)
        if isinstance(hr_sheet_payload, dict):
            hr_sheet = InterviewPrepSheetHR.model_validate(hr_sheet_payload)
            with st.expander("Interview Sheet (HR)", expanded=False):
                hr_cache_hit = bool(
                    st.session_state.get(SSKey.INTERVIEW_PREP_HR_CACHE_HIT.value, False)
                )
                hr_mode = (
                    st.session_state.get(SSKey.INTERVIEW_PREP_HR_LAST_MODE.value)
                    or "unknown"
                )
                hr_models = (
                    st.session_state.get(SSKey.INTERVIEW_PREP_HR_LAST_MODELS.value, {})
                    or {}
                )
                cache_label = "Cache-Hit" if hr_cache_hit else "Kein Cache-Hit"
                st.caption(
                    f"📦 {cache_label} · Modus: `{hr_mode}` · "
                    f"Modell: `{hr_models.get('draft_model', resolved_hr_sheet_model)}`"
                )
                render_interview_prep_hr(hr_sheet)

                hr_json_bytes = json.dumps(
                    hr_sheet.model_dump(mode="json"), indent=2, ensure_ascii=False
                ).encode("utf-8")
                hr_docx_bytes = _interview_prep_hr_to_docx_bytes(hr_sheet)
                x1, x2 = st.columns(2)
                with x1:
                    st.download_button(
                        "Download Interview Sheet JSON",
                        data=hr_json_bytes,
                        file_name="interview_sheet_hr.json",
                        mime="application/json",
                    )
                with x2:
                    st.download_button(
                        "Download Interview Sheet DOCX",
                        data=hr_docx_bytes,
                        file_name="interview_sheet_hr.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )

        fach_sheet_payload = st.session_state.get(SSKey.INTERVIEW_PREP_FACH.value)
        if isinstance(fach_sheet_payload, dict):
            fach_sheet = InterviewPrepSheetHiringManager.model_validate(
                fach_sheet_payload
            )
            with st.expander("Interview Sheet (Fachbereich)", expanded=False):
                fach_cache_hit = bool(
                    st.session_state.get(
                        SSKey.INTERVIEW_PREP_FACH_CACHE_HIT.value, False
                    )
                )
                fach_mode = (
                    st.session_state.get(SSKey.INTERVIEW_PREP_FACH_LAST_MODE.value)
                    or "unknown"
                )
                fach_models = (
                    st.session_state.get(
                        SSKey.INTERVIEW_PREP_FACH_LAST_MODELS.value, {}
                    )
                    or {}
                )
                fach_cache_label = "Cache-Hit" if fach_cache_hit else "Kein Cache-Hit"
                st.caption(
                    f"📦 {fach_cache_label} · Modus: `{fach_mode}` · "
                    f"Modell: `{fach_models.get('draft_model', resolved_fach_sheet_model)}`"
                )
                render_interview_prep_fach(fach_sheet)

                fach_json_bytes = json.dumps(
                    fach_sheet.model_dump(mode="json"), indent=2, ensure_ascii=False
                ).encode("utf-8")
                fach_docx_bytes = _interview_prep_fach_to_docx_bytes(fach_sheet)
                x1, x2 = st.columns(2)
                with x1:
                    st.download_button(
                        "Download Interview Sheet (Fachbereich) JSON",
                        data=fach_json_bytes,
                        file_name="interview_sheet_fachbereich.json",
                        mime="application/json",
                    )
                with x2:
                    st.download_button(
                        "Download Interview Sheet (Fachbereich) DOCX",
                        data=fach_docx_bytes,
                        file_name="interview_sheet_fachbereich.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )

        boolean_payload = st.session_state.get(SSKey.BOOLEAN_SEARCH_STRING.value)
        if isinstance(boolean_payload, dict):
            boolean_pack = BooleanSearchPack.model_validate(boolean_payload)
            with st.expander("Boolean Search Pack", expanded=False):
                boolean_cache_hit = bool(
                    st.session_state.get(SSKey.BOOLEAN_SEARCH_CACHE_HIT.value, False)
                )
                boolean_mode = (
                    st.session_state.get(SSKey.BOOLEAN_SEARCH_LAST_MODE.value)
                    or "unknown"
                )
                boolean_models = (
                    st.session_state.get(SSKey.BOOLEAN_SEARCH_LAST_MODELS.value, {})
                    or {}
                )
                boolean_cache_label = (
                    "Cache-Hit" if boolean_cache_hit else "Kein Cache-Hit"
                )
                st.caption(
                    f"📦 {boolean_cache_label} · Modus: `{boolean_mode}` · "
                    f"Modell: `{boolean_models.get('draft_model', resolved_boolean_search_model)}`"
                )
                render_boolean_search_pack(boolean_pack)

                boolean_json_bytes = json.dumps(
                    boolean_pack.model_dump(mode="json"), indent=2, ensure_ascii=False
                ).encode("utf-8")
                boolean_md = _boolean_search_pack_to_markdown(boolean_pack).encode(
                    "utf-8"
                )
                x1, x2 = st.columns(2)
                with x1:
                    st.download_button(
                        "Download Boolean Search JSON",
                        data=boolean_json_bytes,
                        file_name="boolean_search_pack.json",
                        mime="application/json",
                    )
                with x2:
                    st.download_button(
                        "Download Boolean Search Markdown",
                        data=boolean_md,
                        file_name="boolean_search_pack.md",
                        mime="text/markdown",
                    )

        employment_contract_payload = st.session_state.get(
            SSKey.EMPLOYMENT_CONTRACT_DRAFT.value
        )
        if isinstance(employment_contract_payload, dict):
            employment_contract_draft = EmploymentContractDraft.model_validate(
                employment_contract_payload
            )
            with st.expander("Arbeitsvertrag (Template Draft)", expanded=False):
                contract_cache_hit = bool(
                    st.session_state.get(
                        SSKey.EMPLOYMENT_CONTRACT_CACHE_HIT.value, False
                    )
                )
                contract_mode = (
                    st.session_state.get(SSKey.EMPLOYMENT_CONTRACT_LAST_MODE.value)
                    or "unknown"
                )
                contract_models = (
                    st.session_state.get(
                        SSKey.EMPLOYMENT_CONTRACT_LAST_MODELS.value, {}
                    )
                    or {}
                )
                contract_cache_label = (
                    "Cache-Hit" if contract_cache_hit else "Kein Cache-Hit"
                )
                st.caption(
                    f"📦 {contract_cache_label} · Modus: `{contract_mode}` · "
                    f"Modell: `{contract_models.get('draft_model', resolved_employment_contract_model)}`"
                )
                render_employment_contract_draft(employment_contract_draft)

                contract_json_bytes = json.dumps(
                    employment_contract_draft.model_dump(mode="json"),
                    indent=2,
                    ensure_ascii=False,
                ).encode("utf-8")
                contract_docx_bytes = _employment_contract_to_docx_bytes(
                    employment_contract_draft
                )
                x1, x2 = st.columns(2)
                with x1:
                    st.download_button(
                        "Download Arbeitsvertrag JSON",
                        data=contract_json_bytes,
                        file_name="employment_contract_draft.json",
                        mime="application/json",
                    )
                with x2:
                    st.download_button(
                        "Download Arbeitsvertrag DOCX",
                        data=contract_docx_bytes,
                        file_name="employment_contract_draft.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )

        st.subheader("Export")
        md = _brief_to_markdown(brief)
        json_bytes = json.dumps(
            _build_structured_export_payload(brief), indent=2, ensure_ascii=False
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

        st.markdown("#### ESCO Mapping Report")
        esco_rows = _build_esco_mapping_report_rows()
        esco_mapping_json_bytes = json.dumps(
            esco_rows, indent=2, ensure_ascii=False
        ).encode("utf-8")
        esco_mapping_csv_bytes = _build_esco_mapping_report_csv(esco_rows)
        c4, c5 = st.columns(2)
        with c4:
            st.download_button(
                "Download ESCO Mapping Report CSV (UTF-8)",
                data=esco_mapping_csv_bytes,
                file_name="esco_mapping_report.csv",
                mime="text/csv; charset=utf-8",
            )
        with c5:
            st.download_button(
                "Download ESCO Mapping Report JSON",
                data=esco_mapping_json_bytes,
                file_name="esco_mapping_report.json",
                mime="application/json",
            )

    with advanced_tab:
        with st.expander("Salary Forecast", expanded=False):
            _render_salary_forecast(job, answers)
        st.caption(
            "Selection Matrix und Job-Ad-Editor sind direkt im Action Hub beim Job-Ad-Generator verfügbar."
        )
        with st.expander("Job-Ad-Ergebnis", expanded=False):
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
                st.text_area(
                    "Stellenanzeige",
                    value=custom_job_ad.job_ad_text,
                    height=_estimate_text_area_height(custom_job_ad.job_ad_text),
                    disabled=True,
                )
                st.markdown("**Zielgruppe**")
                for group in custom_job_ad.target_group:
                    st.write(f"- {group}")
                st.markdown("**AGG-Checkliste**")
                for item in custom_job_ad.agg_checklist:
                    st.write(f"- {item}")

                generation_notes_raw = custom_job_ad_raw.get("generation_notes", [])
                generation_notes = (
                    generation_notes_raw
                    if isinstance(generation_notes_raw, list)
                    else []
                )
                if generation_notes:
                    st.info(
                        "Zusätzliche Hinweise wurden aus dem Anzeigentext entfernt und hier separat abgelegt."
                    )
                    for note in generation_notes:
                        st.write(f"- {note}")

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
