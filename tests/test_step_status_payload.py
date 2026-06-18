from __future__ import annotations

from constants import AnswerType, FactKey, STEP_KEY_ROLE_TASKS
from question_dependencies import should_show_question
from question_limits import build_step_question_scope, select_questions_for_step_scope
from schemas import JobAdExtract, Question, QuestionDependency, QuestionStep
from step_status import build_step_status_payload


def _always_visible(*_: object) -> bool:
    return True


def test_build_step_status_payload_includes_missing_essential_ids_and_labels() -> None:
    step = QuestionStep(
        step_key="company",
        title_de="Company",
        questions=[
            Question(
                id="q_core_open",
                label="Pflicht offen",
                answer_type=AnswerType.SHORT_TEXT,
                required=True,
                priority="core",
            ),
            Question(
                id="q_core_done",
                label="Pflicht erledigt",
                answer_type=AnswerType.SHORT_TEXT,
                required=True,
                priority="core",
            ),
            Question(
                id="q_detail",
                label="Detail",
                answer_type=AnswerType.SHORT_TEXT,
                required=False,
                priority="detail",
            ),
        ],
    )

    payload = build_step_status_payload(
        step=step,
        answers={"q_core_done": "Ja"},
        answer_meta={},
        should_show_question=_always_visible,
        step_key=step.step_key,
    )

    assert payload["missing_essential_ids"] == ["q_core_open"]
    assert payload["missing_essentials"] == ["Pflicht offen"]
    assert payload["essentials_answered"] == 1
    assert payload["essentials_total"] == 2


def test_build_step_status_payload_counts_jobspec_covered_company_essentials() -> None:
    step = QuestionStep(
        step_key="company",
        title_de="Company",
        questions=[
            Question(
                id="company_q_name",
                label="Wie heißt das Unternehmen?",
                answer_type=AnswerType.SHORT_TEXT,
                required=True,
                priority="core",
            ),
            Question(
                id="company_q_city",
                label="In welcher Stadt befindet sich das Unternehmen?",
                answer_type=AnswerType.SHORT_TEXT,
                required=True,
                priority="core",
            ),
            Question(
                id="company_q_country",
                label="In welchem Land befindet sich das Unternehmen?",
                answer_type=AnswerType.SHORT_TEXT,
                required=True,
                priority="core",
            ),
            Question(
                id="company_q_contract",
                label="Was ist die Art des Arbeitsvertrags?",
                answer_type=AnswerType.SHORT_TEXT,
                required=True,
                priority="core",
            ),
        ],
    )

    payload = build_step_status_payload(
        step=step,
        answers={},
        answer_meta={},
        should_show_question=_always_visible,
        step_key=step.step_key,
        job_extract=JobAdExtract(
            company_name="Rheinbahn",
            employment_type="Unbefristeter Arbeitsvertrag",
        ),
    )

    assert payload["answered"] == 2
    assert payload["total"] == 4
    assert payload["essentials_answered"] == 2
    assert payload["essentials_total"] == 4
    assert payload["missing_essential_ids"] == [
        "company_q_city",
        "company_q_country",
    ]


def test_build_step_status_payload_passes_canonical_facts_to_visibility() -> None:
    step = QuestionStep(
        step_key="company",
        title_de="Company",
        questions=[
            Question(
                id="company_q_name",
                label="Wie heißt das Unternehmen?",
                answer_type=AnswerType.SHORT_TEXT,
                required=True,
                priority="core",
            ),
            Question(
                id="remote_policy_detail",
                label="Wie viele On-site Tage pro Woche?",
                help="Remote policy und Onsite-Erwartungen beschreiben.",
                answer_type=AnswerType.SHORT_TEXT,
                required=True,
                priority="core",
            ),
        ],
    )

    without_facts = build_step_status_payload(
        step=step,
        answers={"company_q_name": "Example GmbH"},
        answer_meta={},
        should_show_question=should_show_question,
        step_key=step.step_key,
    )
    with_facts = build_step_status_payload(
        step=step,
        answers={"company_q_name": "Example GmbH"},
        answer_meta={},
        should_show_question=should_show_question,
        step_key=step.step_key,
        intake_facts={FactKey.COMPANY_REMOTE_POLICY.value: "Hybrid"},
    )

    assert without_facts["total"] == 1
    assert without_facts["missing_essential_ids"] == []
    assert with_facts["total"] == 2
    assert with_facts["missing_essential_ids"] == ["remote_policy_detail"]


def test_build_step_status_payload_keeps_legacy_visibility_predicates() -> None:
    step = QuestionStep(
        step_key="company",
        title_de="Company",
        questions=[
            Question(
                id="company_q_name",
                label="Wie heißt das Unternehmen?",
                answer_type=AnswerType.SHORT_TEXT,
                target_path="company_name",
                required=True,
                priority="core",
            )
        ],
    )

    def legacy_visibility(
        question: Question,
        answers: dict[str, object],
        answer_meta: dict[str, object],
        step_key: str,
    ) -> bool:
        assert question.id == "company_q_name"
        assert answers == {"company_q_name": "Example GmbH"}
        assert answer_meta == {}
        assert step_key == "company"
        return True

    payload = build_step_status_payload(
        step=step,
        answers={},
        answer_meta={},
        should_show_question=legacy_visibility,
        step_key=step.step_key,
        intake_facts={FactKey.COMPANY_COMPANY_NAME.value: "Example GmbH"},
    )

    assert payload["total"] == 1
    assert payload["answered"] == 1


def test_build_step_status_payload_keeps_jobspec_fallback_without_facts() -> None:
    step = QuestionStep(
        step_key="company",
        title_de="Company",
        questions=[
            Question(
                id="company_q_name",
                label="Wie heißt das Unternehmen?",
                answer_type=AnswerType.SHORT_TEXT,
                required=True,
                priority="core",
            )
        ],
    )

    payload = build_step_status_payload(
        step=step,
        answers={},
        answer_meta={},
        should_show_question=_always_visible,
        step_key=step.step_key,
        job_extract=JobAdExtract(company_name="Example GmbH"),
    )

    assert payload["total"] == 1
    assert payload["answered"] == 1
    assert payload["missing_essential_ids"] == []


def test_build_step_status_payload_counts_jobspec_evidence_fact_and_missing_fact() -> None:
    step = QuestionStep(
        step_key=STEP_KEY_ROLE_TASKS,
        title_de="Role",
        questions=[
            Question(
                id="role_title",
                label="Welche Rolle wird gesucht?",
                answer_type=AnswerType.SHORT_TEXT,
                target_path=FactKey.ROLE_JOB_TITLE.value,
                required=True,
                priority="core",
            ),
            Question(
                id="location_country",
                label="Für welches Land gilt die Vakanz?",
                answer_type=AnswerType.SHORT_TEXT,
                target_path=FactKey.COMPANY_LOCATION_COUNTRY.value,
                required=True,
                priority="core",
            ),
        ],
    )

    payload = build_step_status_payload(
        step=step,
        answers={},
        answer_meta={},
        should_show_question=_always_visible,
        step_key=step.step_key,
        intake_facts={FactKey.ROLE_JOB_TITLE.value: "Data Engineer"},
        intake_fact_evidence={
            FactKey.ROLE_JOB_TITLE.value: {
                "source_label": "Jobspec extraction",
                "confidence": 0.9,
            }
        },
        confidence_threshold=0.6,
    )

    assert payload["answered"] == 1
    assert payload["total"] == 2
    assert payload["essentials_answered"] == 1
    assert payload["essentials_total"] == 2
    assert payload["missing_essential_ids"] == ["location_country"]


def test_build_step_status_payload_uses_canonical_visible_question_scope() -> None:
    step = QuestionStep(
        step_key="company",
        title_de="Company",
        questions=[
            Question(
                id="remote_policy",
                label="Remote policy",
                answer_type=AnswerType.SHORT_TEXT,
                target_path=FactKey.COMPANY_REMOTE_POLICY.value,
                required=True,
                priority="core",
            ),
            Question(
                id="hybrid_days",
                label="Wie viele Office-Tage?",
                answer_type=AnswerType.NUMBER,
                required=True,
                priority="core",
                depends_on=[
                    QuestionDependency(question_id="remote_policy", equals="Hybrid")
                ],
            ),
        ],
    )

    payload = build_step_status_payload(
        step=step,
        answers={},
        answer_meta={},
        should_show_question=should_show_question,
        step_key=step.step_key,
        intake_facts={FactKey.COMPANY_REMOTE_POLICY.value: "Hybrid"},
        intake_fact_evidence={
            FactKey.COMPANY_REMOTE_POLICY.value: {
                "source_label": "Jobspec extraction",
                "confidence": 0.4,
            }
        },
        confidence_threshold=0.6,
    )

    assert payload["answered"] == 0
    assert payload["total"] == 1
    assert payload["missing_essential_ids"] == ["remote_policy"]


def test_step_status_uses_precomputed_visible_scope_for_adaptive_dependencies() -> None:
    trigger = Question(
        id="remote_policy",
        label="Remote policy",
        answer_type=AnswerType.SHORT_TEXT,
        target_path=FactKey.COMPANY_REMOTE_POLICY.value,
        priority="detail",
    )
    dependent = Question(
        id="hybrid_days",
        label="Wie viele Office-Tage?",
        answer_type=AnswerType.NUMBER,
        required=True,
        priority="core",
        depends_on=[QuestionDependency(question_id="remote_policy", equals="Hybrid")],
    )
    intake_facts = {FactKey.COMPANY_REMOTE_POLICY.value: "Hybrid"}
    scope = build_step_question_scope(
        [trigger, dependent],
        step_key="company",
        question_limits={"company": 1},
        answers={},
        answer_meta={},
        job_extract=None,
        intake_facts=intake_facts,
    )

    payload = build_step_status_payload(
        step=QuestionStep(
            step_key="company",
            title_de="Company",
            questions=scope.selected_questions,
        ),
        answers={},
        answer_meta={},
        should_show_question=should_show_question,
        step_key="company",
        intake_facts=intake_facts,
        visible_questions=scope.visible_questions,
    )

    assert [question.id for question in scope.selected_questions] == ["hybrid_days"]
    assert payload["total"] == 1
    assert payload["missing_essential_ids"] == ["hybrid_days"]


def test_step_status_payload_matches_adaptive_selected_question_scope() -> None:
    covered_detail = Question(
        id="covered_detail",
        label="Already covered",
        answer_type=AnswerType.SHORT_TEXT,
        priority="detail",
        target_path=FactKey.COMPANY_COMPANY_NAME.value,
    )
    uncovered_core = Question(
        id="uncovered_core",
        label="Hiring goal",
        answer_type=AnswerType.SHORT_TEXT,
        priority="core",
    )
    selected_questions = select_questions_for_step_scope(
        [covered_detail, uncovered_core],
        step_key="company",
        question_limits={"company": 1},
        answers={},
        answer_meta={},
        job_extract=None,
        intake_facts={FactKey.COMPANY_COMPANY_NAME.value: "Example GmbH"},
    )

    payload = build_step_status_payload(
        step=QuestionStep(
            step_key="company",
            title_de="Company",
            questions=selected_questions,
        ),
        answers={},
        answer_meta={},
        should_show_question=_always_visible,
        step_key="company",
        intake_facts={FactKey.COMPANY_COMPANY_NAME.value: "Example GmbH"},
    )

    assert [question.id for question in selected_questions] == ["uncovered_core"]
    assert payload["total"] == 1
    assert payload["answered"] == 0
    assert payload["missing_essential_ids"] == ["uncovered_core"]
