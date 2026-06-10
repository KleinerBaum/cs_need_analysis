from __future__ import annotations

import re
from collections import Counter

from constants import (
    INTAKE_FACTS,
    FactKey,
    FactPersistenceIntent,
    FactResolutionStatus,
    FactSensitivity,
    FactSourceType,
    FactValueType,
    STEP_KEY_BENEFITS,
    STEP_KEY_COMPANY,
    STEP_KEY_INTERVIEW,
    STEP_KEY_ROLE_TASKS,
    STEP_KEY_SKILLS,
    UsageEventType,
)


EXPECTED_FACT_KEYS = [
    "company.language_guess",
    "company.company_name",
    "company.brand_name",
    "company.company_website",
    "company.location_city",
    "company.location_country",
    "company.place_of_work",
    "company.remote_policy",
    "company.department_name",
    "company.reports_to",
    "company.direct_reports_count",
    "role.job_title",
    "role.employment_type",
    "role.contract_type",
    "role.seniority_level",
    "role.job_ref_number",
    "role.role_overview",
    "role.responsibilities",
    "role.deliverables",
    "role.success_metrics",
    "role.tech_stack",
    "role.domain_expertise",
    "role.travel_required",
    "role.on_call",
    "role.onboarding_notes",
    "role.gaps",
    "role.assumptions",
    "skills.must_have_skills",
    "skills.nice_to_have_skills",
    "skills.soft_skills",
    "skills.education",
    "skills.certifications",
    "skills.languages",
    "benefits.salary_range",
    "benefits.benefits",
    "interview.start_date",
    "interview.application_deadline",
    "interview.recruitment_steps",
    "interview.contacts",
]


def _facts_by_key():
    return {fact.fact_key: fact for fact in INTAKE_FACTS}


def test_fact_key_values_are_unique_and_dot_style() -> None:
    values = [fact_key.value for fact_key in FactKey]

    assert len(values) == len(set(values))
    assert all(
        re.fullmatch(r"[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*", value)
        for value in values
    )


def test_intake_fact_definitions_have_unique_fact_keys() -> None:
    fact_keys = [fact.fact_key for fact in INTAKE_FACTS]

    assert len(fact_keys) == len(set(fact_keys))


def test_every_fact_key_has_exactly_one_definition() -> None:
    definitions_by_key = Counter(fact.fact_key for fact in INTAKE_FACTS)

    assert set(definitions_by_key) == set(FactKey)
    assert all(count == 1 for count in definitions_by_key.values())


def test_fact_definitions_have_valid_metadata() -> None:
    valid_step_keys = {
        STEP_KEY_COMPANY,
        STEP_KEY_ROLE_TASKS,
        STEP_KEY_SKILLS,
        STEP_KEY_BENEFITS,
        STEP_KEY_INTERVIEW,
    }

    assert all(fact.label.strip() for fact in INTAKE_FACTS)
    assert all(fact.step_key in valid_step_keys for fact in INTAKE_FACTS)
    assert all(isinstance(fact.value_type, FactValueType) for fact in INTAKE_FACTS)
    assert all(
        isinstance(fact.persistence_intent, FactPersistenceIntent)
        for fact in INTAKE_FACTS
    )


def test_fact_value_type_contract_values() -> None:
    assert [value_type.value for value_type in FactValueType] == [
        "string",
        "string_list",
        "boolean",
        "integer",
        "date_string",
        "money_range",
        "object_list",
    ]


def test_fact_persistence_intent_contract_values() -> None:
    assert [intent.value for intent in FactPersistenceIntent] == ["legacy_compatible"]


def test_fact_source_type_contract_values() -> None:
    assert [source.value for source in FactSourceType] == [
        "manual",
        "jobspec",
        "homepage",
        "esco",
        "llm",
    ]


def test_fact_sensitivity_contract_values() -> None:
    assert [sensitivity.value for sensitivity in FactSensitivity] == [
        "normal",
        "personal",
        "restricted",
    ]


def test_fact_resolution_status_contract_values() -> None:
    assert [status.value for status in FactResolutionStatus] == [
        "confirmed",
        "inferred",
        "assumed",
        "conflicted",
        "missing",
    ]


def test_usage_event_type_contract_values() -> None:
    assert [event_type.value for event_type in UsageEventType] == [
        "step_entered",
        "step_submitted",
        "fact_confirmed",
        "fact_corrected",
        "fact_rejected",
        "fallback_model_used",
        "homepage_fetch_failed",
        "enrichment_timed",
        "artifact_generated",
    ]


def test_fact_definitions_use_semantic_value_types() -> None:
    facts_by_key = _facts_by_key()

    expected_types = {
        FactKey.COMPANY_LANGUAGE_GUESS: FactValueType.STRING,
        FactKey.COMPANY_COMPANY_NAME: FactValueType.STRING,
        FactKey.COMPANY_BRAND_NAME: FactValueType.STRING,
        FactKey.COMPANY_COMPANY_WEBSITE: FactValueType.STRING,
        FactKey.COMPANY_LOCATION_CITY: FactValueType.STRING,
        FactKey.COMPANY_LOCATION_COUNTRY: FactValueType.STRING,
        FactKey.COMPANY_PLACE_OF_WORK: FactValueType.STRING,
        FactKey.COMPANY_REMOTE_POLICY: FactValueType.STRING,
        FactKey.COMPANY_DEPARTMENT_NAME: FactValueType.STRING,
        FactKey.COMPANY_REPORTS_TO: FactValueType.STRING,
        FactKey.COMPANY_DIRECT_REPORTS_COUNT: FactValueType.INTEGER,
        FactKey.ROLE_JOB_TITLE: FactValueType.STRING,
        FactKey.ROLE_EMPLOYMENT_TYPE: FactValueType.STRING,
        FactKey.ROLE_CONTRACT_TYPE: FactValueType.STRING,
        FactKey.ROLE_SENIORITY_LEVEL: FactValueType.STRING,
        FactKey.ROLE_JOB_REF_NUMBER: FactValueType.STRING,
        FactKey.ROLE_ROLE_OVERVIEW: FactValueType.STRING,
        FactKey.ROLE_RESPONSIBILITIES: FactValueType.STRING_LIST,
        FactKey.ROLE_DELIVERABLES: FactValueType.STRING_LIST,
        FactKey.ROLE_SUCCESS_METRICS: FactValueType.STRING_LIST,
        FactKey.ROLE_TECH_STACK: FactValueType.STRING_LIST,
        FactKey.ROLE_DOMAIN_EXPERTISE: FactValueType.STRING_LIST,
        FactKey.ROLE_TRAVEL_REQUIRED: FactValueType.BOOLEAN,
        FactKey.ROLE_ON_CALL: FactValueType.BOOLEAN,
        FactKey.ROLE_ONBOARDING_NOTES: FactValueType.STRING,
        FactKey.ROLE_GAPS: FactValueType.STRING_LIST,
        FactKey.ROLE_ASSUMPTIONS: FactValueType.STRING_LIST,
        FactKey.SKILLS_MUST_HAVE_SKILLS: FactValueType.STRING_LIST,
        FactKey.SKILLS_NICE_TO_HAVE_SKILLS: FactValueType.STRING_LIST,
        FactKey.SKILLS_SOFT_SKILLS: FactValueType.STRING_LIST,
        FactKey.SKILLS_EDUCATION: FactValueType.STRING_LIST,
        FactKey.SKILLS_CERTIFICATIONS: FactValueType.STRING_LIST,
        FactKey.SKILLS_LANGUAGES: FactValueType.STRING_LIST,
        FactKey.BENEFITS_SALARY_RANGE: FactValueType.MONEY_RANGE,
        FactKey.BENEFITS_BENEFITS: FactValueType.STRING_LIST,
        FactKey.INTERVIEW_START_DATE: FactValueType.DATE_STRING,
        FactKey.INTERVIEW_APPLICATION_DEADLINE: FactValueType.DATE_STRING,
        FactKey.INTERVIEW_RECRUITMENT_STEPS: FactValueType.OBJECT_LIST,
        FactKey.INTERVIEW_CONTACTS: FactValueType.OBJECT_LIST,
    }

    assert {
        fact_key: fact.value_type for fact_key, fact in facts_by_key.items()
    } == expected_types


def test_fact_key_stability_snapshot() -> None:
    assert [fact_key.value for fact_key in FactKey] == EXPECTED_FACT_KEYS
    assert [fact.fact_key.value for fact in INTAKE_FACTS] == EXPECTED_FACT_KEYS
