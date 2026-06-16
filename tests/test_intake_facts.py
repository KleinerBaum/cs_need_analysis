from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

from constants import FactKey, FactResolutionStatus, FactSensitivity, FactSourceType, SSKey
from intake_facts import (
    build_intake_fact_resolution_state,
    collect_legacy_facts,
    get_intake_fact_evidence_state,
    get_intake_fact_state,
    latest_fact_confidence,
    mark_intake_facts_used_by_artifact,
    reset_intake_fact_evidence_state,
    reset_intake_fact_state,
    resolve_legacy_fact,
    sync_selected_skill_intake_facts,
    write_intake_fact,
    write_intake_fact_by_legacy_field,
    write_intake_fact_evidence,
    write_job_extract_intake_facts,
)
from schemas import Contact, JobAdExtract, JobAdFieldEvidence, MoneyRange, RecruitmentStep
import state
from usage_events import get_usage_events


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
    assert fake_session_state[SSKey.INTAKE_FACT_EVIDENCE.value] == {}


def test_reset_intake_fact_state_clears_existing_registry_payload() -> None:
    session_state = {SSKey.INTAKE_FACTS.value: {"role.job_title": "Engineer"}}

    reset_intake_fact_state(session_state)

    assert session_state[SSKey.INTAKE_FACTS.value] == {}


def test_reset_intake_fact_evidence_state_clears_existing_payload() -> None:
    session_state = {
        SSKey.INTAKE_FACT_EVIDENCE.value: {
            "role.job_title": {"confidence": 0.75}
        }
    }

    reset_intake_fact_evidence_state(session_state)

    assert session_state[SSKey.INTAKE_FACT_EVIDENCE.value] == {}


def test_get_intake_fact_state_does_not_create_missing_key() -> None:
    session_state: dict[str, object] = {}

    assert get_intake_fact_state(session_state) == {}
    assert SSKey.INTAKE_FACTS.value not in session_state


def test_get_intake_fact_evidence_state_does_not_create_missing_key() -> None:
    session_state: dict[str, object] = {}

    assert get_intake_fact_evidence_state(session_state) == {}
    assert SSKey.INTAKE_FACT_EVIDENCE.value not in session_state


def test_collect_legacy_facts_resolves_job_extract_values() -> None:
    job_extract = JobAdExtract(
        language_guess="de",
        company_name=" Example GmbH ",
        brand_name="Example",
        company_website=" https://example.test ",
        location_city=" Berlin ",
        location_country=" DE ",
        place_of_work=" Office ",
        remote_policy=" Hybrid ",
        department_name=" Data ",
        reports_to=" CTO ",
        direct_reports_count=2,
        job_title=" Data Engineer ",
        employment_type=" Vollzeit ",
        contract_type=" Unbefristet ",
        seniority_level=" Senior ",
        job_ref_number=" REF-123 ",
        role_overview=" Build data products ",
        responsibilities=[" Build pipelines ", ""],
        deliverables=["Data marts"],
        success_metrics=["Reliable reporting"],
        tech_stack=["Python", "SQL"],
        domain_expertise=["Retail"],
        travel_required="Nein",
        on_call="Nein",
        onboarding_notes="Buddy program",
        gaps=["Budget klaeren"],
        assumptions=["Hybrid is possible"],
        must_have_skills=[" Python ", "SQL"],
        nice_to_have_skills=["Airflow"],
        soft_skills=["Kommunikation"],
        education=["Bachelor"],
        certifications=["AWS"],
        languages=["Deutsch", " Englisch "],
        start_date="2026-07-01",
        application_deadline="2026-06-20",
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

    assert facts[FactKey.COMPANY_LANGUAGE_GUESS] == "de"
    assert facts[FactKey.COMPANY_COMPANY_NAME] == "Example GmbH"
    assert facts[FactKey.COMPANY_BRAND_NAME] == "Example"
    assert facts[FactKey.COMPANY_COMPANY_WEBSITE] == "https://example.test"
    assert facts[FactKey.COMPANY_LOCATION_CITY] == "Berlin"
    assert facts[FactKey.COMPANY_LOCATION_COUNTRY] == "DE"
    assert facts[FactKey.COMPANY_PLACE_OF_WORK] == "Office"
    assert facts[FactKey.COMPANY_REMOTE_POLICY] == "Hybrid"
    assert facts[FactKey.COMPANY_DEPARTMENT_NAME] == "Data"
    assert facts[FactKey.COMPANY_REPORTS_TO] == "CTO"
    assert facts[FactKey.COMPANY_DIRECT_REPORTS_COUNT] == 2
    assert facts[FactKey.ROLE_JOB_TITLE] == "Data Engineer"
    assert facts[FactKey.ROLE_EMPLOYMENT_TYPE] == "Vollzeit"
    assert facts[FactKey.ROLE_CONTRACT_TYPE] == "Unbefristet"
    assert facts[FactKey.ROLE_SENIORITY_LEVEL] == "Senior"
    assert facts[FactKey.ROLE_JOB_REF_NUMBER] == "REF-123"
    assert facts[FactKey.ROLE_ROLE_OVERVIEW] == "Build data products"
    assert facts[FactKey.ROLE_RESPONSIBILITIES] == ["Build pipelines"]
    assert facts[FactKey.ROLE_DELIVERABLES] == ["Data marts"]
    assert facts[FactKey.ROLE_SUCCESS_METRICS] == ["Reliable reporting"]
    assert facts[FactKey.ROLE_TECH_STACK] == ["Python", "SQL"]
    assert facts[FactKey.ROLE_DOMAIN_EXPERTISE] == ["Retail"]
    assert facts[FactKey.ROLE_TRAVEL_REQUIRED] == "Nein"
    assert facts[FactKey.ROLE_ON_CALL] == "Nein"
    assert facts[FactKey.ROLE_ONBOARDING_NOTES] == "Buddy program"
    assert facts[FactKey.ROLE_GAPS] == ["Budget klaeren"]
    assert facts[FactKey.ROLE_ASSUMPTIONS] == ["Hybrid is possible"]
    assert facts[FactKey.SKILLS_MUST_HAVE_SKILLS] == ["Python", "SQL"]
    assert facts[FactKey.SKILLS_NICE_TO_HAVE_SKILLS] == ["Airflow"]
    assert facts[FactKey.SKILLS_SOFT_SKILLS] == ["Kommunikation"]
    assert facts[FactKey.SKILLS_EDUCATION] == ["Bachelor"]
    assert facts[FactKey.SKILLS_CERTIFICATIONS] == ["AWS"]
    assert facts[FactKey.SKILLS_LANGUAGES] == ["Deutsch", "Englisch"]
    assert facts[FactKey.INTERVIEW_START_DATE] == "2026-07-01"
    assert facts[FactKey.INTERVIEW_APPLICATION_DEADLINE] == "2026-06-20"
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


def test_write_intake_fact_by_legacy_field_updates_fact_state_only() -> None:
    session_state = {
        SSKey.ANSWERS.value: {},
        SSKey.INTAKE_FACTS.value: {},
    }

    write_intake_fact_by_legacy_field(session_state, "company_name", " Example GmbH ")
    write_intake_fact_by_legacy_field(session_state, "brand_name", " Example ")
    write_intake_fact_by_legacy_field(session_state, "remote_policy", " Hybrid ")
    write_intake_fact_by_legacy_field(session_state, "direct_reports_count", 2)
    write_intake_fact_by_legacy_field(session_state, "responsibilities", [" Build "])
    write_intake_fact_by_legacy_field(session_state, "travel_required", False)
    write_intake_fact_by_legacy_field(session_state, "on_call", True)
    write_intake_fact_by_legacy_field(session_state, "certifications", [" AWS "])
    write_intake_fact_by_legacy_field(
        session_state,
        "salary_range",
        {"min": 60000, "max": 80000, "currency": " EUR ", "notes": ""},
    )
    write_intake_fact_by_legacy_field(
        session_state,
        "benefits",
        [" Remote work ", " "],
    )
    write_intake_fact_by_legacy_field(
        session_state,
        "recruitment_steps",
        [{"name": " Phone screen ", "details": ""}],
    )
    write_intake_fact_by_legacy_field(
        session_state,
        "contacts",
        [{"name": " Hiring Team ", "role": "Recruiting", "email": ""}],
    )

    assert session_state[SSKey.ANSWERS.value] == {}
    assert session_state[SSKey.INTAKE_FACTS.value] == {
        FactKey.COMPANY_COMPANY_NAME.value: "Example GmbH",
        FactKey.COMPANY_BRAND_NAME.value: "Example",
        FactKey.COMPANY_REMOTE_POLICY.value: "Hybrid",
        FactKey.COMPANY_DIRECT_REPORTS_COUNT.value: 2,
        FactKey.ROLE_RESPONSIBILITIES.value: ["Build"],
        FactKey.ROLE_TRAVEL_REQUIRED.value: False,
        FactKey.ROLE_ON_CALL.value: True,
        FactKey.SKILLS_CERTIFICATIONS.value: ["AWS"],
        FactKey.BENEFITS_SALARY_RANGE.value: {
            "min": 60000,
            "max": 80000,
            "currency": "EUR",
        },
        FactKey.BENEFITS_BENEFITS.value: ["Remote work"],
        FactKey.INTERVIEW_RECRUITMENT_STEPS.value: [{"name": "Phone screen"}],
        FactKey.INTERVIEW_CONTACTS.value: [
            {"name": "Hiring Team", "role": "Recruiting"}
        ],
    }


def test_write_job_extract_intake_facts_mirrors_supported_fields() -> None:
    session_state = {
        SSKey.JOB_EXTRACT.value: {
            "company_name": "Legacy GmbH",
            "job_title": "Legacy title",
        },
        SSKey.INTAKE_FACTS.value: {},
    }
    job = JobAdExtract(
        language_guess="de",
        company_name=" Acme GmbH ",
        brand_name=" Acme Jobs ",
        company_website=" https://example.test ",
        location_city=" Berlin ",
        location_country=" DE ",
        place_of_work=" Berlin office ",
        job_title=" Data Engineer ",
        employment_type=" Vollzeit ",
        contract_type=" Unbefristet ",
        seniority_level=" Senior ",
        job_ref_number=" REF-123 ",
        role_overview=" Build reliable data products ",
        responsibilities=[" Build pipelines "],
        deliverables=["Data marts"],
        success_metrics=["Reliable reporting"],
        tech_stack=["Python"],
        domain_expertise=["Retail"],
        remote_policy=" Hybrid ",
        travel_required="Ja",
        on_call="Nein",
        onboarding_notes="Buddy program",
        gaps=["Budget klaeren"],
        assumptions=["Hybrid possible"],
        must_have_skills=[" Python ", ""],
        nice_to_have_skills=["Airflow"],
        soft_skills=["Kommunikation"],
        education=["Bachelor"],
        certifications=["AWS"],
        languages=["Deutsch"],
        start_date="2026-07-01",
        application_deadline="2026-06-20",
        salary_range=MoneyRange(
            min=60000,
            max=80000,
            currency="EUR",
            period="yearly",
        ),
        benefits=[" Remote work ", " "],
        recruitment_steps=[
            RecruitmentStep(name="Phone screen", details="30 minutes"),
        ],
        contacts=[
            Contact(name="Hiring Team", role="Recruiting"),
        ],
    )

    write_job_extract_intake_facts(session_state, job)

    assert session_state[SSKey.JOB_EXTRACT.value] == {
        "company_name": "Legacy GmbH",
        "job_title": "Legacy title",
    }
    assert session_state[SSKey.INTAKE_FACTS.value] == {
        FactKey.COMPANY_LANGUAGE_GUESS.value: "de",
        FactKey.COMPANY_COMPANY_NAME.value: "Acme GmbH",
        FactKey.COMPANY_BRAND_NAME.value: "Acme Jobs",
        FactKey.COMPANY_COMPANY_WEBSITE.value: "https://example.test",
        FactKey.COMPANY_LOCATION_CITY.value: "Berlin",
        FactKey.COMPANY_LOCATION_COUNTRY.value: "DE",
        FactKey.COMPANY_PLACE_OF_WORK.value: "Berlin office",
        FactKey.COMPANY_REMOTE_POLICY.value: "Hybrid",
        FactKey.ROLE_JOB_TITLE.value: "Data Engineer",
        FactKey.ROLE_EMPLOYMENT_TYPE.value: "Vollzeit",
        FactKey.ROLE_CONTRACT_TYPE.value: "Unbefristet",
        FactKey.ROLE_SENIORITY_LEVEL.value: "Senior",
        FactKey.ROLE_JOB_REF_NUMBER.value: "REF-123",
        FactKey.ROLE_ROLE_OVERVIEW.value: "Build reliable data products",
        FactKey.ROLE_RESPONSIBILITIES.value: ["Build pipelines"],
        FactKey.ROLE_DELIVERABLES.value: ["Data marts"],
        FactKey.ROLE_SUCCESS_METRICS.value: ["Reliable reporting"],
        FactKey.ROLE_TECH_STACK.value: ["Python"],
        FactKey.ROLE_DOMAIN_EXPERTISE.value: ["Retail"],
        FactKey.ROLE_TRAVEL_REQUIRED.value: "Ja",
        FactKey.ROLE_ON_CALL.value: "Nein",
        FactKey.ROLE_ONBOARDING_NOTES.value: "Buddy program",
        FactKey.ROLE_GAPS.value: ["Budget klaeren"],
        FactKey.ROLE_ASSUMPTIONS.value: ["Hybrid possible"],
        FactKey.SKILLS_MUST_HAVE_SKILLS.value: ["Python"],
        FactKey.SKILLS_NICE_TO_HAVE_SKILLS.value: ["Airflow"],
        FactKey.SKILLS_SOFT_SKILLS.value: ["Kommunikation"],
        FactKey.SKILLS_EDUCATION.value: ["Bachelor"],
        FactKey.SKILLS_CERTIFICATIONS.value: ["AWS"],
        FactKey.SKILLS_LANGUAGES.value: ["Deutsch"],
        FactKey.INTERVIEW_START_DATE.value: "2026-07-01",
        FactKey.INTERVIEW_APPLICATION_DEADLINE.value: "2026-06-20",
        FactKey.BENEFITS_SALARY_RANGE.value: {
            "min": 60000.0,
            "max": 80000.0,
            "currency": "EUR",
            "period": "yearly",
        },
        FactKey.BENEFITS_BENEFITS.value: ["Remote work"],
        FactKey.INTERVIEW_RECRUITMENT_STEPS.value: [
            {"name": "Phone screen", "details": "30 minutes"}
        ],
        FactKey.INTERVIEW_CONTACTS.value: [
            {"name": "Hiring Team", "role": "Recruiting"}
        ],
    }


def test_empty_write_through_values_are_not_meaningful_facts() -> None:
    session_state = {
        SSKey.INTAKE_FACTS.value: {
            FactKey.COMPANY_COMPANY_NAME.value: "Acme GmbH",
            FactKey.SKILLS_MUST_HAVE_SKILLS.value: ["Python"],
            FactKey.BENEFITS_SALARY_RANGE.value: {"min": 60000, "max": 80000},
            FactKey.BENEFITS_BENEFITS.value: ["Remote work"],
            FactKey.INTERVIEW_RECRUITMENT_STEPS.value: [{"name": "Phone screen"}],
            FactKey.INTERVIEW_CONTACTS.value: [{"name": "Hiring Team"}],
        }
    }

    write_intake_fact_by_legacy_field(session_state, "company_name", " ")
    write_intake_fact_by_legacy_field(session_state, "must_have_skills", [" "])
    write_intake_fact_by_legacy_field(session_state, "job_title", "")
    write_intake_fact_by_legacy_field(session_state, "salary_range", {})
    write_intake_fact_by_legacy_field(session_state, "benefits", [" "])
    write_intake_fact_by_legacy_field(
        session_state,
        "recruitment_steps",
        [{"name": "", "details": None}],
    )
    write_intake_fact_by_legacy_field(
        session_state,
        "contacts",
        [{"name": "", "role": None}],
    )

    assert session_state[SSKey.INTAKE_FACTS.value] == {}


def test_sync_selected_skill_intake_facts_preserves_legacy_skill_state() -> None:
    session_state = {
        SSKey.SKILLS_SELECTED.value: ["Python", "SQL", "Go"],
        SSKey.SKILLS_SELECTED_STATUS.value: {
            "label:python": {"label": "Python", "status": "must"},
            "label:sql": {"label": "SQL", "status": "nice"},
            "label:go": {"label": "Go", "status": "ignored"},
        },
        SSKey.INTAKE_FACTS.value: {},
    }

    sync_selected_skill_intake_facts(session_state)

    assert session_state[SSKey.SKILLS_SELECTED.value] == ["Python", "SQL", "Go"]
    assert session_state[SSKey.SKILLS_SELECTED_STATUS.value]["label:python"] == {
        "label": "Python",
        "status": "must",
    }
    assert session_state[SSKey.INTAKE_FACTS.value] == {
        FactKey.SKILLS_MUST_HAVE_SKILLS.value: ["Python"],
        FactKey.SKILLS_NICE_TO_HAVE_SKILLS.value: ["SQL"],
    }


def test_state_set_answer_writes_through_supported_fact_and_legacy_answer(
    monkeypatch,
) -> None:
    fake_session_state = {
        SSKey.ANSWERS.value: {},
        SSKey.INTAKE_FACTS.value: {},
        SSKey.QUESTION_PLAN.value: {
            "steps": [
                {
                    "questions": [
                        {
                            "id": "ctx_tech_stack_must",
                            "fact_key": FactKey.ROLE_TECH_STACK.value,
                        }
                    ]
                }
            ]
        },
    }
    monkeypatch.setattr(
        state,
        "st",
        SimpleNamespace(session_state=fake_session_state),
    )

    state.set_answer("job_title", " Data Engineer ")
    state.set_answer("travel_required", False)
    state.set_answer("ctx_tech_stack_must", [" Python "])
    state.set_answer("unmapped_question", "kept legacy-only")

    assert fake_session_state[SSKey.ANSWERS.value] == {
        "job_title": " Data Engineer ",
        "travel_required": False,
        "ctx_tech_stack_must": [" Python "],
        "unmapped_question": "kept legacy-only",
    }
    assert fake_session_state[SSKey.INTAKE_FACTS.value] == {
        FactKey.ROLE_JOB_TITLE.value: "Data Engineer",
        FactKey.ROLE_TRAVEL_REQUIRED.value: False,
        FactKey.ROLE_TECH_STACK.value: ["Python"],
    }


def test_write_intake_fact_writes_manual_evidence_by_default() -> None:
    session_state = {SSKey.INTAKE_FACTS.value: {}, SSKey.INTAKE_FACT_EVIDENCE.value: {}}

    write_intake_fact(session_state, FactKey.ROLE_JOB_TITLE, " Data Engineer ")

    assert session_state[SSKey.INTAKE_FACTS.value] == {
        FactKey.ROLE_JOB_TITLE.value: "Data Engineer"
    }
    evidence = session_state[SSKey.INTAKE_FACT_EVIDENCE.value][
        FactKey.ROLE_JOB_TITLE.value
    ]
    assert evidence["source_type"] == FactSourceType.MANUAL.value
    assert evidence["source_label"] == "Manual input"
    assert evidence["confidence"] == 1.0
    assert evidence["confirmed"] is True
    assert evidence["resolution_status"] == FactResolutionStatus.CONFIRMED.value
    assert evidence["sensitivity"] == FactSensitivity.NORMAL.value
    assert evidence["evidence_snippet"] is None
    assert evidence["used_by_artifacts"] == []
    assert isinstance(evidence["updated_at"], str)


def test_write_intake_fact_accepts_new_routing_and_object_facts() -> None:
    session_state = {SSKey.INTAKE_FACTS.value: {}, SSKey.INTAKE_FACT_EVIDENCE.value: {}}

    write_intake_fact(session_state, FactKey.INTAKE_URGENCY, " high ")
    write_intake_fact(
        session_state,
        FactKey.BENEFITS_VARIABLE_PAY,
        {"eligible": True, "bonus_logic": "10% target bonus"},
    )

    assert session_state[SSKey.INTAKE_FACTS.value] == {
        FactKey.INTAKE_URGENCY.value: "high",
        FactKey.BENEFITS_VARIABLE_PAY.value: {
            "eligible": True,
            "bonus_logic": "10% target bonus",
        },
    }
    assert (
        session_state[SSKey.INTAKE_FACT_EVIDENCE.value][
            FactKey.BENEFITS_VARIABLE_PAY.value
        ]["resolution_status"]
        == FactResolutionStatus.CONFIRMED.value
    )


def test_write_job_extract_intake_facts_writes_jobspec_evidence() -> None:
    session_state = {SSKey.INTAKE_FACTS.value: {}, SSKey.INTAKE_FACT_EVIDENCE.value: {}}
    job = JobAdExtract(job_title="Data Engineer")

    write_job_extract_intake_facts(session_state, job)

    evidence = session_state[SSKey.INTAKE_FACT_EVIDENCE.value][
        FactKey.ROLE_JOB_TITLE.value
    ]
    assert evidence["source_type"] == FactSourceType.JOBSPEC.value
    assert evidence["source_label"] == "Jobspec extraction"
    assert evidence["confidence"] == 0.75
    assert evidence["confirmed"] is False
    assert evidence["resolution_status"] == FactResolutionStatus.INFERRED.value
    assert evidence["sensitivity"] == FactSensitivity.NORMAL.value
    assert evidence["used_by_artifacts"] == []


def test_write_job_extract_intake_facts_uses_field_level_evidence() -> None:
    session_state = {SSKey.INTAKE_FACTS.value: {}, SSKey.INTAKE_FACT_EVIDENCE.value: {}}
    job = JobAdExtract(
        job_title="Data Engineer",
        field_evidence=[
            JobAdFieldEvidence(
                field_name="job_title",
                confidence=0.62,
                evidence_snippet="Senior Data Engineer fuer die Plattform gesucht",
                needs_confirmation=True,
            )
        ],
    )

    write_job_extract_intake_facts(session_state, job)

    evidence = session_state[SSKey.INTAKE_FACT_EVIDENCE.value][
        FactKey.ROLE_JOB_TITLE.value
    ]
    assert evidence["source_type"] == FactSourceType.JOBSPEC.value
    assert evidence["confidence"] == 0.62
    assert evidence["confirmed"] is False
    assert evidence["evidence_snippet"] == (
        "Senior Data Engineer fuer die Plattform gesucht"
    )


def test_empty_write_clears_fact_and_evidence() -> None:
    session_state = {SSKey.INTAKE_FACTS.value: {}, SSKey.INTAKE_FACT_EVIDENCE.value: {}}
    write_intake_fact(session_state, FactKey.ROLE_JOB_TITLE, "Data Engineer")

    write_intake_fact(session_state, FactKey.ROLE_JOB_TITLE, " ")

    assert session_state[SSKey.INTAKE_FACTS.value] == {}
    assert session_state[SSKey.INTAKE_FACT_EVIDENCE.value] == {}


def test_manual_fact_writes_record_lifecycle_events_without_values() -> None:
    session_state = {SSKey.INTAKE_FACTS.value: {}, SSKey.INTAKE_FACT_EVIDENCE.value: {}}

    write_intake_fact(session_state, FactKey.ROLE_JOB_TITLE, "Data Engineer")
    write_intake_fact(session_state, FactKey.ROLE_JOB_TITLE, "Analytics Engineer")
    write_intake_fact(session_state, FactKey.ROLE_JOB_TITLE, " ")

    events = get_usage_events(session_state)
    assert [event["event_type"] for event in events] == [
        "fact_confirmed",
        "fact_corrected",
        "fact_rejected",
    ]
    assert [event["metadata"] for event in events] == [
        {"fact_key": FactKey.ROLE_JOB_TITLE.value, "source_type": "manual"},
        {"fact_key": FactKey.ROLE_JOB_TITLE.value, "source_type": "manual"},
        {"fact_key": FactKey.ROLE_JOB_TITLE.value, "source_type": "manual"},
    ]


def test_jobspec_fact_writes_do_not_record_manual_lifecycle_events() -> None:
    session_state = {SSKey.INTAKE_FACTS.value: {}, SSKey.INTAKE_FACT_EVIDENCE.value: {}}

    write_intake_fact(
        session_state,
        FactKey.ROLE_JOB_TITLE,
        "Data Engineer",
        source_type=FactSourceType.JOBSPEC,
    )

    assert get_usage_events(session_state) == []


def test_manual_confirmation_of_existing_extracted_fact_records_confirmation() -> None:
    session_state = {SSKey.INTAKE_FACTS.value: {}, SSKey.INTAKE_FACT_EVIDENCE.value: {}}
    write_intake_fact(
        session_state,
        FactKey.ROLE_JOB_TITLE,
        "Data Engineer",
        source_type=FactSourceType.JOBSPEC,
    )

    write_intake_fact(session_state, FactKey.ROLE_JOB_TITLE, "Data Engineer")

    events = get_usage_events(session_state)
    assert [event["event_type"] for event in events] == ["fact_confirmed"]
    assert events[0]["metadata"] == {
        "fact_key": FactKey.ROLE_JOB_TITLE.value,
        "source_type": "manual",
    }


def test_write_intake_fact_evidence_clamps_confidence_and_latest_lookup() -> None:
    session_state = {SSKey.INTAKE_FACT_EVIDENCE.value: {}}

    write_intake_fact_evidence(
        session_state,
        FactKey.ROLE_JOB_TITLE,
        source_type="llm",
        source_label="Extraction model",
        confidence=2.5,
        evidence_snippet="Senior Data Engineer gesucht",
        updated_at="2026-06-09T12:00:00+00:00",
    )

    evidence = session_state[SSKey.INTAKE_FACT_EVIDENCE.value][
        FactKey.ROLE_JOB_TITLE.value
    ]
    assert evidence == {
        "source_type": "llm",
        "source_label": "Extraction model",
        "confidence": 1.0,
        "confirmed": False,
        "resolution_status": FactResolutionStatus.INFERRED.value,
        "sensitivity": "normal",
        "evidence_snippet": "Senior Data Engineer gesucht",
        "used_by_artifacts": [],
        "updated_at": "2026-06-09T12:00:00+00:00",
    }
    assert latest_fact_confidence(
        FactKey.ROLE_JOB_TITLE,
        session_state[SSKey.INTAKE_FACT_EVIDENCE.value],
    ) == 1.0


def test_write_intake_fact_evidence_uses_source_default_for_invalid_confidence() -> None:
    session_state = {SSKey.INTAKE_FACT_EVIDENCE.value: {}}

    write_intake_fact_evidence(
        session_state,
        FactKey.ROLE_JOB_TITLE,
        source_type=FactSourceType.JOBSPEC,
        confidence="not-a-number",  # type: ignore[arg-type]
    )

    evidence = session_state[SSKey.INTAKE_FACT_EVIDENCE.value][
        FactKey.ROLE_JOB_TITLE.value
    ]
    assert evidence["confidence"] == 0.75


def test_write_intake_fact_accepts_explicit_resolution_status() -> None:
    session_state = {SSKey.INTAKE_FACTS.value: {}, SSKey.INTAKE_FACT_EVIDENCE.value: {}}

    write_intake_fact(
        session_state,
        FactKey.ROLE_JOB_TITLE,
        "Engineer",
        source_type=FactSourceType.JOBSPEC,
        resolution_status=FactResolutionStatus.CONFLICTED,
    )

    evidence = session_state[SSKey.INTAKE_FACT_EVIDENCE.value][
        FactKey.ROLE_JOB_TITLE.value
    ]
    assert evidence["resolution_status"] == FactResolutionStatus.CONFLICTED.value


def test_build_intake_fact_resolution_state_includes_missing_and_present_facts() -> None:
    session_state = {SSKey.INTAKE_FACTS.value: {}, SSKey.INTAKE_FACT_EVIDENCE.value: {}}
    write_intake_fact(
        session_state,
        FactKey.ROLE_JOB_TITLE,
        "Engineer",
        source_type=FactSourceType.MANUAL,
        updated_at="2026-06-10T00:00:00+00:00",
    )

    resolution_state = build_intake_fact_resolution_state(
        session_state,
        fact_keys=[FactKey.ROLE_JOB_TITLE, FactKey.COMPANY_COMPANY_NAME],
    )

    assert resolution_state[FactKey.ROLE_JOB_TITLE.value]["status"] == (
        FactResolutionStatus.CONFIRMED.value
    )
    assert resolution_state[FactKey.ROLE_JOB_TITLE.value]["value"] == "Engineer"
    assert resolution_state[FactKey.COMPANY_COMPANY_NAME.value] == {
        "status": FactResolutionStatus.MISSING.value
    }


def test_write_intake_fact_evidence_redacts_snippet_before_storage() -> None:
    session_state = {SSKey.INTAKE_FACT_EVIDENCE.value: {}}

    write_intake_fact_evidence(
        session_state,
        FactKey.INTERVIEW_CONTACTS,
        source_type=FactSourceType.LLM,
        evidence_snippet=(
            "Kontakt: recruiting@example.com oder +49 30 12345678 fuer Rueckfragen."
        ),
    )

    snippet = session_state[SSKey.INTAKE_FACT_EVIDENCE.value][
        FactKey.INTERVIEW_CONTACTS.value
    ]["evidence_snippet"]
    assert "recruiting@example.com" not in snippet
    assert "+49 30 12345678" not in snippet
    assert snippet == "Kontakt: [REDACTED] oder [REDACTED] fuer Rueckfragen."


def test_write_intake_fact_evidence_stores_sensitivity_and_artifact_usage() -> None:
    session_state = {SSKey.INTAKE_FACT_EVIDENCE.value: {}}

    write_intake_fact_evidence(
        session_state,
        FactKey.BENEFITS_SALARY_RANGE,
        source_type=FactSourceType.HOMEPAGE,
        confirmed=True,
        used_by_artifacts=[
            "brief",
            "job_ad",
            "invalid",
            "brief",
            "employment_contract",
        ],
    )
    write_intake_fact_evidence(
        session_state,
        FactKey.INTERVIEW_CONTACTS,
        source_type=FactSourceType.MANUAL,
        sensitivity=FactSensitivity.PERSONAL,
    )

    salary_evidence = session_state[SSKey.INTAKE_FACT_EVIDENCE.value][
        FactKey.BENEFITS_SALARY_RANGE.value
    ]
    assert salary_evidence["confirmed"] is True
    assert salary_evidence["sensitivity"] == FactSensitivity.RESTRICTED.value
    assert salary_evidence["used_by_artifacts"] == [
        "brief",
        "job_ad",
        "employment_contract",
    ]
    contacts_evidence = session_state[SSKey.INTAKE_FACT_EVIDENCE.value][
        FactKey.INTERVIEW_CONTACTS.value
    ]
    assert contacts_evidence["confirmed"] is True
    assert contacts_evidence["sensitivity"] == FactSensitivity.PERSONAL.value


def test_mark_intake_facts_used_by_artifact_updates_existing_evidence_rows() -> None:
    session_state = {
        SSKey.INTAKE_FACT_EVIDENCE.value: {
            FactKey.ROLE_JOB_TITLE.value: {
                "source_type": "manual",
                "used_by_artifacts": ["brief"],
                "updated_at": "old",
            },
            FactKey.COMPANY_COMPANY_NAME.value: {
                "source_type": "jobspec",
                "used_by_artifacts": [],
                "updated_at": "old",
            },
        }
    }

    mark_intake_facts_used_by_artifact(
        session_state,
        "job_ad",
        updated_at="2026-06-10T10:00:00+00:00",
    )

    evidence = session_state[SSKey.INTAKE_FACT_EVIDENCE.value]
    assert evidence[FactKey.ROLE_JOB_TITLE.value]["used_by_artifacts"] == [
        "brief",
        "job_ad",
    ]
    assert evidence[FactKey.COMPANY_COMPANY_NAME.value]["used_by_artifacts"] == [
        "job_ad"
    ]
    assert (
        evidence[FactKey.ROLE_JOB_TITLE.value]["updated_at"]
        == "2026-06-10T10:00:00+00:00"
    )


def test_mark_intake_facts_used_by_artifact_can_target_selected_facts() -> None:
    session_state = {
        SSKey.INTAKE_FACT_EVIDENCE.value: {
            FactKey.ROLE_JOB_TITLE.value: {
                "source_type": "manual",
                "used_by_artifacts": [],
                "updated_at": "old",
            },
            FactKey.COMPANY_COMPANY_NAME.value: {
                "source_type": "jobspec",
                "used_by_artifacts": [],
                "updated_at": "old",
            },
        }
    }

    mark_intake_facts_used_by_artifact(
        session_state,
        "invalid",
        fact_keys=[FactKey.ROLE_JOB_TITLE],
        updated_at="ignored",
    )
    mark_intake_facts_used_by_artifact(
        session_state,
        "brief",
        fact_keys=[FactKey.ROLE_JOB_TITLE, "not.a.fact"],
        updated_at="2026-06-10T10:00:00+00:00",
    )

    evidence = session_state[SSKey.INTAKE_FACT_EVIDENCE.value]
    assert evidence[FactKey.ROLE_JOB_TITLE.value]["used_by_artifacts"] == ["brief"]
    assert evidence[FactKey.COMPANY_COMPANY_NAME.value]["used_by_artifacts"] == []
