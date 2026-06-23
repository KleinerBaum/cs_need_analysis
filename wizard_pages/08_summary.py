# wizard_pages/08_summary.py

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
from state_store import StateStore
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
    build_live_artifact_preview_payload,
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
    render_live_artifact_preview_panel,
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
    resolve_dynamic_step_copy,
)



from wizard_pages import summary_artifact_actions as _summary_artifact_actions
from wizard_pages import summary_exporters as _summary_exporters
from wizard_pages import summary_readiness as _summary_readiness
from wizard_pages import summary_view as _summary_view

SUPPORTED_LOGO_MIME_TYPES = _summary_exporters.SUPPORTED_LOGO_MIME_TYPES
DocxPictureDocument = _summary_exporters.DocxPictureDocument
LogoPayload = _summary_exporters.LogoPayload
EscoExportConcept = _summary_exporters.EscoExportConcept
EscoMatchExplainability = _summary_exporters.EscoMatchExplainability
EscoSharedFields = _summary_exporters.EscoSharedFields
SUMMARY_FACT_OVERVIEW_COLUMNS = _summary_readiness.SUMMARY_FACT_OVERVIEW_COLUMNS
SUMMARY_FACT_EMPTY_VALUES = _summary_readiness.SUMMARY_FACT_EMPTY_VALUES
SUMMARY_FACT_STEP_ORDER = _summary_readiness.SUMMARY_FACT_STEP_ORDER
SUMMARY_FACT_STEP_LABELS = _summary_readiness.SUMMARY_FACT_STEP_LABELS
SUMMARY_AREA_TO_STEP_KEY = _summary_readiness.SUMMARY_AREA_TO_STEP_KEY
SUMMARY_FACT_DEFS_BY_KEY = _summary_readiness.SUMMARY_FACT_DEFS_BY_KEY
SummaryMeta = _summary_readiness.SummaryMeta
SummaryStatus = _summary_readiness.SummaryStatus
SummaryArtifactState = _summary_readiness.SummaryArtifactState
CanonicalBriefStatus = _summary_readiness.CanonicalBriefStatus
SummaryViewModel = _summary_readiness.SummaryViewModel
SummaryFactReadiness = _summary_readiness.SummaryFactReadiness
SummaryAction = _summary_artifact_actions.SummaryAction
SUMMARY_PRIMARY_ARTIFACT_IDS = _summary_artifact_actions.SUMMARY_PRIMARY_ARTIFACT_IDS
NextBestActionRecommendation = _summary_artifact_actions.NextBestActionRecommendation
STYLEGUIDE_TEMPLATE_BLOCKS = _summary_view.STYLEGUIDE_TEMPLATE_BLOCKS
CHANGE_REQUEST_TEMPLATE_BLOCKS = _summary_view.CHANGE_REQUEST_TEMPLATE_BLOCKS
JOB_AD_PRESET_BLOCKS = _summary_view.JOB_AD_PRESET_BLOCKS
JOB_AD_ADDRESS_BLOCKS = _summary_view.JOB_AD_ADDRESS_BLOCKS
JOB_AD_TONE_BLOCKS = _summary_view.JOB_AD_TONE_BLOCKS
JOB_AD_LENGTH_BLOCKS = _summary_view.JOB_AD_LENGTH_BLOCKS
JOB_AD_CTA_BLOCKS = _summary_view.JOB_AD_CTA_BLOCKS
JOB_AD_OPTIMIZATION_BLOCKS = _summary_view.JOB_AD_OPTIMIZATION_BLOCKS
JOB_AD_ALWAYS_ON_COMPLIANCE_TEXT = _summary_view.JOB_AD_ALWAYS_ON_COMPLIANCE_TEXT
RenderableContainer = _summary_view.RenderableContainer
SummaryTabs = _summary_view.SummaryTabs

_SUMMARY_SLICE_MODULES = (
    _summary_exporters,
    _summary_readiness,
    _summary_artifact_actions,
    _summary_view,
)
_SUMMARY_SLICE_ORIGINALS = {
    _summary_exporters: {
        "_session_list": _summary_exporters._session_list,
        "_session_dict": _summary_exporters._session_dict,
        "_session_str": _summary_exporters._session_str,
        "_read_esco_shared_fields": _summary_exporters._read_esco_shared_fields,
        "_read_esco_semantic_context": _summary_exporters._read_esco_semantic_context,
        "_show_semantic_esco_sections": _summary_exporters._show_semantic_esco_sections,
        "_count_skill_relation_traces": _summary_exporters._count_skill_relation_traces,
        "_compute_esco_coverage_metrics": _summary_exporters._compute_esco_coverage_metrics,
        "_build_esco_mapping_report_rows": _summary_exporters._build_esco_mapping_report_rows,
        "_build_structured_export_payload": _summary_exporters._build_structured_export_payload,
        "_build_brief_structured_preview_payload": _summary_exporters._build_brief_structured_preview_payload,
        "_read_saved_selection_labels": _summary_exporters._read_saved_selection_labels,
        "_read_esco_skill_refs": _summary_exporters._read_esco_skill_refs,
        "_read_selected_esco_occupation": _summary_exporters._read_selected_esco_occupation,
        "_read_esco_match_explainability": _summary_exporters._read_esco_match_explainability,
        "_job_ad_to_docx_bytes": _summary_exporters._job_ad_to_docx_bytes,
        "_job_ad_to_pdf_bytes": _summary_exporters._job_ad_to_pdf_bytes,
        "_brief_to_docx_bytes": _summary_exporters._brief_to_docx_bytes,
        "_interview_prep_hr_to_docx_bytes": _summary_exporters._interview_prep_hr_to_docx_bytes,
        "_apply_interview_docx_brand_style": _summary_exporters._apply_interview_docx_brand_style,
        "_interview_prep_fach_to_docx_bytes": _summary_exporters._interview_prep_fach_to_docx_bytes,
        "_interview_prep_fach_to_pdf_bytes": _summary_exporters._interview_prep_fach_to_pdf_bytes,
        "_employment_contract_to_docx_bytes": _summary_exporters._employment_contract_to_docx_bytes,
        "_normalize_logo_payload": _summary_exporters._normalize_logo_payload,
        "_read_logo_payload": _summary_exporters._read_logo_payload,
        "_normalize_stored_logo_payload": _summary_exporters._normalize_stored_logo_payload,
        "_job_ad_logo_payload": _summary_exporters._job_ad_logo_payload,
        "_add_logo_to_docx": _summary_exporters._add_logo_to_docx,
        "_job_ad_preview_shell_options": _summary_exporters._job_ad_preview_shell_options,
        "_job_ad_preview_html": _summary_exporters._job_ad_preview_html,
    },
    _summary_readiness: {
        "_resolve_canonical_brief_status": _summary_readiness._resolve_canonical_brief_status,
        "_read_summary_confidence_threshold": _summary_readiness._read_summary_confidence_threshold,
        "_build_summary_completion_status": _summary_readiness._build_summary_completion_status,
        "_build_summary_fact_fingerprint_payload": _summary_readiness._build_summary_fact_fingerprint_payload,
        "_summary_fact_requirement_stage": _summary_readiness._summary_fact_requirement_stage,
        "_is_critical_summary_fact_row": _summary_readiness._is_critical_summary_fact_row,
        "_summary_fact_resolution_status": _summary_readiness._summary_fact_resolution_status,
        "_summary_fact_confidence_allows_readiness": _summary_readiness._summary_fact_confidence_allows_readiness,
        "_summary_fact_readiness_bucket": _summary_readiness._summary_fact_readiness_bucket,
        "_build_summary_fact_readiness": _summary_readiness._build_summary_fact_readiness,
        "_build_summary_status": _summary_readiness._build_summary_status,
        "_build_summary_view_model": _summary_readiness._build_summary_view_model,
        "_summary_fact_allows_readiness": _summary_readiness._summary_fact_allows_readiness,
        "_resolve_summary_meta_value": _summary_readiness._resolve_summary_meta_value,
        "_build_summary_meta": _summary_readiness._build_summary_meta,
        "_build_summary_artifact_state": _summary_readiness._build_summary_artifact_state,
        "_build_internal_fallback_brief": _summary_readiness._build_internal_fallback_brief,
        "_build_country_readiness_items": _summary_readiness._build_country_readiness_items,
        "_fallback_summary_source_type": _summary_readiness._fallback_summary_source_type,
        "_summary_row_provenance_label": _summary_readiness._summary_row_provenance_label,
        "_summary_step_key_for_area": _summary_readiness._summary_step_key_for_area,
        "_with_summary_row_metadata": _summary_readiness._with_summary_row_metadata,
        "_is_meaningful_summary_fact_row": _summary_readiness._is_meaningful_summary_fact_row,
        "_should_include_missing_summary_fact": _summary_readiness._should_include_missing_summary_fact,
        "_build_summary_fact_rows": _summary_readiness._build_summary_fact_rows,
        "_is_visible_summary_fact_row": _summary_readiness._is_visible_summary_fact_row,
        "_summary_fact_row_id": _summary_readiness._summary_fact_row_id,
        "_summary_visible_fact_rows": _summary_readiness._summary_visible_fact_rows,
        "_summary_fact_rows_by_step": _summary_readiness._summary_fact_rows_by_step,
        "_apply_summary_fact_edits": _summary_readiness._apply_summary_fact_edits,
        "_build_summary_critical_gap_rows": _summary_readiness._build_summary_critical_gap_rows,
        "_build_missing_critical_items": _summary_readiness._build_missing_critical_items,
    },
    _summary_artifact_actions: {
        "_record_artifact_generated_with_fact_usage": _summary_artifact_actions._record_artifact_generated_with_fact_usage,
        "_resolve_active_artifact_id": _summary_artifact_actions._resolve_active_artifact_id,
        "_has_required_state": _summary_artifact_actions._has_required_state,
        "_get_brief_requirement_status": _summary_artifact_actions._get_brief_requirement_status,
        "_get_brief_status": _summary_artifact_actions._get_brief_status,
        "_summary_nested_dict_state": _summary_artifact_actions._summary_nested_dict_state,
        "_read_artifact_options": _summary_artifact_actions._read_artifact_options,
        "_write_artifact_options": _summary_artifact_actions._write_artifact_options,
        "_read_artifact_change_request": _summary_artifact_actions._read_artifact_change_request,
        "_write_artifact_change_request": _summary_artifact_actions._write_artifact_change_request,
        "_artifact_current_fingerprint": _summary_artifact_actions._artifact_current_fingerprint,
        "_mark_artifact_current": _summary_artifact_actions._mark_artifact_current,
        "_artifact_result_key": _summary_artifact_actions._artifact_result_key,
        "_artifact_has_result": _summary_artifact_actions._artifact_has_result,
        "_artifact_status_label": _summary_artifact_actions._artifact_status_label,
        "_build_artifact_status_rows": _summary_artifact_actions._build_artifact_status_rows,
        "_resolve_next_best_action_recommendation": _summary_artifact_actions._resolve_next_best_action_recommendation,
        "_resolve_next_best_action": _summary_artifact_actions._resolve_next_best_action,
        "_artifact_pipeline_status": _summary_artifact_actions._artifact_pipeline_status,
        "_build_enrichment_timing_rows": _summary_artifact_actions._build_enrichment_timing_rows,
        "_build_action_registry": _summary_artifact_actions._build_action_registry,
    },
    _summary_view: {
        "_widget_key": _summary_view._widget_key,
        "_append_template_blocks": _summary_view._append_template_blocks,
        "_render_template_toggles": _summary_view._render_template_toggles,
        "_build_selection_rows": _summary_view._build_selection_rows,
        "_collect_critical_gaps": _summary_view._collect_critical_gaps,
        "_selection_options_by_group": _summary_view._selection_options_by_group,
        "_first_existing_group": _summary_view._first_existing_group,
        "_render_guided_multiselect": _summary_view._render_guided_multiselect,
        "_build_job_ad_styleguide_text": _summary_view._build_job_ad_styleguide_text,
        "_build_job_ad_change_request_text": _summary_view._build_job_ad_change_request_text,
        "_render_job_ad_settings_summary": _summary_view._render_job_ad_settings_summary,
        "_render_pills_multiselect": _summary_view._render_pills_multiselect,
        "_render_selection_matrix": _summary_view._render_selection_matrix,
        "_render_summary_hero": _summary_view._render_summary_hero,
        "_build_summary_headline": _summary_view._build_summary_headline,
        "_build_summary_subheader": _summary_view._build_summary_subheader,
        "_render_summary_meta_badges": _summary_view._render_summary_meta_badges,
        "_render_esco_coverage_kpis": _summary_view._render_esco_coverage_kpis,
        "_render_summary_facts_column_overview": _summary_view._render_summary_facts_column_overview,
        "_render_summary_facts_section": _summary_view._render_summary_facts_section,
        "_summary_fact_caption": _summary_view._summary_fact_caption,
        "_render_summary_facts_table": _summary_view._render_summary_facts_table,
        "_render_summary_facts_matrix": _summary_view._render_summary_facts_matrix,
        "_render_summary_critical_gaps_table": _summary_view._render_summary_critical_gaps_table,
        "_default_job_ad_selected_values": _summary_view._default_job_ad_selected_values,
        "_append_distinct_text": _summary_view._append_distinct_text,
        "_build_fach_competency_suggestions": _summary_view._build_fach_competency_suggestions,
        "_read_optional_text_upload": _summary_view._read_optional_text_upload,
        "_render_job_ad_compact_controls": _summary_view._render_job_ad_compact_controls,
        "_render_interview_compact_controls": _summary_view._render_interview_compact_controls,
        "_render_boolean_compact_controls": _summary_view._render_boolean_compact_controls,
        "_render_contract_compact_controls": _summary_view._render_contract_compact_controls,
        "_render_summary_artifact_grid": _summary_view._render_summary_artifact_grid,
        "_render_action_card": _summary_view._render_action_card,
        "_render_job_ad_configuration_panel": _summary_view._render_job_ad_configuration_panel,
        "_render_primary_brief_card": _summary_view._render_primary_brief_card,
        "_render_follow_up_cards": _summary_view._render_follow_up_cards,
        "_render_export_bar": _summary_view._render_export_bar,
        "_render_summary_dashboard_css": _summary_view._render_summary_dashboard_css,
        "_render_artifact_pipeline": _summary_view._render_artifact_pipeline,
        "_render_summary_readiness_metrics": _summary_view._render_summary_readiness_metrics,
        "_render_readiness_tab": _summary_view._render_readiness_tab,
        "_render_readiness_dashboard_header": _summary_view._render_readiness_dashboard_header,
        "_render_next_best_action_card": _summary_view._render_next_best_action_card,
        "_render_critical_gaps_card": _summary_view._render_critical_gaps_card,
        "_render_artifact_launcher_cards": _summary_view._render_artifact_launcher_cards,
        "_build_summary_tabs": _summary_view._build_summary_tabs,
        "_render_summary_workspace_tabs": _summary_view._render_summary_workspace_tabs,
        "_render_summary_processing_hub": _summary_view._render_summary_processing_hub,
        "_is_warning_checklist_item": _summary_view._is_warning_checklist_item,
        "_render_agg_checklist_review": _summary_view._render_agg_checklist_review,
        "_render_job_ad_artifact": _summary_view._render_job_ad_artifact,
        "_render_active_artifact": _summary_view._render_active_artifact,
        "_generated_summary_artifact_ids": _summary_view._generated_summary_artifact_ids,
        "_resolve_output_artifact_id": _summary_view._resolve_output_artifact_id,
        "_render_artifact_result_switcher": _summary_view._render_artifact_result_switcher,
        "_render_artifact_refinement_box": _summary_view._render_artifact_refinement_box,
        "_current_boolean_search_pack": _summary_view._current_boolean_search_pack,
        "_render_boolean_artifact_context_panels": _summary_view._render_boolean_artifact_context_panels,
        "_render_summary_output_workspace": _summary_view._render_summary_output_workspace,
        "_render_secondary_artifacts": _summary_view._render_secondary_artifacts,
        "_render_summary_results_workspace": _summary_view._render_summary_results_workspace,
        "_render_summary_export_workspace": _summary_view._render_summary_export_workspace,
    },
}
_SUMMARY_SYNC_GLOBAL_NAMES = (
    "st",
    "docx",
    "BooleanSearchPack",
    "EmploymentContractDraft",
    "InterviewPrepSheetHiringManager",
    "InterviewPrepSheetHR",
    "JobAdExtract",
    "JobAdGenerationResult",
    "QuestionPlan",
    "VacancyBrief",
    "VacancyStructuredData",
    "get_esco_occupation_selected",
    "get_answers",
    "get_answer_meta",
    "has_confirmed_esco_anchor",
    "get_model_override",
    "set_answer",
    "write_intake_fact",
    "load_openai_settings",
    "resolve_model_for_task",
    "render_output_header",
    "render_card_start",
    "render_pill",
    "render_critical_gaps",
    "render_next_best_action",
    "render_brief",
    "render_interview_prep_hr",
    "render_interview_prep_fach",
    "render_boolean_search_pack",
    "render_boolean_supporting_terms",
    "render_boolean_usage_notes",
    "render_boolean_risks",
    "render_employment_contract_draft",
    "document_preview_shell",
    "markdown_article_preview_html",
    "get_usage_events",
    "record_artifact_generated",
    "mark_intake_facts_used_by_artifact",
    "_artifact_display_label",
    "_build_summary_input_fingerprint",
    "_build_esco_coverage_kpis",
    "_build_esco_coverage_metrics",
    "_build_esco_mapping_report_csv",
    "_build_esco_coverage_chart_spec",
    "_extract_skills_step_raw_terms",
    "_normalize_skill_term",
    "_to_esco_export_concepts",
    "_build_publishable_job_ad_markdown",
    "_build_publishable_job_ad_plain_text",
    "_dedupe_preserve_order",
    "_estimate_text_area_height",
    "_sanitize_generated_job_ad",
    "_normalize_company_website_research_payload",
)

def _sync_summary_slice_modules() -> None:
    for module in _SUMMARY_SLICE_MODULES:
        for name in _SUMMARY_SYNC_GLOBAL_NAMES:
            if name in globals() and hasattr(module, name):
                setattr(module, name, globals()[name])
        for name in _SUMMARY_WRAPPERS:
            if name in globals() and hasattr(module, name):
                setattr(module, name, globals()[name])
    for module, originals in _SUMMARY_SLICE_ORIGINALS.items():
        for name, original in originals.items():
            current = globals().get(name)
            wrapper = _SUMMARY_WRAPPERS.get(name)
            setattr(module, name, current if current is not wrapper else original)

def _delegate_summary_helper(module: Any, name: str, *args: Any, **kwargs: Any) -> Any:
    _sync_summary_slice_modules()
    return getattr(module, name)(*args, **kwargs)

def _make_summary_helper_wrapper(module: Any, name: str) -> Callable[..., Any]:
    def _wrapper(*args: Any, **kwargs: Any) -> Any:
        return _delegate_summary_helper(module, name, *args, **kwargs)
    _wrapper.__name__ = name
    _wrapper.__qualname__ = name
    _wrapper.__doc__ = getattr(module, name).__doc__
    return _wrapper

_SUMMARY_WRAPPERS: dict[str, Callable[..., Any]] = {}
for _summary_helper_name, _summary_helper_module in {
    "_session_list": _summary_exporters,
    "_session_dict": _summary_exporters,
    "_session_str": _summary_exporters,
    "_read_esco_shared_fields": _summary_exporters,
    "_read_esco_semantic_context": _summary_exporters,
    "_show_semantic_esco_sections": _summary_exporters,
    "_count_skill_relation_traces": _summary_exporters,
    "_compute_esco_coverage_metrics": _summary_exporters,
    "_build_esco_mapping_report_rows": _summary_exporters,
    "_build_structured_export_payload": _summary_exporters,
    "_build_brief_structured_preview_payload": _summary_exporters,
    "_read_saved_selection_labels": _summary_exporters,
    "_read_esco_skill_refs": _summary_exporters,
    "_read_selected_esco_occupation": _summary_exporters,
    "_read_esco_match_explainability": _summary_exporters,
    "_job_ad_to_docx_bytes": _summary_exporters,
    "_job_ad_to_pdf_bytes": _summary_exporters,
    "_brief_to_docx_bytes": _summary_exporters,
    "_interview_prep_hr_to_docx_bytes": _summary_exporters,
    "_apply_interview_docx_brand_style": _summary_exporters,
    "_interview_prep_fach_to_docx_bytes": _summary_exporters,
    "_interview_prep_fach_to_pdf_bytes": _summary_exporters,
    "_employment_contract_to_docx_bytes": _summary_exporters,
    "_normalize_logo_payload": _summary_exporters,
    "_read_logo_payload": _summary_exporters,
    "_normalize_stored_logo_payload": _summary_exporters,
    "_job_ad_logo_payload": _summary_exporters,
    "_add_logo_to_docx": _summary_exporters,
    "_job_ad_preview_shell_options": _summary_exporters,
    "_job_ad_preview_html": _summary_exporters,
    "_resolve_canonical_brief_status": _summary_readiness,
    "_read_summary_confidence_threshold": _summary_readiness,
    "_build_summary_completion_status": _summary_readiness,
    "_build_summary_fact_fingerprint_payload": _summary_readiness,
    "_summary_fact_requirement_stage": _summary_readiness,
    "_is_critical_summary_fact_row": _summary_readiness,
    "_summary_fact_resolution_status": _summary_readiness,
    "_summary_fact_confidence_allows_readiness": _summary_readiness,
    "_summary_fact_readiness_bucket": _summary_readiness,
    "_build_summary_fact_readiness": _summary_readiness,
    "_build_summary_status": _summary_readiness,
    "_build_summary_view_model": _summary_readiness,
    "_summary_fact_allows_readiness": _summary_readiness,
    "_resolve_summary_meta_value": _summary_readiness,
    "_build_summary_meta": _summary_readiness,
    "_build_summary_artifact_state": _summary_readiness,
    "_build_internal_fallback_brief": _summary_readiness,
    "_build_country_readiness_items": _summary_readiness,
    "_fallback_summary_source_type": _summary_readiness,
    "_summary_row_provenance_label": _summary_readiness,
    "_summary_step_key_for_area": _summary_readiness,
    "_with_summary_row_metadata": _summary_readiness,
    "_is_meaningful_summary_fact_row": _summary_readiness,
    "_should_include_missing_summary_fact": _summary_readiness,
    "_build_summary_fact_rows": _summary_readiness,
    "_is_visible_summary_fact_row": _summary_readiness,
    "_summary_fact_row_id": _summary_readiness,
    "_summary_visible_fact_rows": _summary_readiness,
    "_summary_fact_rows_by_step": _summary_readiness,
    "_apply_summary_fact_edits": _summary_readiness,
    "_build_summary_critical_gap_rows": _summary_readiness,
    "_build_missing_critical_items": _summary_readiness,
    "_record_artifact_generated_with_fact_usage": _summary_artifact_actions,
    "_resolve_active_artifact_id": _summary_artifact_actions,
    "_has_required_state": _summary_artifact_actions,
    "_get_brief_requirement_status": _summary_artifact_actions,
    "_get_brief_status": _summary_artifact_actions,
    "_summary_nested_dict_state": _summary_artifact_actions,
    "_read_artifact_options": _summary_artifact_actions,
    "_write_artifact_options": _summary_artifact_actions,
    "_read_artifact_change_request": _summary_artifact_actions,
    "_write_artifact_change_request": _summary_artifact_actions,
    "_artifact_current_fingerprint": _summary_artifact_actions,
    "_mark_artifact_current": _summary_artifact_actions,
    "_artifact_result_key": _summary_artifact_actions,
    "_artifact_has_result": _summary_artifact_actions,
    "_artifact_status_label": _summary_artifact_actions,
    "_build_artifact_status_rows": _summary_artifact_actions,
    "_resolve_next_best_action_recommendation": _summary_artifact_actions,
    "_resolve_next_best_action": _summary_artifact_actions,
    "_artifact_pipeline_status": _summary_artifact_actions,
    "_build_enrichment_timing_rows": _summary_artifact_actions,
    "_build_action_registry": _summary_artifact_actions,
    "_widget_key": _summary_view,
    "_append_template_blocks": _summary_view,
    "_render_template_toggles": _summary_view,
    "_build_selection_rows": _summary_view,
    "_collect_critical_gaps": _summary_view,
    "_selection_options_by_group": _summary_view,
    "_first_existing_group": _summary_view,
    "_render_guided_multiselect": _summary_view,
    "_build_job_ad_styleguide_text": _summary_view,
    "_build_job_ad_change_request_text": _summary_view,
    "_render_job_ad_settings_summary": _summary_view,
    "_render_pills_multiselect": _summary_view,
    "_render_selection_matrix": _summary_view,
    "_render_summary_hero": _summary_view,
    "_build_summary_headline": _summary_view,
    "_build_summary_subheader": _summary_view,
    "_render_summary_meta_badges": _summary_view,
    "_render_esco_coverage_kpis": _summary_view,
    "_render_summary_facts_column_overview": _summary_view,
    "_render_summary_facts_section": _summary_view,
    "_summary_fact_caption": _summary_view,
    "_render_summary_facts_table": _summary_view,
    "_render_summary_facts_matrix": _summary_view,
    "_render_summary_critical_gaps_table": _summary_view,
    "_default_job_ad_selected_values": _summary_view,
    "_append_distinct_text": _summary_view,
    "_build_fach_competency_suggestions": _summary_view,
    "_read_optional_text_upload": _summary_view,
    "_render_job_ad_compact_controls": _summary_view,
    "_render_interview_compact_controls": _summary_view,
    "_render_boolean_compact_controls": _summary_view,
    "_render_contract_compact_controls": _summary_view,
    "_render_summary_artifact_grid": _summary_view,
    "_render_action_card": _summary_view,
    "_render_job_ad_configuration_panel": _summary_view,
    "_render_primary_brief_card": _summary_view,
    "_render_follow_up_cards": _summary_view,
    "_render_export_bar": _summary_view,
    "_render_summary_dashboard_css": _summary_view,
    "_render_artifact_pipeline": _summary_view,
    "_render_summary_readiness_metrics": _summary_view,
    "_render_readiness_tab": _summary_view,
    "_render_readiness_dashboard_header": _summary_view,
    "_render_next_best_action_card": _summary_view,
    "_render_critical_gaps_card": _summary_view,
    "_render_artifact_launcher_cards": _summary_view,
    "_build_summary_tabs": _summary_view,
    "_render_summary_workspace_tabs": _summary_view,
    "_render_summary_processing_hub": _summary_view,
    "_is_warning_checklist_item": _summary_view,
    "_render_agg_checklist_review": _summary_view,
    "_render_job_ad_artifact": _summary_view,
    "_render_active_artifact": _summary_view,
    "_generated_summary_artifact_ids": _summary_view,
    "_resolve_output_artifact_id": _summary_view,
    "_render_artifact_result_switcher": _summary_view,
    "_render_artifact_refinement_box": _summary_view,
    "_current_boolean_search_pack": _summary_view,
    "_render_boolean_artifact_context_panels": _summary_view,
    "_render_summary_output_workspace": _summary_view,
    "_render_secondary_artifacts": _summary_view,
    "_render_summary_results_workspace": _summary_view,
    "_render_summary_export_workspace": _summary_view,
}.items():
    _SUMMARY_WRAPPERS[_summary_helper_name] = _make_summary_helper_wrapper(
        _summary_helper_module, _summary_helper_name
    )
    globals()[_summary_helper_name] = _SUMMARY_WRAPPERS[_summary_helper_name]
del _summary_helper_name, _summary_helper_module



def render(ctx: WizardContext) -> None:
    render_error_banner()
    ui_mode = get_current_ui_mode()
    is_advanced_mode = ui_mode == "expert"

    # SUMMARY_ZONE: GUARD_INIT
    vm = _build_summary_view_model()
    if vm is None:
        st.warning("Bitte zuerst im Start-Schritt eine Analyse durchführen.")
        st.button("Zur Startseite", on_click=lambda: ctx.goto("landing"))
        nav_buttons(ctx, disable_next=True)
        return

    current_summary_fingerprint = vm.artifacts.input_fingerprint
    StateStore(st.session_state).set_summary_freshness(
        input_fingerprint=current_summary_fingerprint,
        is_dirty=vm.artifacts.is_dirty,
    )

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
        show_errors: bool = True,
    ) -> bool:
        clear_error()
        store = bool(st.session_state.get(SSKey.STORE_API_OUTPUT.value, False))
        raw_company_website_research = st.session_state.get(
            SSKey.COMPANY_WEBSITE_RESEARCH.value
        )
        company_website_research: CompanyWebsiteResearch | None = None
        if raw_company_website_research not in (None, {}):
            try:
                normalized_company_website_research = (
                    _normalize_company_website_research_payload(
                        raw_company_website_research
                    )
                )
                company_website_research = CompanyWebsiteResearch.model_validate(
                    normalized_company_website_research
                )
                st.session_state[SSKey.COMPANY_WEBSITE_RESEARCH.value] = (
                    company_website_research.model_dump(mode="json")
                )
            except ValueError:
                if show_errors:
                    st.error(
                        "Die Firmen-Website-Research-Daten sind ungültig. "
                        "Bitte prüfe die Angaben im Unternehmensschritt und versuche es erneut."
                    )
                return False

        try:
            with st.spinner(spinner_text):
                brief, usage = generate_vacancy_brief(
                    vm.job,
                    vm.answers,
                    model=resolved_brief_model,
                    selected_role_tasks=vm.artifacts.selected_role_tasks,
                    selected_skills=vm.artifacts.selected_skills,
                    selected_benefits=vm.artifacts.selected_benefits,
                    company_website_research=company_website_research,
                    store=store,
                )
            st.session_state[SSKey.BRIEF.value] = brief.model_dump()
            brief_cached = usage_has_cache_hit(usage)
            st.session_state[SSKey.SUMMARY_CACHE_HIT.value] = brief_cached
            StateStore(st.session_state).mark_summary_brief_current(
                current_summary_fingerprint
            )
            st.session_state[SSKey.SUMMARY_LAST_MODE.value] = mode
            st.session_state[SSKey.SUMMARY_LAST_MODELS.value] = {
                "draft_model": resolved_brief_model
            }
            _record_artifact_generated_with_fact_usage(
                st.session_state,
                artifact_id="brief",
                cache_hit=brief_cached,
                mode=mode,
            )
            if brief_cached:
                st.info("Recruiting Brief aus dem Cache geladen.")
            return True
        except OpenAICallError as e:
            if show_errors:
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
        change_request = _read_artifact_change_request("job_ad") or str(
            st.session_state.get(SSKey.SUMMARY_CHANGE_REQUEST_TEXT.value, "")
        )
        logo_payload = _read_logo_payload()
        try:
            with st.spinner("Generiere zielgruppen-optimierte Stellenanzeige …"):
                result, usage = generate_custom_job_ad(
                    job=vm.job,
                    answers=vm.answers,
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
                logo_payload.get("name") if logo_payload else None
            )
            payload["logo"] = logo_payload
            payload["preview_options"] = _read_artifact_options("job_ad")
            st.session_state[SSKey.JOB_AD_DRAFT_CUSTOM.value] = payload
            st.session_state[SSKey.JOB_AD_LAST_USAGE.value] = usage or {}
            _mark_artifact_current(vm, "job_ad")
            st.session_state[SSKey.SUMMARY_ACTIVE_ARTIFACT.value] = "job_ad"
            _record_artifact_generated_with_fact_usage(
                st.session_state,
                artifact_id="job_ad",
                cache_hit=usage_has_cache_hit(usage),
            )
        except OpenAICallError as e:
            render_openai_error(e)
        except Exception as exc:
            handle_unexpected_exception(
                step="summary.job_ad_generation",
                exc=exc,
                error_type=type(exc).__name__,
                error_code="SUMMARY_JOB_AD_GENERATION_UNEXPECTED",
            )

    def _get_brief_status() -> tuple[str, VacancyBrief | None]:
        canonical_status = _resolve_canonical_brief_status(
            resolved_brief_model=resolved_brief_model
        )
        brief_payload = st.session_state.get(SSKey.BRIEF.value)
        if not isinstance(brief_payload, dict):
            return "missing", None
        try:
            brief = VacancyBrief.model_validate(brief_payload)
        except Exception:
            return "invalid", None
        if not canonical_status.ready_for_follow_ups:
            return "stale", brief
        return "ready", brief

    def _resolve_brief_for_follow_up_action() -> VacancyBrief:
        brief_status, brief_model = _get_brief_status()
        if brief_status == "ready":
            return brief_model
        generated = _run_generate_recruiting_brief(
            mode="internal_context",
            spinner_text="Bereite internen Kontext vor…",
            error_step="summary.internal_brief_context",
            show_errors=False,
        )
        if generated:
            _, generated_brief = _get_brief_status()
            if generated_brief is not None:
                return generated_brief
        return _build_internal_fallback_brief(vm)

    def _generate_interview_prep_hr() -> None:
        clear_error()
        brief_model = _resolve_brief_for_follow_up_action()
        try:
            store = bool(st.session_state.get(SSKey.STORE_API_OUTPUT.value, False))
            with st.spinner("Generiere Interview-Sheet (HR)…"):
                sheet, usage = generate_interview_sheet_hr(
                    brief=brief_model,
                    model=resolved_hr_sheet_model,
                    generation_options=_read_artifact_options("interview_hr"),
                    change_request=_read_artifact_change_request("interview_hr"),
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
            _mark_artifact_current(vm, "interview_hr")
            st.session_state[SSKey.SUMMARY_ACTIVE_ARTIFACT.value] = "interview_hr"
            _record_artifact_generated_with_fact_usage(
                st.session_state,
                artifact_id="interview_hr",
                cache_hit=usage_has_cache_hit(usage),
                mode="from_brief",
            )
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
        try:
            store = bool(st.session_state.get(SSKey.STORE_API_OUTPUT.value, False))
            with st.spinner("Generiere Interview-Sheet (Fachbereich)…"):
                sheet, usage = generate_interview_sheet_hm(
                    brief=brief_model,
                    model=resolved_fach_sheet_model,
                    generation_options=_read_artifact_options("interview_fach"),
                    change_request=_read_artifact_change_request("interview_fach"),
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
            _mark_artifact_current(vm, "interview_fach")
            st.session_state[SSKey.SUMMARY_ACTIVE_ARTIFACT.value] = "interview_fach"
            _record_artifact_generated_with_fact_usage(
                st.session_state,
                artifact_id="interview_fach",
                cache_hit=usage_has_cache_hit(usage),
                mode="from_brief",
            )
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
        try:
            store = bool(st.session_state.get(SSKey.STORE_API_OUTPUT.value, False))
            with st.spinner("Generiere Suchstrings…"):
                pack, usage = generate_boolean_search_pack(
                    brief=brief_model,
                    model=resolved_boolean_search_model,
                    generation_options=_read_artifact_options("boolean_search"),
                    change_request=_read_artifact_change_request("boolean_search"),
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
            _mark_artifact_current(vm, "boolean_search")
            st.session_state[SSKey.SUMMARY_ACTIVE_ARTIFACT.value] = "boolean_search"
            _record_artifact_generated_with_fact_usage(
                st.session_state,
                artifact_id="boolean_search",
                cache_hit=usage_has_cache_hit(usage),
                mode="from_brief",
            )
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
        try:
            store = bool(st.session_state.get(SSKey.STORE_API_OUTPUT.value, False))
            with st.spinner("Generiere Arbeitsvertragsvorlage…"):
                draft, usage = generate_employment_contract_draft(
                    brief=brief_model,
                    model=resolved_employment_contract_model,
                    generation_options=_read_artifact_options("employment_contract"),
                    change_request=_read_artifact_change_request("employment_contract"),
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
            _mark_artifact_current(vm, "employment_contract")
            st.session_state[SSKey.SUMMARY_ACTIVE_ARTIFACT.value] = "employment_contract"
            _record_artifact_generated_with_fact_usage(
                st.session_state,
                artifact_id="employment_contract",
                cache_hit=usage_has_cache_hit(usage),
                mode="from_brief",
            )
        except OpenAICallError as e:
            render_openai_error(e)
        except Exception as exc:
            handle_unexpected_exception(
                step="summary.employment_contract_generation",
                exc=exc,
                error_type=type(exc).__name__,
                error_code="SUMMARY_EMPLOYMENT_CONTRACT_GENERATION_UNEXPECTED",
            )

    def _render_job_ad_action_hub_inputs() -> None:
        rows = _build_selection_rows(vm.job, vm.answers)
        grouped_values = _selection_options_by_group(rows)
        critical_gaps = _collect_critical_gaps(vm.job, rows)
        selected_values: dict[str, list[str]] = {}

        st.markdown("#### 1. Ziel der Anzeige")
        preset = st.radio(
            "Wähle den Schwerpunkt für die erste Variante.",
            options=list(JOB_AD_PRESET_BLOCKS.keys()),
            index=0,
            format_func=lambda value: (
                f"{value} — {JOB_AD_PRESET_BLOCKS[value]['summary']}"
            ),
            key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, "job_ad.preset"),
        )

        st.markdown("#### 2. Inhalte auswählen")
        st.caption(
            "Die wichtigsten Inhalte werden vorausgewählt. Passe nur an, was in der Anzeige wirklich sichtbar sein soll."
        )
        _render_guided_multiselect(
            label="Wichtigste Aufgaben / Rollenbeschreibung",
            group_key=_first_existing_group(
                grouped_values,
                ("Rolle · Kurzbeschreibung", "Manager-Eingabe · role_tasks"),
            ),
            grouped=grouped_values,
            selected_values=selected_values,
            suffix="job_ad.guided.role",
            max_default=3,
        )
        _render_guided_multiselect(
            label="Wichtigste Anforderungen",
            group_key=_first_existing_group(
                grouped_values,
                ("Skills · Must-have", "Manager-Eingabe · must_have_skills"),
            ),
            grouped=grouped_values,
            selected_values=selected_values,
            suffix="job_ad.guided.must_have",
            max_default=5,
        )
        _render_guided_multiselect(
            label="Wichtigste Benefits",
            group_key=_first_existing_group(
                grouped_values,
                ("Benefits · Ausgewählter Benefit", "Benefits · Benefit"),
            ),
            grouped=grouped_values,
            selected_values=selected_values,
            suffix="job_ad.guided.benefits",
            max_default=5,
        )
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
        st.session_state[SSKey.SUMMARY_SELECTIONS.value] = selected_values

        st.markdown("#### 3. Sprache & Marke")
        style_col_a, style_col_b = st.columns(2)
        with style_col_a:
            address = st.selectbox(
                "Ansprache",
                options=list(JOB_AD_ADDRESS_BLOCKS.keys()),
                index=0,
                key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, "job_ad.address"),
            )
            tone = st.selectbox(
                "Tonalität",
                options=list(JOB_AD_TONE_BLOCKS.keys()),
                index=0,
                key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, "job_ad.tone"),
            )
        with style_col_b:
            length = st.selectbox(
                "Länge",
                options=list(JOB_AD_LENGTH_BLOCKS.keys()),
                index=0,
                key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, "job_ad.length"),
            )
            cta = st.selectbox(
                "CTA-Stärke",
                options=list(JOB_AD_CTA_BLOCKS.keys()),
                index=0,
                key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, "job_ad.cta"),
            )
        st.caption(
            "AGG-konforme, inklusive Sprache ist immer aktiv und kann nicht deaktiviert werden."
        )

        logo_file = st.file_uploader(
            "Logo-Upload (optional)",
            type=[
                extension.lstrip(".")
                for extension in SUMMARY_LOGO_UPLOAD_ALLOWED_EXTENSIONS
            ],
            help="Das Logo wird als Metadatum gespeichert und kann im Exportprozess weiterverwendet werden.",
            key=SSKey.SUMMARY_LOGO_UPLOAD_WIDGET.value,
        )
        normalized_logo = _normalize_logo_payload(logo_file)
        st.session_state[SSKey.SUMMARY_LOGO.value] = normalized_logo
        if logo_file is not None and normalized_logo is None:
            st.warning(
                "Logo kann nicht verwendet werden. Bitte PNG oder JPG/JPEG mit "
                "unterstützter Größe und gültigen Bilddaten verwenden."
            )
        if normalized_logo:
            st.image(
                normalized_logo["bytes"],
                caption=f"Verwendetes Firmenlogo: {normalized_logo.get('name', 'logo')}",
                width=180,
            )

        manual_styleguide_key = _widget_key(
            SSKey.SUMMARY_STYLEGUIDE_BLOCK_WIDGET_PREFIX, "manual"
        )
        if manual_styleguide_key not in st.session_state:
            st.session_state[manual_styleguide_key] = st.session_state.get(
                SSKey.SUMMARY_STYLEGUIDE_TEXT.value, ""
            )
        manual_styleguide = st.text_area(
            "Zusätzlicher Styleguide des Arbeitgebers (optional)",
            placeholder="z. B. Tonalität, Wording, No-Gos, Corporate Language, Du/Sie, Diversity-Hinweise …",
            key=manual_styleguide_key,
        )
        styleguide = _build_job_ad_styleguide_text(
            preset=preset,
            address=address,
            tone=tone,
            length=length,
            cta=cta,
            manual_styleguide=manual_styleguide,
        )
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
                "styleguide_uploaded": False,
            },
        )

        st.markdown("#### 4. Optimierung")
        optimization_picks = st.multiselect(
            "Was soll bei der nächsten Variante besonders verbessert werden?",
            options=list(JOB_AD_OPTIMIZATION_BLOCKS.keys()),
            default=[],
            key=_widget_key(
                SSKey.SUMMARY_CHANGE_REQUEST_BLOCK_WIDGET_PREFIX,
                "job_ad.optimization",
            ),
        )
        manual_change_request_key = _widget_key(
            SSKey.SUMMARY_CHANGE_REQUEST_BLOCK_WIDGET_PREFIX,
            "manual",
        )
        if manual_change_request_key not in st.session_state:
            st.session_state[manual_change_request_key] = st.session_state.get(
                SSKey.SUMMARY_CHANGE_REQUEST_TEXT.value, ""
            )
        manual_change_request = st.text_area(
            "Weitere Anpassungswünsche (optional)",
            placeholder="z. B. stärker auf Senior-Profile fokussieren, CTA kürzen, Benefits konkretisieren …",
            key=manual_change_request_key,
        )
        st.session_state[SSKey.SUMMARY_CHANGE_REQUEST_TEXT.value] = (
            _build_job_ad_change_request_text(
                optimization_picks=optimization_picks,
                manual_change_request=manual_change_request,
            )
        )

        _render_job_ad_settings_summary(
            preset=preset,
            address=address,
            length=length,
            selected_values=selected_values,
            critical_gaps=critical_gaps,
        )

        if critical_gaps:
            st.info(
                "Hinweis: Kritische Lücken werden in der AGG-Checkliste markiert und nicht halluziniert."
            )
        with st.expander("Quellen & Details prüfen", expanded=False):
            _render_selection_matrix(job=vm.job, answers=vm.answers)
        st.caption(f"Job-Ad-Modell: `{resolved_job_ad_model}`")

    action_registry = _build_action_registry(
        resolved_brief_model=resolved_brief_model,
        resolved_job_ad_model=resolved_job_ad_model,
        resolved_hr_sheet_model=resolved_hr_sheet_model,
        resolved_fach_sheet_model=resolved_fach_sheet_model,
        resolved_boolean_search_model=resolved_boolean_search_model,
        resolved_employment_contract_model=resolved_employment_contract_model,
        render_job_ad_inputs=_render_job_ad_action_hub_inputs
        if is_advanced_mode
        else None,
        follow_up_requirement_check=lambda: _get_brief_requirement_status(
            resolved_brief_model
        ),
        generate_recruiting_brief=_generate_recruiting_brief,
        generate_job_ad=_generate_job_ad,
        generate_interview_prep_hr=_generate_interview_prep_hr,
        generate_interview_prep_fach=_generate_interview_prep_fach,
        generate_boolean_search=_generate_boolean_search_pack,
        generate_employment_contract=_generate_employment_contract,
    )

    brief_dict = st.session_state.get(SSKey.BRIEF.value)
    brief: VacancyBrief | None = None
    if isinstance(brief_dict, dict):
        try:
            brief = VacancyBrief.model_validate(brief_dict)
        except Exception:
            brief = None

    internal_brief = brief or _build_internal_fallback_brief(vm)
    generator_by_id: dict[str, Callable[[], None]] = {
        "job_ad": _generate_job_ad,
        "interview_hr": _generate_interview_prep_hr,
        "interview_fach": _generate_interview_prep_fach,
        "boolean_search": _generate_boolean_search_pack,
        "employment_contract": _generate_employment_contract,
    }

    summary_copy = resolve_dynamic_step_copy(
        STEP_KEY_SUMMARY,
        job=vm.job,
        readiness_score=vm.status.readiness_percent,
        critical_gaps_count=len(_build_missing_critical_items(vm)),
    )
    render_output_header(
        summary_copy.headline,
        summary_copy.subheadline,
        meta_items=[("💡", "", summary_copy.value_line)]
        if summary_copy.value_line
        else (),
    )
    _render_readiness_dashboard_header(vm)
    _render_esco_coverage_kpis()
    _render_summary_critical_gaps_table(vm, ctx=ctx)
    render_live_artifact_preview_panel(
        key="summary",
        default_open=True,
        streamlit_module=st,
        preview_builder=lambda: build_live_artifact_preview_payload(
            job=vm.job,
            answers=vm.answers,
            selected_role_tasks=vm.artifacts.selected_role_tasks,
            selected_skills=vm.artifacts.selected_skills,
            selected_benefits=vm.artifacts.selected_benefits,
            intake_facts=get_intake_fact_state(st.session_state),
            interview_process=build_interview_export_payload(
                job=vm.job,
                answers=vm.answers,
                plan=vm.plan,
                internal_flow=normalize_interview_internal_flow(
                    st.session_state.get(SSKey.INTERVIEW_INTERNAL_FLOW.value, {})
                ),
            ),
        ),
    )
    _render_summary_artifact_grid(vm=vm, generator_by_id=generator_by_id)
    facts_workspace = (
        st.expander("Fakten je Schritt bearbeiten", expanded=False)
        if hasattr(st, "expander")
        else nullcontext()
    )
    with facts_workspace:
        _render_summary_facts_matrix(vm)
    _render_summary_output_workspace(
        vm=vm,
        brief=internal_brief,
        generator_by_id=generator_by_id,
    )

    nav_buttons(ctx, disable_next=True)


PAGE = WizardPage(
    key="summary",
    title_de="Zusammenfassung",
    icon="✅",
    render=render,
    requires_jobspec=True,
)
