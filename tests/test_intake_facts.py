from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

from constants import FactKey, SSKey
from intake_facts import (
    collect_legacy_facts,
    get_intake_fact_state,
    reset_intake_fact_state,
    resolve_legacy_fact,
)
from schemas import Contact, JobAdExtract, MoneyRange, RecruitmentStep
import state


def test_init_session_state_initializes_intake_fact_state(monkeypatch) -> None:
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

    assert fake_session_state[SSKey.INTAKE_FACTS.value] == {}


def test_reset_intake_fact_state_clears_existing_registry_payload() -> None:
    session_state = {SSKey.INTAKE_FACTS.value: {"role.job_title": "Engineer"}}

    reset_intake_fact_state(session_state)

    assert session_state[SSKey.INTAKE_FACTS.value] == {}


def test_get_intake_fact_state_does_not_create_missing_key() -> None:
    session_state: dict[str, object] = {}

    assert get_intake_fact_state(session_state) == {}
    assert SSKey.INTAKE_FACTS.value not in session_state


def test_collect_legacy_facts_resolves_job_extract_values() -> None:
    job_extract = JobAdExtract(
        company_name=" Example GmbH ",
        company_website=" https://example.test ",
        location_city=" Berlin ",
        job_title=" Data Engineer ",
        responsibilities=[" Build pipelines ", ""],
        success_metrics=["Reliable reporting"],
        must_have_skills=[" Python ", "SQL"],
        nice_to_have_skills=["Airflow"],
        languages=["Deutsch", " Englisch "],
        salary_range=MoneyRange(
            min=60000,
            max=80000,
            currency="EUR",
            period="yearly",
        ),
        benefits=[" Remote work ", "Weiterbildung"],
        recruitment_steps=[
            RecruitmentStep(name="Phone screen", details="30 minutes"),
        ],
        contacts=[
            Contact(name="Hiring Team", role="Recruiting"),
        ],
    ).model_dump(mode="json")
    session_state = {SSKey.JOB_EXTRACT.value: job_extract}

    facts = collect_legacy_facts(session_state)

    assert facts[FactKey.COMPANY_COMPANY_NAME] == "Example GmbH"
    assert facts[FactKey.COMPANY_COMPANY_WEBSITE] == "https://example.test"
    assert facts[FactKey.COMPANY_LOCATION_CITY] == "Berlin"
    assert facts[FactKey.ROLE_JOB_TITLE] == "Data Engineer"
    assert facts[FactKey.ROLE_RESPONSIBILITIES] == ["Build pipelines"]
    assert facts[FactKey.ROLE_SUCCESS_METRICS] == ["Reliable reporting"]
    assert facts[FactKey.SKILLS_MUST_HAVE_SKILLS] == ["Python", "SQL"]
    assert facts[FactKey.SKILLS_NICE_TO_HAVE_SKILLS] == ["Airflow"]
    assert facts[FactKey.SKILLS_LANGUAGES] == ["Deutsch", "Englisch"]
    assert facts[FactKey.BENEFITS_SALARY_RANGE] == {
        "min": 60000.0,
        "max": 80000.0,
        "currency": "EUR",
        "period": "yearly",
    }
    assert facts[FactKey.BENEFITS_BENEFITS] == ["Remote work", "Weiterbildung"]
    assert facts[FactKey.INTERVIEW_RECRUITMENT_STEPS] == [
        {"name": "Phone screen", "details": "30 minutes"}
    ]
    assert facts[FactKey.INTERVIEW_CONTACTS] == [
        {"name": "Hiring Team", "role": "Recruiting"}
    ]


def test_resolve_legacy_fact_uses_session_state_fallbacks() -> None:
    session_state = {
        SSKey.ROLE_TASKS_SELECTED.value: ["Build APIs", "  "],
        SSKey.SKILLS_SELECTED.value: ["Python", "SQL", "Go"],
        SSKey.SKILLS_SELECTED_STATUS.value: {
            "label:python": {"status": "must"},
            "label:sql": {"status": "nice"},
            "label:go": {"status": "ignored"},
        },
        SSKey.BENEFITS_SELECTED.value: ["Remote work"],
        SSKey.INTERVIEW_INTERNAL_FLOW.value: {
            "contacts": [
                {
                    "name": "Recruiting Team",
                    "role": "Talent Acquisition",
                    "email": "",
                    "phone": None,
                }
            ],
            "info_loop_items": [],
            "earliest_start_date": None,
            "latest_start_date": None,
            "selected_value_ids": [],
        },
    }

    assert resolve_legacy_fact(FactKey.ROLE_RESPONSIBILITIES, session_state) == [
        "Build APIs"
    ]
    assert resolve_legacy_fact(
        FactKey.SKILLS_MUST_HAVE_SKILLS.value,
        session_state,
    ) == ["Python"]
    assert resolve_legacy_fact(FactKey.SKILLS_NICE_TO_HAVE_SKILLS, session_state) == [
        "SQL"
    ]
    assert resolve_legacy_fact(FactKey.BENEFITS_BENEFITS, session_state) == [
        "Remote work"
    ]
    assert resolve_legacy_fact(FactKey.INTERVIEW_CONTACTS, session_state) == [
        {"name": "Recruiting Team", "role": "Talent Acquisition"}
    ]


def test_empty_legacy_values_do_not_produce_meaningful_facts() -> None:
    session_state = {
        SSKey.JOB_EXTRACT.value: {
            "company_name": " ",
            "job_title": "",
            "responsibilities": [" "],
            "salary_range": {},
            "contacts": [{"name": "", "role": None}],
        },
        SSKey.ROLE_TASKS_SELECTED.value: [" "],
        SSKey.SKILLS_SELECTED.value: ["Python"],
        SSKey.SKILLS_SELECTED_STATUS.value: {},
        SSKey.BENEFITS_SELECTED.value: [],
        SSKey.INTERVIEW_INTERNAL_FLOW.value: {"contacts": []},
    }

    assert collect_legacy_facts(session_state) == {}


def test_adapters_do_not_mutate_session_state() -> None:
    session_state = {
        SSKey.INTAKE_FACTS.value: {"existing": "payload"},
        SSKey.JOB_EXTRACT.value: JobAdExtract(
            job_title="Engineer",
            contacts=[Contact(name="Hiring Team")],
        ).model_dump(mode="json"),
        SSKey.INTERVIEW_INTERNAL_FLOW.value: {
            "contacts": [{"name": "Recruiting Team"}],
        },
    }
    before = deepcopy(session_state)

    assert resolve_legacy_fact(FactKey.ROLE_JOB_TITLE, session_state) == "Engineer"
    assert collect_legacy_facts(session_state)[FactKey.ROLE_JOB_TITLE] == "Engineer"

    assert session_state == before
