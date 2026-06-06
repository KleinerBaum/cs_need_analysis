from __future__ import annotations

import re
from collections import Counter

from constants import (
    INTAKE_FACTS,
    FactKey,
    FactPersistenceIntent,
    FactValueType,
    STEP_KEY_BENEFITS,
    STEP_KEY_COMPANY,
    STEP_KEY_INTERVIEW,
    STEP_KEY_ROLE_TASKS,
    STEP_KEY_SKILLS,
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


def test_fact_key_stability_snapshot() -> None:
    assert [fact_key.value for fact_key in FactKey] == EXPECTED_FACT_KEYS
    assert [fact.fact_key.value for fact in INTAKE_FACTS] == EXPECTED_FACT_KEYS
