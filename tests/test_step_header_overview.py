from __future__ import annotations

from constants import (
    ESCO_ANCHOR_STATE_ANCHORED,
    FactKey,
    SSKey,
    STEP_KEY_BENEFITS,
    STEP_KEY_COMPANY,
    STEP_KEY_INTERVIEW,
    STEP_KEY_ROLE_TASKS,
    STEP_KEY_SKILLS,
)
from schemas import JobAdExtract, MoneyRange, RecruitmentStep
from step_header_overview import (
    build_step_header_overview,
    build_summary_header_overview,
)


def _payload(job: JobAdExtract, facts: dict[str, object] | None = None) -> dict[str, object]:
    return {
        "job_extract": job,
        "intake_facts": facts or {},
        "section_statuses": [],
    }


def _all_item_text(overview: object) -> str:
    groups = getattr(overview, "groups")
    parts: list[str] = []
    for group in groups:
        parts.append(group.title)
        for item in group.items:
            parts.append(item.label)
            parts.append(item.value)
            parts.extend(item.items)
    return " | ".join(part for part in parts if part)


def test_company_header_overview_uses_employer_and_context_facts() -> None:
    overview = build_step_header_overview(
        step_key=STEP_KEY_COMPANY,
        step_payload=_payload(
            JobAdExtract(company_name="Acme Corp", location_city="Berlin"),
            {
                FactKey.COMPANY_WORK_ARRANGEMENT.value: "hybrid",
                FactKey.COMPANY_EMPLOYER_PITCH.value: "AI product company",
            },
        ),
        session_state={},
    )

    text = _all_item_text(overview)
    assert "Arbeitgeber" in text
    assert "Acme Corp" in text
    assert "Berlin" in text
    assert "hybrid" in text
    assert "AI product company" in text


def test_role_tasks_header_overview_groups_tasks_and_success_signals() -> None:
    overview = build_step_header_overview(
        step_key=STEP_KEY_ROLE_TASKS,
        step_payload=_payload(
            JobAdExtract(
                job_title="Senior Data Scientist",
                responsibilities=["Build models", "Ship model monitoring"],
                deliverables=["Forecasting pipeline"],
                success_metrics=["Accuracy uplift"],
                tech_stack=["Python"],
            )
        ),
        session_state={},
    )

    text = _all_item_text(overview)
    assert "Rolle" in text
    assert "Senior Data Scientist" in text
    assert "Build models" in text
    assert "Forecasting pipeline" in text
    assert "Accuracy uplift" in text
    assert "Python" in text


def test_skills_header_overview_prefers_selected_statuses_and_esco_anchor() -> None:
    overview = build_step_header_overview(
        step_key=STEP_KEY_SKILLS,
        step_payload=_payload(JobAdExtract(must_have_skills=["Fallback Skill"])),
        session_state={
            SSKey.SKILLS_SELECTED.value: ["Python", "Stakeholder management"],
            SSKey.SKILLS_SELECTED_STATUS.value: {
                "label:python": {"status": "must"},
                "label:stakeholder management": {"status": "nice"},
            },
            SSKey.ESCO_ANCHOR_STATE.value: ESCO_ANCHOR_STATE_ANCHORED,
            SSKey.ESCO_OCCUPATION_SELECTED.value: {"title": "Data scientist"},
            SSKey.ESCO_UNMAPPED_REQUIREMENT_TERMS.value: ["PySpark"],
        },
    )

    text = _all_item_text(overview)
    assert "Python" in text
    assert "Stakeholder management" in text
    assert "Data scientist" in text
    assert "PySpark" in text
    assert "Fallback Skill" not in text


def test_benefits_header_overview_formats_offer_components() -> None:
    overview = build_step_header_overview(
        step_key=STEP_KEY_BENEFITS,
        step_payload=_payload(
            JobAdExtract(
                salary_range=MoneyRange(min=80000, max=100000, currency="EUR", period="yearly"),
                benefits=["Health insurance"],
                remote_policy="remote-first",
            ),
            {
                FactKey.BENEFITS_VARIABLE_PAY.value: {"eligible": True},
                FactKey.TIMELINE_START_FLEXIBILITY.value: {
                    "target_start": "2026-09-01",
                    "flexibility": "flexible",
                },
            },
        ),
        session_state={SSKey.BENEFITS_SELECTED.value: ["401(k)", "Training budget"]},
    )

    text = _all_item_text(overview)
    assert "80000.0 - 100000.0 EUR year" in text
    assert "Vorgesehen" in text
    assert "401(k)" in text
    assert "Training budget" in text
    assert "remote-first" in text
    assert "2026-09-01 · flexible" in text


def test_interview_header_overview_avoids_contact_names() -> None:
    overview = build_step_header_overview(
        step_key=STEP_KEY_INTERVIEW,
        step_payload=_payload(
            JobAdExtract(
                recruitment_steps=[RecruitmentStep(name="Phone screen")],
            ),
            {
                FactKey.INTERVIEW_CONTACTS.value: [{"name": "Jane Doe", "role": "Recruiter"}],
                FactKey.INTERVIEW_STAGE_OWNERS.value: [
                    {"stage": "Phone screen", "owner": "Recruiter"}
                ],
                FactKey.INTERVIEW_CORE_QUESTIONS.value: ["Why this role?"],
            },
        ),
        session_state={},
    )

    text = _all_item_text(overview)
    assert "Phone screen" in text
    assert "1 hinterlegt" in text
    assert "1 Rollen geklärt" in text
    assert "Why this role?" in text
    assert "Jane Doe" not in text


def test_summary_header_overview_uses_readiness_and_artifact_state() -> None:
    overview = build_summary_header_overview(
        readiness_percent=82,
        completion_text="11/34 kritische Fakten geklärt",
        blocker_count=3,
        esco_ready=True,
        brief_state="current",
        brief_status_label="Aktueller Recruiting Brief vorhanden.",
        ready_for_follow_ups=False,
        session_state={
            SSKey.SUMMARY_ACTIVE_ARTIFACT.value: "job_ad",
            SSKey.BRIEF.value: {"one_liner": "Ready"},
            SSKey.BOOLEAN_SEARCH_STRING.value: "python AND data",
            SSKey.SUMMARY_ARTIFACT_LAST_ERROR.value: {"job_ad": "failed"},
        },
    )

    text = _all_item_text(overview)
    assert "82%" in text
    assert "3" in text
    assert "11/34 kritische Fakten geklärt" in text
    assert "Bestätigt" in text
    assert "job_ad" in text
    assert "2/5" in text
