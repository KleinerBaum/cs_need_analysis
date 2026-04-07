# schemas.py

"""Pydantic models used for Structured Outputs and internal state.

These models are used in two ways:
1) As the JSON schema contract with the OpenAI API (Structured Outputs).
2) As the app's internal data model (stored as dicts in st.session_state).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from constants import AnswerType, QUESTION_SCHEMA_VERSION, VACANCY_SCHEMA_VERSION


class MoneyRange(BaseModel):
    min: Optional[float] = Field(default=None, description="Minimum salary/compensation (numeric).")
    max: Optional[float] = Field(default=None, description="Maximum salary/compensation (numeric).")
    currency: Optional[str] = Field(default=None, description="ISO currency code or free-form like 'EUR'.")
    period: Optional[str] = Field(default=None, description="e.g., yearly, monthly, hourly.")
    notes: Optional[str] = Field(default=None, description="Any caveats (e.g., depends on experience).")


class Contact(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class RecruitmentStep(BaseModel):
    name: str = Field(description="Short step name, e.g., 'Phone screen', 'Technical interview'.")
    details: Optional[str] = Field(default=None, description="Optional details like duration, format, who participates.")


class JobAdExtract(BaseModel):
    """Normalized extraction from a jobspec/job ad."""

    schema_version: str = Field(default=VACANCY_SCHEMA_VERSION)

    language_guess: Optional[str] = Field(default=None, description="Detected language of input, e.g., 'de' or 'en'.")
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    brand_name: Optional[str] = None

    location_city: Optional[str] = None
    location_country: Optional[str] = None
    place_of_work: Optional[str] = None
    remote_policy: Optional[str] = None

    employment_type: Optional[str] = None  # full-time, part-time, etc.
    contract_type: Optional[str] = None  # permanent, temporary, etc.
    seniority_level: Optional[str] = None

    start_date: Optional[str] = Field(default=None, description="Start date if present (keep as string).")
    application_deadline: Optional[str] = Field(default=None, description="Application deadline if present (keep as string).")
    job_ref_number: Optional[str] = None

    department_name: Optional[str] = None
    reports_to: Optional[str] = None
    direct_reports_count: Optional[int] = None

    role_overview: Optional[str] = None
    responsibilities: List[str] = Field(default_factory=list)
    deliverables: List[str] = Field(default_factory=list)
    success_metrics: List[str] = Field(default_factory=list)

    must_have_skills: List[str] = Field(default_factory=list)
    nice_to_have_skills: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)
    education: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)

    tech_stack: List[str] = Field(default_factory=list)
    domain_expertise: List[str] = Field(default_factory=list)

    travel_required: Optional[str] = None
    on_call: Optional[str] = None

    salary_range: Optional[MoneyRange] = None
    benefits: List[str] = Field(default_factory=list)

    recruitment_steps: List[RecruitmentStep] = Field(default_factory=list)
    onboarding_notes: Optional[str] = None

    contacts: List[Contact] = Field(default_factory=list)

    gaps: List[str] = Field(
        default_factory=list,
        description="List of missing or unclear items that should be clarified with the hiring manager.",
    )
    assumptions: List[str] = Field(
        default_factory=list,
        description="If the model inferred something, list assumptions explicitly here.",
    )


class Question(BaseModel):
    id: str = Field(description="Stable unique question id (machine-readable).")
    label: str = Field(description="Exact question text shown to the user.")
    help: Optional[str] = Field(default=None, description="Helper text / tooltip.")
    answer_type: AnswerType = Field(description="Widget/answer type.")
    required: bool = Field(default=False)
    options: Optional[List[str]] = Field(default=None, description="Options for select widgets.")
    default: Optional[
        Union[str, int, float, bool, List[str], List[int], List[float], List[bool]]
    ] = Field(default=None, description="Default value if applicable.")
    target_path: Optional[str] = Field(
        default=None,
        description="Optional dot-path into the final vacancy brief structure; can be used for mapping.",
    )
    rationale: Optional[str] = Field(
        default=None,
        description="Why this question matters (used in debug/UI).",
    )


class QuestionStep(BaseModel):
    step_key: str = Field(description="One of the wizard step keys, e.g. 'team' or 'skills'.")
    title_de: str
    description_de: Optional[str] = None
    questions: List[Question] = Field(default_factory=list)


class QuestionPlan(BaseModel):
    schema_version: str = Field(default=QUESTION_SCHEMA_VERSION)
    language: str = Field(default="de")
    steps: List[QuestionStep] = Field(default_factory=list)


class VacancyBrief(BaseModel):
    """Final structured output for recruiters / ATS / stakeholder alignment."""

    schema_version: str = Field(default=VACANCY_SCHEMA_VERSION)
    language: str = Field(default="de")

    one_liner: str = Field(description="One-sentence role pitch.")
    hiring_context: str = Field(description="Why do we hire now, impact, urgency, business context.")
    role_summary: str = Field(description="Manager-ready role summary.")
    top_responsibilities: List[str] = Field(default_factory=list)
    must_have: List[str] = Field(default_factory=list)
    nice_to_have: List[str] = Field(default_factory=list)
    dealbreakers: List[str] = Field(default_factory=list)

    interview_plan: List[str] = Field(default_factory=list)
    evaluation_rubric: List[str] = Field(default_factory=list, description="Bullet rubric: what to test and how.")
    sourcing_channels: List[str] = Field(default_factory=list, description="Suggested channels based on role.")
    risks_open_questions: List[str] = Field(default_factory=list, description="Remaining unknowns / risks.")

    job_ad_draft: str = Field(description="A publishable job ad draft (German).")
    structured_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Machine-readable full data (job extract + manager answers).",
    )
