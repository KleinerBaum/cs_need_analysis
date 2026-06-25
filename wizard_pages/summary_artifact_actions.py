# wizard_pages/summary_artifact_actions.py
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

from audience import is_candidate_audience, normalize_audience_mode
from i18n import active_language
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
    SUMMARY_ACTIVE_ARTIFACT_IDS,
    UI_PREFERENCE_CONFIDENCE_THRESHOLD,
)
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
from homepage_research import (
    normalize_company_website_research_payload as _normalize_company_website_research_payload,
)
from esco_client import EscoClient, EscoClientError
from esco_semantics import normalize_anchor_ref, sync_esco_semantic_state
from llm_client import (
    JobAdGenerationResult,
    OpenAICallError,
    TASK_GENERATE_BOOLEAN_SEARCH,
    TASK_GENERATE_INTERVIEW_SHEET_HM,
    TASK_GENERATE_INTERVIEW_SHEET_HR,
    TASK_GENERATE_JOB_AD,
    TASK_GENERATE_VACANCY_BRIEF,
    generate_boolean_search_pack,
    generate_custom_job_ad,
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
from ux_copy_contract import summary_ui_copy
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
    render_error_banner,
    render_interview_prep_fach,
    render_interview_prep_hr,
    render_openai_error,
)
from usage_events import get_usage_events, record_artifact_generated
from usage_utils import usage_has_cache_hit
from wizard_pages.base import (
    WizardContext,
    WizardPage,
    get_current_ui_mode,
    nav_buttons,
    render_active_ui_mode_caption,
)

from wizard_pages.summary_readiness import (
    SummaryViewModel,
    _is_critical_summary_fact_row,
    _resolve_canonical_brief_status,
)

def _record_artifact_generated_with_fact_usage(
    session_state: dict[str, Any],
    *,
    artifact_id: str,
    cache_hit: bool | None = None,
    mode: str | None = None,
) -> None:
    record_artifact_generated(
        session_state,
        artifact_id=artifact_id,
        cache_hit=cache_hit,
        mode=mode,
    )
    mark_intake_facts_used_by_artifact(session_state, artifact_id)


class SummaryAction(TypedDict):
    id: str
    title: str
    benefit: str
    cta_label: str
    blocked_cta_label: str | None
    requires: tuple[SSKey, ...]
    requirement_text: str
    requirement_check_fn: Callable[[], tuple[bool, str]] | None
    generator_fn: Callable[[], None] | None
    result_key: SSKey
    input_hints: tuple[str, ...]
    input_renderer: Callable[[], None] | None


SUMMARY_PRIMARY_ARTIFACT_IDS: Final[tuple[str, ...]] = tuple(
    artifact_id
    for artifact_id in SUMMARY_ACTIVE_ARTIFACT_IDS
    if artifact_id != "brief"
)


def _resolve_active_artifact_id(*, available_artifact_ids: list[str]) -> str:
    active_raw = st.session_state.get(SSKey.SUMMARY_ACTIVE_ARTIFACT.value, "")
    normalized_active = _to_canonical_artifact_id(active_raw)
    if normalized_active in available_artifact_ids:
        if active_raw != normalized_active:
            st.session_state[SSKey.SUMMARY_ACTIVE_ARTIFACT.value] = normalized_active
        return normalized_active
    if available_artifact_ids:
        fallback = available_artifact_ids[0]
    else:
        fallback = ""
    st.session_state[SSKey.SUMMARY_ACTIVE_ARTIFACT.value] = fallback
    return fallback


def _has_required_state(requirements: tuple[SSKey, ...]) -> bool:
    for required_key in requirements:
        if not st.session_state.get(required_key.value):
            return False
    return True


def _get_brief_requirement_status(resolved_brief_model: str) -> tuple[bool, str]:
    status = _resolve_canonical_brief_status(resolved_brief_model=resolved_brief_model)
    return status.ready_for_follow_ups, status.message


def _get_brief_status(
    *,
    primary_action: SummaryAction,
    resolved_brief_model: str,
) -> tuple[str, str, str]:
    status = _resolve_canonical_brief_status(
        resolved_brief_model=resolved_brief_model,
        has_brief_prerequisites=_has_required_state(primary_action["requires"]),
    )
    return (status.state, status.message, status.cta_label)


def _summary_nested_dict_state(key: SSKey) -> dict[str, Any]:
    raw_value = st.session_state.get(key.value)
    if isinstance(raw_value, dict):
        return raw_value
    st.session_state[key.value] = {}
    return st.session_state[key.value]


def _read_artifact_options(artifact_id: str) -> dict[str, Any]:
    state = _summary_nested_dict_state(SSKey.SUMMARY_ARTIFACT_OPTIONS)
    value = state.get(artifact_id)
    return value if isinstance(value, dict) else {}


def _write_artifact_options(artifact_id: str, options: Mapping[str, Any]) -> None:
    state = _summary_nested_dict_state(SSKey.SUMMARY_ARTIFACT_OPTIONS)
    state[artifact_id] = dict(options)
    st.session_state[SSKey.SUMMARY_ARTIFACT_OPTIONS.value] = state


def _read_artifact_change_request(artifact_id: str) -> str:
    state = _summary_nested_dict_state(SSKey.SUMMARY_ARTIFACT_CHANGE_REQUESTS)
    return str(state.get(artifact_id) or "").strip()


def _write_artifact_change_request(artifact_id: str, value: str) -> None:
    state = _summary_nested_dict_state(SSKey.SUMMARY_ARTIFACT_CHANGE_REQUESTS)
    state[artifact_id] = value
    st.session_state[SSKey.SUMMARY_ARTIFACT_CHANGE_REQUESTS.value] = state


def _artifact_current_fingerprint(vm: SummaryViewModel, artifact_id: str) -> str:
    payload = {
        "summary_input": vm.artifacts.input_fingerprint,
        "artifact_id": artifact_id,
        "options": _read_artifact_options(artifact_id),
        "change_request": _read_artifact_change_request(artifact_id),
        "audience_mode": normalize_audience_mode(
            st.session_state.get(SSKey.AUDIENCE_MODE.value)
        ),
    }
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _mark_artifact_current(vm: SummaryViewModel, artifact_id: str) -> None:
    fingerprints = _summary_nested_dict_state(SSKey.SUMMARY_ARTIFACT_FINGERPRINTS)
    fingerprints[artifact_id] = _artifact_current_fingerprint(vm, artifact_id)
    st.session_state[SSKey.SUMMARY_ARTIFACT_FINGERPRINTS.value] = fingerprints


def _artifact_result_key(artifact_id: str) -> SSKey | None:
    return {
        "job_ad": SSKey.JOB_AD_DRAFT_CUSTOM,
        "interview_hr": SSKey.INTERVIEW_PREP_HR,
        "interview_fach": SSKey.INTERVIEW_PREP_FACH,
        "boolean_search": SSKey.BOOLEAN_SEARCH_STRING,
    }.get(artifact_id)


def _artifact_has_result(artifact_id: str) -> bool:
    result_key = _artifact_result_key(artifact_id)
    return bool(result_key and st.session_state.get(result_key.value))


def _artifact_status_label(vm: SummaryViewModel, artifact_id: str) -> tuple[str, str]:
    language = active_language()
    if not _artifact_has_result(artifact_id):
        return "open", summary_ui_copy("artifact_status.open", language=language)
    fingerprints = _summary_nested_dict_state(SSKey.SUMMARY_ARTIFACT_FINGERPRINTS)
    stored = str(fingerprints.get(artifact_id) or "")
    if not stored and vm.artifacts.input_fingerprint:
        return "stale", summary_ui_copy("artifact_status.stale", language=language)
    if stored and stored != _artifact_current_fingerprint(vm, artifact_id):
        return "stale", summary_ui_copy("artifact_status.stale", language=language)
    return "current", summary_ui_copy("artifact_status.current", language=language)


def _build_artifact_status_rows(
    *, action_registry: list[SummaryAction]
) -> list[dict[str, str]]:
    language = active_language()
    rows: list[dict[str, str]] = []
    for action in action_registry:
        has_result = bool(st.session_state.get(action["result_key"].value))
        requirements_ok = _has_required_state(action["requires"])
        requirement_ok = True
        requirement_check_fn = action.get("requirement_check_fn")
        if requirement_check_fn is not None:
            requirement_ok, _ = requirement_check_fn()
        rows.append(
            {
                "Unterlage": action["title"],
                "Status": summary_ui_copy(
                    "artifact_status.current" if has_result else "artifact_status.open",
                    language=language,
                ),
                "Voraussetzungen": (
                    summary_ui_copy("artifact_status.met", language=language)
                    if (requirements_ok and requirement_ok)
                    else summary_ui_copy("artifact_status.open", language=language)
                ),
            }
        )
    return rows


@dataclass(frozen=True)
class NextBestActionRecommendation:
    action: SummaryAction
    reason: str
    cta_label: str


def _resolve_next_best_action_recommendation(
    action_registry: list[SummaryAction],
    resolved_brief_model: str,
    vm: SummaryViewModel,
) -> NextBestActionRecommendation | None:
    action_by_id = {action["id"]: action for action in action_registry}

    missing_or_partial = {
        (row.bereich, row.feld)
        for row in vm.fact_rows
        if row.status in {"Fehlend", "Teilweise"}
        and _is_critical_summary_fact_row(row)
    }

    def _first_available_action(ids: tuple[str, ...]) -> SummaryAction | None:
        for action_id in ids:
            action = action_by_id.get(action_id)
            if action is None:
                continue
            if bool(st.session_state.get(action["result_key"].value)):
                continue
            if not _has_required_state(action["requires"]):
                continue
            requirement_check_fn = action.get("requirement_check_fn")
            if requirement_check_fn is not None:
                requirement_ok, _ = requirement_check_fn()
                if not requirement_ok:
                    continue
            return action
        return None

    def _is_group_missing(group: set[tuple[str, str]]) -> bool:
        return any(item in missing_or_partial for item in group)

    def _recommend(action_id: str, reason: str, *, cta_label: str | None = None) -> NextBestActionRecommendation | None:
        action = action_by_id.get(action_id)
        if action is None:
            return None
        return NextBestActionRecommendation(action=action, reason=reason, cta_label=cta_label or action["cta_label"])

    core_profile_group = {
        ("Kernprofil", "Rolle"),
        ("Kernprofil", "Land"),
        ("Kernprofil", "Stadt"),
        ("Klassifikation", "NACE-Code"),
        ("Klassifikation", "NACE → ESCO Mapping"),
    }
    company_basics_group = {
        ("Kernprofil", "Unternehmen"),
        ("Unternehmen", "Wie lautet der Firmenname?"),
    }
    role_profile_group = {("Rolle & Aufgaben", "Aufgaben"), ("Rolle & Aufgaben", "Ziele")}
    skills_profile_group = {
        ("Skills", "Must-have-Skills"),
        ("Skills", "Nice-to-have-Skills"),
    }
    benefits_group = {("Benefits", "Benefit")}
    interview_group = {("Interview", "Interviewphasen")}

    if _is_group_missing(core_profile_group | company_basics_group):
        reason = (
            "Core profile, location, or company context is missing."
            if active_language() == "en"
            else "Kernprofil, Standort oder Unternehmenskontext fehlen."
        )
        cta = (
            "Complete company context"
            if active_language() == "en"
            else "Unternehmenskontext vervollständigen"
        )
        return _recommend("brief", reason, cta_label=cta)
    if _is_group_missing(role_profile_group):
        return _recommend(
            "brief",
            "Role profile is still incomplete." if active_language() == "en" else "Rollenprofil ist noch unvollständig.",
            cta_label="Complete role profile" if active_language() == "en" else "Rollenprofil vervollständigen",
        )
    if _is_group_missing(skills_profile_group):
        return _recommend(
            "brief",
            "Skills and requirements are still incomplete." if active_language() == "en" else "Skills und Anforderungen sind noch unvollständig.",
            cta_label="Clarify skills and requirements" if active_language() == "en" else "Skills und Anforderungen klären",
        )
    if _is_group_missing(benefits_group):
        return _recommend(
            "brief",
            "Benefits and conditions are missing." if active_language() == "en" else "Benefits und Rahmenbedingungen fehlen.",
            cta_label="Add benefits and conditions" if active_language() == "en" else "Benefits und Rahmenbedingungen ergänzen",
        )
    if _is_group_missing(interview_group):
        return _recommend(
            "brief",
            "Interview process is not defined yet." if active_language() == "en" else "Interviewprozess ist noch nicht definiert.",
            cta_label="Define interview process" if active_language() == "en" else "Interviewprozess definieren",
        )

    brief_action = action_by_id.get("brief")
    if brief_action is not None:
        brief_status = _resolve_canonical_brief_status(resolved_brief_model=resolved_brief_model)
        if not brief_status.ready_for_follow_ups:
            return _recommend(
                "brief",
                summary_ui_copy(
                    "release_gate.brief_missing_or_not_ready",
                    language=active_language(),
                ),
                cta_label=summary_ui_copy(
                    "release_gate.brief_missing_or_not_ready_cta",
                    language=active_language(),
                ),
            )

    sourcing_action = _first_available_action(("job_ad", "boolean_search"))
    if sourcing_action is not None:
        reason = summary_ui_copy(
            "release_gate.sourcing_ready_reason",
            language=active_language(),
        )
        return NextBestActionRecommendation(action=sourcing_action, reason=reason, cta_label=sourcing_action["cta_label"])

    fallback_action = _first_available_action(
        ("interview_hr", "interview_fach", "boolean_search")
    )
    if fallback_action is not None:
        return NextBestActionRecommendation(
            action=fallback_action,
            reason=summary_ui_copy(
                "release_gate.fallback_next_reason",
                language=active_language(),
            ),
            cta_label=fallback_action["cta_label"],
        )
    if brief_action is not None:
        return NextBestActionRecommendation(
            action=brief_action,
            reason=summary_ui_copy(
                "release_gate.safe_brief_reason",
                language=active_language(),
            ),
            cta_label=brief_action["cta_label"],
        )
    return None


def _resolve_next_best_action(
    action_registry: list[SummaryAction],
    resolved_brief_model: str,
    vm: SummaryViewModel,
) -> SummaryAction | None:
    recommendation = _resolve_next_best_action_recommendation(
        action_registry=action_registry,
        resolved_brief_model=resolved_brief_model,
        vm=vm,
    )
    return recommendation.action if recommendation is not None else None


def _artifact_pipeline_status(
    action: SummaryAction, *, resolved_brief_model: str
) -> tuple[str, str]:
    language = active_language()
    if action["id"] == "brief":
        state, _, _ = _get_brief_status(
            primary_action=action,
            resolved_brief_model=resolved_brief_model,
        )
        return brief_pipeline_status_for_state(state, language=language)

    has_result = bool(st.session_state.get(action["result_key"].value))
    if has_result:
        return "current", summary_ui_copy("artifact_status.current", language=language)

    requirements_ok = _has_required_state(action["requires"])
    requirement_ok = True
    requirement_check_fn = action.get("requirement_check_fn")
    if requirement_check_fn is not None:
        requirement_ok, _ = requirement_check_fn()
    if requirements_ok and requirement_ok and action["generator_fn"] is not None:
        return "ready", summary_ui_copy("artifact_status.ready", language=language)
    if not requirements_ok or not requirement_ok:
        return "blocked", summary_ui_copy("artifact_status.blocked", language=language)
    return "open", summary_ui_copy("artifact_status.open", language=language)


def _build_enrichment_timing_rows(session_state: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in get_usage_events(session_state):
        if event.get("event_type") != "enrichment_timed":
            continue
        metadata = event.get("metadata")
        if not isinstance(metadata, dict):
            continue
        rows.append(
            {
                "Stage": str(metadata.get("stage") or ""),
                "Pfad": str(metadata.get("path") or ""),
                "Status": str(metadata.get("status") or ""),
                "Dauer (ms)": int(metadata.get("duration_ms") or 0),
                "Cache": metadata.get("cache_hit"),
                "Fragment": metadata.get("fragment_enabled"),
                "Treffer": metadata.get("result_count"),
            }
        )
    return sorted(rows, key=lambda row: int(row["Dauer (ms)"]), reverse=True)


def _build_action_registry(
    *,
    resolved_brief_model: str,
    resolved_job_ad_model: str,
    resolved_hr_sheet_model: str,
    resolved_fach_sheet_model: str,
    resolved_boolean_search_model: str,
    render_job_ad_inputs: Callable[[], None] | None = None,
    follow_up_requirement_check: Callable[[], tuple[bool, str]],
    generate_recruiting_brief: Callable[[], None],
    generate_job_ad: Callable[[], None],
    generate_interview_prep_hr: Callable[[], None],
    generate_interview_prep_fach: Callable[[], None],
    generate_boolean_search: Callable[[], None],
) -> list[SummaryAction]:
    language = active_language()
    c = lambda key, **params: summary_ui_copy(
        f"action_registry.{key}",
        language=language,
        **params,
    )
    candidate_view = is_candidate_audience(
        st.session_state.get(SSKey.AUDIENCE_MODE.value)
    )

    def cta(default_key: str, candidate_de: str, candidate_en: str) -> str:
        if not candidate_view:
            return c(default_key)
        return candidate_en if language == "en" else candidate_de

    return [
        {
            "id": "brief",
            "title": _artifact_display_label("brief", language=language),
            "benefit": c("brief_benefit"),
            "cta_label": cta(
                "brief_cta",
                "Brief verständlich erklären",
                "Explain brief clearly",
            ),
            "blocked_cta_label": None,
            "requires": (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN),
            "requirement_text": c("brief_requirement"),
            "requirement_check_fn": None,
            "generator_fn": generate_recruiting_brief,
            "result_key": SSKey.BRIEF,
            "input_hints": (
                c("brief_hint_job"),
                c("brief_hint_answers"),
                c("draft_model", model=resolved_brief_model),
            ),
            "input_renderer": None,
        },
        {
            "id": "job_ad",
            "title": _artifact_display_label("job_ad", language=language),
            "benefit": c("job_ad_benefit"),
            "cta_label": cta(
                "job_ad_cta",
                "Kandidatenansicht erstellen",
                "Create candidate view",
            ),
            "blocked_cta_label": None,
            "requires": (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN),
            "requirement_text": c("brief_requirement"),
            "requirement_check_fn": None,
            "generator_fn": generate_job_ad,
            "result_key": SSKey.JOB_AD_DRAFT_CUSTOM,
            "input_hints": (),
            "input_renderer": render_job_ad_inputs,
        },
        {
            "id": "interview_hr",
            "title": _artifact_display_label("interview_hr", language=language),
            "benefit": c("hr_benefit"),
            "cta_label": cta(
                "hr_cta",
                "Interview-Erwartungen erklären",
                "Explain interview expectations",
            ),
            "blocked_cta_label": c("hr_blocked_cta"),
            "requires": (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN),
            "requirement_text": c("brief_required"),
            "requirement_check_fn": follow_up_requirement_check,
            "generator_fn": generate_interview_prep_hr,
            "result_key": SSKey.INTERVIEW_PREP_HR,
            "input_hints": (
                c("current_brief_hint"),
                c("critical_must_haves"),
                c("hr_model", model=resolved_hr_sheet_model),
            ),
            "input_renderer": None,
        },
        {
            "id": "interview_fach",
            "title": _artifact_display_label("interview_fach", language=language),
            "benefit": c("fach_benefit"),
            "cta_label": cta(
                "fach_cta",
                "Fachgespräch transparent machen",
                "Make technical interview transparent",
            ),
            "blocked_cta_label": c("fach_blocked_cta"),
            "requires": (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN),
            "requirement_text": c("brief_required"),
            "requirement_check_fn": follow_up_requirement_check,
            "generator_fn": generate_interview_prep_fach,
            "result_key": SSKey.INTERVIEW_PREP_FACH,
            "input_hints": (
                c("current_brief_hint"),
                c("must_haves_tasks"),
                c("fach_model", model=resolved_fach_sheet_model),
            ),
            "input_renderer": None,
        },
        {
            "id": "boolean_search",
            "title": _artifact_display_label("boolean_search", language=language),
            "benefit": c("boolean_benefit"),
            "cta_label": cta(
                "boolean_cta",
                "Suchprofil verständlich machen",
                "Clarify search profile",
            ),
            "blocked_cta_label": c("boolean_blocked_cta"),
            "requires": (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN),
            "requirement_text": c("brief_required"),
            "requirement_check_fn": follow_up_requirement_check,
            "generator_fn": generate_boolean_search,
            "result_key": SSKey.BOOLEAN_SEARCH_STRING,
            "input_hints": (
                c("current_brief_hint"),
                c("skills_hint"),
                c("boolean_model", model=resolved_boolean_search_model),
            ),
            "input_renderer": None,
        },
    ]
