from __future__ import annotations

from constants import (
    AnswerType,
    FactKey,
    FactResolutionStatus,
    FactSourceType,
    SSKey,
)
from question_progress import (
    build_answered_lookup,
    build_answers_with_job_extract_coverage,
    build_step_scope_progress_labels,
    compute_question_progress,
    is_answered,
)
from schemas import JobAdExtract, Question


def _question(answer_type: AnswerType) -> Question:
    return Question(id=f"q_{answer_type.value}", label="Frage", answer_type=answer_type)


def test_is_answered_text_requires_non_empty_value() -> None:
    question = _question(AnswerType.SHORT_TEXT)

    assert is_answered(question, "Ja", {}) is True
    assert is_answered(question, "   ", {}) is False


def test_is_answered_multi_select_requires_non_empty_list() -> None:
    question = _question(AnswerType.MULTI_SELECT)

    assert is_answered(question, ["A"], {}) is True
    assert is_answered(question, [], {}) is False


def test_is_answered_single_select_rejects_placeholder() -> None:
    question = _question(AnswerType.SINGLE_SELECT)

    assert is_answered(question, "Option A", {}) is True
    assert is_answered(question, "— Bitte wählen —", {}) is False
    assert is_answered(question, None, {}) is False


def test_is_answered_boolean_requires_touch_or_confirm() -> None:
    question = _question(AnswerType.BOOLEAN)

    assert is_answered(question, False, {}) is False
    assert is_answered(question, False, {"touched": True}) is True
    assert is_answered(question, False, {"confirmed": True}) is True


def test_is_answered_number_requires_touch_or_confirm() -> None:
    question = _question(AnswerType.NUMBER)

    assert is_answered(question, 50, {}) is False
    assert is_answered(question, 50, {"touched": True}) is True


def test_is_answered_date_requires_non_empty_string() -> None:
    question = _question(AnswerType.DATE)

    assert is_answered(question, "2026-04-08", {}) is True
    assert is_answered(question, "", {}) is False


def test_compute_question_progress_counts_answered_and_required_open() -> None:
    required_text = Question(
        id="q_req_text",
        label="Pflicht Text",
        answer_type=AnswerType.SHORT_TEXT,
        required=True,
    )
    optional_multi = Question(
        id="q_opt_multi",
        label="Optional Multi",
        answer_type=AnswerType.MULTI_SELECT,
        required=False,
    )
    required_boolean = Question(
        id="q_req_bool",
        label="Pflicht Bool",
        answer_type=AnswerType.BOOLEAN,
        required=True,
    )
    required_number = Question(
        id="q_req_number",
        label="Pflicht Zahl",
        answer_type=AnswerType.NUMBER,
        required=True,
    )

    progress = compute_question_progress(
        [required_text, optional_multi, required_boolean, required_number],
        answers={
            "q_req_text": "Ja",
            "q_opt_multi": ["A"],
            "q_req_bool": False,
            "q_req_number": 3,
        },
        answer_meta={
            "q_req_bool": {"touched": True},
            "q_req_number": {},
        },
    )

    assert progress == {"total": 4, "answered": 3, "required_unanswered": 1}


def test_jobspec_extract_covers_company_alias_questions_without_answers() -> None:
    questions = [
        Question(
            id="company_q_1",
            label="Wie heißt das Unternehmen?",
            answer_type=AnswerType.SHORT_TEXT,
            required=True,
        ),
        Question(
            id="company_website",
            label="Welche Website hat das Unternehmen?",
            answer_type=AnswerType.SHORT_TEXT,
            required=True,
        ),
        Question(
            id="contract_kind",
            label="Was ist die Art des Arbeitsvertrags?",
            answer_type=AnswerType.SHORT_TEXT,
            required=True,
        ),
    ]
    job_extract = JobAdExtract(
        company_name="Rheinbahn",
        employment_type="Unbefristeter Arbeitsvertrag",
    )

    answered_lookup = build_answered_lookup(
        questions,
        answers={},
        answer_meta={},
        job_extract=job_extract,
    )
    progress = compute_question_progress(
        questions,
        answers={},
        answer_meta={},
        answered_lookup=answered_lookup,
    )

    assert answered_lookup == {
        "company_q_1": True,
        "company_website": False,
        "contract_kind": True,
    }
    assert progress == {"total": 3, "answered": 2, "required_unanswered": 1}


def test_legacy_target_path_question_resolves_jobspec_coverage() -> None:
    question = Question(
        id="legacy_role_title",
        label="Welche Rolle wird gesucht?",
        answer_type=AnswerType.SHORT_TEXT,
        required=True,
        target_path="job_title",
    )

    answered_lookup = build_answered_lookup(
        [question],
        answers={},
        answer_meta={},
        job_extract=JobAdExtract(job_title="Data Engineer"),
    )

    assert answered_lookup == {"legacy_role_title": True}


def test_canonical_intake_facts_cover_supported_fact_keys() -> None:
    questions = [
        Question(
            id="q_company",
            label="Unternehmen",
            answer_type=AnswerType.SHORT_TEXT,
            target_path="company_name",
        ),
        Question(
            id="q_role",
            label="Rolle",
            answer_type=AnswerType.SHORT_TEXT,
            target_path=FactKey.ROLE_JOB_TITLE.value,
        ),
        Question(
            id="q_must_have",
            label="Must-have Skills",
            answer_type=AnswerType.MULTI_SELECT,
            target_path="job.must_have_skills",
        ),
    ]
    session_state = {
        SSKey.INTAKE_FACTS.value: {
            FactKey.COMPANY_COMPANY_NAME.value: "Example GmbH",
            FactKey.ROLE_JOB_TITLE.value: "Data Engineer",
            FactKey.SKILLS_MUST_HAVE_SKILLS.value: ["Python", "SQL"],
        }
    }

    answered_lookup = build_answered_lookup(
        questions,
        answers={},
        answer_meta={},
        intake_facts=session_state[SSKey.INTAKE_FACTS.value],
    )
    effective_answers = build_answers_with_job_extract_coverage(
        questions,
        answers={},
        answer_meta={},
        intake_facts=session_state[SSKey.INTAKE_FACTS.value],
    )

    assert answered_lookup == {
        "q_company": True,
        "q_role": True,
        "q_must_have": True,
    }
    assert effective_answers == {
        "q_company": "Example GmbH",
        "q_role": "Data Engineer",
        "q_must_have": ["Python", "SQL"],
    }


def test_low_confidence_intake_fact_does_not_cover_matching_question() -> None:
    question = Question(
        id="q_role",
        label="Rolle",
        answer_type=AnswerType.SHORT_TEXT,
        target_path=FactKey.ROLE_JOB_TITLE.value,
    )
    intake_facts = {FactKey.ROLE_JOB_TITLE.value: "Data Engineer"}
    intake_fact_evidence = {
        FactKey.ROLE_JOB_TITLE.value: {
            "source_type": "jobspec",
            "confidence": 0.4,
        }
    }

    answered_lookup = build_answered_lookup(
        [question],
        answers={},
        answer_meta={},
        job_extract=JobAdExtract(job_title="Data Engineer"),
        intake_facts=intake_facts,
        intake_fact_evidence=intake_fact_evidence,
        confidence_threshold=0.6,
    )
    effective_answers = build_answers_with_job_extract_coverage(
        [question],
        answers={},
        answer_meta={},
        job_extract=JobAdExtract(job_title="Data Engineer"),
        intake_facts=intake_facts,
        intake_fact_evidence=intake_fact_evidence,
        confidence_threshold=0.6,
    )

    assert answered_lookup == {"q_role": False}
    assert effective_answers == {}


def test_homepage_intake_fact_covers_matching_question() -> None:
    question = Question(
        id="q_company",
        label="Unternehmen",
        answer_type=AnswerType.SHORT_TEXT,
        target_path=FactKey.COMPANY_COMPANY_NAME.value,
    )

    answered_lookup = build_answered_lookup(
        [question],
        answers={},
        answer_meta={},
        intake_facts={FactKey.COMPANY_COMPANY_NAME.value: "Example GmbH"},
        intake_fact_evidence={
            FactKey.COMPANY_COMPANY_NAME.value: {
                "source_type": FactSourceType.HOMEPAGE.value,
                "confidence": 0.85,
                "resolution_status": FactResolutionStatus.CONFIRMED.value,
            }
        },
        confidence_threshold=0.6,
    )

    assert answered_lookup == {"q_company": True}


def test_conflicted_intake_fact_does_not_cover_matching_question() -> None:
    question = Question(
        id="q_company",
        label="Unternehmen",
        answer_type=AnswerType.SHORT_TEXT,
        target_path=FactKey.COMPANY_COMPANY_NAME.value,
    )

    answered_lookup = build_answered_lookup(
        [question],
        answers={},
        answer_meta={},
        intake_facts={FactKey.COMPANY_COMPANY_NAME.value: "Example GmbH"},
        intake_fact_evidence={
            FactKey.COMPANY_COMPANY_NAME.value: {
                "source_type": FactSourceType.HOMEPAGE.value,
                "confidence": 0.85,
                "resolution_status": FactResolutionStatus.CONFLICTED.value,
            }
        },
        confidence_threshold=0.6,
    )

    assert answered_lookup == {"q_company": False}


def test_secondary_homepage_conflict_keeps_confirmed_fact_coverage() -> None:
    question = Question(
        id="q_company",
        label="Unternehmen",
        answer_type=AnswerType.SHORT_TEXT,
        target_path=FactKey.COMPANY_COMPANY_NAME.value,
    )

    answered_lookup = build_answered_lookup(
        [question],
        answers={},
        answer_meta={},
        intake_facts={FactKey.COMPANY_COMPANY_NAME.value: "Example GmbH"},
        intake_fact_evidence={
            FactKey.COMPANY_COMPANY_NAME.value: {
                "source_type": FactSourceType.MANUAL.value,
                "confidence": 1.0,
                "confirmed": True,
                "resolution_status": FactResolutionStatus.CONFIRMED.value,
                "secondary_evidence": [
                    {
                        "source_type": FactSourceType.HOMEPAGE.value,
                        "resolution_status": FactResolutionStatus.CONFLICTED.value,
                        "value": "Other GmbH",
                    }
                ],
            }
        },
        confidence_threshold=0.6,
    )

    assert answered_lookup == {"q_company": True}


def test_intake_fact_without_evidence_keeps_legacy_coverage_behavior() -> None:
    question = Question(
        id="q_role",
        label="Rolle",
        answer_type=AnswerType.SHORT_TEXT,
        target_path=FactKey.ROLE_JOB_TITLE.value,
    )

    answered_lookup = build_answered_lookup(
        [question],
        answers={},
        answer_meta={},
        intake_facts={FactKey.ROLE_JOB_TITLE.value: "Data Engineer"},
        confidence_threshold=0.95,
    )

    assert answered_lookup == {"q_role": True}


def test_explicit_fact_key_covers_question_without_aliasable_id_or_target_path() -> None:
    question = Question(
        id="q_1",
        label="Welche Rolle wird gesucht?",
        answer_type=AnswerType.SHORT_TEXT,
        target_path="answers.company.custom_role_question",
        fact_key=FactKey.ROLE_JOB_TITLE.value,
    )

    answered_lookup = build_answered_lookup(
        [question],
        answers={},
        answer_meta={},
        intake_facts={FactKey.ROLE_JOB_TITLE.value: "Data Engineer"},
    )

    assert answered_lookup == {"q_1": True}


def test_empty_canonical_intake_fact_values_do_not_count_as_answered() -> None:
    questions = [
        Question(
            id="q_company",
            label="Unternehmen",
            answer_type=AnswerType.SHORT_TEXT,
            target_path="company_name",
        ),
        Question(
            id="q_must_have",
            label="Must-have Skills",
            answer_type=AnswerType.MULTI_SELECT,
            target_path="must_have_skills",
        ),
        Question(
            id="q_salary",
            label="Gehalt",
            answer_type=AnswerType.SHORT_TEXT,
            target_path="salary_range",
        ),
    ]
    intake_facts = {
        FactKey.COMPANY_COMPANY_NAME.value: "   ",
        FactKey.SKILLS_MUST_HAVE_SKILLS.value: [],
        FactKey.BENEFITS_SALARY_RANGE.value: {"min": None, "max": ""},
    }

    answered_lookup = build_answered_lookup(
        questions,
        answers={},
        answer_meta={},
        intake_facts=intake_facts,
    )

    assert answered_lookup == {
        "q_company": False,
        "q_must_have": False,
        "q_salary": False,
    }


def test_jobspec_fallbacks_still_work_without_canonical_facts() -> None:
    questions = [
        Question(
            id="direct_website",
            label="Website",
            answer_type=AnswerType.SHORT_TEXT,
            target_path="company_website",
        ),
        Question(
            id="legacy.location_city",
            label="Standort",
            answer_type=AnswerType.SHORT_TEXT,
        ),
        Question(
            id="contract_kind",
            label="Was ist die Art des Arbeitsvertrags?",
            answer_type=AnswerType.SHORT_TEXT,
        ),
    ]
    job_extract = JobAdExtract(
        company_website="https://example.test",
        location_city="Berlin",
        employment_type="Unbefristeter Arbeitsvertrag",
    )

    answered_lookup = build_answered_lookup(
        questions,
        answers={},
        answer_meta={},
        job_extract=job_extract,
    )

    assert answered_lookup == {
        "direct_website": True,
        "legacy.location_city": True,
        "contract_kind": True,
    }


def test_effective_answers_include_jobspec_values_for_dependency_visibility() -> None:
    remote_question = Question(
        id="work_mode",
        label="Welche Remote-Regelung gilt?",
        answer_type=AnswerType.SHORT_TEXT,
        target_path="remote_policy",
    )
    effective_answers = build_answers_with_job_extract_coverage(
        [remote_question],
        answers={},
        answer_meta={},
        job_extract=JobAdExtract(remote_policy="Mobiles Arbeiten"),
    )

    assert effective_answers["work_mode"] == "Mobiles Arbeiten"


def test_build_step_scope_progress_labels_marks_scope_difference() -> None:
    labels = build_step_scope_progress_labels(
        visible_answered=1,
        visible_total=1,
        overall_answered=1,
        overall_total=3,
    )

    assert labels["visible_label"] == "Sichtbar im aktuellen Umfang: 1/1"
    assert (
        labels["overall_label"]
        == "Gesamt im Step (inkl. derzeit ausgeblendeter Details): 1/3"
    )
    assert labels["has_different_denominator"] is True
