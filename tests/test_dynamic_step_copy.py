from __future__ import annotations

from constants import (
    FactKey,
    SSKey,
    STEP_KEY_BENEFITS,
    STEP_KEY_COMPANY,
    STEP_KEY_INTERVIEW,
    STEP_KEY_ROLE_TASKS,
    STEP_KEY_SKILLS,
    STEP_KEY_SUMMARY,
)
from schemas import JobAdExtract
from wizard_pages.base import resolve_dynamic_step_copy


ACTIVE_DYNAMIC_STEP_KEYS = (
    STEP_KEY_COMPANY,
    STEP_KEY_ROLE_TASKS,
    STEP_KEY_SKILLS,
    STEP_KEY_BENEFITS,
    STEP_KEY_INTERVIEW,
    STEP_KEY_SUMMARY,
)


def _session_state(**extra: object) -> dict[str, object]:
    state: dict[str, object] = {
        SSKey.ANSWERS.value: {},
        SSKey.INTAKE_FACTS.value: {},
        SSKey.JOB_EXTRACT.value: {},
    }
    state.update(extra)
    return state


def test_dynamic_step_copy_personalizes_active_route_in_german() -> None:
    job = JobAdExtract(job_title="Data Engineer", company_name="ACME")
    state = _session_state(
        **{
            SSKey.ANSWERS.value: {
                FactKey.ROLE_JOB_TITLE.value: "Analytics Lead",
            },
            SSKey.INTAKE_FACTS.value: {
                FactKey.COMPANY_COMPANY_NAME.value: "Example GmbH",
            },
        }
    )

    company = resolve_dynamic_step_copy(
        STEP_KEY_COMPANY,
        job=job,
        language="de",
        session_state=state,
    )
    role_tasks = resolve_dynamic_step_copy(
        STEP_KEY_ROLE_TASKS,
        job=job,
        language="de",
        session_state=state,
    )
    benefits = resolve_dynamic_step_copy(
        STEP_KEY_BENEFITS,
        job=job,
        language="de",
        session_state=state,
    )
    interview = resolve_dynamic_step_copy(
        STEP_KEY_INTERVIEW,
        job=job,
        language="de",
        session_state=state,
    )

    assert company.headline == "Example GmbH als Arbeitgeber für Analytics Lead einordnen"
    assert role_tasks.headline == "Klären, wofür Analytics Lead wirklich verantwortlich ist"
    assert benefits.headline == (
        "Das Angebot für Analytics Lead klar und überzeugend formulieren"
    )
    assert interview.headline == "Einen fairen Interviewprozess für Analytics Lead planen"
    assert all(
        copy.value_line
        for copy in (company, role_tasks, benefits, interview)
    )


def test_dynamic_step_copy_keeps_english_parity_and_summary_readiness() -> None:
    job = JobAdExtract(job_title="Product Manager", company_name="ACME")
    state = _session_state()

    company = resolve_dynamic_step_copy(
        STEP_KEY_COMPANY,
        job=job,
        language="en",
        session_state=state,
    )
    summary_gap = resolve_dynamic_step_copy(
        STEP_KEY_SUMMARY,
        job=job,
        language="en",
        readiness_score=86,
        critical_gaps_count=2,
        session_state=state,
    )
    summary_ready = resolve_dynamic_step_copy(
        STEP_KEY_SUMMARY,
        job=job,
        language="en",
        readiness_score=100,
        critical_gaps_count=0,
        session_state=state,
    )

    assert company.headline == "Position ACME as the employer for Product Manager"
    assert company.subheadline.startswith("Clarify company context")
    assert company.value_line == "Helps explain why this role exists."
    assert summary_gap.headline == "2 critical points still open"
    assert summary_ready.headline == "Ready for recruiting, interviews, and active sourcing"


def test_dynamic_step_copy_falls_back_without_context() -> None:
    state = _session_state()

    for step_key in ACTIVE_DYNAMIC_STEP_KEYS:
        copy = resolve_dynamic_step_copy(
            step_key,
            language="de",
            session_state=state,
        )

        assert copy.headline
        assert copy.subheadline
        assert copy.value_line
        assert "{" not in copy.headline
        assert "}" not in copy.headline


def test_dynamic_step_copy_covers_short_predictable_active_step_copy() -> None:
    state = _session_state()

    for step_key in ACTIVE_DYNAMIC_STEP_KEYS:
        copy = resolve_dynamic_step_copy(
            step_key,
            language="en",
            session_state=state,
        )

        assert len(copy.headline) <= 90
        assert len(copy.value_line) <= 90
