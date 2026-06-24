# schemas.py

"""Pydantic models used for Structured Outputs and internal state.

These models are used in two ways:
1) As the JSON schema contract with the OpenAI API (Structured Outputs).
2) As the app's internal data model (stored as dicts in st.session_state).
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

from constants import (
    AnswerType,
    JOB_AD_SCHEMA_VERSION,
    OCCUPATION_CONTEXT_SCHEMA_VERSION,
    OCCUPATION_QUESTION_CONTEXT_SCHEMA_VERSION,
    QUESTION_SCHEMA_VERSION,
    VACANCY_SCHEMA_VERSION,
    WEBSITE_RESEARCH_HOMEPAGE_URL,
    WEBSITE_RESEARCH_OPEN_QUESTION_MATCHES,
    WEBSITE_RESEARCH_SECTIONS,
    WEBSITE_SECTION_FACTS,
    WEBSITE_SECTION_FETCHED_AT,
    WEBSITE_SECTION_SOURCE_URL,
    WEBSITE_SECTION_SUMMARY,
)


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
    context: Optional[str] = Field(
        default=None,
        description="Use context, e.g. internal team work or external client contact.",
    )


SkillRequirementStatus = Literal["must", "nice", "trainable", "knockout"]
SkillReadinessTiming = Literal["start", "90_days", "6_months", "later"]
SkillProficiencyLevel = Literal[
    "basic",
    "practical",
    "solid",
    "expert",
]


class SkillRequirementItem(StrictSchemaModel):
    label: str = Field(description="Human-readable skill or requirement label.")
    status: SkillRequirementStatus = Field(
        description="Recruiting requirement bucket for this skill."
    )
    proficiency: Optional[SkillProficiencyLevel] = Field(
        default=None,
        description="Minimum required proficiency level.",
    )
    readiness_timing: Optional[SkillReadinessTiming] = Field(
        default=None,
        description="When the skill must be available.",
    )
    esco_uri: Optional[str] = Field(
        default=None,
        description="Canonical ESCO skill URI when mapped.",
    )
    evidence_required: Optional[str] = Field(
        default=None,
        description="Evidence, certificate, portfolio, or work sample expected.",
    )
    free_text_reason: Optional[str] = Field(
        default=None,
        description="Reason for keeping this as free text when no ESCO mapping exists.",
    )


class VariablePay(StrictSchemaModel):
    eligible: Optional[bool] = None
    ote_min: Optional[float] = None
    ote_max: Optional[float] = None
    currency: Optional[str] = None
    period: Optional[str] = None
    bonus_logic: Optional[str] = None
    notes: Optional[str] = None


class TravelProfile(StrictSchemaModel):
    required: Optional[bool] = None
    percent: Optional[float] = Field(default=None, ge=0, le=100)
    frequency: Optional[str] = None
    region: Optional[str] = None
    overnight_required: Optional[bool] = None
    driving_license_required: Optional[str] = None
    vehicle_policy: Optional[str] = None


class ScorecardCriterion(StrictSchemaModel):
    title: str
    weight_percent: Optional[int] = Field(default=None, ge=0, le=100)
    scale: Optional[str] = Field(default=None, description="e.g. 1-5 or 1-4.")
    evidence_anchor: Optional[str] = None


class InterviewScorecardTemplate(StrictSchemaModel):
    stage: Optional[str] = None
    criteria: List[ScorecardCriterion] = Field(default_factory=list)
    recommendation_options: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


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


class EscoDisplayLanguageMetadata(StrictSchemaModel):
    display_language: str = Field(description="Language requested by the UI.")
    source_language: Optional[str] = Field(
        default=None,
        description="Language that supplied the displayed field value.",
    )
    fallback_used: bool = Field(
        default=False,
        description="Whether display used a fallback language.",
    )
    field_state: Literal[
        "available",
        "fallback",
        "missing",
        "not_loaded",
        "unsupported",
    ] = Field(default="available", description="Canonical display field state.")
    preferred_label: Optional[str] = Field(
        default=None,
        description="Preferred label used for display, if available.",
    )


class EscoCapabilitySnapshot(StrictSchemaModel):
    release_lane: Literal["stable", "preview"] = "stable"
    selected_version: str = Field(description="Resolved ESCO selectedVersion.")
    api_mode: Literal["hosted", "local"] = "hosted"
    data_source_mode: Literal["live_api", "offline_index", "hybrid"] = "live_api"
    language: str = "de"
    fallback_language: str = "en"
    view_obsolete: bool = False
    last_data_source: Optional[str] = None
    supports_occupation_skills: bool = False
    supports_occupation_knowledge: bool = False
    supports_skill_group_share: bool = False


class EscoAnchorRef(StrictSchemaModel):
    uri: str = Field(description="Canonical ESCO occupation URI.")
    title: str = Field(description="Preferred occupation label.")
    type: str = Field(default="occupation", description="ESCO concept type.")
    code: Optional[str] = Field(default=None, description="Optional ESCO code.")
    reason: Optional[str] = Field(
        default=None,
        description="Reason for secondary anchors or manual confirmation context.",
    )
    selected_as: Literal["primary", "secondary"] = "primary"


class EscoSemanticContext(StrictSchemaModel):
    anchor_state: Literal[
        "degraded_unconfirmed",
        "anchored",
        "anchored_with_context",
    ] = "degraded_unconfirmed"
    semantic_export_mode: Literal["degraded", "anchored"] = "degraded"
    primary_anchor: Optional[EscoAnchorRef] = None
    secondary_anchors: List[EscoAnchorRef] = Field(default_factory=list, max_length=2)
    capability_snapshot: Optional[EscoCapabilitySnapshot] = None
    can_use_esco_normalization: bool = False
    can_use_matrix_coverage: bool = False
    can_use_semantic_exports: bool = False
    can_use_esco_interview_prioritization: bool = False
    can_use_task_suggestions: bool = False


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


class OccupationFamily(str, Enum):
    DIGITAL_PRODUCT = "digital_product"
    CLINICAL_PHYSICIAN = "clinical_physician"
    NURSING_CARE = "nursing_care"
    FIELD_SALES = "field_sales"
    FIELD_SERVICE = "field_service"
    TRANSPORT_LOGISTICS = "transport_logistics"
    CUSTOMER_SUPPORT = "customer_support"
    OFFICE_OPERATIONS = "office_operations"
    EDUCATION_SOCIAL = "education_social"
    INDUSTRIAL_SHIFT = "industrial_shift"
    LEADERSHIP_GENERAL = "leadership_general"
    UNKNOWN = "unknown"


class WorkArrangement(str, Enum):
    ONSITE_REQUIRED = "onsite_required"
    HYBRID_POSSIBLE = "hybrid_possible"
    REMOTE_POSSIBLE = "remote_possible"
    REMOTE_GLOBAL_POSSIBLE = "remote_global_possible"
    UNKNOWN = "unknown"


class RelevanceLevel(str, Enum):
    REQUIRED = "required"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    IRRELEVANT = "irrelevant"
    UNKNOWN = "unknown"


class ClassificationEvidence(StrictSchemaModel):
    source: str
    signal: str
    weight: float = Field(ge=0, le=1)
    rationale: str


class OccupationQuestionConcept(StrictSchemaModel):
    uri: str = Field(default="", description="ESCO concept URI when available.")
    label: str = Field(default="", description="Human-readable concept label.")
    concept_type: Literal["skill", "knowledge", "unknown"] = "unknown"
    relation: Literal["essential", "optional", "unknown"] = "unknown"
    source: Optional[str] = None
    skill_group: Optional[str] = None
    reuse_level: Optional[str] = None


class OccupationQuestionContext(StrictSchemaModel):
    schema_version: str = Field(default=OCCUPATION_QUESTION_CONTEXT_SCHEMA_VERSION)
    occupation_uri: str = ""
    preferred_label: str = ""
    alternative_labels: List[str] = Field(default_factory=list)
    isco_code: Optional[str] = None
    isco_path: List[str] = Field(default_factory=list)
    nace_codes: List[str] = Field(default_factory=list)
    regulated_profession: Optional[bool] = None
    essential_skill_uris: List[str] = Field(default_factory=list)
    optional_skill_uris: List[str] = Field(default_factory=list)
    essential_knowledge_uris: List[str] = Field(default_factory=list)
    optional_knowledge_uris: List[str] = Field(default_factory=list)
    essential_skills: List[OccupationQuestionConcept] = Field(default_factory=list)
    optional_skills: List[OccupationQuestionConcept] = Field(default_factory=list)
    essential_knowledge: List[OccupationQuestionConcept] = Field(default_factory=list)
    optional_knowledge: List[OccupationQuestionConcept] = Field(default_factory=list)
    skill_groups: List[str] = Field(default_factory=list)
    reuse_levels: List[str] = Field(default_factory=list)
    esco_version: Optional[str] = None
    source_mode: Optional[str] = None
    language: str = "de"


class OccupationContextProfile(StrictSchemaModel):
    schema_version: str = Field(default=OCCUPATION_CONTEXT_SCHEMA_VERSION)
    esco_version: Optional[str] = None
    occupation_family: OccupationFamily = OccupationFamily.UNKNOWN
    confidence: float = Field(default=0.0, ge=0, le=1)
    hiring_reason: Optional[str] = None
    urgency: Optional[str] = None
    hiring_volume: Optional[int] = None
    search_confidentiality: Optional[str] = None
    role_definition_maturity: Optional[str] = None
    work_arrangement: WorkArrangement = WorkArrangement.UNKNOWN
    region_scope: str = "unknown"
    contract_context: Optional[str] = None
    international_context: bool = False
    leadership_scope: Optional[str] = None
    driving_relevance: RelevanceLevel = RelevanceLevel.UNKNOWN
    travel_relevance: RelevanceLevel = RelevanceLevel.UNKNOWN
    regulated_profession: Optional[bool] = None
    shift_oncall_relevance: RelevanceLevel = RelevanceLevel.UNKNOWN
    customer_contact_relevance: RelevanceLevel = RelevanceLevel.UNKNOWN
    language_locality_relevance: RelevanceLevel = RelevanceLevel.UNKNOWN
    authority_source: Literal[
        "user_confirmed_esco",
        "deterministic_rules",
        "generic_fallback",
    ] = "generic_fallback"
    pack_keys: List[str] = Field(default_factory=list)
    evidence: List[ClassificationEvidence] = Field(default_factory=list)


class QuestionFlowProvenance(StrictSchemaModel):
    schema_version: str = Field(default=OCCUPATION_CONTEXT_SCHEMA_VERSION)
    profile_fingerprint: str = ""
    base_question_count: int = Field(default=0, ge=0)
    compiled_question_count: int = Field(default=0, ge=0)
    selected_pack_keys: List[str] = Field(default_factory=list)
    resolved_module_keys: List[str] = Field(default_factory=list)
    skipped_module_reasons: Dict[str, str] = Field(default_factory=dict)
    source_uris_by_question_id: Dict[str, List[str]] = Field(default_factory=dict)
    suppressed_question_ids: List[str] = Field(default_factory=list)
    demoted_question_ids: List[str] = Field(default_factory=list)
    injected_question_ids: List[str] = Field(default_factory=list)


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


class JobAdFieldEvidence(StrictSchemaModel):
    field_name: str = Field(
        description="Top-level JobAdExtract field this evidence supports."
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Model confidence for the extracted field value from 0.0 to 1.0.",
    )
    evidence_snippet: Optional[str] = Field(
        default=None,
        description="Short source-text fragment supporting the extracted field; omit unsafe personal data.",
    )
    needs_confirmation: bool = Field(
        default=False,
        description="True when the field is inferred, ambiguous, conflicting, or needs human confirmation.",
    )


class JobAdExtract(StrictSchemaModel):
    """Normalized extraction from a jobspec/job ad."""

    schema_version: str = Field(default=JOB_AD_SCHEMA_VERSION)

    language_guess: Optional[str] = Field(
        default=None, description="Detected language of input, e.g., 'de' or 'en'."
    )
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    brand_name: Optional[str] = None
    company_website: Optional[str] = Field(
        default=None,
        description="Primary public employer homepage URL if identifiable.",
    )

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
    field_evidence: List[JobAdFieldEvidence] = Field(
        default_factory=list,
        description="Optional field-level evidence and confidence for extracted top-level fields.",
    )


class RequirementSuggestionItem(StrictSchemaModel):
    label: str
    type: Literal["skill", "task"]
    source_hint: Literal["llm", "esco_rag"]
    rationale: str
    evidence: str
    importance: Literal["high", "medium", "low"]


class RequirementSuggestionPack(StrictSchemaModel):
    skills: list[RequirementSuggestionItem] = Field(default_factory=list)
    tasks: list[RequirementSuggestionItem] = Field(default_factory=list)


class BenefitSuggestionItem(StrictSchemaModel):
    label: str
    source_hint: Literal["llm"]
    rationale: str
    evidence: str
    importance: Literal["high", "medium", "low"]


class BenefitSuggestionPack(StrictSchemaModel):
    benefits: list[BenefitSuggestionItem] = Field(default_factory=list)


class RoleTaskSalaryForecast(StrictSchemaModel):
    yearly_salary_eur: int = Field(
        ge=0,
        description="Indicative yearly gross salary forecast in EUR.",
    )
    confidence_note: str = Field(
        description="Short confidence note with key assumptions.",
    )


class QuestionOption(StrictSchemaModel):
    value: str = Field(description="Canonical machine-readable option value.")
    label: Optional[str] = Field(
        default=None, description="Human-readable label rendered in the UI."
    )


class Question(StrictSchemaModel):
    id: str = Field(description="Stable unique question id (machine-readable).")
    label: str = Field(description="Exact question text shown to the user.")
    help: Optional[str] = Field(default=None, description="Helper text / tooltip.")
    answer_type: AnswerType = Field(description="Widget/answer type.")
    required: bool = Field(default=False)
    options: Optional[List[Union[str, QuestionOption]]] = Field(
        default=None, description="Options for select widgets."
    )
    default: Optional[
        Union[str, int, float, bool, List[str], List[int], List[float], List[bool]]
    ] = Field(default=None, description="Default value if applicable.")
    target_path: Optional[str] = Field(
        default=None,
        description="Optional dot-path into the final vacancy brief structure; can be used for mapping.",
    )
    fact_key: Optional[str] = Field(
        default=None,
        description="Optional canonical intake fact key used for fact-backed prefill and coverage.",
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
    follow_up_prompts: List[str] = Field(
        default_factory=list,
        description="Optional concise prompts to prioritize this question when deeper probing is useful.",
    )
    impact_targets: List[str] = Field(
        default_factory=list,
        description="Downstream areas affected by this answer, e.g. brief, salary, skills, interview, export.",
    )
    acquisition_cost: Literal["low", "medium", "high"] = Field(
        default="medium",
        description="Estimated user effort required to answer the question.",
    )
    info_gain_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional normalized information-gain score used for adaptive question ranking.",
    )


_OPTION_LABEL_OVERRIDES: dict[str, str] = {
    "keine_hands_on_mentalitaet": "Keine Hands-on-Mentalität",
}


def _humanize_option_value(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        return normalized
    override = _OPTION_LABEL_OVERRIDES.get(normalized.lower())
    if override:
        return override
    normalized = normalized.replace("_", " ").replace("-", " ")
    words = [word for word in normalized.split() if word]
    if not words:
        return value
    return " ".join(word.capitalize() for word in words)


def question_option_label_map(question: Question) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for raw_option in question.options or []:
        if isinstance(raw_option, str):
            option_value = raw_option.strip()
            if option_value:
                mapping[option_value] = _humanize_option_value(option_value)
            continue
        option_value = raw_option.value.strip()
        if not option_value:
            continue
        option_label = (raw_option.label or "").strip() or _humanize_option_value(
            option_value
        )
        mapping[option_value] = option_label
    return mapping


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


class EscoUnresolvedTermDecision(StrictSchemaModel):
    raw_term: str = Field(description="Original unresolved term from jobspec input.")
    action: Literal[
        "map_to_esco_skill",
        "keep_free_text",
        "ignore",
        "retry_search",
    ] = Field(
        validation_alias=AliasChoices("action", "status"),
        description="Canonical unresolved-term action.",
    )
    mapped_uri: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("mapped_uri", "esco_uri"),
        description="Chosen ESCO URI when action resolves to an ESCO skill.",
    )
    mapped_title: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("mapped_title", "matched_label"),
        description="Chosen ESCO label when action resolves to an ESCO skill.",
    )
    bucket: Optional[str] = Field(
        default=None,
        description="Source bucket of the unresolved term (e.g., must/nice/unknown).",
    )
    source_mode: Optional[str] = Field(
        default=None,
        description="ESCO data_source_mode active while taking the decision.",
    )

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_fields(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        payload = dict(value)
        legacy_status = str(payload.get("status") or "").strip().lower()
        legacy_method = str(payload.get("match_method") or "").strip().lower()
        if not payload.get("action"):
            if legacy_status in {"mapped", "merged"}:
                payload["action"] = "map_to_esco_skill"
            elif legacy_status == "custom":
                payload["action"] = "keep_free_text"
            elif legacy_status == "ignored":
                payload["action"] = "ignore"
            elif legacy_status == "retried" or legacy_method == "retry_query":
                payload["action"] = "retry_search"
        payload.pop("status", None)
        payload.pop("match_method", None)
        payload.pop("language", None)
        return payload


class EscoMatrixCoverageRow(StrictSchemaModel):
    occupation_group: str = Field(
        description="ISCO occupation group key used for matrix coverage lookup."
    )
    skill_group_uri: Optional[str] = Field(
        default=None,
        description="Optional ESCO skill-group URI for the expected matrix row.",
    )
    skill_group_id: Optional[str] = Field(
        default=None,
        description="Optional stable skill-group identifier from preprocessed matrix data.",
    )
    skill_group_label: str = Field(
        description="Human-readable skill-group label."
    )
    expected_share_percent: Optional[float] = Field(
        default=None,
        description="Expected ISCO matrix share percentage for this skill-group row.",
    )
    matched_skill_uris: List[str] = Field(
        default_factory=list,
        description="Matched confirmed skill URIs contributing to coverage.",
    )
    matched_skill_titles: List[str] = Field(
        default_factory=list,
        description="Matched confirmed skill titles contributing to coverage.",
    )
    coverage_status: Literal[
        "covered",
        "missing",
        "partial",
        "overrepresented",
    ] = Field(
        description="Deterministic coverage classification for this matrix row.",
    )
    match_basis: Optional[Literal["uri", "group", "none"]] = Field(
        default=None,
        description="Optional deterministic reason explaining whether matching used URI, group fallback, or no match.",
    )
    matrix_bucket: Literal["must", "nice"] = Field(
        description="Matrix bucket associated with the expected row."
    )


class WebsiteResearchSection(StrictSchemaModel):
    source_url: Optional[str] = Field(
        default=None,
        serialization_alias=WEBSITE_SECTION_SOURCE_URL,
    )
    summary: List[str] = Field(
        default_factory=list,
        serialization_alias=WEBSITE_SECTION_SUMMARY,
    )
    facts: Dict[str, str] = Field(
        default_factory=dict,
        serialization_alias=WEBSITE_SECTION_FACTS,
    )
    fetched_at: Optional[str] = Field(
        default=None,
        serialization_alias=WEBSITE_SECTION_FETCHED_AT,
    )


class WebsiteOpenQuestionMatch(StrictSchemaModel):
    question_id: str
    question_label: str
    source_topic: str
    match_tokens: Optional[str] = None


class CompanyWebsiteResearch(StrictSchemaModel):
    homepage_url: Optional[str] = Field(
        default=None,
        serialization_alias=WEBSITE_RESEARCH_HOMEPAGE_URL,
    )
    sections: Dict[str, WebsiteResearchSection] = Field(
        default_factory=dict,
        serialization_alias=WEBSITE_RESEARCH_SECTIONS,
    )
    open_question_matches: List[WebsiteOpenQuestionMatch] = Field(
        default_factory=list,
        serialization_alias=WEBSITE_RESEARCH_OPEN_QUESTION_MATCHES,
    )


class VacancyStructuredData(StrictSchemaModel):
    job_extract: Dict[str, Any] = Field(default_factory=dict)
    answers: Dict[str, Any] = Field(default_factory=dict)
    skill_items: Optional[List[SkillRequirementItem]] = Field(
        default=None,
        description="Optional normalized skill rows with proficiency, timing, and evidence.",
    )
    variable_pay: Optional[VariablePay] = Field(
        default=None,
        description="Optional normalized variable compensation details.",
    )
    travel_profile: Optional[TravelProfile] = Field(
        default=None,
        description="Optional normalized travel and mobility requirements.",
    )
    interview_scorecard_template: Optional[InterviewScorecardTemplate] = Field(
        default=None,
        description="Optional structured scorecard template for interview exports.",
    )
    selected_role_tasks: Optional[List[str]] = Field(
        default=None,
        description="Optional role task labels explicitly selected in the wizard.",
    )
    selected_skills: Optional[List[str]] = Field(
        default=None,
        description="Optional skill labels explicitly selected in the wizard.",
    )
    selected_benefits: Optional[List[str]] = Field(
        default=None,
        description="Optional benefit labels explicitly selected in the wizard.",
    )
    offer_positioning: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional offer decision context for benefits, terms, caveats, and output impact.",
    )
    salary_forecast: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional deterministic salary forecast snapshot used as orientation only.",
    )
    interview_process: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional sanitized hiring-plan context for downstream interview artifacts.",
    )
    company_website_research: Optional[CompanyWebsiteResearch] = Field(
        default=None,
        description="Optional homepage research findings captured in the company step.",
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
    esco_unresolved_term_decisions: Optional[List[EscoUnresolvedTermDecision]] = Field(
        default=None,
        description="Optional decision log for unresolved terms with provenance fields.",
    )
    esco_matrix_coverage: Optional[List[EscoMatrixCoverageRow]] = Field(
        default=None,
        description="Optional ISCO matrix skill-group coverage rows.",
    )
    esco_matrix_coverage_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional matrix coverage context metadata (reason, occupation_group, row count).",
    )
    occupation_context_profile: Optional[OccupationContextProfile] = Field(
        default=None,
        description="Optional deterministic occupation-aware context profile used for question flow selection.",
    )
    occupation_question_context: Optional[OccupationQuestionContext] = Field(
        default=None,
        description="Optional ESCO/ISCO question context used for deterministic question module resolution.",
    )
    question_flow_provenance: Optional[QuestionFlowProvenance] = Field(
        default=None,
        description="Optional deterministic question-flow compilation provenance.",
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
