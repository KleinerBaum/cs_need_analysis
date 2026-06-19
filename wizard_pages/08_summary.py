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
from step_status import build_step_status_payload
from components.design_system import (
    render_card_start,
    render_critical_gaps,
    render_next_best_action,
    render_output_header,
    render_pill,
)
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


class DocxPictureDocument(Protocol):
    def add_picture(self, image_path_or_stream: Any, width: Any = ...) -> Any: ...


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


class LogoPayload(TypedDict):
    name: str
    mime_type: str
    bytes: bytes


class EscoExportConcept(TypedDict):
    uri: str
    label: str


class EscoMatchExplainability(TypedDict, total=False):
    reason: str
    confidence: str
    provenance_categories: list[str]


class EscoSharedFields(TypedDict):
    selected_occupation_uri: str
    essential_skills: list[dict[str, Any]]
    optional_skills: list[dict[str, Any]]
    unmapped_terms: list[str]
    unmapped_roles: list[str]
    unmapped_actions: dict[str, Any]


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
    "Legal": STEP_KEY_BENEFITS,
    "Timeline": STEP_KEY_INTERVIEW,
    "Interview": STEP_KEY_INTERVIEW,
    "Candidate Communication": STEP_KEY_INTERVIEW,
}
SUMMARY_FACT_DEFS_BY_KEY = {fact.fact_key.value: fact for fact in INTAKE_FACTS}
SUMMARY_PRIMARY_ARTIFACT_IDS: Final[tuple[str, ...]] = (
    "job_ad",
    "interview",
    "boolean_search",
    "employment_contract",
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


def _widget_key(base_key: SSKey, suffix: str | None = None) -> str:
    if not suffix:
        return base_key.value
    return f"{base_key.value}.{suffix}"


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


def _session_list(key: SSKey, default: list[Any] | None = None) -> list[Any]:
    raw = st.session_state.get(key.value, default if default is not None else [])
    return raw if isinstance(raw, list) else []


def _session_dict(key: SSKey, default: dict[str, Any] | None = None) -> dict[str, Any]:
    raw = st.session_state.get(key.value, default if default is not None else {})
    return raw if isinstance(raw, dict) else {}


def _session_str(key: SSKey, default: str = "") -> str:
    return str(st.session_state.get(key.value, default) or "").strip()


def _read_esco_shared_fields() -> EscoSharedFields:
    selected_uri = _session_str(SSKey.ESCO_SELECTED_OCCUPATION_URI)
    essential_raw = _session_list(
        SSKey.ESCO_CONFIRMED_ESSENTIAL_SKILLS,
        default=_session_list(SSKey.ESCO_SKILLS_SELECTED_MUST),
    )
    optional_raw = _session_list(
        SSKey.ESCO_CONFIRMED_OPTIONAL_SKILLS,
        default=_session_list(SSKey.ESCO_SKILLS_SELECTED_NICE),
    )
    unmapped_raw = _session_list(SSKey.ESCO_UNMAPPED_REQUIREMENT_TERMS)
    unmapped_role_raw = _session_list(SSKey.ESCO_UNMAPPED_ROLE_TERMS)
    unmapped_actions_raw = _session_dict(SSKey.ESCO_UNMAPPED_TERM_ACTIONS)
    essential = essential_raw if isinstance(essential_raw, list) else []
    optional = optional_raw if isinstance(optional_raw, list) else []
    unmapped = (
        [str(item).strip() for item in unmapped_raw if str(item).strip()]
        if isinstance(unmapped_raw, list)
        else []
    )
    unmapped_roles = (
        [str(item).strip() for item in unmapped_role_raw if str(item).strip()]
        if isinstance(unmapped_role_raw, list)
        else []
    )
    return {
        "selected_occupation_uri": selected_uri,
        "essential_skills": essential,
        "optional_skills": optional,
        "unmapped_terms": unmapped,
        "unmapped_roles": unmapped_roles,
        "unmapped_actions": unmapped_actions_raw,
    }


def _read_esco_semantic_context() -> EscoSemanticContext:
    selected_occupation = get_esco_occupation_selected()
    if isinstance(selected_occupation, dict):
        anchor = normalize_anchor_ref(selected_occupation)
        if anchor is not None:
            st.session_state[SSKey.ESCO_PRIMARY_ANCHOR.value] = anchor
    return sync_esco_semantic_state(st.session_state)


def _show_semantic_esco_sections() -> bool:
    try:
        semantic_context = _read_esco_semantic_context()
    except Exception:
        semantic_context = None
    return bool(
        semantic_context is not None
        and semantic_context.can_use_semantic_exports
    ) or has_confirmed_esco_anchor()


def _count_skill_relation_traces(skills: list[dict[str, Any]]) -> int:
    relation_traces = 0
    for item in skills:
        if not isinstance(item, dict):
            continue
        if str(item.get("related_occupation_uri") or "").strip():
            relation_traces += 1
            continue
        skill_uri = str(item.get("uri") or "").strip()
        if not skill_uri:
            continue
        try:
            payload = EscoClient().get_skill_related_occupations(
                skill_uri=skill_uri, limit=1
            )
        except EscoClientError:
            continue
        if isinstance(payload, dict) and payload:
            relation_traces += 1
    return relation_traces


def _compute_esco_coverage_metrics(shared_esco: EscoSharedFields) -> dict[str, int]:
    job_extract = st.session_state.get(SSKey.JOB_EXTRACT.value, {})
    return _build_esco_coverage_metrics(
        job_extract_payload=job_extract,
        essential_skills=shared_esco.get("essential_skills", []),
        optional_skills=shared_esco.get("optional_skills", []),
    )


def _build_esco_mapping_report_rows() -> list[dict[str, str]]:
    report_payload = st.session_state.get(SSKey.ESCO_SKILLS_MAPPING_REPORT.value, {})
    try:
        report = EscoMappingReport.model_validate(report_payload)
    except Exception:
        report = EscoMappingReport(
            mapped_count=0, unmapped_terms=[], collisions=[], notes=[]
        )

    shared_esco = _read_esco_shared_fields()
    chosen_must = _to_esco_export_concepts(shared_esco["essential_skills"])
    chosen_nice = _to_esco_export_concepts(shared_esco["optional_skills"])
    chosen_concepts = chosen_must + chosen_nice

    by_label: defaultdict[str, list[EscoExportConcept]] = defaultdict(list)
    for concept in chosen_concepts:
        by_label[_normalize_skill_term(concept.get("label", ""))].append(concept)

    raw_terms = _extract_skills_step_raw_terms(
        st.session_state.get(SSKey.JOB_EXTRACT.value, {})
    )

    rows: list[dict[str, str]] = []
    linked_uris: set[str] = set()
    normalized_unmapped = {
        _normalize_skill_term(term): term
        for term in (
            shared_esco["unmapped_terms"]
            if shared_esco["unmapped_terms"]
            else report.unmapped_terms
        )
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


def _build_structured_export_payload(brief: VacancyBrief) -> dict[str, Any]:
    payload = dict(brief.structured_data.model_dump(mode="json", exclude_none=True))
    intake_facts = get_intake_fact_state(st.session_state)
    if intake_facts:
        payload["intake_facts"] = dict(intake_facts)
        session_structured_fields = {
            "skill_items": FactKey.SKILLS_ITEMS,
            "variable_pay": FactKey.BENEFITS_VARIABLE_PAY,
            "travel_profile": FactKey.ROLE_TRAVEL_PROFILE,
            "interview_scorecard_template": FactKey.INTERVIEW_SCORECARD_TEMPLATE,
        }
        for payload_key, fact_key in session_structured_fields.items():
            if payload.get(payload_key):
                continue
            value = intake_facts.get(fact_key.value)
            if value:
                payload[payload_key] = value
    intake_fact_evidence = get_intake_fact_evidence_state(st.session_state)
    if intake_fact_evidence:
        payload["intake_fact_evidence"] = dict(intake_fact_evidence)
    intake_fact_resolution = build_intake_fact_resolution_state(st.session_state)
    if intake_fact_resolution:
        payload["intake_fact_resolution"] = intake_fact_resolution
    try:
        export_job = JobAdExtract.model_validate(brief.structured_data.job_extract)
    except Exception:
        export_job = JobAdExtract()
    export_answers = dict(brief.structured_data.answers)
    plan_payload = st.session_state.get(SSKey.QUESTION_PLAN.value)
    export_plan: QuestionPlan | None = None
    if isinstance(plan_payload, dict):
        try:
            export_plan = QuestionPlan.model_validate(plan_payload)
        except Exception:
            export_plan = None
    payload["interview_process"] = build_interview_export_payload(
        job=export_job,
        answers=export_answers,
        plan=export_plan,
        internal_flow=normalize_interview_internal_flow(
            st.session_state.get(SSKey.INTERVIEW_INTERNAL_FLOW.value, {})
        ),
    )
    occupation_profile_raw = st.session_state.get(SSKey.OCCUPATION_PROFILE.value)
    if isinstance(occupation_profile_raw, dict):
        try:
            payload["occupation_context_profile"] = (
                OccupationContextProfile.model_validate(
                    occupation_profile_raw
                ).model_dump(mode="json", exclude_none=True)
            )
        except Exception:
            pass
    question_context_raw = st.session_state.get(SSKey.OCCUPATION_QUESTION_CONTEXT.value)
    if isinstance(question_context_raw, dict):
        try:
            payload["occupation_question_context"] = (
                OccupationQuestionContext.model_validate(
                    question_context_raw
                ).model_dump(mode="json", exclude_none=True)
            )
        except Exception:
            pass
    flow_provenance_raw = st.session_state.get(SSKey.QUESTION_FLOW_PROVENANCE.value)
    if isinstance(flow_provenance_raw, dict) and flow_provenance_raw:
        try:
            payload["question_flow_provenance"] = (
                QuestionFlowProvenance.model_validate(
                    flow_provenance_raw
                ).model_dump(mode="json", exclude_none=True)
            )
        except Exception:
            pass
    semantic_context = _read_esco_semantic_context()
    payload["semantic_export_mode"] = semantic_context.semantic_export_mode
    payload["esco_anchor_state"] = semantic_context.anchor_state
    if semantic_context.capability_snapshot is not None:
        payload["esco_capability_snapshot"] = (
            semantic_context.capability_snapshot.model_dump(
                mode="json",
                exclude_none=True,
            )
        )

    selected_occupation = get_esco_occupation_selected()
    if semantic_context.can_use_semantic_exports:
        if semantic_context.primary_anchor is not None:
            primary_anchor = semantic_context.primary_anchor.model_dump(
                mode="json",
                exclude_none=True,
            )
            payload["esco_primary_anchor"] = primary_anchor
            payload["esco_occupations"] = [
                {
                    "uri": semantic_context.primary_anchor.uri,
                    "label": semantic_context.primary_anchor.title,
                }
            ]
            explainability = _read_esco_match_explainability()
            if explainability:
                payload["esco_occupation_provenance"] = explainability
        elif isinstance(selected_occupation, dict):
            try:
                parsed_occupation = EscoConceptRef.model_validate(selected_occupation)
            except Exception:
                pass
            else:
                payload["esco_occupations"] = [
                    {"uri": parsed_occupation.uri, "label": parsed_occupation.title}
                ]
                explainability = _read_esco_match_explainability()
                if explainability:
                    payload["esco_occupation_provenance"] = explainability
        if semantic_context.secondary_anchors:
            payload["esco_secondary_anchors"] = [
                anchor.model_dump(mode="json", exclude_none=True)
                for anchor in semantic_context.secondary_anchors
            ]

        shared_esco = _read_esco_shared_fields()
        must_skills = _to_esco_export_concepts(shared_esco["essential_skills"])
        if must_skills:
            payload["esco_skills_must"] = must_skills

        nice_skills = _to_esco_export_concepts(shared_esco["optional_skills"])
        if nice_skills:
            payload["esco_skills_nice"] = nice_skills
        if shared_esco["unmapped_terms"]:
            payload["esco_unmapped_requirement_terms"] = shared_esco["unmapped_terms"]
        if shared_esco["unmapped_roles"]:
            payload["esco_unmapped_role_terms"] = shared_esco["unmapped_roles"]
        unresolved_decisions_raw = _session_list(SSKey.ESCO_UNRESOLVED_TERM_DECISIONS)
        if shared_esco["unmapped_actions"]:
            payload["esco_unmapped_term_actions"] = shared_esco["unmapped_actions"]
        unresolved_decisions: list[dict[str, Any]] = []
        if isinstance(unresolved_decisions_raw, list):
            for entry in unresolved_decisions_raw:
                if not isinstance(entry, dict):
                    continue
                try:
                    parsed = EscoUnresolvedTermDecision.model_validate(entry)
                except ValueError:
                    continue
                unresolved_decisions.append(
                    parsed.model_dump(mode="json", exclude_none=True)
                )
        if not unresolved_decisions and shared_esco["unmapped_actions"]:
            for raw_term, action_payload in shared_esco["unmapped_actions"].items():
                if not isinstance(action_payload, dict):
                    continue
                candidate = dict(action_payload)
                candidate.setdefault("raw_term", str(raw_term))
                try:
                    parsed = EscoUnresolvedTermDecision.model_validate(candidate)
                except ValueError:
                    continue
                unresolved_decisions.append(
                    parsed.model_dump(mode="json", exclude_none=True)
                )
        if unresolved_decisions:
            payload["esco_unresolved_term_decisions"] = unresolved_decisions

    esco_config = _session_dict(SSKey.ESCO_CONFIG)
    release_lane = str(
        esco_config.get("release_lane")
        or st.session_state.get(SSKey.ESCO_RELEASE_LANE.value)
        or ""
    ).strip()
    if release_lane:
        payload["esco_release_lane"] = release_lane
    selected_version = str(esco_config.get("selected_version") or "").strip()
    if selected_version:
        payload["esco_version"] = selected_version
    esco_source = str(st.session_state.get(SSKey.ESCO_LAST_DATA_SOURCE.value) or "").strip()
    if esco_source:
        payload["esco_data_source"] = esco_source
    data_source_mode = str(esco_config.get("data_source_mode") or "").strip()
    if data_source_mode:
        payload["esco_data_source_mode"] = data_source_mode
    if semantic_context.can_use_matrix_coverage:
        matrix_metadata = st.session_state.get(SSKey.ESCO_MATRIX_METADATA.value, {})
        matrix_loaded = bool(st.session_state.get(SSKey.ESCO_MATRIX_LOADED.value, False))
        if isinstance(matrix_metadata, dict) and (matrix_loaded or matrix_metadata):
            payload["esco_matrix"] = {
                "enabled": bool(
                    st.session_state.get(SSKey.ESCO_MATRIX_ENABLED.value, False)
                ),
                "loaded": matrix_loaded,
                "source": str(matrix_metadata.get("source") or "").strip(),
                "version": str(matrix_metadata.get("version") or "").strip(),
                "records": int(matrix_metadata.get("records") or 0),
            }
        matrix_coverage_rows_raw = _session_list(SSKey.ESCO_MATRIX_COVERAGE_ROWS)
        matrix_coverage_rows: list[dict[str, Any]] = []
        for row in matrix_coverage_rows_raw:
            if not isinstance(row, dict):
                continue
            try:
                matrix_coverage_rows.append(
                    EscoMatrixCoverageRow.model_validate(row).model_dump(mode="json")
                )
            except Exception:
                continue
        if matrix_coverage_rows:
            payload["esco_matrix_coverage"] = matrix_coverage_rows
            if isinstance(payload.get("esco_matrix"), dict):
                payload["esco_matrix"]["coverage_rows"] = len(matrix_coverage_rows)
        matrix_coverage_context = _session_dict(SSKey.ESCO_MATRIX_COVERAGE_CONTEXT)
        if matrix_coverage_context:
            context_payload = {
                "reason": str(matrix_coverage_context.get("reason") or "").strip(),
                "occupation_group": str(
                    matrix_coverage_context.get("occupation_group") or ""
                ).strip(),
                "rows": int(matrix_coverage_context.get("rows") or 0),
            }
            if any(context_payload.values()):
                payload["esco_matrix_coverage_context"] = context_payload

        title_variants_raw = _session_dict(SSKey.ESCO_OCCUPATION_TITLE_VARIANTS)
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

    selected_benefits = _read_saved_selection_labels(SSKey.BENEFITS_SELECTED)
    if selected_benefits:
        payload["selected_benefits"] = selected_benefits

    salary_forecast = st.session_state.get(SSKey.SALARY_FORECAST_LAST_RESULT.value)
    if isinstance(salary_forecast, dict):
        payload["salary_forecast"] = salary_forecast

    scenario_lab_rows = st.session_state.get(SSKey.SALARY_SCENARIO_LAB_ROWS.value)
    if isinstance(scenario_lab_rows, list):
        payload["salary_scenarios"] = scenario_lab_rows[:100]

    def _normalized_provenance_rows(raw_rows: Any) -> list[dict[str, Any]]:
        if not isinstance(raw_rows, list):
            return []
        rows: list[dict[str, Any]] = []
        for item in raw_rows:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or "").strip()
            if not label:
                continue
            row = {
                "label": label,
                "source_hint": str(item.get("source_hint") or "").strip(),
                "source_file": str(item.get("source_file") or "").strip(),
                "concept_uri": str(item.get("concept_uri") or item.get("uri") or "").strip(),
                "rationale": str(item.get("rationale") or "").strip(),
                "evidence": str(item.get("evidence") or "").strip(),
            }
            if not row["source_hint"]:
                source_text = str(item.get("source") or "").strip().casefold()
                row["source_hint"] = "esco_rag" if "rag" in source_text else "llm"
            rows.append(row)
        return rows

    role_task_suggestions = _normalized_provenance_rows(
        st.session_state.get(SSKey.ROLE_TASKS_LLM_SUGGESTED.value, [])
    )
    if role_task_suggestions:
        payload["role_task_suggestions"] = role_task_suggestions

    skill_suggestions = _normalized_provenance_rows(
        st.session_state.get(SSKey.SKILLS_LLM_SUGGESTED.value, [])
    )
    if skill_suggestions:
        payload["skill_suggestions"] = skill_suggestions

    benefit_suggestions = _normalized_provenance_rows(
        st.session_state.get(SSKey.BENEFITS_LLM_SUGGESTED.value, [])
    )
    if benefit_suggestions:
        payload["benefit_suggestions"] = benefit_suggestions
    return payload


def _build_brief_structured_preview_payload(brief: VacancyBrief) -> dict[str, Any]:
    export_payload = _build_structured_export_payload(brief)
    preview_keys = (
        "job_extract",
        "question_plan",
        "answers",
        "selected_role_tasks",
        "selected_skills",
        "selected_benefits",
    )
    return {
        key: export_payload[key]
        for key in preview_keys
        if key in export_payload
    }


def _read_saved_selection_labels(key: SSKey) -> list[str]:
    raw = st.session_state.get(key.value, [])
    if not isinstance(raw, list):
        return []
    values: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            continue
        label = item.strip()
        if label:
            values.append(label)
    return values


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


def _job_ad_to_docx_bytes(
    job_ad: JobAdGenerationResult,
    styleguide: str = "",
    *,
    logo_payload: LogoPayload | None = None,
) -> bytes:
    d = docx.Document()
    if logo_payload is None:
        logo_payload = _read_logo_payload()
    _add_logo_to_docx(document=d, logo_payload=logo_payload)
    d.add_heading(job_ad.headline or "Stellenanzeige", level=1)
    if any(
        (
            job_ad.intro.strip(),
            job_ad.responsibilities,
            job_ad.profile,
            job_ad.offer,
            job_ad.cta.strip(),
            job_ad.equal_opportunity_note.strip(),
        )
    ):
        if job_ad.intro.strip():
            d.add_paragraph(job_ad.intro.strip())
        for heading, items in (
            ("Deine Aufgaben", job_ad.responsibilities),
            ("Dein Profil", job_ad.profile),
            ("Was wir bieten", job_ad.offer),
        ):
            clean_items = _dedupe_preserve_order(items)
            if not clean_items:
                continue
            d.add_heading(heading, level=2)
            for item in clean_items:
                d.add_paragraph(item, style="List Bullet")
        if job_ad.cta.strip():
            d.add_paragraph(job_ad.cta.strip())
        if job_ad.equal_opportunity_note.strip():
            d.add_paragraph(job_ad.equal_opportunity_note.strip())
    else:
        d.add_paragraph(_build_publishable_job_ad_plain_text(job_ad))
    d.add_heading("Zielgruppe", level=2)
    for item in job_ad.target_group:
        d.add_paragraph(item, style="List Bullet")
    d.add_heading("AGG-Checkliste", level=2)
    for item in job_ad.agg_checklist:
        d.add_paragraph(item, style="List Bullet")
    bio = io.BytesIO()
    d.save(bio)
    return bio.getvalue()


def _job_ad_to_pdf_bytes(
    job_ad: JobAdGenerationResult,
    styleguide: str = "",
    *,
    logo_payload: LogoPayload | None = None,
) -> bytes | None:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.lib.utils import ImageReader
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import (
            Image,
            ListFlowable,
            ListItem,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
        )
    except Exception:
        return None

    bio = io.BytesIO()
    document = SimpleDocTemplate(
        bio,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=job_ad.headline or "Stellenanzeige",
        author="anonymous",
    )
    styles = getSampleStyleSheet()
    story: list[Any] = []

    if logo_payload is None:
        logo_payload = _read_logo_payload()
    if logo_payload is not None:
        logo_bytes = logo_payload.get("bytes")
        if isinstance(logo_bytes, bytes) and logo_bytes:
            image_stream = io.BytesIO(logo_bytes)
            try:
                image_width, image_height = ImageReader(image_stream).getSize()
                max_width = 4.2 * cm
                max_height = 1.8 * cm
                scale = min(max_width / image_width, max_height / image_height, 1)
                story.append(
                    Image(
                        io.BytesIO(logo_bytes),
                        width=image_width * scale,
                        height=image_height * scale,
                    )
                )
                story.append(Spacer(1, 0.5 * cm))
            except Exception:
                pass

    def _paragraph(value: str, style_name: str = "BodyText") -> Paragraph:
        return Paragraph(escape(value).replace("\n", "<br/>"), styles[style_name])

    def _append_heading(value: str, style_name: str = "Heading2") -> None:
        if value.strip():
            story.append(_paragraph(value.strip(), style_name))

    def _append_bullets(items: Sequence[str]) -> None:
        clean_items = _dedupe_preserve_order(list(items))
        if not clean_items:
            return
        story.append(
            ListFlowable(
                [
                    ListItem(_paragraph(item), leftIndent=0)
                    for item in clean_items
                ],
                bulletType="bullet",
                leftIndent=14,
            )
        )

    _append_heading(job_ad.headline or "Stellenanzeige", "Title")
    if any(
        (
            job_ad.intro.strip(),
            job_ad.responsibilities,
            job_ad.profile,
            job_ad.offer,
            job_ad.cta.strip(),
            job_ad.equal_opportunity_note.strip(),
        )
    ):
        if job_ad.intro.strip():
            story.append(_paragraph(job_ad.intro.strip()))
            story.append(Spacer(1, 0.25 * cm))
        for heading, items in (
            ("Deine Aufgaben", job_ad.responsibilities),
            ("Dein Profil", job_ad.profile),
            ("Was wir bieten", job_ad.offer),
        ):
            clean_items = _dedupe_preserve_order(items)
            if not clean_items:
                continue
            _append_heading(heading)
            _append_bullets(clean_items)
            story.append(Spacer(1, 0.2 * cm))
        for value in (job_ad.cta, job_ad.equal_opportunity_note):
            if value.strip():
                story.append(_paragraph(value.strip()))
                story.append(Spacer(1, 0.2 * cm))
    else:
        for paragraph in _build_publishable_job_ad_plain_text(job_ad).split("\n\n"):
            if paragraph.strip():
                story.append(_paragraph(paragraph.strip()))
                story.append(Spacer(1, 0.2 * cm))

    _append_heading("Zielgruppe")
    _append_bullets(job_ad.target_group)
    _append_heading("AGG-Checkliste")
    _append_bullets(job_ad.agg_checklist)
    document.build(story)
    return bio.getvalue()


def _brief_to_docx_bytes(brief: VacancyBrief) -> bytes:
    d = docx.Document()
    logo_payload = _read_logo_payload()
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


def _apply_interview_docx_brand_style(document: docx.Document, styleguide: str) -> None:
    normal = document.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = docx.shared.Pt(10.5)
    for style_name in ("Title", "Heading 1", "Heading 2", "Heading 3"):
        style = document.styles[style_name]
        style.font.name = "Arial"
    if styleguide.strip():
        for style_name in ("Heading 1", "Heading 2"):
            document.styles[style_name].font.color.rgb = docx.shared.RGBColor(
                31, 78, 121
            )


def _interview_prep_fach_to_docx_bytes(
    sheet: InterviewPrepSheetHiringManager,
    *,
    logo_payload: LogoPayload | None = None,
    styleguide: str = "",
) -> bytes:
    d = docx.Document()
    _apply_interview_docx_brand_style(d, styleguide)
    if logo_payload is None:
        logo_payload = _read_logo_payload()
    _add_logo_to_docx(document=d, logo_payload=logo_payload)
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


def _interview_prep_fach_to_pdf_bytes(
    sheet: InterviewPrepSheetHiringManager,
    *,
    logo_payload: LogoPayload | None = None,
    styleguide: str = "",
) -> bytes | None:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.lib.utils import ImageReader
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.colors import HexColor
        from reportlab.platypus import (
            Image,
            ListFlowable,
            ListItem,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
        )
    except Exception:
        return None

    bio = io.BytesIO()
    document = SimpleDocTemplate(
        bio,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="Interview Sheet (Fachbereich)",
        author="anonymous",
    )
    styles = getSampleStyleSheet()
    if styleguide.strip():
        styles["Heading1"].textColor = HexColor("#1F4E79")
        styles["Heading2"].textColor = HexColor("#1F4E79")
    story: list[Any] = []

    if logo_payload is None:
        logo_payload = _read_logo_payload()
    if logo_payload is not None:
        logo_bytes = logo_payload.get("bytes")
        if isinstance(logo_bytes, bytes) and logo_bytes:
            try:
                image_width, image_height = ImageReader(io.BytesIO(logo_bytes)).getSize()
                max_width = 4.2 * cm
                max_height = 1.8 * cm
                scale = min(max_width / image_width, max_height / image_height, 1)
                story.append(
                    Image(
                        io.BytesIO(logo_bytes),
                        width=image_width * scale,
                        height=image_height * scale,
                    )
                )
                story.append(Spacer(1, 0.5 * cm))
            except Exception:
                pass

    def _paragraph(value: str, style_name: str = "BodyText") -> Paragraph:
        return Paragraph(escape(value).replace("\n", "<br/>"), styles[style_name])

    def _heading(value: str, style_name: str = "Heading2") -> None:
        if value.strip():
            story.append(_paragraph(value.strip(), style_name))

    def _bullets(items: Sequence[str]) -> None:
        clean_items = _dedupe_preserve_order(
            [str(item).strip() for item in items if str(item).strip()]
        )
        if not clean_items:
            return
        story.append(
            ListFlowable(
                [ListItem(_paragraph(item), leftIndent=0) for item in clean_items],
                bulletType="bullet",
                leftIndent=14,
            )
        )

    _heading("Interview Sheet (Fachbereich)", "Title")
    story.append(_paragraph(f"Rolle: {sheet.role_title}"))
    story.append(_paragraph(f"Interview-Stage: {sheet.interview_stage}"))
    story.append(_paragraph(f"Dauer: {sheet.duration_minutes} Minuten"))
    story.append(Spacer(1, 0.25 * cm))

    _heading("Kompetenzen validieren")
    _bullets(sheet.competencies_to_validate)
    _heading("Frageblöcke")
    for block in sheet.question_blocks:
        _heading(block.title, "Heading3")
        story.append(_paragraph(f"Ziel: {block.objective}"))
        if block.questions:
            story.append(_paragraph("Fragen:"))
            _bullets(block.questions)
        if block.follow_up_prompts:
            story.append(_paragraph("Follow-ups:"))
            _bullets(block.follow_up_prompts)
    _heading("Technical Deep Dive")
    _bullets(sheet.technical_deep_dive_topics)
    _heading("Case/Task Prompt")
    story.append(_paragraph(sheet.case_or_task_prompt or "Kein Case/Task hinterlegt."))
    _heading("Bewertungsrubrik")
    for criterion in sheet.evaluation_rubric:
        _heading(criterion.title, "Heading3")
        story.append(_paragraph(criterion.description))
        story.append(_paragraph(f"Gewichtung: {criterion.weight_percent} %"))
        if criterion.score_scale:
            story.append(_paragraph(f"Skala: {' | '.join(criterion.score_scale)}"))
        _bullets(criterion.evidence_examples)
    _heading("Debrief-Fragen")
    _bullets(sheet.debrief_questions)

    document.build(story)
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


def _normalize_logo_payload(uploaded_logo: Any) -> LogoPayload | None:
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
        "bytes": bytes(raw_bytes),
    }


def _read_logo_payload() -> LogoPayload | None:
    raw_payload = st.session_state.get(SSKey.SUMMARY_LOGO.value)
    return _normalize_stored_logo_payload(raw_payload)


def _normalize_stored_logo_payload(raw_payload: Any) -> LogoPayload | None:
    if isinstance(raw_payload, dict):
        name = str(raw_payload.get("name") or "logo").strip() or "logo"
        mime_type = str(raw_payload.get("mime_type") or "").strip().lower()
        logo_bytes = raw_payload.get("bytes")
        if (
            mime_type in SUPPORTED_LOGO_MIME_TYPES
            and isinstance(logo_bytes, (bytes, bytearray))
            and logo_bytes
        ):
            return {"name": name, "mime_type": mime_type, "bytes": bytes(logo_bytes)}
        return None
    return _normalize_logo_payload(raw_payload)


def _job_ad_logo_payload(custom_job_ad_raw: Mapping[str, Any]) -> LogoPayload | None:
    if "logo" in custom_job_ad_raw:
        return _normalize_stored_logo_payload(custom_job_ad_raw.get("logo"))
    return _read_logo_payload()


def _add_logo_to_docx(
    document: DocxPictureDocument, logo_payload: LogoPayload | None
) -> bool:
    if logo_payload is None:
        return False
    logo_bytes = logo_payload.get("bytes")
    if not isinstance(logo_bytes, bytes):
        return False
    image_stream = io.BytesIO(bytes(logo_bytes))
    image_stream.seek(0)
    try:
        document.add_picture(image_stream, width=docx.shared.Cm(4.0))
    except Exception:
        return False
    return True


def _render_summary_hero(vm: SummaryViewModel) -> None:
    st.header(_build_summary_headline(vm.meta))
    st.markdown(_build_summary_subheader(vm.meta, vm.status))
    _render_summary_meta_badges(vm.meta, vm.status)


def _build_summary_headline(meta: SummaryMeta) -> str:
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
        "Die Vakanz ist inhaltlich bereit für Folge-Artefakte."
        if status.ready_for_follow_ups
        else "Die Vakanz ist noch nicht vollständig entscheidungsreif."
    )
    brief_clause = (
        "Der Recruiting Brief ist aktuell."
        if status.brief_state == "current"
        else status.brief_status_label
    )
    return (
        f"**Für {company} ist die Rolle {role} für den Zielmarkt {country} als klare Hiring-Story "
        "zusammengeführt.**\n\n"
        f"{readiness_intro} Aktueller Stand: **{status.completion_text}**, {brief_clause}\n\n"
        f"Die fachliche Verortung ist {mapping_status}, damit Übergaben an Sourcing, Interview und "
        "Angebotsphase konsistent bleiben.\n\n"
        f"**Empfohlener nächster Schritt:** {status.next_step}."
    )


def _render_summary_meta_badges(meta: SummaryMeta, status: SummaryStatus) -> None:
    readiness = (
        "Bereit"
        if status.ready_for_follow_ups
        else ("Veraltet" if status.brief_state == "stale" else "In Arbeit")
    )
    badges = (
        ("Rolle", meta.role_label or "Nicht angegeben"),
        ("Unternehmen", meta.company_label or "Nicht angegeben"),
        ("Land", meta.country_label or "Nicht angegeben"),
        ("ESCO", "✅" if status.esco_ready else "—"),
        ("Readiness", readiness),
    )
    columns = st.columns(len(badges))
    for idx, (label, value) in enumerate(badges):
        columns[idx].metric(label, str(value))


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


def _read_esco_skill_refs(key: SSKey) -> list[dict[str, str]]:
    raw_value = st.session_state.get(key.value, [])
    if not isinstance(raw_value, list):
        return []
    refs: list[dict[str, str]] = []
    for item in raw_value:
        if not isinstance(item, dict):
            continue
        uri = str(item.get("uri", "") or "").strip()
        title = str(item.get("title", "") or "").strip()
        if not uri and not title:
            continue
        refs.append({"uri": uri, "title": title})
    return refs


def _read_selected_esco_occupation() -> dict[str, str]:
    shared_esco = _read_esco_shared_fields()
    selected_occupation = get_esco_occupation_selected()
    if not isinstance(selected_occupation, dict):
        if shared_esco["selected_occupation_uri"]:
            return {"uri": shared_esco["selected_occupation_uri"], "title": ""}
        return {}
    return {
        "uri": shared_esco["selected_occupation_uri"]
        or str(selected_occupation.get("uri", "") or "").strip(),
        "title": str(selected_occupation.get("title", "") or "").strip(),
    }


def _read_esco_match_explainability() -> EscoMatchExplainability:
    reason_raw = st.session_state.get(SSKey.ESCO_MATCH_REASON.value)
    confidence_raw = st.session_state.get(SSKey.ESCO_MATCH_CONFIDENCE.value)
    provenance_raw = _session_list(SSKey.ESCO_MATCH_PROVENANCE)

    reason = str(reason_raw or "").strip()
    confidence = str(confidence_raw or "").strip()
    provenance = [str(item).strip() for item in provenance_raw if str(item).strip()]

    explainability: EscoMatchExplainability = {}
    if reason:
        explainability["reason"] = reason
    if confidence:
        explainability["confidence"] = confidence
    if provenance:
        explainability["provenance_categories"] = provenance
    return explainability


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


def _render_esco_coverage_kpis() -> None:
    shared_esco = _read_esco_shared_fields()
    coverage_metrics = _compute_esco_coverage_metrics(shared_esco)
    requirements_total = coverage_metrics["essential_total"] + coverage_metrics["optional_total"]
    unmapped_requirements = len(shared_esco.get("unmapped_terms", []))
    if requirements_total == 0 and unmapped_requirements == 0:
        st.info("Keine ESCO-RAG-Anforderungsdaten verfügbar.")
    else:
        st.caption("ESCO RAG Coverage: kompakte KPI-Übersicht zur Anforderungsabdeckung")
        kpis = _build_esco_coverage_kpis(
            metrics=coverage_metrics,
            unmapped_requirements_count=unmapped_requirements,
        )
        columns = st.columns(4)
        for idx, (label, value) in enumerate(kpis):
            columns[idx].metric(label=label, value=str(value))


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
        parts.append("Second Source: Website-Review")
    return " · ".join(parts)


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
                    "Jobspec-Review",
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
        ("Must-have Skills", FactKey.SKILLS_MUST_HAVE_SKILLS, job.must_have_skills),
        (
            "Nice-to-have Skills",
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
        ("Unternehmen", "Brand", FactKey.COMPANY_BRAND_NAME),
        ("Unternehmen", "Employer Pitch", FactKey.COMPANY_EMPLOYER_PITCH),
        ("Unternehmen", "Business Unit", FactKey.COMPANY_BUSINESS_UNIT),
        ("Unternehmen", "Rollenrelevante Positionierung", FactKey.COMPANY_ROLE_RELEVANT_POSITIONING),
        ("Unternehmen", "Arbeitsmodell", FactKey.COMPANY_WORK_ARRANGEMENT),
        ("Unternehmen", "Office-Tage pro Woche", FactKey.COMPANY_OFFICE_DAYS_PER_WEEK),
        ("Unternehmen", "Zulaessige Regionen/Zeitzonen", FactKey.COMPANY_ALLOWED_REGIONS_TIMEZONES),
        ("Unternehmen", "Interne Sprache", FactKey.COMPANY_LANGUAGE_INTERNAL),
        ("Unternehmen", "Externe Sprache", FactKey.COMPANY_LANGUAGE_EXTERNAL),
        ("Unternehmen", "Nicht verhandelbar", FactKey.COMPANY_NON_NEGOTIABLES),
        ("Unternehmen", "Compliance-Kontext", FactKey.COMPANY_COMPLIANCE_CONTEXT),
        ("Unternehmen", "Tarifkontext", FactKey.COMPANY_TARIFF_CONTEXT),
        ("Unternehmen", "Abteilung", FactKey.COMPANY_DEPARTMENT_NAME),
        ("Unternehmen", "Berichtet an", FactKey.COMPANY_REPORTS_TO),
        ("Unternehmen", "Direkte Reports", FactKey.COMPANY_DIRECT_REPORTS_COUNT),
        ("Team", "Team", FactKey.TEAM_NAME),
        ("Team", "Leadership Scope", FactKey.TEAM_LEADERSHIP_SCOPE),
        ("Team", "Teamgröße", FactKey.TEAM_SIZE_DIRECT),
        ("Team", "Stakeholder", FactKey.TEAM_STAKEHOLDERS_PRIMARY),
        ("Team", "90-Tage Kontext", FactKey.TEAM_SUCCESS_CONTEXT_90D),
        ("Rolle", "Rollenüberblick", FactKey.ROLE_ROLE_OVERVIEW),
        ("Rolle", "Business Outcome", FactKey.ROLE_BUSINESS_OUTCOME_PRIMARY),
        ("Rolle", "Day-1 Aufgaben", FactKey.ROLE_DAY1_RESPONSIBILITIES),
        ("Rolle", "Aufgaben später ausbaubar", FactKey.ROLE_EXPANSION_SCOPE),
        ("Rolle", "Deliverables", FactKey.ROLE_DELIVERABLES),
        ("Rolle", "Erfolgsmetriken", FactKey.ROLE_SUCCESS_METRICS),
        ("Rolle", "Priorisierte Aufgaben", FactKey.ROLE_RESPONSIBILITIES_PRIORITIZED),
        ("Rolle", "Success Timeline", FactKey.ROLE_SUCCESS_METRICS_TIMELINE),
        ("Rolle", "Decision Scope", FactKey.ROLE_DECISION_SCOPE),
        ("Rolle", "12-Monats Erfolgssignale", FactKey.ROLE_YEAR1_SUCCESS_SIGNALS),
        ("Rolle", "Tech Stack", FactKey.ROLE_TECH_STACK),
        ("Rolle", "Domänen-Expertise", FactKey.ROLE_DOMAIN_EXPERTISE),
        ("Rolle", "Reise erforderlich", FactKey.ROLE_TRAVEL_REQUIRED),
        ("Rolle", "Reiseprofil", FactKey.ROLE_TRAVEL_PROFILE),
        ("Rolle", "Rufbereitschaft", FactKey.ROLE_ON_CALL),
        ("Rolle", "Onboarding Notes", FactKey.ROLE_ONBOARDING_NOTES),
        ("Rolle", "Extraktionslücken", FactKey.ROLE_GAPS),
        ("Rolle", "Annahmen", FactKey.ROLE_ASSUMPTIONS),
        ("Skills", "Skill Items", FactKey.SKILLS_ITEMS),
        ("Skills", "Soft Skills", FactKey.SKILLS_SOFT_SKILLS),
        ("Skills", "Ausbildung", FactKey.SKILLS_EDUCATION),
        ("Skills", "Zertifikate", FactKey.SKILLS_CERTIFICATIONS),
        ("Skills", "Skill Timing", FactKey.SKILLS_READINESS_TIMING),
        ("Skills", "Free-Text Begründung", FactKey.SKILLS_FREE_TEXT_REASON),
        ("Skills", "KO-Kriterien", FactKey.SKILLS_KNOCKOUT_CRITERIA),
        ("Skills", "Trainierbare Skills", FactKey.SKILLS_TRAINABLE_SKILLS),
        ("Benefits", "Variable Vergütung", FactKey.BENEFITS_VARIABLE_PAY),
        ("Benefits", "Schicht-/Rufbereitschaftsausgleich", FactKey.BENEFITS_SHIFT_COMPENSATION),
        ("Benefits", "Tarif / Vorgaben", FactKey.BENEFITS_COLLECTIVE_AGREEMENT_CONTEXT),
        ("Benefits", "Offer-Komponenten", FactKey.BENEFITS_OFFER_COMPONENTS),
        ("Legal", "Work Authorization", FactKey.LEGAL_WORK_AUTHORIZATION_SUPPORT),
        ("Timeline", "Startflexibilität", FactKey.TIMELINE_START_FLEXIBILITY),
        ("Interview", "Assessment Evidence", FactKey.INTERVIEW_ASSESSMENT_EVIDENCE),
        ("Interview", "Stage Owner", FactKey.INTERVIEW_STAGE_OWNERS),
        ("Interview", "Scorecard", FactKey.INTERVIEW_SCORECARD_TEMPLATE),
        ("Interview", "Kernfragen", FactKey.INTERVIEW_CORE_QUESTIONS),
        ("Interview", "Candidate SLA", FactKey.INTERVIEW_COMMUNICATION_SLA),
        ("Interview", "Compliance Notes", FactKey.INTERVIEW_COMPLIANCE_NOTES),
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
                "Second Source": st.column_config.TextColumn("Second Source"),
            },
        )


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
                            "Website-Review" if row.website_enrichable else ""
                        ),
                    }
                    for row_id, row in row_lookup.items()
                ]
                data_editor = getattr(st, "data_editor", None)
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
                            "Feld": st.column_config.TextColumn("Angabe", disabled=True),
                            "Wert": st.column_config.TextColumn("Inhalt"),
                            "Quelle": st.column_config.TextColumn("Quelle", disabled=True),
                            "Salary": st.column_config.TextColumn("Salary", disabled=True),
                            "Pflichtigkeit": st.column_config.TextColumn(
                                "Pflichtigkeit",
                                disabled=True,
                            ),
                            "Second Source": st.column_config.TextColumn(
                                "Second Source",
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
                            "Pflichtigkeit": st.column_config.TextColumn("Pflichtigkeit"),
                            "Second Source": st.column_config.TextColumn("Second Source"),
                        },
                    )
                    edited = editor_rows
                editable_count = sum(1 for row in rows if row.editable)
                if st.button(
                    "Änderungen speichern",
                    key=_widget_key(
                        SSKey.SUMMARY_ACTION_WIDGET_PREFIX,
                        f"facts.save.{step_key}",
                    ),
                    width="stretch",
                    disabled=editable_count == 0,
                ):
                    if _apply_summary_fact_edits(
                        edited_rows=list(edited),
                        row_lookup=row_lookup,
                    ):
                        st.success("Änderungen gespeichert.")
                        st.rerun()
                    else:
                        st.info("Keine Änderungen erkannt.")


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
        rows.append(
            {
                "Schritt": SUMMARY_FACT_STEP_LABELS[step_key],
                "Feld": row.feld,
                "Status": row.status,
                "Pflichtigkeit": _display_requirement_stage(row.requirement_stage),
                "Aktion": f"{reason}: {row.feld} im Schritt „{SUMMARY_FACT_STEP_LABELS[step_key]}“ prüfen.",
            }
        )
    return rows


def _render_summary_critical_gaps_table(vm: SummaryViewModel) -> None:
    st.markdown("### Kritische Lücken")
    gap_rows = _build_summary_critical_gap_rows(vm)
    if not gap_rows:
        st.success("Keine kritischen Lücken erkannt.")
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
        "employment_contract": SSKey.EMPLOYMENT_CONTRACT_DRAFT,
    }.get(artifact_id)


def _artifact_has_result(artifact_id: str) -> bool:
    result_key = _artifact_result_key(artifact_id)
    return bool(result_key and st.session_state.get(result_key.value))


def _artifact_status_label(vm: SummaryViewModel, artifact_id: str) -> tuple[str, str]:
    if not _artifact_has_result(artifact_id):
        return "open", "Offen"
    fingerprints = _summary_nested_dict_state(SSKey.SUMMARY_ARTIFACT_FINGERPRINTS)
    stored = str(fingerprints.get(artifact_id) or "")
    if not stored and vm.artifacts.input_fingerprint:
        return "stale", "Veraltet"
    if stored and stored != _artifact_current_fingerprint(vm, artifact_id):
        return "stale", "Veraltet"
    return "current", "Aktuell"


def _default_job_ad_selected_values(vm: SummaryViewModel) -> dict[str, list[str]]:
    rows = _build_selection_rows(vm.job, vm.answers)
    grouped_values = _selection_options_by_group(rows)
    selected_values: dict[str, list[str]] = {}
    for group_key, max_items in (
        (_first_existing_group(grouped_values, ("Rolle · Kurzbeschreibung", "Manager-Input · role_tasks")), 3),
        (_first_existing_group(grouped_values, ("Skills · Must-have", "Manager-Input · must_have_skills")), 5),
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
        type=["png", "jpg", "jpeg"],
        key=SSKey.SUMMARY_LOGO_UPLOAD_WIDGET.value,
    )
    normalized_logo = _normalize_logo_payload(logo_file)
    st.session_state[SSKey.SUMMARY_LOGO.value] = normalized_logo
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
            "Stage",
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
            options=["Kultur & Motivation", "Must-haves", "Deep Dive", "Scorecard"],
            index=1,
            key=_widget_key(SSKey.SUMMARY_ACTION_WIDGET_PREFIX, "interview.focus"),
        )
        depth = st.selectbox(
            "Bewertung",
            options=["kompakt", "standard", "detailliert"],
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
    st.caption("Legal Review bleibt erforderlich; der Output ist nur ein Template-Draft.")
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


def _render_summary_artifact_grid(
    *,
    vm: SummaryViewModel,
    generator_by_id: Mapping[str, Callable[[], None]],
) -> None:
    st.markdown("### Artefakte")
    st.caption("Wähle ein Output, schärfe die wichtigsten Einflussfaktoren und generiere direkt aus den aktuellen Daten.")
    specs: list[dict[str, Any]] = [
        {
            "id": "job_ad",
            "title": "Job-Ad-Generator",
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
            "title": "Boolean Search",
            "description": "Kanal-spezifische Suchstrings für aktive Sourcing-Recherche.",
            "controls": _render_boolean_compact_controls,
            "cta": "Boolean Search erstellen",
        },
        {
            "id": "employment_contract",
            "title": "Arbeitsvertrag",
            "description": "Template-Draft mit Platzhaltern und Review-Hinweisen.",
            "controls": _render_contract_compact_controls,
            "cta": "Arbeitsvertrag erstellen",
        },
        {
            "id": "reserved_export",
            "title": "Weitere Exportformate",
            "description": "Reserviert für zusätzliche Download-Workflows.",
        },
        {
            "id": "reserved_templates",
            "title": "Weitere Vorlagen",
            "description": "Reserviert für künftige Hiring-Team-Artefakte.",
        },
    ]
    for row_start in range(0, len(specs), 3):
        columns = st.columns(3, gap="medium")
        for column, spec in zip(columns, specs[row_start : row_start + 3]):
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
                    status_key, status_label = _artifact_status_label(vm, artifact_id)
                    st.caption(f"Status: {status_label}")
                    button_type = "primary" if status_key in {"open", "stale"} else "secondary"
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
        st.caption(f"Status-Chip: {status_chip}")

        requirement_label = action["requirement_text"]
        if requirement_status_message:
            requirement_label = f"{requirement_label} — {requirement_status_message}"
        if requirements_ok and requirement_status_ok:
            st.caption(f"Voraussetzung: ✅ {requirement_label}")
        else:
            st.caption(f"Voraussetzung: ⚠️ {requirement_label}")

        input_renderer = action.get("input_renderer")
        if input_renderer is not None:
            st.caption("Vorbereitung im separaten Panel unterhalb der Action Cards.")
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
            st.markdown("**Inputs**")
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
    st.markdown("### Folgeartefakte")
    st.caption(
        "Nachgelagerte Artefakte bauen auf einem aktuellen Recruiting Brief auf."
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
            "Export wird im Bereich **Brief & Export** bereitgestellt (JSON, Markdown, DOCX, ESCO-Mapping)."
        )
        if has_brief:
            st.success(
                "Bereit: Recruiting Brief vorhanden – Exporte können erstellt werden."
            )
        else:
            st.info(
                "Noch nicht bereit: Erst den Recruiting Brief erstellen, dann Exporte nutzen."
            )


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


def _build_artifact_status_rows(
    *, action_registry: list[SummaryAction]
) -> list[dict[str, str]]:
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
                "Artefakt": action["title"],
                "Status": "Aktuell" if has_result else "Offen",
                "Voraussetzungen": (
                    "Erfüllt" if (requirements_ok and requirement_ok) else "Offen"
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
        ("Skills", "Must-have Skills"),
        ("Skills", "Nice-to-have Skills"),
    }
    benefits_group = {("Benefits", "Benefit")}
    interview_group = {("Interview", "Interviewphasen")}

    if _is_group_missing(core_profile_group | company_basics_group):
        return _recommend("brief", "Kernprofil, Standort oder Unternehmenskontext fehlen.", cta_label="Unternehmenskontext vervollständigen")
    if _is_group_missing(role_profile_group):
        return _recommend("brief", "Rollenprofil ist noch unvollständig.", cta_label="Rollenprofil vervollständigen")
    if _is_group_missing(skills_profile_group):
        return _recommend("brief", "Skills und Anforderungen sind noch unvollständig.", cta_label="Skills und Anforderungen klären")
    if _is_group_missing(benefits_group):
        return _recommend("brief", "Benefits und Rahmenbedingungen fehlen.", cta_label="Benefits und Rahmenbedingungen ergänzen")
    if _is_group_missing(interview_group):
        return _recommend("brief", "Interviewprozess ist noch nicht definiert.", cta_label="Interviewprozess definieren")

    brief_action = action_by_id.get("brief")
    if brief_action is not None:
        brief_status = _resolve_canonical_brief_status(resolved_brief_model=resolved_brief_model)
        if not brief_status.ready_for_follow_ups:
            return _recommend("brief", "Recruiting Brief fehlt oder ist noch nicht bereit.", cta_label="Recruiting Brief erstellen")

    sourcing_action = _first_available_action(("job_ad", "boolean_search"))
    if sourcing_action is not None:
        reason = "Recruiting Brief ist verfügbar, nächster Schritt ist Sourcing-Output."
        return NextBestActionRecommendation(action=sourcing_action, reason=reason, cta_label=sourcing_action["cta_label"])

    contract_prereq_group = core_profile_group | company_basics_group | role_profile_group
    if not _is_group_missing(contract_prereq_group) and bool(st.session_state.get(SSKey.BRIEF.value)):
        contract_action = _first_available_action(("employment_contract",))
        if contract_action is not None:
            return NextBestActionRecommendation(action=contract_action, reason="Vertragsrelevante Basisdaten sind vorhanden.", cta_label=contract_action["cta_label"])

    fallback_action = _first_available_action(("interview_hr", "interview_fach", "boolean_search", "employment_contract"))
    if fallback_action is not None:
        return NextBestActionRecommendation(action=fallback_action, reason="Nächster verfügbarer Schritt basierend auf dem aktuellen Status.", cta_label=fallback_action["cta_label"])
    if brief_action is not None:
        return NextBestActionRecommendation(action=brief_action, reason="Brief als sicherer Startpunkt.", cta_label=brief_action["cta_label"])
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


def _render_summary_dashboard_css() -> None:
    st.markdown(
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
        unsafe_allow_html=True,
    )


def _artifact_pipeline_status(
    action: SummaryAction, *, resolved_brief_model: str
) -> tuple[str, str]:
    if action["id"] == "brief":
        state, _, _ = _get_brief_status(
            primary_action=action,
            resolved_brief_model=resolved_brief_model,
        )
        return brief_pipeline_status_for_state(state)

    has_result = bool(st.session_state.get(action["result_key"].value))
    if has_result:
        return "current", "Aktuell"

    requirements_ok = _has_required_state(action["requires"])
    requirement_ok = True
    requirement_check_fn = action.get("requirement_check_fn")
    if requirement_check_fn is not None:
        requirement_ok, _ = requirement_check_fn()
    if requirements_ok and requirement_ok and action["generator_fn"] is not None:
        return "ready", "Bereit"
    if not requirements_ok or not requirement_ok:
        return "blocked", "Wartet"
    return "open", "Offen"


def _render_artifact_pipeline(
    action_registry: list[SummaryAction], *, resolved_brief_model: str
) -> None:
    st.markdown("#### Artefakt-Pipeline")
    st.caption("Status der wichtigsten Folge-Outputs auf einen Blick.")
    card_columns = st.columns(2)
    for index, action in enumerate(action_registry):
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
                st.caption(f"Status: {status_label}")
                requirement_text = action["requirement_text"]
                if requirement_message:
                    requirement_text = f"{requirement_text} — {requirement_message}"
                st.caption(f"Voraussetzungen: {requirement_text}")
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
    brief_label = {
        "current": "Aktuell",
        "stale": "Veraltet",
        "missing": "Fehlt",
        "invalid": "Ungültig",
        "blocked": "Blockiert",
    }.get(vm.status.brief_state, vm.status.brief_status_label)
    metric_columns = st.columns(4)
    metric_columns[0].metric("Readiness", f"{vm.status.readiness_percent}%")
    metric_columns[1].metric("Kritische Fakten", vm.status.completion_text)
    metric_columns[2].metric("ESCO", "Bestätigt" if vm.status.esco_ready else "Offen")
    metric_columns[3].metric("Brief", brief_label)


def _render_readiness_tab(
    *,
    vm: SummaryViewModel,
    action_registry: list[SummaryAction],
    resolved_brief_model: str,
    brief: VacancyBrief | None = None,
) -> None:
    _render_summary_dashboard_css()
    render_output_header(
        "Alles bereit für Recruiting und Hiring-Team",
        (
            "Hier siehst du, wie entscheidungsreif die Vakanz bereits ist, welche "
            "Lücken noch offen sind und welche Folgeartefakte jetzt sinnvoll "
            "gestartet werden können."
        ),
    )
    _render_summary_facts_column_overview(vm)

    recommendation = _resolve_next_best_action_recommendation(
        action_registry, resolved_brief_model=resolved_brief_model, vm=vm
    )
    action_col, pipeline_col = st.columns([1.12, 0.88], gap="large")
    with action_col:
        _render_next_best_action_card(recommendation=recommendation)
    with pipeline_col:
        _render_artifact_pipeline(
            action_registry,
            resolved_brief_model=resolved_brief_model,
        )
    if brief is not None:
        _render_summary_results_workspace(brief=brief)

    _render_critical_gaps_card(vm)
    _render_summary_workspace_tabs(
        vm=vm,
        action_registry=action_registry,
        resolved_brief_model=resolved_brief_model,
        brief=brief,
    )


def _render_readiness_dashboard_header(vm: SummaryViewModel) -> None:
    with st.container(border=True):
        st.markdown("### Readiness-Übersicht")
        _render_summary_readiness_metrics(vm)
        st.caption(
            "Diese Kennzahlen steuern die nächsten Artefakte; Detailwerte stehen im Fakten-Workspace."
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
        f"CTA: {recommendation.cta_label}",
    )
    requirement_label = next_action["requirement_text"]
    if requirement_status_message:
        requirement_label = f"{requirement_label} — {requirement_status_message}"
    st.caption(
        f"Voraussetzung: {'✅' if (requirements_ok and requirement_status_ok) else '⚠️'} {requirement_label}"
    )
    if st.button(
        f"CTA: {recommendation.cta_label}",
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
        st.success("Keine kritischen Lücken erkannt.")
        return
    render_critical_gaps(missing_items, title="Kritische Lücken (Top 5)")


def _render_artifact_launcher_cards(
    *, action_registry: list[SummaryAction], resolved_brief_model: str
) -> None:
    st.markdown("#### Artefakte starten")
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
    tab_labels = ["Brief", "Fakten", "Export", "Advanced"]
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
    st.markdown("### Workspaces")
    st.markdown(
        '<p class="cs-summary-section-note">'
        "Details sind nach Aufgabe getrennt, damit Fakten und Exporte nicht doppelt erscheinen."
        "</p>",
        unsafe_allow_html=True,
    )
    brief_tab, facts_tab, export_tab, advanced_tab = _build_summary_tabs()

    with brief_tab:
        if brief is None:
            st.info("Noch kein gültiger Recruiting Brief verfügbar.")
        else:
            render_output_header(
                "Recruiting Brief",
                "Kompakte Vorschau ohne Export-JSON. Downloads liegen im Export-Workspace.",
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
            st.info("Export ist verfügbar, sobald ein gültiger Recruiting Brief vorhanden ist.")
        else:
            _render_summary_export_workspace(brief=brief)

    with advanced_tab:
        st.subheader("Advanced")
        st.caption("Technische Vorschauen und Statusdaten bleiben hier gebündelt.")
        if brief is not None:
            with st.expander("Structured Export Preview", expanded=False):
                st.json(_build_brief_structured_preview_payload(brief), expanded=False)
        with st.expander("Artifact Status", expanded=False):
            st.dataframe(
                _build_artifact_status_rows(action_registry=action_registry),
                width="stretch",
                hide_index=True,
                column_config={
                    "Artefakt": st.column_config.TextColumn("Dokument"),
                    "Status": st.column_config.TextColumn("Status"),
                    "Voraussetzungen": st.column_config.TextColumn("Voraussetzungen"),
                },
            )
        with st.expander("Enrichment Timing", expanded=False):
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
                        "Treffer": st.column_config.NumberColumn("Treffer"),
                    },
                )
            else:
                st.info("Noch keine Timing-Daten für Enrichment-Pfade verfügbar.")


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
    resolved_employment_contract_model: str,
    render_job_ad_inputs: Callable[[], None] | None = None,
    follow_up_requirement_check: Callable[[], tuple[bool, str]],
    generate_recruiting_brief: Callable[[], None],
    generate_job_ad: Callable[[], None],
    generate_interview_prep_hr: Callable[[], None],
    generate_interview_prep_fach: Callable[[], None],
    generate_boolean_search: Callable[[], None],
    generate_employment_contract: Callable[[], None],
) -> list[SummaryAction]:
    return [
        {
            "id": "brief",
            "title": "Recruiting Brief",
            "benefit": "Verdichtet Jobspec und Wizard-Antworten zu einem sofort nutzbaren Recruiting Brief.",
            "cta_label": "Recruiting Brief erstellen",
            "blocked_cta_label": None,
            "requires": (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN),
            "requirement_text": "Jobspec und Wizard-Plan sind vorhanden",
            "requirement_check_fn": None,
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
            "id": "job_ad",
            "title": "Job-Ad-Generator",
            "benefit": "Erstellt eine zielgruppenorientierte Stellenanzeige mit nachvollziehbarer AGG-Checkliste.",
            "cta_label": "Stellenanzeige erstellen",
            "blocked_cta_label": None,
            "requires": (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN),
            "requirement_text": "Jobspec und Wizard-Plan sind vorhanden",
            "requirement_check_fn": None,
            "generator_fn": generate_job_ad,
            "result_key": SSKey.JOB_AD_DRAFT_CUSTOM,
            "input_hints": (),
            "input_renderer": render_job_ad_inputs,
        },
        {
            "id": "interview_hr",
            "title": "Interview-Vorbereitungssheet (HR)",
            "benefit": "Liefert ein strukturiertes HR-Interviewblatt mit Leitfaden und Bewertungsrubrik.",
            "cta_label": "HR-Sheet erstellen",
            "blocked_cta_label": "Recruiting Brief erstellen und danach HR-Sheet erstellen",
            "requires": (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN),
            "requirement_text": "Aktueller Recruiting Brief ist erforderlich",
            "requirement_check_fn": follow_up_requirement_check,
            "generator_fn": generate_interview_prep_hr,
            "result_key": SSKey.INTERVIEW_PREP_HR,
            "input_hints": (
                "Aktueller Recruiting Brief (kein Auto-Fallback)",
                "Kritische Must-haves",
                f"HR-Sheet-Modell: {resolved_hr_sheet_model}",
            ),
            "input_renderer": None,
        },
        {
            "id": "interview_fach",
            "title": "Interview-Vorbereitungssheet (Fachbereich)",
            "benefit": "Liefert ein fachliches Interviewblatt für Deep Dives und konsistente Bewertung.",
            "cta_label": "Fachbereich-Sheet erstellen",
            "blocked_cta_label": "Recruiting Brief erstellen und danach Fachbereich-Sheet erstellen",
            "requires": (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN),
            "requirement_text": "Aktueller Recruiting Brief ist erforderlich",
            "requirement_check_fn": follow_up_requirement_check,
            "generator_fn": generate_interview_prep_fach,
            "result_key": SSKey.INTERVIEW_PREP_FACH,
            "input_hints": (
                "Aktueller Recruiting Brief (kein Auto-Fallback)",
                "Must-have-Skills und Top Responsibilities",
                f"Fachbereich-Sheet-Modell: {resolved_fach_sheet_model}",
            ),
            "input_renderer": None,
        },
        {
            "id": "boolean_search",
            "title": "Boolean Search",
            "benefit": "Erstellt kanal-spezifische Boolean-Queries für Google, LinkedIn und XING.",
            "cta_label": "Boolean Search erstellen",
            "blocked_cta_label": "Recruiting Brief erstellen und danach Boolean Search erstellen",
            "requires": (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN),
            "requirement_text": "Aktueller Recruiting Brief ist erforderlich",
            "requirement_check_fn": follow_up_requirement_check,
            "generator_fn": generate_boolean_search,
            "result_key": SSKey.BOOLEAN_SEARCH_STRING,
            "input_hints": (
                "Aktueller Recruiting Brief (kein Auto-Fallback)",
                "Must-have- und Nice-to-have-Skills",
                f"Boolean-Modell: {resolved_boolean_search_model}",
            ),
            "input_renderer": None,
        },
        {
            "id": "employment_contract",
            "title": "Arbeitsvertrag",
            "benefit": "Erstellt einen Vertragsentwurf mit Platzhaltern und klarer Review-Struktur.",
            "cta_label": "Arbeitsvertrag erstellen",
            "blocked_cta_label": "Recruiting Brief erstellen und danach Arbeitsvertrag erstellen",
            "requires": (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN),
            "requirement_text": "Aktueller Recruiting Brief ist erforderlich",
            "requirement_check_fn": follow_up_requirement_check,
            "generator_fn": generate_employment_contract,
            "result_key": SSKey.EMPLOYMENT_CONTRACT_DRAFT,
            "input_hints": (
                "Aktueller Recruiting Brief (kein Auto-Fallback)",
                "Vertragsart und Konditionen",
                f"Contract-Modell: {resolved_employment_contract_model}",
            ),
            "input_renderer": None,
        },
    ]


def _render_summary_processing_hub(
    *,
    action_registry: list[SummaryAction],
    resolved_brief_model: str,
    show_job_ad_configuration_panel: bool = True,
    show_export_bar: bool = True,
) -> None:
    render_output_header(
        "Processing Hub",
        "Primärer Pfad kompakt: Recruiting Brief → Folgeartefakte → Export.",
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
            f"**Pipeline:** `Recruiting Brief` → `Interview HR/Fach` → "
            f"`Boolean Search` → `Arbeitsvertrag` → `Export`  \n"
            f"Status Recruiting Brief: {header_badge} · {brief_status_label}"
        )
    )

    st.markdown("#### Artefaktübersicht")
    header_columns = st.columns([2.1, 1.1, 1.2, 2.0], gap="small")
    header_columns[0].markdown("**Artefakt**")
    header_columns[1].markdown("**Status**")
    header_columns[2].markdown("**Prereqs**")
    header_columns[3].markdown("**Primary CTA**")

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
                st.markdown("**Inputs**")
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
    publishable_text = _build_publishable_job_ad_plain_text(custom_job_ad)
    publishable_markdown = _build_publishable_job_ad_markdown(custom_job_ad)
    logo_payload = _job_ad_logo_payload(custom_job_ad_raw)
    render_output_header(
        custom_job_ad.headline or "Stellenanzeige",
        "Generierte Stellenanzeige mit Zielgruppen- und AGG-Hinweisen.",
    )
    render_card_start("cs-card cs-result-card")
    st.markdown("### Primary Output")
    st.text_area(
        "Stellenanzeige",
        value=publishable_text,
        height=_estimate_text_area_height(publishable_text),
        disabled=True,
    )
    st.markdown("</section>", unsafe_allow_html=True)

    render_card_start("cs-card cs-result-card")
    st.markdown("### Review")
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
    st.markdown("</section>", unsafe_allow_html=True)

    render_card_start("cs-card cs-result-card")
    st.markdown("### Export")
    custom_docx = _job_ad_to_docx_bytes(custom_job_ad, logo_payload=logo_payload)
    custom_pdf = _job_ad_to_pdf_bytes(custom_job_ad, logo_payload=logo_payload)
    custom_md = publishable_markdown.encode("utf-8")
    x1, x2, x3 = st.columns(3)
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
    with x3:
        st.download_button(
            "Download Stellenanzeige (Markdown)",
            data=custom_md,
            file_name="stellenanzeige.md",
            mime="text/markdown",
        )
    st.markdown("</section>", unsafe_allow_html=True)


def _render_active_artifact(*, artifact_id: str, brief: VacancyBrief) -> None:
    if artifact_id == "brief":
        render_card_start("cs-card cs-result-card")
        render_brief(
            brief,
            structured_data_payload=_build_brief_structured_preview_payload(brief),
        )
        st.markdown("</section>", unsafe_allow_html=True)
        return

    if artifact_id == "job_ad":
        custom_job_ad_raw = st.session_state.get(SSKey.JOB_AD_DRAFT_CUSTOM.value)
        if not isinstance(custom_job_ad_raw, dict):
            st.info("Für dieses Artefakt liegt noch kein Ergebnis vor.")
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
        else:
            st.info("Für dieses Artefakt liegt noch kein Ergebnis vor.")
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
            x1, x2, x3 = st.columns(3)
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
            with x3:
                if fach_pdf_bytes is None:
                    st.caption("PDF-Export benötigt reportlab (nicht verfügbar).")
                else:
                    st.download_button(
                        "Download Interview Sheet (Fachbereich) PDF",
                        data=fach_pdf_bytes,
                        file_name="interview_sheet_fachbereich.pdf",
                        mime="application/pdf",
                    )
        else:
            st.info("Für dieses Artefakt liegt noch kein Ergebnis vor.")
        return

    if artifact_id == "boolean_search":
        payload = st.session_state.get(SSKey.BOOLEAN_SEARCH_STRING.value)
        if isinstance(payload, dict):
            boolean_pack = BooleanSearchPack.model_validate(payload)
            render_boolean_search_pack(boolean_pack)
        else:
            st.info("Für dieses Artefakt liegt noch kein Ergebnis vor.")
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
        else:
            st.info("Für dieses Artefakt liegt noch kein Ergebnis vor.")


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
    st.caption("Vorhandene Outputs")
    columns = st.columns(min(len(available_artifact_ids), 4), gap="small")
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
    request_value = st.text_area(
        "Was soll am Output angepasst werden?",
        value=current_value,
        placeholder="z. B. kürzer, stärker auf Senior-Profile, mehr Interviewfragen zu Stakeholder-Management …",
        key=_widget_key(
            SSKey.SUMMARY_ACTION_WIDGET_PREFIX,
            f"refinement.{artifact_id}",
        ),
        height=110,
    )
    _write_artifact_change_request(artifact_id, request_value)
    generator = generator_by_id.get(artifact_id)
    if st.button(
        "Anpassungen übernehmen",
        width="stretch",
        type="primary",
        disabled=generator is None,
        key=_widget_key(
            SSKey.SUMMARY_ACTION_WIDGET_PREFIX,
            f"refinement.apply.{artifact_id}",
        ),
    ):
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

    columns = st.columns(4)
    with columns[0]:
        render_boolean_supporting_terms(boolean_pack)
    with columns[1]:
        render_boolean_usage_notes(boolean_pack)
    with columns[2]:
        render_boolean_risks(boolean_pack)
    with columns[3]:
        _render_artifact_refinement_box(
            vm=vm,
            artifact_id="boolean_search",
            generator_by_id=generator_by_id,
            heading="### Anpassungswünsche",
        )
    return True


def _render_summary_output_workspace(
    *,
    vm: SummaryViewModel,
    brief: VacancyBrief,
    generator_by_id: Mapping[str, Callable[[], None]],
) -> None:
    st.markdown("### Output")
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
        st.warning("Dieser Output basiert auf älteren Fakten oder Optionen. Bitte neu generieren.")
    if active_artifact_id in available_artifact_ids:
        _render_active_artifact(artifact_id=active_artifact_id, brief=brief)
    else:
        st.info("Für dieses Artefakt liegt noch kein Ergebnis vor.")
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
        st.info("Noch keine Folgeartefakte vorhanden.")
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
    st.session_state[SSKey.SUMMARY_INPUT_FINGERPRINT.value] = (
        current_summary_fingerprint
    )
    st.session_state[SSKey.SUMMARY_DIRTY.value] = vm.artifacts.is_dirty

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
            st.session_state[SSKey.SUMMARY_LAST_BRIEF_FINGERPRINT.value] = (
                current_summary_fingerprint
            )
            st.session_state[SSKey.SUMMARY_DIRTY.value] = False
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
            with st.spinner("Generiere Boolean Search Pack…"):
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
            with st.spinner("Generiere Arbeitsvertrags-Template…"):
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
                ("Rolle · Kurzbeschreibung", "Manager-Input · role_tasks"),
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
                ("Skills · Must-have", "Manager-Input · must_have_skills"),
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
        st.session_state[SSKey.SUMMARY_STYLEGUIDE_TEXT.value] = (
            _build_job_ad_styleguide_text(
                preset=preset,
                address=address,
                tone=tone,
                length=length,
                cta=cta,
                manual_styleguide=manual_styleguide,
            )
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

    render_output_header(
        "Alles bereit für Recruiting und Hiring-Team",
        "Prüfe die vorhandenen Fakten, schließe kritische Lücken und erstelle die passenden Outputs.",
    )
    _render_esco_coverage_kpis()
    _render_summary_facts_matrix(vm)
    _render_summary_critical_gaps_table(vm)
    _render_summary_artifact_grid(vm=vm, generator_by_id=generator_by_id)
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
