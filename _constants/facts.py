"""Canonical intake fact contract."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final

from _constants.wizard import (
    STEP_KEY_BENEFITS,
    STEP_KEY_COMPANY,
    STEP_KEY_INTERVIEW,
    STEP_KEY_LANDING,
    STEP_KEY_ROLE_TASKS,
    STEP_KEY_SKILLS,
)


# ---- Canonical intake fact contract ----
class FactKey(str, Enum):
    INTAKE_HIRING_REASON = "intake.hiring_reason"
    INTAKE_URGENCY = "intake.urgency"
    INTAKE_HIRING_VOLUME = "intake.hiring_volume"
    INTAKE_SEARCH_CONFIDENTIALITY = "intake.search_confidentiality"
    INTAKE_ROLE_DEFINITION_MATURITY = "intake.role_definition_maturity"
    COMPANY_LANGUAGE_GUESS = "company.language_guess"
    COMPANY_COMPANY_NAME = "company.company_name"
    COMPANY_BRAND_NAME = "company.brand_name"
    COMPANY_COMPANY_WEBSITE = "company.company_website"
    COMPANY_LOCATION_CITY = "company.location_city"
    COMPANY_LOCATION_COUNTRY = "company.location_country"
    COMPANY_PLACE_OF_WORK = "company.place_of_work"
    COMPANY_REMOTE_POLICY = "company.remote_policy"
    COMPANY_WORK_ARRANGEMENT = "company.work_arrangement"
    COMPANY_OFFICE_DAYS_PER_WEEK = "company.office_days_per_week"
    COMPANY_ALLOWED_REGIONS_TIMEZONES = "company.allowed_regions_timezones"
    COMPANY_EMPLOYER_PITCH = "company.employer_pitch"
    COMPANY_ROLE_RELEVANT_POSITIONING = "company.role_relevant_positioning"
    COMPANY_BUSINESS_UNIT = "company.business_unit"
    COMPANY_HIRING_REASON = "company.hiring_reason"
    COMPANY_GROWTH_CONTEXT = "company.growth_context"
    COMPANY_ROLE_BUSINESS_IMPACT = "company.role_business_impact"
    COMPANY_LANGUAGE_INTERNAL = "company.language_internal"
    COMPANY_LANGUAGE_EXTERNAL = "company.language_external"
    COMPANY_NON_NEGOTIABLES = "company.non_negotiables"
    COMPANY_COMPLIANCE_CONTEXT = "company.compliance_context"
    COMPANY_TARIFF_CONTEXT = "company.tariff_context"
    COMPANY_DEPARTMENT_NAME = "company.department_name"
    COMPANY_REPORTS_TO = "company.reports_to"
    COMPANY_DIRECT_REPORTS_COUNT = "company.direct_reports_count"
    TEAM_NAME = "team.name"
    TEAM_LEADERSHIP_SCOPE = "team.leadership_scope"
    TEAM_SIZE_DIRECT = "team.size_direct"
    TEAM_STAKEHOLDERS_PRIMARY = "team.stakeholders_primary"
    TEAM_SUCCESS_CONTEXT_90D = "team.success_context_90d"
    ROLE_JOB_TITLE = "role.job_title"
    ROLE_EMPLOYMENT_TYPE = "role.employment_type"
    ROLE_CONTRACT_TYPE = "role.contract_type"
    ROLE_SENIORITY_LEVEL = "role.seniority_level"
    ROLE_JOB_REF_NUMBER = "role.job_ref_number"
    ROLE_ROLE_OVERVIEW = "role.role_overview"
    ROLE_RESPONSIBILITIES = "role.responsibilities"
    ROLE_RESPONSIBILITIES_PRIORITIZED = "role.responsibilities_prioritized"
    ROLE_DELIVERABLES = "role.deliverables"
    ROLE_SUCCESS_METRICS = "role.success_metrics"
    ROLE_SUCCESS_METRICS_TIMELINE = "role.success_metrics_timeline"
    ROLE_BUSINESS_OUTCOME_PRIMARY = "role.business_outcome_primary"
    ROLE_DAY1_RESPONSIBILITIES = "role.day1_responsibilities"
    ROLE_EXPANSION_SCOPE = "role.expansion_scope"
    ROLE_DECISION_SCOPE = "role.decision_scope"
    ROLE_YEAR1_SUCCESS_SIGNALS = "role.year1_success_signals"
    ROLE_TECH_STACK = "role.tech_stack"
    ROLE_DOMAIN_EXPERTISE = "role.domain_expertise"
    ROLE_TRAVEL_REQUIRED = "role.travel_required"
    ROLE_TRAVEL_PROFILE = "role.travel_profile"
    ROLE_ON_CALL = "role.on_call"
    ROLE_ONBOARDING_NOTES = "role.onboarding_notes"
    ROLE_GAPS = "role.gaps"
    ROLE_ASSUMPTIONS = "role.assumptions"
    SKILLS_ITEMS = "skills.items"
    SKILLS_MUST_HAVE_SKILLS = "skills.must_have_skills"
    SKILLS_NICE_TO_HAVE_SKILLS = "skills.nice_to_have_skills"
    SKILLS_SOFT_SKILLS = "skills.soft_skills"
    SKILLS_EDUCATION = "skills.education"
    SKILLS_CERTIFICATIONS = "skills.certifications"
    SKILLS_LANGUAGES = "skills.languages"
    SKILLS_READINESS_TIMING = "skills.readiness_timing"
    SKILLS_FREE_TEXT_REASON = "skills.free_text_reason"
    SKILLS_KNOCKOUT_CRITERIA = "skills.knockout_criteria"
    SKILLS_TRAINABLE_SKILLS = "skills.trainable_skills"
    BENEFITS_SALARY_RANGE = "benefits.salary_range"
    BENEFITS_VARIABLE_PAY = "benefits.variable_pay"
    BENEFITS_BENEFITS = "benefits.benefits"
    BENEFITS_SHIFT_COMPENSATION = "benefits.shift_compensation"
    BENEFITS_COLLECTIVE_AGREEMENT_CONTEXT = "benefits.collective_agreement_context"
    BENEFITS_OFFER_COMPONENTS = "benefits.offer_components"
    LEGAL_WORK_AUTHORIZATION_SUPPORT = "legal.work_authorization_support"
    TIMELINE_START_FLEXIBILITY = "timeline.start_flexibility"
    INTERVIEW_START_DATE = "interview.start_date"
    INTERVIEW_APPLICATION_DEADLINE = "interview.application_deadline"
    INTERVIEW_RECRUITMENT_STEPS = "interview.recruitment_steps"
    INTERVIEW_CONTACTS = "interview.contacts"
    INTERVIEW_ASSESSMENT_EVIDENCE = "interview.assessment_evidence"
    INTERVIEW_STAGE_OWNERS = "interview.stage_owners"
    INTERVIEW_COMMUNICATION_SLA = "interview.communication_sla"
    INTERVIEW_SCORECARD_TEMPLATE = "interview.scorecard_template"
    INTERVIEW_CORE_QUESTIONS = "interview.core_questions"
    INTERVIEW_COMPLIANCE_NOTES = "interview.compliance_notes"


class FactValueType(str, Enum):
    STRING = "string"
    STRING_LIST = "string_list"
    BOOLEAN = "boolean"
    INTEGER = "integer"
    DATE_STRING = "date_string"
    MONEY_RANGE = "money_range"
    OBJECT = "object"
    OBJECT_LIST = "object_list"


class FactPersistenceIntent(str, Enum):
    LEGACY_COMPATIBLE = "legacy_compatible"


class FactSalaryImpact(str, Enum):
    NONE = "none"
    QUALITY_INDIRECT = "quality_indirect"
    P50_DIRECT = "p50_direct"


class FactRequirementStage(str, Enum):
    BEFORE_SUMMARY = "before_summary"
    BEFORE_ARTIFACT = "before_artifact"
    OPTIONAL = "optional"


FACT_SALARY_IMPACT_DISPLAY_LABELS: Final[dict[FactSalaryImpact, str]] = {
    FactSalaryImpact.P50_DIRECT: "Salary-Treiber",
    FactSalaryImpact.QUALITY_INDIRECT: "Qualität/Unsicherheit",
    FactSalaryImpact.NONE: "Kein Salary-Einfluss",
}
FACT_REQUIREMENT_STAGE_DISPLAY_LABELS: Final[dict[FactRequirementStage, str]] = {
    FactRequirementStage.BEFORE_SUMMARY: "Pflicht vor Summary",
    FactRequirementStage.BEFORE_ARTIFACT: "Pflicht vor Recruiting-Unterlage",
    FactRequirementStage.OPTIONAL: "Optional",
}


class FactSourceType(str, Enum):
    MANUAL = "manual"
    JOBSPEC = "jobspec"
    HOMEPAGE = "homepage"
    ESCO = "esco"
    LLM = "llm"


class FactResolutionStatus(str, Enum):
    CONFIRMED = "confirmed"
    INFERRED = "inferred"
    ASSUMED = "assumed"
    CONFLICTED = "conflicted"
    MISSING = "missing"


class FactSensitivity(str, Enum):
    NORMAL = "normal"
    PERSONAL = "personal"
    RESTRICTED = "restricted"

@dataclass(frozen=True)
class IntakeFactDef:
    fact_key: FactKey
    label: str
    step_key: str
    value_type: FactValueType
    persistence_intent: FactPersistenceIntent
    salary_impact: FactSalaryImpact
    requirement_stage: FactRequirementStage
    website_enrichable: bool


_FACT_PERSISTENCE_LEGACY_COMPATIBLE: Final[FactPersistenceIntent] = (
    FactPersistenceIntent.LEGACY_COMPATIBLE
)
SALARY_DRIVER_FACT_KEYS: Final[frozenset[FactKey]] = frozenset(
    {
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
)
SALARY_QUALITY_DRIVER_FACT_KEYS: Final[frozenset[FactKey]] = frozenset(
    {
        FactKey.INTAKE_HIRING_REASON,
        FactKey.INTAKE_URGENCY,
        FactKey.INTAKE_HIRING_VOLUME,
        FactKey.INTAKE_SEARCH_CONFIDENTIALITY,
        FactKey.INTAKE_ROLE_DEFINITION_MATURITY,
        FactKey.COMPANY_WORK_ARRANGEMENT,
        FactKey.COMPANY_OFFICE_DAYS_PER_WEEK,
        FactKey.COMPANY_ALLOWED_REGIONS_TIMEZONES,
        FactKey.COMPANY_EMPLOYER_PITCH,
        FactKey.COMPANY_ROLE_RELEVANT_POSITIONING,
        FactKey.COMPANY_BUSINESS_UNIT,
        FactKey.COMPANY_HIRING_REASON,
        FactKey.COMPANY_GROWTH_CONTEXT,
        FactKey.COMPANY_ROLE_BUSINESS_IMPACT,
        FactKey.COMPANY_LANGUAGE_INTERNAL,
        FactKey.COMPANY_LANGUAGE_EXTERNAL,
        FactKey.COMPANY_NON_NEGOTIABLES,
        FactKey.COMPANY_COMPLIANCE_CONTEXT,
        FactKey.COMPANY_TARIFF_CONTEXT,
        FactKey.TEAM_NAME,
        FactKey.TEAM_LEADERSHIP_SCOPE,
        FactKey.TEAM_SIZE_DIRECT,
        FactKey.TEAM_STAKEHOLDERS_PRIMARY,
        FactKey.TEAM_SUCCESS_CONTEXT_90D,
        FactKey.ROLE_RESPONSIBILITIES,
        FactKey.ROLE_RESPONSIBILITIES_PRIORITIZED,
        FactKey.ROLE_SUCCESS_METRICS_TIMELINE,
        FactKey.ROLE_BUSINESS_OUTCOME_PRIMARY,
        FactKey.ROLE_DAY1_RESPONSIBILITIES,
        FactKey.ROLE_EXPANSION_SCOPE,
        FactKey.ROLE_DECISION_SCOPE,
        FactKey.ROLE_YEAR1_SUCCESS_SIGNALS,
        FactKey.SKILLS_ITEMS,
        FactKey.SKILLS_READINESS_TIMING,
        FactKey.SKILLS_FREE_TEXT_REASON,
        FactKey.SKILLS_KNOCKOUT_CRITERIA,
        FactKey.SKILLS_TRAINABLE_SKILLS,
        FactKey.TIMELINE_START_FLEXIBILITY,
    }
)
BEFORE_SUMMARY_REQUIRED_FACT_KEYS: Final[frozenset[FactKey]] = (
    SALARY_DRIVER_FACT_KEYS
    | frozenset(
        {
            FactKey.INTAKE_SEARCH_CONFIDENTIALITY,
            FactKey.ROLE_EMPLOYMENT_TYPE,
            FactKey.ROLE_CONTRACT_TYPE,
            FactKey.ROLE_TRAVEL_REQUIRED,
            FactKey.ROLE_ON_CALL,
            FactKey.BENEFITS_VARIABLE_PAY,
            FactKey.COMPANY_COMPLIANCE_CONTEXT,
            FactKey.LEGAL_WORK_AUTHORIZATION_SUPPORT,
            FactKey.INTERVIEW_START_DATE,
            FactKey.INTERVIEW_APPLICATION_DEADLINE,
        }
    )
)
BEFORE_ARTIFACT_REQUIRED_FACT_KEYS: Final[frozenset[FactKey]] = frozenset(
    {
        FactKey.BENEFITS_OFFER_COMPONENTS,
        FactKey.INTERVIEW_ASSESSMENT_EVIDENCE,
        FactKey.INTERVIEW_STAGE_OWNERS,
        FactKey.INTERVIEW_COMMUNICATION_SLA,
        FactKey.INTERVIEW_SCORECARD_TEMPLATE,
        FactKey.INTERVIEW_CORE_QUESTIONS,
        FactKey.INTERVIEW_COMPLIANCE_NOTES,
    }
)
WEBSITE_ENRICHABLE_FACT_KEYS: Final[frozenset[FactKey]] = frozenset(
    {
        FactKey.COMPANY_COMPANY_NAME,
        FactKey.COMPANY_COMPANY_WEBSITE,
        FactKey.COMPANY_LOCATION_CITY,
        FactKey.COMPANY_LOCATION_COUNTRY,
        FactKey.COMPANY_WORK_ARRANGEMENT,
        FactKey.COMPANY_OFFICE_DAYS_PER_WEEK,
        FactKey.COMPANY_ALLOWED_REGIONS_TIMEZONES,
        FactKey.COMPANY_EMPLOYER_PITCH,
        FactKey.COMPANY_ROLE_RELEVANT_POSITIONING,
        FactKey.COMPANY_LANGUAGE_INTERNAL,
        FactKey.COMPANY_COMPLIANCE_CONTEXT,
        FactKey.ROLE_TECH_STACK,
        FactKey.ROLE_DOMAIN_EXPERTISE,
        FactKey.BENEFITS_BENEFITS,
    }
)


def _intake_fact(
    fact_key: FactKey,
    label: str,
    step_key: str,
    value_type: FactValueType,
    *,
    salary_impact: FactSalaryImpact | None = None,
    requirement_stage: FactRequirementStage | None = None,
    website_enrichable: bool | None = None,
) -> IntakeFactDef:
    if salary_impact is None:
        if fact_key in SALARY_DRIVER_FACT_KEYS:
            salary_impact = FactSalaryImpact.P50_DIRECT
        elif fact_key in SALARY_QUALITY_DRIVER_FACT_KEYS:
            salary_impact = FactSalaryImpact.QUALITY_INDIRECT
        else:
            salary_impact = FactSalaryImpact.NONE
    if requirement_stage is None:
        if fact_key in BEFORE_SUMMARY_REQUIRED_FACT_KEYS:
            requirement_stage = FactRequirementStage.BEFORE_SUMMARY
        elif fact_key in BEFORE_ARTIFACT_REQUIRED_FACT_KEYS:
            requirement_stage = FactRequirementStage.BEFORE_ARTIFACT
        else:
            requirement_stage = FactRequirementStage.OPTIONAL
    if website_enrichable is None:
        website_enrichable = fact_key in WEBSITE_ENRICHABLE_FACT_KEYS
    return IntakeFactDef(
        fact_key=fact_key,
        label=label,
        step_key=step_key,
        value_type=value_type,
        persistence_intent=_FACT_PERSISTENCE_LEGACY_COMPATIBLE,
        salary_impact=salary_impact,
        requirement_stage=requirement_stage,
        website_enrichable=website_enrichable,
    )


# FACT_REGISTRY: canonical intake fact definitions used by runtime write-through.
INTAKE_FACTS: Final[tuple[IntakeFactDef, ...]] = (
    _intake_fact(
        FactKey.INTAKE_HIRING_REASON,
        "Hiring reason",
        STEP_KEY_LANDING,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.INTAKE_URGENCY,
        "Hiring urgency",
        STEP_KEY_LANDING,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.INTAKE_HIRING_VOLUME,
        "Hiring volume",
        STEP_KEY_LANDING,
        FactValueType.INTEGER,
    ),
    _intake_fact(
        FactKey.INTAKE_SEARCH_CONFIDENTIALITY,
        "Search confidentiality",
        STEP_KEY_LANDING,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.INTAKE_ROLE_DEFINITION_MATURITY,
        "Role definition maturity",
        STEP_KEY_LANDING,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.COMPANY_LANGUAGE_GUESS,
        "Detected language",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.COMPANY_COMPANY_NAME,
        "Company name",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.COMPANY_BRAND_NAME,
        "Brand name",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.COMPANY_COMPANY_WEBSITE,
        "Company website",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.COMPANY_LOCATION_CITY,
        "Location city",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.COMPANY_LOCATION_COUNTRY,
        "Location country",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.COMPANY_PLACE_OF_WORK,
        "Place of work",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.COMPANY_REMOTE_POLICY,
        "Remote policy",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.COMPANY_WORK_ARRANGEMENT,
        "Work arrangement",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.COMPANY_OFFICE_DAYS_PER_WEEK,
        "Office days per week",
        STEP_KEY_COMPANY,
        FactValueType.INTEGER,
    ),
    _intake_fact(
        FactKey.COMPANY_ALLOWED_REGIONS_TIMEZONES,
        "Allowed regions and timezones",
        STEP_KEY_COMPANY,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.COMPANY_EMPLOYER_PITCH,
        "Employer pitch",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.COMPANY_ROLE_RELEVANT_POSITIONING,
        "Role-relevant positioning",
        STEP_KEY_COMPANY,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.COMPANY_BUSINESS_UNIT,
        "Business unit",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.COMPANY_HIRING_REASON,
        "Company hiring reason",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.COMPANY_GROWTH_CONTEXT,
        "Company growth context",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.COMPANY_ROLE_BUSINESS_IMPACT,
        "Role business impact",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.COMPANY_LANGUAGE_INTERNAL,
        "Internal working language",
        STEP_KEY_COMPANY,
        FactValueType.OBJECT,
    ),
    _intake_fact(
        FactKey.COMPANY_LANGUAGE_EXTERNAL,
        "External communication language",
        STEP_KEY_COMPANY,
        FactValueType.OBJECT,
    ),
    _intake_fact(
        FactKey.COMPANY_NON_NEGOTIABLES,
        "Non-negotiables",
        STEP_KEY_COMPANY,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.COMPANY_COMPLIANCE_CONTEXT,
        "Compliance context",
        STEP_KEY_COMPANY,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.COMPANY_TARIFF_CONTEXT,
        "Tariff context",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.COMPANY_DEPARTMENT_NAME,
        "Department name",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.COMPANY_REPORTS_TO,
        "Reports to",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.COMPANY_DIRECT_REPORTS_COUNT,
        "Direct reports count",
        STEP_KEY_COMPANY,
        FactValueType.INTEGER,
    ),
    _intake_fact(
        FactKey.TEAM_NAME,
        "Team name",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.TEAM_LEADERSHIP_SCOPE,
        "Leadership scope",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.TEAM_SIZE_DIRECT,
        "Direct team size",
        STEP_KEY_COMPANY,
        FactValueType.INTEGER,
    ),
    _intake_fact(
        FactKey.TEAM_STAKEHOLDERS_PRIMARY,
        "Primary stakeholders",
        STEP_KEY_COMPANY,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.TEAM_SUCCESS_CONTEXT_90D,
        "90-day team success context",
        STEP_KEY_COMPANY,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.ROLE_JOB_TITLE,
        "Job title",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.ROLE_EMPLOYMENT_TYPE,
        "Employment type",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.ROLE_CONTRACT_TYPE,
        "Contract type",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.ROLE_SENIORITY_LEVEL,
        "Seniority level",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.ROLE_JOB_REF_NUMBER,
        "Job reference number",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.ROLE_ROLE_OVERVIEW,
        "Role overview",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.ROLE_RESPONSIBILITIES,
        "Responsibilities",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.ROLE_RESPONSIBILITIES_PRIORITIZED,
        "Prioritized responsibilities",
        STEP_KEY_ROLE_TASKS,
        FactValueType.OBJECT_LIST,
    ),
    _intake_fact(
        FactKey.ROLE_DELIVERABLES,
        "Deliverables",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.ROLE_SUCCESS_METRICS,
        "Success metrics",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.ROLE_SUCCESS_METRICS_TIMELINE,
        "Success metrics timeline",
        STEP_KEY_ROLE_TASKS,
        FactValueType.OBJECT,
    ),
    _intake_fact(
        FactKey.ROLE_BUSINESS_OUTCOME_PRIMARY,
        "Primary business outcome",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.ROLE_DAY1_RESPONSIBILITIES,
        "Day-1 responsibilities",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.ROLE_EXPANSION_SCOPE,
        "Expansion scope",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.ROLE_DECISION_SCOPE,
        "Decision scope",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.ROLE_YEAR1_SUCCESS_SIGNALS,
        "Year-1 success signals",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.ROLE_TECH_STACK,
        "Tech stack",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.ROLE_DOMAIN_EXPERTISE,
        "Domain expertise",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.ROLE_TRAVEL_REQUIRED,
        "Travel required",
        STEP_KEY_ROLE_TASKS,
        FactValueType.BOOLEAN,
    ),
    _intake_fact(
        FactKey.ROLE_TRAVEL_PROFILE,
        "Travel profile",
        STEP_KEY_BENEFITS,
        FactValueType.OBJECT,
    ),
    _intake_fact(
        FactKey.ROLE_ON_CALL,
        "On-call requirement",
        STEP_KEY_ROLE_TASKS,
        FactValueType.BOOLEAN,
    ),
    _intake_fact(
        FactKey.ROLE_ONBOARDING_NOTES,
        "Onboarding notes",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.ROLE_GAPS,
        "Extraction gaps",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.ROLE_ASSUMPTIONS,
        "Extraction assumptions",
        STEP_KEY_ROLE_TASKS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.SKILLS_ITEMS,
        "Structured skill items",
        STEP_KEY_SKILLS,
        FactValueType.OBJECT_LIST,
    ),
    _intake_fact(
        FactKey.SKILLS_MUST_HAVE_SKILLS,
        "Must-have skills",
        STEP_KEY_SKILLS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.SKILLS_NICE_TO_HAVE_SKILLS,
        "Nice-to-have skills",
        STEP_KEY_SKILLS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.SKILLS_SOFT_SKILLS,
        "Soft skills",
        STEP_KEY_SKILLS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.SKILLS_EDUCATION,
        "Education",
        STEP_KEY_SKILLS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.SKILLS_CERTIFICATIONS,
        "Certifications",
        STEP_KEY_SKILLS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.SKILLS_LANGUAGES,
        "Languages",
        STEP_KEY_SKILLS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.SKILLS_READINESS_TIMING,
        "Skill readiness timing",
        STEP_KEY_SKILLS,
        FactValueType.OBJECT_LIST,
    ),
    _intake_fact(
        FactKey.SKILLS_FREE_TEXT_REASON,
        "Free-text skill retention reason",
        STEP_KEY_SKILLS,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.SKILLS_KNOCKOUT_CRITERIA,
        "Knockout criteria",
        STEP_KEY_SKILLS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.SKILLS_TRAINABLE_SKILLS,
        "Trainable skills",
        STEP_KEY_SKILLS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.BENEFITS_SALARY_RANGE,
        "Salary range",
        STEP_KEY_BENEFITS,
        FactValueType.MONEY_RANGE,
    ),
    _intake_fact(
        FactKey.BENEFITS_VARIABLE_PAY,
        "Variable pay",
        STEP_KEY_BENEFITS,
        FactValueType.OBJECT,
    ),
    _intake_fact(
        FactKey.BENEFITS_BENEFITS,
        "Benefits",
        STEP_KEY_BENEFITS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.BENEFITS_SHIFT_COMPENSATION,
        "Shift compensation",
        STEP_KEY_BENEFITS,
        FactValueType.OBJECT,
    ),
    _intake_fact(
        FactKey.BENEFITS_COLLECTIVE_AGREEMENT_CONTEXT,
        "Collective agreement context",
        STEP_KEY_BENEFITS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.BENEFITS_OFFER_COMPONENTS,
        "Offer components",
        STEP_KEY_BENEFITS,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.LEGAL_WORK_AUTHORIZATION_SUPPORT,
        "Work authorization support",
        STEP_KEY_BENEFITS,
        FactValueType.STRING,
    ),
    _intake_fact(
        FactKey.TIMELINE_START_FLEXIBILITY,
        "Start flexibility",
        STEP_KEY_BENEFITS,
        FactValueType.OBJECT,
    ),
    _intake_fact(
        FactKey.INTERVIEW_START_DATE,
        "Start date",
        STEP_KEY_INTERVIEW,
        FactValueType.DATE_STRING,
    ),
    _intake_fact(
        FactKey.INTERVIEW_APPLICATION_DEADLINE,
        "Application deadline",
        STEP_KEY_INTERVIEW,
        FactValueType.DATE_STRING,
    ),
    _intake_fact(
        FactKey.INTERVIEW_RECRUITMENT_STEPS,
        "Recruitment steps",
        STEP_KEY_INTERVIEW,
        FactValueType.OBJECT_LIST,
    ),
    _intake_fact(
        FactKey.INTERVIEW_CONTACTS,
        "Contacts",
        STEP_KEY_INTERVIEW,
        FactValueType.OBJECT_LIST,
    ),
    _intake_fact(
        FactKey.INTERVIEW_ASSESSMENT_EVIDENCE,
        "Assessment evidence",
        STEP_KEY_INTERVIEW,
        FactValueType.OBJECT_LIST,
    ),
    _intake_fact(
        FactKey.INTERVIEW_STAGE_OWNERS,
        "Stage owners",
        STEP_KEY_INTERVIEW,
        FactValueType.OBJECT_LIST,
    ),
    _intake_fact(
        FactKey.INTERVIEW_COMMUNICATION_SLA,
        "Candidate communication SLA",
        STEP_KEY_INTERVIEW,
        FactValueType.OBJECT_LIST,
    ),
    _intake_fact(
        FactKey.INTERVIEW_SCORECARD_TEMPLATE,
        "Scorecard template",
        STEP_KEY_INTERVIEW,
        FactValueType.OBJECT,
    ),
    _intake_fact(
        FactKey.INTERVIEW_CORE_QUESTIONS,
        "Core interview questions",
        STEP_KEY_INTERVIEW,
        FactValueType.STRING_LIST,
    ),
    _intake_fact(
        FactKey.INTERVIEW_COMPLIANCE_NOTES,
        "Interview compliance notes",
        STEP_KEY_INTERVIEW,
        FactValueType.STRING,
    ),
)
