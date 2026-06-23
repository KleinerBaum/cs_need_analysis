# wizard_pages/summary_view.py
"""Vertical Summary helpers extracted from ``08_summary.py``."""

import io
import hashlib
import json
from contextlib import nullcontext
from dataclasses import dataclass, replace
from collections import defaultdict
from html import escape
from typing import Any, Callable, Final, Mapping, Protocol, Sequence, TypedDict

import streamlit as st
import docx

from constants import (
    INTAKE_FACTS,
    FactKey,
    FactRequirementStage,
    FactResolutionStatus,
    FactSourceType,
    NON_INTAKE_STEP_KEYS,
    SSKey,
    STEP_KEY_BENEFITS,
    STEP_KEY_COMPANY,
    STEP_KEY_INTERVIEW,
    STEP_KEY_ROLE_TASKS,
    STEP_KEY_SKILLS,
    STEP_KEY_SUMMARY,
    SUMMARY_LOGO_UPLOAD_ALLOWED_EXTENSIONS,
    UI_PREFERENCE_CONFIDENCE_THRESHOLD,
)
from i18n import active_language
from interview_process import (
    build_candidate_stage_values,
    build_interview_export_payload,
    build_interview_value_rows,
    default_selected_interview_value_ids,
    normalize_interview_internal_flow,
)
from intake_facts import (
    build_intake_fact_resolution_state,
    get_intake_fact_evidence_state,
    get_intake_fact_state,
    latest_fact_confidence,
    mark_intake_facts_used_by_artifact,
    write_intake_fact,
)
from safe_html import render_static_html
from homepage_research import (
    normalize_company_website_research_payload as _normalize_company_website_research_payload,
)
from esco_client import EscoClient, EscoClientError
from esco_semantics import normalize_anchor_ref, sync_esco_semantic_state
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
from schemas import (
    BooleanSearchPack,
    EscoConceptRef,
    EscoMatrixCoverageRow,
    EscoMappingReport,
    EscoSemanticContext,
    EscoUnresolvedTermDecision,
    EmploymentContractDraft,
    InterviewPrepSheetHiringManager,
    InterviewPrepSheetHR,
    JobAdExtract,
    LanguageRequirement,
    OccupationContextProfile,
    OccupationQuestionContext,
    QuestionFlowProvenance,
    QuestionPlan,
    QuestionStep,
    VacancyBrief,
    VacancyStructuredData,
    CompanyWebsiteResearch,
)
from settings_openai import load_openai_settings
from state import (
    clear_error,
    get_esco_occupation_selected,
    get_answers,
    get_answer_meta,
    has_confirmed_esco_anchor,
    get_model_override,
    handle_unexpected_exception,
    set_answer,
)
from question_dependencies import should_show_question
from question_limits import select_visible_questions_for_step_scope
from step_status import build_step_status_payload
from components.design_system import (
    render_card_start,
    render_critical_gaps,
    render_next_best_action,
    render_output_header,
    render_pill,
)
from document_preview import document_preview_shell, markdown_article_preview_html
from summary_facts import (
    SummaryFactsRow,
    display_requirement_stage as _display_requirement_stage,
    display_salary_impact as _display_salary_impact,
    format_summary_answer_value as _format_summary_answer_value,
    format_summary_fact_value as _format_summary_fact_value,
    group_summary_fact_rows_by_area as _group_summary_fact_rows_by_area,
    status_for_answer_value as _status_for_answer_value,
    status_for_classification_value as _status_for_classification_value,
    status_for_value as _status_for_value,
    source_label_with_secondary_evidence as _source_label_with_secondary_evidence,
    summary_core_fact_row as _summary_core_fact_row,
    summary_fact_row_to_table_dict as _summary_fact_row_to_table_dict,
    summary_provenance_label as _summary_provenance_label,
)
from summary_artifacts import (
    artifact_display_label as _artifact_display_label,
    brief_pipeline_status_for_state,
    to_canonical_artifact_id as _to_canonical_artifact_id,
)
from summary_exports import (
    brief_to_markdown as _brief_to_markdown,
    build_summary_input_fingerprint as _build_summary_input_fingerprint,
)
from summary_esco import (
    build_esco_coverage_chart_spec as _build_esco_coverage_chart_spec,
    build_esco_coverage_kpis as _build_esco_coverage_kpis,
    build_esco_coverage_metrics as _build_esco_coverage_metrics,
    build_esco_mapping_report_csv as _build_esco_mapping_report_csv,
    extract_skills_step_raw_terms as _extract_skills_step_raw_terms,
    normalize_skill_term as _normalize_skill_term,
    to_esco_export_concepts as _to_esco_export_concepts,
)
from summary_job_ad import (
    build_publishable_job_ad_markdown as _build_publishable_job_ad_markdown,
    build_publishable_job_ad_plain_text as _build_publishable_job_ad_plain_text,
    dedupe_preserve_order as _dedupe_preserve_order,
    estimate_text_area_height as _estimate_text_area_height,
    sanitize_generated_job_ad as _sanitize_generated_job_ad,
)
from ui_components import (
    inject_pills_grid_css,
    render_boolean_risks,
    render_boolean_search_pack,
    render_boolean_supporting_terms,
    render_boolean_usage_notes,
    render_brief,
    render_employment_contract_draft,
    render_error_banner,
    render_interview_prep_fach,
    render_interview_prep_hr,
    render_openai_error,
)
from ux_copy_contract import VacancyCopyContext, build_step_copy
from ui_badges import render_provenance_badge
from usage_events import get_usage_events, record_artifact_generated
from usage_utils import usage_has_cache_hit
from wizard_pages.base import (
    WizardContext,
    WizardPage,
    get_current_ui_mode,
    nav_buttons,
    render_active_ui_mode_caption,
)

from wizard_pages.summary_exporters import (
    _brief_to_docx_bytes,
    _build_brief_structured_preview_payload,
    _build_structured_export_payload,
    _compute_esco_coverage_metrics,
    _employment_contract_to_docx_bytes,
    _interview_prep_fach_to_docx_bytes,
    _interview_prep_fach_to_pdf_bytes,
    _interview_prep_hr_to_docx_bytes,
    _job_ad_logo_payload,
    _job_ad_preview_html,
    _job_ad_preview_shell_options,
    _job_ad_to_docx_bytes,
    _job_ad_to_pdf_bytes,
    _normalize_logo_payload,
    _read_esco_shared_fields,
    _read_logo_payload,
    _read_saved_selection_labels,
)

from wizard_pages.summary_readiness import (
    SUMMARY_FACT_OVERVIEW_COLUMNS,
    SUMMARY_AREA_TO_STEP_KEY,
    SUMMARY_FACT_STEP_LABELS,
    SUMMARY_FACT_STEP_ORDER,
    SummaryMeta,
    SummaryArtifactGate,
    SummaryReleaseBlocker,
    SummaryStatus,
    SummaryViewModel,
    _apply_summary_fact_edits,
    _build_missing_critical_items,
    _build_summary_critical_gap_rows,
    _is_visible_summary_fact_row,
    _release_state_label,
    _summary_fact_row_id,
    _summary_fact_rows_by_step,
    _summary_visible_fact_rows,
)
from wizard_pages.summary_readiness_dashboard import (
    render_readiness_dashboard_header as _render_readiness_dashboard_header_impl,
    render_summary_readiness_metrics as _render_summary_readiness_metrics_impl,
)

from wizard_pages.summary_artifact_actions import (
    NextBestActionRecommendation,
    SummaryAction,
    _artifact_has_result,
    _artifact_pipeline_status,
    _artifact_status_label,
    _build_artifact_status_rows,
    _build_enrichment_timing_rows,
    _get_brief_status,
    _has_required_state,
    _mark_artifact_current,
    _read_artifact_change_request,
    _read_artifact_options,
    _resolve_active_artifact_id,
    _resolve_next_best_action_recommendation,
    _write_artifact_change_request,
    _write_artifact_options,
)

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


JOB_AD_PRESET_BLOCKS: dict[str, dict[str, str]] = {
    "Ausgewogen": {
        "summary": "Allround-Variante mit Aufgaben, Anforderungen und Benefits.",
        "style": (
            "Anzeigenziel: Ausgewogen. Aufgaben, Must-haves und konkrete Benefits "
            "gleichgewichtig darstellen."
        ),
    },
    "Kandidatenorientiert": {
        "summary": "Stärkerer Fokus auf Nutzen, Einstiegshürden und Bewerbung.",
        "style": (
            "Anzeigenziel: Kandidatenorientiert. Arbeitgebernutzen, konkrete Benefits "
            "und einen einfachen Bewerbungsweg besonders sichtbar machen."
        ),
    },
    "Senior/Expert": {
        "summary": "Schärft Verantwortung, fachlichen Anspruch und Wirkung der Rolle.",
        "style": (
            "Anzeigenziel: Senior/Expert. Verantwortung, Gestaltungsspielraum, "
            "fachliche Tiefe und erwartete Erfahrung klar herausarbeiten."
        ),
    },
    "Kurz & direkt": {
        "summary": "Kompakte Anzeige mit wenigen, klaren Entscheidungspunkten.",
        "style": (
            "Anzeigenziel: Kurz & direkt. Anzeige knapp halten, Redundanzen vermeiden "
            "und nur die entscheidenden Aufgaben, Anforderungen und Benefits nennen."
        ),
    },
}


JOB_AD_ADDRESS_BLOCKS: dict[str, str] = {
    "Du": "Ansprache: Durchgängig in Du-Form formulieren.",
    "Sie": "Ansprache: Durchgängig in Sie-Form formulieren.",
}


JOB_AD_TONE_BLOCKS: dict[str, str] = {
    "Professionell & nahbar": (
        "Tonalität: Professionell, klar und nahbar. Aktiv formulieren, keine "
        "Buzzword-Überladung."
    ),
    "Direkt & pragmatisch": (
        "Tonalität: Direkt, konkret und pragmatisch. Keine übertriebene "
        "Marketing-Sprache."
    ),
    "Motivierend": (
        "Tonalität: Motivierend und kandidatenorientiert, ohne fachliche "
        "Anforderungen weichzuzeichnen."
    ),
}


JOB_AD_LENGTH_BLOCKS: dict[str, str] = {
    "Kompakt": (
        "Länge: Kompakt halten (ca. 350–500 Wörter), Fokus auf Aufgaben, Must-haves "
        "und konkrete Benefits."
    ),
    "Standard": (
        "Länge: Standardumfang nutzen (ca. 500–700 Wörter), mit klaren Abschnitten "
        "für Aufgabe, Profil, Angebot und Bewerbung."
    ),
    "Ausführlich": (
        "Länge: Ausführlicher formulieren, wenn dadurch Rolle, Kontext und Angebot "
        "konkreter werden."
    ),
}


JOB_AD_CTA_BLOCKS: dict[str, str] = {
    "Deutlich": (
        "CTA: Klare Handlungsaufforderung mit einfachem Bewerbungsweg und nächstem "
        "Schritt."
    ),
    "Niedrige Hürde": (
        "CTA: Bewerbungshürde niedrig darstellen, z. B. kurze Bewerbung ohne "
        "unnötige Pflichtangaben."
    ),
    "Zurückhaltend": (
        "CTA: Sachlich und unaufdringlich formulieren, aber Bewerbungsweg klar "
        "benennen."
    ),
}


JOB_AD_OPTIMIZATION_BLOCKS: dict[str, str] = {
    "Kürzer formulieren": "Bitte die Anzeige kürzen und Wiederholungen entfernen.",
    "Konkreter machen": (
        "Bitte generische Aussagen durch konkrete Aufgaben, Anforderungen und "
        "Arbeitgeberangebote ersetzen."
    ),
    "CTA stärken": "Bitte den CTA sichtbarer und handlungsorientierter formulieren.",
    "Benefits sichtbarer": (
        "Bitte die wichtigsten Benefits früher und konkreter herausarbeiten."
    ),
}


JOB_AD_ALWAYS_ON_COMPLIANCE_TEXT: Final[str] = (
    "Compliance: AGG-konforme, inklusive und diskriminierungsfreie Sprache nutzen; "
    "fehlende Informationen klar markieren und nicht halluzinieren."
)


class RenderableContainer(Protocol):
    def __enter__(self) -> object: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: Any,
    ) -> bool | None: ...


SummaryTabs = tuple[
    RenderableContainer,
    RenderableContainer,
    RenderableContainer,
    RenderableContainer,
]


SUMMARY_RELEASE_FACT_AREAS_BY_ARTIFACT: Final[dict[str, frozenset[str] | None]] = {
    "brief": None,
    "job_ad": frozenset(
        {
            "Kernprofil",
            "Klassifikation",
            "Routing",
            "Unternehmen",
            "Team",
            "Rolle",
            "Rolle & Aufgaben",
            "Skills",
            "Benefits",
            "Rechtliches",
        }
    ),
    "interview_hr": frozenset(
        {
            "Kernprofil",
            "Unternehmen",
            "Team",
            "Rolle",
            "Rolle & Aufgaben",
            "Skills",
            "Interview",
            "Kandidatenkommunikation",
        }
    ),
    "interview_fach": frozenset(
        {
            "Kernprofil",
            "Rolle",
            "Rolle & Aufgaben",
            "Skills",
            "Interview",
        }
    ),
    "boolean_search": frozenset(
        {
            "Kernprofil",
            "Klassifikation",
            "Rolle",
            "Rolle & Aufgaben",
            "Skills",
        }
    ),
    "employment_contract": frozenset(
        {
            "Kernprofil",
            "Unternehmen",
            "Rolle",
            "Rolle & Aufgaben",
            "Benefits",
            "Rechtliches",
            "Zeitplan",
            "Timeline",
            "Timing",
        }
    ),
}


def _widget_key(base_key: SSKey, suffix: str | None = None) -> str:
    if not suffix:
        return base_key.value
    return f"{base_key.value}.{suffix}"


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
        "Beruf (ESCO)",
        (selected_occupation or {}).get("title", ""),
        "ESCO",
        False,
    )
    add_row("Basis", "Unternehmen", job.company_name or "", "Jobspec", True)
    add_row("Basis", "Marke", job.brand_name or "", "Jobspec", False)
    add_row("Basis", "Anstellungsart", job.employment_type or "", "Jobspec", True)
    add_row("Basis", "Vertragsart", job.contract_type or "", "Jobspec", True)
    add_row("Standort", "Ort", job.location_city or "", "Jobspec", True)
    add_row("Standort", "Land", job.location_country or "", "Jobspec", True)
    add_row("Standort", "Remote-Regelung", job.remote_policy or "", "Jobspec", False)
    add_row("Rolle", "Kurzbeschreibung", job.role_overview or "", "Jobspec", True)
    for value in job.must_have_skills:
        add_row("Skills", "Must-have", value, "Jobspec", True)
    for value in job.nice_to_have_skills:
        add_row("Skills", "Nice-to-have", value, "Jobspec", False)
    for value in job.benefits:
        add_row("Benefits", "Benefit", value, "Jobspec", False)
    for value in _read_saved_selection_labels(SSKey.BENEFITS_SELECTED):
        add_row("Benefits", "Ausgewählter Benefit", value, "Auswahl", False)
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
                "Manager-Eingabe",
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
                        "Manager-Eingabe",
                        answer_key,
                        formatted_language,
                        "Antwort",
                        False,
                    )
                    continue
                add_row("Manager-Eingabe", answer_key, str(value), "Antwort", False)
            continue
        add_row("Manager-Eingabe", answer_key, str(raw), "Antwort", False)

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


def _selection_options_by_group(rows: list[dict[str, str]]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        grouped[f"{row['Kategorie']} · {row['Feld']}"].append(row["Wert"])
    return {
        group_key: sorted(set(values))
        for group_key, values in grouped.items()
        if values
    }


def _first_existing_group(
    grouped: dict[str, list[str]], candidate_keys: Sequence[str]
) -> str | None:
    for key in candidate_keys:
        if key in grouped and grouped[key]:
            return key
    return None


def _render_guided_multiselect(
    *,
    label: str,
    group_key: str | None,
    grouped: dict[str, list[str]],
    selected_values: dict[str, list[str]],
    suffix: str,
    max_default: int = 4,
    help_text: str | None = None,
) -> None:
    if group_key is None:
        st.caption(f"{label}: Keine passenden Daten vorhanden.")
        return
    options = grouped.get(group_key, [])
    if not options:
        st.caption(f"{label}: Keine passenden Daten vorhanden.")
        return
    picks = st.multiselect(
        label,
        options=options,
        default=options[:max_default],
        key=_widget_key(SSKey.SUMMARY_SELECTION_PICK_WIDGET_PREFIX, suffix),
        help=help_text,
    )
    if picks:
        selected_values[group_key] = picks


def _build_job_ad_styleguide_text(
    *,
    preset: str,
    address: str,
    tone: str,
    length: str,
    cta: str,
    manual_styleguide: str,
) -> str:
    blocks = [
        JOB_AD_PRESET_BLOCKS.get(preset, {}).get("style", ""),
        JOB_AD_ADDRESS_BLOCKS.get(address, ""),
        JOB_AD_TONE_BLOCKS.get(tone, ""),
        JOB_AD_LENGTH_BLOCKS.get(length, ""),
        JOB_AD_CTA_BLOCKS.get(cta, ""),
        JOB_AD_ALWAYS_ON_COMPLIANCE_TEXT,
        manual_styleguide.strip(),
    ]
    return "\n\n".join(block for block in blocks if block)


def _build_job_ad_change_request_text(
    *, optimization_picks: Sequence[str], manual_change_request: str
) -> str:
    blocks = [
        JOB_AD_OPTIMIZATION_BLOCKS[pick]
        for pick in optimization_picks
        if pick in JOB_AD_OPTIMIZATION_BLOCKS
    ]
    if manual_change_request.strip():
        blocks.append(manual_change_request.strip())
    return "\n\n".join(blocks)


def _render_job_ad_settings_summary(
    *,
    preset: str,
    address: str,
    length: str,
    selected_values: dict[str, list[str]],
    critical_gaps: list[str],
) -> None:
    focus_labels = [
        key.split(" · ", 1)[1]
        for key, values in selected_values.items()
        if values and " · " in key
    ]
    focus_text = ", ".join(focus_labels[:4]) if focus_labels else "Standardauswahl"
    gaps_text = ", ".join(critical_gaps[:3]) if critical_gaps else "Keine kritischen Lücken"
    st.markdown("**Einstellungs-Zusammenfassung**")
    st.write(f"- Zielgruppe: {preset}")
    st.write(f"- Länge: {length}")
    st.write(f"- Ansprache: {address}")
    st.write(f"- Fokus: {focus_text}")
    st.write(f"- Offene Lücken: {gaps_text}")


def _render_pills_multiselect(label: str, options: list[str], key: str) -> list[str]:
    if hasattr(st, "pills"):
        inject_pills_grid_css()
        return st.pills(label, options=options, selection_mode="multi", key=key) or []
    return st.multiselect(label, options=options, default=options, key=key)


def _render_selection_matrix(
    *,
    job: JobAdExtract,
    answers: dict[str, Any],
) -> tuple[dict[str, list[str]], list[str]]:
    rows = _build_selection_rows(job, answers)
    st.subheader("Datenmatrix für Stellenanzeigen-Generierung")
    st.dataframe(
        rows,
        width="stretch",
        hide_index=True,
        column_config={
            "Kategorie": st.column_config.TextColumn("Abschnitt"),
            "Feld": st.column_config.TextColumn("Angabe"),
            "Wert": st.column_config.TextColumn("Inhalt"),
            "Quelle": st.column_config.TextColumn("Quelle"),
            "Kritisch": st.column_config.TextColumn("Wichtig"),
        },
    )

    grouped: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        grouped[f"{row['Kategorie']} · {row['Feld']}"].append(row["Wert"])

    st.markdown("**Auswahl (Multi-Select Pills pro Angabe)**")
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


def _render_summary_hero(vm: SummaryViewModel) -> None:
    st.header(_build_summary_headline(vm.meta, vm.status))
    st.markdown(_build_summary_subheader(vm.meta, vm.status))
    _render_summary_meta_badges(vm.meta, vm.status)


def _build_summary_headline(
    meta: SummaryMeta, status: SummaryStatus | None = None
) -> str:
    if status is not None:
        if status.ready_for_follow_ups:
            return f"{status.readiness_percent}% bereit für Recruiting-Unterlagen"
        return f"{status.readiness_percent}% bereit - offene Punkte zuerst klären"
    role = meta.role_label
    company = meta.company_label
    if role and company:
        return f"{role} bei {company} – entscheidungsreif zusammengefasst"
    if role:
        return f"{role} – entscheidungsreif zusammengefasst"
    if company:
        return f"Hiring-Zusammenfassung für {company}"
    return "Hiring-Zusammenfassung mit klaren nächsten Schritten"


def _build_summary_subheader(meta: SummaryMeta, status: SummaryStatus) -> str:
    role = meta.role_label or "Nicht angegeben"
    company = meta.company_label or "Nicht angegeben"
    country = meta.country_label or "Nicht angegeben"
    mapping_fragments: list[str] = []
    if status.esco_ready:
        mapping_fragments.append(
            f"semantischer Anker bestätigt ({meta.selected_occupation_title})"
        )
    else:
        mapping_fragments.append("semantischer Anker noch offen")
    mapping_status = " und ".join(mapping_fragments)

    readiness_intro = (
        "Die Vakanz ist inhaltlich bereit; prüfen Sie nur noch die gewünschte Unterlage vor Export."
        if status.ready_for_follow_ups
        else "Die Vakanz ist noch nicht releasebereit."
    )
    brief_clause = (
        "Der Recruiting Brief ist aktuell und als Grundlage verwendbar."
        if status.brief_state == "current"
        else status.brief_status_label
    )
    return (
        f"**Für {company} ist die Rolle {role} für den Zielmarkt {country} als klare Hiring-Story "
        "zusammengeführt.**\n\n"
        f"{readiness_intro} Stand: **{status.completion_text}**. {brief_clause}\n\n"
        f"Die fachliche Verortung ist {mapping_status}, damit Übergaben an Sourcing, Interview und "
        "Angebotsphase konsistent bleiben.\n\n"
        f"**Nächster Schritt:** {status.next_step}."
    )


def _render_summary_meta_badges(meta: SummaryMeta, status: SummaryStatus) -> None:
    readiness = (
        "Releasebereit"
        if status.ready_for_follow_ups
        else ("Brief aktualisieren" if status.brief_state == "stale" else "Blocker prüfen")
    )
    badges = (
        ("Rolle", meta.role_label or "Nicht angegeben"),
        ("Unternehmen", meta.company_label or "Nicht angegeben"),
        ("Land", meta.country_label or "Nicht angegeben"),
        ("ESCO", "✅" if status.esco_ready else "—"),
        ("Bereitschaft", readiness),
    )
    columns = st.columns(3)
    for idx, (label, value) in enumerate(badges):
        columns[idx % len(columns)].metric(label, str(value))


def _render_esco_coverage_kpis() -> None:
    shared_esco = _read_esco_shared_fields()
    coverage_metrics = _compute_esco_coverage_metrics(shared_esco)
    requirements_total = coverage_metrics["essential_total"] + coverage_metrics["optional_total"]
    unmapped_requirements = len(shared_esco.get("unmapped_terms", []))
    if requirements_total == 0 and unmapped_requirements == 0:
        st.info("Keine ESCO-RAG-Anforderungsdaten verfügbar.")
    else:
        st.caption("ESCO-RAG-Abdeckung: kompakte KPI-Übersicht zur Anforderungsabdeckung")
        kpis = _build_esco_coverage_kpis(
            metrics=coverage_metrics,
            unmapped_requirements_count=unmapped_requirements,
        )
        columns = st.columns(2)
        for idx, (label, value) in enumerate(kpis):
            columns[idx % len(columns)].metric(label=label, value=str(value))


def _render_summary_facts_column_overview(vm: SummaryViewModel) -> None:
    st.markdown("### Fakten")
    _render_esco_coverage_kpis()
    visible_rows = [
        row for row in vm.fact_rows if _is_visible_summary_fact_row(row.to_dict())
    ]
    grouped_rows = _group_summary_fact_rows_by_area(visible_rows)
    if not grouped_rows:
        st.info("Keine Fakten verfügbar.")
        return

    for start_index in range(0, len(grouped_rows), SUMMARY_FACT_OVERVIEW_COLUMNS):
        row_groups = grouped_rows[
            start_index : start_index + SUMMARY_FACT_OVERVIEW_COLUMNS
        ]
        columns = st.columns(len(row_groups), gap="large")
        for column, (area, fact_rows) in zip(columns, row_groups):
            with column:
                with st.container(border=True):
                    st.markdown(f"**{area}**")
                    for fact in fact_rows:
                        value = str(fact.wert or "").strip() or "Nicht beantwortet"
                        st.markdown(f"**{fact.feld}**")
                        st.write(value)
                        st.caption(_summary_fact_caption(fact))


def _render_summary_facts_section(vm: SummaryViewModel) -> None:
    st.markdown("### Fakten")
    _render_esco_coverage_kpis()
    _render_summary_facts_table(
        [_summary_fact_row_to_table_dict(row) for row in vm.fact_rows]
    )


def _summary_fact_caption(row: SummaryFactsRow) -> str:
    parts = [row.status, f"Quelle: {row.quelle}"]
    if row.provenienz:
        parts.append(f"Provenienz: {row.provenienz}")
    salary = _display_salary_impact(row.salary_impact)
    if salary and salary != "Kein Salary-Einfluss":
        parts.append(f"Salary: {salary}")
    requirement = _display_requirement_stage(row.requirement_stage)
    if requirement and requirement != "Optional":
        parts.append(requirement)
    if row.website_enrichable:
        parts.append("Zweitquelle: Website-Prüfung")
    return " · ".join(parts)


def _render_summary_facts_table(rows: list[dict[str, str]]) -> None:
    table_col, filter_col = st.columns([2, 1], gap="large")
    with filter_col:
        search_query = (
            st.text_input(
                "Suche in Fakten",
                key=SSKey.SUMMARY_FACTS_SEARCH.value,
                placeholder="Bereich, Feld, Wert oder Quelle filtern …",
            )
            .strip()
            .lower()
        )
        status_filter = st.selectbox(
            "Statusfilter",
            options=[
                "Alle",
                "Vollständig",
                "Teilweise",
                "Automatisch erkannt",
            ],
            key=SSKey.SUMMARY_FACTS_STATUS_FILTER.value,
        )

    filtered_rows = [row for row in rows if _is_visible_summary_fact_row(row)]
    if search_query:
        filtered_rows = [
            row
            for row in filtered_rows
            if search_query
            in " ".join(
                str(row.get(column, "")).lower()
                for column in (
                    "Bereich",
                    "Feld",
                    "Wert",
                    "Quelle",
                    "Status",
                    "Provenienz",
                    "Salary",
                    "Pflichtigkeit",
                    "Second Source",
                )
            )
        ]
    if status_filter != "Alle":
        filtered_rows = [
            row for row in filtered_rows if row.get("Status", "") == status_filter
        ]

    with table_col:
        st.dataframe(
            filtered_rows,
            width="stretch",
            hide_index=True,
            column_order=[
                "Bereich",
                "Feld",
                "Wert",
                "Quelle",
                "Status",
                "Provenienz",
                "Salary",
                "Pflichtigkeit",
                "Second Source",
            ],
            column_config={
                "Bereich": st.column_config.TextColumn("Abschnitt"),
                "Feld": st.column_config.TextColumn("Angabe"),
                "Wert": st.column_config.TextColumn("Inhalt"),
                "Quelle": st.column_config.TextColumn("Quelle"),
                "Status": st.column_config.TextColumn("Status"),
                "Provenienz": st.column_config.TextColumn("Provenienz"),
                "Salary": st.column_config.TextColumn("Salary"),
                "Pflichtigkeit": st.column_config.TextColumn("Pflichtigkeit"),
                "Second Source": st.column_config.TextColumn("Zweitquelle"),
            },
        )


def _render_summary_facts_matrix(vm: SummaryViewModel) -> None:
    visible_rows = _summary_visible_fact_rows(vm)
    grouped_rows = _summary_fact_rows_by_step(visible_rows)
    st.markdown("### Fakten je Schritt")
    st.caption("Nur vorhandene Werte werden angezeigt. Änderungen werden in die kanonischen Intake-Daten zurückgeschrieben.")
    if not any(grouped_rows.values()):
        st.info("Keine auswertbaren Fakten vorhanden.")
        return

    columns = st.columns(len(SUMMARY_FACT_STEP_ORDER), gap="small")
    for column, step_key in zip(columns, SUMMARY_FACT_STEP_ORDER):
        rows = grouped_rows[step_key]
        with column:
            with st.container(border=True):
                st.markdown(f"**{SUMMARY_FACT_STEP_LABELS[step_key]}**")
                if not rows:
                    st.caption("Keine Werte vorhanden.")
                    continue
                row_lookup = {_summary_fact_row_id(row): row for row in rows}
                editor_rows = [
                    {
                        "_id": row_id,
                        "Feld": row.feld,
                        "Wert": row.wert,
                        "Quelle": row.quelle,
                        "Salary": _display_salary_impact(row.salary_impact),
                        "Pflichtigkeit": _display_requirement_stage(
                            row.requirement_stage
                        ),
                        "Second Source": (
                            "Website-Prüfung" if row.website_enrichable else ""
                        ),
                    }
                    for row_id, row in row_lookup.items()
                ]
                editable_count = sum(1 for row in rows if row.editable)
                data_editor = getattr(st, "data_editor", None)
                with st.form(
                    _widget_key(
                        SSKey.SUMMARY_ACTION_WIDGET_PREFIX,
                        f"facts.form.{step_key}",
                    ),
                    clear_on_submit=False,
                ):
                    if callable(data_editor):
                        edited = data_editor(
                            editor_rows,
                            key=_widget_key(
                                SSKey.SUMMARY_ACTION_WIDGET_PREFIX,
                                f"facts.{step_key}",
                            ),
                            width="stretch",
                            hide_index=True,
                            column_order=[
                                "Feld",
                                "Wert",
                                "Quelle",
                                "Salary",
                                "Pflichtigkeit",
                                "Second Source",
                            ],
                            column_config={
                                "Feld": st.column_config.TextColumn(
                                    "Angabe", disabled=True
                                ),
                                "Wert": st.column_config.TextColumn("Inhalt"),
                                "Quelle": st.column_config.TextColumn(
                                    "Quelle", disabled=True
                                ),
                                "Salary": st.column_config.TextColumn(
                                    "Salary", disabled=True
                                ),
                                "Pflichtigkeit": st.column_config.TextColumn(
                                    "Pflichtigkeit",
                                    disabled=True,
                                ),
                                "Second Source": st.column_config.TextColumn(
                                    "Zweitquelle",
                                    disabled=True,
                                ),
                            },
                        )
                    else:
                        st.dataframe(
                            editor_rows,
                            width="stretch",
                            hide_index=True,
                            column_order=[
                                "Feld",
                                "Wert",
                                "Quelle",
                                "Salary",
                                "Pflichtigkeit",
                                "Second Source",
                            ],
                            column_config={
                                "Feld": st.column_config.TextColumn("Angabe"),
                                "Wert": st.column_config.TextColumn("Inhalt"),
                                "Quelle": st.column_config.TextColumn("Quelle"),
                                "Salary": st.column_config.TextColumn("Salary"),
                                "Pflichtigkeit": st.column_config.TextColumn(
                                    "Pflichtigkeit"
                                ),
                                "Second Source": st.column_config.TextColumn(
                                    "Zweitquelle"
                                ),
                            },
                        )
                        edited = editor_rows
                    submitted = st.form_submit_button(
                        "Änderungen speichern",
                        width="stretch",
                        disabled=editable_count == 0,
                    )
                if submitted:
                    if _apply_summary_fact_edits(
                        edited_rows=list(edited),
                        row_lookup=row_lookup,
                    ):
                        st.success("Änderungen gespeichert.")
                        st.rerun()
                    else:
                        st.info("Keine Änderungen erkannt.")


def _summary_gap_navigation_payload(row: Mapping[str, str]) -> dict[str, str]:
    return {
        "target_step": str(row.get("target_step") or "").strip(),
        "target_section": str(row.get("target_section") or "").strip(),
        "target_fact_key": str(row.get("target_fact_key") or "").strip(),
        "target_question_id": str(row.get("target_question_id") or "").strip(),
        "label": str(row.get("Feld") or "").strip(),
        "source": "summary_critical_gap",
    }


def _render_summary_critical_gap_actions(
    gap_rows: Sequence[Mapping[str, str]],
    *,
    ctx: WizardContext,
) -> None:
    for index, row in enumerate(gap_rows):
        field_label = str(row.get("Feld") or "").strip() or "Angabe"
        step_label = str(row.get("Schritt") or "").strip() or "Wizard"
        status = str(row.get("Status") or "").strip()
        requirement = str(row.get("Pflichtigkeit") or "").strip()
        action = str(row.get("Aktion") or "").strip()
        provenance = str(row.get("Provenienz") or "").strip()
        target = _summary_gap_navigation_payload(row)
        target_step = target["target_step"]
        row_id = str(row.get("_id") or f"{index}").strip()
        with st.container(border=True):
            st.markdown(f"**{field_label}**")
            meta = " · ".join(
                item for item in (step_label, status, requirement) if item
            )
            if meta:
                st.caption(meta)
            if provenance:
                render_provenance_badge(label=provenance, streamlit_module=st)
            if action:
                st.caption(action)
            if st.button(
                "Zum Feld",
                key=_widget_key(
                    SSKey.SUMMARY_ACTION_WIDGET_PREFIX,
                    f"critical_gap.{row_id}.goto",
                ),
                disabled=not target_step,
            ):
                st.session_state[SSKey.NAV_DEEP_LINK_TARGET.value] = target
                ctx.goto(target_step)
                st.rerun()


def _render_summary_critical_gaps_table(
    vm: SummaryViewModel,
    *,
    ctx: WizardContext | None = None,
) -> None:
    st.markdown("### Kritische Lücken")
    gap_rows = _build_summary_critical_gap_rows(vm)
    if not gap_rows:
        st.success("Keine kritischen Lücken erkannt.")
        return
    if ctx is not None:
        _render_summary_critical_gap_actions(gap_rows, ctx=ctx)
        return
    st.dataframe(
        gap_rows,
        width="stretch",
        hide_index=True,
        column_order=["Schritt", "Feld", "Status", "Pflichtigkeit", "Aktion"],
        column_config={
            "Schritt": st.column_config.TextColumn("Schritt"),
            "Feld": st.column_config.TextColumn("Angabe"),
            "Status": st.column_config.TextColumn("Status"),
            "Pflichtigkeit": st.column_config.TextColumn("Pflichtigkeit"),
            "Aktion": st.column_config.TextColumn("Nächster Schritt"),
        },
    )


def _default_job_ad_selected_values(vm: SummaryViewModel) -> dict[str, list[str]]:
    rows = _build_selection_rows(vm.job, vm.answers)
    grouped_values = _selection_options_by_group(rows)
    selected_values: dict[str, list[str]] = {}
    for group_key, max_items in (
        (_first_existing_group(grouped_values, ("Rolle · Kurzbeschreibung", "Manager-Eingabe · role_tasks")), 3),
        (_first_existing_group(grouped_values, ("Skills · Must-have", "Manager-Eingabe · must_have_skills")), 5),
        (_first_existing_group(grouped_values, ("Benefits · Ausgewählter Benefit", "Benefits · Benefit")), 5),
    ):
        values = grouped_values.get(group_key)
        if values:
            selected_values[group_key] = values[:max_items]
    for group_key in (
        "Basis · Titel",
        "Basis · Unternehmen",
        "Basis · Anstellungsart",
        "Basis · Vertragsart",
        "Standort · Ort",
        "Standort · Land",
        "Standort · Remote",
        "Kontakt · Ansprechpartner",
        "Kontakt · Kontakt E-Mail",
    ):
        values = grouped_values.get(group_key)
        if values:
            selected_values[group_key] = values
    return selected_values


def _append_distinct_text(output: list[str], values: Any, *, limit: int = 10) -> None:
    if isinstance(values, (str, bytes)) or isinstance(values, Mapping):
        iterable: Sequence[Any] = [values]
    elif isinstance(values, Sequence):
        iterable = values
    else:
        iterable = []
    seen = {item.casefold() for item in output}
    for item in iterable:
        if isinstance(item, Mapping):
            value = str(
                item.get("label") or item.get("title") or item.get("name") or ""
            )
        else:
            value = str(item)
        value = value.strip()
        dedupe_key = value.casefold()
        if not value or dedupe_key in seen:
            continue
        output.append(value)
        seen.add(dedupe_key)
        if len(output) >= limit:
            return


def _build_fach_competency_suggestions(vm: SummaryViewModel) -> list[str]:
    suggestions: list[str] = []
    brief = vm.artifacts.brief
    if brief is not None:
        _append_distinct_text(suggestions, brief.must_have, limit=10)
        _append_distinct_text(
            suggestions, brief.structured_data.selected_skills or [], limit=10
        )
        esco_must = brief.structured_data.esco_skills_must or []
        _append_distinct_text(suggestions, esco_must, limit=10)
        _append_distinct_text(suggestions, brief.evaluation_rubric, limit=10)
        _append_distinct_text(suggestions, brief.top_responsibilities, limit=10)
    _append_distinct_text(suggestions, vm.job.must_have_skills, limit=10)
    _append_distinct_text(suggestions, vm.job.soft_skills, limit=10)
    _append_distinct_text(suggestions, vm.job.domain_expertise, limit=10)
    _append_distinct_text(suggestions, vm.job.responsibilities, limit=10)
    _append_distinct_text(
        suggestions, vm.answers.get(FactKey.SKILLS_MUST_HAVE_SKILLS.value, []), limit=10
    )
    return suggestions[:10]


def _read_optional_text_upload(uploaded_file: Any) -> str:
    if uploaded_file is None:
        return ""
    try:
        raw_bytes = uploaded_file.getvalue()
    except Exception:
        return ""
    try:
        return raw_bytes.decode("utf-8").strip()
    except UnicodeDecodeError:
        return raw_bytes.decode("latin-1", errors="ignore").strip()


def _render_job_ad_compact_controls(vm: SummaryViewModel) -> None:
    preset = st.selectbox(
        "Zielgruppe",
        options=list(JOB_AD_PRESET_BLOCKS.keys()),
        index=0,
        key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, "job_ad.target_group"),
    )
    left, right = st.columns(2)
    with left:
        address = st.selectbox(
            "Ansprache",
            options=list(JOB_AD_ADDRESS_BLOCKS.keys()),
            index=0,
            key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, "job_ad.address.compact"),
        )
        length = st.selectbox(
            "Länge",
            options=list(JOB_AD_LENGTH_BLOCKS.keys()),
            index=0,
            key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, "job_ad.length.compact"),
        )
    with right:
        tone = st.selectbox(
            "Tonalität",
            options=list(JOB_AD_TONE_BLOCKS.keys()),
            index=0,
            key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, "job_ad.tone.compact"),
        )
        cta = st.selectbox(
            "CTA",
            options=list(JOB_AD_CTA_BLOCKS.keys()),
            index=0,
            key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, "job_ad.cta.compact"),
        )
    logo_file = st.file_uploader(
        "Logo (PNG/JPG)",
        type=[
            extension.lstrip(".")
            for extension in SUMMARY_LOGO_UPLOAD_ALLOWED_EXTENSIONS
        ],
        key=SSKey.SUMMARY_LOGO_UPLOAD_WIDGET.value,
    )
    normalized_logo = _normalize_logo_payload(logo_file)
    st.session_state[SSKey.SUMMARY_LOGO.value] = normalized_logo
    if logo_file is not None and normalized_logo is None:
        st.warning(
            "Logo kann nicht verwendet werden. Bitte PNG oder JPG/JPEG mit "
            "unterstützter Größe und gültigen Bilddaten verwenden."
        )
    style_upload = st.file_uploader(
        "Styleguide (TXT/MD)",
        type=["txt", "md"],
        key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, "job_ad.style_upload"),
    )
    manual_styleguide = st.text_area(
        "Styleguide / No-Gos",
        value="",
        placeholder="z. B. Corporate Language, Wording, No-Gos",
        key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, "job_ad.style_text"),
        height=90,
    )
    uploaded_styleguide = _read_optional_text_upload(style_upload)
    styleguide = _build_job_ad_styleguide_text(
        preset=preset,
        address=address,
        tone=tone,
        length=length,
        cta=cta,
        manual_styleguide="\n".join(
            item for item in (uploaded_styleguide, manual_styleguide) if item
        ),
    )
    selected_values = _default_job_ad_selected_values(vm)
    st.session_state[SSKey.SUMMARY_SELECTIONS.value] = selected_values
    st.session_state[SSKey.SUMMARY_STYLEGUIDE_TEXT.value] = styleguide
    _write_artifact_options(
        "job_ad",
        {
            "target_group": preset,
            "address": address,
            "tone": tone,
            "length": length,
            "cta": cta,
            "logo_filename": normalized_logo.get("name") if normalized_logo else "",
            "styleguide_uploaded": bool(uploaded_styleguide),
        },
    )


def _render_interview_compact_controls(vm: SummaryViewModel) -> str:
    sheet_type = st.selectbox(
        "Sheet",
        options=["HR", "Fachbereich"],
        key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, "interview.sheet_type"),
    )
    left, right = st.columns(2)
    with left:
        stage = st.selectbox(
            "Phase",
            options=["Screening", "Erstgespräch", "Fachinterview", "Finale Runde"],
            index=0,
            key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, "interview.stage"),
        )
        duration = st.selectbox(
            "Dauer",
            options=[30, 45, 60, 90],
            index=1,
            key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, "interview.duration"),
        )
    with right:
        focus = st.selectbox(
            "Fokus",
            options=["Kultur & Motivation", "Must-haves", "Fachliche Vertiefung", "Scorecard"],
            index=1,
            key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, "interview.focus"),
        )
        depth = st.selectbox(
            "Bewertung",
            options=["Überblick", "Standard", "Detailliert"],
            index=1,
            key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, "interview.depth"),
        )
    artifact_id = "interview_fach" if sheet_type == "Fachbereich" else "interview_hr"
    options = {
        "sheet_type": sheet_type,
        "stage": stage,
        "duration_minutes": duration,
        "focus": focus,
        "evaluation_depth": depth,
    }
    if artifact_id == "interview_fach":
        suggestions = _build_fach_competency_suggestions(vm)
        saved_options = _read_artifact_options("interview_fach")
        saved_competencies = [
            str(item).strip()
            for item in saved_options.get("selected_competencies", [])
            if str(item).strip()
        ] if isinstance(saved_options.get("selected_competencies"), list) else []
        default_competencies = [
            item for item in saved_competencies if item in suggestions
        ] or suggestions[: min(5, len(suggestions))]
        selected_competencies = st.multiselect(
            "Kompetenzen validieren",
            options=suggestions,
            default=default_competencies,
            help="Bis zu 10 fachbereichsbezogene Vorschläge aus Brief, Skills und ESCO-Kontext.",
            key=_widget_key(
                SSKey.SUMMARY_ACTION_WIDGET_PREFIX,
                "interview_fach.competencies",
            ),
        )
        left_fach, right_fach = st.columns(2)
        with left_fach:
            questions_per_block = st.selectbox(
                "Fragen je Frageblock",
                options=[1, 2, 3, 4, 5],
                index=2,
                key=_widget_key(
                    SSKey.SUMMARY_ACTION_WIDGET_PREFIX,
                    "interview_fach.questions_per_block",
                ),
            )
        with right_fach:
            debrief_question_count = st.selectbox(
                "Debrief-Fragen",
                options=[1, 2, 3, 4, 5],
                index=2,
                key=_widget_key(
                    SSKey.SUMMARY_ACTION_WIDGET_PREFIX,
                    "interview_fach.debrief_question_count",
                ),
            )
        options.update(
            {
                "selected_competencies": selected_competencies[:10],
                "questions_per_block": questions_per_block,
                "debrief_question_count": debrief_question_count,
            }
        )
    _write_artifact_options(artifact_id, options)
    return artifact_id


def _render_boolean_compact_controls() -> None:
    left, right = st.columns(2)
    with left:
        channels = st.multiselect(
            "Kanäle",
            options=["Google", "LinkedIn", "XING"],
            default=["Google", "LinkedIn", "XING"],
            key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, "boolean.channels"),
        )
        breadth = st.selectbox(
            "Suchbreite",
            options=["breit", "ausgewogen", "fokussiert"],
            index=1,
            key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, "boolean.breadth"),
        )
    with right:
        keyword_count = st.number_input(
            "Schlagworte",
            min_value=3,
            max_value=15,
            value=8,
            step=1,
            key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, "boolean.keyword_count"),
        )
        operators = st.multiselect(
            "Operatoren",
            options=["AND", "OR", "NOT", '"..."', "(...)", "site:", "-"],
            default=["AND", "OR", "NOT", '"..."', "(...)"],
            key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, "boolean.operators"),
        )
    locations = st.text_input(
        "Zielregionen",
        value="",
        placeholder="z. B. Berlin, remote DACH",
        key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, "boolean.locations"),
    )
    exclusions = st.text_input(
        "Ausschlüsse",
        value="",
        placeholder="z. B. Praktikum, Werkstudent",
        key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, "boolean.exclusions"),
    )
    _write_artifact_options(
        "boolean_search",
        {
            "channels": channels,
            "breadth": breadth,
            "keyword_count": int(keyword_count),
            "operators": operators,
            "target_locations": locations,
            "exclusions": exclusions,
        },
    )


def _render_contract_compact_controls() -> None:
    left, right = st.columns(2)
    with left:
        contract_type = st.selectbox(
            "Vertragsart",
            options=["Unbefristet", "Befristet", "Teilzeit", "Freelance"],
            index=0,
            key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, "contract.type"),
        )
        jurisdiction = st.text_input(
            "Jurisdiction",
            value="Deutschland",
            key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, "contract.jurisdiction"),
        )
    with right:
        probation = st.selectbox(
            "Probezeit",
            options=["offen", "3 Monate", "6 Monate"],
            index=0,
            key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, "contract.probation"),
        )
        language = st.selectbox(
            "Sprache",
            options=["de", "en"],
            index=0,
            key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, "contract.language"),
        )
    working_hours = st.text_input(
        "Arbeitszeit / Gehaltshinweis",
        value="",
        placeholder="z. B. 40h/Woche, Gehaltsband aus Intake übernehmen",
        key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, "contract.working_hours"),
    )
    st.caption("Rechtliche Prüfung bleibt erforderlich; das Ergebnis ist nur ein Vorlagenentwurf.")
    _write_artifact_options(
        "employment_contract",
        {
            "contract_type": contract_type,
            "jurisdiction": jurisdiction,
            "probation": probation,
            "language": language,
            "working_hours_salary_note": working_hours,
        },
    )


def _artifact_release_fact_rows(
    vm: SummaryViewModel,
    artifact_id: str,
) -> list[SummaryFactsRow]:
    scoped_areas = SUMMARY_RELEASE_FACT_AREAS_BY_ARTIFACT.get(artifact_id)
    rows: list[SummaryFactsRow] = []
    for row in vm.fact_rows:
        if row.bereich == "Recruiting-Unterlagen":
            continue
        if scoped_areas is not None and row.bereich not in scoped_areas:
            continue
        requirement_stage = str(row.requirement_stage or "").strip()
        if requirement_stage == FactRequirementStage.BEFORE_SUMMARY.value:
            rows.append(row)
        elif (
            artifact_id != "brief"
            and requirement_stage == FactRequirementStage.BEFORE_ARTIFACT.value
        ):
            rows.append(row)
    return rows


def _summary_fact_blocks_release(row: SummaryFactsRow) -> bool:
    resolution_status = str(row.resolution_status or "").strip()
    return (
        row.status in {"Fehlend", "Teilweise"}
        or resolution_status
        in {
            FactResolutionStatus.MISSING.value,
            FactResolutionStatus.CONFLICTED.value,
        }
    )


def _summary_fact_blocker_reason(row: SummaryFactsRow) -> str:
    resolution_status = str(row.resolution_status or "").strip()
    if resolution_status == FactResolutionStatus.CONFLICTED.value:
        return f"Widerspruch prüfen: {row.bereich} · {row.feld}"
    if row.status == "Teilweise":
        return f"Teilweise geklärt: {row.bereich} · {row.feld}"
    return f"Fehlt: {row.bereich} · {row.feld}"


def _summary_fact_blocker_next_step(row: SummaryFactsRow) -> str:
    step_key = row.step_key or SUMMARY_AREA_TO_STEP_KEY.get(row.bereich, "")
    step_label = SUMMARY_FACT_STEP_LABELS.get(step_key, "passenden Wizard-Schritt")
    return f"{row.feld} im Schritt „{step_label}“ prüfen."


def _release_blockers_for_artifact(
    vm: SummaryViewModel,
    *,
    artifact_id: str,
    artifact_label: str,
    limit: int = 4,
) -> list[SummaryReleaseBlocker]:
    blockers: list[SummaryReleaseBlocker] = []
    for row in _artifact_release_fact_rows(vm, artifact_id):
        if not _summary_fact_blocks_release(row):
            continue
        blockers.append(
            SummaryReleaseBlocker(
                artifact_id=artifact_id,
                artifact_label=artifact_label,
                reason=_summary_fact_blocker_reason(row),
                next_step=_summary_fact_blocker_next_step(row),
                blocker_type="fact",
            )
        )
        if len(blockers) >= limit:
            break
    return blockers


def _brief_blocker_for_artifact(
    *,
    artifact_id: str,
    artifact_label: str,
    requirement_ok: bool,
    requirement_message: str,
) -> SummaryReleaseBlocker | None:
    if requirement_ok or not requirement_message:
        return None
    next_step = "Recruiting Brief erstellen oder aktualisieren."
    if "ungültig" in requirement_message.casefold():
        next_step = "Recruiting Brief neu erstellen."
    elif (
        "veraltet" in requirement_message.casefold()
        or "passt nicht" in requirement_message.casefold()
    ):
        next_step = "Recruiting Brief aktualisieren."
    return SummaryReleaseBlocker(
        artifact_id=artifact_id,
        artifact_label=artifact_label,
        reason=requirement_message,
        next_step=next_step,
        blocker_type="brief",
    )


def _stale_result_blocker(
    *,
    artifact_id: str,
    artifact_label: str,
    status_key: str,
) -> SummaryReleaseBlocker | None:
    if status_key != "stale":
        return None
    return SummaryReleaseBlocker(
        artifact_id=artifact_id,
        artifact_label=artifact_label,
        reason=f"{artifact_label} passt nicht mehr zu den aktuellen Eingaben.",
        next_step=f"{artifact_label} neu erstellen.",
        blocker_type="stale_artifact",
    )


def _build_artifact_release_gate(
    vm: SummaryViewModel,
    action: SummaryAction,
    *,
    resolved_brief_model: str,
) -> SummaryArtifactGate:
    artifact_id = _to_canonical_artifact_id(action["id"]) or action["id"]
    artifact_label = _artifact_display_label(artifact_id) or action["title"]
    blockers: list[SummaryReleaseBlocker] = []
    requirements_ok = _has_required_state(action["requires"])
    requirement_ok = True
    requirement_message = ""
    requirement_check_fn = action.get("requirement_check_fn")
    if requirement_check_fn is not None:
        requirement_ok, requirement_message = requirement_check_fn()
    if not requirements_ok:
        blockers.append(
            SummaryReleaseBlocker(
                artifact_id=artifact_id,
                artifact_label=artifact_label,
                reason="Jobspec oder Wizard-Plan fehlt.",
                next_step="Start-Schritt abschließen und Summary erneut öffnen.",
                blocker_type="prerequisite",
            )
        )
    brief_blocker = _brief_blocker_for_artifact(
        artifact_id=artifact_id,
        artifact_label=artifact_label,
        requirement_ok=requirement_ok,
        requirement_message=requirement_message,
    )
    if brief_blocker is not None:
        blockers.append(brief_blocker)
    blockers.extend(
        _release_blockers_for_artifact(
            vm,
            artifact_id=artifact_id,
            artifact_label=artifact_label,
        )
    )

    if artifact_id == "brief":
        state, status_label, cta_label = _get_brief_status(
            primary_action=action,
            resolved_brief_model=resolved_brief_model,
        )
        if state in {"stale", "invalid", "blocked"} and not blockers:
            blockers.append(
                SummaryReleaseBlocker(
                    artifact_id=artifact_id,
                    artifact_label=artifact_label,
                    reason=status_label,
                    next_step=cta_label,
                    blocker_type=state,
                )
            )
    else:
        state, status_label = _artifact_status_label(vm, artifact_id)
        stale_blocker = _stale_result_blocker(
            artifact_id=artifact_id,
            artifact_label=artifact_label,
            status_key=state,
        )
        if stale_blocker is not None:
            blockers.append(stale_blocker)
        if state == "open" and not blockers and action["generator_fn"] is not None:
            state = "ready"
            status_label = _release_state_label(state)

    if blockers:
        state_label = f"{len(blockers)} Blocker"
        next_step = blockers[0].next_step
    else:
        state_label = _release_state_label(state)
        if state in {"current"}:
            next_step = "Kann exportiert oder bei Änderungen aktualisiert werden."
        elif state == "ready":
            next_step = f"{artifact_label} erstellen."
        else:
            next_step = str(status_label or action["cta_label"])
    return SummaryArtifactGate(
        artifact_id=artifact_id,
        artifact_label=artifact_label,
        state=state,
        state_label=state_label,
        blockers=blockers,
        next_step=next_step,
    )


def _build_summary_release_gates(
    vm: SummaryViewModel,
    action_registry: list[SummaryAction],
    *,
    resolved_brief_model: str,
) -> list[SummaryArtifactGate]:
    return [
        _build_artifact_release_gate(
            vm,
            action,
            resolved_brief_model=resolved_brief_model,
        )
        for action in action_registry
    ]


def _release_blocker_count(gates: Sequence[SummaryArtifactGate]) -> int:
    unique_blockers = {
        (blocker.blocker_type, blocker.reason, blocker.next_step)
        for gate in gates
        for blocker in gate.blockers
    }
    return len(unique_blockers)


def _render_artifact_blockers(gate: SummaryArtifactGate) -> None:
    if not gate.blockers:
        st.caption(f"Nächster Schritt: {gate.next_step}")
        return
    for blocker in gate.blockers[:3]:
        st.caption(f"Blocker: {blocker.reason}")
        st.caption(f"To do: {blocker.next_step}")
    remaining = len(gate.blockers) - 3
    if remaining > 0:
        st.caption(f"Weitere {remaining} Blocker im Fakten-Workspace prüfen.")


def _render_summary_artifact_grid(
    *,
    vm: SummaryViewModel,
    generator_by_id: Mapping[str, Callable[[], None]],
    action_registry: list[SummaryAction] | None = None,
    resolved_brief_model: str = "",
) -> None:
    st.markdown("### Recruiting-Unterlagen")
    st.caption(
        "Wähle eine Unterlage, schärfe die wichtigsten Einflussfaktoren und "
        "generiere direkt aus den aktuellen Daten."
    )
    specs: list[dict[str, Any]] = [
        {
            "id": "job_ad",
            "title": "Stellenanzeige",
            "description": "Zielgruppenorientierte Stellenanzeige mit AGG-Check.",
            "controls": lambda: _render_job_ad_compact_controls(vm),
            "cta": "Stellenanzeige erstellen",
        },
        {
            "id": "interview",
            "title": "Interview-Vorbereitungssheet",
            "description": "HR- oder Fachbereich-Sheet mit Fragen und Bewertungslogik.",
            "controls": lambda: _render_interview_compact_controls(vm),
            "cta": "Interview-Sheet erstellen",
        },
        {
            "id": "boolean_search",
            "title": "Suchstrings",
            "description": "Kanal-spezifische Suchstrings für aktive Sourcing-Recherche.",
            "controls": _render_boolean_compact_controls,
            "cta": "Suchstrings erstellen",
        },
        {
            "id": "employment_contract",
            "title": "Arbeitsvertrag",
            "description": "Vorlagenentwurf mit Platzhaltern und Prüfhinweisen.",
            "controls": _render_contract_compact_controls,
            "cta": "Arbeitsvertrag erstellen",
        },
        {
            "id": "reserved_export",
            "title": "Weitere Exportformate",
            "description": "Reserviert für zusätzliche Download-Abläufe.",
        },
        {
            "id": "reserved_templates",
            "title": "Weitere Vorlagen",
            "description": "Reserviert für künftige Hiring-Team-Unterlagen.",
        },
    ]
    action_by_id = {action["id"]: action for action in action_registry or []}
    for row_start in range(0, len(specs), 2):
        columns = st.columns(2, gap="medium")
        for column, spec in zip(columns, specs[row_start : row_start + 2]):
            with column:
                with st.container(border=True):
                    st.markdown(f"**{spec['title']}**")
                    st.caption(str(spec["description"]))
                    if spec["id"].startswith("reserved_"):
                        st.caption("Reservierter Slot")
                        st.button(
                            "Noch nicht aktiv",
                            disabled=True,
                            width="stretch",
                            key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, spec["id"]),
                        )
                        continue
                    artifact_id = str(spec["id"])
                    controls = spec.get("controls")
                    if callable(controls):
                        maybe_artifact_id = controls()
                        if isinstance(maybe_artifact_id, str) and maybe_artifact_id:
                            artifact_id = maybe_artifact_id
                    gate = None
                    action = action_by_id.get(artifact_id)
                    if action is not None:
                        gate = _build_artifact_release_gate(
                            vm,
                            action,
                            resolved_brief_model=resolved_brief_model,
                        )
                    if gate is not None:
                        status_key = gate.state
                        status_label = gate.state_label
                        st.caption(f"Release Gate: {status_label}")
                        _render_artifact_blockers(gate)
                    else:
                        status_key, status_label = _artifact_status_label(
                            vm, artifact_id
                        )
                        st.caption(f"Status: {_release_state_label(status_key)}")
                    button_type = (
                        "primary"
                        if status_key in {"ready", "open", "stale", "missing"}
                        else "secondary"
                    )
                    if st.button(
                        str(spec["cta"]),
                        type=button_type,
                        width="stretch",
                        key=_widget_key(
                            SSKey.SUMMARY_ACTION_WIDGET_PREFIX,
                            f"grid.generate.{spec['id']}",
                        ),
                    ):
                        st.session_state[SSKey.SUMMARY_ACTIVE_ARTIFACT.value] = artifact_id
                        generator = generator_by_id.get(artifact_id)
                        if generator is not None:
                            generator()
                            st.rerun()


def _render_action_card(action: SummaryAction) -> bool:
    has_result = bool(st.session_state.get(action["result_key"].value))
    requirements_ok = _has_required_state(action["requires"])
    requirement_status_ok = True
    requirement_status_message = ""
    requirement_check_fn = action.get("requirement_check_fn")
    if requirement_check_fn is not None:
        requirement_status_ok, requirement_status_message = requirement_check_fn()

    cta_enabled = (
        requirements_ok and requirement_status_ok and action["generator_fn"] is not None
    )
    status_chip = "🟢 aktuell" if has_result else "🟡 offen"

    with st.container(border=True):
        st.markdown(f"**{action['title']}**")
        st.caption(action["benefit"])
        st.caption(f"Status: {status_chip}")

        requirement_label = action["requirement_text"]
        if requirement_status_message:
            requirement_label = f"{requirement_label} — {requirement_status_message}"
        if requirements_ok and requirement_status_ok:
            st.caption(f"Voraussetzung: ✅ {requirement_label}")
        else:
            st.caption(f"Voraussetzung: ⚠️ {requirement_label}")

        input_renderer = action.get("input_renderer")
        if input_renderer is not None:
            st.caption("Vorbereitung im separaten Panel unterhalb der Aktionskarten.")
            open_config_clicked = st.button(
                "Stellenanzeige vorbereiten",
                width="stretch",
                key=_widget_key(
                    SSKey.SUMMARY_ACTION_WIDGET_PREFIX,
                    f"{action['id']}.open_config",
                ),
            )
            if open_config_clicked:
                st.session_state[SSKey.SUMMARY_SHOW_JOB_AD_CONFIG.value] = True
        elif action["input_hints"]:
            st.markdown("**Eingaben**")
            for input_hint in action["input_hints"]:
                st.write(f"- {input_hint}")

        if action["generator_fn"] is None:
            st.button(
                f"{action['cta_label']} (Platzhalter)",
                disabled=True,
                width="stretch",
                key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, action["id"]),
            )
            return False

        triggered = st.button(
            action["cta_label"],
            width="stretch",
            type="primary",
            disabled=not cta_enabled,
            key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, action["id"]),
        )
        blocked_cta_label = action.get("blocked_cta_label")
        if blocked_cta_label and not requirement_status_ok:
            st.button(
                blocked_cta_label,
                width="stretch",
                disabled=True,
                key=_widget_key(
                    SSKey.SUMMARY_ACTION_WIDGET_PREFIX,
                    f"{action['id']}.blocked",
                ),
            )
        if triggered:
            st.session_state[SSKey.SUMMARY_ACTIVE_ARTIFACT.value] = (
                _to_canonical_artifact_id(action["id"])
            )
        return triggered


def _render_job_ad_configuration_panel(*, action_registry: list[SummaryAction]) -> None:
    job_ad_action = next(
        (action for action in action_registry if action["id"] == "job_ad"),
        None,
    )
    input_renderer = job_ad_action.get("input_renderer") if job_ad_action else None
    if input_renderer is None:
        return

    st.markdown("### Stellenanzeige vorbereiten")
    st.caption("Welche Informationen sollen in die Stellenanzeige einfließen?")
    st.toggle(
        "Konfigurationspanel anzeigen",
        key=SSKey.SUMMARY_SHOW_JOB_AD_CONFIG.value,
        help="Blendet Auswahl, Spracheinstellungen und Optimierung für die Stellenanzeige ein oder aus.",
    )
    if not bool(st.session_state.get(SSKey.SUMMARY_SHOW_JOB_AD_CONFIG.value, False)):
        st.caption(
            "Panel ausgeblendet. Nutze „Stellenanzeige vorbereiten“ in der Job-Ad-Karte."
        )
        return

    with st.container(border=True):
        input_renderer()


def _render_primary_brief_card(
    *,
    primary_action: SummaryAction,
    brief_status: tuple[str, str, str],
) -> bool:
    state, status_label, cta_label = brief_status
    cta_enabled = _has_required_state(primary_action["requires"])
    with st.container(border=True):
        st.markdown("### Recruiting Brief")
        st.caption(primary_action["benefit"])
        badge = {
            "current": "🟢 aktuell",
            "stale": "🟠 veraltet",
            "missing": "🟡 fehlt",
            "invalid": "🟠 ungültig",
            "blocked": "⚪ blockiert",
        }.get(state, "🟡 offen")
        st.caption(f"Status: {badge} · {status_label}")
        triggered = st.button(
            cta_label,
            width="stretch",
            type="primary",
            disabled=not cta_enabled or primary_action["generator_fn"] is None,
            key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, primary_action["id"]),
        )
        if triggered:
            st.session_state[SSKey.SUMMARY_ACTIVE_ARTIFACT.value] = (
                _to_canonical_artifact_id(primary_action["id"])
            )
        return triggered


def _render_follow_up_cards(
    *,
    follow_up_actions: list[SummaryAction],
) -> tuple[bool, SummaryAction | None]:
    st.markdown("### Weitere Recruiting-Unterlagen")
    st.caption(
        "Nachgelagerte Unterlagen bauen auf einem aktuellen Recruiting Brief auf."
    )
    card_columns = st.columns(2)
    for index, action in enumerate(follow_up_actions):
        with card_columns[index % 2]:
            triggered = _render_action_card(action)
            if triggered:
                return True, action
    return False, None


def _render_export_bar(*, has_brief: bool) -> None:
    st.markdown("### Export")
    with st.container(border=True):
        st.caption(
            "Exportfreigabe im Bereich **Brief & Export**: erst prüfen, dann JSON, "
            "Markdown, DOCX oder ESCO-Mapping herunterladen."
        )
        if has_brief:
            st.success(
                "Bereit zur Prüfung: Ein gültiger Recruiting Brief ist vorhanden. "
                "Exportieren Sie nur, wenn die Release Gate Karten keine Blocker zeigen."
            )
        else:
            st.info(
                "Blockiert: Erstellen Sie zuerst den Recruiting Brief. Danach werden "
                "Exportformate freigegeben."
            )


def _render_summary_dashboard_css() -> None:
    render_static_html(
        """
        <style>
        .cs-summary-pipeline {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.65rem;
        }
        .cs-summary-pipeline-item {
            border: 1px solid var(--cs-border);
            border-radius: 8px;
            padding: 0.72rem 0.75rem;
            background: var(--cs-surface);
            min-height: 4.6rem;
            box-shadow: var(--cs-shadow-sm);
        }
        .cs-summary-pipeline-item strong {
            display: block;
            overflow-wrap: anywhere;
            font-size: 0.9rem;
            line-height: 1.24;
            color: var(--cs-text);
        }
        .cs-summary-pipeline-item span {
            display: inline-flex;
            margin-top: 0.35rem;
            border-radius: 999px;
            padding: 0.16rem 0.46rem;
            font-size: 0.76rem;
            font-weight: 700;
            line-height: 1.2;
        }
        .cs-summary-pipeline-item[data-status="current"] span {
            background: var(--cs-success-soft);
            color: var(--cs-text);
            border: 1px solid var(--cs-success);
        }
        .cs-summary-pipeline-item[data-status="ready"] span {
            background: var(--cs-primary-soft);
            color: var(--cs-text);
            border: 1px solid var(--cs-primary);
        }
        .cs-summary-pipeline-item[data-status="blocked"] span {
            background: var(--cs-warning-soft);
            color: var(--cs-text);
            border: 1px solid var(--cs-warning);
        }
        .cs-summary-pipeline-item[data-status="stale"] span {
            background: var(--cs-warning-soft);
            color: var(--cs-text);
            border: 1px solid var(--cs-warning);
        }
        .cs-summary-pipeline-item[data-status="open"] span {
            background: var(--cs-surface-muted);
            color: var(--cs-text-muted);
            border: 1px solid var(--cs-border);
        }
        .cs-summary-section-note {
            color: var(--cs-text-subtle);
            margin: -0.1rem 0 0.9rem 0;
            font-size: 0.9rem;
            line-height: 1.45;
        }
        .cs-summary-section-note + [data-testid="stVerticalBlockBorderWrapper"] {
            margin-top: 0.35rem;
        }
        @media (max-width: 900px) {
            .cs-summary-pipeline {
                grid-template-columns: minmax(0, 1fr);
            }
        }
        </style>
        """,
        streamlit_module=st,
    )


def _render_artifact_pipeline(
    action_registry: list[SummaryAction],
    *,
    resolved_brief_model: str,
    vm: SummaryViewModel | None = None,
) -> None:
    st.markdown("#### Unterlagen-Pipeline")
    st.caption("Release-Status je Unterlage: bereit, offen oder durch konkrete Punkte blockiert.")
    card_columns = st.columns(2)
    for index, action in enumerate(action_registry):
        gate = (
            _build_artifact_release_gate(
                vm,
                action,
                resolved_brief_model=resolved_brief_model,
            )
            if vm is not None
            else None
        )
        if gate is not None:
            status_key, status_label = gate.state, gate.state_label
        else:
            status_key, status_label = _artifact_pipeline_status(
                action,
                resolved_brief_model=resolved_brief_model,
            )
        requirements_ok = _has_required_state(action["requires"])
        requirement_ok = True
        requirement_message = ""
        requirement_check_fn = action.get("requirement_check_fn")
        if requirement_check_fn is not None:
            requirement_ok, requirement_message = requirement_check_fn()

        cta_label = action["cta_label"]
        if action["id"] == "brief":
            _, _, cta_label = _get_brief_status(
                primary_action=action, resolved_brief_model=resolved_brief_model
            )
        if not (requirements_ok and requirement_ok) and action.get("blocked_cta_label"):
            cta_label = str(action["blocked_cta_label"])

        with card_columns[index % 2]:
            with st.container(border=True):
                st.markdown(f"**{action['title']}**")
                st.caption(action["benefit"])
                st.caption(f"Release Gate: {status_label}")
                requirement_text = action["requirement_text"]
                if requirement_message:
                    requirement_text = f"{requirement_text} — {requirement_message}"
                st.caption(f"Voraussetzungen: {requirement_text}")
                if gate is not None:
                    _render_artifact_blockers(gate)
                if st.button(
                    cta_label,
                    width="stretch",
                    key=_widget_key(
                        SSKey.SUMMARY_ACTION_WIDGET_PREFIX,
                        f"readiness.pipeline.{action['id']}",
                    ),
                    disabled=(
                        not (requirements_ok and requirement_ok)
                        or action["generator_fn"] is None
                    ),
                ):
                    st.session_state[SSKey.SUMMARY_ACTIVE_ARTIFACT.value] = (
                        _to_canonical_artifact_id(action["id"])
                    )
                    if action["generator_fn"] is not None:
                        action["generator_fn"]()
                    st.rerun()


def _render_summary_readiness_metrics(vm: SummaryViewModel) -> None:
    _render_summary_readiness_metrics_impl(vm, streamlit_module=st)


def _render_readiness_tab(
    *,
    vm: SummaryViewModel,
    action_registry: list[SummaryAction],
    resolved_brief_model: str,
    brief: VacancyBrief | None = None,
) -> None:
    _render_summary_dashboard_css()
    release_gates = _build_summary_release_gates(
        vm,
        action_registry,
        resolved_brief_model=resolved_brief_model,
    )
    release_blocker_count = _release_blocker_count(release_gates)
    summary_copy = build_step_copy(
        STEP_KEY_SUMMARY,
        language=active_language(),
        context=VacancyCopyContext(
            role_title=vm.meta.role_label,
            company_name=vm.meta.company_label,
            location=vm.meta.country_label,
            readiness_score=vm.status.readiness_percent,
            critical_gaps_count=release_blocker_count,
        )
    )
    render_output_header(summary_copy.headline, summary_copy.subheadline)
    _render_readiness_dashboard_header(vm, blocker_count=release_blocker_count)

    recommendation = _resolve_next_best_action_recommendation(
        action_registry, resolved_brief_model=resolved_brief_model, vm=vm
    )
    _render_critical_gaps_card(vm)
    action_col, pipeline_col = st.columns([1.12, 0.88], gap="large")
    with action_col:
        _render_next_best_action_card(recommendation=recommendation)
    with pipeline_col:
        _render_artifact_pipeline(
            action_registry,
            resolved_brief_model=resolved_brief_model,
            vm=vm,
        )
    _render_summary_workspace_tabs(
        vm=vm,
        action_registry=action_registry,
        resolved_brief_model=resolved_brief_model,
        brief=brief,
    )


def _render_readiness_dashboard_header(
    vm: SummaryViewModel, *, blocker_count: int | None = None
) -> None:
    _render_readiness_dashboard_header_impl(
        vm,
        metric_renderer=_render_summary_readiness_metrics,
        blocker_count=blocker_count,
        streamlit_module=st,
    )


def _render_next_best_action_card(*, recommendation: NextBestActionRecommendation | None) -> None:
    if recommendation is None:
        st.info("Aktuell ist kein nächster Schritt verfügbar.")
        return
    next_action = recommendation.action
    requirements_ok = _has_required_state(next_action["requires"])
    requirement_status_ok = True
    requirement_status_message = ""
    requirement_check_fn = next_action.get("requirement_check_fn")
    if requirement_check_fn is not None:
        requirement_status_ok, requirement_status_message = requirement_check_fn()
    cta_enabled = (
        requirements_ok and requirement_status_ok and next_action["generator_fn"] is not None
    )
    render_next_best_action(
        next_action["title"],
        recommendation.reason,
        f"Aktion: {recommendation.cta_label}",
    )
    requirement_label = next_action["requirement_text"]
    if requirement_status_message:
        requirement_label = f"{requirement_label} — {requirement_status_message}"
    st.caption(
        f"Voraussetzung: {'✅' if (requirements_ok and requirement_status_ok) else '⚠️'} {requirement_label}"
    )
    if st.button(
        f"Aktion: {recommendation.cta_label}",
        type="primary",
        width="stretch",
        key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, "readiness.next_action"),
        disabled=not cta_enabled,
    ):
        st.session_state[SSKey.SUMMARY_ACTIVE_ARTIFACT.value] = _to_canonical_artifact_id(
            next_action["id"]
        )
        if next_action["generator_fn"] is not None:
            next_action["generator_fn"]()
        st.rerun()


def _render_critical_gaps_card(vm: SummaryViewModel) -> None:
    missing_items = _build_missing_critical_items(vm)
    if not missing_items:
        st.success(
            "Keine kritischen Fakten-Blocker erkannt. Prüfen Sie jetzt die "
            "Unterlagenkarten."
        )
        return
    render_critical_gaps(missing_items, title="Fakten-Blocker vor Export (Top 5)")


def _render_artifact_launcher_cards(
    *, action_registry: list[SummaryAction], resolved_brief_model: str
) -> None:
    st.markdown("#### Recruiting-Unterlagen starten")
    for action in action_registry:
        requirements_ok = _has_required_state(action["requires"])
        requirement_ok = True
        requirement_message = ""
        requirement_check_fn = action.get("requirement_check_fn")
        if requirement_check_fn is not None:
            requirement_ok, requirement_message = requirement_check_fn()
        has_result = bool(st.session_state.get(action["result_key"].value))
        status_label = "Aktuell" if has_result else "Offen"
        prerequisites_label = "Erfüllt" if (requirements_ok and requirement_ok) else "Offen"
        with st.container(border=True):
            st.markdown(f"**{action['title']}**")
            st.caption(action["benefit"])
            st.caption(f"Status: {status_label} · Voraussetzungen: {prerequisites_label}")
            requirement_text = action["requirement_text"]
            if requirement_message:
                requirement_text = f"{requirement_text} — {requirement_message}"
            st.caption(f"Voraussetzungen: {requirement_text}")
            if action["id"] == "brief":
                _, _, cta_label = _get_brief_status(
                    primary_action=action, resolved_brief_model=resolved_brief_model
                )
            else:
                cta_label = action["cta_label"]
            if not (requirements_ok and requirement_ok) and action.get("blocked_cta_label"):
                cta_label = str(action["blocked_cta_label"])
            if st.button(
                cta_label,
                width="stretch",
                key=_widget_key(
                    SSKey.SUMMARY_ACTION_WIDGET_PREFIX, f"readiness.launcher.{action['id']}"
                ),
                disabled=(
                    not (requirements_ok and requirement_ok) or action["generator_fn"] is None
                ),
            ):
                st.session_state[SSKey.SUMMARY_ACTIVE_ARTIFACT.value] = _to_canonical_artifact_id(
                    action["id"]
                )
                if action["generator_fn"] is not None:
                    action["generator_fn"]()
                st.rerun()


def _build_summary_tabs() -> SummaryTabs:
    tab_labels = ["Brief", "Fakten", "Export", "Technik"]
    if hasattr(st, "tabs"):
        tabs = st.tabs(tab_labels)
        if len(tabs) == 4:
            return tabs[0], tabs[1], tabs[2], tabs[3]
    if hasattr(st, "container"):
        return (
            st.container(),
            st.container(),
            st.container(),
            st.container(),
        )
    return (
        nullcontext(),
        nullcontext(),
        nullcontext(),
        nullcontext(),
    )


def _render_summary_workspace_tabs(
    *,
    vm: SummaryViewModel,
    action_registry: list[SummaryAction],
    resolved_brief_model: str,
    brief: VacancyBrief | None,
) -> None:
    st.markdown("### Arbeitsbereiche")
    render_static_html(
        '<p class="cs-summary-section-note">'
        "Details sind nach Aufgabe getrennt, damit Fakten und Exporte nicht doppelt erscheinen."
        "</p>",
        streamlit_module=st,
    )
    brief_tab, facts_tab, export_tab, advanced_tab = _build_summary_tabs()

    with brief_tab:
        if brief is None:
            st.info("Noch kein gültiger Recruiting Brief verfügbar.")
        else:
            render_output_header(
                "Recruiting Brief",
                "Kompakte Vorschau ohne Export-JSON. Downloads liegen im Export-Arbeitsbereich.",
            )
            render_brief(
                brief,
                structured_data_payload=_build_brief_structured_preview_payload(brief),
                show_title=False,
                show_structured_data=False,
            )

    with facts_tab:
        _render_summary_facts_section(vm)

    with export_tab:
        if brief is None:
            st.info(
                "Export blockiert: Erstellen oder aktualisieren Sie zuerst den Recruiting Brief."
            )
        else:
            _render_summary_export_workspace(brief=brief)

    with advanced_tab:
        st.subheader("Technik")
        st.caption("Technische Vorschauen und Statusdaten bleiben hier gebündelt.")
        if brief is not None:
            with st.expander("Strukturierte Exportvorschau", expanded=False):
                st.json(_build_brief_structured_preview_payload(brief), expanded=False)
        with st.expander("Unterlagenstatus", expanded=False):
            st.dataframe(
                _build_artifact_status_rows(action_registry=action_registry),
                width="stretch",
                hide_index=True,
                column_config={
                    "Unterlage": st.column_config.TextColumn("Dokument"),
                    "Status": st.column_config.TextColumn("Status"),
                    "Voraussetzungen": st.column_config.TextColumn("Voraussetzungen"),
                },
            )
        with st.expander("Anreicherungs-Laufzeiten", expanded=False):
            timing_rows = _build_enrichment_timing_rows(st.session_state)
            if timing_rows:
                st.dataframe(
                    timing_rows,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "Stage": st.column_config.TextColumn("Schritt"),
                        "Pfad": st.column_config.TextColumn("Pfad"),
                        "Status": st.column_config.TextColumn("Status"),
                        "Dauer (ms)": st.column_config.NumberColumn("Dauer (ms)"),
                        "Cache": st.column_config.CheckboxColumn("Aus Cache"),
                        "Fragment": st.column_config.CheckboxColumn("Fragment"),
                        "Treffer": st.column_config.NumberColumn("Treffer"),
                    },
                )
            else:
                st.info("Noch keine Timing-Daten für Enrichment-Pfade verfügbar.")


def _render_summary_processing_hub(
    *,
    action_registry: list[SummaryAction],
    resolved_brief_model: str,
    show_job_ad_configuration_panel: bool = True,
    show_export_bar: bool = True,
) -> None:
    render_output_header(
        "Processing Hub",
        "Primärer Pfad kompakt: Recruiting Brief → weitere Recruiting-Unterlagen → Export.",
    )

    primary_action = next(
        (action for action in action_registry if action["id"] == "brief"),
        action_registry[0],
    )
    follow_up_actions = [
        action for action in action_registry if action["id"] != "brief"
    ]
    brief_status = _get_brief_status(
        primary_action=primary_action,
        resolved_brief_model=resolved_brief_model,
    )
    brief_state, brief_status_label, brief_cta_label = brief_status
    header_badge = {
        "current": "🟢 aktuell",
        "stale": "🟠 veraltet",
        "missing": "🟡 fehlt",
        "invalid": "🟠 ungültig",
        "blocked": "⚪ blockiert",
    }.get(brief_state, "🟡 offen")
    st.markdown(
        (
            f"**Pipeline:** `Recruiting Brief` → `HR-Sheet/Fachbereich-Sheet` → "
            f"`Suchstrings` → `Arbeitsvertrag` → `Export`  \n"
            f"Status Recruiting Brief: {header_badge} · {brief_status_label}"
        )
    )

    st.markdown("#### Unterlagenübersicht")
    header_columns = st.columns([2.1, 1.1, 1.2, 2.0], gap="small")
    header_columns[0].markdown("**Unterlage**")
    header_columns[1].markdown("**Status**")
    header_columns[2].markdown("**Voraussetzungen**")
    header_columns[3].markdown("**Primäre Aktion**")

    for action in [primary_action, *follow_up_actions]:
        has_result = bool(st.session_state.get(action["result_key"].value))
        requirements_ok = _has_required_state(action["requires"])
        requirement_ok = True
        requirement_message = ""
        requirement_check_fn = action.get("requirement_check_fn")
        if requirement_check_fn is not None:
            requirement_ok, requirement_message = requirement_check_fn()

        effective_requirements_ok = requirements_ok and requirement_ok
        cta_label = brief_cta_label if action["id"] == "brief" else action["cta_label"]
        if not effective_requirements_ok and action.get("blocked_cta_label"):
            cta_label = str(action["blocked_cta_label"])

        row_columns = st.columns([2.1, 1.1, 1.2, 2.0], gap="small")
        row_columns[0].write(action["title"])
        row_columns[1].write("🟢 Aktuell" if has_result else "🟡 Offen")
        row_columns[2].write("✅ Erfüllt" if effective_requirements_ok else "⚠️ Offen")

        with row_columns[3]:
            triggered = st.button(
                cta_label,
                width="stretch",
                type="primary" if action["id"] == "brief" else "secondary",
                disabled=(
                    not effective_requirements_ok or action["generator_fn"] is None
                ),
                key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, action["id"]),
            )
            if triggered and action["generator_fn"] is not None:
                st.session_state[SSKey.SUMMARY_ACTIVE_ARTIFACT.value] = (
                    _to_canonical_artifact_id(action["id"])
                )
                action["generator_fn"]()
                st.rerun()

        detail_suffix = " (Recruiting Brief)" if action["id"] == "brief" else ""
        with st.expander(f"Details: {action['title']}{detail_suffix}", expanded=False):
            st.caption(action["benefit"])
            requirement_label = action["requirement_text"]
            if requirement_message:
                requirement_label = f"{requirement_label} — {requirement_message}"
            st.write(
                f"**Voraussetzungen:** {'✅' if effective_requirements_ok else '⚠️'} {requirement_label}"
            )
            if action.get("input_renderer") is not None:
                if st.button(
                    "Stellenanzeige vorbereiten",
                    width="content",
                    key=_widget_key(
                        SSKey.SUMMARY_ACTION_WIDGET_PREFIX,
                        f"{action['id']}.open_config",
                    ),
                ):
                    st.session_state[SSKey.SUMMARY_SHOW_JOB_AD_CONFIG.value] = True
            elif action["input_hints"]:
                st.markdown("**Eingaben**")
                for input_hint in action["input_hints"]:
                    st.write(f"- {input_hint}")

    if show_job_ad_configuration_panel:
        _render_job_ad_configuration_panel(action_registry=action_registry)

    if show_export_bar:
        _render_export_bar(has_brief=brief_state == "current")


def _is_warning_checklist_item(item: str) -> bool:
    normalized = item.strip().lower()
    if not normalized:
        return False
    warning_tokens = ("fehlt", "nicht", "missing", "kritisch")
    return any(token in normalized for token in warning_tokens)


def _render_agg_checklist_review(items: Sequence[str]) -> None:
    if not items:
        st.caption("Keine AGG-Checkliste hinterlegt.")
        return
    for raw_item in items:
        item = str(raw_item).strip()
        if not item:
            continue
        if _is_warning_checklist_item(item):
            render_pill(item, tone="warning")
        else:
            render_pill(item, tone="neutral")


def _render_job_ad_artifact(custom_job_ad_raw: dict[str, Any]) -> None:
    custom_job_ad = JobAdGenerationResult.model_validate(
        {
            "headline": custom_job_ad_raw.get("headline", ""),
            "target_group": custom_job_ad_raw.get("target_group", []),
            "agg_checklist": custom_job_ad_raw.get("agg_checklist", []),
            "job_ad_text": custom_job_ad_raw.get("job_ad_text", ""),
            "intro": custom_job_ad_raw.get("intro", ""),
            "responsibilities": custom_job_ad_raw.get("responsibilities", []),
            "profile": custom_job_ad_raw.get("profile", []),
            "offer": custom_job_ad_raw.get("offer", []),
            "cta": custom_job_ad_raw.get("cta", ""),
            "equal_opportunity_note": custom_job_ad_raw.get(
                "equal_opportunity_note", ""
            ),
        }
    )
    publishable_markdown = _build_publishable_job_ad_markdown(custom_job_ad)
    logo_payload = _job_ad_logo_payload(custom_job_ad_raw)
    preview_options_raw = custom_job_ad_raw.get("preview_options")
    preview_options = (
        preview_options_raw if isinstance(preview_options_raw, Mapping) else {}
    )
    shell_options = _job_ad_preview_shell_options(preview_options)
    render_output_header(
        custom_job_ad.headline or "Stellenanzeige",
        "Generierte Stellenanzeige mit Zielgruppen- und AGG-Hinweisen.",
    )
    render_card_start("cs-card cs-result-card")
    st.markdown("### Ergebnis")
    render_static_html(
        document_preview_shell(
            _job_ad_preview_html(custom_job_ad, logo_payload=logo_payload),
            title="Stellenanzeige",
            fit_pages=True,
            **shell_options,
        ),
        streamlit_module=st,
    )
    render_static_html("</section>", streamlit_module=st)

    render_card_start("cs-card cs-result-card")
    st.markdown("### Prüfung")
    st.markdown("**Zielgruppe**")
    if custom_job_ad.target_group:
        for index, group in enumerate(custom_job_ad.target_group):
            render_pill(group, tone="primary" if index == 0 else "neutral")
    else:
        st.caption("Keine Zielgruppe hinterlegt.")
    st.markdown("**AGG-Checkliste**")
    _render_agg_checklist_review(custom_job_ad.agg_checklist)
    critical_gaps_raw = custom_job_ad_raw.get("critical_gaps")
    critical_gaps: list[str] = []
    if isinstance(critical_gaps_raw, list):
        critical_gaps.extend(str(note).strip() for note in critical_gaps_raw if str(note).strip())
    generation_notes = custom_job_ad_raw.get("generation_notes", [])
    if isinstance(generation_notes, list):
        critical_gaps.extend(str(note).strip() for note in generation_notes if str(note).strip())
    critical_gaps = _dedupe_preserve_order(critical_gaps)
    if critical_gaps:
        render_critical_gaps(critical_gaps, title="Kritische Lücken")
    render_static_html("</section>", streamlit_module=st)

    render_card_start("cs-card cs-result-card")
    st.markdown("### Export")
    custom_docx = _job_ad_to_docx_bytes(custom_job_ad, logo_payload=logo_payload)
    custom_pdf = _job_ad_to_pdf_bytes(custom_job_ad, logo_payload=logo_payload)
    custom_md = publishable_markdown.encode("utf-8")
    export_columns = st.columns(2)
    with export_columns[0]:
        st.download_button(
            "Stellenanzeige herunterladen (DOCX)",
            data=custom_docx,
            file_name="stellenanzeige.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    with export_columns[1]:
        if custom_pdf is None:
            st.caption("PDF-Export benötigt reportlab (nicht verfügbar).")
        else:
            st.download_button(
                "Stellenanzeige herunterladen (PDF)",
                data=custom_pdf,
                file_name="stellenanzeige.pdf",
                mime="application/pdf",
            )
    with export_columns[0]:
        st.download_button(
            "Stellenanzeige herunterladen (Markdown)",
            data=custom_md,
            file_name="stellenanzeige.md",
            mime="text/markdown",
        )
    render_static_html("</section>", streamlit_module=st)


def _render_active_artifact(*, artifact_id: str, brief: VacancyBrief) -> None:
    if artifact_id == "brief":
        render_card_start("cs-card cs-result-card")
        render_brief(
            brief,
            structured_data_payload=_build_brief_structured_preview_payload(brief),
        )
        render_static_html("</section>", streamlit_module=st)
        return

    if artifact_id == "job_ad":
        custom_job_ad_raw = st.session_state.get(SSKey.JOB_AD_DRAFT_CUSTOM.value)
        if not isinstance(custom_job_ad_raw, dict):
            st.info("Für diese Unterlage liegt noch kein Ergebnis vor.")
            return
        _render_job_ad_artifact(custom_job_ad_raw)
        return

    if artifact_id == "interview_hr":
        payload = st.session_state.get(SSKey.INTERVIEW_PREP_HR.value)
        if isinstance(payload, dict):
            sheet = InterviewPrepSheetHR.model_validate(payload)
            render_interview_prep_hr(sheet)
            hr_json_bytes = json.dumps(
                sheet.model_dump(mode="json"), indent=2, ensure_ascii=False
            ).encode("utf-8")
            hr_docx_bytes = _interview_prep_hr_to_docx_bytes(sheet)
            x1, x2 = st.columns(2)
            with x1:
                st.download_button(
                    "HR-Sheet herunterladen (JSON)",
                    data=hr_json_bytes,
                    file_name="interview_sheet_hr.json",
                    mime="application/json",
                )
            with x2:
                st.download_button(
                    "HR-Sheet herunterladen (DOCX)",
                    data=hr_docx_bytes,
                    file_name="interview_sheet_hr.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
        else:
            st.info("Für diese Unterlage liegt noch kein Ergebnis vor.")
        return

    if artifact_id == "interview_fach":
        payload = st.session_state.get(SSKey.INTERVIEW_PREP_FACH.value)
        if isinstance(payload, dict):
            sheet = InterviewPrepSheetHiringManager.model_validate(payload)
            render_interview_prep_fach(sheet)
            fach_json_bytes = json.dumps(
                sheet.model_dump(mode="json"), indent=2, ensure_ascii=False
            ).encode("utf-8")
            logo_payload = _read_logo_payload()
            styleguide = str(st.session_state.get(SSKey.SUMMARY_STYLEGUIDE_TEXT.value, ""))
            fach_docx_bytes = _interview_prep_fach_to_docx_bytes(
                sheet,
                logo_payload=logo_payload,
                styleguide=styleguide,
            )
            fach_pdf_bytes = _interview_prep_fach_to_pdf_bytes(
                sheet,
                logo_payload=logo_payload,
                styleguide=styleguide,
            )
            download_columns = st.columns(2)
            with download_columns[0]:
                st.download_button(
                    "Fachbereich-Sheet herunterladen (JSON)",
                    data=fach_json_bytes,
                    file_name="interview_sheet_fachbereich.json",
                    mime="application/json",
                )
            with download_columns[1]:
                st.download_button(
                    "Fachbereich-Sheet herunterladen (DOCX)",
                    data=fach_docx_bytes,
                    file_name="interview_sheet_fachbereich.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            with download_columns[0]:
                if fach_pdf_bytes is None:
                    st.caption("PDF-Export benötigt reportlab (nicht verfügbar).")
                else:
                    st.download_button(
                        "Fachbereich-Sheet herunterladen (PDF)",
                        data=fach_pdf_bytes,
                        file_name="interview_sheet_fachbereich.pdf",
                        mime="application/pdf",
                    )
        else:
            st.info("Für diese Unterlage liegt noch kein Ergebnis vor.")
        return

    if artifact_id == "boolean_search":
        payload = st.session_state.get(SSKey.BOOLEAN_SEARCH_STRING.value)
        if isinstance(payload, dict):
            boolean_pack = BooleanSearchPack.model_validate(payload)
            render_boolean_search_pack(boolean_pack)
        else:
            st.info("Für diese Unterlage liegt noch kein Ergebnis vor.")
        return

    if artifact_id == "employment_contract":
        payload = st.session_state.get(SSKey.EMPLOYMENT_CONTRACT_DRAFT.value)
        if isinstance(payload, dict):
            contract = EmploymentContractDraft.model_validate(payload)
            render_employment_contract_draft(contract)
            contract_json_bytes = json.dumps(
                contract.model_dump(mode="json"), indent=2, ensure_ascii=False
            ).encode("utf-8")
            contract_docx_bytes = _employment_contract_to_docx_bytes(contract)
            x1, x2 = st.columns(2)
            with x1:
                st.download_button(
                    "Arbeitsvertrag herunterladen (JSON)",
                    data=contract_json_bytes,
                    file_name="employment_contract_draft.json",
                    mime="application/json",
                )
            with x2:
                st.download_button(
                    "Arbeitsvertrag herunterladen (DOCX)",
                    data=contract_docx_bytes,
                    file_name="employment_contract_draft.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
        else:
            st.info("Für diese Unterlage liegt noch kein Ergebnis vor.")


def _generated_summary_artifact_ids() -> list[str]:
    ordered_ids = [
        "job_ad",
        "interview_hr",
        "interview_fach",
        "boolean_search",
        "employment_contract",
    ]
    return [artifact_id for artifact_id in ordered_ids if _artifact_has_result(artifact_id)]


def _resolve_output_artifact_id(
    *,
    available_artifact_ids: list[str],
    generator_by_id: Mapping[str, Callable[[], None]],
) -> str:
    active_raw = st.session_state.get(SSKey.SUMMARY_ACTIVE_ARTIFACT.value, "")
    active_id = _to_canonical_artifact_id(active_raw)
    if active_id == "brief":
        active_id = ""
    if active_id in available_artifact_ids or active_id in generator_by_id:
        return active_id
    if available_artifact_ids:
        return available_artifact_ids[0]
    return "job_ad"


def _render_artifact_result_switcher(
    *, active_artifact_id: str, available_artifact_ids: list[str]
) -> None:
    if len(available_artifact_ids) <= 1:
        return
    st.caption("Vorhandene Ergebnisse")
    columns = st.columns(min(len(available_artifact_ids), 2), gap="small")
    for index, artifact_id in enumerate(available_artifact_ids):
        with columns[index % len(columns)]:
            if st.button(
                _artifact_display_label(artifact_id),
                width="stretch",
                type="primary" if artifact_id == active_artifact_id else "secondary",
                key=_widget_key(
                    SSKey.SUMMARY_ACTION_WIDGET_PREFIX,
                    f"output.switch.{artifact_id}",
                ),
            ):
                st.session_state[SSKey.SUMMARY_ACTIVE_ARTIFACT.value] = artifact_id
                st.rerun()


def _render_artifact_refinement_box(
    *,
    vm: SummaryViewModel,
    artifact_id: str,
    generator_by_id: Mapping[str, Callable[[], None]],
    heading: str = "### Anpassungswünsche",
) -> None:
    st.markdown(heading)
    current_value = _read_artifact_change_request(artifact_id)
    generator = generator_by_id.get(artifact_id)
    with st.form(
        _widget_key(
            SSKey.SUMMARY_ACTION_WIDGET_PREFIX,
            f"refinement.form.{artifact_id}",
        ),
        clear_on_submit=False,
    ):
        request_value = st.text_area(
            "Was soll am Ergebnis angepasst werden?",
            value=current_value,
            placeholder="z. B. kürzer, stärker auf Senior-Profile, mehr Interviewfragen zu Stakeholder-Management …",
            key=_widget_key(
                SSKey.SUMMARY_ACTION_WIDGET_PREFIX,
                f"refinement.{artifact_id}",
            ),
            height=110,
        )
        submitted = st.form_submit_button(
            "Anpassungen übernehmen",
            width="stretch",
            type="primary",
            disabled=generator is None,
        )
    if submitted:
        _write_artifact_change_request(artifact_id, request_value)
        if generator is not None:
            st.session_state[SSKey.SUMMARY_ACTIVE_ARTIFACT.value] = artifact_id
            generator()
            _mark_artifact_current(vm, artifact_id)
            st.rerun()


def _current_boolean_search_pack() -> BooleanSearchPack | None:
    payload = st.session_state.get(SSKey.BOOLEAN_SEARCH_STRING.value)
    if not isinstance(payload, dict):
        return None
    try:
        return BooleanSearchPack.model_validate(payload)
    except Exception:
        return None


def _render_boolean_artifact_context_panels(
    *,
    vm: SummaryViewModel,
    generator_by_id: Mapping[str, Callable[[], None]],
) -> bool:
    boolean_pack = _current_boolean_search_pack()
    if boolean_pack is None:
        return False

    columns = st.columns(2)
    panels = (
        lambda: render_boolean_supporting_terms(boolean_pack),
        lambda: render_boolean_usage_notes(boolean_pack),
        lambda: render_boolean_risks(boolean_pack),
        lambda: _render_artifact_refinement_box(
            vm=vm,
            artifact_id="boolean_search",
            generator_by_id=generator_by_id,
            heading="### Anpassungswünsche",
        ),
    )
    for index, render_panel in enumerate(panels):
        with columns[index % len(columns)]:
            render_panel()
    return True


def _render_summary_output_workspace(
    *,
    vm: SummaryViewModel,
    brief: VacancyBrief,
    generator_by_id: Mapping[str, Callable[[], None]],
) -> None:
    st.markdown("### Ergebnis")
    available_artifact_ids = _generated_summary_artifact_ids()
    active_artifact_id = _resolve_output_artifact_id(
        available_artifact_ids=available_artifact_ids,
        generator_by_id=generator_by_id,
    )
    st.session_state[SSKey.SUMMARY_ACTIVE_ARTIFACT.value] = active_artifact_id
    _render_artifact_result_switcher(
        active_artifact_id=active_artifact_id,
        available_artifact_ids=available_artifact_ids,
    )
    status_key, status_label = _artifact_status_label(vm, active_artifact_id)
    render_output_header(
        _artifact_display_label(active_artifact_id),
        f"Status: {status_label}",
    )
    if status_key == "stale":
        st.warning("Dieses Ergebnis basiert auf älteren Fakten oder Optionen. Bitte neu generieren.")
    if active_artifact_id in available_artifact_ids:
        _render_active_artifact(artifact_id=active_artifact_id, brief=brief)
    else:
        st.info("Für diese Unterlage liegt noch kein Ergebnis vor.")
    if active_artifact_id == "boolean_search":
        rendered_context = _render_boolean_artifact_context_panels(
            vm=vm,
            generator_by_id=generator_by_id,
        )
        if rendered_context:
            return
    _render_artifact_refinement_box(
        vm=vm,
        artifact_id=active_artifact_id,
        generator_by_id=generator_by_id,
    )


def _render_secondary_artifacts(
    *, active_artifact_id: str, available_artifact_ids: list[str]
) -> None:
    secondary_priority = [
        "interview_hr",
        "interview_fach",
        "boolean_search",
        "employment_contract",
        "brief",
    ]
    priority_rank = {artifact_id: index for index, artifact_id in enumerate(secondary_priority)}
    secondary_ids = [
        artifact_id
        for artifact_id in available_artifact_ids
        if artifact_id != active_artifact_id
    ]
    secondary_ids = [
        artifact_id
        for _, artifact_id in sorted(
            enumerate(secondary_ids),
            key=lambda item: (
                priority_rank.get(item[1], len(priority_rank)),
                item[0],
            ),
        )
    ]
    if not secondary_ids:
        return
    st.caption("Weitere Ergebnisse")
    for artifact_id in secondary_ids:
        if st.button(
            f"Als Fokus öffnen: {_artifact_display_label(artifact_id)}",
            key=_widget_key(
                SSKey.SUMMARY_ACTION_WIDGET_PREFIX, f"activate.{artifact_id}"
            ),
            width="stretch",
        ):
            st.session_state[SSKey.SUMMARY_ACTIVE_ARTIFACT.value] = artifact_id
            st.rerun()


def _render_summary_results_workspace(*, brief: VacancyBrief) -> None:
    available_artifact_ids: list[str] = []
    if isinstance(st.session_state.get(SSKey.JOB_AD_DRAFT_CUSTOM.value), dict):
        available_artifact_ids.append("job_ad")
    if isinstance(st.session_state.get(SSKey.INTERVIEW_PREP_HR.value), dict):
        available_artifact_ids.append("interview_hr")
    if isinstance(st.session_state.get(SSKey.INTERVIEW_PREP_FACH.value), dict):
        available_artifact_ids.append("interview_fach")
    if isinstance(st.session_state.get(SSKey.BOOLEAN_SEARCH_STRING.value), dict):
        available_artifact_ids.append("boolean_search")
    if isinstance(st.session_state.get(SSKey.EMPLOYMENT_CONTRACT_DRAFT.value), dict):
        available_artifact_ids.append("employment_contract")
    if not available_artifact_ids:
        st.info("Noch keine weiteren Recruiting-Unterlagen vorhanden.")
        return

    active_artifact_id = _resolve_active_artifact_id(
        available_artifact_ids=available_artifact_ids
    )
    render_output_header(
        "Ergebnis-Fokus",
        _artifact_display_label(active_artifact_id),
    )
    _render_active_artifact(artifact_id=active_artifact_id, brief=brief)
    _render_secondary_artifacts(
        active_artifact_id=active_artifact_id,
        available_artifact_ids=available_artifact_ids,
    )


def _render_summary_export_workspace(*, brief: VacancyBrief) -> None:
    st.subheader("Export")
    export_payload = _build_structured_export_payload(brief)
    export_json_text = json.dumps(export_payload, indent=2, ensure_ascii=False)
    md = _brief_to_markdown(brief)
    json_bytes = export_json_text.encode("utf-8")
    docx_bytes = _brief_to_docx_bytes(brief)
    st.caption(
        "Lade die Exportformate direkt herunter. JSON-Vorschau und Debug-Details sind standardmäßig eingeklappt."
    )
    download_columns = st.columns(2)
    with download_columns[0]:
        st.download_button(
            "JSON herunterladen",
            data=json_bytes,
            file_name="vacancy_brief.json",
            mime="application/json",
        )
    with download_columns[1]:
        st.download_button(
            "Markdown herunterladen",
            data=md.encode("utf-8"),
            file_name="vacancy_brief.md",
            mime="text/markdown",
        )
    with download_columns[0]:
        st.download_button(
            "DOCX herunterladen",
            data=docx_bytes,
            file_name="vacancy_brief.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
