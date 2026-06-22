# wizard_pages/summary_readiness.py
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
    STEP_SECTION_OPEN_QUESTIONS,
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
from question_dependencies import should_show_question
from question_limits import select_visible_questions_for_step_scope
from step_sections import get_step_fact_keys, get_step_section_for_fact
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
    _read_esco_match_explainability,
    _read_esco_skill_refs,
    _read_saved_selection_labels,
    _read_selected_esco_occupation,
    _show_semantic_esco_sections,
)

SUMMARY_FACT_OVERVIEW_COLUMNS = 3


SUMMARY_FACT_EMPTY_VALUES: Final[set[str]] = {
    "",
    "—",
    "Nicht angegeben",
    "Nicht beantwortet",
    "Nicht gesetzt",
    "Noch nicht generiert",
}


SUMMARY_FACT_STEP_ORDER: Final[tuple[str, ...]] = (
    STEP_KEY_COMPANY,
    STEP_KEY_ROLE_TASKS,
    STEP_KEY_SKILLS,
    STEP_KEY_BENEFITS,
    STEP_KEY_INTERVIEW,
)


SUMMARY_FACT_STEP_LABELS: Final[dict[str, str]] = {
    STEP_KEY_COMPANY: "Unternehmen",
    STEP_KEY_ROLE_TASKS: "Rolle & Aufgaben",
    STEP_KEY_SKILLS: "Skills & Anforderungen",
    STEP_KEY_BENEFITS: "Benefits & Rahmenbedingungen",
    STEP_KEY_INTERVIEW: "Interviewprozess",
}


SUMMARY_AREA_TO_STEP_KEY: Final[dict[str, str]] = {
    "Kernprofil": STEP_KEY_COMPANY,
    "Klassifikation": STEP_KEY_ROLE_TASKS,
    "Routing": STEP_KEY_COMPANY,
    "Unternehmen": STEP_KEY_COMPANY,
    "Team": STEP_KEY_COMPANY,
    "Rolle": STEP_KEY_ROLE_TASKS,
    "Rolle & Aufgaben": STEP_KEY_ROLE_TASKS,
    "Skills": STEP_KEY_SKILLS,
    "Benefits": STEP_KEY_BENEFITS,
    "Rechtliches": STEP_KEY_BENEFITS,
    "Legal": STEP_KEY_BENEFITS,
    "Zeitplan": STEP_KEY_INTERVIEW,
    "Timeline": STEP_KEY_INTERVIEW,
    "Timing": STEP_KEY_INTERVIEW,
    "Interview": STEP_KEY_INTERVIEW,
    "Kandidatenkommunikation": STEP_KEY_INTERVIEW,
    "Candidate Communication": STEP_KEY_INTERVIEW,
}


SUMMARY_FACT_DEFS_BY_KEY = {fact.fact_key.value: fact for fact in INTAKE_FACTS}
SUMMARY_SECTION_FACT_KEYS: Final[frozenset[FactKey]] = frozenset(
    fact_key
    for step_key in SUMMARY_FACT_STEP_ORDER
    for fact_key in get_step_fact_keys(step_key)
)


@dataclass(frozen=True)
class SummaryMeta:
    role_label: str
    company_label: str
    country_label: str
    selected_occupation_title: str
    readiness_items: list[tuple[str, str, bool]]


@dataclass(frozen=True)
class SummaryStatus:
    completion_ratio: float
    completion_text: str
    brief_state: str
    brief_status_label: str
    next_step: str
    readiness_percent: int
    ready_for_follow_ups: bool
    esco_ready: bool


@dataclass(frozen=True)
class SummaryArtifactState:
    brief: VacancyBrief | None
    selected_role_tasks: list[str]
    selected_skills: list[str]
    selected_benefits: list[str]
    input_fingerprint: str
    last_brief_fingerprint: str
    is_dirty: bool


@dataclass(frozen=True)
class CanonicalBriefStatus:
    state: str
    message: str
    cta_label: str
    ready_for_follow_ups: bool


@dataclass(frozen=True)
class SummaryViewModel:
    job: JobAdExtract
    answers: dict[str, Any]
    plan: QuestionPlan | None
    meta: SummaryMeta
    status: SummaryStatus
    fact_rows: list[SummaryFactsRow]
    artifacts: SummaryArtifactState


def _resolve_canonical_brief_status(
    *,
    resolved_brief_model: str | None,
    has_brief_prerequisites: bool = True,
    input_fingerprint: str | None = None,
    last_brief_fingerprint: str | None = None,
    is_dirty: bool | None = None,
) -> CanonicalBriefStatus:
    if not has_brief_prerequisites:
        return CanonicalBriefStatus(
            state="blocked",
            message="Brief-Grundlagen fehlen",
            cta_label="Recruiting Brief vorbereiten",
            ready_for_follow_ups=False,
        )

    brief_payload = st.session_state.get(SSKey.BRIEF.value)
    if not isinstance(brief_payload, dict):
        return CanonicalBriefStatus(
            state="missing",
            message="Kein Recruiting Brief vorhanden.",
            cta_label="Recruiting Brief erstellen",
            ready_for_follow_ups=False,
        )
    try:
        VacancyBrief.model_validate(brief_payload)
    except Exception:
        return CanonicalBriefStatus(
            state="invalid",
            message="Recruiting Brief ist ungültig.",
            cta_label="Recruiting Brief neu erstellen",
            ready_for_follow_ups=False,
        )

    dirty = (
        bool(st.session_state.get(SSKey.SUMMARY_DIRTY.value))
        if is_dirty is None
        else is_dirty
    )
    if dirty:
        return CanonicalBriefStatus(
            state="stale",
            message="Recruiting Brief ist veraltet.",
            cta_label="Recruiting Brief aktualisieren",
            ready_for_follow_ups=False,
        )

    last_models_raw = st.session_state.get(SSKey.SUMMARY_LAST_MODELS.value, {})
    last_models = last_models_raw if isinstance(last_models_raw, dict) else {}
    if resolved_brief_model and last_models.get("draft_model") != resolved_brief_model:
        return CanonicalBriefStatus(
            state="stale",
            message="Recruiting Brief ist veraltet.",
            cta_label="Recruiting Brief aktualisieren",
            ready_for_follow_ups=False,
        )

    current_input_fingerprint = str(
        input_fingerprint
        if input_fingerprint is not None
        else st.session_state.get(SSKey.SUMMARY_INPUT_FINGERPRINT.value, "") or ""
    )
    resolved_last_brief_fingerprint = str(
        last_brief_fingerprint
        if last_brief_fingerprint is not None
        else st.session_state.get(SSKey.SUMMARY_LAST_BRIEF_FINGERPRINT.value, "") or ""
    )
    if current_input_fingerprint and not resolved_last_brief_fingerprint:
        return CanonicalBriefStatus(
            state="stale",
            message="Recruiting Brief hat keinen aktuellen Eingabe-Snapshot.",
            cta_label="Recruiting Brief aktualisieren",
            ready_for_follow_ups=False,
        )
    if (
        current_input_fingerprint
        and resolved_last_brief_fingerprint
        and current_input_fingerprint != resolved_last_brief_fingerprint
    ):
        return CanonicalBriefStatus(
            state="stale",
            message="Recruiting Brief passt nicht mehr zu den aktuellen Eingaben.",
            cta_label="Recruiting Brief aktualisieren",
            ready_for_follow_ups=False,
        )

    return CanonicalBriefStatus(
        state="current",
        message="Aktueller Recruiting Brief vorhanden.",
        cta_label="Brief aktualisieren",
        ready_for_follow_ups=True,
    )


def _read_summary_confidence_threshold() -> float | None:
    preferences_raw = st.session_state.get(SSKey.UI_PREFERENCES.value, {})
    if not isinstance(preferences_raw, Mapping):
        return None
    try:
        return max(
            0.0,
            min(1.0, float(preferences_raw.get(UI_PREFERENCE_CONFIDENCE_THRESHOLD))),
        )
    except (TypeError, ValueError):
        return None


def _build_summary_completion_status(
    *,
    plan: QuestionPlan | None,
    answers: dict[str, Any],
    answer_meta: Mapping[str, Any],
    job_extract: JobAdExtract | None,
    intake_facts: Mapping[str, Any],
    intake_fact_evidence: Mapping[str, Any],
    confidence_threshold: float | None,
) -> tuple[float, str]:
    if plan is None:
        return 0.0, f"{len(answers)} Antworten"

    limits_raw = st.session_state.get(SSKey.QUESTION_LIMITS.value, {})
    question_limits = limits_raw if isinstance(limits_raw, dict) else None
    answered_questions = 0
    total_questions = 0
    for step in plan.steps:
        if step.step_key in NON_INTAKE_STEP_KEYS:
            continue
        questions = select_visible_questions_for_step_scope(
            step.questions,
            step_key=step.step_key,
            question_limits=question_limits,
            answers=answers,
            answer_meta=answer_meta,
            job_extract=job_extract,
            intake_facts=intake_facts,
            intake_fact_evidence=intake_fact_evidence,
            confidence_threshold=confidence_threshold,
            visibility_predicate=should_show_question,
        )
        status = build_step_status_payload(
            step=QuestionStep(
                step_key=step.step_key,
                title_de=step.title_de,
                description_de=step.description_de,
                questions=questions,
            ),
            answers=answers,
            answer_meta=answer_meta,
            should_show_question=should_show_question,
            step_key=step.step_key,
            job_extract=job_extract,
            intake_facts=intake_facts,
            intake_fact_evidence=intake_fact_evidence,
            confidence_threshold=confidence_threshold,
            visible_questions=questions,
        )
        answered_questions += status["answered"]
        total_questions += status["total"]

    if total_questions <= 0:
        return 0.0, f"{len(answers)} Antworten"
    return (
        answered_questions / total_questions,
        f"{answered_questions}/{total_questions} beantwortet",
    )


def _build_summary_fact_fingerprint_payload(
    *,
    intake_facts: Mapping[str, Any],
    intake_fact_evidence: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    fact_keys = sorted(
        {
            str(fact_key)
            for fact_key in [*intake_facts.keys(), *intake_fact_evidence.keys()]
            if str(fact_key).strip()
        }
    )
    resolution_state = build_intake_fact_resolution_state(
        st.session_state,
        fact_keys=fact_keys,
    )
    fingerprint_state: dict[str, dict[str, Any]] = {}
    stable_fields = ("status", "value", "source_type", "confidence", "confirmed")
    for fact_key in fact_keys:
        entry = resolution_state.get(fact_key)
        if not isinstance(entry, Mapping):
            continue
        stable_entry = {
            field_name: entry[field_name]
            for field_name in stable_fields
            if field_name in entry
        }
        if stable_entry:
            fingerprint_state[fact_key] = stable_entry
    return fingerprint_state


@dataclass(frozen=True)
class SummaryFactReadiness:
    total: int
    resolved: int
    partial: int
    open: int
    completion_ratio: float
    completion_text: str
    readiness_percent: int
    ready_for_follow_ups: bool


def _summary_fact_requirement_stage(row: SummaryFactsRow) -> FactRequirementStage | None:
    try:
        return FactRequirementStage(str(row.requirement_stage or "").strip())
    except ValueError:
        return None


def _is_critical_summary_fact_row(row: SummaryFactsRow) -> bool:
    return _summary_fact_requirement_stage(row) == FactRequirementStage.BEFORE_SUMMARY


def _summary_fact_resolution_status(row: SummaryFactsRow) -> FactResolutionStatus:
    raw_status = str(row.resolution_status or "").strip()
    if raw_status:
        try:
            return FactResolutionStatus(raw_status)
        except ValueError:
            pass
    if row.status == "Fehlend":
        return FactResolutionStatus.MISSING
    if row.status == "Teilweise":
        return FactResolutionStatus.ASSUMED
    return FactResolutionStatus.INFERRED


def _summary_fact_confidence_allows_readiness(
    row: SummaryFactsRow,
    *,
    intake_fact_evidence: Mapping[str, Any] | None,
    confidence_threshold: float | None,
) -> bool:
    if not row.fact_key:
        return True
    try:
        fact_key = FactKey(row.fact_key)
    except ValueError:
        return True
    return _summary_fact_allows_readiness(
        fact_key,
        intake_fact_evidence=intake_fact_evidence,
        confidence_threshold=confidence_threshold,
    )


def _summary_fact_readiness_bucket(
    row: SummaryFactsRow,
    *,
    intake_fact_evidence: Mapping[str, Any] | None,
    confidence_threshold: float | None,
) -> str:
    resolution_status = _summary_fact_resolution_status(row)
    if (
        row.status == "Fehlend"
        or resolution_status
        in {FactResolutionStatus.MISSING, FactResolutionStatus.CONFLICTED}
        or not _summary_fact_confidence_allows_readiness(
            row,
            intake_fact_evidence=intake_fact_evidence,
            confidence_threshold=confidence_threshold,
        )
    ):
        return "open"
    if row.status == "Teilweise" or resolution_status == FactResolutionStatus.ASSUMED:
        return "partial"
    if row.status in {"Vollständig", "Automatisch erkannt"} and resolution_status in {
        FactResolutionStatus.CONFIRMED,
        FactResolutionStatus.INFERRED,
    }:
        return "resolved"
    return "partial"


def _build_summary_fact_readiness(
    fact_rows: Sequence[SummaryFactsRow],
    *,
    intake_fact_evidence: Mapping[str, Any] | None,
    confidence_threshold: float | None,
) -> SummaryFactReadiness | None:
    critical_rows = [row for row in fact_rows if _is_critical_summary_fact_row(row)]
    total = len(critical_rows)
    if total <= 0:
        return None

    bucket_counts = {"resolved": 0, "partial": 0, "open": 0}
    for row in critical_rows:
        bucket = _summary_fact_readiness_bucket(
            row,
            intake_fact_evidence=intake_fact_evidence,
            confidence_threshold=confidence_threshold,
        )
        bucket_counts[bucket] += 1

    resolved = bucket_counts["resolved"]
    partial = bucket_counts["partial"]
    open_count = bucket_counts["open"]
    weighted_completed = resolved + (partial * 0.5)
    completion_ratio = weighted_completed / total
    completion_text = f"{resolved}/{total} kritische Fakten geklärt"
    if partial:
        completion_text = f"{completion_text}, {partial} teilweise"
    return SummaryFactReadiness(
        total=total,
        resolved=resolved,
        partial=partial,
        open=open_count,
        completion_ratio=completion_ratio,
        completion_text=completion_text,
        readiness_percent=round(completion_ratio * 100),
        ready_for_follow_ups=(resolved == total and partial == 0 and open_count == 0),
    )


def _build_summary_status(
    *,
    answers: dict[str, Any],
    meta: SummaryMeta,
    resolved_brief_model: str | None,
    plan: QuestionPlan | None = None,
    answer_meta: Mapping[str, Any] | None = None,
    job_extract: JobAdExtract | None = None,
    intake_facts: Mapping[str, Any] | None = None,
    intake_fact_evidence: Mapping[str, Any] | None = None,
    confidence_threshold: float | None = None,
    fact_rows: Sequence[SummaryFactsRow] | None = None,
    artifacts: SummaryArtifactState | None = None,
) -> SummaryStatus:
    esco_ready = bool(meta.selected_occupation_title)
    if plan is None:
        plan_payload = st.session_state.get(SSKey.QUESTION_PLAN.value)
        if isinstance(plan_payload, dict):
            try:
                plan = QuestionPlan.model_validate(plan_payload)
            except Exception:
                plan = None
    completion_ratio, completion_text = _build_summary_completion_status(
        plan=plan,
        answers=answers,
        answer_meta=answer_meta or {},
        job_extract=job_extract,
        intake_facts=intake_facts or {},
        intake_fact_evidence=intake_fact_evidence or {},
        confidence_threshold=confidence_threshold,
    )
    fact_readiness = (
        _build_summary_fact_readiness(
            fact_rows,
            intake_fact_evidence=intake_fact_evidence or {},
            confidence_threshold=confidence_threshold,
        )
        if fact_rows is not None
        else None
    )
    if fact_readiness is not None:
        completion_ratio = fact_readiness.completion_ratio
        completion_text = fact_readiness.completion_text

    brief_status = _resolve_canonical_brief_status(
        resolved_brief_model=resolved_brief_model,
        input_fingerprint=artifacts.input_fingerprint if artifacts else None,
        last_brief_fingerprint=artifacts.last_brief_fingerprint if artifacts else None,
        is_dirty=artifacts.is_dirty if artifacts else None,
    )
    brief_state = brief_status.state
    brief_status_label = brief_status.message
    next_step = "Gewünschtes Recruiting-Artefakt erzeugen"

    if fact_readiness is not None:
        readiness_percent = fact_readiness.readiness_percent
        ready_for_follow_ups = fact_readiness.ready_for_follow_ups
    else:
        readiness_checks = [
            bool(meta.role_label),
            bool(meta.company_label),
            bool(meta.country_label),
            esco_ready,
        ]
        readiness_percent = round(
            (sum(1 for item in readiness_checks if item) / len(readiness_checks)) * 100
        )
        ready_for_follow_ups = bool(meta.role_label)

    return SummaryStatus(
        completion_ratio=completion_ratio,
        completion_text=completion_text,
        brief_state=brief_state,
        brief_status_label=brief_status_label,
        next_step=next_step,
        readiness_percent=readiness_percent,
        ready_for_follow_ups=ready_for_follow_ups,
        esco_ready=esco_ready,
    )


def _build_summary_view_model() -> SummaryViewModel | None:
    job_dict = st.session_state.get(SSKey.JOB_EXTRACT.value)
    plan_dict = st.session_state.get(SSKey.QUESTION_PLAN.value)
    if not job_dict or not plan_dict:
        return None

    try:
        job = JobAdExtract.model_validate(job_dict)
    except Exception:
        return None
    answers = get_answers()
    try:
        plan = (
            QuestionPlan.model_validate(plan_dict)
            if isinstance(plan_dict, dict)
            else None
        )
    except Exception:
        plan = None

    selected_role_tasks = _read_saved_selection_labels(SSKey.ROLE_TASKS_SELECTED)
    selected_skills = _read_saved_selection_labels(SSKey.SKILLS_SELECTED)
    selected_benefits = _read_saved_selection_labels(SSKey.BENEFITS_SELECTED)
    answer_meta = get_answer_meta()
    intake_facts = get_intake_fact_state(st.session_state)
    intake_fact_evidence = get_intake_fact_evidence_state(st.session_state)
    confidence_threshold = _read_summary_confidence_threshold()
    meta = _build_summary_meta(
        job,
        intake_facts=intake_facts,
        intake_fact_evidence=intake_fact_evidence,
        confidence_threshold=confidence_threshold,
    )
    session_override = get_model_override()
    settings = load_openai_settings()
    resolved_brief_model = resolve_model_for_task(
        task_kind=TASK_GENERATE_VACANCY_BRIEF,
        session_override=session_override,
        settings=settings,
    )
    input_fingerprint = _build_summary_input_fingerprint(
        job=job,
        answers=answers,
        intake_facts=dict(intake_facts),
        intake_fact_resolution=_build_summary_fact_fingerprint_payload(
            intake_facts=intake_facts,
            intake_fact_evidence=intake_fact_evidence,
        ),
        confidence_threshold=confidence_threshold,
        selected_role_tasks=selected_role_tasks,
        selected_skills=selected_skills,
        selected_benefits=selected_benefits,
        esco_occupation_selected=_read_selected_esco_occupation(),
        esco_match_explainability=_read_esco_match_explainability(),
        esco_selected_skills_must=_read_esco_skill_refs(
            SSKey.ESCO_SKILLS_SELECTED_MUST
        ),
        esco_selected_skills_nice=_read_esco_skill_refs(
            SSKey.ESCO_SKILLS_SELECTED_NICE
        ),
    )
    artifacts = _build_summary_artifact_state(
        selected_role_tasks=selected_role_tasks,
        selected_skills=selected_skills,
        selected_benefits=selected_benefits,
        input_fingerprint=input_fingerprint,
    )
    fact_rows = _build_summary_fact_rows(
        job=job,
        answers=answers,
        plan=plan,
        artifacts=artifacts,
        meta=meta,
    )
    status = _build_summary_status(
        answers=answers,
        meta=meta,
        resolved_brief_model=resolved_brief_model,
        plan=plan,
        answer_meta=answer_meta,
        job_extract=job,
        intake_facts=intake_facts,
        intake_fact_evidence=intake_fact_evidence,
        confidence_threshold=confidence_threshold,
        fact_rows=fact_rows,
        artifacts=artifacts,
    )
    return SummaryViewModel(
        job=job,
        answers=answers,
        plan=plan,
        meta=meta,
        status=status,
        fact_rows=fact_rows,
        artifacts=artifacts,
    )


def _summary_fact_allows_readiness(
    fact_key: FactKey,
    *,
    intake_fact_evidence: Mapping[str, Any] | None,
    confidence_threshold: float | None,
) -> bool:
    if confidence_threshold is None:
        return True
    confidence = latest_fact_confidence(fact_key, intake_fact_evidence)
    return confidence is None or confidence >= confidence_threshold


def _resolve_summary_meta_value(
    fact_key: FactKey,
    fallback_value: Any,
    *,
    intake_facts: Mapping[str, Any] | None,
    intake_fact_evidence: Mapping[str, Any] | None,
    confidence_threshold: float | None,
) -> str:
    if isinstance(intake_facts, Mapping) and fact_key.value in intake_facts:
        fact_value = intake_facts.get(fact_key.value)
        has_value = _status_for_value(fact_value) != "Fehlend"
        if has_value and _summary_fact_allows_readiness(
            fact_key,
            intake_fact_evidence=intake_fact_evidence,
            confidence_threshold=confidence_threshold,
        ):
            return _format_summary_fact_value(fact_value).strip()
    return _format_summary_fact_value(fallback_value).strip()


def _build_summary_meta(
    job: JobAdExtract,
    *,
    intake_facts: Mapping[str, Any] | None = None,
    intake_fact_evidence: Mapping[str, Any] | None = None,
    confidence_threshold: float | None = None,
) -> SummaryMeta:
    selected_occupation = _read_selected_esco_occupation()
    return SummaryMeta(
        role_label=_resolve_summary_meta_value(
            FactKey.ROLE_JOB_TITLE,
            job.job_title,
            intake_facts=intake_facts,
            intake_fact_evidence=intake_fact_evidence,
            confidence_threshold=confidence_threshold,
        ),
        company_label=_resolve_summary_meta_value(
            FactKey.COMPANY_COMPANY_NAME,
            job.company_name,
            intake_facts=intake_facts,
            intake_fact_evidence=intake_fact_evidence,
            confidence_threshold=confidence_threshold,
        ),
        country_label=_resolve_summary_meta_value(
            FactKey.COMPANY_LOCATION_COUNTRY,
            job.location_country,
            intake_facts=intake_facts,
            intake_fact_evidence=intake_fact_evidence,
            confidence_threshold=confidence_threshold,
        ),
        selected_occupation_title=selected_occupation.get("title", ""),
        readiness_items=_build_country_readiness_items(job),
    )


def _build_summary_artifact_state(
    *,
    selected_role_tasks: list[str],
    selected_skills: list[str],
    selected_benefits: list[str],
    input_fingerprint: str,
) -> SummaryArtifactState:
    brief_dict = st.session_state.get(SSKey.BRIEF.value)
    brief_for_snapshot: VacancyBrief | None = None
    if isinstance(brief_dict, dict):
        try:
            brief_for_snapshot = VacancyBrief.model_validate(brief_dict)
        except Exception:
            brief_for_snapshot = None
    last_brief_fingerprint = str(
        st.session_state.get(SSKey.SUMMARY_LAST_BRIEF_FINGERPRINT.value, "") or ""
    )
    is_dirty = bool(
        last_brief_fingerprint and last_brief_fingerprint != input_fingerprint
    )
    return SummaryArtifactState(
        brief=brief_for_snapshot,
        selected_role_tasks=selected_role_tasks,
        selected_skills=selected_skills,
        selected_benefits=selected_benefits,
        input_fingerprint=input_fingerprint,
        last_brief_fingerprint=last_brief_fingerprint,
        is_dirty=is_dirty,
    )


def _build_internal_fallback_brief(vm: SummaryViewModel) -> VacancyBrief:
    job = vm.job
    role_title = str(job.job_title or vm.meta.role_label or "Rolle").strip() or "Rolle"
    company = str(job.company_name or vm.meta.company_label or "").strip()
    one_liner = f"{role_title} bei {company}" if company else role_title
    responsibilities = [
        str(item).strip()
        for item in [*vm.artifacts.selected_role_tasks, *list(job.responsibilities or [])]
        if str(item).strip()
    ][:6]
    must_have = [
        str(item).strip()
        for item in [*vm.artifacts.selected_skills, *list(job.must_have_skills or [])]
        if str(item).strip()
    ][:8]
    nice_to_have = [str(item).strip() for item in job.nice_to_have_skills or [] if str(item).strip()][:6]
    benefits = [str(item).strip() for item in vm.artifacts.selected_benefits if str(item).strip()]
    structured_data = VacancyStructuredData.model_validate(
        {
            "job_extract": job.model_dump(mode="json"),
            "answers": vm.answers,
            "selected_role_tasks": vm.artifacts.selected_role_tasks or None,
            "selected_skills": vm.artifacts.selected_skills or None,
            "selected_benefits": vm.artifacts.selected_benefits or None,
        }
    )
    return VacancyBrief(
        language="de",
        one_liner=one_liner,
        hiring_context="Aus den vorhandenen Intake-Daten abgeleiteter interner Kontext.",
        role_summary=str(job.role_overview or one_liner),
        top_responsibilities=responsibilities,
        must_have=must_have,
        nice_to_have=nice_to_have,
        dealbreakers=[],
        interview_plan=[
            str(step.name).strip()
            for step in job.recruitment_steps or []
            if str(step.name).strip()
        ],
        evaluation_rubric=[],
        sourcing_channels=[],
        risks_open_questions=[
            row.feld for row in vm.fact_rows if row.status in {"Fehlend", "Teilweise"}
        ][:8],
        job_ad_draft="\n".join(
            item
            for item in (
                one_liner,
                str(job.role_overview or "").strip(),
                "Benefits: " + ", ".join(benefits) if benefits else "",
            )
            if item
        ),
        structured_data=structured_data,
    )


def _build_country_readiness_items(job: JobAdExtract) -> list[tuple[str, str, bool]]:
    selected_occupation = get_esco_occupation_selected()
    show_esco_sections = _show_semantic_esco_sections()
    rows: list[tuple[str, str, bool]] = [
        (
            "Land vorhanden",
            job.location_country or "Nicht angegeben",
            bool(job.location_country),
        ),
    ]
    if show_esco_sections:
        rows.insert(
            1,
            (
                "Semantischer Anker bestätigt",
                "Ja" if selected_occupation else "Nein",
                bool(selected_occupation),
            ),
        )
    return rows


def _fallback_summary_source_type(row: SummaryFactsRow) -> str:
    source = str(row.quelle or "").strip().casefold()
    if "jobspec" in source:
        return FactSourceType.JOBSPEC.value
    manual_markers = ("intake", "antwort", "manual", "auswahl", "interview-step")
    if any(marker in source for marker in manual_markers):
        return FactSourceType.MANUAL.value
    if "homepage" in source or "website" in source:
        return FactSourceType.HOMEPAGE.value
    if "esco" in source:
        return FactSourceType.ESCO.value
    return ""


def _summary_row_provenance_label(
    row: SummaryFactsRow,
    *,
    fact_key: str,
) -> str:
    if row.provenienz:
        return row.provenienz
    evidence: Mapping[str, Any] = {}
    if fact_key:
        evidence_state = get_intake_fact_evidence_state(st.session_state)
        evidence_raw = evidence_state.get(fact_key)
        evidence = evidence_raw if isinstance(evidence_raw, Mapping) else {}
    fallback_resolution = row.resolution_status or _summary_fact_resolution_status(
        row
    ).value
    return _summary_provenance_label(
        evidence,
        fallback_source_type=_fallback_summary_source_type(row),
        fallback_source_label=row.quelle,
        fallback_resolution_status=fallback_resolution,
        confidence_threshold=_read_summary_confidence_threshold(),
    )


def _summary_step_key_for_area(area: str) -> str:
    return SUMMARY_AREA_TO_STEP_KEY.get(str(area or "").strip(), STEP_KEY_ROLE_TASKS)


def _with_summary_row_metadata(
    row: SummaryFactsRow,
    *,
    step_key: str | None = None,
    fact_key: FactKey | str | None = None,
    question_id: str = "",
    editable: bool | None = None,
    value_type: str = "text",
) -> SummaryFactsRow:
    resolved_fact_key = fact_key.value if isinstance(fact_key, FactKey) else (fact_key or "")
    resolved_step_key = step_key or row.step_key or _summary_step_key_for_area(row.bereich)
    resolved_editable = (
        bool(editable)
        if editable is not None
        else bool(resolved_fact_key or question_id or row.fact_key or row.question_id)
    )
    fact_def = SUMMARY_FACT_DEFS_BY_KEY.get(str(resolved_fact_key or row.fact_key or ""))
    provenance = _summary_row_provenance_label(
        row,
        fact_key=str(resolved_fact_key or row.fact_key or ""),
    )
    return replace(
        row,
        step_key=resolved_step_key,
        fact_key=str(resolved_fact_key or row.fact_key or ""),
        question_id=question_id or row.question_id,
        editable=resolved_editable,
        value_type=value_type or row.value_type,
        salary_impact=(
            fact_def.salary_impact.value if fact_def is not None else row.salary_impact
        ),
        requirement_stage=(
            fact_def.requirement_stage.value
            if fact_def is not None
            else row.requirement_stage
        ),
        website_enrichable=(
            fact_def.website_enrichable if fact_def is not None else row.website_enrichable
        ),
        provenienz=provenance,
    )


def _is_meaningful_summary_fact_row(row: SummaryFactsRow) -> bool:
    if row.bereich == "Artefakte":
        return False
    if row.status == "Fehlend":
        return False
    value = str(row.wert or "").strip()
    return value not in SUMMARY_FACT_EMPTY_VALUES


def _should_include_missing_summary_fact(fact_key: FactKey) -> bool:
    fact_def = SUMMARY_FACT_DEFS_BY_KEY.get(fact_key.value)
    if fact_def is None:
        return False
    if fact_key not in SUMMARY_SECTION_FACT_KEYS:
        return False
    return fact_def.requirement_stage == FactRequirementStage.BEFORE_SUMMARY


def _build_summary_fact_rows(
    *,
    job: JobAdExtract,
    answers: dict[str, Any],
    plan: QuestionPlan | None,
    artifacts: SummaryArtifactState,
    meta: SummaryMeta,
) -> list[SummaryFactsRow]:
    show_esco_sections = _show_semantic_esco_sections()
    intake_facts = get_intake_fact_state(st.session_state)
    intake_fact_evidence = get_intake_fact_evidence_state(st.session_state)
    rows: list[SummaryFactsRow] = [
        _with_summary_row_metadata(
            _summary_core_fact_row(
                label="Rolle",
                fact_key=FactKey.ROLE_JOB_TITLE,
                fallback_value=job.job_title,
                intake_facts=intake_facts,
                intake_fact_evidence=intake_fact_evidence,
            ),
            step_key=STEP_KEY_ROLE_TASKS,
            fact_key=FactKey.ROLE_JOB_TITLE,
        ),
        _with_summary_row_metadata(
            _summary_core_fact_row(
                label="Unternehmen",
                fact_key=FactKey.COMPANY_COMPANY_NAME,
                fallback_value=job.company_name,
                intake_facts=intake_facts,
                intake_fact_evidence=intake_fact_evidence,
            ),
            step_key=STEP_KEY_COMPANY,
            fact_key=FactKey.COMPANY_COMPANY_NAME,
        ),
        _with_summary_row_metadata(
            _summary_core_fact_row(
                label="Land",
                fact_key=FactKey.COMPANY_LOCATION_COUNTRY,
                fallback_value=job.location_country,
                intake_facts=intake_facts,
                intake_fact_evidence=intake_fact_evidence,
            ),
            step_key=STEP_KEY_COMPANY,
            fact_key=FactKey.COMPANY_LOCATION_COUNTRY,
        ),
        _with_summary_row_metadata(
            _summary_core_fact_row(
                label="Stadt",
                fact_key=FactKey.COMPANY_LOCATION_CITY,
                fallback_value=job.location_city,
                intake_facts=intake_facts,
                intake_fact_evidence=intake_fact_evidence,
            ),
            step_key=STEP_KEY_COMPANY,
            fact_key=FactKey.COMPANY_LOCATION_CITY,
        ),
    ]
    if show_esco_sections:
        rows.append(
            _with_summary_row_metadata(
                SummaryFactsRow(
                    "Klassifikation",
                    "Beruf (ESCO)",
                    meta.selected_occupation_title or "Nicht gesetzt",
                    "Jobspec-Prüfung",
                    _status_for_classification_value(meta.selected_occupation_title),
                ),
                step_key=STEP_KEY_ROLE_TASKS,
                editable=False,
            ),
        )
    for label, fact_key, fallback_value in (
        ("Homepage", FactKey.COMPANY_COMPANY_WEBSITE, job.company_website),
        ("Arbeitsort", FactKey.COMPANY_PLACE_OF_WORK, job.place_of_work),
        ("Remote-Regelung", FactKey.COMPANY_REMOTE_POLICY, job.remote_policy),
        ("Beschäftigungsart", FactKey.ROLE_EMPLOYMENT_TYPE, job.employment_type),
        ("Vertragsart", FactKey.ROLE_CONTRACT_TYPE, job.contract_type),
        ("Seniorität", FactKey.ROLE_SENIORITY_LEVEL, job.seniority_level),
        ("Startdatum", FactKey.INTERVIEW_START_DATE, job.start_date),
        (
            "Bewerbungsfrist",
            FactKey.INTERVIEW_APPLICATION_DEADLINE,
            job.application_deadline,
        ),
        (
            "Gehalt",
            FactKey.BENEFITS_SALARY_RANGE,
            job.salary_range.model_dump(mode="json")
            if job.salary_range is not None
            else None,
        ),
        ("Must-have-Skills", FactKey.SKILLS_MUST_HAVE_SKILLS, job.must_have_skills),
        (
            "Nice-to-have-Skills",
            FactKey.SKILLS_NICE_TO_HAVE_SKILLS,
            job.nice_to_have_skills,
        ),
        ("Sprachen", FactKey.SKILLS_LANGUAGES, job.languages),
    ):
        if (
            fact_key.value not in intake_facts
            and _status_for_value(fallback_value) == "Fehlend"
            and not _should_include_missing_summary_fact(fact_key)
        ):
            continue
        rows.append(
            _with_summary_row_metadata(
                _summary_core_fact_row(
                    label=label,
                    fact_key=fact_key,
                    fallback_value=fallback_value,
                    intake_facts=intake_facts,
                    intake_fact_evidence=intake_fact_evidence,
                ),
                fact_key=fact_key,
            )
        )
    for area, label, fact_key in (
        ("Routing", "Besetzungsanlass", FactKey.INTAKE_HIRING_REASON),
        ("Routing", "Dringlichkeit", FactKey.INTAKE_URGENCY),
        ("Routing", "Besetzungsvolumen", FactKey.INTAKE_HIRING_VOLUME),
        ("Routing", "Suchvertraulichkeit", FactKey.INTAKE_SEARCH_CONFIDENTIALITY),
        ("Routing", "Rollenreife", FactKey.INTAKE_ROLE_DEFINITION_MATURITY),
        ("Unternehmen", "Marke", FactKey.COMPANY_BRAND_NAME),
        ("Unternehmen", "Arbeitgeber-Pitch", FactKey.COMPANY_EMPLOYER_PITCH),
        ("Unternehmen", "Geschäftsbereich", FactKey.COMPANY_BUSINESS_UNIT),
        ("Unternehmen", "Rollenrelevante Positionierung", FactKey.COMPANY_ROLE_RELEVANT_POSITIONING),
        ("Unternehmen", "Arbeitsmodell", FactKey.COMPANY_WORK_ARRANGEMENT),
        ("Unternehmen", "Office-Tage pro Woche", FactKey.COMPANY_OFFICE_DAYS_PER_WEEK),
        ("Unternehmen", "Zulässige Regionen/Zeitzonen", FactKey.COMPANY_ALLOWED_REGIONS_TIMEZONES),
        ("Unternehmen", "Interne Sprache", FactKey.COMPANY_LANGUAGE_INTERNAL),
        ("Unternehmen", "Externe Sprache", FactKey.COMPANY_LANGUAGE_EXTERNAL),
        ("Unternehmen", "Nicht verhandelbar", FactKey.COMPANY_NON_NEGOTIABLES),
        ("Unternehmen", "Compliance-Kontext", FactKey.COMPANY_COMPLIANCE_CONTEXT),
        ("Unternehmen", "Tarifkontext", FactKey.COMPANY_TARIFF_CONTEXT),
        ("Unternehmen", "Abteilung", FactKey.COMPANY_DEPARTMENT_NAME),
        ("Unternehmen", "Berichtet an", FactKey.COMPANY_REPORTS_TO),
        ("Unternehmen", "Direkte Reports", FactKey.COMPANY_DIRECT_REPORTS_COUNT),
        ("Team", "Team", FactKey.TEAM_NAME),
        ("Team", "Führungsverantwortung", FactKey.TEAM_LEADERSHIP_SCOPE),
        ("Team", "Teamgröße", FactKey.TEAM_SIZE_DIRECT),
        ("Team", "Stakeholder", FactKey.TEAM_STAKEHOLDERS_PRIMARY),
        ("Team", "90-Tage Kontext", FactKey.TEAM_SUCCESS_CONTEXT_90D),
        ("Rolle", "Rollenüberblick", FactKey.ROLE_ROLE_OVERVIEW),
        ("Rolle", "Geschäftlicher Beitrag", FactKey.ROLE_BUSINESS_OUTCOME_PRIMARY),
        ("Rolle", "Aufgaben ab Tag 1", FactKey.ROLE_DAY1_RESPONSIBILITIES),
        ("Rolle", "Aufgaben später ausbaubar", FactKey.ROLE_EXPANSION_SCOPE),
        ("Rolle", "Lieferergebnisse", FactKey.ROLE_DELIVERABLES),
        ("Rolle", "Erfolgsmetriken", FactKey.ROLE_SUCCESS_METRICS),
        ("Rolle", "Priorisierte Aufgaben", FactKey.ROLE_RESPONSIBILITIES_PRIORITIZED),
        ("Rolle", "Erfolgstiming", FactKey.ROLE_SUCCESS_METRICS_TIMELINE),
        ("Rolle", "Entscheidungsspielraum", FactKey.ROLE_DECISION_SCOPE),
        ("Rolle", "12-Monats Erfolgssignale", FactKey.ROLE_YEAR1_SUCCESS_SIGNALS),
        ("Rolle", "Tech Stack", FactKey.ROLE_TECH_STACK),
        ("Rolle", "Domänen-Expertise", FactKey.ROLE_DOMAIN_EXPERTISE),
        ("Rolle", "Reise erforderlich", FactKey.ROLE_TRAVEL_REQUIRED),
        ("Rolle", "Reiseprofil", FactKey.ROLE_TRAVEL_PROFILE),
        ("Rolle", "Rufbereitschaft", FactKey.ROLE_ON_CALL),
        ("Rolle", "Onboarding-Hinweise", FactKey.ROLE_ONBOARDING_NOTES),
        ("Rolle", "Extraktionslücken", FactKey.ROLE_GAPS),
        ("Rolle", "Annahmen", FactKey.ROLE_ASSUMPTIONS),
        ("Skills", "Skill-Anforderungen", FactKey.SKILLS_ITEMS),
        ("Skills", "Soft Skills", FactKey.SKILLS_SOFT_SKILLS),
        ("Skills", "Ausbildung", FactKey.SKILLS_EDUCATION),
        ("Skills", "Zertifikate", FactKey.SKILLS_CERTIFICATIONS),
        ("Skills", "Skill-Timing", FactKey.SKILLS_READINESS_TIMING),
        ("Skills", "Freitext-Begründung", FactKey.SKILLS_FREE_TEXT_REASON),
        ("Skills", "KO-Kriterien", FactKey.SKILLS_KNOCKOUT_CRITERIA),
        ("Skills", "Trainierbare Skills", FactKey.SKILLS_TRAINABLE_SKILLS),
        ("Benefits", "Variable Vergütung", FactKey.BENEFITS_VARIABLE_PAY),
        ("Benefits", "Schicht-/Rufbereitschaftsausgleich", FactKey.BENEFITS_SHIFT_COMPENSATION),
        ("Benefits", "Tarif / Vorgaben", FactKey.BENEFITS_COLLECTIVE_AGREEMENT_CONTEXT),
        ("Benefits", "Angebotsbausteine", FactKey.BENEFITS_OFFER_COMPONENTS),
        ("Rechtliches", "Arbeitserlaubnis-Support", FactKey.LEGAL_WORK_AUTHORIZATION_SUPPORT),
        ("Zeitplan", "Startflexibilität", FactKey.TIMELINE_START_FLEXIBILITY),
        ("Interview", "Assessment-Evidenz", FactKey.INTERVIEW_ASSESSMENT_EVIDENCE),
        ("Interview", "Phasenverantwortliche", FactKey.INTERVIEW_STAGE_OWNERS),
        ("Interview", "Scorecard", FactKey.INTERVIEW_SCORECARD_TEMPLATE),
        ("Interview", "Kernfragen", FactKey.INTERVIEW_CORE_QUESTIONS),
        ("Interview", "Kandidaten-SLA", FactKey.INTERVIEW_COMMUNICATION_SLA),
        ("Interview", "Compliance-Hinweise", FactKey.INTERVIEW_COMPLIANCE_NOTES),
        ("Interview", "Kontaktpersonen", FactKey.INTERVIEW_CONTACTS),
    ):
        if fact_key.value not in intake_facts:
            if not _should_include_missing_summary_fact(fact_key):
                continue
            value = None
            evidence: Mapping[str, Any] = {}
        else:
            value = intake_facts.get(fact_key.value)
            evidence_raw = intake_fact_evidence.get(fact_key.value)
            evidence = evidence_raw if isinstance(evidence_raw, Mapping) else {}
        rows.append(
            _with_summary_row_metadata(
                SummaryFactsRow(
                    area,
                    label,
                    _format_summary_fact_value(value) or "Nicht angegeben",
                    _source_label_with_secondary_evidence(evidence, "Offen")
                    if _status_for_value(value) == "Fehlend"
                    else _source_label_with_secondary_evidence(
                        evidence, "Intake-Fakt"
                    ),
                    _status_for_value(value),
                    str(evidence.get("resolution_status") or "").strip(),
                ),
                step_key=_summary_step_key_for_area(area),
                fact_key=fact_key,
            )
        )
    if artifacts.selected_benefits:
        rows.append(
            _with_summary_row_metadata(
                SummaryFactsRow(
                    "Benefits",
                    "Ausgewählte Benefits",
                    " | ".join(artifacts.selected_benefits),
                    "Auswahl",
                    "Vollständig",
                ),
                step_key=STEP_KEY_BENEFITS,
                fact_key=FactKey.BENEFITS_BENEFITS,
            )
        )

    internal_flow = normalize_interview_internal_flow(
        st.session_state.get(SSKey.INTERVIEW_INTERNAL_FLOW.value, {})
    )
    candidate_stages = build_candidate_stage_values(
        job=job,
        answers=answers,
        plan=plan,
    )
    rows.append(
        _with_summary_row_metadata(
            SummaryFactsRow(
                "Interview",
                "Interviewphasen",
                " | ".join(candidate_stages) if candidate_stages else "Nicht beantwortet",
                "Jobspec" if job.recruitment_steps else "Intake-Antwort",
                _status_for_value(candidate_stages),
            ),
            step_key=STEP_KEY_INTERVIEW,
            fact_key=FactKey.INTERVIEW_RECRUITMENT_STEPS,
        )
    )

    interview_value_rows = build_interview_value_rows(
        job=job,
        answers=answers,
        plan=plan,
        internal_flow=internal_flow,
    )
    selected_ids = internal_flow["selected_value_ids"] or default_selected_interview_value_ids(
        interview_value_rows
    )
    selected_id_set = set(selected_ids)
    existing_fact_keys = {(row.bereich, row.feld, row.quelle) for row in rows}
    for value_row in interview_value_rows:
        if value_row["id"] not in selected_id_set:
            continue
        row_key = (
            value_row["Bereich"],
            value_row["Feld"],
            f"{value_row['Quelle']} / Interview-Wert",
        )
        if row_key in existing_fact_keys:
            continue
        rows.append(
            _with_summary_row_metadata(
                SummaryFactsRow(
                    value_row["Bereich"],
                    value_row["Feld"],
                    value_row["Wert"],
                    row_key[2],
                    value_row["Status"],
                ),
                step_key=_summary_step_key_for_area(value_row["Bereich"]),
                editable=False,
            )
        )
        existing_fact_keys.add(row_key)

    if plan is None:
        return rows

    seen_row_keys = {(row.bereich, row.feld, row.quelle) for row in rows}
    for step in plan.steps:
        if step.step_key in NON_INTAKE_STEP_KEYS:
            continue
        for question in step.questions:
            row_key = (step.title_de, question.label, "Intake-Antwort")
            if row_key in seen_row_keys:
                continue
            raw_value = answers.get(question.id)
            formatted = _format_summary_answer_value(question, raw_value)
            rows.append(
                _with_summary_row_metadata(
                    SummaryFactsRow(
                        step.title_de,
                        question.label,
                        formatted or "Nicht beantwortet",
                        "Intake-Antwort",
                        _status_for_answer_value(
                            question=question,
                            raw_value=raw_value,
                            formatted=formatted,
                        ),
                    ),
                    step_key=step.step_key,
                    fact_key=question.fact_key or "",
                    question_id=question.id,
                )
            )
            seen_row_keys.add(row_key)
    return rows


def _is_visible_summary_fact_row(row: Mapping[str, str]) -> bool:
    if str(row.get("Bereich", "")).strip() == "Artefakte":
        return False
    if str(row.get("Status", "")).strip() == "Fehlend":
        return False
    value = str(row.get("Wert", "")).strip()
    return value not in SUMMARY_FACT_EMPTY_VALUES


def _summary_fact_row_id(row: SummaryFactsRow) -> str:
    source = "|".join(
        (
            row.step_key,
            row.bereich,
            row.feld,
            row.fact_key,
            row.question_id,
            row.quelle,
        )
    )
    return hashlib.sha1(source.encode("utf-8")).hexdigest()[:12]


def _summary_visible_fact_rows(vm: SummaryViewModel) -> list[SummaryFactsRow]:
    return [row for row in vm.fact_rows if _is_meaningful_summary_fact_row(row)]


def _summary_fact_rows_by_step(
    rows: Sequence[SummaryFactsRow],
) -> dict[str, list[SummaryFactsRow]]:
    grouped = {step_key: [] for step_key in SUMMARY_FACT_STEP_ORDER}
    for row in rows:
        step_key = row.step_key or _summary_step_key_for_area(row.bereich)
        if step_key not in grouped:
            continue
        grouped[step_key].append(row)
    return grouped


def _apply_summary_fact_edits(
    *,
    edited_rows: list[dict[str, Any]],
    row_lookup: Mapping[str, SummaryFactsRow],
) -> bool:
    changed = False
    for edited_row in edited_rows:
        row_id = str(edited_row.get("_id") or "")
        source_row = row_lookup.get(row_id)
        if source_row is None or not source_row.editable:
            continue
        new_value = str(edited_row.get("Wert") or "").strip()
        old_value = str(source_row.wert or "").strip()
        if new_value == old_value:
            continue
        if source_row.question_id:
            set_answer(
                source_row.question_id,
                new_value,
                fact_key=source_row.fact_key or None,
            )
        elif source_row.fact_key:
            write_intake_fact(
                st.session_state,
                source_row.fact_key,
                new_value,
                source_type=FactSourceType.MANUAL,
                source_label="Summary edit",
                confirmed=True,
                resolution_status=FactResolutionStatus.CONFIRMED,
            )
        else:
            continue
        changed = True
    if changed:
        st.session_state[SSKey.SUMMARY_DIRTY.value] = True
    return changed


def _summary_gap_target_for_row(row: SummaryFactsRow, *, step_key: str) -> dict[str, str]:
    target_section = ""
    if row.question_id:
        target_section = STEP_SECTION_OPEN_QUESTIONS
    elif row.fact_key:
        target_section = get_step_section_for_fact(step_key, row.fact_key)
    return {
        "target_step": step_key,
        "target_section": target_section,
        "target_fact_key": row.fact_key,
        "target_question_id": row.question_id,
    }


def _build_summary_critical_gap_rows(vm: SummaryViewModel) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in vm.fact_rows:
        if (
            row.bereich == "Artefakte"
            or row.status not in {"Fehlend", "Teilweise"}
            or not _is_critical_summary_fact_row(row)
        ):
            continue
        step_key = row.step_key or _summary_step_key_for_area(row.bereich)
        if step_key not in SUMMARY_FACT_STEP_LABELS:
            continue
        reason = "Teilweise geklärt" if row.status == "Teilweise" else "Noch offen"
        target = _summary_gap_target_for_row(row, step_key=step_key)
        rows.append(
            {
                "_id": _summary_fact_row_id(row),
                "Schritt": SUMMARY_FACT_STEP_LABELS[step_key],
                "Feld": row.feld,
                "Status": row.status,
                "Pflichtigkeit": _display_requirement_stage(row.requirement_stage),
                "Provenienz": row.provenienz,
                "Aktion": f"{reason}: {row.feld} im Schritt „{SUMMARY_FACT_STEP_LABELS[step_key]}“ prüfen.",
                **target,
            }
        )
    return rows


def _build_missing_critical_items(vm: SummaryViewModel, *, limit: int = 5) -> list[str]:
    missing_rows = [
        row
        for row in vm.fact_rows
        if row.status == "Fehlend" and _is_critical_summary_fact_row(row)
    ]
    partial_rows = [
        row
        for row in vm.fact_rows
        if row.status == "Teilweise" and _is_critical_summary_fact_row(row)
    ]
    ordered_rows = [*missing_rows, *partial_rows]
    items: list[str] = []
    for row in ordered_rows:
        label = f"{row.bereich} · {row.feld}"
        if row.wert and row.wert not in {"Nicht angegeben", "—"}:
            label = f"{label} ({row.wert})"
        items.append(label)
        if len(items) >= limit:
            break
    return items
