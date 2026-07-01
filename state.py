# state.py
"""Session state management.

Streamlit re-runs the script on each interaction; st.session_state is the backbone
of a wizard workflow.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any, Dict, cast

import streamlit as st
from pydantic import ValidationError

from constants import (
    AUDIENCE_MODE_DEFAULT,
    AUDIENCE_MODE_VALUES,
    DEFAULT_ESCO_DATA_SOURCE_MODE,
    DEFAULT_ESCO_INDEX_STORAGE_PATH,
    DEFAULT_ESCO_RELEASE_LANE,
    DEFAULT_LANGUAGE,
    ESCO_ANCHOR_STATE_DEGRADED,
    ESCO_DATA_SOURCE_MODES,
    ESCO_SEMANTIC_EXPORT_MODE_DEGRADED,
    FactSourceType,
    JOBSPEC_SOURCE_LEGACY_TEXT,
    JOBSPEC_SOURCE_MANUAL,
    JOBSPEC_SOURCE_UPLOAD,
    JOBSPEC_SOURCE_VALUES,
    SSKey,
    UI_PREFERENCE_ANSWER_MODE,
    UI_PREFERENCE_CONFIDENCE_THRESHOLD,
    UI_PREFERENCE_DETAILS_EXPANDED_DEFAULT,
    UI_PREFERENCE_ESCO_MATCHING_STRICTNESS,
    UI_MODE_DEFAULT,
    UI_MODE_VALUES,
    UI_PREFERENCE_INFORMATION_DEPTH,
    UI_PREFERENCE_PII_REDUCTION,
    UI_PREFERENCE_REGIONAL_FOCUS,
    UI_PREFERENCE_SHOW_SOURCES_DEFAULT,
    UI_PREFERENCE_STEP_COMPACT,
    UI_PREFERENCE_UI_LANGUAGE,
    UI_PREFERENCE_WIZARD_DESIGN,
    UI_WIZARD_DESIGN_DEFAULT,
    UI_WIZARD_DESIGN_VALUES,
    STALE_REDESIGN_SESSION_KEY_PREFIXES,
    STEPS,
    SUMMARY_ACTIVE_ARTIFACT_IDS,
    SUMMARY_ARTIFACT_LEGACY_ALIASES,
    SUMMARY_SESSION_KEY_LEGACY_ALIASES,
    VACANCY_DRAFT_SCHEMA_VERSION,
)
from esco_semantics import (
    normalize_release_lane,
    selected_version_for_release_lane,
    sync_esco_semantic_state,
)
from intake_facts import (
    reset_intake_fact_evidence_state,
    reset_intake_fact_state,
    write_intake_fact,
    write_intake_fact_by_legacy_field,
)
from interview_process import INTERVIEW_INTERNAL_FLOW_DEFAULT
from question_progress import AnswerMeta, AnswerMetaMap, value_hash
from schemas import (
    EscoConceptRef,
    EscoMappingReport,
    EscoSemanticContext,
    EscoSuggestionItem,
)
from settings_openai import load_openai_settings
from state_store import StateStore, SummaryDirtyState
from summary_exports import (
    VACANCY_DRAFT_SCHEMA_ID,
    parse_vacancy_draft_json,
    vacancy_draft_state_fingerprint,
    vacancy_draft_to_json,
)
from usage_events import reset_usage_events

DEFAULT_ESCO_API_BASE_URL = "https://ec.europa.eu/esco/api/"

VACANCY_DRAFT_SESSION_KEYS: tuple[SSKey, ...] = (
    SSKey.CURRENT_STEP,
    SSKey.NAV_SELECTED,
    SSKey.LANGUAGE,
    SSKey.UI_MODE,
    SSKey.AUDIENCE_MODE,
    SSKey.UI_PREFERENCES,
    SSKey.OPEN_GROUPS,
    SSKey.SOURCE_TEXT,
    SSKey.SOURCE_REDACT_PII,
    SSKey.SOURCE_ACTIVE,
    SSKey.SOURCE_MANUAL_TEXT,
    SSKey.SOURCE_UPLOADED_TEXT,
    SSKey.SOURCE_UPLOAD_TEXT_INPUT,
    SSKey.JOB_EXTRACT,
    SSKey.INTAKE_FACTS,
    SSKey.INTAKE_FACT_EVIDENCE,
    SSKey.QUESTION_PLAN_BASE,
    SSKey.QUESTION_PLAN,
    SSKey.QUESTION_LIMITS,
    SSKey.OCCUPATION_PROFILE,
    SSKey.OCCUPATION_QUESTION_CONTEXT,
    SSKey.OCCUPATION_CLASSIFICATION_TRACE,
    SSKey.OCCUPATION_PACK_KEYS,
    SSKey.QUESTION_FLOW_PROVENANCE,
    SSKey.QUESTION_FLOW_FINGERPRINT,
    SSKey.ANSWERS,
    SSKey.ANSWER_META,
    SSKey.BRIEF,
    SSKey.SUMMARY_DIRTY,
    SSKey.SUMMARY_INPUT_FINGERPRINT,
    SSKey.SUMMARY_LAST_BRIEF_FINGERPRINT,
    SSKey.SUMMARY_ACTIVE_ARTIFACT,
    SSKey.SUMMARY_SHOW_JOB_AD_CONFIG,
    SSKey.SUMMARY_SELECTIONS,
    SSKey.SUMMARY_STYLEGUIDE_BLOCKS,
    SSKey.SUMMARY_CHANGE_REQUEST_BLOCKS,
    SSKey.SUMMARY_STYLEGUIDE_TEXT,
    SSKey.SUMMARY_CHANGE_REQUEST_TEXT,
    SSKey.SUMMARY_ARTIFACT_OPTIONS,
    SSKey.SUMMARY_ARTIFACT_CHANGE_REQUESTS,
    SSKey.SUMMARY_ARTIFACT_FINGERPRINTS,
    SSKey.JOB_AD_DRAFT_CUSTOM,
    SSKey.INTERVIEW_PREP_HR,
    SSKey.INTERVIEW_PREP_FACH,
    SSKey.BOOLEAN_SEARCH_STRING,
    SSKey.EMPLOYMENT_CONTRACT_DRAFT,
    SSKey.ESCO_RELEASE_LANE,
    SSKey.ESCO_LOOKUP_METADATA,
    SSKey.ESCO_ANCHOR_STATE,
    SSKey.ESCO_PRIMARY_ANCHOR,
    SSKey.ESCO_SECONDARY_ANCHORS,
    SSKey.ESCO_SEMANTIC_EXPORT_MODE,
    SSKey.ESCO_OCCUPATION_SELECTED,
    SSKey.ESCO_SELECTED_OCCUPATION_URI,
    SSKey.ESCO_OCCUPATION_PAYLOAD,
    SSKey.ESCO_OCCUPATION_RELATED_COUNTS,
    SSKey.ESCO_OCCUPATION_SKILL_GROUP_SHARE,
    SSKey.ESCO_OCCUPATION_CANDIDATES,
    SSKey.ESCO_MATCH_REASON,
    SSKey.ESCO_MATCH_CONFIDENCE,
    SSKey.ESCO_MATCH_PROVENANCE,
    SSKey.ESCO_SKILLS_SELECTED_MUST,
    SSKey.ESCO_SKILLS_SELECTED_NICE,
    SSKey.ESCO_SKILLS_REMOVED,
    SSKey.ESCO_CONFIRMED_ESSENTIAL_SKILLS,
    SSKey.ESCO_CONFIRMED_OPTIONAL_SKILLS,
    SSKey.ESCO_UNMAPPED_REQUIREMENT_TERMS,
    SSKey.ESCO_UNMAPPED_ROLE_TERMS,
    SSKey.ESCO_UNMAPPED_TERM_ACTIONS,
    SSKey.ESCO_UNRESOLVED_TERM_DECISIONS,
    SSKey.ESCO_SKILLS_MAPPING_REPORT,
    SSKey.ESCO_MATRIX_METADATA,
    SSKey.ESCO_MATRIX_LOADED,
    SSKey.ESCO_MATRIX_COVERAGE_ROWS,
    SSKey.ESCO_MATRIX_COVERAGE_CONTEXT,
    SSKey.COMPANY_WEBSITE_RESEARCH,
    SSKey.COMPANY_WEBSITE_SELECTED_MATCHES,
    SSKey.COMPANY_WEBSITE_FACT_REVIEW,
    SSKey.COMPANY_WEBSITE_MANUAL_URL,
    SSKey.ROLE_TASKS_JOBSPEC_SUGGESTED,
    SSKey.ROLE_TASKS_ESCO_SUGGESTED,
    SSKey.ROLE_TASKS_LLM_SUGGESTED,
    SSKey.ROLE_TASKS_SELECTED,
    SSKey.ROLE_TASKS_SUGGEST_COUNT,
    SSKey.ROLE_TASKS_JOBSPEC_PILLS,
    SSKey.ROLE_TASKS_ESCO_PILLS,
    SSKey.ROLE_TASKS_AI_PILLS,
    SSKey.INTERVIEW_INTERNAL_FLOW,
    SSKey.SKILLS_JOBSPEC_SUGGESTED,
    SSKey.SKILLS_LLM_SUGGESTED,
    SSKey.SKILLS_AI_INITIAL_GENERATED,
    SSKey.SKILLS_SELECTED,
    SSKey.SKILLS_SELECTED_STATUS,
    SSKey.SKILLS_SUGGEST_COUNT,
    SSKey.SKILLS_JOBSPEC_PILLS,
    SSKey.SKILLS_ESCO_PILLS,
    SSKey.SKILLS_AI_PILLS,
    SSKey.SKILLS_ESCO_LOAD_CLICKED,
    SSKey.SKILLS_ESCO_SEARCH,
    SSKey.SKILLS_ESCO_SORT,
    SSKey.BENEFITS_JOBSPEC_SUGGESTED,
    SSKey.BENEFITS_LLM_SUGGESTED,
    SSKey.BENEFITS_SELECTED,
    SSKey.BENEFITS_JOBSPEC_PILLS,
    SSKey.BENEFITS_CONTEXT_PILLS,
    SSKey.BENEFITS_AI_PILLS,
    SSKey.BENEFITS_SUGGEST_COUNT,
    SSKey.BENEFITS_AI_INITIAL_GENERATED,
    SSKey.BENEFITS_REGION_CONTEXT,
    SSKey.SALARY_SCENARIO_SKILLS_ADD,
    SSKey.SALARY_SCENARIO_SKILLS_REMOVE,
    SSKey.SALARY_SCENARIO_LOCATION_OVERRIDE,
    SSKey.SALARY_SCENARIO_LOCATION_CITY_OVERRIDE,
    SSKey.SALARY_SCENARIO_LOCATION_COUNTRY_OVERRIDE,
    SSKey.SALARY_SCENARIO_RADIUS_KM,
    SSKey.SALARY_SCENARIO_REMOTE_SHARE_PERCENT,
    SSKey.SALARY_SCENARIO_SENIORITY_OVERRIDE,
    SSKey.SALARY_SCENARIO_LAB_ROWS,
    SSKey.SALARY_SCENARIO_SELECTED_ROW_ID,
    SSKey.SALARY_FORECAST_SELECTED_SCENARIO,
    SSKey.SALARY_FORECAST_LAST_RESULT,
    SSKey.SALARY_FORECAST_INPUT_FINGERPRINT,
    SSKey.SALARY_FORECAST_INPUT_SELECTIONS,
    SSKey.SALARY_FORECAST_FACTOR_SELECTIONS,
    SSKey.SALARY_SCENARIO_CONTEXT_DEFAULTS,
)


@dataclass(frozen=True)
class VacancyDraftLoadResult:
    success: bool
    message: str
    saved_at: str = ""
    restored_step: str = ""
    restored_key_count: int = 0
    schema_version: str = ""


def _normalize_jobspec_source(source: str) -> str:
    normalized = str(source or "").strip().lower()
    if normalized == JOBSPEC_SOURCE_LEGACY_TEXT:
        return JOBSPEC_SOURCE_MANUAL
    if normalized in JOBSPEC_SOURCE_VALUES:
        return normalized
    return JOBSPEC_SOURCE_MANUAL


def _hash_text(value: object) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _safe_int(value: object, *, default: int = 0) -> int:
    try:
        return int(value or default)
    except (TypeError, ValueError):
        return default


def _upload_signature_parts(upload_signature: object) -> tuple[str, int]:
    if isinstance(upload_signature, (list, tuple)) and len(upload_signature) >= 2:
        return str(upload_signature[0] or ""), _safe_int(upload_signature[1])
    if isinstance(upload_signature, Mapping):
        return str(upload_signature.get("name") or ""), _safe_int(
            upload_signature.get("size")
        )
    return "", 0


def build_jobspec_source_fingerprint(
    source: str,
    text: str,
    *,
    file_meta: Mapping[str, Any] | None = None,
    upload_signature: object = None,
) -> str:
    """Return a non-sensitive fingerprint for the active jobspec source."""

    normalized_source = _normalize_jobspec_source(source)
    source_text = str(text or "")
    meta = file_meta if isinstance(file_meta, Mapping) else {}
    signature_name, signature_size = _upload_signature_parts(upload_signature)
    file_name = str(meta.get("name") or signature_name or "")
    file_size = _safe_int(meta.get("size"), default=signature_size)
    payload: dict[str, object] = {
        "source": normalized_source,
        "text_hash": _hash_text(source_text),
        "text_length": len(source_text),
    }
    if normalized_source == JOBSPEC_SOURCE_UPLOAD:
        payload.update(
            {
                "file_name_hash": _hash_text(file_name) if file_name else "",
                "file_size": file_size,
            }
        )
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _streamlit_esco_secret(key: str) -> object:
    try:
        section = st.secrets.get("esco")  # type: ignore[attr-defined]
    except Exception:
        return None
    if isinstance(section, Mapping):
        return section.get(key)
    return None


def _config_text_value(*values: object) -> str:
    for value in values:
        if value is None:
            continue
        normalized = str(value).strip()
        if normalized:
            return normalized
    return ""


def _apply_summary_legacy_key_aliases() -> None:
    """Populate canonical summary keys from compatible legacy aliases when possible."""

    for canonical_key, legacy_keys in SUMMARY_SESSION_KEY_LEGACY_ALIASES.items():
        canonical_name = canonical_key.value
        if canonical_name in st.session_state:
            continue
        for legacy_key in legacy_keys:
            if legacy_key not in st.session_state:
                continue
            st.session_state[canonical_name] = st.session_state[legacy_key]
            break


def _normalize_summary_active_artifact(raw_artifact_id: Any) -> str:
    normalized = str(raw_artifact_id or "").strip()
    if not normalized:
        return "brief"
    normalized_key = normalized.casefold()
    canonical = SUMMARY_ARTIFACT_LEGACY_ALIASES.get(
        normalized,
        SUMMARY_ARTIFACT_LEGACY_ALIASES.get(normalized_key, normalized_key),
    )
    return canonical if canonical in SUMMARY_ACTIVE_ARTIFACT_IDS else "brief"


def _clear_stale_redesign_state() -> None:
    """Drop stale redesign-only session keys while preserving canonical state."""

    canonical_keys = {key.value for key in SSKey}
    for session_key in list(st.session_state.keys()):
        if session_key in canonical_keys:
            continue
        if any(
            session_key.startswith(prefix)
            for prefix in STALE_REDESIGN_SESSION_KEY_PREFIXES
        ):
            st.session_state.pop(session_key, None)
            continue
        for legacy_keys in SUMMARY_SESSION_KEY_LEGACY_ALIASES.values():
            if session_key in legacy_keys:
                st.session_state.pop(session_key, None)
                break


def _clear_jobspec_fact_state(session_state: MutableMapping[str, Any]) -> None:
    fact_state_raw = session_state.get(SSKey.INTAKE_FACTS.value)
    evidence_state_raw = session_state.get(SSKey.INTAKE_FACT_EVIDENCE.value)
    fact_state = dict(fact_state_raw) if isinstance(fact_state_raw, Mapping) else {}
    evidence_state = (
        dict(evidence_state_raw) if isinstance(evidence_state_raw, Mapping) else {}
    )
    changed = False
    for fact_key, raw_evidence in list(evidence_state.items()):
        if not isinstance(raw_evidence, Mapping):
            continue
        if raw_evidence.get("source_type") == FactSourceType.JOBSPEC.value:
            evidence_state.pop(fact_key, None)
            fact_state.pop(fact_key, None)
            changed = True
            continue
        secondary_raw = raw_evidence.get("secondary_evidence")
        if not isinstance(secondary_raw, list):
            continue
        filtered_secondary = [
            entry
            for entry in secondary_raw
            if not (
                isinstance(entry, Mapping)
                and entry.get("source_type") == FactSourceType.JOBSPEC.value
            )
        ]
        if filtered_secondary == secondary_raw:
            continue
        entry = dict(raw_evidence)
        if filtered_secondary:
            entry["secondary_evidence"] = filtered_secondary
        else:
            entry.pop("secondary_evidence", None)
        evidence_state[fact_key] = entry
        changed = True
    if changed:
        session_state[SSKey.INTAKE_FACTS.value] = fact_state
        session_state[SSKey.INTAKE_FACT_EVIDENCE.value] = evidence_state


def _prune_auto_promoted_answers(session_state: MutableMapping[str, Any]) -> None:
    answers_raw = session_state.get(SSKey.ANSWERS.value)
    meta_raw = session_state.get(SSKey.ANSWER_META.value)
    answers = dict(answers_raw) if isinstance(answers_raw, Mapping) else {}
    meta = dict(meta_raw) if isinstance(meta_raw, Mapping) else {}
    changed = False
    for question_id, raw_meta in list(meta.items()):
        if not isinstance(raw_meta, Mapping):
            continue
        if raw_meta.get("touched"):
            continue
        if "last_value_hash" not in raw_meta:
            continue
        answers.pop(question_id, None)
        meta.pop(question_id, None)
        changed = True
    if changed:
        session_state[SSKey.ANSWERS.value] = answers
        session_state[SSKey.ANSWER_META.value] = meta


def _has_jobspec_source_dependent_state(session_state: Mapping[str, Any]) -> bool:
    if session_state.get(SSKey.JOB_EXTRACT.value) is not None:
        return True
    nullable_keys = (
        SSKey.QUESTION_PLAN_BASE,
        SSKey.QUESTION_PLAN,
        SSKey.OCCUPATION_PROFILE,
        SSKey.OCCUPATION_QUESTION_CONTEXT,
        SSKey.ESCO_OCCUPATION_SELECTED,
        SSKey.ESCO_OCCUPATION_PAYLOAD,
        SSKey.ESCO_MATCH_REASON,
        SSKey.ESCO_MATCH_CONFIDENCE,
        SSKey.ESCO_SKILLS_MAPPING_REPORT,
    )
    if any(session_state.get(key.value) is not None for key in nullable_keys):
        return True
    collection_keys = (
        SSKey.QUESTION_LIMITS,
        SSKey.OCCUPATION_CLASSIFICATION_TRACE,
        SSKey.OCCUPATION_PACK_KEYS,
        SSKey.QUESTION_FLOW_PROVENANCE,
        SSKey.JOBAD_CACHE_HIT,
        SSKey.ESCO_OCCUPATION_RELATED_COUNTS,
        SSKey.ESCO_OCCUPATION_SKILL_GROUP_SHARE,
        SSKey.ESCO_OCCUPATION_CANDIDATES,
        SSKey.ESCO_MATCH_PROVENANCE,
        SSKey.ESCO_SKILLS_SELECTED_MUST,
        SSKey.ESCO_SKILLS_SELECTED_NICE,
        SSKey.ESCO_SKILLS_REMOVED,
        SSKey.ESCO_CONFIRMED_ESSENTIAL_SKILLS,
        SSKey.ESCO_CONFIRMED_OPTIONAL_SKILLS,
        SSKey.ESCO_UNMAPPED_REQUIREMENT_TERMS,
        SSKey.ESCO_UNMAPPED_ROLE_TERMS,
        SSKey.ESCO_UNMAPPED_TERM_ACTIONS,
        SSKey.ESCO_UNRESOLVED_TERM_DECISIONS,
        SSKey.ESCO_MATRIX_COVERAGE_ROWS,
        SSKey.ROLE_TASKS_JOBSPEC_SUGGESTED,
        SSKey.ROLE_TASKS_ESCO_SUGGESTED,
        SSKey.ROLE_TASKS_JOBSPEC_PILLS,
        SSKey.ROLE_TASKS_ESCO_PILLS,
        SSKey.SKILLS_JOBSPEC_SUGGESTED,
        SSKey.SKILLS_JOBSPEC_PILLS,
        SSKey.SKILLS_ESCO_PILLS,
        SSKey.BENEFITS_JOBSPEC_SUGGESTED,
        SSKey.BENEFITS_JOBSPEC_PILLS,
        SSKey.SALARY_FORECAST_LAST_RESULT,
        SSKey.SALARY_FORECAST_INPUT_FINGERPRINT,
        SSKey.SALARY_FORECAST_INPUT_SELECTIONS,
        SSKey.SALARY_FORECAST_FACTOR_SELECTIONS,
        SSKey.SALARY_SCENARIO_CONTEXT_DEFAULTS,
    )
    if any(bool(session_state.get(key.value)) for key in collection_keys):
        return True
    if str(session_state.get(SSKey.QUESTION_FLOW_FINGERPRINT.value) or "").strip():
        return True
    if str(session_state.get(SSKey.ESCO_SELECTED_OCCUPATION_URI.value) or "").strip():
        return True
    if str(session_state.get(SSKey.LAST_ERROR.value) or "").strip():
        return True
    if str(session_state.get(SSKey.LAST_ERROR_DEBUG.value) or "").strip():
        return True
    evidence_raw = session_state.get(SSKey.INTAKE_FACT_EVIDENCE.value)
    if isinstance(evidence_raw, Mapping):
        for raw_evidence in evidence_raw.values():
            if not isinstance(raw_evidence, Mapping):
                continue
            if raw_evidence.get("source_type") == FactSourceType.JOBSPEC.value:
                return True
    meta_raw = session_state.get(SSKey.ANSWER_META.value)
    if isinstance(meta_raw, Mapping):
        return any(
            isinstance(raw_meta, Mapping)
            and not raw_meta.get("touched")
            and "last_value_hash" in raw_meta
            for raw_meta in meta_raw.values()
        )
    return False


def _reset_jobspec_source_dependent_state(
    session_state: MutableMapping[str, Any],
) -> None:
    session_state[SSKey.JOB_EXTRACT.value] = None
    session_state[SSKey.QUESTION_PLAN_BASE.value] = None
    session_state[SSKey.QUESTION_PLAN.value] = None
    session_state[SSKey.QUESTION_LIMITS.value] = {}
    session_state[SSKey.OCCUPATION_PROFILE.value] = None
    session_state[SSKey.OCCUPATION_QUESTION_CONTEXT.value] = None
    session_state[SSKey.OCCUPATION_CLASSIFICATION_TRACE.value] = []
    session_state[SSKey.OCCUPATION_PACK_KEYS.value] = []
    session_state[SSKey.QUESTION_FLOW_PROVENANCE.value] = {}
    session_state[SSKey.QUESTION_FLOW_FINGERPRINT.value] = ""
    _clear_jobspec_fact_state(session_state)
    _prune_auto_promoted_answers(session_state)

    session_state[SSKey.ESCO_OCCUPATION_SELECTED.value] = None
    session_state[SSKey.ESCO_SELECTED_OCCUPATION_URI.value] = ""
    session_state[SSKey.ESCO_OCCUPATION_PAYLOAD.value] = None
    session_state[SSKey.ESCO_OCCUPATION_RELATED_COUNTS.value] = {}
    session_state[SSKey.ESCO_OCCUPATION_SKILL_GROUP_SHARE.value] = []
    session_state[SSKey.ESCO_OCCUPATION_CANDIDATES.value] = []
    session_state[SSKey.ESCO_MATCH_REASON.value] = None
    session_state[SSKey.ESCO_MATCH_CONFIDENCE.value] = None
    session_state[SSKey.ESCO_MATCH_PROVENANCE.value] = []
    session_state[SSKey.ESCO_LAST_DATA_SOURCE.value] = ""
    session_state[SSKey.ESCO_LOOKUP_METADATA.value] = {}
    session_state[SSKey.ESCO_SKILLS_SELECTED_MUST.value] = []
    session_state[SSKey.ESCO_SKILLS_SELECTED_NICE.value] = []
    session_state[SSKey.ESCO_SKILLS_REMOVED.value] = []
    session_state[SSKey.ESCO_CONFIRMED_ESSENTIAL_SKILLS.value] = []
    session_state[SSKey.ESCO_CONFIRMED_OPTIONAL_SKILLS.value] = []
    session_state[SSKey.ESCO_UNMAPPED_REQUIREMENT_TERMS.value] = []
    session_state[SSKey.ESCO_UNMAPPED_ROLE_TERMS.value] = []
    session_state[SSKey.ESCO_UNMAPPED_TERM_ACTIONS.value] = {}
    session_state[SSKey.ESCO_UNRESOLVED_TERM_DECISIONS.value] = []
    session_state[SSKey.ESCO_SKILLS_MAPPING_REPORT.value] = None
    session_state[SSKey.ESCO_MATRIX_COVERAGE_ROWS.value] = []
    session_state[SSKey.ESCO_MATRIX_COVERAGE_CONTEXT.value] = {
        "reason": "source_changed",
        "occupation_group": "",
        "rows": 0,
    }
    session_state[SSKey.ESCO_ANCHOR_STATE.value] = ESCO_ANCHOR_STATE_DEGRADED
    session_state[SSKey.ESCO_PRIMARY_ANCHOR.value] = None
    session_state[SSKey.ESCO_SECONDARY_ANCHORS.value] = []
    session_state[SSKey.ESCO_SEMANTIC_EXPORT_MODE.value] = (
        ESCO_SEMANTIC_EXPORT_MODE_DEGRADED
    )
    session_state[SSKey.ESCO_CAPABILITY_SNAPSHOT.value] = {}

    session_state[SSKey.ROLE_TASKS_JOBSPEC_SUGGESTED.value] = []
    session_state[SSKey.ROLE_TASKS_ESCO_SUGGESTED.value] = []
    session_state[SSKey.ROLE_TASKS_LLM_SUGGESTED.value] = []
    session_state[SSKey.ROLE_TASKS_JOBSPEC_PILLS.value] = []
    session_state[SSKey.ROLE_TASKS_ESCO_PILLS.value] = []
    session_state[SSKey.SKILLS_JOBSPEC_SUGGESTED.value] = []
    session_state[SSKey.SKILLS_LLM_SUGGESTED.value] = []
    session_state[SSKey.SKILLS_AI_INITIAL_GENERATED.value] = False
    session_state[SSKey.SKILLS_JOBSPEC_PILLS.value] = []
    session_state[SSKey.SKILLS_ESCO_PILLS.value] = []
    session_state[SSKey.SKILLS_AI_GENERATE_CLICKED.value] = False
    session_state[SSKey.BENEFITS_JOBSPEC_SUGGESTED.value] = []
    session_state[SSKey.BENEFITS_LLM_SUGGESTED.value] = []
    session_state[SSKey.BENEFITS_JOBSPEC_PILLS.value] = []
    session_state[SSKey.BENEFITS_AI_GENERATE_CLICKED.value] = False
    session_state[SSKey.BENEFITS_AI_INITIAL_GENERATED.value] = False

    session_state[SSKey.SALARY_FORECAST_LAST_RESULT.value] = {}
    session_state[SSKey.SALARY_FORECAST_INPUT_FINGERPRINT.value] = {}
    session_state[SSKey.SALARY_FORECAST_INPUT_SELECTIONS.value] = {}
    session_state[SSKey.SALARY_FORECAST_FACTOR_SELECTIONS.value] = {}
    session_state[SSKey.SALARY_SCENARIO_CONTEXT_DEFAULTS.value] = {}
    session_state[SSKey.JOBAD_CACHE_HIT.value] = {}
    session_state[SSKey.LAST_ERROR.value] = None
    session_state[SSKey.LAST_ERROR_DEBUG.value] = None
    sync_esco_semantic_state(session_state)


def apply_jobspec_source_change(
    source: str,
    text: str,
    *,
    file_meta: Mapping[str, Any] | None = None,
    upload_signature: object = None,
    explicit_reset: bool = False,
    session_state: MutableMapping[str, Any] | None = None,
) -> str:
    """Set the active jobspec source and clear stale source-derived state."""

    target_state = session_state if session_state is not None else st.session_state
    normalized_source = _normalize_jobspec_source(source)
    source_text = str(text or "")
    fingerprint = build_jobspec_source_fingerprint(
        normalized_source,
        source_text,
        file_meta=file_meta,
        upload_signature=upload_signature,
    )
    current_fingerprint = str(
        target_state.get(SSKey.SOURCE_ACTIVE_FINGERPRINT.value, "") or ""
    )
    should_reset = explicit_reset or (
        current_fingerprint != fingerprint
        and (bool(current_fingerprint) or _has_jobspec_source_dependent_state(target_state))
    )
    if should_reset:
        _reset_jobspec_source_dependent_state(target_state)
    target_state[SSKey.SOURCE_TEXT.value] = source_text
    target_state[SSKey.SOURCE_ACTIVE.value] = normalized_source
    target_state[SSKey.SOURCE_ACTIVE_FINGERPRINT.value] = fingerprint
    if normalized_source == JOBSPEC_SOURCE_UPLOAD:
        if isinstance(file_meta, Mapping):
            target_state[SSKey.SOURCE_FILE_META.value] = dict(file_meta)
    else:
        target_state[SSKey.SOURCE_FILE_META.value] = {}
    return fingerprint


@dataclass(frozen=True)
class EscoCoverageSnapshot:
    selected_occupation_uri: str
    confirmed_essential_skills: list[Dict[str, str]]
    confirmed_optional_skills: list[Dict[str, str]]
    unmapped_requirement_terms: list[str]
    essential_total: int
    essential_covered: int
    optional_total: int
    optional_covered: int

    @property
    def essential_coverage_percent(self) -> int:
        if self.essential_total <= 0:
            return 0
        return round((self.essential_covered / self.essential_total) * 100)

    @property
    def optional_coverage_percent(self) -> int:
        if self.optional_total <= 0:
            return 0
        return round((self.optional_covered / self.optional_total) * 100)


@dataclass(frozen=True)
class EscoAnchorStatus:
    anchor_confirmed: bool
    selected_occupation: Dict[str, Any] | None
    status_reason: str


def get_model_override() -> str | None:
    """Return a cleaned model override from the UI, if provided."""

    model_override = st.session_state.get(SSKey.MODEL.value)
    if isinstance(model_override, str):
        cleaned_override = model_override.strip()
        if cleaned_override:
            return cleaned_override
    return None


def _default_ui_preferences() -> dict[str, Any]:
    return {
        UI_PREFERENCE_ANSWER_MODE: "balanced",
        UI_PREFERENCE_INFORMATION_DEPTH: "standard",
        UI_PREFERENCE_SHOW_SOURCES_DEFAULT: True,
        UI_PREFERENCE_CONFIDENCE_THRESHOLD: 0.6,
        UI_PREFERENCE_PII_REDUCTION: True,
        UI_PREFERENCE_DETAILS_EXPANDED_DEFAULT: False,
        UI_PREFERENCE_STEP_COMPACT: {},
        UI_PREFERENCE_UI_LANGUAGE: DEFAULT_LANGUAGE,
        UI_PREFERENCE_WIZARD_DESIGN: UI_WIZARD_DESIGN_DEFAULT,
    }


def normalize_ui_preferences(raw_preferences: Any) -> dict[str, Any]:
    defaults = _default_ui_preferences()
    normalized = dict(defaults)
    if isinstance(raw_preferences, dict):
        normalized.update(raw_preferences)
    for retired_key in (
        UI_PREFERENCE_ESCO_MATCHING_STRICTNESS,
        UI_PREFERENCE_REGIONAL_FOCUS,
    ):
        normalized.pop(retired_key, None)
    if not isinstance(normalized.get(UI_PREFERENCE_STEP_COMPACT), dict):
        normalized[UI_PREFERENCE_STEP_COMPACT] = {}
    language = (
        str(normalized.get(UI_PREFERENCE_UI_LANGUAGE, DEFAULT_LANGUAGE)).strip().lower()
    )
    normalized[UI_PREFERENCE_UI_LANGUAGE] = (
        language if language in {"de", "en"} else DEFAULT_LANGUAGE
    )
    wizard_design = (
        str(
            normalized.get(UI_PREFERENCE_WIZARD_DESIGN, UI_WIZARD_DESIGN_DEFAULT)
        )
        .strip()
        .lower()
    )
    normalized[UI_PREFERENCE_WIZARD_DESIGN] = (
        wizard_design
        if wizard_design in UI_WIZARD_DESIGN_VALUES
        else UI_WIZARD_DESIGN_DEFAULT
    )
    confidence = normalized.get(UI_PREFERENCE_CONFIDENCE_THRESHOLD)
    try:
        normalized[UI_PREFERENCE_CONFIDENCE_THRESHOLD] = min(
            0.95, max(0.05, float(confidence))
        )
    except (TypeError, ValueError):
        normalized[UI_PREFERENCE_CONFIDENCE_THRESHOLD] = defaults[
            UI_PREFERENCE_CONFIDENCE_THRESHOLD
        ]
    for key in (
        UI_PREFERENCE_SHOW_SOURCES_DEFAULT,
        UI_PREFERENCE_PII_REDUCTION,
        UI_PREFERENCE_DETAILS_EXPANDED_DEFAULT,
    ):
        normalized[key] = bool(normalized.get(key, defaults[key]))
    return normalized


def _normalize_audience_mode(raw_mode: Any) -> str:
    mode = str(raw_mode or "").strip().lower()
    if mode in AUDIENCE_MODE_VALUES:
        return mode
    return AUDIENCE_MODE_DEFAULT


def _sync_source_redaction_from_preferences() -> None:
    preferences = normalize_ui_preferences(
        st.session_state.get(SSKey.UI_PREFERENCES.value)
    )
    st.session_state[SSKey.UI_PREFERENCES.value] = preferences
    st.session_state[SSKey.SOURCE_REDACT_PII.value] = bool(
        preferences[UI_PREFERENCE_PII_REDUCTION]
    )


def get_active_model() -> str:
    """Return UI override model or OpenAI settings fallback model."""

    return get_model_override() or load_openai_settings().openai_model


def init_session_state() -> None:
    _apply_summary_legacy_key_aliases()
    configured_language = st.session_state.get(SSKey.LANGUAGE.value, DEFAULT_LANGUAGE)
    if not isinstance(configured_language, str) or not configured_language.strip():
        configured_language = DEFAULT_LANGUAGE
    configured_language = configured_language.strip().lower()
    if configured_language not in {"de", "en"}:
        configured_language = DEFAULT_LANGUAGE
    configured_esco_base_url = _config_text_value(
        _streamlit_esco_secret("api_base_url"),
        os.getenv("ESCO_API_BASE_URL", ""),
        DEFAULT_ESCO_API_BASE_URL,
    )
    configured_esco_release_lane = normalize_release_lane(
        _config_text_value(
            _streamlit_esco_secret("release_lane"),
            os.getenv("ESCO_RELEASE_LANE", DEFAULT_ESCO_RELEASE_LANE),
        )
    )
    configured_esco_selected_version = _config_text_value(
        _streamlit_esco_secret("selected_version"),
        os.getenv("ESCO_SELECTED_VERSION", ""),
        selected_version_for_release_lane(configured_esco_release_lane),
    )
    configured_esco_language = _config_text_value(
        _streamlit_esco_secret("language"),
        configured_language,
    ).lower()
    if configured_esco_language not in {"de", "en"}:
        configured_esco_language = configured_language
    configured_esco_data_source_mode = _config_text_value(
        _streamlit_esco_secret("data_source_mode"),
        os.getenv("ESCO_DATA_SOURCE_MODE", DEFAULT_ESCO_DATA_SOURCE_MODE),
    ).lower()
    if configured_esco_data_source_mode not in ESCO_DATA_SOURCE_MODES:
        configured_esco_data_source_mode = DEFAULT_ESCO_DATA_SOURCE_MODE
    configured_esco_fallback_language = _config_text_value(
        _streamlit_esco_secret("fallback_language"),
        os.getenv("ESCO_FALLBACK_LANGUAGE", ""),
        "en" if configured_language != "en" else "de",
    ).lower()
    configured_esco_api_mode = _config_text_value(
        _streamlit_esco_secret("api_mode"),
        os.getenv("ESCO_API_MODE", "hosted"),
        "hosted",
    ).lower()
    configured_esco_index_storage_path = _config_text_value(
        _streamlit_esco_secret("index_storage_path"),
        os.getenv("ESCO_INDEX_STORAGE_PATH", DEFAULT_ESCO_INDEX_STORAGE_PATH),
        DEFAULT_ESCO_INDEX_STORAGE_PATH,
    )
    configured_esco_index_version = _config_text_value(
        _streamlit_esco_secret("index_version"),
        os.getenv("ESCO_INDEX_VERSION", ""),
        configured_esco_selected_version,
    )

    default_ui_preferences = _default_ui_preferences()
    default_ui_preferences[UI_PREFERENCE_UI_LANGUAGE] = configured_language

    defaults: Dict[str, Any] = {
        SSKey.CURRENT_STEP.value: STEPS[0].key,
        SSKey.LAST_RENDERED_STEP.value: None,
        SSKey.NAV_SELECTED.value: STEPS[0].key,
        SSKey.NAV_SYNC_PENDING.value: False,
        SSKey.NAV_DEEP_LINK_TARGET.value: {},
        SSKey.LANGUAGE.value: configured_language,
        SSKey.MODEL.value: load_openai_settings().openai_model,
        SSKey.STORE_API_OUTPUT.value: False,
        SSKey.DRAFT_RESUME_NOTICE.value: None,
        SSKey.DRAFT_LAST_SAVED_FINGERPRINT.value: "",
        SSKey.SOURCE_TEXT.value: "",
        SSKey.SOURCE_FILE_META.value: {},
        SSKey.SOURCE_REDACT_PII.value: True,
        SSKey.SOURCE_ACTIVE.value: JOBSPEC_SOURCE_MANUAL,
        SSKey.SOURCE_ACTIVE_FINGERPRINT.value: "",
        SSKey.SOURCE_MANUAL_TEXT.value: "",
        SSKey.SOURCE_UPLOADED_TEXT.value: "",
        SSKey.SOURCE_UPLOAD_TEXT_INPUT.value: "",
        SSKey.SOURCE_UPLOAD_SIGNATURE.value: None,
        SSKey.JOB_EXTRACT.value: None,
        SSKey.INTAKE_FACTS.value: {},
        SSKey.INTAKE_FACT_EVIDENCE.value: {},
        SSKey.QUESTION_PLAN_BASE.value: None,
        SSKey.QUESTION_PLAN.value: None,
        SSKey.QUESTION_LIMITS.value: {},
        SSKey.OCCUPATION_PROFILE.value: None,
        SSKey.OCCUPATION_QUESTION_CONTEXT.value: None,
        SSKey.OCCUPATION_CLASSIFICATION_TRACE.value: [],
        SSKey.OCCUPATION_PACK_KEYS.value: [],
        SSKey.QUESTION_FLOW_PROVENANCE.value: {},
        SSKey.QUESTION_FLOW_FINGERPRINT.value: "",
        SSKey.ANSWERS.value: {},
        SSKey.ANSWER_META.value: {},
        SSKey.UI_MODE.value: UI_MODE_DEFAULT,
        SSKey.AUDIENCE_MODE.value: AUDIENCE_MODE_DEFAULT,
        SSKey.UI_PREFERENCES.value: default_ui_preferences,
        SSKey.OPEN_GROUPS.value: {},
        SSKey.INTRO_CYCLE_FOCUS.value: None,
        SSKey.BRIEF.value: None,
        SSKey.LAST_ERROR.value: None,
        SSKey.LAST_ERROR_DEBUG.value: None,
        SSKey.OPENAI_LAST_STRUCTURED_OUTPUT_PATH.value: None,
        SSKey.OPENAI_DEBUG_ERRORS.value: False,
        SSKey.DEBUG.value: False,
        SSKey.PERF_FRAGMENT_PILOT_ENABLED.value: False,
        SSKey.CONTENT_SHARING_CONSENT.value: False,
        SSKey.LLM_RESPONSE_CACHE.value: {},
        SSKey.USAGE_EVENTS.value: [],
        SSKey.JOBAD_CACHE_HIT.value: {},
        SSKey.SUMMARY_CACHE_HIT.value: False,
        SSKey.SUMMARY_DIRTY.value: False,
        SSKey.SUMMARY_INPUT_FINGERPRINT.value: "",
        SSKey.SUMMARY_LAST_BRIEF_FINGERPRINT.value: "",
        SSKey.SUMMARY_ACTIVE_ARTIFACT.value: "brief",
        SSKey.SUMMARY_SHOW_JOB_AD_CONFIG.value: False,
        SSKey.SUMMARY_LAST_MODE.value: None,
        SSKey.SUMMARY_LAST_MODELS.value: {},
        SSKey.SUMMARY_FACTS_SEARCH.value: "",
        SSKey.SUMMARY_FACTS_STATUS_FILTER.value: "Alle",
        SSKey.SUMMARY_SELECTIONS.value: {},
        SSKey.SUMMARY_STYLEGUIDE_BLOCKS.value: [],
        SSKey.SUMMARY_CHANGE_REQUEST_BLOCKS.value: [],
        SSKey.SUMMARY_STYLEGUIDE_TEXT.value: "",
        SSKey.SUMMARY_CHANGE_REQUEST_TEXT.value: "",
        SSKey.SUMMARY_ARTIFACT_OPTIONS.value: {},
        SSKey.SUMMARY_ARTIFACT_CHANGE_REQUESTS.value: {},
        SSKey.SUMMARY_ARTIFACT_FINGERPRINTS.value: {},
        SSKey.SUMMARY_ARTIFACT_LAST_ERROR.value: {},
        SSKey.SUMMARY_LOGO.value: None,
        SSKey.JOB_AD_DRAFT_CUSTOM.value: None,
        SSKey.JOB_AD_LAST_USAGE.value: {},
        SSKey.INTERVIEW_PREP_HR.value: None,
        SSKey.INTERVIEW_PREP_HR_LAST_USAGE.value: {},
        SSKey.INTERVIEW_PREP_HR_CACHE_HIT.value: False,
        SSKey.INTERVIEW_PREP_HR_LAST_MODE.value: None,
        SSKey.INTERVIEW_PREP_HR_LAST_MODELS.value: {},
        SSKey.INTERVIEW_PREP_FACH.value: None,
        SSKey.INTERVIEW_PREP_FACH_LAST_USAGE.value: {},
        SSKey.INTERVIEW_PREP_FACH_CACHE_HIT.value: False,
        SSKey.INTERVIEW_PREP_FACH_LAST_MODE.value: None,
        SSKey.INTERVIEW_PREP_FACH_LAST_MODELS.value: {},
        SSKey.BOOLEAN_SEARCH_STRING.value: None,
        SSKey.BOOLEAN_SEARCH_LAST_USAGE.value: {},
        SSKey.BOOLEAN_SEARCH_CACHE_HIT.value: False,
        SSKey.BOOLEAN_SEARCH_LAST_MODE.value: None,
        SSKey.BOOLEAN_SEARCH_LAST_MODELS.value: {},
        SSKey.EMPLOYMENT_CONTRACT_DRAFT.value: None,
        SSKey.EMPLOYMENT_CONTRACT_LAST_USAGE.value: {},
        SSKey.EMPLOYMENT_CONTRACT_CACHE_HIT.value: False,
        SSKey.EMPLOYMENT_CONTRACT_LAST_MODE.value: None,
        SSKey.EMPLOYMENT_CONTRACT_LAST_MODELS.value: {},
        SSKey.ESCO_CONFIG.value: {
            "base_url": configured_esco_base_url,
            "release_lane": configured_esco_release_lane,
            "selected_version": configured_esco_selected_version,
            "language": configured_esco_language,
            "fallback_language": configured_esco_fallback_language,
            "view_obsolete": False,
            "api_mode": configured_esco_api_mode or "hosted",
            "data_source_mode": configured_esco_data_source_mode,
            "index_storage_path": configured_esco_index_storage_path,
            "index_version": configured_esco_index_version,
        },
        SSKey.ESCO_LAST_DATA_SOURCE.value: "",
        SSKey.ESCO_LOOKUP_METADATA.value: {},
        SSKey.ESCO_RELEASE_LANE.value: configured_esco_release_lane,
        SSKey.ESCO_ANCHOR_STATE.value: ESCO_ANCHOR_STATE_DEGRADED,
        SSKey.ESCO_PRIMARY_ANCHOR.value: None,
        SSKey.ESCO_SECONDARY_ANCHORS.value: [],
        SSKey.ESCO_SEMANTIC_EXPORT_MODE.value: ESCO_SEMANTIC_EXPORT_MODE_DEGRADED,
        SSKey.ESCO_CAPABILITY_SNAPSHOT.value: {},
        SSKey.ESCO_OCCUPATION_SELECTED.value: None,
        SSKey.ESCO_SELECTED_OCCUPATION_URI.value: "",
        SSKey.ESCO_OCCUPATION_PAYLOAD.value: None,
        SSKey.ESCO_OCCUPATION_RELATED_COUNTS.value: {},
        SSKey.ESCO_OCCUPATION_SKILL_GROUP_SHARE.value: [],
        SSKey.ESCO_OCCUPATION_CANDIDATES.value: [],
        SSKey.ESCO_MATCH_REASON.value: None,
        SSKey.ESCO_MATCH_CONFIDENCE.value: None,
        SSKey.ESCO_MATCH_PROVENANCE.value: [],
        SSKey.ESCO_SKILLS_SELECTED_MUST.value: [],
        SSKey.ESCO_SKILLS_SELECTED_NICE.value: [],
        SSKey.ESCO_SKILLS_REMOVED.value: [],
        SSKey.ESCO_CONFIRMED_ESSENTIAL_SKILLS.value: [],
        SSKey.ESCO_CONFIRMED_OPTIONAL_SKILLS.value: [],
        SSKey.ESCO_UNMAPPED_REQUIREMENT_TERMS.value: [],
        SSKey.ESCO_UNMAPPED_ROLE_TERMS.value: [],
        SSKey.ESCO_UNMAPPED_TERM_ACTIONS.value: {},
        SSKey.ESCO_UNRESOLVED_TERM_DECISIONS.value: [],
        SSKey.ESCO_SKILLS_MAPPING_REPORT.value: None,
        SSKey.ESCO_SKILL_DETAIL_CACHE.value: {},
        SSKey.ESCO_OCCUPATION_TITLE_VARIANTS.value: {},
        SSKey.ESCO_NEGATIVE_CACHE.value: {},
        SSKey.ESCO_MIGRATION_LOG.value: [],
        SSKey.ESCO_MIGRATION_PENDING.value: None,
        SSKey.ESCO_MATRIX_ENABLED.value: bool(
            os.getenv("ESCO_MATRIX_ENABLED", "").strip().lower() in {"1", "true", "yes"}
        ),
        SSKey.ESCO_MATRIX_METADATA.value: {"source": "", "version": "", "records": 0},
        SSKey.ESCO_MATRIX_LOADED.value: False,
        SSKey.ESCO_MATRIX_COVERAGE_ROWS.value: [],
        SSKey.ESCO_MATRIX_COVERAGE_CONTEXT.value: {
            "reason": "no_matrix_loaded",
            "occupation_group": "",
            "rows": 0,
        },
        SSKey.COMPANY_WEBSITE_RESEARCH.value: {},
        SSKey.COMPANY_WEBSITE_SELECTED_MATCHES.value: [],
        SSKey.COMPANY_WEBSITE_FACT_REVIEW.value: {},
        SSKey.COMPANY_WEBSITE_LAST_ERROR.value: None,
        SSKey.COMPANY_WEBSITE_MANUAL_URL.value: "",
        SSKey.ROLE_TASKS_JOBSPEC_SUGGESTED.value: [],
        SSKey.ROLE_TASKS_ESCO_SUGGESTED.value: [],
        SSKey.ROLE_TASKS_LLM_SUGGESTED.value: [],
        SSKey.ROLE_TASKS_SELECTED.value: [],
        SSKey.ROLE_TASKS_SUGGEST_COUNT.value: 5,
        SSKey.ROLE_TASKS_JOBSPEC_PILLS.value: [],
        SSKey.ROLE_TASKS_ESCO_PILLS.value: [],
        SSKey.ROLE_TASKS_AI_PILLS.value: [],
        SSKey.ROLE_TASKS_SELECTED_BULK_BUFFER.value: [],
        SSKey.INTERVIEW_INTERNAL_FLOW.value: dict(INTERVIEW_INTERNAL_FLOW_DEFAULT),
        SSKey.SKILLS_JOBSPEC_SUGGESTED.value: [],
        SSKey.SKILLS_LLM_SUGGESTED.value: [],
        SSKey.SKILLS_AI_INITIAL_GENERATED.value: False,
        SSKey.SKILLS_SELECTED.value: [],
        SSKey.SKILLS_SELECTED_STATUS.value: {},
        SSKey.SKILLS_SUGGEST_COUNT.value: 5,
        SSKey.SKILLS_JOBSPEC_PILLS.value: [],
        SSKey.SKILLS_ESCO_PILLS.value: [],
        SSKey.SKILLS_AI_PILLS.value: [],
        SSKey.SKILLS_SELECTED_BULK_BUFFER.value: [],
        SSKey.SKILLS_ESCO_LOAD_CLICKED.value: False,
        SSKey.SKILLS_ESCO_SEARCH.value: "",
        SSKey.SKILLS_ESCO_SORT.value: "alphabetisch",
        SSKey.SKILLS_AI_GENERATE_CLICKED.value: False,
        SSKey.BENEFITS_JOBSPEC_SUGGESTED.value: [],
        SSKey.BENEFITS_LLM_SUGGESTED.value: [],
        SSKey.BENEFITS_SELECTED.value: [],
        SSKey.BENEFITS_SELECTED_BULK_BUFFER.value: [],
        SSKey.BENEFITS_JOBSPEC_PILLS.value: [],
        SSKey.BENEFITS_CONTEXT_PILLS.value: [],
        SSKey.BENEFITS_AI_PILLS.value: [],
        SSKey.BENEFITS_SUGGEST_COUNT.value: 5,
        SSKey.BENEFITS_AI_GENERATE_CLICKED.value: False,
        SSKey.BENEFITS_AI_INITIAL_GENERATED.value: False,
        SSKey.BENEFITS_REGION_CONTEXT.value: "",
        SSKey.SALARY_SCENARIO_SKILLS_ADD.value: [],
        SSKey.SALARY_SCENARIO_SKILLS_REMOVE.value: [],
        SSKey.SALARY_SCENARIO_LOCATION_OVERRIDE.value: "",
        SSKey.SALARY_SCENARIO_LOCATION_CITY_OVERRIDE.value: "",
        SSKey.SALARY_SCENARIO_LOCATION_COUNTRY_OVERRIDE.value: "",
        SSKey.SALARY_SCENARIO_RADIUS_KM.value: 50,
        SSKey.SALARY_SCENARIO_REMOTE_SHARE_PERCENT.value: 0,
        SSKey.SALARY_SCENARIO_SENIORITY_OVERRIDE.value: "",
        SSKey.SALARY_SCENARIO_LAB_ROWS.value: [],
        SSKey.SALARY_SCENARIO_SELECTED_ROW_ID.value: "",
        SSKey.SALARY_SCENARIO_PENDING_SKILLS_ADD.value: None,
        SSKey.SALARY_SCENARIO_PENDING_SKILLS_REMOVE.value: None,
        SSKey.SALARY_SCENARIO_PENDING_LOCATION_CITY_OVERRIDE.value: None,
        SSKey.SALARY_SCENARIO_PENDING_RADIUS_KM.value: None,
        SSKey.SALARY_SCENARIO_PENDING_REMOTE_SHARE_PERCENT.value: None,
        SSKey.SALARY_SCENARIO_PENDING_SENIORITY_OVERRIDE.value: None,
        SSKey.SALARY_SCENARIO_APPLY_PENDING_UPDATE.value: False,
        SSKey.SALARY_SCENARIO_PENDING_SELECTED_ROW_ID.value: None,
        SSKey.SALARY_FORECAST_SELECTED_SCENARIO.value: "base",
        SSKey.SALARY_FORECAST_LAST_RESULT.value: {},
        SSKey.SALARY_FORECAST_INPUT_FINGERPRINT.value: {},
        SSKey.SALARY_FORECAST_INPUT_SELECTIONS.value: {},
        SSKey.SALARY_FORECAST_FACTOR_SELECTIONS.value: {},
        SSKey.SALARY_SCENARIO_CONTEXT_DEFAULTS.value: {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    st.session_state[SSKey.SUMMARY_ACTIVE_ARTIFACT.value] = (
        _normalize_summary_active_artifact(
            st.session_state.get(SSKey.SUMMARY_ACTIVE_ARTIFACT.value)
        )
    )
    preferences = normalize_ui_preferences(
        st.session_state.get(SSKey.UI_PREFERENCES.value)
    )
    active_language = str(preferences.get(UI_PREFERENCE_UI_LANGUAGE) or configured_language)
    if active_language not in {"de", "en"}:
        active_language = DEFAULT_LANGUAGE
    st.session_state[SSKey.LANGUAGE.value] = active_language
    preferences[UI_PREFERENCE_UI_LANGUAGE] = active_language
    st.session_state[SSKey.UI_PREFERENCES.value] = preferences
    esco_config = st.session_state.get(SSKey.ESCO_CONFIG.value)
    if isinstance(esco_config, dict):
        esco_language = str(esco_config.get("language") or active_language).strip().lower()
        if esco_language not in {"de", "en"}:
            esco_language = active_language
        fallback_language = str(esco_config.get("fallback_language") or "").strip().lower()
        if fallback_language not in {"de", "en"}:
            fallback_language = "en" if esco_language == "de" else "de"
        st.session_state[SSKey.ESCO_CONFIG.value] = {
            **esco_config,
            "language": esco_language,
            "fallback_language": fallback_language,
        }
    sync_esco_semantic_state(st.session_state)
    _sync_source_redaction_from_preferences()


def build_vacancy_draft_json(
    session_state: Mapping[str, Any] | None = None,
) -> str:
    """Return an explicit, allowlisted JSON draft for the current vacancy."""

    target_state = session_state if session_state is not None else st.session_state
    return vacancy_draft_to_json(
        target_state,
        allowed_keys=VACANCY_DRAFT_SESSION_KEYS,
    )


def build_vacancy_draft_fingerprint(
    session_state: Mapping[str, Any] | None = None,
) -> str:
    """Return a stable fingerprint for the current explicit draft payload."""

    target_state = session_state if session_state is not None else st.session_state
    return vacancy_draft_state_fingerprint(
        target_state,
        allowed_keys=VACANCY_DRAFT_SESSION_KEYS,
    )


def _extract_vacancy_draft_state(
    payload: Mapping[str, Any],
) -> tuple[dict[str, Any], str, str]:
    schema = str(payload.get("schema") or "").strip()
    if schema != VACANCY_DRAFT_SCHEMA_ID:
        raise ValueError("unsupported_schema")
    schema_version = str(payload.get("schema_version") or "").strip()
    if not schema_version:
        raise ValueError("missing_schema_version")
    raw_state = payload.get("state")
    if not isinstance(raw_state, Mapping):
        raise ValueError("missing_state")

    allowed_key_names = {key.value for key in VACANCY_DRAFT_SESSION_KEYS}
    restored_state = {
        str(key): value
        for key, value in raw_state.items()
        if str(key) in allowed_key_names
    }
    if not restored_state:
        raise ValueError("empty_state")
    saved_at = str(payload.get("saved_at") or "").strip()
    return restored_state, schema_version, saved_at


def _normalize_loaded_vacancy_draft_state(
    session_state: MutableMapping[str, Any],
) -> str:
    store = StateStore(session_state)
    jobspec_source = store.jobspec_source()
    source_fingerprint = ""
    if jobspec_source.source_text.strip():
        source_fingerprint = build_jobspec_source_fingerprint(
            jobspec_source.active,
            jobspec_source.source_text,
        )
    store.set_jobspec_source(
        replace(jobspec_source, active_fingerprint=source_fingerprint)
    )
    store.set_job_extract(store.job_extract())
    store.set_esco(store.esco())
    store.set_question_answers(store.answers(), store.answer_meta())
    store.set_intake_facts(store.intake_facts())
    store.set_intake_fact_evidence(store.intake_fact_evidence())
    store.set_summary_dirty_state(store.summary_dirty())

    language = str(session_state.get(SSKey.LANGUAGE.value, DEFAULT_LANGUAGE)).strip()
    if language not in {"de", "en"}:
        language = DEFAULT_LANGUAGE
    session_state[SSKey.LANGUAGE.value] = language

    ui_mode = str(session_state.get(SSKey.UI_MODE.value) or UI_MODE_DEFAULT).strip()
    session_state[SSKey.UI_MODE.value] = (
        ui_mode if ui_mode in UI_MODE_VALUES else UI_MODE_DEFAULT
    )
    session_state[SSKey.AUDIENCE_MODE.value] = _normalize_audience_mode(
        session_state.get(SSKey.AUDIENCE_MODE.value)
    )
    session_state[SSKey.UI_PREFERENCES.value] = normalize_ui_preferences(
        session_state.get(SSKey.UI_PREFERENCES.value)
    )
    _sync_source_redaction_from_preferences()

    valid_step_keys = {step.key for step in STEPS}
    restored_step = str(session_state.get(SSKey.CURRENT_STEP.value) or "").strip()
    if restored_step not in valid_step_keys:
        restored_step = STEPS[0].key
    session_state[SSKey.CURRENT_STEP.value] = restored_step
    session_state[SSKey.NAV_SELECTED.value] = restored_step
    session_state[SSKey.NAV_SYNC_PENDING.value] = False
    session_state[SSKey.LAST_RENDERED_STEP.value] = None
    session_state[SSKey.NAV_DEEP_LINK_TARGET.value] = {}
    session_state[SSKey.SUMMARY_ACTIVE_ARTIFACT.value] = (
        _normalize_summary_active_artifact(
            session_state.get(SSKey.SUMMARY_ACTIVE_ARTIFACT.value)
        )
    )

    sync_esco_semantic_state(session_state)
    _clear_stale_redesign_state()
    return restored_step


def load_vacancy_draft_json(raw_json: str | bytes) -> VacancyDraftLoadResult:
    """Reset the current vacancy and restore a schema-versioned JSON draft."""

    try:
        payload = parse_vacancy_draft_json(raw_json)
        restored_state, schema_version, saved_at = _extract_vacancy_draft_state(payload)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return VacancyDraftLoadResult(
            success=False,
            message=(
                "Entwurf konnte nicht geladen werden. Bitte eine gültige "
                "Cognitive Staffing Entwurf-JSON-Datei verwenden."
            ),
        )

    reset_vacancy()
    st.session_state.update(restored_state)
    restored_step = _normalize_loaded_vacancy_draft_state(st.session_state)
    st.session_state[SSKey.DRAFT_LAST_SAVED_FINGERPRINT.value] = (
        build_vacancy_draft_fingerprint(st.session_state)
    )
    restored_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    st.session_state[SSKey.DRAFT_RESUME_NOTICE.value] = {
        "saved_at": saved_at,
        "restored_at": restored_at,
        "restored_step": restored_step,
        "restored_key_count": len(restored_state),
        "schema_version": schema_version,
    }
    version_note = (
        ""
        if schema_version == VACANCY_DRAFT_SCHEMA_VERSION
        else f" Schema-Version importiert: {schema_version}."
    )
    return VacancyDraftLoadResult(
        success=True,
        message=f"Entwurf wurde geladen.{version_note}",
        saved_at=saved_at,
        restored_step=restored_step,
        restored_key_count=len(restored_state),
        schema_version=schema_version,
    )


def reset_vacancy() -> None:
    """Reset only vacancy-related state, not preferences."""
    st.session_state[SSKey.DRAFT_RESUME_NOTICE.value] = None
    st.session_state[SSKey.DRAFT_LAST_SAVED_FINGERPRINT.value] = ""
    st.session_state[SSKey.SOURCE_TEXT.value] = ""
    st.session_state[SSKey.SOURCE_FILE_META.value] = {}
    st.session_state[SSKey.SOURCE_ACTIVE.value] = JOBSPEC_SOURCE_MANUAL
    st.session_state[SSKey.SOURCE_ACTIVE_FINGERPRINT.value] = ""
    st.session_state[SSKey.SOURCE_MANUAL_TEXT.value] = ""
    st.session_state[SSKey.SOURCE_UPLOADED_TEXT.value] = ""
    st.session_state[SSKey.SOURCE_UPLOAD_TEXT_INPUT.value] = ""
    st.session_state[SSKey.SOURCE_UPLOAD_SIGNATURE.value] = None
    st.session_state.pop(SSKey.SOURCE_UPLOAD_FILE.value, None)
    st.session_state[SSKey.JOB_EXTRACT.value] = None
    reset_intake_fact_state(st.session_state)
    reset_intake_fact_evidence_state(st.session_state)
    st.session_state[SSKey.QUESTION_PLAN_BASE.value] = None
    st.session_state[SSKey.QUESTION_PLAN.value] = None
    st.session_state[SSKey.QUESTION_LIMITS.value] = {}
    st.session_state[SSKey.OCCUPATION_PROFILE.value] = None
    st.session_state[SSKey.OCCUPATION_QUESTION_CONTEXT.value] = None
    st.session_state[SSKey.OCCUPATION_CLASSIFICATION_TRACE.value] = []
    st.session_state[SSKey.OCCUPATION_PACK_KEYS.value] = []
    st.session_state[SSKey.QUESTION_FLOW_PROVENANCE.value] = {}
    st.session_state[SSKey.QUESTION_FLOW_FINGERPRINT.value] = ""
    st.session_state[SSKey.ANSWERS.value] = {}
    st.session_state[SSKey.ANSWER_META.value] = {}
    st.session_state[SSKey.UI_MODE.value] = UI_MODE_DEFAULT
    st.session_state[SSKey.AUDIENCE_MODE.value] = _normalize_audience_mode(
        st.session_state.get(SSKey.AUDIENCE_MODE.value)
    )
    if SSKey.UI_PREFERENCES.value not in st.session_state:
        st.session_state[SSKey.UI_PREFERENCES.value] = _default_ui_preferences()
    else:
        st.session_state[SSKey.UI_PREFERENCES.value] = normalize_ui_preferences(
            st.session_state.get(SSKey.UI_PREFERENCES.value)
        )
    _sync_source_redaction_from_preferences()
    st.session_state[SSKey.OPEN_GROUPS.value] = {}
    st.session_state[SSKey.INTRO_CYCLE_FOCUS.value] = None
    st.session_state[SSKey.BRIEF.value] = None
    reset_usage_events(st.session_state)
    st.session_state[SSKey.JOBAD_CACHE_HIT.value] = {}
    st.session_state[SSKey.SUMMARY_CACHE_HIT.value] = False
    StateStore(st.session_state).set_summary_dirty_state(SummaryDirtyState())
    st.session_state[SSKey.SUMMARY_SHOW_JOB_AD_CONFIG.value] = False
    st.session_state[SSKey.SUMMARY_LAST_MODE.value] = None
    st.session_state[SSKey.SUMMARY_LAST_MODELS.value] = {}
    st.session_state[SSKey.SUMMARY_FACTS_SEARCH.value] = ""
    st.session_state[SSKey.SUMMARY_FACTS_STATUS_FILTER.value] = "Alle"
    st.session_state[SSKey.SUMMARY_SELECTIONS.value] = {}
    st.session_state[SSKey.SUMMARY_STYLEGUIDE_BLOCKS.value] = []
    st.session_state[SSKey.SUMMARY_CHANGE_REQUEST_BLOCKS.value] = []
    st.session_state[SSKey.SUMMARY_STYLEGUIDE_TEXT.value] = ""
    st.session_state[SSKey.SUMMARY_CHANGE_REQUEST_TEXT.value] = ""
    st.session_state[SSKey.SUMMARY_ARTIFACT_OPTIONS.value] = {}
    st.session_state[SSKey.SUMMARY_ARTIFACT_CHANGE_REQUESTS.value] = {}
    st.session_state[SSKey.SUMMARY_ARTIFACT_FINGERPRINTS.value] = {}
    st.session_state[SSKey.SUMMARY_ARTIFACT_LAST_ERROR.value] = {}
    st.session_state[SSKey.SUMMARY_LOGO.value] = None
    st.session_state[SSKey.JOB_AD_DRAFT_CUSTOM.value] = None
    st.session_state[SSKey.JOB_AD_LAST_USAGE.value] = {}
    st.session_state[SSKey.INTERVIEW_PREP_HR.value] = None
    st.session_state[SSKey.INTERVIEW_PREP_HR_LAST_USAGE.value] = {}
    st.session_state[SSKey.INTERVIEW_PREP_HR_CACHE_HIT.value] = False
    st.session_state[SSKey.INTERVIEW_PREP_HR_LAST_MODE.value] = None
    st.session_state[SSKey.INTERVIEW_PREP_HR_LAST_MODELS.value] = {}
    st.session_state[SSKey.INTERVIEW_PREP_FACH.value] = None
    st.session_state[SSKey.INTERVIEW_PREP_FACH_LAST_USAGE.value] = {}
    st.session_state[SSKey.INTERVIEW_PREP_FACH_CACHE_HIT.value] = False
    st.session_state[SSKey.INTERVIEW_PREP_FACH_LAST_MODE.value] = None
    st.session_state[SSKey.INTERVIEW_PREP_FACH_LAST_MODELS.value] = {}
    st.session_state[SSKey.BOOLEAN_SEARCH_STRING.value] = None
    st.session_state[SSKey.BOOLEAN_SEARCH_LAST_USAGE.value] = {}
    st.session_state[SSKey.BOOLEAN_SEARCH_CACHE_HIT.value] = False
    st.session_state[SSKey.BOOLEAN_SEARCH_LAST_MODE.value] = None
    st.session_state[SSKey.BOOLEAN_SEARCH_LAST_MODELS.value] = {}
    st.session_state[SSKey.EMPLOYMENT_CONTRACT_DRAFT.value] = None
    st.session_state[SSKey.EMPLOYMENT_CONTRACT_LAST_USAGE.value] = {}
    st.session_state[SSKey.EMPLOYMENT_CONTRACT_CACHE_HIT.value] = False
    st.session_state[SSKey.EMPLOYMENT_CONTRACT_LAST_MODE.value] = None
    st.session_state[SSKey.EMPLOYMENT_CONTRACT_LAST_MODELS.value] = {}
    st.session_state[SSKey.ESCO_OCCUPATION_SELECTED.value] = None
    st.session_state[SSKey.ESCO_SELECTED_OCCUPATION_URI.value] = ""
    st.session_state[SSKey.ESCO_OCCUPATION_PAYLOAD.value] = None
    st.session_state[SSKey.ESCO_OCCUPATION_RELATED_COUNTS.value] = {}
    st.session_state[SSKey.ESCO_OCCUPATION_SKILL_GROUP_SHARE.value] = []
    st.session_state[SSKey.ESCO_OCCUPATION_CANDIDATES.value] = []
    st.session_state[SSKey.ESCO_MATCH_REASON.value] = None
    st.session_state[SSKey.ESCO_MATCH_CONFIDENCE.value] = None
    st.session_state[SSKey.ESCO_MATCH_PROVENANCE.value] = []
    st.session_state[SSKey.ESCO_SKILLS_SELECTED_MUST.value] = []
    st.session_state[SSKey.ESCO_SKILLS_SELECTED_NICE.value] = []
    st.session_state[SSKey.ESCO_SKILLS_REMOVED.value] = []
    st.session_state[SSKey.ESCO_CONFIRMED_ESSENTIAL_SKILLS.value] = []
    st.session_state[SSKey.ESCO_CONFIRMED_OPTIONAL_SKILLS.value] = []
    st.session_state[SSKey.ESCO_UNMAPPED_REQUIREMENT_TERMS.value] = []
    st.session_state[SSKey.ESCO_UNMAPPED_ROLE_TERMS.value] = []
    st.session_state[SSKey.ESCO_UNMAPPED_TERM_ACTIONS.value] = {}
    st.session_state[SSKey.ESCO_UNRESOLVED_TERM_DECISIONS.value] = []
    st.session_state[SSKey.ESCO_SKILLS_MAPPING_REPORT.value] = None
    st.session_state[SSKey.ESCO_SKILL_DETAIL_CACHE.value] = {}
    st.session_state[SSKey.ESCO_OCCUPATION_TITLE_VARIANTS.value] = {}
    st.session_state[SSKey.ESCO_NEGATIVE_CACHE.value] = {}
    st.session_state[SSKey.ESCO_MIGRATION_LOG.value] = []
    st.session_state[SSKey.ESCO_MIGRATION_PENDING.value] = None
    st.session_state[SSKey.ESCO_LAST_DATA_SOURCE.value] = ""
    st.session_state[SSKey.ESCO_LOOKUP_METADATA.value] = {}
    st.session_state[SSKey.ESCO_ANCHOR_STATE.value] = ESCO_ANCHOR_STATE_DEGRADED
    st.session_state[SSKey.ESCO_PRIMARY_ANCHOR.value] = None
    st.session_state[SSKey.ESCO_SECONDARY_ANCHORS.value] = []
    st.session_state[SSKey.ESCO_SEMANTIC_EXPORT_MODE.value] = (
        ESCO_SEMANTIC_EXPORT_MODE_DEGRADED
    )
    st.session_state[SSKey.ESCO_CAPABILITY_SNAPSHOT.value] = {}
    st.session_state[SSKey.ESCO_MATRIX_METADATA.value] = {
        "source": "",
        "version": "",
        "records": 0,
    }
    st.session_state[SSKey.ESCO_MATRIX_LOADED.value] = False
    st.session_state[SSKey.ESCO_MATRIX_COVERAGE_ROWS.value] = []
    st.session_state[SSKey.ESCO_MATRIX_COVERAGE_CONTEXT.value] = {
        "reason": "no_matrix_loaded",
        "occupation_group": "",
        "rows": 0,
    }
    st.session_state[SSKey.COMPANY_WEBSITE_RESEARCH.value] = {}
    st.session_state[SSKey.COMPANY_WEBSITE_SELECTED_MATCHES.value] = []
    st.session_state[SSKey.COMPANY_WEBSITE_FACT_REVIEW.value] = {}
    st.session_state[SSKey.COMPANY_WEBSITE_LAST_ERROR.value] = None
    st.session_state[SSKey.COMPANY_WEBSITE_MANUAL_URL.value] = ""
    st.session_state[SSKey.ROLE_TASKS_JOBSPEC_SUGGESTED.value] = []
    st.session_state[SSKey.ROLE_TASKS_ESCO_SUGGESTED.value] = []
    st.session_state[SSKey.ROLE_TASKS_LLM_SUGGESTED.value] = []
    st.session_state[SSKey.ROLE_TASKS_SELECTED.value] = []
    st.session_state[SSKey.ROLE_TASKS_SUGGEST_COUNT.value] = 5
    st.session_state[SSKey.ROLE_TASKS_JOBSPEC_PILLS.value] = []
    st.session_state[SSKey.ROLE_TASKS_ESCO_PILLS.value] = []
    st.session_state[SSKey.ROLE_TASKS_AI_PILLS.value] = []
    st.session_state[SSKey.ROLE_TASKS_SELECTED_BULK_BUFFER.value] = []
    st.session_state[SSKey.INTERVIEW_INTERNAL_FLOW.value] = dict(
        INTERVIEW_INTERNAL_FLOW_DEFAULT
    )
    st.session_state[SSKey.SKILLS_JOBSPEC_SUGGESTED.value] = []
    st.session_state[SSKey.SKILLS_LLM_SUGGESTED.value] = []
    st.session_state[SSKey.SKILLS_AI_INITIAL_GENERATED.value] = False
    st.session_state[SSKey.SKILLS_SELECTED.value] = []
    st.session_state[SSKey.SKILLS_SELECTED_STATUS.value] = {}
    st.session_state[SSKey.SKILLS_SUGGEST_COUNT.value] = 5
    st.session_state[SSKey.SKILLS_JOBSPEC_PILLS.value] = []
    st.session_state[SSKey.SKILLS_ESCO_PILLS.value] = []
    st.session_state[SSKey.SKILLS_AI_PILLS.value] = []
    st.session_state[SSKey.SKILLS_SELECTED_BULK_BUFFER.value] = []
    st.session_state[SSKey.SKILLS_ESCO_LOAD_CLICKED.value] = False
    st.session_state[SSKey.SKILLS_ESCO_SEARCH.value] = ""
    st.session_state[SSKey.SKILLS_ESCO_SORT.value] = "alphabetisch"
    st.session_state[SSKey.SKILLS_AI_GENERATE_CLICKED.value] = False
    st.session_state[SSKey.BENEFITS_JOBSPEC_SUGGESTED.value] = []
    st.session_state[SSKey.BENEFITS_LLM_SUGGESTED.value] = []
    st.session_state[SSKey.BENEFITS_SELECTED.value] = []
    st.session_state[SSKey.BENEFITS_SELECTED_BULK_BUFFER.value] = []
    st.session_state[SSKey.BENEFITS_JOBSPEC_PILLS.value] = []
    st.session_state[SSKey.BENEFITS_CONTEXT_PILLS.value] = []
    st.session_state[SSKey.BENEFITS_AI_PILLS.value] = []
    st.session_state[SSKey.BENEFITS_SUGGEST_COUNT.value] = 5
    st.session_state[SSKey.BENEFITS_AI_GENERATE_CLICKED.value] = False
    st.session_state[SSKey.BENEFITS_AI_INITIAL_GENERATED.value] = False
    st.session_state[SSKey.BENEFITS_REGION_CONTEXT.value] = ""
    st.session_state[SSKey.SALARY_SCENARIO_SKILLS_ADD.value] = []
    st.session_state[SSKey.SALARY_SCENARIO_SKILLS_REMOVE.value] = []
    st.session_state[SSKey.SALARY_SCENARIO_LOCATION_OVERRIDE.value] = ""
    st.session_state[SSKey.SALARY_SCENARIO_LOCATION_CITY_OVERRIDE.value] = ""
    st.session_state[SSKey.SALARY_SCENARIO_LOCATION_COUNTRY_OVERRIDE.value] = ""
    st.session_state[SSKey.SALARY_SCENARIO_RADIUS_KM.value] = 50
    st.session_state[SSKey.SALARY_SCENARIO_REMOTE_SHARE_PERCENT.value] = 0
    st.session_state[SSKey.SALARY_SCENARIO_SENIORITY_OVERRIDE.value] = ""
    st.session_state[SSKey.SALARY_SCENARIO_LAB_ROWS.value] = []
    st.session_state[SSKey.SALARY_SCENARIO_SELECTED_ROW_ID.value] = ""
    st.session_state[SSKey.SALARY_SCENARIO_PENDING_SKILLS_ADD.value] = None
    st.session_state[SSKey.SALARY_SCENARIO_PENDING_SKILLS_REMOVE.value] = None
    st.session_state[SSKey.SALARY_SCENARIO_PENDING_LOCATION_CITY_OVERRIDE.value] = None
    st.session_state[SSKey.SALARY_SCENARIO_PENDING_RADIUS_KM.value] = None
    st.session_state[SSKey.SALARY_SCENARIO_PENDING_REMOTE_SHARE_PERCENT.value] = None
    st.session_state[SSKey.SALARY_SCENARIO_PENDING_SENIORITY_OVERRIDE.value] = None
    st.session_state[SSKey.SALARY_SCENARIO_APPLY_PENDING_UPDATE.value] = False
    st.session_state[SSKey.SALARY_SCENARIO_PENDING_SELECTED_ROW_ID.value] = None
    st.session_state[SSKey.SALARY_FORECAST_SELECTED_SCENARIO.value] = "base"
    sync_esco_semantic_state(st.session_state)
    _clear_stale_redesign_state()
    st.session_state[SSKey.SALARY_FORECAST_LAST_RESULT.value] = {}
    st.session_state[SSKey.SALARY_FORECAST_INPUT_FINGERPRINT.value] = {}
    st.session_state[SSKey.SALARY_FORECAST_INPUT_SELECTIONS.value] = {}
    st.session_state[SSKey.SALARY_FORECAST_FACTOR_SELECTIONS.value] = {}
    st.session_state[SSKey.SALARY_SCENARIO_CONTEXT_DEFAULTS.value] = {}
    st.session_state[SSKey.LAST_ERROR.value] = None
    st.session_state[SSKey.LAST_ERROR_DEBUG.value] = None
    st.session_state[SSKey.OPENAI_LAST_STRUCTURED_OUTPUT_PATH.value] = None
    st.session_state[SSKey.CURRENT_STEP.value] = STEPS[0].key
    st.session_state[SSKey.LAST_RENDERED_STEP.value] = STEPS[0].key
    st.session_state[SSKey.NAV_SELECTED.value] = STEPS[0].key
    st.session_state[SSKey.NAV_SYNC_PENDING.value] = False
    st.session_state[SSKey.NAV_DEEP_LINK_TARGET.value] = {}


def get_answers() -> Dict[str, Any]:
    return StateStore(st.session_state).answers()


def set_answer(question_id: str, value: Any, *, fact_key: str | None = None) -> None:
    answers = get_answers()
    answers[question_id] = value
    st.session_state[SSKey.ANSWERS.value] = answers
    write_intake_fact_by_legacy_field(st.session_state, question_id, value)
    resolved_fact_key = fact_key or _question_fact_key_from_plan(question_id)
    if resolved_fact_key:
        write_intake_fact(st.session_state, resolved_fact_key, value)


def _question_fact_key_from_plan(question_id: str) -> str | None:
    raw_plan = st.session_state.get(SSKey.QUESTION_PLAN.value)
    raw_steps = _raw_question_plan_steps(raw_plan)
    for raw_step in raw_steps:
        raw_questions = _raw_step_questions(raw_step)
        for raw_question in raw_questions:
            if not isinstance(raw_question, dict):
                continue
            if raw_question.get("id") != question_id:
                continue
            fact_key = raw_question.get("fact_key")
            if isinstance(fact_key, str) and fact_key.strip():
                return fact_key.strip()
    return None


def _raw_question_plan_steps(raw_plan: Any) -> list[Any]:
    if isinstance(raw_plan, dict):
        raw_steps = raw_plan.get("steps")
        return raw_steps if isinstance(raw_steps, list) else []
    raw_steps = getattr(raw_plan, "steps", None)
    return list(raw_steps) if isinstance(raw_steps, list) else []


def _raw_step_questions(raw_step: Any) -> list[Any]:
    if isinstance(raw_step, dict):
        raw_questions = raw_step.get("questions")
        return raw_questions if isinstance(raw_questions, list) else []
    raw_questions = getattr(raw_step, "questions", None)
    if isinstance(raw_questions, list):
        return [
            question.model_dump(mode="json")
            if hasattr(question, "model_dump")
            else question
            for question in raw_questions
        ]
    return []


def get_answer_meta() -> AnswerMetaMap:
    return cast(AnswerMetaMap, StateStore(st.session_state).answer_meta())


def mark_answer_touched(
    question_id: str, previous_value: Any, current_value: Any
) -> None:
    """Persist touch-state when the value differs from the previous value."""

    meta = dict(get_answer_meta())
    current = cast(AnswerMeta, dict(meta.get(question_id, {})))
    previous_hash = value_hash(previous_value)
    current_hash = value_hash(current_value)
    if previous_hash != current_hash:
        current["touched"] = True
    current["last_value_hash"] = current_hash
    current.setdefault("confirmed", False)
    meta[question_id] = current
    st.session_state[SSKey.ANSWER_META.value] = meta


def set_error(msg: str) -> None:
    st.session_state[SSKey.LAST_ERROR.value] = msg


def set_safe_error_debug(
    *,
    step: str,
    error_type: str,
    error_code: str | None = None,
) -> None:
    """Store non-sensitive debug details for optional UI display."""

    st.session_state[SSKey.LAST_ERROR_DEBUG.value] = None
    if not bool(st.session_state.get(SSKey.OPENAI_DEBUG_ERRORS.value, False)):
        return

    details: list[str] = [
        f"step={step}",
        f"type={error_type}",
        f"category={error_type}",
    ]
    if error_code:
        details.insert(1, f"code={error_code}")
    st.session_state[SSKey.LAST_ERROR_DEBUG.value] = " | ".join(details)


def handle_unexpected_exception(
    *,
    step: str,
    exc: Exception,
    error_type: str | None = None,
    error_code: str | None = None,
    user_message: str = "Es ist ein unerwarteter Fehler aufgetreten. Bitte erneut versuchen.",
) -> None:
    """Set a generic UI error plus safe non-sensitive debug metadata."""

    resolved_error_type = error_type or type(exc).__name__
    set_error(user_message)
    set_safe_error_debug(
        step=step,
        error_type=resolved_error_type,
        error_code=error_code,
    )


def clear_error() -> None:
    st.session_state[SSKey.LAST_ERROR.value] = None
    st.session_state[SSKey.LAST_ERROR_DEBUG.value] = None


def get_esco_occupation_selected() -> Dict[str, Any] | None:
    """Return a validated ESCO occupation payload; normalize legacy shape first."""

    def _normalize_selected_payload(raw_payload: Any) -> Dict[str, Any] | None:
        if not isinstance(raw_payload, dict):
            return None
        normalized_uri = str(raw_payload.get("uri") or "").strip()
        if not normalized_uri:
            return None

        normalized_title = str(
            raw_payload.get("title")
            or raw_payload.get("preferredLabel")
            or raw_payload.get("label")
            or raw_payload.get("name")
            or ""
        ).strip()
        if not normalized_title:
            return None

        normalized_type = str(raw_payload.get("type") or "").strip().lower()
        if not normalized_type:
            normalized_type = "occupation"

        normalized: Dict[str, Any] = {
            "uri": normalized_uri,
            "title": normalized_title,
            "type": normalized_type,
        }
        code_value = raw_payload.get("code")
        if code_value is not None:
            normalized["code"] = str(code_value).strip() or None
        return normalized

    raw = st.session_state.get(SSKey.ESCO_OCCUPATION_SELECTED.value)
    if raw is None:
        return None
    normalized_payload = _normalize_selected_payload(raw)
    if normalized_payload is None:
        return None
    try:
        validated = EscoConceptRef.model_validate(normalized_payload).model_dump()
        st.session_state[SSKey.ESCO_OCCUPATION_SELECTED.value] = validated
        st.session_state[SSKey.ESCO_SELECTED_OCCUPATION_URI.value] = str(
            validated.get("uri") or ""
        ).strip()
        if not st.session_state.get(SSKey.ESCO_PRIMARY_ANCHOR.value):
            st.session_state[SSKey.ESCO_PRIMARY_ANCHOR.value] = {
                **validated,
                "reason": None,
                "selected_as": "primary",
            }
        sync_esco_semantic_state(st.session_state)
        return validated
    except Exception:
        return None


def get_esco_semantic_context() -> EscoSemanticContext:
    """Return and synchronize the canonical ESCO semantic context."""

    return sync_esco_semantic_state(st.session_state)


def has_confirmed_esco_anchor() -> bool:
    """Return True when an ESCO occupation anchor URI is confirmed in session state."""

    context = get_esco_semantic_context()
    selected_uri = str(
        getattr(context.primary_anchor, "uri", "") if context.primary_anchor else ""
    ).strip()
    return bool(selected_uri)


def get_esco_anchor_status() -> EscoAnchorStatus:
    """Resolve ESCO anchor state atomically for consistent UI decisions."""

    context = get_esco_semantic_context()
    selected_occupation = get_esco_occupation_selected()
    selected_uri = str(
        st.session_state.get(SSKey.ESCO_SELECTED_OCCUPATION_URI.value)
        or (getattr(context.primary_anchor, "uri", "") if context.primary_anchor else "")
        or (selected_occupation or {}).get("uri")
        or ""
    ).strip()
    st.session_state[SSKey.ESCO_SELECTED_OCCUPATION_URI.value] = selected_uri
    anchor_confirmed = bool(selected_uri)

    if not anchor_confirmed:
        status_reason = "anchor_not_confirmed"
    elif selected_occupation is None:
        status_reason = "anchor_confirmed_invalid_payload"
    else:
        status_reason = "anchor_confirmed_with_payload"
    return EscoAnchorStatus(
        anchor_confirmed=anchor_confirmed,
        selected_occupation=selected_occupation,
        status_reason=status_reason,
    )


def get_esco_occupation_payload() -> Dict[str, Any] | None:
    """Return selected ESCO occupation detail payload if available."""

    raw = st.session_state.get(SSKey.ESCO_OCCUPATION_PAYLOAD.value)
    return raw if isinstance(raw, dict) else None


def get_esco_occupation_candidates() -> list[Dict[str, Any]]:
    """Return validated ESCO candidate suggestions; tolerate legacy payloads."""

    raw = st.session_state.get(SSKey.ESCO_OCCUPATION_CANDIDATES.value, [])
    if not isinstance(raw, list):
        return []
    items: list[Dict[str, Any]] = []
    for item in raw:
        try:
            items.append(EscoSuggestionItem.model_validate(item).model_dump())
        except ValidationError:
            continue
    return items


def get_esco_skills_mapping_report() -> Dict[str, Any] | None:
    """Return validated ESCO mapping report or None for missing/legacy sessions."""

    raw = st.session_state.get(SSKey.ESCO_SKILLS_MAPPING_REPORT.value)
    if raw is None:
        return None
    try:
        return EscoMappingReport.model_validate(raw).model_dump()
    except Exception:
        return None


def _normalize_requirement_term(value: Any) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _dedupe_requirement_terms(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = str(value or "").strip()
        normalized = _normalize_requirement_term(cleaned)
        if not normalized or normalized in seen:
            continue
        deduped.append(cleaned)
        seen.add(normalized)
    return deduped


def _validated_esco_skill_bucket(raw: Any) -> list[Dict[str, str]]:
    if not isinstance(raw, list):
        return []
    validated: list[Dict[str, str]] = []
    seen_uris: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        uri = str(item.get("uri") or "").strip()
        title = str(item.get("title") or "").strip()
        if not uri and not title:
            continue
        dedupe_key = uri or _normalize_requirement_term(title)
        if not dedupe_key or dedupe_key in seen_uris:
            continue
        validated.append(
            {
                "uri": uri,
                "title": title,
                "type": str(item.get("type") or "skill").strip() or "skill",
            }
        )
        seen_uris.add(dedupe_key)
    return validated


def sync_esco_shared_state() -> EscoCoverageSnapshot:
    selected = get_esco_occupation_selected() or {}
    selected_occupation_uri = str(
        st.session_state.get(SSKey.ESCO_SELECTED_OCCUPATION_URI.value)
        or selected.get("uri")
        or ""
    ).strip()
    st.session_state[SSKey.ESCO_SELECTED_OCCUPATION_URI.value] = selected_occupation_uri

    essential_skills = _validated_esco_skill_bucket(
        st.session_state.get(SSKey.ESCO_SKILLS_SELECTED_MUST.value, [])
    )
    optional_skills = _validated_esco_skill_bucket(
        st.session_state.get(SSKey.ESCO_SKILLS_SELECTED_NICE.value, [])
    )
    st.session_state[SSKey.ESCO_CONFIRMED_ESSENTIAL_SKILLS.value] = essential_skills
    st.session_state[SSKey.ESCO_CONFIRMED_OPTIONAL_SKILLS.value] = optional_skills

    unmapped_raw = st.session_state.get(SSKey.ESCO_UNMAPPED_REQUIREMENT_TERMS.value, [])
    unmapped_terms = (
        _dedupe_requirement_terms([str(item) for item in unmapped_raw])
        if isinstance(unmapped_raw, list)
        else []
    )
    st.session_state[SSKey.ESCO_UNMAPPED_REQUIREMENT_TERMS.value] = unmapped_terms

    job_extract = st.session_state.get(SSKey.JOB_EXTRACT.value, {})
    essential_terms = []
    optional_terms = []
    if isinstance(job_extract, dict):
        essential_terms = _dedupe_requirement_terms(
            [str(item) for item in (job_extract.get("must_have_skills") or [])]
        )
        optional_terms = _dedupe_requirement_terms(
            [str(item) for item in (job_extract.get("nice_to_have_skills") or [])]
        )

    essential_titles = {
        _normalize_requirement_term(item.get("title") or "")
        for item in essential_skills
    }
    optional_titles = {
        _normalize_requirement_term(item.get("title") or "") for item in optional_skills
    }

    essential_covered = sum(
        1
        for term in essential_terms
        if _normalize_requirement_term(term) in essential_titles
    )
    optional_covered = sum(
        1
        for term in optional_terms
        if _normalize_requirement_term(term) in optional_titles
    )

    return EscoCoverageSnapshot(
        selected_occupation_uri=selected_occupation_uri,
        confirmed_essential_skills=essential_skills,
        confirmed_optional_skills=optional_skills,
        unmapped_requirement_terms=unmapped_terms,
        essential_total=len(essential_terms),
        essential_covered=essential_covered,
        optional_total=len(optional_terms),
        optional_covered=optional_covered,
    )
