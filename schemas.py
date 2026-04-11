# schemas.py

"""Pydantic models used for Structured Outputs and internal state.

These models are used in two ways:
1) As the JSON schema contract with the OpenAI API (Structured Outputs).
2) As the app's internal data model (stored as dicts in st.session_state).
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from constants import AnswerType, QUESTION_SCHEMA_VERSION, VACANCY_SCHEMA_VERSION


class StrictSchemaModel(BaseModel):
    """Strict model base for Structured Outputs compatibility."""

    model_config = ConfigDict(extra="forbid")


class MoneyRange(StrictSchemaModel):
    min: Optional[float] = Field(
        default=None, description="Minimum salary/compensation (numeric)."
    )
    max: Optional[float] = Field(
        default=None, description="Maximum salary/compensation (numeric)."
    )
    currency: Optional[str] = Field(
        default=None, description="ISO currency code or free-form like 'EUR'."
    )
    period: Optional[str] = Field(
        default=None, description="e.g., yearly, monthly, hourly."
    )
    notes: Optional[str] = Field(
        default=None, description="Any caveats (e.g., depends on experience)."
    )


class Contact(StrictSchemaModel):
    name: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class RecruitmentStep(StrictSchemaModel):
    name: str = Field(
        description="Short step name, e.g., 'Phone screen', 'Technical interview'."
    )
    details: Optional[str] = Field(
        default=None,
        description="Optional details like duration, format, who participates.",
    )


CEFRLevel = Literal["A1", "A2", "B1", "B2", "C1", "C2"]


class LanguageRequirement(StrictSchemaModel):
    language: str = Field(description="Language name, e.g., 'Deutsch' or 'Englisch'.")
    level: CEFRLevel = Field(description="Required CEFR level from A1 to C2.")


class EscoConceptRef(StrictSchemaModel):
    uri: str = Field(description="Canonical ESCO concept URI.")
    title: str = Field(description="Preferred ESCO label.")
    type: str = Field(description="ESCO concept type, e.g., 'occupation' or 'skill'.")
    code: Optional[str] = Field(
        default=None,
        description="Optional ESCO concept code.",
    )


class EscoSuggestionItem(StrictSchemaModel):
    uri: str = Field(description="Canonical ESCO concept URI.")
    title: str = Field(description="Preferred ESCO label.")
    type: str = Field(description="ESCO concept type, e.g., 'occupation' or 'skill'.")
    score: Optional[float] = Field(
        default=None,
        description="Optional suggestion confidence score.",
    )


class EscoMappingReport(StrictSchemaModel):
    mapped_count: int = Field(ge=0, description="Count of terms successfully mapped.")
    unmapped_terms: List[str] = Field(
        default_factory=list,
        description="Input terms that could not be mapped to ESCO concepts.",
    )
    collisions: List[str] = Field(
        default_factory=list,
        description="Terms that matched multiple candidate concepts.",
    )
    notes: List[str] = Field(
        default_factory=list,
        description="Additional normalization or mapping notes.",
    )


class EscoLinks(StrictSchemaModel):
    links: Dict[str, EscoConceptRef] = Field(
        default_factory=dict,
        description="Normalized ESCO _links payload by relation key.",
    )


class EscoBreadcrumbNode(StrictSchemaModel):
    uri: str = Field(description="Canonical ESCO concept URI.")
    title: str = Field(description="Preferred label for breadcrumb display.")
    type: Optional[str] = Field(
        default=None,
        description="Optional ESCO concept type.",
    )


class EscoSkillDetail(StrictSchemaModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    label: str = Field(description="Human-readable ESCO skill label.")
    description: Optional[str] = Field(
        default=None,
        description="Short ESCO skill description text if available.",
    )
    scope_note: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("scopeNote", "scope_note"),
        serialization_alias="scopeNote",
        description="Optional ESCO scope note.",
    )


class JobAdExtract(StrictSchemaModel):
    """Normalized extraction from a jobspec/job ad."""

    schema_version: str = Field(default=VACANCY_SCHEMA_VERSION)

    language_guess: Optional[str] = Field(
        default=None, description="Detected language of input, e.g., 'de' or 'en'."
    )
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

    start_date: Optional[str] = Field(
        default=None, description="Start date if present (keep as string)."
    )
    application_deadline: Optional[str] = Field(
        default=None, description="Application deadline if present (keep as string)."
    )
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


class RequirementSuggestionItem(StrictSchemaModel):
    label: str
    type: Literal["skill", "task"]
    source_hint: Literal["llm"]
    rationale: str
    evidence: str
    importance: Literal["high", "medium", "low"]


class RequirementSuggestionPack(StrictSchemaModel):
    skills: list[RequirementSuggestionItem] = Field(default_factory=list)
    tasks: list[RequirementSuggestionItem] = Field(default_factory=list)


class Question(StrictSchemaModel):
    id: str = Field(description="Stable unique question id (machine-readable).")
    label: str = Field(description="Exact question text shown to the user.")
    help: Optional[str] = Field(default=None, description="Helper text / tooltip.")
    answer_type: AnswerType = Field(description="Widget/answer type.")
    required: bool = Field(default=False)
    options: Optional[List[str]] = Field(
        default=None, description="Options for select widgets."
    )
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
    min_value: Optional[float] = Field(
        default=None,
        description="Lower numeric bound for AnswerType.NUMBER questions.",
    )
    max_value: Optional[float] = Field(
        default=None,
        description="Upper numeric bound for AnswerType.NUMBER questions.",
    )
    step_value: Optional[float] = Field(
        default=None,
        description="Optional step increment for AnswerType.NUMBER questions.",
    )
    priority: Optional[Literal["core", "standard", "detail"]] = Field(
        default=None,
        description="Optional UX priority tier for progressive disclosure.",
    )
    group_key: Optional[str] = Field(
        default=None,
        description="Optional stable group identifier for UI grouping.",
    )
    depends_on: Optional[List["QuestionDependency"]] = Field(
        default=None,
        description="Optional declarative dependency rules for conditional visibility.",
    )


class QuestionDependency(StrictSchemaModel):
    question_id: str = Field(description="Question id this rule depends on.")
    equals: Optional[Union[str, int, float, bool]] = Field(
        default=None,
        description="Exact value that must match for visibility.",
    )
    any_of: Optional[List[Union[str, int, float, bool]]] = Field(
        default=None,
        description="Any matching value enables visibility.",
    )
    is_answered: Optional[bool] = Field(
        default=None,
        description="If true, dependent question is shown when source has an answer.",
    )


class QuestionStep(StrictSchemaModel):
    step_key: str = Field(
        description="One of the wizard step keys, e.g. 'team' or 'skills'."
    )
    title_de: str
    description_de: Optional[str] = None
    questions: List[Question] = Field(default_factory=list)


class QuestionPlan(StrictSchemaModel):
    schema_version: str = Field(default=QUESTION_SCHEMA_VERSION)
    language: str = Field(default="de")
    steps: List[QuestionStep] = Field(default_factory=list)


class VacancyBriefLLM(StrictSchemaModel):
    """Strict parse-time model for generated briefing sections only."""

    schema_version: str = Field(default=VACANCY_SCHEMA_VERSION)
    language: str = Field(default="de")

    one_liner: str = Field(description="One-sentence role pitch.")
    hiring_context: str = Field(
        description="Why do we hire now, impact, urgency, business context."
    )
    role_summary: str = Field(description="Manager-ready role summary.")
    top_responsibilities: List[str] = Field(default_factory=list)
    must_have: List[str] = Field(default_factory=list)
    nice_to_have: List[str] = Field(default_factory=list)
    dealbreakers: List[str] = Field(default_factory=list)
    interview_plan: List[str] = Field(default_factory=list)
    evaluation_rubric: List[str] = Field(
        default_factory=list, description="Bullet rubric: what to test and how."
    )
    sourcing_channels: List[str] = Field(
        default_factory=list, description="Suggested channels based on role."
    )
    risks_open_questions: List[str] = Field(
        default_factory=list, description="Remaining unknowns / risks."
    )
    job_ad_draft: str = Field(description="A publishable job ad draft (German).")


class VacancyBrief(StrictSchemaModel):
    """Final structured output for recruiters / ATS / stakeholder alignment."""

    schema_version: str = Field(default=VACANCY_SCHEMA_VERSION)
    language: str = Field(default="de")

    one_liner: str = Field(description="One-sentence role pitch.")
    hiring_context: str = Field(
        description="Why do we hire now, impact, urgency, business context."
    )
    role_summary: str = Field(description="Manager-ready role summary.")
    top_responsibilities: List[str] = Field(default_factory=list)
    must_have: List[str] = Field(default_factory=list)
    nice_to_have: List[str] = Field(default_factory=list)
    dealbreakers: List[str] = Field(default_factory=list)

    interview_plan: List[str] = Field(default_factory=list)
    evaluation_rubric: List[str] = Field(
        default_factory=list, description="Bullet rubric: what to test and how."
    )
    sourcing_channels: List[str] = Field(
        default_factory=list, description="Suggested channels based on role."
    )
    risks_open_questions: List[str] = Field(
        default_factory=list, description="Remaining unknowns / risks."
    )

    job_ad_draft: str = Field(description="A publishable job ad draft (German).")
    structured_data: "VacancyStructuredData" = Field(
        default_factory=lambda: VacancyStructuredData(),
        description="Machine-readable full data (job extract + manager answers + optional ESCO mappings).",
    )


class EscoExportConcept(StrictSchemaModel):
    uri: str = Field(description="Canonical ESCO concept URI.")
    label: str = Field(description="Human-readable ESCO label.")


class VacancyStructuredData(StrictSchemaModel):
    job_extract: Dict[str, Any] = Field(default_factory=dict)
    answers: Dict[str, Any] = Field(default_factory=dict)
    selected_role_tasks: Optional[List[str]] = Field(
        default=None,
        description="Optional role task labels explicitly selected in the wizard.",
    )
    selected_skills: Optional[List[str]] = Field(
        default=None,
        description="Optional skill labels explicitly selected in the wizard.",
    )
    esco_occupations: Optional[List[EscoExportConcept]] = Field(
        default=None,
        description="Optional mapped ESCO occupations used for the role.",
    )
    esco_skills_must: Optional[List[EscoExportConcept]] = Field(
        default=None,
        description="Optional mapped ESCO must-have skills.",
    )
    esco_skills_nice: Optional[List[EscoExportConcept]] = Field(
        default=None,
        description="Optional mapped ESCO nice-to-have skills.",
    )
    esco_version: Optional[str] = Field(
        default=None,
        description="Optional ESCO dataset version used during mapping.",
    )


class InterviewQuestionBlock(StrictSchemaModel):
    block_id: str = Field(description="Stable block identifier for UI rendering/order.")
    title: str = Field(
        description="Block title shown in interviewer preparation sheets."
    )
    objective: str = Field(
        description="Why this block is included and what evidence should be collected."
    )
    questions: List[str] = Field(
        default_factory=list,
        description="Concrete interview questions in the sequence they should be asked.",
    )
    follow_up_prompts: List[str] = Field(
        default_factory=list,
        description="Optional prompts for deeper probing when initial answers are vague.",
    )
    signal_tags: List[str] = Field(
        default_factory=list,
        description="Stable tags used for downstream analytics and exports.",
    )


class EvaluationRubricCriterion(StrictSchemaModel):
    criterion_id: str = Field(description="Stable criterion identifier.")
    title: str = Field(description="Short criterion title.")
    description: str = Field(description="What to evaluate for this criterion.")
    weight_percent: int = Field(
        ge=0,
        le=100,
        description="Relative importance from 0 to 100 for score normalization.",
    )
    score_scale: List[str] = Field(
        default_factory=list,
        description="Ordered anchors, e.g., ['1-low', '3-medium', '5-high'].",
    )
    evidence_examples: List[str] = Field(
        default_factory=list,
        description="Examples of observable evidence that supports the score.",
    )


class InterviewPrepSheetHR(StrictSchemaModel):
    role_title: str = Field(description="Role title for recruiter-facing preparation.")
    interview_stage: str = Field(
        description="Pipeline stage this sheet is designed for, e.g., 'HR screen'."
    )
    duration_minutes: int = Field(
        ge=0,
        description="Planned interview duration in minutes.",
    )
    opening_script: str = Field(
        description="Suggested opening script for the interviewer."
    )
    question_blocks: List[InterviewQuestionBlock] = Field(default_factory=list)
    knockout_criteria: List[str] = Field(
        default_factory=list,
        description="Immediate rejection criteria that should be checked consistently.",
    )
    candidate_experience_notes: List[str] = Field(
        default_factory=list,
        description="Notes to keep communication and process candidate-friendly.",
    )
    evaluation_rubric: List[EvaluationRubricCriterion] = Field(default_factory=list)
    final_recommendation_options: List[str] = Field(
        default_factory=list,
        description="Allowed recommendation labels shown in UI and exports.",
    )


class InterviewPrepSheetHiringManager(StrictSchemaModel):
    role_title: str = Field(description="Role title for hiring-manager preparation.")
    interview_stage: str = Field(
        description="Pipeline stage this sheet is designed for, e.g., 'panel interview'."
    )
    duration_minutes: int = Field(
        ge=0,
        description="Planned interview duration in minutes.",
    )
    competencies_to_validate: List[str] = Field(
        default_factory=list,
        description="Priority competencies that must be tested in this interview.",
    )
    question_blocks: List[InterviewQuestionBlock] = Field(default_factory=list)
    technical_deep_dive_topics: List[str] = Field(
        default_factory=list,
        description="Topics reserved for technical depth checks.",
    )
    case_or_task_prompt: Optional[str] = Field(
        default=None,
        description="Optional case-study or assignment prompt.",
    )
    evaluation_rubric: List[EvaluationRubricCriterion] = Field(default_factory=list)
    hiring_signal_summary: List[str] = Field(
        default_factory=list,
        description="Expected strong signals used in the debrief process.",
    )
    debrief_questions: List[str] = Field(
        default_factory=list,
        description="Guided questions for panel debrief and decision alignment.",
    )


class BooleanSearchChannelQueries(StrictSchemaModel):
    broad: List[str] = Field(
        default_factory=list,
        description="Broad query variants for discovery-oriented sourcing.",
    )
    focused: List[str] = Field(
        default_factory=list,
        description="Targeted query variants for precise sourcing.",
    )
    fallback: List[str] = Field(
        default_factory=list,
        description="Fallback query variants when result volume is too low.",
    )


class BooleanSearchPack(StrictSchemaModel):
    role_title: str = Field(description="Role title these search queries target.")
    target_locations: List[str] = Field(
        default_factory=list,
        description="Locations encoded in search variants.",
    )
    seniority_terms: List[str] = Field(
        default_factory=list,
        description="Seniority aliases used across channels.",
    )
    must_have_terms: List[str] = Field(
        default_factory=list,
        description="Core keywords that should appear in most queries.",
    )
    exclusion_terms: List[str] = Field(
        default_factory=list,
        description="Keywords for noise reduction using NOT clauses.",
    )
    google: BooleanSearchChannelQueries = Field(
        description="Google-specific boolean query variants."
    )
    linkedin: BooleanSearchChannelQueries = Field(
        description="LinkedIn-specific boolean query variants."
    )
    xing: BooleanSearchChannelQueries = Field(
        description="XING-specific boolean query variants."
    )
    channel_limitations: List[str] = Field(
        default_factory=list,
        description="Known per-channel constraints and practical caveats.",
    )
    usage_notes: List[str] = Field(
        default_factory=list,
        description="Operational hints for recruiters to adapt queries quickly.",
    )


class ContractClause(StrictSchemaModel):
    clause_id: str = Field(description="Stable clause identifier for legal review.")
    title: str = Field(description="Clause title shown in contract preview/export.")
    clause_text: str = Field(description="Draft wording for the clause.")
    required: bool = Field(
        description="Whether the clause is mandatory for this contract template."
    )
    legal_note: Optional[str] = Field(
        default=None,
        description="Optional legal context or implementation note.",
    )


class EmploymentContractDraft(StrictSchemaModel):
    contract_language: str = Field(description="Contract language, e.g., 'de' or 'en'.")
    jurisdiction: str = Field(
        description="Applicable jurisdiction, e.g., country/state."
    )
    role_title: str = Field(description="Contracted role title.")
    employment_type: str = Field(description="Employment type, e.g., full-time.")
    contract_type: str = Field(description="Contract type, e.g., permanent.")
    start_date: Optional[str] = Field(
        default=None,
        description="Planned start date as plain string for export compatibility.",
    )
    probation_period_months: Optional[int] = Field(
        default=None,
        ge=0,
        description="Optional probation period in months.",
    )
    salary: MoneyRange = Field(description="Compensation range and metadata.")
    working_hours_per_week: Optional[float] = Field(
        default=None,
        ge=0,
        description="Optional weekly working hours.",
    )
    vacation_days_per_year: Optional[int] = Field(
        default=None,
        ge=0,
        description="Optional annual vacation entitlement.",
    )
    place_of_work: Optional[str] = Field(
        default=None,
        description="Main place of work or hybrid setup statement.",
    )
    notice_period: Optional[str] = Field(
        default=None,
        description="Termination notice period wording.",
    )
    clauses: List[ContractClause] = Field(
        default_factory=list,
        description="Ordered contract clauses for rendering and export.",
    )
    signature_requirements: List[str] = Field(
        default_factory=list,
        description="Checklist for compliant execution/signatures.",
    )
    missing_inputs: List[str] = Field(
        default_factory=list,
        description="Data still required before contract can be finalized.",
    )
