from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from constants import JOBSPEC_SOURCE_MANUAL, SSKey
from schemas import JobAdExtract, QuestionPlan, VacancyBrief, VacancyStructuredData
from state import build_jobspec_source_fingerprint

SYNTHETIC_SUMMARY_SEED_QUERY_VALUE = "summary_artifact"
SYNTHETIC_JOB_TITLE = "Synthetic Data Engineer"
SYNTHETIC_JOB_AD_MARKDOWN_FRAGMENT = "contains only synthetic placeholder data"
SYNTHETIC_NO_AI_MODEL_LABEL = "synthetic-no-ai-model"


def build_summary_artifact_smoke_state(
    *, last_mode: str = "smoke_seed"
) -> dict[str, Any]:
    source_text = (
        "Synthetic vacancy for a Data Engineer in Berlin. "
        "Responsibilities include data pipelines, analytics modeling, and "
        "stakeholder reporting. Required skills are Python, SQL, and cloud "
        "data tooling."
    )
    job = JobAdExtract(
        language_guess="de",
        job_title=SYNTHETIC_JOB_TITLE,
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
        one_liner="Synthetic Data Engineer role for deterministic smoke tests.",
        hiring_context="Synthetic context used only for smoke coverage.",
        role_summary="Own synthetic data pipelines and analytics reporting.",
        top_responsibilities=job.responsibilities,
        must_have=job.must_have_skills,
        nice_to_have=job.nice_to_have_skills,
        interview_plan=["Synthetic technical interview"],
        evaluation_rubric=["Assess Python, SQL, and data modeling depth."],
        risks_open_questions=["Confirm final team setup."],
        job_ad_draft="Synthetic job ad draft for smoke tests.",
        structured_data=VacancyStructuredData(job_extract=job_payload, answers={}),
    )
    job_ad_payload = {
        "headline": SYNTHETIC_JOB_TITLE,
        "target_group": ["Synthetic engineering candidates"],
        "agg_checklist": ["Synthetic inclusive-language review passed."],
        "job_ad_text": (
            "Synthetic Data Engineer\n\n"
            "Build synthetic data pipelines with Python and SQL.\n\n"
            "This fixture is deterministic and "
            f"{SYNTHETIC_JOB_AD_MARKDOWN_FRAGMENT}."
        ),
        "intro": "Join a synthetic data team for deterministic smoke testing.",
        "responsibilities": job.responsibilities,
        "profile": job.must_have_skills,
        "offer": job.benefits,
        "cta": "Apply through the synthetic test channel.",
        "equal_opportunity_note": "Synthetic equal opportunity note.",
    }

    return {
        SSKey.SOURCE_TEXT.value: source_text,
        SSKey.SOURCE_MANUAL_TEXT.value: source_text,
        SSKey.SOURCE_ACTIVE.value: JOBSPEC_SOURCE_MANUAL,
        SSKey.SOURCE_ACTIVE_FINGERPRINT.value: build_jobspec_source_fingerprint(
            JOBSPEC_SOURCE_MANUAL,
            source_text,
        ),
        SSKey.JOB_EXTRACT.value: job_payload,
        SSKey.QUESTION_PLAN_BASE.value: plan_payload,
        SSKey.QUESTION_PLAN.value: plan_payload,
        SSKey.ANSWERS.value: {},
        SSKey.BRIEF.value: brief.model_dump(mode="json"),
        SSKey.JOB_AD_DRAFT_CUSTOM.value: job_ad_payload,
        SSKey.SUMMARY_ACTIVE_ARTIFACT.value: "job_ad",
        SSKey.SUMMARY_LAST_MODE.value: last_mode,
        SSKey.SUMMARY_LAST_MODELS.value: {"draft_model": SYNTHETIC_NO_AI_MODEL_LABEL},
    }


def seed_summary_artifact_smoke_state(
    session_state: MutableMapping[str, Any],
    *,
    last_mode: str = "smoke_seed",
) -> None:
    for key, value in build_summary_artifact_smoke_state(last_mode=last_mode).items():
        session_state[key] = value
