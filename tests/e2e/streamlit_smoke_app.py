from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import app as real_app  # noqa: E402
from constants import JOBSPEC_SOURCE_MANUAL, SSKey  # noqa: E402
from llm_client import JobAdGenerationResult  # noqa: E402
from schemas import JobAdExtract, QuestionPlan, VacancyBrief, VacancyStructuredData  # noqa: E402
from state import build_jobspec_source_fingerprint  # noqa: E402

_ORIGINAL_INIT_SESSION_STATE = real_app.init_session_state


def _first_query_param_value(name: str) -> str | None:
    value = st.query_params.get(name)
    if isinstance(value, list):
        value = value[0] if value else None
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _should_seed_summary_artifact() -> bool:
    return (
        os.getenv("CS_E2E_TEST_MODE") == "1"
        and _first_query_param_value("e2e_seed") == "summary_artifact"
    )


def _seed_summary_artifact_state() -> None:
    source_text = (
        "Synthetic vacancy for a Data Engineer in Berlin. "
        "Responsibilities include data pipelines, analytics modeling, and stakeholder reporting. "
        "Required skills are Python, SQL, and cloud data tooling."
    )
    job = JobAdExtract(
        language_guess="de",
        job_title="Synthetic Data Engineer",
        company_name="Example Labs GmbH",
        location_city="Berlin",
        location_country="Deutschland",
        remote_policy="Hybrid",
        employment_type="Vollzeit",
        contract_type="Unbefristet",
        seniority_level="Senior",
        role_overview="Build and maintain synthetic analytics pipelines.",
        responsibilities=[
            "Design synthetic data pipelines",
            "Maintain analytics models",
            "Coordinate reporting requirements",
        ],
        must_have_skills=["Python", "SQL", "Cloud data tooling"],
        nice_to_have_skills=["Data quality automation"],
        benefits=["Hybrid work", "Learning budget"],
    )
    job_payload = job.model_dump(mode="json")
    plan_payload = QuestionPlan.model_validate({"steps": []}).model_dump(mode="json")
    brief = VacancyBrief(
        one_liner="Synthetic Data Engineer role for deterministic browser smoke tests.",
        hiring_context="Synthetic context used only for e2e smoke coverage.",
        role_summary="Own synthetic data pipelines and analytics reporting.",
        top_responsibilities=job.responsibilities,
        must_have=job.must_have_skills,
        nice_to_have=job.nice_to_have_skills,
        interview_plan=["Synthetic technical interview"],
        evaluation_rubric=["Assess Python, SQL, and data modeling depth."],
        risks_open_questions=["Confirm final team setup."],
        job_ad_draft="Synthetic job ad draft for browser smoke tests.",
        structured_data=VacancyStructuredData(job_extract=job_payload, answers={}),
    )
    job_ad = JobAdGenerationResult(
        headline="Synthetic Data Engineer",
        target_group=["Synthetic engineering candidates"],
        agg_checklist=["Synthetic inclusive-language review passed."],
        job_ad_text=(
            "Synthetic Data Engineer\n\n"
            "Build synthetic data pipelines with Python and SQL.\n\n"
            "This fixture is deterministic and contains no real customer data."
        ),
        intro="Join a synthetic data team for deterministic browser testing.",
        responsibilities=job.responsibilities,
        profile=job.must_have_skills,
        offer=job.benefits,
        cta="Apply through the synthetic test channel.",
        equal_opportunity_note="Synthetic equal opportunity note.",
    )

    st.session_state[SSKey.SOURCE_TEXT.value] = source_text
    st.session_state[SSKey.SOURCE_MANUAL_TEXT.value] = source_text
    st.session_state[SSKey.SOURCE_ACTIVE.value] = JOBSPEC_SOURCE_MANUAL
    st.session_state[SSKey.SOURCE_ACTIVE_FINGERPRINT.value] = (
        build_jobspec_source_fingerprint(JOBSPEC_SOURCE_MANUAL, source_text)
    )
    st.session_state[SSKey.JOB_EXTRACT.value] = job_payload
    st.session_state[SSKey.QUESTION_PLAN_BASE.value] = plan_payload
    st.session_state[SSKey.QUESTION_PLAN.value] = plan_payload
    st.session_state[SSKey.ANSWERS.value] = {}
    st.session_state[SSKey.BRIEF.value] = brief.model_dump(mode="json")
    st.session_state[SSKey.JOB_AD_DRAFT_CUSTOM.value] = job_ad.model_dump(mode="json")
    st.session_state[SSKey.SUMMARY_ACTIVE_ARTIFACT.value] = "job_ad"
    st.session_state[SSKey.SUMMARY_LAST_MODE.value] = "e2e_seed"
    st.session_state[SSKey.SUMMARY_LAST_MODELS.value] = {
        "draft_model": "e2e-synthetic-model"
    }


def _init_session_state_for_e2e() -> None:
    _ORIGINAL_INIT_SESSION_STATE()
    if _should_seed_summary_artifact():
        _seed_summary_artifact_state()


real_app.init_session_state = _init_session_state_for_e2e
real_app.main()
