# wizard_pages/08_summary.py

import io
import json
import re
import textwrap
import csv
import hashlib
from contextlib import nullcontext
from dataclasses import dataclass
from collections import defaultdict
from typing import Any, Callable, Protocol, TypedDict

import streamlit as st
import docx

from constants import (
    AnswerType,
    NON_INTAKE_STEP_KEYS,
    SSKey,
    SUMMARY_ARTIFACT_IDS,
    SUMMARY_ARTIFACT_LEGACY_ALIASES,
)
from esco_client import EscoClient, EscoClientError
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
    EscoMappingReport,
    EmploymentContractDraft,
    InterviewPrepSheetHiringManager,
    InterviewPrepSheetHR,
    JobAdExtract,
    LanguageRequirement,
    Question,
    QuestionPlan,
    VacancyBrief,
    question_option_label_map,
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
    render_esco_explainability,
    render_boolean_search_pack,
    render_brief,
    render_employment_contract_draft,
    render_error_banner,
    render_interview_prep_fach,
    render_interview_prep_hr,
    render_openai_error,
)
from usage_utils import usage_has_cache_hit
from wizard_pages.base import (
    WizardContext,
    WizardPage,
    get_current_ui_mode,
    nav_buttons,
)
from wizard_pages.salary_forecast_panel import render_salary_forecast_panel

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


ACTION_ID_TO_CANONICAL_ARTIFACT_ID: dict[str, str] = {
    **SUMMARY_ARTIFACT_LEGACY_ALIASES,
    **{artifact_id: artifact_id for artifact_id in SUMMARY_ARTIFACT_IDS},
}


@dataclass(frozen=True)
class SummaryMeta:
    role_label: str
    company_label: str
    country_label: str
    selected_occupation_title: str
    nace_code: str
    nace_mapped_esco_uri: str
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
    nace_ready: bool


@dataclass(frozen=True)
class SummaryFactsRow:
    bereich: str
    feld: str
    wert: str
    quelle: str
    status: str

    def to_dict(self) -> dict[str, str]:
        return {
            "Bereich": self.bereich,
            "Feld": self.feld,
            "Wert": self.wert,
            "Quelle": self.quelle,
            "Status": self.status,
        }


@dataclass(frozen=True)
class SummaryArtifactState:
    brief: VacancyBrief | None
    selected_role_tasks: list[str]
    selected_skills: list[str]
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
            cta_label="Recruiting Brief generieren",
            ready_for_follow_ups=False,
        )
    try:
        VacancyBrief.model_validate(brief_payload)
    except Exception:
        return CanonicalBriefStatus(
            state="invalid",
            message="Recruiting Brief ist ungültig.",
            cta_label="Recruiting Brief neu generieren",
            ready_for_follow_ups=False,
        )

    if bool(st.session_state.get(SSKey.SUMMARY_DIRTY.value)):
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
        st.session_state.get(SSKey.SUMMARY_INPUT_FINGERPRINT.value, "") or ""
    )
    last_brief_fingerprint = str(
        st.session_state.get(SSKey.SUMMARY_LAST_BRIEF_FINGERPRINT.value, "") or ""
    )
    if (
        current_input_fingerprint
        and last_brief_fingerprint
        and current_input_fingerprint != last_brief_fingerprint
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


def _to_canonical_artifact_id(raw_id: Any) -> str:
    if not isinstance(raw_id, str):
        return ""
    return ACTION_ID_TO_CANONICAL_ARTIFACT_ID.get(raw_id, "")


def _resolve_active_artifact_id(*, available_artifact_ids: list[str]) -> str:
    active_raw = st.session_state.get(SSKey.SUMMARY_ACTIVE_ARTIFACT.value, "")
    normalized_active = _to_canonical_artifact_id(active_raw)
    if normalized_active in available_artifact_ids:
        if active_raw != normalized_active:
            st.session_state[SSKey.SUMMARY_ACTIVE_ARTIFACT.value] = normalized_active
        return normalized_active
    if "brief" in available_artifact_ids:
        fallback = "brief"
    elif available_artifact_ids:
        fallback = available_artifact_ids[0]
    else:
        fallback = "brief"
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


def _build_summary_input_fingerprint(
    *,
    job: JobAdExtract,
    answers: dict[str, Any],
    selected_role_tasks: list[str],
    selected_skills: list[str],
    esco_occupation_selected: dict[str, str],
    esco_match_explainability: EscoMatchExplainability,
    esco_selected_skills_must: list[dict[str, str]],
    esco_selected_skills_nice: list[dict[str, str]],
    nace_code: str,
    nace_to_esco_mapping: dict[str, str],
) -> str:
    non_sensitive_payload = {
        "job": job.model_dump(mode="json", exclude_none=True),
        "answers": answers,
        "selected_role_tasks": selected_role_tasks,
        "selected_skills": selected_skills,
        "esco_occupation_selected": esco_occupation_selected,
        "esco_match_explainability": esco_match_explainability,
        "esco_selected_skills_must": esco_selected_skills_must,
        "esco_selected_skills_nice": esco_selected_skills_nice,
        "nace_code": nace_code,
        "nace_to_esco_mapping": nace_to_esco_mapping,
    }
    serialized = json.dumps(
        non_sensitive_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


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


def _session_list(key: SSKey, default: list[Any] | None = None) -> list[Any]:
    raw = st.session_state.get(key.value, default if default is not None else [])
    return raw if isinstance(raw, list) else []


def _session_dict(key: SSKey, default: dict[str, Any] | None = None) -> dict[str, Any]:
    raw = st.session_state.get(key.value, default if default is not None else {})
    return raw if isinstance(raw, dict) else {}


def _session_str(key: SSKey, default: str = "") -> str:
    return str(st.session_state.get(key.value, default) or "").strip()


def _to_esco_export_concepts(raw_items: Any) -> list[EscoExportConcept]:
    if not isinstance(raw_items, list):
        return []
    concepts: list[EscoExportConcept] = []
    for item in raw_items:
        try:
            parsed = EscoConceptRef.model_validate(item)
        except Exception:
            continue
        concepts.append({"uri": parsed.uri, "label": parsed.title})
    return concepts


def _normalize_skill_term(value: str) -> str:
    return " ".join(str(value or "").strip().casefold().split())


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
    must_terms = (
        _extract_skills_step_raw_terms(
            {"must_have_skills": job_extract.get("must_have_skills", [])}
        )
        if isinstance(job_extract, dict)
        else []
    )
    nice_terms = (
        _extract_skills_step_raw_terms(
            {"nice_to_have_skills": job_extract.get("nice_to_have_skills", [])}
        )
        if isinstance(job_extract, dict)
        else []
    )

    essential_titles = {
        _normalize_skill_term(str(item.get("title") or ""))
        for item in shared_esco.get("essential_skills", [])
        if isinstance(item, dict)
    }
    optional_titles = {
        _normalize_skill_term(str(item.get("title") or ""))
        for item in shared_esco.get("optional_skills", [])
        if isinstance(item, dict)
    }

    essential_covered = sum(
        1 for term in must_terms if _normalize_skill_term(term) in essential_titles
    )
    optional_covered = sum(
        1 for term in nice_terms if _normalize_skill_term(term) in optional_titles
    )
    essential_total = len(must_terms)
    optional_total = len(nice_terms)
    essential_pct = (
        round((essential_covered / essential_total) * 100) if essential_total else 0
    )
    optional_pct = (
        round((optional_covered / optional_total) * 100) if optional_total else 0
    )
    return {
        "essential_covered": essential_covered,
        "essential_total": essential_total,
        "essential_pct": essential_pct,
        "optional_covered": optional_covered,
        "optional_total": optional_total,
        "optional_pct": optional_pct,
    }


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
            explainability = _read_esco_match_explainability()
            if explainability:
                payload["esco_occupation_provenance"] = explainability

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
    if shared_esco["unmapped_actions"]:
        payload["esco_unmapped_term_actions"] = shared_esco["unmapped_actions"]

    esco_config = _session_dict(SSKey.ESCO_CONFIG)
    selected_version = str(esco_config.get("selected_version") or "").strip()
    if selected_version:
        payload["esco_version"] = selected_version

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

    salary_forecast = st.session_state.get(SSKey.SALARY_FORECAST_LAST_RESULT.value)
    if isinstance(salary_forecast, dict):
        payload["salary_forecast"] = salary_forecast

    scenario_lab_rows = st.session_state.get(SSKey.SALARY_SCENARIO_LAB_ROWS.value)
    if isinstance(scenario_lab_rows, list):
        payload["salary_scenarios"] = scenario_lab_rows[:100]
    return payload


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
    logo_payload = _read_logo_payload()
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
    if status.nace_ready:
        mapping_fragments.append(f"NACE gesetzt ({meta.nace_code})")
    else:
        mapping_fragments.append("NACE noch offen")
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
        ("NACE", "✅" if status.nace_ready else "—"),
        ("Readiness", readiness),
    )
    columns = st.columns(len(badges))
    for idx, (label, value) in enumerate(badges):
        columns[idx].metric(label, str(value))


def _build_summary_status(
    *, answers: dict[str, Any], meta: SummaryMeta, resolved_brief_model: str | None
) -> SummaryStatus:
    esco_ready = bool(meta.selected_occupation_title)
    nace_ready = bool(meta.nace_code)
    completion_text = f"{len(answers)} Antworten"
    completion_ratio = 0.0
    plan_payload = st.session_state.get(SSKey.QUESTION_PLAN.value)
    if isinstance(plan_payload, dict):
        try:
            plan_model = QuestionPlan.model_validate(plan_payload)
            question_ids = [
                question.id
                for step in plan_model.steps
                if step.step_key not in NON_INTAKE_STEP_KEYS
                for question in step.questions
            ]
            total_questions = len(question_ids)
            answered_questions = sum(
                1 for qid in question_ids if answers.get(qid) not in (None, "", [])
            )
            completion_ratio = (
                answered_questions / total_questions if total_questions > 0 else 0.0
            )
            completion_text = f"{answered_questions}/{total_questions} beantwortet"
        except Exception:
            completion_text = f"{len(answers)} Antworten"

    brief_status = _resolve_canonical_brief_status(
        resolved_brief_model=resolved_brief_model
    )
    brief_state = brief_status.state
    brief_status_label = brief_status.message

    if brief_state in {"missing", "blocked"}:
        next_step = "Recruiting Brief generieren"
    elif brief_state in {"invalid", "stale"}:
        next_step = "Recruiting Brief aktualisieren"
    else:
        next_step = "Gewünschtes Folge-Artefakt erzeugen"

    readiness_checks = [
        bool(meta.role_label),
        bool(meta.company_label),
        bool(meta.country_label),
        esco_ready,
        nace_ready,
        brief_status.ready_for_follow_ups,
    ]
    readiness_percent = round(
        (sum(1 for item in readiness_checks if item) / len(readiness_checks)) * 100
    )
    ready_for_follow_ups = brief_status.ready_for_follow_ups

    return SummaryStatus(
        completion_ratio=completion_ratio,
        completion_text=completion_text,
        brief_state=brief_state,
        brief_status_label=brief_status_label,
        next_step=next_step,
        readiness_percent=readiness_percent,
        ready_for_follow_ups=ready_for_follow_ups,
        esco_ready=esco_ready,
        nace_ready=nace_ready,
    )


def _build_summary_view_model() -> SummaryViewModel | None:
    job_dict = st.session_state.get(SSKey.JOB_EXTRACT.value)
    plan_dict = st.session_state.get(SSKey.QUESTION_PLAN.value)
    if not job_dict or not plan_dict:
        return None

    job = JobAdExtract.model_validate(job_dict)
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
    meta = _build_summary_meta(job)
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
        selected_role_tasks=selected_role_tasks,
        selected_skills=selected_skills,
        esco_occupation_selected=_read_selected_esco_occupation(),
        esco_match_explainability=_read_esco_match_explainability(),
        esco_selected_skills_must=_read_esco_skill_refs(
            SSKey.ESCO_SKILLS_SELECTED_MUST
        ),
        esco_selected_skills_nice=_read_esco_skill_refs(
            SSKey.ESCO_SKILLS_SELECTED_NICE
        ),
        nace_code=meta.nace_code,
        nace_to_esco_mapping=_read_nace_to_esco_mapping(),
    )
    artifacts = _build_summary_artifact_state(
        selected_role_tasks=selected_role_tasks,
        selected_skills=selected_skills,
        input_fingerprint=input_fingerprint,
    )
    status = _build_summary_status(
        answers=answers,
        meta=meta,
        resolved_brief_model=resolved_brief_model,
    )
    fact_rows = _build_summary_fact_rows(
        job=job,
        answers=answers,
        plan=plan,
        artifacts=artifacts,
        meta=meta,
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


def _read_nace_to_esco_mapping() -> dict[str, str]:
    nace_lookup_raw = _session_dict(SSKey.EURES_NACE_TO_ESCO)
    mapping: dict[str, str] = {}
    for code, uri in nace_lookup_raw.items():
        normalized_code = str(code or "").strip()
        normalized_uri = str(uri or "").strip()
        if normalized_code and normalized_uri:
            mapping[normalized_code] = normalized_uri
    return mapping


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


def _build_summary_meta(job: JobAdExtract) -> SummaryMeta:
    selected_occupation = _read_selected_esco_occupation()
    nace_code = _session_str(SSKey.COMPANY_NACE_CODE)
    nace_mapping = _read_nace_to_esco_mapping()
    return SummaryMeta(
        role_label=str(job.job_title or "").strip(),
        company_label=str(job.company_name or "").strip(),
        country_label=str(job.location_country or "").strip(),
        selected_occupation_title=selected_occupation.get("title", ""),
        nace_code=nace_code,
        nace_mapped_esco_uri=str(nace_mapping.get(nace_code, "") or "").strip(),
        readiness_items=_build_country_readiness_items(job),
    )


def _build_summary_artifact_state(
    *,
    selected_role_tasks: list[str],
    selected_skills: list[str],
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
        input_fingerprint=input_fingerprint,
        last_brief_fingerprint=last_brief_fingerprint,
        is_dirty=is_dirty,
    )


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
            "Semantischer Anker bestätigt",
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


def _render_summary_facts_section(vm: SummaryViewModel) -> None:
    st.markdown("### Fakten")
    _render_summary_facts_table([row.to_dict() for row in vm.fact_rows])


def _format_summary_answer_value(question: Question, value: Any) -> str:
    option_label_map = question_option_label_map(question)

    def _label_for(item: Any) -> str:
        item_str = str(item).strip()
        if not item_str:
            return ""
        return option_label_map.get(item_str, item_str)

    if question.answer_type == AnswerType.BOOLEAN:
        return "Ja" if bool(value) else "Nein"
    if question.answer_type == AnswerType.MULTI_SELECT:
        if isinstance(value, list):
            labels = [_label_for(item) for item in value]
            return ", ".join(label for label in labels if label)
        return ""
    if question.answer_type == AnswerType.SINGLE_SELECT:
        return _label_for(value)
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


def _is_missing_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set)):
        return len(value) == 0
    if isinstance(value, dict):
        return len(value) == 0
    return False


def _has_partial_payload(value: Any) -> bool:
    if isinstance(value, dict):
        values = list(value.values())
        if not values:
            return False
        has_present = any(not _is_missing_value(item) for item in values)
        has_missing = any(_is_missing_value(item) for item in values)
        return has_present and has_missing
    if isinstance(value, list):
        if not value:
            return False
        has_present = any(not _is_missing_value(item) for item in value)
        has_missing = any(_is_missing_value(item) for item in value)
        return has_present and has_missing
    return False


def _status_for_value(value: Any) -> str:
    if _is_missing_value(value):
        return "Fehlend"
    if _has_partial_payload(value):
        return "Teilweise"
    return "Vollständig"


def _status_for_classification_value(value: Any) -> str:
    if _is_missing_value(value):
        return "Fehlend"
    return "Automatisch erkannt"


def _status_for_answer_value(
    *, question: Question, raw_value: Any, formatted: str
) -> str:
    if _is_missing_value(raw_value):
        return "Fehlend"
    if question.answer_type == AnswerType.MULTI_SELECT and isinstance(raw_value, list):
        normalized_items = [str(item).strip() for item in raw_value]
        non_empty_count = sum(1 for item in normalized_items if item)
        if non_empty_count == 0:
            return "Fehlend"
        if non_empty_count < len(normalized_items):
            return "Teilweise"
    if question.answer_type in {
        AnswerType.SHORT_TEXT,
        AnswerType.LONG_TEXT,
    } and isinstance(raw_value, dict):
        return "Teilweise" if _has_partial_payload(raw_value) else "Vollständig"
    if not formatted:
        return "Teilweise"
    return "Teilweise" if _has_partial_payload(raw_value) else "Vollständig"


def _build_summary_fact_rows(
    *,
    job: JobAdExtract,
    answers: dict[str, Any],
    plan: QuestionPlan | None,
    artifacts: SummaryArtifactState,
    meta: SummaryMeta,
) -> list[SummaryFactsRow]:
    rows: list[SummaryFactsRow] = [
        SummaryFactsRow(
            "Kernprofil",
            "Rolle",
            str(job.job_title or "").strip() or "Nicht angegeben",
            "Jobspec",
            _status_for_value(job.job_title),
        ),
        SummaryFactsRow(
            "Kernprofil",
            "Unternehmen",
            str(job.company_name or "").strip() or "Nicht angegeben",
            "Jobspec",
            _status_for_value(job.company_name),
        ),
        SummaryFactsRow(
            "Kernprofil",
            "Land",
            str(job.location_country or "").strip() or "Nicht angegeben",
            "Jobspec",
            _status_for_value(job.location_country),
        ),
        SummaryFactsRow(
            "Kernprofil",
            "Stadt",
            str(job.location_city or "").strip() or "Nicht angegeben",
            "Jobspec",
            _status_for_value(job.location_city),
        ),
        SummaryFactsRow(
            "Klassifikation",
            "ESCO Occupation",
            meta.selected_occupation_title or "Nicht gesetzt",
            "Jobspec-Review",
            _status_for_classification_value(meta.selected_occupation_title),
        ),
        SummaryFactsRow(
            "Klassifikation",
            "NACE-Code",
            meta.nace_code or "Nicht gesetzt",
            "Unternehmen",
            _status_for_classification_value(meta.nace_code),
        ),
        SummaryFactsRow(
            "Klassifikation",
            "NACE → ESCO Mapping",
            meta.nace_mapped_esco_uri or "Nicht verfügbar",
            "EURES",
            _status_for_classification_value(meta.nace_mapped_esco_uri),
        ),
        SummaryFactsRow(
            "Artefakte",
            "Recruiting Brief",
            "Vorhanden" if artifacts.brief is not None else "Noch nicht generiert",
            "Summary",
            "Vollständig" if artifacts.brief is not None else "Teilweise",
        ),
    ]

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
                )
            )
            seen_row_keys.add(row_key)
    return rows


def _render_summary_facts_table(rows: list[dict[str, str]]) -> None:
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
        options=["Alle", "Vollständig", "Teilweise", "Fehlend", "Automatisch erkannt"],
        key=SSKey.SUMMARY_FACTS_STATUS_FILTER.value,
    )

    filtered_rows = rows
    if search_query:
        filtered_rows = [
            row
            for row in filtered_rows
            if search_query
            in " ".join(
                str(row.get(column, "")).lower()
                for column in ("Bereich", "Feld", "Wert", "Quelle", "Status")
            )
        ]
    if status_filter != "Alle":
        filtered_rows = [
            row for row in filtered_rows if row.get("Status", "") == status_filter
        ]

    st.dataframe(
        filtered_rows,
        width="stretch",
        hide_index=True,
        column_order=["Bereich", "Feld", "Wert", "Quelle", "Status"],
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
            st.caption("Konfiguration im separaten Panel unterhalb der Action Cards.")
            open_config_clicked = st.button(
                "Job-Ad-Konfiguration öffnen",
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

    st.markdown("### Job-Ad-Konfiguration")
    st.caption(
        "Selection Matrix und Editor sind ausgelagert, damit der Hub scannbar bleibt."
    )
    st.toggle(
        "Konfigurationspanel anzeigen",
        key=SSKey.SUMMARY_SHOW_JOB_AD_CONFIG.value,
        help="Blendet Selection Matrix und Job-Ad-Editor für die Stellenanzeige ein oder aus.",
    )
    if not bool(st.session_state.get(SSKey.SUMMARY_SHOW_JOB_AD_CONFIG.value, False)):
        st.caption(
            "Panel ausgeblendet. Nutze „Job-Ad-Konfiguration öffnen“ in der Job-Ad-Karte."
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
    missing_rows = [row for row in vm.fact_rows if row.status == "Fehlend"]
    partial_rows = [row for row in vm.fact_rows if row.status == "Teilweise"]
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


def _resolve_next_best_action(
    action_registry: list[SummaryAction],
) -> SummaryAction | None:
    brief_action = next(
        (action for action in action_registry if action["id"] == "brief"),
        None,
    )
    if brief_action is not None:
        brief_status = _resolve_canonical_brief_status(resolved_brief_model="")
        if not brief_status.ready_for_follow_ups:
            return brief_action
    for action in action_registry:
        if action["id"] == "brief":
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
    return brief_action


def _render_readiness_tab(
    *,
    vm: SummaryViewModel,
    action_registry: list[SummaryAction],
) -> None:
    if hasattr(st, "subheader"):
        st.subheader("Readiness")
    else:
        st.markdown("### Readiness")
    next_action = _resolve_next_best_action(action_registry)
    if next_action is None:
        st.info("Aktuell ist kein nächster Schritt verfügbar.")
    else:
        st.markdown(f"**Nächste beste Aktion:** {next_action['title']}")
        if st.button(
            f"CTA: {next_action['cta_label']}",
            type="primary",
            width="stretch",
            key=_widget_key(
                SSKey.SUMMARY_ACTION_WIDGET_PREFIX, "readiness.next_action"
            ),
            disabled=next_action["generator_fn"] is None,
        ):
            st.session_state[SSKey.SUMMARY_ACTIVE_ARTIFACT.value] = (
                _to_canonical_artifact_id(next_action["id"])
            )
            if next_action["generator_fn"] is not None:
                next_action["generator_fn"]()
            st.rerun()

    shared_esco = _read_esco_shared_fields()
    coverage = _compute_esco_coverage_metrics(shared_esco)
    occupation_explainability = _read_esco_match_explainability()
    st.markdown("**ESCO-Coverage**")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "Essential Coverage",
        f"{coverage['essential_covered']}/{coverage['essential_total']}",
        f"{coverage['essential_pct']}%",
    )
    c2.metric(
        "Optional Coverage",
        f"{coverage['optional_covered']}/{coverage['optional_total']}",
        f"{coverage['optional_pct']}%",
    )
    c3.metric("Unmapped Gaps", str(len(shared_esco["unmapped_terms"])))
    relation_traces = _count_skill_relation_traces(
        shared_esco["essential_skills"] + shared_esco["optional_skills"]
    )
    c4.metric("Skill→Occupation traces", str(relation_traces))
    confirmed_occupation = int(
        str(occupation_explainability.get("confidence", "")).strip().lower() == "high"
    )
    inferred_occupation = (
        1 - confirmed_occupation if vm.meta.selected_occupation_title else 0
    )
    inferred_skill_count = sum(
        1
        for item in (shared_esco["essential_skills"] + shared_esco["optional_skills"])
        if str(item.get("relation") or "").strip().startswith("has")
    )
    confirmed_skill_count = (
        len(shared_esco["essential_skills"]) + len(shared_esco["optional_skills"])
    ) - inferred_skill_count
    st.markdown("**Confirmed vs. Inferred ESCO Coverage**")
    cc1, cc2 = st.columns(2)
    cc1.metric(
        "Confirmed",
        str(max(confirmed_skill_count, 0) + confirmed_occupation),
        "High-confidence / user-confirmed",
    )
    cc2.metric(
        "Inferred",
        str(max(inferred_skill_count, 0) + inferred_occupation),
        "Relation-derived / weaker confidence",
    )
    render_esco_explainability(
        labels=occupation_explainability.get("provenance_categories", []),
        confidence=str(occupation_explainability.get("confidence", "low")),
        reason=str(occupation_explainability.get("reason", "") or ""),
        caption_prefix="Summary Occupation Explainability",
    )
    if shared_esco["unmapped_terms"]:
        st.caption(
            "Offene Begriffe: "
            + ", ".join(shared_esco["unmapped_terms"][:8])
            + (" …" if len(shared_esco["unmapped_terms"]) > 8 else "")
        )
    if shared_esco["unmapped_roles"]:
        st.caption(
            "Nicht normalisierte Rollenbegriffe: "
            + ", ".join(shared_esco["unmapped_roles"][:4])
        )

    st.markdown("**Kritische Lücken (Top 5)**")
    missing_items = _build_missing_critical_items(vm)
    if not missing_items:
        st.success("Keine kritischen Lücken erkannt.")
    else:
        for item in missing_items:
            st.write(f"- {item}")

    st.markdown("**Artefakt-Status**")
    status_rows = _build_artifact_status_rows(action_registry=action_registry)
    if hasattr(st, "dataframe"):
        st.dataframe(
            status_rows,
            hide_index=True,
            width="stretch",
        )
    else:
        for row in status_rows:
            st.write(
                f"- {row['Artefakt']}: {row['Status']} (Voraussetzungen: {row['Voraussetzungen']})"
            )


def _build_summary_tabs() -> SummaryTabs:
    tab_labels = ["Readiness", "Fakten", "Artefakte", "Export", "Advanced"]
    if hasattr(st, "tabs"):
        tabs = st.tabs(tab_labels)
        if len(tabs) == 5:
            return tabs[0], tabs[1], tabs[2], tabs[3], tabs[4]
    if hasattr(st, "container"):
        return (
            st.container(),
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
        nullcontext(),
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
            "cta_label": "Recruiting Brief generieren",
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
            "cta_label": "Stellenanzeige generieren/verbessern",
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
            "title": "Boolean Search String",
            "benefit": "Erstellt kanal-spezifische Boolean-Queries für Google, LinkedIn und XING.",
            "cta_label": "Boolean String erstellen",
            "blocked_cta_label": "Recruiting Brief erstellen und danach Boolean String erstellen",
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
    st.markdown("### Processing Hub")
    st.caption("Primärer Pfad kompakt: Recruiting Brief → Folgeartefakte → Export.")

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
                    "Job-Ad-Konfiguration öffnen",
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


def _render_active_artifact(*, artifact_id: str, brief: VacancyBrief) -> None:
    if artifact_id == "brief":
        render_brief(brief)
        return

    if artifact_id == "job_ad":
        custom_job_ad_raw = st.session_state.get(SSKey.JOB_AD_DRAFT_CUSTOM.value)
        if not isinstance(custom_job_ad_raw, dict):
            st.info("Für dieses Artefakt liegt noch kein Ergebnis vor.")
            return
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
            fach_docx_bytes = _interview_prep_fach_to_docx_bytes(sheet)
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
        else:
            st.info("Für dieses Artefakt liegt noch kein Ergebnis vor.")
        return

    if artifact_id == "boolean_search":
        payload = st.session_state.get(SSKey.BOOLEAN_SEARCH_STRING.value)
        if isinstance(payload, dict):
            boolean_pack = BooleanSearchPack.model_validate(payload)
            render_boolean_search_pack(boolean_pack)
            boolean_json_bytes = json.dumps(
                boolean_pack.model_dump(mode="json"), indent=2, ensure_ascii=False
            ).encode("utf-8")
            boolean_md = _boolean_search_pack_to_markdown(boolean_pack).encode("utf-8")
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


def _render_secondary_artifacts(
    *, active_artifact_id: str, available_artifact_ids: list[str]
) -> None:
    secondary_ids = [
        artifact_id
        for artifact_id in available_artifact_ids
        if artifact_id != active_artifact_id
    ]
    if not secondary_ids:
        return
    st.caption("Weitere Ergebnisse")
    for artifact_id in secondary_ids:
        if st.button(
            f"Als Fokus öffnen: {artifact_id}",
            key=_widget_key(
                SSKey.SUMMARY_ACTION_WIDGET_PREFIX, f"activate.{artifact_id}"
            ),
            width="stretch",
        ):
            st.session_state[SSKey.SUMMARY_ACTIVE_ARTIFACT.value] = artifact_id
            st.rerun()


def _render_summary_results_workspace(*, brief: VacancyBrief) -> None:
    available_artifact_ids: list[str] = ["brief"]
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

    active_artifact_id = _resolve_active_artifact_id(
        available_artifact_ids=available_artifact_ids
    )
    st.subheader(f"Ergebnis-Fokus: {active_artifact_id}")
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
    with st.expander("JSON-Vorschau & Debug (optional)", expanded=False):
        snippet_limit = 380
        snippet = export_json_text[:snippet_limit]
        if len(export_json_text) > snippet_limit:
            snippet = f"{snippet}…"
        st.code(snippet, language="json")
        st.text_area(
            "Komplette JSON-Vorschau",
            value=export_json_text,
            height=240,
            disabled=True,
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

    # SUMMARY_ZONE: HERO
    _render_summary_hero(vm=vm)

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
    ) -> bool:
        clear_error()
        store = bool(st.session_state.get(SSKey.STORE_API_OUTPUT.value, False))
        try:
            with st.spinner(spinner_text):
                brief, usage = generate_vacancy_brief(
                    vm.job,
                    vm.answers,
                    model=resolved_brief_model,
                    selected_role_tasks=vm.artifacts.selected_role_tasks,
                    selected_skills=vm.artifacts.selected_skills,
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
            if brief_cached:
                st.info("Recruiting Brief aus dem Cache geladen.")
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

    def _resolve_brief_for_follow_up_action() -> VacancyBrief | None:
        brief_status, brief_model = _get_brief_status()
        if brief_status == "ready":
            return brief_model
        if brief_status == "missing":
            st.info(
                "Kein Recruiting Brief vorhanden. Bitte zuerst die Karte "
                "„Recruiting Brief generieren“ ausführen."
            )
            return None
        if brief_status == "invalid":
            st.warning(
                "Recruiting Brief ist ungültig. Bitte über „Recruiting Brief generieren“ neu erstellen."
            )
            return None
        st.info(
            "Recruiting Brief ist veraltet. Bitte über „Recruiting Brief generieren“ aktualisieren."
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

    def _render_job_ad_action_hub_inputs() -> None:
        st.markdown("**Selection Matrix (optional)**")
        selected_values, _ = _render_selection_matrix(job=vm.job, answers=vm.answers)
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
            vm.job,
            _build_selection_rows(vm.job, vm.answers),
        )
        if critical_gaps:
            st.info(
                "Hinweis: Kritische Lücken werden in der AGG-Checkliste markiert und nicht halluziniert."
            )
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

    supports_tabs = hasattr(st, "tabs")
    if supports_tabs:
        readiness_tab, facts_tab, artifacts_tab, export_tab, advanced_tab = (
            _build_summary_tabs()
        )

        with readiness_tab:
            _render_readiness_tab(vm=vm, action_registry=action_registry)

        with facts_tab:
            # SUMMARY_ZONE: FACTS
            _render_summary_facts_section(vm)

        with artifacts_tab:
            # SUMMARY_ZONE: PROCESSING_HUB
            _render_summary_processing_hub(
                action_registry=action_registry,
                resolved_brief_model=resolved_brief_model,
                show_job_ad_configuration_panel=False,
                show_export_bar=False,
            )
    else:
        _render_summary_processing_hub(
            action_registry=action_registry,
            resolved_brief_model=resolved_brief_model,
        )

    brief_dict = st.session_state.get(SSKey.BRIEF.value)
    if not brief_dict:
        st.info(
            "Noch kein Recruiting Brief verfügbar. Prüfe die Eingaben und versuche es erneut."
        )
        nav_buttons(ctx, disable_next=True)
        return

    try:
        brief = VacancyBrief.model_validate(brief_dict)
    except Exception:
        st.warning(
            "Recruiting Brief ist ungültig. Bitte über „Recruiting Brief generieren“ neu erstellen."
        )
        nav_buttons(ctx, disable_next=True)
        return

    if supports_tabs:
        with artifacts_tab:
            # SUMMARY_ZONE: RESULTS
            _render_summary_results_workspace(brief=brief)

        with export_tab:
            _render_export_bar(has_brief=True)
            _render_summary_export_workspace(brief=brief)

        with advanced_tab:
            if bool(st.session_state.get(SSKey.SUMMARY_CACHE_HIT.value, False)):
                st.caption("📦 Zusammenfassung: aus dem Cache geladen.")
            last_mode = st.session_state.get(SSKey.SUMMARY_LAST_MODE.value) or "unknown"
            last_models = (
                st.session_state.get(SSKey.SUMMARY_LAST_MODELS.value, {}) or {}
            )
            st.caption(
                f"🧠 Modus: `{last_mode}` · Modelle: Draft=`{last_models.get('draft_model', resolved_brief_model)}`"
            )
            if not is_advanced_mode:
                st.info(
                    "Advanced Studio ist im aktuellen UI-Modus reduziert. "
                    "Wechsle auf **Expert**, um Gehaltsprognose und Job-Ad-Editor zu öffnen."
                )
            else:
                with st.container(border=True):
                    st.markdown("### Gehaltsprognose")
                    render_salary_forecast_panel(vm.job, vm.answers)
                _render_job_ad_configuration_panel(action_registry=action_registry)
    else:
        _render_summary_results_workspace(brief=brief)

    nav_buttons(ctx, disable_next=True)


PAGE = WizardPage(
    key="summary",
    title_de="Zusammenfassung",
    icon="✅",
    render=render,
    requires_jobspec=True,
)
