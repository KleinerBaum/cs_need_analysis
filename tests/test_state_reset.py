from __future__ import annotations

import json
from types import SimpleNamespace

from constants import FactKey, FactSourceType, SSKey, STEP_KEY_INTRO
from schemas import JobAdExtract
import state
from state_store import (
    EscoState,
    JobspecSourceState,
    StateStore,
    SummaryDirtyState,
)


RESET_EXPECTATIONS: dict[SSKey, object] = {
    SSKey.SOURCE_TEXT: "",
    SSKey.SOURCE_FILE_META: {},
    SSKey.SOURCE_REDACT_PII: True,
    SSKey.SOURCE_ACTIVE: "manual",
    SSKey.SOURCE_ACTIVE_FINGERPRINT: "",
    SSKey.SOURCE_MANUAL_TEXT: "",
    SSKey.SOURCE_UPLOADED_TEXT: "",
    SSKey.SOURCE_UPLOAD_TEXT_INPUT: "",
    SSKey.SOURCE_UPLOAD_SIGNATURE: None,
    SSKey.JOB_EXTRACT: None,
    SSKey.INTAKE_FACTS: {},
    SSKey.INTAKE_FACT_EVIDENCE: {},
    SSKey.QUESTION_PLAN_BASE: None,
    SSKey.QUESTION_PLAN: None,
    SSKey.QUESTION_LIMITS: {},
    SSKey.OCCUPATION_PROFILE: None,
    SSKey.OCCUPATION_QUESTION_CONTEXT: None,
    SSKey.OCCUPATION_CLASSIFICATION_TRACE: [],
    SSKey.OCCUPATION_PACK_KEYS: [],
    SSKey.QUESTION_FLOW_PROVENANCE: {},
    SSKey.QUESTION_FLOW_FINGERPRINT: "",
    SSKey.ANSWERS: {},
    SSKey.ANSWER_META: {},
    SSKey.UI_MODE: "standard",
    SSKey.UI_PREFERENCES: {
        "answer_mode": "balanced",
        "information_depth": "standard",
        "esco_matching_strictness": "ausgewogen",
        "regional_focus": "DACH",
        "show_sources_default": True,
        "confidence_threshold": 0.6,
        "pii_reduction": True,
        "details_expanded_default": False,
        "step_compact": {},
        "ui_language": "de",
        "wizard_design": "classic",
    },
    SSKey.OPEN_GROUPS: {},
    SSKey.BRIEF: None,
    SSKey.OPENAI_LAST_STRUCTURED_OUTPUT_PATH: None,
    SSKey.USAGE_EVENTS: [],
    SSKey.JOBAD_CACHE_HIT: {},
    SSKey.SUMMARY_CACHE_HIT: False,
    SSKey.SUMMARY_DIRTY: False,
    SSKey.SUMMARY_INPUT_FINGERPRINT: "",
    SSKey.SUMMARY_LAST_BRIEF_FINGERPRINT: "",
    SSKey.SUMMARY_ACTIVE_ARTIFACT: "brief",
    SSKey.SUMMARY_SHOW_JOB_AD_CONFIG: False,
    SSKey.SUMMARY_LAST_MODE: None,
    SSKey.SUMMARY_LAST_MODELS: {},
    SSKey.SUMMARY_SELECTIONS: {},
    SSKey.SUMMARY_STYLEGUIDE_BLOCKS: [],
    SSKey.SUMMARY_CHANGE_REQUEST_BLOCKS: [],
    SSKey.SUMMARY_STYLEGUIDE_TEXT: "",
    SSKey.SUMMARY_CHANGE_REQUEST_TEXT: "",
    SSKey.SUMMARY_ARTIFACT_OPTIONS: {},
    SSKey.SUMMARY_ARTIFACT_CHANGE_REQUESTS: {},
    SSKey.SUMMARY_ARTIFACT_FINGERPRINTS: {},
    SSKey.SUMMARY_LOGO: None,
    SSKey.JOB_AD_DRAFT_CUSTOM: None,
    SSKey.JOB_AD_LAST_USAGE: {},
    SSKey.INTERVIEW_PREP_HR: None,
    SSKey.INTERVIEW_PREP_HR_LAST_USAGE: {},
    SSKey.INTERVIEW_PREP_HR_CACHE_HIT: False,
    SSKey.INTERVIEW_PREP_HR_LAST_MODE: None,
    SSKey.INTERVIEW_PREP_HR_LAST_MODELS: {},
    SSKey.INTERVIEW_PREP_FACH: None,
    SSKey.INTERVIEW_PREP_FACH_LAST_USAGE: {},
    SSKey.INTERVIEW_PREP_FACH_CACHE_HIT: False,
    SSKey.INTERVIEW_PREP_FACH_LAST_MODE: None,
    SSKey.INTERVIEW_PREP_FACH_LAST_MODELS: {},
    SSKey.BOOLEAN_SEARCH_STRING: None,
    SSKey.BOOLEAN_SEARCH_LAST_USAGE: {},
    SSKey.BOOLEAN_SEARCH_CACHE_HIT: False,
    SSKey.BOOLEAN_SEARCH_LAST_MODE: None,
    SSKey.BOOLEAN_SEARCH_LAST_MODELS: {},
    SSKey.EMPLOYMENT_CONTRACT_DRAFT: None,
    SSKey.EMPLOYMENT_CONTRACT_LAST_USAGE: {},
    SSKey.EMPLOYMENT_CONTRACT_CACHE_HIT: False,
    SSKey.EMPLOYMENT_CONTRACT_LAST_MODE: None,
    SSKey.EMPLOYMENT_CONTRACT_LAST_MODELS: {},
    SSKey.ESCO_MATCH_REASON: None,
    SSKey.ESCO_MATCH_CONFIDENCE: None,
    SSKey.ESCO_MATCH_PROVENANCE: [],
    SSKey.ESCO_RELEASE_LANE: "stable",
    SSKey.ESCO_LOOKUP_METADATA: {},
    SSKey.ESCO_ANCHOR_STATE: "degraded_unconfirmed",
    SSKey.ESCO_PRIMARY_ANCHOR: None,
    SSKey.ESCO_SECONDARY_ANCHORS: [],
    SSKey.ESCO_SEMANTIC_EXPORT_MODE: "degraded",
    SSKey.ESCO_CAPABILITY_SNAPSHOT: {
        "release_lane": "stable",
        "selected_version": "v1.2.0",
        "api_mode": "hosted",
        "data_source_mode": "live_api",
        "language": "de",
        "fallback_language": "en",
        "view_obsolete": False,
        "supports_occupation_skills": False,
        "supports_occupation_knowledge": False,
        "supports_skill_group_share": False,
    },
    SSKey.ESCO_OCCUPATION_SELECTED: None,
    SSKey.ESCO_SELECTED_OCCUPATION_URI: "",
    SSKey.ESCO_OCCUPATION_PAYLOAD: None,
    SSKey.ESCO_OCCUPATION_RELATED_COUNTS: {},
    SSKey.ESCO_OCCUPATION_SKILL_GROUP_SHARE: [],
    SSKey.ESCO_OCCUPATION_CANDIDATES: [],
    SSKey.ESCO_SKILLS_SELECTED_MUST: [],
    SSKey.ESCO_SKILLS_SELECTED_NICE: [],
    SSKey.ESCO_SKILLS_REMOVED: [],
    SSKey.ESCO_CONFIRMED_ESSENTIAL_SKILLS: [],
    SSKey.ESCO_CONFIRMED_OPTIONAL_SKILLS: [],
    SSKey.ESCO_UNMAPPED_REQUIREMENT_TERMS: [],
    SSKey.ESCO_UNMAPPED_ROLE_TERMS: [],
    SSKey.ESCO_UNMAPPED_TERM_ACTIONS: {},
    SSKey.ESCO_UNRESOLVED_TERM_DECISIONS: [],
    SSKey.ESCO_SKILLS_MAPPING_REPORT: None,
    SSKey.ESCO_SKILL_DETAIL_CACHE: {},
    SSKey.ESCO_OCCUPATION_TITLE_VARIANTS: {},
    SSKey.ESCO_MIGRATION_LOG: [],
    SSKey.ESCO_MIGRATION_PENDING: None,
    SSKey.ESCO_MATRIX_METADATA: {"source": "", "version": "", "records": 0},
    SSKey.ESCO_MATRIX_LOADED: False,
    SSKey.ESCO_MATRIX_COVERAGE_ROWS: [],
    SSKey.ESCO_MATRIX_COVERAGE_CONTEXT: {
        "reason": "no_matrix_loaded",
        "occupation_group": "",
        "rows": 0,
    },
    SSKey.COMPANY_WEBSITE_RESEARCH: {},
    SSKey.COMPANY_WEBSITE_SELECTED_MATCHES: [],
    SSKey.COMPANY_WEBSITE_FACT_REVIEW: {},
    SSKey.COMPANY_WEBSITE_LAST_ERROR: None,
    SSKey.COMPANY_WEBSITE_MANUAL_URL: "",
    SSKey.ROLE_TASKS_JOBSPEC_SUGGESTED: [],
    SSKey.ROLE_TASKS_ESCO_SUGGESTED: [],
    SSKey.ROLE_TASKS_LLM_SUGGESTED: [],
    SSKey.ROLE_TASKS_SELECTED: [],
    SSKey.ROLE_TASKS_SUGGEST_COUNT: 5,
    SSKey.ROLE_TASKS_JOBSPEC_PILLS: [],
    SSKey.ROLE_TASKS_ESCO_PILLS: [],
    SSKey.ROLE_TASKS_AI_PILLS: [],
    SSKey.ROLE_TASKS_SELECTED_BULK_BUFFER: [],
    SSKey.INTERVIEW_INTERNAL_FLOW: {
        "contacts": [],
        "info_loop_items": [],
        "earliest_start_date": None,
        "latest_start_date": None,
        "selected_value_ids": [],
    },
    SSKey.SKILLS_JOBSPEC_SUGGESTED: [],
    SSKey.SKILLS_LLM_SUGGESTED: [],
    SSKey.SKILLS_AI_INITIAL_GENERATED: False,
    SSKey.SKILLS_SELECTED: [],
    SSKey.SKILLS_SELECTED_STATUS: {},
    SSKey.SKILLS_SUGGEST_COUNT: 5,
    SSKey.SKILLS_JOBSPEC_PILLS: [],
    SSKey.SKILLS_ESCO_PILLS: [],
    SSKey.SKILLS_AI_PILLS: [],
    SSKey.SKILLS_SELECTED_BULK_BUFFER: [],
    SSKey.SKILLS_ESCO_LOAD_CLICKED: False,
    SSKey.SKILLS_ESCO_SEARCH: "",
    SSKey.SKILLS_ESCO_SORT: "alphabetisch",
    SSKey.SKILLS_AI_GENERATE_CLICKED: False,
    SSKey.BENEFITS_JOBSPEC_SUGGESTED: [],
    SSKey.BENEFITS_LLM_SUGGESTED: [],
    SSKey.BENEFITS_SELECTED: [],
    SSKey.BENEFITS_SELECTED_BULK_BUFFER: [],
    SSKey.BENEFITS_JOBSPEC_PILLS: [],
    SSKey.BENEFITS_CONTEXT_PILLS: [],
    SSKey.BENEFITS_AI_PILLS: [],
    SSKey.BENEFITS_SUGGEST_COUNT: 5,
    SSKey.BENEFITS_AI_GENERATE_CLICKED: False,
    SSKey.SALARY_FORECAST_INPUT_FINGERPRINT: {},
    SSKey.SALARY_FORECAST_INPUT_SELECTIONS: {},
    SSKey.LAST_ERROR: None,
}


def test_state_store_read_defaults_do_not_create_missing_keys() -> None:
    session_state: dict[str, object] = {}
    store = StateStore(session_state)

    assert store.jobspec_source().active == "manual"
    assert store.job_extraction().extract is None
    assert store.esco().anchor_state == "degraded_unconfirmed"
    assert store.question_answers().answers == {}
    assert store.question_answers().answer_meta == {}
    assert store.summary_dirty().is_dirty is False
    assert session_state == {}


def test_state_store_normalizes_invalid_summary_dirty_state_without_writes() -> None:
    session_state: dict[str, object] = {
        SSKey.SUMMARY_DIRTY.value: "false",
        SSKey.SUMMARY_INPUT_FINGERPRINT.value: " current ",
        SSKey.SUMMARY_LAST_BRIEF_FINGERPRINT.value: None,
        SSKey.SUMMARY_ACTIVE_ARTIFACT.value: "",
    }
    keys_before = set(session_state)
    store = StateStore(session_state)

    summary_state = store.summary_dirty()

    assert summary_state.is_dirty is False
    assert summary_state.input_fingerprint == "current"
    assert summary_state.last_brief_fingerprint == ""
    assert summary_state.active_artifact == "brief"
    assert set(session_state) == keys_before


def test_state_store_setters_write_only_canonical_session_keys() -> None:
    session_state: dict[str, object] = {}
    store = StateStore(session_state)

    store.set_jobspec_source(
        JobspecSourceState(
            active="upload",
            active_fingerprint="source-fp",
            source_text="synthetic jobspec",
            file_meta={"size": 123},
            uploaded_text="synthetic jobspec",
        )
    )
    store.set_job_extract(JobAdExtract(job_title="Data Engineer"))
    store.set_esco(
        EscoState(
            anchor_state="anchored",
            primary_anchor={"uri": "esco:occupation:1", "title": "Data Engineer"},
            semantic_export_mode="anchored",
            occupation_selected={
                "uri": "esco:occupation:1",
                "title": "Data Engineer",
            },
            selected_occupation_uri="esco:occupation:1",
        )
    )
    store.set_question_answers({"role_title": "Data Engineer"}, {"role_title": {}})
    store.set_summary_dirty_state(
        SummaryDirtyState(
            is_dirty=True,
            input_fingerprint="current",
            last_brief_fingerprint="previous",
            active_artifact="job_ad",
        )
    )

    assert set(session_state).issubset({key.value for key in SSKey})
    assert session_state[SSKey.SOURCE_ACTIVE.value] == "upload"
    assert session_state[SSKey.JOB_EXTRACT.value]["job_title"] == "Data Engineer"
    assert session_state[SSKey.ESCO_SELECTED_OCCUPATION_URI.value] == "esco:occupation:1"
    assert session_state[SSKey.ANSWERS.value] == {"role_title": "Data Engineer"}
    assert session_state[SSKey.SUMMARY_DIRTY.value] is True


def test_state_store_summary_freshness_writes_only_canonical_session_keys() -> None:
    session_state: dict[str, object] = {}
    store = StateStore(session_state)

    store.set_summary_freshness(
        input_fingerprint=" current ",
        last_brief_fingerprint=" previous ",
        is_dirty=True,
    )
    store.mark_summary_brief_current(" current ")

    assert set(session_state).issubset({key.value for key in SSKey})
    assert session_state[SSKey.SUMMARY_INPUT_FINGERPRINT.value] == "current"
    assert session_state[SSKey.SUMMARY_LAST_BRIEF_FINGERPRINT.value] == "current"
    assert session_state[SSKey.SUMMARY_DIRTY.value] is False


def test_vacancy_draft_json_round_trips_allowlisted_state_only(monkeypatch) -> None:
    source_state: dict[str, object] = {
        SSKey.CURRENT_STEP.value: "summary",
        SSKey.NAV_SELECTED.value: "summary",
        SSKey.SOURCE_TEXT.value: "Synthetic jobspec",
        SSKey.SOURCE_ACTIVE.value: "manual",
        SSKey.SOURCE_ACTIVE_FINGERPRINT.value: "source-fingerprint",
        SSKey.JOB_EXTRACT.value: JobAdExtract(job_title="Data Engineer"),
        SSKey.ANSWERS.value: {"company_name": "Example GmbH"},
        SSKey.ANSWER_META.value: {"company_name": {"touched": True}},
        SSKey.INTAKE_FACTS.value: {FactKey.COMPANY_COMPANY_NAME.value: "Example GmbH"},
        SSKey.ROLE_TASKS_SELECTED.value: ["Build data pipelines"],
        SSKey.SKILLS_SELECTED.value: ["Python"],
        SSKey.BENEFITS_SELECTED.value: ["Remote work"],
        SSKey.BRIEF.value: {"one_liner": "Hire a data engineer"},
        SSKey.JOB_AD_DRAFT_CUSTOM.value: "Publishable draft",
        SSKey.MODEL.value: "runtime-model",
        SSKey.USAGE_EVENTS.value: [{"event_type": "artifact_generated"}],
        SSKey.LLM_RESPONSE_CACHE.value: {"cache": "ignored"},
        SSKey.OPENAI_LAST_STRUCTURED_OUTPUT_PATH.value: {"path": "ignored"},
        SSKey.LAST_ERROR.value: "ignored error",
        SSKey.SUMMARY_LOGO.value: {"bytes": b"not exported"},
        SSKey.CONTENT_SHARING_CONSENT.value: True,
    }

    raw_json = state.build_vacancy_draft_json(source_state)
    exported_state = json.loads(raw_json)["state"]

    assert exported_state[SSKey.SOURCE_TEXT.value] == "Synthetic jobspec"
    assert exported_state[SSKey.JOB_EXTRACT.value]["job_title"] == "Data Engineer"
    assert SSKey.SOURCE_ACTIVE_FINGERPRINT.value not in exported_state
    assert SSKey.SOURCE_FILE_META.value not in exported_state
    assert SSKey.SOURCE_UPLOAD_SIGNATURE.value not in exported_state
    assert SSKey.MODEL.value not in exported_state
    assert SSKey.USAGE_EVENTS.value not in exported_state
    assert SSKey.LLM_RESPONSE_CACHE.value not in exported_state
    assert SSKey.OPENAI_LAST_STRUCTURED_OUTPUT_PATH.value not in exported_state
    assert SSKey.LAST_ERROR.value not in exported_state
    assert SSKey.SUMMARY_LOGO.value not in exported_state
    assert SSKey.CONTENT_SHARING_CONSENT.value not in exported_state

    target_state: dict[str, object] = {
        SSKey.MODEL.value: "runtime-model",
        SSKey.SOURCE_TEXT.value: "stale jobspec",
        SSKey.ANSWERS.value: {"stale": "value"},
        SSKey.USAGE_EVENTS.value: [{"event_type": "old"}],
        SSKey.LAST_ERROR.value: "old error",
        SSKey.CONTENT_SHARING_CONSENT.value: False,
    }
    monkeypatch.setattr(
        state,
        "st",
        SimpleNamespace(session_state=target_state),
    )

    result = state.load_vacancy_draft_json(raw_json)

    assert result.success is True
    assert target_state[SSKey.MODEL.value] == "runtime-model"
    assert target_state[SSKey.SOURCE_TEXT.value] == "Synthetic jobspec"
    assert target_state[SSKey.JOB_EXTRACT.value]["job_title"] == "Data Engineer"
    assert target_state[SSKey.ANSWERS.value] == {"company_name": "Example GmbH"}
    assert target_state[SSKey.ROLE_TASKS_SELECTED.value] == ["Build data pipelines"]
    assert target_state[SSKey.SKILLS_SELECTED.value] == ["Python"]
    assert target_state[SSKey.BENEFITS_SELECTED.value] == ["Remote work"]
    assert target_state[SSKey.CURRENT_STEP.value] == "summary"
    assert target_state[SSKey.NAV_SELECTED.value] == "summary"
    assert target_state[SSKey.USAGE_EVENTS.value] == []
    assert target_state[SSKey.LAST_ERROR.value] is None
    assert target_state[SSKey.CONTENT_SHARING_CONSENT.value] is False
    assert isinstance(target_state[SSKey.DRAFT_RESUME_NOTICE.value], dict)
    assert (
        target_state[SSKey.DRAFT_RESUME_NOTICE.value]["restored_step"]
        == "summary"
    )


def test_reset_vacancy_clears_progressive_disclosure_state(
    monkeypatch,
) -> None:
    fake_session_state = {
        SSKey.SOURCE_TEXT.value: "Jobspec",
        SSKey.SOURCE_FILE_META.value: {"name": "input.pdf"},
        SSKey.SOURCE_REDACT_PII.value: False,
        SSKey.JOB_EXTRACT.value: {"job_title": "Engineer"},
        SSKey.INTAKE_FACTS.value: {"role.job_title": "Engineer"},
        SSKey.INTAKE_FACT_EVIDENCE.value: {
            "role.job_title": {"confidence": 0.75}
        },
        SSKey.QUESTION_PLAN_BASE.value: {"steps": []},
        SSKey.QUESTION_PLAN.value: {"steps": []},
        SSKey.QUESTION_LIMITS.value: {"company": 3},
        SSKey.OCCUPATION_PROFILE.value: {"occupation_family": "digital_product"},
        SSKey.OCCUPATION_CLASSIFICATION_TRACE.value: [{"signal": "developer"}],
        SSKey.OCCUPATION_PACK_KEYS.value: ["family.digital_product"],
        SSKey.QUESTION_FLOW_PROVENANCE.value: {"compiled_question_count": 3},
        SSKey.QUESTION_FLOW_FINGERPRINT.value: "abc",
        SSKey.ANSWERS.value: {"q1": "value"},
        SSKey.ANSWER_META.value: {"q1": {"touched": True}},
        SSKey.UI_MODE.value: "expert",
        SSKey.OPEN_GROUPS.value: {"company": {"Details": True}},
        SSKey.BRIEF.value: {"one_liner": "x"},
        SSKey.OPENAI_LAST_STRUCTURED_OUTPUT_PATH.value: {
            "endpoint": "responses.parse",
            "requested_model": "gpt-5",
            "final_model": "gpt-5",
            "used_reduced_request": False,
        },
        SSKey.USAGE_EVENTS.value: [{"event_type": "artifact_generated"}],
        SSKey.JOBAD_CACHE_HIT.value: {"hit": True},
        SSKey.SUMMARY_CACHE_HIT.value: True,
        SSKey.SUMMARY_LAST_MODE.value: "custom",
        SSKey.SUMMARY_LAST_MODELS.value: {"summary": "gpt"},
        SSKey.SUMMARY_SELECTIONS.value: {"a": 1},
        SSKey.JOB_AD_DRAFT_CUSTOM.value: "draft",
        SSKey.JOB_AD_LAST_USAGE.value: {"tokens": 12},
        SSKey.COMPANY_WEBSITE_SELECTED_MATCHES.value: [
            {"option_id": "company_q::about::1"}
        ],
        SSKey.COMPANY_WEBSITE_FACT_REVIEW.value: {
            "company.company_name:imprint:abc": {
                "fact_key": "company.company_name",
                "value": "Example GmbH",
                "selected": True,
            }
        },
        SSKey.ESCO_SELECTED_OCCUPATION_URI.value: "http://data.europa.eu/esco/occupation/123",
        SSKey.INTERVIEW_INTERNAL_FLOW.value: {
            "contacts": [{"role": "Money", "name": "M. Example"}],
            "info_loop_items": ["Interviewtag abstimmen"],
            "earliest_start_date": "2026-06-01",
            "latest_start_date": "2026-07-01",
            "selected_value_ids": ["abc"],
        },
        SSKey.LAST_ERROR.value: "error",
        SSKey.CURRENT_STEP.value: "summary",
    }
    monkeypatch.setattr(
        state,
        "st",
        SimpleNamespace(session_state=fake_session_state),
    )

    state.reset_vacancy()

    for key, expected in RESET_EXPECTATIONS.items():
        assert fake_session_state[key.value] == expected
    assert fake_session_state[SSKey.CURRENT_STEP.value] == STEP_KEY_INTRO
    store = StateStore(fake_session_state)
    assert store.jobspec_source().active == "manual"
    assert store.job_extraction().extract is None
    assert store.esco().selected_occupation_uri == ""
    assert store.question_answers().answers == {}
    assert store.summary_dirty().is_dirty is False


def test_apply_jobspec_source_change_clears_only_source_dependent_state(
    monkeypatch,
) -> None:
    old_fingerprint = state.build_jobspec_source_fingerprint(
        "upload",
        "Alter Upload",
        file_meta={"name": "old.pdf", "size": 123},
        upload_signature=("old.pdf", 123),
    )
    manual_fact_key = FactKey.COMPANY_COMPANY_NAME.value
    jobspec_fact_key = FactKey.ROLE_JOB_TITLE.value
    mixed_fact_key = FactKey.BENEFITS_BENEFITS.value
    fake_session_state = {
        SSKey.SOURCE_ACTIVE.value: "upload",
        SSKey.SOURCE_ACTIVE_FINGERPRINT.value: old_fingerprint,
        SSKey.SOURCE_TEXT.value: "Alter Upload",
        SSKey.SOURCE_FILE_META.value: {"name": "old.pdf", "size": 123},
        SSKey.JOB_EXTRACT.value: {"job_title": "Old Engineer"},
        SSKey.QUESTION_PLAN_BASE.value: {"steps": ["old"]},
        SSKey.QUESTION_PLAN.value: {"steps": ["old"]},
        SSKey.QUESTION_LIMITS.value: {"company": 3},
        SSKey.OCCUPATION_PROFILE.value: {"occupation_family": "digital"},
        SSKey.OCCUPATION_QUESTION_CONTEXT.value: {"modules": ["old"]},
        SSKey.OCCUPATION_CLASSIFICATION_TRACE.value: [{"signal": "old"}],
        SSKey.OCCUPATION_PACK_KEYS.value: ["old"],
        SSKey.QUESTION_FLOW_PROVENANCE.value: {"compiled_question_count": 2},
        SSKey.QUESTION_FLOW_FINGERPRINT.value: "old-flow",
        SSKey.ANSWERS.value: {
            "job_title": "Old Engineer",
            "manual_q": "Manual value",
            FactKey.INTAKE_URGENCY.value: "high",
        },
        SSKey.ANSWER_META.value: {
            "job_title": {"touched": False, "last_value_hash": "old"},
            "manual_q": {"touched": True, "last_value_hash": "manual"},
        },
        SSKey.INTAKE_FACTS.value: {
            jobspec_fact_key: "Old Engineer",
            manual_fact_key: "Manual GmbH",
            mixed_fact_key: ["Mobiles Arbeiten"],
        },
        SSKey.INTAKE_FACT_EVIDENCE.value: {
            jobspec_fact_key: {"source_type": FactSourceType.JOBSPEC.value},
            manual_fact_key: {"source_type": FactSourceType.MANUAL.value},
            mixed_fact_key: {
                "source_type": FactSourceType.MANUAL.value,
                "secondary_evidence": [
                    {"source_type": FactSourceType.JOBSPEC.value},
                    {"source_type": FactSourceType.HOMEPAGE.value},
                ],
            },
        },
        SSKey.ESCO_OCCUPATION_SELECTED.value: {"uri": "uri:old", "title": "Old"},
        SSKey.ESCO_SELECTED_OCCUPATION_URI.value: "uri:old",
        SSKey.ESCO_OCCUPATION_PAYLOAD.value: {"uri": "uri:old"},
        SSKey.ESCO_OCCUPATION_RELATED_COUNTS.value: {"skills": 5},
        SSKey.ESCO_OCCUPATION_SKILL_GROUP_SHARE.value: [{"group": "old"}],
        SSKey.ESCO_OCCUPATION_CANDIDATES.value: [{"uri": "uri:candidate"}],
        SSKey.ESCO_MATCH_REASON.value: "old match",
        SSKey.ESCO_MATCH_CONFIDENCE.value: "high",
        SSKey.ESCO_MATCH_PROVENANCE.value: ["old provenance"],
        SSKey.ESCO_SKILLS_SELECTED_MUST.value: [{"uri": "skill:old"}],
        SSKey.ESCO_SKILLS_SELECTED_NICE.value: [{"uri": "skill:nice"}],
        SSKey.ESCO_SKILLS_REMOVED.value: ["skill:removed"],
        SSKey.ESCO_CONFIRMED_ESSENTIAL_SKILLS.value: [{"uri": "skill:old"}],
        SSKey.ESCO_CONFIRMED_OPTIONAL_SKILLS.value: [{"uri": "skill:nice"}],
        SSKey.ESCO_UNMAPPED_REQUIREMENT_TERMS.value: ["legacy"],
        SSKey.ESCO_UNMAPPED_ROLE_TERMS.value: ["legacy role"],
        SSKey.ESCO_UNMAPPED_TERM_ACTIONS.value: {"legacy": "ignore"},
        SSKey.ESCO_UNRESOLVED_TERM_DECISIONS.value: [{"term": "legacy"}],
        SSKey.ESCO_SKILLS_MAPPING_REPORT.value: {"mapped": True},
        SSKey.ESCO_MATRIX_COVERAGE_ROWS.value: [{"row": 1}],
        SSKey.ROLE_TASKS_JOBSPEC_SUGGESTED.value: [{"label": "old"}],
        SSKey.ROLE_TASKS_ESCO_SUGGESTED.value: [{"label": "old esco"}],
        SSKey.ROLE_TASKS_SELECTED.value: ["Keep selected task"],
        SSKey.ROLE_TASKS_JOBSPEC_PILLS.value: ["old"],
        SSKey.ROLE_TASKS_ESCO_PILLS.value: ["old esco"],
        SSKey.SKILLS_JOBSPEC_SUGGESTED.value: [{"label": "old"}],
        SSKey.SKILLS_LLM_SUGGESTED.value: [{"label": "old ai"}],
        SSKey.SKILLS_SELECTED.value: ["Keep selected skill"],
        SSKey.SKILLS_JOBSPEC_PILLS.value: ["old"],
        SSKey.SKILLS_ESCO_PILLS.value: ["old esco"],
        SSKey.BENEFITS_JOBSPEC_SUGGESTED.value: [{"label": "old"}],
        SSKey.BENEFITS_LLM_SUGGESTED.value: [{"label": "old ai"}],
        SSKey.BENEFITS_SELECTED.value: ["Keep selected benefit"],
        SSKey.BENEFITS_JOBSPEC_PILLS.value: ["old"],
        SSKey.SALARY_FORECAST_LAST_RESULT.value: {"base": 1},
        SSKey.SALARY_FORECAST_INPUT_FINGERPRINT.value: {"role_tasks": "old"},
        SSKey.SALARY_FORECAST_INPUT_SELECTIONS.value: {"role_tasks": {}},
        SSKey.JOBAD_CACHE_HIT.value: {"extract_job_ad": True},
        SSKey.LLM_RESPONSE_CACHE.value: {"keep": {"result": "cached"}},
        SSKey.LAST_ERROR.value: "old error",
        SSKey.LAST_ERROR_DEBUG.value: "old debug",
    }
    monkeypatch.setattr(state, "st", SimpleNamespace(session_state=fake_session_state))

    next_fingerprint = state.apply_jobspec_source_change("manual", "Neuer Freitext")

    assert fake_session_state[SSKey.SOURCE_ACTIVE.value] == "manual"
    assert fake_session_state[SSKey.SOURCE_TEXT.value] == "Neuer Freitext"
    assert fake_session_state[SSKey.SOURCE_ACTIVE_FINGERPRINT.value] == next_fingerprint
    assert fake_session_state[SSKey.SOURCE_FILE_META.value] == {}
    assert fake_session_state[SSKey.JOB_EXTRACT.value] is None
    assert fake_session_state[SSKey.QUESTION_PLAN_BASE.value] is None
    assert fake_session_state[SSKey.QUESTION_PLAN.value] is None
    assert fake_session_state[SSKey.QUESTION_LIMITS.value] == {}
    assert fake_session_state[SSKey.QUESTION_FLOW_FINGERPRINT.value] == ""
    assert fake_session_state[SSKey.INTAKE_FACTS.value] == {
        manual_fact_key: "Manual GmbH",
        mixed_fact_key: ["Mobiles Arbeiten"],
    }
    assert jobspec_fact_key not in fake_session_state[SSKey.INTAKE_FACT_EVIDENCE.value]
    assert fake_session_state[SSKey.INTAKE_FACT_EVIDENCE.value][manual_fact_key][
        "source_type"
    ] == FactSourceType.MANUAL.value
    assert fake_session_state[SSKey.INTAKE_FACT_EVIDENCE.value][mixed_fact_key][
        "secondary_evidence"
    ] == [{"source_type": FactSourceType.HOMEPAGE.value}]
    assert fake_session_state[SSKey.ANSWERS.value] == {
        "manual_q": "Manual value",
        FactKey.INTAKE_URGENCY.value: "high",
    }
    assert fake_session_state[SSKey.ANSWER_META.value] == {
        "manual_q": {"touched": True, "last_value_hash": "manual"}
    }
    assert fake_session_state[SSKey.ESCO_SELECTED_OCCUPATION_URI.value] == ""
    assert fake_session_state[SSKey.ESCO_OCCUPATION_SELECTED.value] is None
    assert fake_session_state[SSKey.ROLE_TASKS_JOBSPEC_SUGGESTED.value] == []
    assert fake_session_state[SSKey.ROLE_TASKS_ESCO_SUGGESTED.value] == []
    assert fake_session_state[SSKey.ROLE_TASKS_SELECTED.value] == [
        "Keep selected task"
    ]
    assert fake_session_state[SSKey.SKILLS_SELECTED.value] == ["Keep selected skill"]
    assert fake_session_state[SSKey.BENEFITS_SELECTED.value] == [
        "Keep selected benefit"
    ]
    assert fake_session_state[SSKey.SALARY_FORECAST_LAST_RESULT.value] == {}
    assert fake_session_state[SSKey.SALARY_FORECAST_INPUT_FINGERPRINT.value] == {}
    assert fake_session_state[SSKey.JOBAD_CACHE_HIT.value] == {}
    assert fake_session_state[SSKey.LLM_RESPONSE_CACHE.value] == {
        "keep": {"result": "cached"}
    }
    assert fake_session_state[SSKey.LAST_ERROR.value] is None
    assert fake_session_state[SSKey.LAST_ERROR_DEBUG.value] is None


def test_apply_jobspec_source_change_preserves_state_for_same_fingerprint(
    monkeypatch,
) -> None:
    fingerprint = state.build_jobspec_source_fingerprint("manual", "Gleicher Text")
    fake_session_state = {
        SSKey.SOURCE_ACTIVE.value: "manual",
        SSKey.SOURCE_ACTIVE_FINGERPRINT.value: fingerprint,
        SSKey.JOB_EXTRACT.value: {"job_title": "Engineer"},
        SSKey.QUESTION_PLAN.value: {"steps": []},
        SSKey.JOBAD_CACHE_HIT.value: {"extract_job_ad": True},
    }
    monkeypatch.setattr(state, "st", SimpleNamespace(session_state=fake_session_state))

    state.apply_jobspec_source_change("text", "Gleicher Text")

    assert fake_session_state[SSKey.JOB_EXTRACT.value] == {"job_title": "Engineer"}
    assert fake_session_state[SSKey.QUESTION_PLAN.value] == {"steps": []}
    assert fake_session_state[SSKey.JOBAD_CACHE_HIT.value] == {"extract_job_ad": True}


def test_init_session_state_and_reset_vacancy_share_same_defaults(monkeypatch) -> None:
    fake_session_state: dict[str, object] = {}
    monkeypatch.setattr(
        state,
        "load_openai_settings",
        lambda: SimpleNamespace(openai_model="gpt-5-mini"),
    )
    monkeypatch.setattr(
        state,
        "st",
        SimpleNamespace(session_state=fake_session_state),
    )

    state.init_session_state()

    initialized_defaults = {
        key.value: fake_session_state[key.value] for key in RESET_EXPECTATIONS
    }
    fake_session_state[SSKey.SOURCE_TEXT.value] = "filled"
    fake_session_state[SSKey.INTERVIEW_PREP_HR.value] = {"blocks": []}

    state.reset_vacancy()

    for key, expected in RESET_EXPECTATIONS.items():
        assert fake_session_state[key.value] == expected
        assert initialized_defaults[key.value] == expected


def test_reset_vacancy_preserves_existing_ui_preferences(monkeypatch) -> None:
    preserved_preferences = {
        "details_expanded_default": True,
        "pii_reduction": False,
        "step_compact": {"company": False},
        "ui_language": "en",
        "wizard_design": "focus",
    }
    fake_session_state = {
        SSKey.UI_PREFERENCES.value: preserved_preferences,
        SSKey.UI_MODE.value: "expert",
    }
    monkeypatch.setattr(
        state,
        "st",
        SimpleNamespace(session_state=fake_session_state),
    )

    state.reset_vacancy()

    assert fake_session_state[SSKey.UI_MODE.value] == "standard"
    resolved_preferences = fake_session_state[SSKey.UI_PREFERENCES.value]
    assert resolved_preferences["details_expanded_default"] is True
    assert resolved_preferences["step_compact"] == {"company": False}
    assert resolved_preferences["confidence_threshold"] == 0.6
    assert resolved_preferences["pii_reduction"] is False
    assert resolved_preferences["ui_language"] == "en"
    assert resolved_preferences["wizard_design"] == "focus"
    assert fake_session_state[SSKey.SOURCE_REDACT_PII.value] is False


def test_init_session_state_uses_env_esco_api_base_url(monkeypatch) -> None:
    fake_session_state: dict[str, object] = {}
    monkeypatch.setenv("ESCO_API_BASE_URL", "https://env.example/esco/")
    monkeypatch.setattr(
        state,
        "load_openai_settings",
        lambda: SimpleNamespace(openai_model="gpt-5-mini"),
    )
    monkeypatch.setattr(
        state,
        "st",
        SimpleNamespace(session_state=fake_session_state),
    )

    state.init_session_state()

    assert fake_session_state[SSKey.ESCO_CONFIG.value]["base_url"] == (
        "https://env.example/esco/"
    )


def test_init_session_state_uses_env_esco_selected_version(monkeypatch) -> None:
    fake_session_state: dict[str, object] = {}
    monkeypatch.setenv("ESCO_SELECTED_VERSION", "v1.3.1")
    monkeypatch.setattr(
        state,
        "load_openai_settings",
        lambda: SimpleNamespace(openai_model="gpt-5-mini"),
    )
    monkeypatch.setattr(
        state,
        "st",
        SimpleNamespace(session_state=fake_session_state),
    )
    state.init_session_state()
    assert fake_session_state[SSKey.ESCO_CONFIG.value]["selected_version"] == "v1.3.1"


def test_init_session_state_uses_streamlit_esco_secrets(monkeypatch) -> None:
    fake_session_state: dict[str, object] = {}
    monkeypatch.setenv("ESCO_SELECTED_VERSION", "v1.3.1")
    monkeypatch.setattr(
        state,
        "load_openai_settings",
        lambda: SimpleNamespace(openai_model="gpt-5-mini"),
    )
    monkeypatch.setattr(
        state,
        "st",
        SimpleNamespace(
            session_state=fake_session_state,
            secrets={
                "esco": {
                    "api_base_url": "https://secret.example/esco/",
                    "release_lane": "preview",
                    "selected_version": "v1.2.1",
                    "language": "en",
                    "fallback_language": "de",
                    "api_mode": "local",
                    "data_source_mode": "hybrid",
                    "index_storage_path": "data/custom_esco_index",
                    "index_version": "v1.2.1",
                }
            },
        ),
    )

    state.init_session_state()

    esco_config = fake_session_state[SSKey.ESCO_CONFIG.value]
    assert esco_config["base_url"] == "https://secret.example/esco/"
    assert esco_config["release_lane"] == "preview"
    assert esco_config["selected_version"] == "v1.2.1"
    assert esco_config["language"] == "en"
    assert esco_config["fallback_language"] == "de"
    assert esco_config["api_mode"] == "local"
    assert esco_config["data_source_mode"] == "hybrid"
    assert esco_config["index_storage_path"] == "data/custom_esco_index"
    assert esco_config["index_version"] == "v1.2.1"



def test_init_session_state_maps_legacy_summary_alias_key(monkeypatch) -> None:
    fake_session_state: dict[str, object] = {"cs.summary.active_action": "job_ad"}
    monkeypatch.setattr(
        state,
        "load_openai_settings",
        lambda: SimpleNamespace(openai_model="gpt-5-mini"),
    )
    monkeypatch.setattr(
        state,
        "st",
        SimpleNamespace(session_state=fake_session_state),
    )

    state.init_session_state()

    assert fake_session_state[SSKey.SUMMARY_ACTIVE_ARTIFACT.value] == "job_ad"


def test_reset_vacancy_clears_stale_redesign_and_legacy_alias_keys(monkeypatch) -> None:
    fake_session_state = {
        SSKey.SUMMARY_ACTIVE_ARTIFACT.value: "brief",
        "cs.summary.active_action": "job_ad_generator",
        "cs.redesign.summary.mode": "advanced",
        "cs.summary.redesign.matrix": {"rows": []},
    }
    monkeypatch.setattr(
        state,
        "st",
        SimpleNamespace(session_state=fake_session_state),
    )

    state.reset_vacancy()

    assert "cs.summary.active_action" not in fake_session_state
    assert "cs.redesign.summary.mode" not in fake_session_state
    assert "cs.summary.redesign.matrix" not in fake_session_state
