from constants import (
    AnswerType,
    FactKey,
    QUESTION_IMPACT_TARGET_BRIEF,
    QUESTION_IMPACT_TARGET_EXPORT,
    QUESTION_IMPACT_TARGET_SALARY,
)
from llm_client import normalize_question_plan
from schemas import Question, QuestionDependency, QuestionPlan, QuestionStep


def test_normalize_category_questions_to_select_types() -> None:
    plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="skills",
                title_de="Skills",
                questions=[
                    Question(
                        id="hard_skills",
                        label="Hard Skills",
                        answer_type=AnswerType.SHORT_TEXT,
                        required=True,
                    ),
                    Question(
                        id="seniority_level",
                        label="Seniority",
                        answer_type=AnswerType.LONG_TEXT,
                    ),
                    Question(
                        id="work_mode",
                        label="Arbeitsmodell",
                        answer_type=AnswerType.SHORT_TEXT,
                        default=["Hybrid"],
                    ),
                ],
            )
        ]
    )

    normalized = normalize_question_plan(plan)
    questions = normalized.steps[0].questions

    assert questions[0].answer_type is AnswerType.MULTI_SELECT
    assert "Sonstiges" in (questions[0].options or [])
    assert questions[0].default == []

    assert questions[1].answer_type is AnswerType.SINGLE_SELECT
    assert "Sonstiges" in (questions[1].options or [])

    assert questions[2].answer_type is AnswerType.SINGLE_SELECT
    assert questions[2].default == "Hybrid"


def test_normalize_numeric_questions_to_number_with_bounds() -> None:
    plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="team",
                title_de="Team",
                questions=[
                    Question(
                        id="years_experience",
                        label="Wie viele Jahre Berufserfahrung sind erforderlich?",
                        answer_type=AnswerType.SHORT_TEXT,
                        required=True,
                    ),
                    Question(
                        id="salary_budget",
                        label="Welches Gehaltsbudget ist geplant?",
                        answer_type=AnswerType.NUMBER,
                    ),
                ],
            )
        ]
    )

    normalized = normalize_question_plan(plan)
    questions = normalized.steps[0].questions

    assert questions[0].answer_type is AnswerType.NUMBER
    assert questions[0].min_value == 0.0
    assert questions[0].max_value == 30.0
    assert questions[0].step_value == 1.0

    assert questions[1].answer_type is AnswerType.NUMBER
    assert questions[1].min_value == 20_000.0
    assert questions[1].max_value == 500_000.0
    assert questions[1].step_value == 1_000.0


def test_normalize_progressive_disclosure_metadata() -> None:
    plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="team",
                title_de="Team",
                questions=[
                    Question(
                        id="Team Lead",
                        label="Gibt es Führungsverantwortung?",
                        answer_type=AnswerType.BOOLEAN,
                        priority="core",
                        group_key="Team Setup",
                    ),
                    Question(
                        id="team_size",
                        label="Wie groß ist das Team?",
                        answer_type=AnswerType.NUMBER,
                        follow_up_prompts=[
                            "  Ab welcher Teamgroesse?  ",
                            "Ab welcher Teamgroesse?",
                            "",
                            "Wer fuehrt fachlich?",
                            "Wie veraendert sich das Team?",
                            "Wird die Rolle aufgebaut?",
                        ],
                        depends_on=[
                            QuestionDependency(question_id="team lead", equals=True),
                            QuestionDependency(question_id="unknown_id", equals=True),
                        ],
                    ),
                ],
            )
        ]
    )

    normalized = normalize_question_plan(plan)
    questions = normalized.steps[0].questions

    assert questions[0].priority == "core"
    assert questions[0].group_key == "team_setup"
    assert questions[1].priority is None
    assert questions[1].group_key == "team_team_size"
    assert questions[1].depends_on == [
        QuestionDependency(question_id="team_lead", equals=True)
    ]
    assert questions[1].follow_up_prompts == [
        "Ab welcher Teamgroesse?",
        "Wer fuehrt fachlich?",
        "Wie veraendert sich das Team?",
    ]


def test_normalize_dependencies_only_keep_earlier_same_step_questions() -> None:
    plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="company",
                title_de="Unternehmen",
                questions=[
                    Question(
                        id="source question",
                        label="Ist Remote-Arbeit moeglich?",
                        answer_type=AnswerType.BOOLEAN,
                    ),
                    Question(
                        id="middle",
                        label="Welche Remote-Regeln gelten?",
                        answer_type=AnswerType.SHORT_TEXT,
                        depends_on=[
                            QuestionDependency(
                                question_id="source question",
                                equals=True,
                            ),
                            QuestionDependency(
                                question_id="later question",
                                equals=True,
                            ),
                            QuestionDependency(question_id="middle", equals=True),
                            QuestionDependency(
                                question_id="source question",
                                equals=True,
                                is_answered=True,
                            ),
                            QuestionDependency(
                                question_id="unknown",
                                is_answered=True,
                            ),
                        ],
                    ),
                    Question(
                        id="later question",
                        label="Welche Regionen sind erlaubt?",
                        answer_type=AnswerType.SHORT_TEXT,
                    ),
                ],
            )
        ]
    )

    normalized = normalize_question_plan(plan)
    questions = normalized.steps[0].questions

    assert questions[1].depends_on == [
        QuestionDependency(question_id="source_question", equals=True)
    ]


def test_normalize_question_fact_key_metadata() -> None:
    plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="company",
                title_de="Unternehmen",
                questions=[
                    Question(
                        id="company_display_name",
                        label="Unternehmen",
                        answer_type=AnswerType.SHORT_TEXT,
                        target_path="company_name",
                    ),
                    Question(
                        id="role_title",
                        label="Rolle",
                        answer_type=AnswerType.SHORT_TEXT,
                        fact_key=FactKey.ROLE_JOB_TITLE.value,
                    ),
                    Question(
                        id="custom_context",
                        label="Kontext",
                        answer_type=AnswerType.SHORT_TEXT,
                        fact_key="invalid.fact_key",
                    ),
                ],
            )
        ]
    )

    normalized = normalize_question_plan(plan)
    questions = normalized.steps[0].questions

    assert questions[0].fact_key == FactKey.COMPANY_COMPANY_NAME.value
    assert questions[1].fact_key == FactKey.ROLE_JOB_TITLE.value
    assert questions[2].fact_key is None


def test_normalize_preserves_adaptive_question_metadata() -> None:
    plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="company",
                title_de="Unternehmen",
                questions=[
                    Question(
                        id="metadata_probe",
                        label="Metadata probe",
                        answer_type=AnswerType.SHORT_TEXT,
                        rationale="Explains why this deterministic question matters.",
                        impact_targets=[QUESTION_IMPACT_TARGET_BRIEF],
                        acquisition_cost="low",
                        info_gain_score=0.67,
                    )
                ],
            )
        ]
    )

    normalized = normalize_question_plan(plan)
    question = normalized.steps[0].questions[0]

    assert question.rationale == "Explains why this deterministic question matters."
    assert question.impact_targets == [QUESTION_IMPACT_TARGET_BRIEF]
    assert question.acquisition_cost == "low"
    assert question.info_gain_score == 0.67


def test_normalize_filters_impact_targets_and_priority_tiers() -> None:
    valid_metadata = Question(
        id="valid_metadata",
        label="Welche Info fehlt?",
        answer_type=AnswerType.SHORT_TEXT,
        impact_targets=[
            QUESTION_IMPACT_TARGET_BRIEF,
            "unknown",
            "Salary",
            QUESTION_IMPACT_TARGET_BRIEF,
            " export ",
        ],
    )
    valid_metadata.priority = " CORE "  # type: ignore[assignment]
    invalid_metadata = Question(
        id="invalid_metadata",
        label="Welche Info ist unklar?",
        answer_type=AnswerType.SHORT_TEXT,
        impact_targets=["crm", ""],
    )
    invalid_metadata.priority = "critical"  # type: ignore[assignment]
    plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="company",
                title_de="Unternehmen",
                questions=[valid_metadata, invalid_metadata],
            )
        ]
    )

    normalized = normalize_question_plan(plan)
    questions = normalized.steps[0].questions

    assert questions[0].priority == "core"
    assert questions[0].impact_targets == [
        QUESTION_IMPACT_TARGET_BRIEF,
        QUESTION_IMPACT_TARGET_SALARY,
        QUESTION_IMPACT_TARGET_EXPORT,
    ]
    assert questions[1].priority is None
    assert questions[1].impact_targets == []


def test_normalize_active_step_group_keys_to_canonical_domains() -> None:
    plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="company",
                title_de="Unternehmen",
                questions=[
                    Question(
                        id="employer_pitch",
                        label="Wie beschreiben wir den Arbeitgeber für Kandidaten?",
                        answer_type=AnswerType.SHORT_TEXT,
                        group_key="Employer Story",
                    ),
                    Question(
                        id="office_policy",
                        label="Welche Remote- oder Hybrid-Regel gilt?",
                        answer_type=AnswerType.SHORT_TEXT,
                        group_key="random workplace bucket",
                    ),
                ],
            ),
            QuestionStep(
                step_key="role_tasks",
                title_de="Rolle",
                questions=[
                    Question(
                        id="decision_scope",
                        label="Welche Entscheidungen darf die Person selbst treffen?",
                        answer_type=AnswerType.SHORT_TEXT,
                    ),
                    Question(
                        id="success_90_days",
                        label="Woran erkennt ihr Erfolg nach 90 Tagen?",
                        answer_type=AnswerType.SHORT_TEXT,
                        group_key="success_30_90_180",
                    ),
                ],
            ),
            QuestionStep(
                step_key="skills",
                title_de="Skills",
                questions=[
                    Question(
                        id="python_depth",
                        label="Welches Niveau in Python ist erforderlich?",
                        answer_type=AnswerType.SHORT_TEXT,
                        group_key="Skill Levels",
                    ),
                    Question(
                        id="skill_substitute",
                        label="Welche Skills können durch Lernkurve ersetzt werden?",
                        answer_type=AnswerType.SHORT_TEXT,
                    ),
                ],
            ),
            QuestionStep(
                step_key="benefits",
                title_de="Benefits",
                questions=[
                    Question(
                        id="salary_budget",
                        label="Welches Gehaltsbudget ist geplant?",
                        answer_type=AnswerType.SHORT_TEXT,
                    ),
                    Question(
                        id="start_contract",
                        label="Welche Vertragsart und welcher Starttermin sind fix?",
                        answer_type=AnswerType.SHORT_TEXT,
                    ),
                ],
            ),
            QuestionStep(
                step_key="interview",
                title_de="Interview",
                questions=[
                    Question(
                        id="scorecard_evidence",
                        label="Welche Bewertungsevidenz braucht ihr je Stufe?",
                        answer_type=AnswerType.SHORT_TEXT,
                    ),
                    Question(
                        id="feedback_sla",
                        label="Welche Feedback-SLA gilt für Kandidaten?",
                        answer_type=AnswerType.SHORT_TEXT,
                    ),
                ],
            ),
        ]
    )

    normalized = normalize_question_plan(plan)
    groups_by_id = {
        question.id: question.group_key
        for step in normalized.steps
        for question in step.questions
    }

    assert groups_by_id == {
        "employer_pitch": "employer_narrative",
        "office_policy": "work_model_location",
        "decision_scope": "ownership_scope",
        "success_90_days": "success_30_90_180",
        "python_depth": "proficiency_depth",
        "skill_substitute": "substitutability",
        "salary_budget": "compensation",
        "start_contract": "contract_start",
        "scorecard_evidence": "evaluation_evidence",
        "feedback_sla": "slas_communication",
    }


def test_normalize_active_step_unknown_group_keys_use_stable_step_fallback() -> None:
    plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="benefits",
                title_de="Benefits",
                questions=[
                    Question(
                        id="unclear_offer_question",
                        label="Welche Besonderheit ist relevant?",
                        answer_type=AnswerType.SHORT_TEXT,
                        group_key="bespoke customer phrase",
                    )
                ],
            )
        ]
    )

    normalized = normalize_question_plan(plan)

    assert normalized.steps[0].questions[0].group_key == "differentiating_benefits"
