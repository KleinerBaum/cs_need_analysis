from __future__ import annotations

import re
from collections import Counter

from constants import (
    INTAKE_FACTS,
    FactKey,
    FactPersistenceIntent,
    FactRequirementStage,
    FactResolutionStatus,
    FactSalaryImpact,
    FactSensitivity,
    FactSourceType,
    FactValueType,
    STEP_KEY_BENEFITS,
    STEP_KEY_COMPANY,
    STEP_KEY_INTERVIEW,
    STEP_KEY_LANDING,
    STEP_KEY_ROLE_TASKS,
    STEP_KEY_SKILLS,
    UsageEventType,
)


EXPECTED_FACT_KEYS = [
    "intake.hiring_reason",
    "intake.urgency",
    "intake.hiring_volume",
    "intake.search_confidentiality",
    "intake.role_definition_maturity",
    "company.language_guess",
    "company.company_name",
    "company.brand_name",
    "company.company_website",
    "company.location_city",
    "company.location_country",
    "company.place_of_work",
    "company.remote_policy",
    "company.work_arrangement",
    "company.office_days_per_week",
    "company.allowed_regions_timezones",
    "company.employer_pitch",
    "company.role_relevant_positioning",
    "company.business_unit",
    "company.hiring_reason",
    "company.growth_context",
    "company.role_business_impact",
    "company.language_internal",
    "company.language_external",
    "company.non_negotiables",
    "company.compliance_context",
    "company.tariff_context",
    "company.department_name",
    "company.reports_to",
    "company.direct_reports_count",
    "team.name",
    "team.leadership_scope",
    "team.size_direct",
    "team.stakeholders_primary",
    "team.success_context_90d",
    "role.job_title",
    "role.employment_type",
    "role.contract_type",
    "role.seniority_level",
    "role.job_ref_number",
    "role.role_overview",
    "role.responsibilities",
    "role.responsibilities_prioritized",
    "role.deliverables",
    "role.success_metrics",
    "role.success_metrics_timeline",
    "role.business_outcome_primary",
    "role.day1_responsibilities",
    "role.expansion_scope",
    "role.decision_scope",
    "role.year1_success_signals",
    "role.tech_stack",
    "role.domain_expertise",
    "role.travel_required",
    "role.travel_profile",
    "role.on_call",
    "role.onboarding_notes",
    "role.gaps",
    "role.assumptions",
    "skills.items",
    "skills.must_have_skills",
    "skills.nice_to_have_skills",
    "skills.soft_skills",
    "skills.education",
    "skills.certifications",
    "skills.languages",
    "skills.readiness_timing",
    "skills.free_text_reason",
    "skills.knockout_criteria",
    "skills.trainable_skills",
    "benefits.salary_range",
    "benefits.variable_pay",
    "benefits.benefits",
    "benefits.shift_compensation",
    "benefits.collective_agreement_context",
    "benefits.offer_components",
    "legal.work_authorization_support",
    "timeline.start_flexibility",
    "interview.start_date",
    "interview.application_deadline",
    "interview.recruitment_steps",
    "interview.contacts",
    "interview.assessment_evidence",
    "interview.stage_owners",
    "interview.communication_sla",
    "interview.scorecard_template",
    "interview.core_questions",
    "interview.compliance_notes",
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
        STEP_KEY_LANDING,
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
    assert all(isinstance(fact.salary_impact, FactSalaryImpact) for fact in INTAKE_FACTS)
    assert all(
        isinstance(fact.requirement_stage, FactRequirementStage)
        for fact in INTAKE_FACTS
    )
    assert all(isinstance(fact.website_enrichable, bool) for fact in INTAKE_FACTS)


def test_fact_value_type_contract_values() -> None:
    assert [value_type.value for value_type in FactValueType] == [
        "string",
        "string_list",
        "boolean",
        "integer",
        "date_string",
        "money_range",
        "object",
        "object_list",
    ]


def test_fact_persistence_intent_contract_values() -> None:
    assert [intent.value for intent in FactPersistenceIntent] == ["legacy_compatible"]


def test_fact_salary_impact_contract_values() -> None:
    assert [impact.value for impact in FactSalaryImpact] == [
        "none",
        "quality_indirect",
        "p50_direct",
    ]


def test_fact_requirement_stage_contract_values() -> None:
    assert [stage.value for stage in FactRequirementStage] == [
        "before_summary",
        "before_artifact",
        "optional",
    ]


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
        "evaluation_run_completed",
    ]


def test_fact_definitions_use_semantic_value_types() -> None:
    facts_by_key = _facts_by_key()

    expected_types = {
        FactKey.INTAKE_HIRING_REASON: FactValueType.STRING,
        FactKey.INTAKE_URGENCY: FactValueType.STRING,
        FactKey.INTAKE_HIRING_VOLUME: FactValueType.INTEGER,
        FactKey.INTAKE_SEARCH_CONFIDENTIALITY: FactValueType.STRING,
        FactKey.INTAKE_ROLE_DEFINITION_MATURITY: FactValueType.STRING,
        FactKey.COMPANY_LANGUAGE_GUESS: FactValueType.STRING,
        FactKey.COMPANY_COMPANY_NAME: FactValueType.STRING,
        FactKey.COMPANY_BRAND_NAME: FactValueType.STRING,
        FactKey.COMPANY_COMPANY_WEBSITE: FactValueType.STRING,
        FactKey.COMPANY_LOCATION_CITY: FactValueType.STRING,
        FactKey.COMPANY_LOCATION_COUNTRY: FactValueType.STRING,
        FactKey.COMPANY_PLACE_OF_WORK: FactValueType.STRING,
        FactKey.COMPANY_REMOTE_POLICY: FactValueType.STRING,
        FactKey.COMPANY_WORK_ARRANGEMENT: FactValueType.STRING,
        FactKey.COMPANY_OFFICE_DAYS_PER_WEEK: FactValueType.INTEGER,
        FactKey.COMPANY_ALLOWED_REGIONS_TIMEZONES: FactValueType.STRING_LIST,
        FactKey.COMPANY_EMPLOYER_PITCH: FactValueType.STRING,
        FactKey.COMPANY_ROLE_RELEVANT_POSITIONING: FactValueType.STRING_LIST,
        FactKey.COMPANY_BUSINESS_UNIT: FactValueType.STRING,
        FactKey.COMPANY_HIRING_REASON: FactValueType.STRING,
        FactKey.COMPANY_GROWTH_CONTEXT: FactValueType.STRING,
        FactKey.COMPANY_ROLE_BUSINESS_IMPACT: FactValueType.STRING,
        FactKey.COMPANY_LANGUAGE_INTERNAL: FactValueType.OBJECT,
        FactKey.COMPANY_LANGUAGE_EXTERNAL: FactValueType.OBJECT,
        FactKey.COMPANY_NON_NEGOTIABLES: FactValueType.STRING_LIST,
        FactKey.COMPANY_COMPLIANCE_CONTEXT: FactValueType.STRING_LIST,
        FactKey.COMPANY_TARIFF_CONTEXT: FactValueType.STRING,
        FactKey.COMPANY_DEPARTMENT_NAME: FactValueType.STRING,
        FactKey.COMPANY_REPORTS_TO: FactValueType.STRING,
        FactKey.COMPANY_DIRECT_REPORTS_COUNT: FactValueType.INTEGER,
        FactKey.TEAM_NAME: FactValueType.STRING,
        FactKey.TEAM_LEADERSHIP_SCOPE: FactValueType.STRING,
        FactKey.TEAM_SIZE_DIRECT: FactValueType.INTEGER,
        FactKey.TEAM_STAKEHOLDERS_PRIMARY: FactValueType.STRING_LIST,
        FactKey.TEAM_SUCCESS_CONTEXT_90D: FactValueType.STRING,
        FactKey.ROLE_JOB_TITLE: FactValueType.STRING,
        FactKey.ROLE_EMPLOYMENT_TYPE: FactValueType.STRING,
        FactKey.ROLE_CONTRACT_TYPE: FactValueType.STRING,
        FactKey.ROLE_SENIORITY_LEVEL: FactValueType.STRING,
        FactKey.ROLE_JOB_REF_NUMBER: FactValueType.STRING,
        FactKey.ROLE_ROLE_OVERVIEW: FactValueType.STRING,
        FactKey.ROLE_RESPONSIBILITIES: FactValueType.STRING_LIST,
        FactKey.ROLE_RESPONSIBILITIES_PRIORITIZED: FactValueType.OBJECT_LIST,
        FactKey.ROLE_DELIVERABLES: FactValueType.STRING_LIST,
        FactKey.ROLE_SUCCESS_METRICS: FactValueType.STRING_LIST,
        FactKey.ROLE_SUCCESS_METRICS_TIMELINE: FactValueType.OBJECT,
        FactKey.ROLE_BUSINESS_OUTCOME_PRIMARY: FactValueType.STRING,
        FactKey.ROLE_DAY1_RESPONSIBILITIES: FactValueType.STRING_LIST,
        FactKey.ROLE_EXPANSION_SCOPE: FactValueType.STRING_LIST,
        FactKey.ROLE_DECISION_SCOPE: FactValueType.STRING,
        FactKey.ROLE_YEAR1_SUCCESS_SIGNALS: FactValueType.STRING,
        FactKey.ROLE_TECH_STACK: FactValueType.STRING_LIST,
        FactKey.ROLE_DOMAIN_EXPERTISE: FactValueType.STRING_LIST,
        FactKey.ROLE_TRAVEL_REQUIRED: FactValueType.BOOLEAN,
        FactKey.ROLE_TRAVEL_PROFILE: FactValueType.OBJECT,
        FactKey.ROLE_ON_CALL: FactValueType.BOOLEAN,
        FactKey.ROLE_ONBOARDING_NOTES: FactValueType.STRING,
        FactKey.ROLE_GAPS: FactValueType.STRING_LIST,
        FactKey.ROLE_ASSUMPTIONS: FactValueType.STRING_LIST,
        FactKey.SKILLS_ITEMS: FactValueType.OBJECT_LIST,
        FactKey.SKILLS_MUST_HAVE_SKILLS: FactValueType.STRING_LIST,
        FactKey.SKILLS_NICE_TO_HAVE_SKILLS: FactValueType.STRING_LIST,
        FactKey.SKILLS_SOFT_SKILLS: FactValueType.STRING_LIST,
        FactKey.SKILLS_EDUCATION: FactValueType.STRING_LIST,
        FactKey.SKILLS_CERTIFICATIONS: FactValueType.STRING_LIST,
        FactKey.SKILLS_LANGUAGES: FactValueType.STRING_LIST,
        FactKey.SKILLS_READINESS_TIMING: FactValueType.OBJECT_LIST,
        FactKey.SKILLS_FREE_TEXT_REASON: FactValueType.STRING,
        FactKey.SKILLS_KNOCKOUT_CRITERIA: FactValueType.STRING_LIST,
        FactKey.SKILLS_TRAINABLE_SKILLS: FactValueType.STRING_LIST,
        FactKey.BENEFITS_SALARY_RANGE: FactValueType.MONEY_RANGE,
        FactKey.BENEFITS_VARIABLE_PAY: FactValueType.OBJECT,
        FactKey.BENEFITS_BENEFITS: FactValueType.STRING_LIST,
        FactKey.BENEFITS_SHIFT_COMPENSATION: FactValueType.OBJECT,
        FactKey.BENEFITS_COLLECTIVE_AGREEMENT_CONTEXT: FactValueType.STRING_LIST,
        FactKey.BENEFITS_OFFER_COMPONENTS: FactValueType.STRING_LIST,
        FactKey.LEGAL_WORK_AUTHORIZATION_SUPPORT: FactValueType.STRING,
        FactKey.TIMELINE_START_FLEXIBILITY: FactValueType.OBJECT,
        FactKey.INTERVIEW_START_DATE: FactValueType.DATE_STRING,
        FactKey.INTERVIEW_APPLICATION_DEADLINE: FactValueType.DATE_STRING,
        FactKey.INTERVIEW_RECRUITMENT_STEPS: FactValueType.OBJECT_LIST,
        FactKey.INTERVIEW_CONTACTS: FactValueType.OBJECT_LIST,
        FactKey.INTERVIEW_ASSESSMENT_EVIDENCE: FactValueType.OBJECT_LIST,
        FactKey.INTERVIEW_STAGE_OWNERS: FactValueType.OBJECT_LIST,
        FactKey.INTERVIEW_COMMUNICATION_SLA: FactValueType.OBJECT_LIST,
        FactKey.INTERVIEW_SCORECARD_TEMPLATE: FactValueType.OBJECT,
        FactKey.INTERVIEW_CORE_QUESTIONS: FactValueType.STRING_LIST,
        FactKey.INTERVIEW_COMPLIANCE_NOTES: FactValueType.STRING,
    }

    assert {
        fact_key: fact.value_type for fact_key, fact in facts_by_key.items()
    } == expected_types


def test_fact_key_stability_snapshot() -> None:
    assert [fact_key.value for fact_key in FactKey] == EXPECTED_FACT_KEYS
    assert [fact.fact_key.value for fact in INTAKE_FACTS] == EXPECTED_FACT_KEYS


def test_fact_definitions_mark_salary_drivers_and_requirement_stages() -> None:
    facts_by_key = _facts_by_key()

    salary_driver_keys = {
        FactKey.BENEFITS_SALARY_RANGE,
        FactKey.ROLE_SENIORITY_LEVEL,
        FactKey.COMPANY_REMOTE_POLICY,
        FactKey.COMPANY_LOCATION_CITY,
        FactKey.COMPANY_LOCATION_COUNTRY,
        FactKey.ROLE_JOB_TITLE,
        FactKey.SKILLS_MUST_HAVE_SKILLS,
        FactKey.SKILLS_NICE_TO_HAVE_SKILLS,
        FactKey.SKILLS_CERTIFICATIONS,
        FactKey.SKILLS_LANGUAGES,
        FactKey.INTERVIEW_RECRUITMENT_STEPS,
    }

    assert {
        key
        for key, fact in facts_by_key.items()
        if fact.salary_impact == FactSalaryImpact.P50_DIRECT
    } == salary_driver_keys
    assert all(
        facts_by_key[key].requirement_stage == FactRequirementStage.BEFORE_SUMMARY
        for key in salary_driver_keys
    )
    assert (
        facts_by_key[FactKey.INTERVIEW_SCORECARD_TEMPLATE].requirement_stage
        == FactRequirementStage.BEFORE_ARTIFACT
    )
    assert facts_by_key[FactKey.COMPANY_EMPLOYER_PITCH].website_enrichable is True
