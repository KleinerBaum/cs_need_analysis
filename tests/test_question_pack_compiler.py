from __future__ import annotations

import json
import warnings
from enum import Enum
from pathlib import Path

import pytest
from constants import (
    AnswerType,
    ESCO_QUESTION_SKILL_GROUP_DIGITAL_DATA_AI,
    ESCO_QUESTION_SKILL_GROUP_REGULATION_SAFETY,
    ESCO_QUESTION_SKILL_GROUP_TOOLS_METHODS,
    FactKey,
    QUESTION_IMPACT_TARGET_BRIEF,
    QUESTION_IMPACT_TARGET_EXPORT,
    QUESTION_IMPACT_TARGET_INTERVIEW,
    QUESTION_IMPACT_TARGET_SALARY,
    QUESTION_IMPACT_TARGET_SKILLS,
    QUESTION_IMPACT_TARGETS,
    STEP_KEY_COMPANY,
    STEP_KEY_INTERVIEW,
    STEP_KEY_ROLE_TASKS,
    STEP_KEY_SKILLS,
)
from question_limits import (
    _question_is_adaptive_essential,
    compute_adaptive_question_limits,
    select_questions_for_step_scope_from_plan,
)
from question_plan_compiler import _clone_question, compile_question_plan
from question_packs import QUESTION_PACK_REGISTRY
from question_packs.types import (
    QuestionPackDataError,
    load_question_pack_from_json,
)
from schemas import (
    JobAdExtract,
    OccupationContextProfile,
    OccupationQuestionConcept,
    OccupationQuestionContext,
    Question,
    QuestionPlan,
    QuestionStep,
    RelevanceLevel,
)
from occupation_context import classify_occupation_context


_EXPECTED_COMPANY_METADATA = {
    "ctx_company_employer_pitch": (
        [QUESTION_IMPACT_TARGET_BRIEF, QUESTION_IMPACT_TARGET_EXPORT],
        "medium",
        0.86,
    ),
    "ctx_company_business_unit": (
        [
            QUESTION_IMPACT_TARGET_BRIEF,
            QUESTION_IMPACT_TARGET_SALARY,
            QUESTION_IMPACT_TARGET_EXPORT,
        ],
        "low",
        0.78,
    ),
    "ctx_company_hiring_reason": (
        [QUESTION_IMPACT_TARGET_BRIEF, QUESTION_IMPACT_TARGET_INTERVIEW],
        "low",
        None,
    ),
    "ctx_company_growth_context": (
        [QUESTION_IMPACT_TARGET_BRIEF, QUESTION_IMPACT_TARGET_SALARY],
        "medium",
        None,
    ),
    "ctx_company_role_business_impact": (
        [QUESTION_IMPACT_TARGET_BRIEF, QUESTION_IMPACT_TARGET_INTERVIEW],
        "medium",
        None,
    ),
    "ctx_company_role_positioning": (
        [QUESTION_IMPACT_TARGET_BRIEF, QUESTION_IMPACT_TARGET_EXPORT],
        "low",
        None,
    ),
    "ctx_team_name": (
        [
            QUESTION_IMPACT_TARGET_BRIEF,
            QUESTION_IMPACT_TARGET_INTERVIEW,
            QUESTION_IMPACT_TARGET_EXPORT,
        ],
        "low",
        0.76,
    ),
    "ctx_team_leadership_scope": (
        [
            QUESTION_IMPACT_TARGET_BRIEF,
            QUESTION_IMPACT_TARGET_SALARY,
            QUESTION_IMPACT_TARGET_INTERVIEW,
            QUESTION_IMPACT_TARGET_EXPORT,
        ],
        "low",
        0.88,
    ),
    "ctx_team_size_direct": (
        [QUESTION_IMPACT_TARGET_BRIEF, QUESTION_IMPACT_TARGET_SALARY],
        "low",
        None,
    ),
    "ctx_team_stakeholders_primary": (
        [
            QUESTION_IMPACT_TARGET_BRIEF,
            QUESTION_IMPACT_TARGET_INTERVIEW,
            QUESTION_IMPACT_TARGET_EXPORT,
        ],
        "low",
        0.80,
    ),
    "ctx_team_success_context_90d": (
        [QUESTION_IMPACT_TARGET_BRIEF, QUESTION_IMPACT_TARGET_INTERVIEW],
        "medium",
        None,
    ),
    "ctx_hiring_growth_context": (
        [QUESTION_IMPACT_TARGET_BRIEF, QUESTION_IMPACT_TARGET_SALARY],
        "medium",
        0.66,
    ),
    "ctx_confidential_external_narrative": (
        [QUESTION_IMPACT_TARGET_BRIEF, QUESTION_IMPACT_TARGET_EXPORT],
        "medium",
        0.82,
    ),
    "ctx_low_maturity_role_assumptions": (
        [
            QUESTION_IMPACT_TARGET_BRIEF,
            QUESTION_IMPACT_TARGET_INTERVIEW,
            QUESTION_IMPACT_TARGET_EXPORT,
        ],
        "medium",
        0.84,
    ),
    "ctx_leadership_reporting_detail": (
        [
            QUESTION_IMPACT_TARGET_BRIEF,
            QUESTION_IMPACT_TARGET_SALARY,
            QUESTION_IMPACT_TARGET_INTERVIEW,
            QUESTION_IMPACT_TARGET_EXPORT,
        ],
        "medium",
        0.88,
    ),
}

_EXPECTED_ROLE_WORK_CONTEXT_METADATA = {
    "ctx_company_work_arrangement": (
        [
            QUESTION_IMPACT_TARGET_BRIEF,
            QUESTION_IMPACT_TARGET_SALARY,
            QUESTION_IMPACT_TARGET_EXPORT,
        ],
        "low",
        0.90,
    ),
    "ctx_company_language_internal": (
        [QUESTION_IMPACT_TARGET_SKILLS, QUESTION_IMPACT_TARGET_INTERVIEW],
        "low",
        None,
    ),
    "ctx_company_language_external": (
        [QUESTION_IMPACT_TARGET_SKILLS, QUESTION_IMPACT_TARGET_EXPORT],
        "low",
        None,
    ),
    "ctx_company_non_negotiables": (
        [
            QUESTION_IMPACT_TARGET_BRIEF,
            QUESTION_IMPACT_TARGET_SALARY,
            QUESTION_IMPACT_TARGET_SKILLS,
            QUESTION_IMPACT_TARGET_EXPORT,
        ],
        "medium",
        0.88,
    ),
    "ctx_remote_geography": (
        [
            QUESTION_IMPACT_TARGET_BRIEF,
            QUESTION_IMPACT_TARGET_SALARY,
            QUESTION_IMPACT_TARGET_EXPORT,
        ],
        "low",
        0.86,
    ),
    "ctx_company_allowed_regions_timezones": (
        [
            QUESTION_IMPACT_TARGET_BRIEF,
            QUESTION_IMPACT_TARGET_SALARY,
            QUESTION_IMPACT_TARGET_EXPORT,
        ],
        "low",
        0.86,
    ),
}

_EXPECTED_INTERVIEW_JSON_PACK_FIELDS = {
    "ctx_interview_evidence": {
        "label": (
            "Welche Nachweise oder Arbeitsproben sollen im Interview bewertet werden?"
        ),
        "answer_type": AnswerType.LONG_TEXT,
        "required": False,
        "target_path": "recruitment_steps",
        "fact_key": FactKey.INTERVIEW_RECRUITMENT_STEPS.value,
        "priority": "core",
        "group_key": "assessment",
        "impact_targets": [
            QUESTION_IMPACT_TARGET_SKILLS,
            QUESTION_IMPACT_TARGET_INTERVIEW,
            QUESTION_IMPACT_TARGET_EXPORT,
        ],
        "acquisition_cost": "medium",
        "info_gain_score": 0.82,
    },
    "ctx_interview_stages": {
        "label": "Welche Interviewstufen gibt es und welches Ziel hat jede Stufe?",
        "answer_type": AnswerType.LONG_TEXT,
        "required": True,
        "target_path": FactKey.INTERVIEW_RECRUITMENT_STEPS.value,
        "fact_key": FactKey.INTERVIEW_RECRUITMENT_STEPS.value,
        "priority": "core",
        "group_key": "stage_evaluation",
        "impact_targets": [
            QUESTION_IMPACT_TARGET_BRIEF,
            QUESTION_IMPACT_TARGET_INTERVIEW,
            QUESTION_IMPACT_TARGET_EXPORT,
        ],
        "acquisition_cost": "medium",
        "info_gain_score": 0.86,
    },
    "ctx_interview_stage_owners": {
        "label": "Wer ist Owner und Entscheider pro Interviewstufe?",
        "answer_type": AnswerType.LONG_TEXT,
        "required": True,
        "target_path": FactKey.INTERVIEW_STAGE_OWNERS.value,
        "fact_key": FactKey.INTERVIEW_STAGE_OWNERS.value,
        "priority": "core",
        "group_key": "stage_evaluation",
        "impact_targets": [
            QUESTION_IMPACT_TARGET_INTERVIEW,
            QUESTION_IMPACT_TARGET_EXPORT,
        ],
        "acquisition_cost": "low",
        "info_gain_score": 0.78,
    },
    "ctx_interview_scorecard_template": {
        "label": "Welche Scorecard oder Bewertungsskala nutzen wir je Stufe?",
        "answer_type": AnswerType.LONG_TEXT,
        "required": True,
        "target_path": FactKey.INTERVIEW_SCORECARD_TEMPLATE.value,
        "fact_key": FactKey.INTERVIEW_SCORECARD_TEMPLATE.value,
        "priority": "core",
        "group_key": "stage_evaluation",
        "impact_targets": [
            QUESTION_IMPACT_TARGET_SKILLS,
            QUESTION_IMPACT_TARGET_INTERVIEW,
            QUESTION_IMPACT_TARGET_EXPORT,
        ],
        "acquisition_cost": "medium",
        "info_gain_score": 0.86,
    },
    "ctx_interview_core_questions": {
        "label": "Welche Fragen sind für alle Kandidat:innen identisch?",
        "answer_type": AnswerType.MULTI_SELECT,
        "required": True,
        "target_path": FactKey.INTERVIEW_CORE_QUESTIONS.value,
        "fact_key": FactKey.INTERVIEW_CORE_QUESTIONS.value,
        "priority": "core",
        "group_key": "stage_evaluation",
        "impact_targets": [
            QUESTION_IMPACT_TARGET_SKILLS,
            QUESTION_IMPACT_TARGET_INTERVIEW,
            QUESTION_IMPACT_TARGET_EXPORT,
        ],
        "acquisition_cost": "medium",
        "info_gain_score": 0.82,
        "options": [
            "Motivation und Wechselgrund",
            "relevante Praxiserfahrung",
            "kritische Situation",
            "Zusammenarbeit",
            "fachlicher Deep Dive",
            "Arbeitsprobe",
            "Sonstiges",
        ],
    },
    "ctx_interview_communication_sla": {
        "label": "Welches Update-SLA gilt für Kandidat:innen nach jeder Stufe?",
        "answer_type": AnswerType.LONG_TEXT,
        "required": True,
        "target_path": FactKey.INTERVIEW_COMMUNICATION_SLA.value,
        "fact_key": FactKey.INTERVIEW_COMMUNICATION_SLA.value,
        "priority": "core",
        "group_key": "candidate_communication",
        "impact_targets": [
            QUESTION_IMPACT_TARGET_BRIEF,
            QUESTION_IMPACT_TARGET_INTERVIEW,
            QUESTION_IMPACT_TARGET_EXPORT,
        ],
        "acquisition_cost": "low",
        "info_gain_score": 0.80,
    },
    "ctx_interview_compliance_notes": {
        "label": (
            "Welche Datenschutz- oder Dokumentationspflichten gelten im Auswahlprozess?"
        ),
        "answer_type": AnswerType.LONG_TEXT,
        "required": False,
        "target_path": FactKey.INTERVIEW_COMPLIANCE_NOTES.value,
        "fact_key": FactKey.INTERVIEW_COMPLIANCE_NOTES.value,
        "priority": "detail",
        "group_key": "process_compliance",
        "impact_targets": [
            QUESTION_IMPACT_TARGET_INTERVIEW,
            QUESTION_IMPACT_TARGET_EXPORT,
        ],
        "acquisition_cost": "high",
        "info_gain_score": None,
    },
}

_EXPECTED_INTERVIEW_PACK_ENTRY_ORDER = tuple(_EXPECTED_INTERVIEW_JSON_PACK_FIELDS)


def test_clone_question_normalizes_stale_answer_type_enum_without_warning() -> None:
    class ReloadedAnswerType(str, Enum):
        NUMBER = AnswerType.NUMBER.value

    stale_question = Question.model_construct(
        id="ctx_stale_number",
        label="How many?",
        answer_type=ReloadedAnswerType.NUMBER,
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        cloned = _clone_question(stale_question)

    assert cloned.answer_type == AnswerType.NUMBER
    assert not any(
        "Pydantic serializer warnings" in str(item.message) for item in caught
    )


def _question(question_id: str, label: str) -> Question:
    return Question(
        id=question_id,
        label=label,
        answer_type=AnswerType.SHORT_TEXT,
        priority="standard",
        group_key="base",
    )


def _company_registry_questions() -> dict[str, Question]:
    return _registry_questions_for_step(STEP_KEY_COMPANY)


def _registry_questions_for_step(step_key: str) -> dict[str, Question]:
    questions: dict[str, Question] = {}
    for pack in QUESTION_PACK_REGISTRY.values():
        for entry in pack.entries:
            if entry.step_key != step_key:
                continue
            assert entry.question.id not in questions
            questions[entry.question.id] = entry.question
    return questions


def _synthetic_question_pack_payload() -> dict[str, object]:
    return {
        "pack_key": "test.synthetic",
        "description": "Synthetic question pack for loader validation.",
        "entries": [
            {
                "step_key": STEP_KEY_COMPANY,
                "question": {
                    "id": "ctx_loader_first",
                    "label": "Welche synthetische Information fehlt?",
                    "answer_type": AnswerType.SHORT_TEXT.value,
                    "target_path": FactKey.COMPANY_EMPLOYER_PITCH.value,
                    "fact_key": FactKey.COMPANY_EMPLOYER_PITCH.value,
                    "rationale": "Validates JSON question pack loading.",
                    "priority": "standard",
                    "group_key": "company_profile",
                    "impact_targets": [QUESTION_IMPACT_TARGET_BRIEF],
                    "acquisition_cost": "low",
                },
            },
            {
                "step_key": STEP_KEY_COMPANY,
                "question": {
                    "id": "ctx_loader_second",
                    "label": "Welche zweite synthetische Information fehlt?",
                    "answer_type": AnswerType.LONG_TEXT.value,
                    "target_path": FactKey.COMPANY_GROWTH_CONTEXT.value,
                    "fact_key": FactKey.COMPANY_GROWTH_CONTEXT.value,
                    "rationale": "Validates deterministic JSON entry ordering.",
                    "priority": "detail",
                    "group_key": "business_context",
                    "impact_targets": [QUESTION_IMPACT_TARGET_EXPORT],
                    "acquisition_cost": "medium",
                },
            },
        ],
    }


def _write_question_pack_json(tmp_path: Path, payload: object) -> Path:
    path = tmp_path / "pack.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_json_loaded_interview_pack_preserves_legacy_fields() -> None:
    pack = QUESTION_PACK_REGISTRY["base.interview"]

    assert pack.pack_key == "base.interview"
    assert pack.description == "Baseline interview evidence collection."
    assert tuple(entry.question.id for entry in pack.entries) == (
        _EXPECTED_INTERVIEW_PACK_ENTRY_ORDER
    )

    for entry in pack.entries:
        assert entry.step_key == STEP_KEY_INTERVIEW
        question = entry.question
        expected = _EXPECTED_INTERVIEW_JSON_PACK_FIELDS[question.id]

        for field_name, expected_value in expected.items():
            assert getattr(question, field_name) == expected_value
        assert question.rationale and question.rationale.strip()


def test_json_loaded_interview_pack_compiles_like_legacy_pack() -> None:
    compiled = compile_question_plan(
        base_plan=QuestionPlan(steps=[]),
        profile=OccupationContextProfile(
            pack_keys=["base.interview"],
            confidence=0.0,
        ),
    )
    interview_step = next(
        step for step in compiled.plan.steps if step.step_key == STEP_KEY_INTERVIEW
    )
    questions = {question.id: question for question in interview_step.questions}

    assert compiled.provenance.selected_pack_keys == ["base.interview"]
    assert tuple(compiled.provenance.injected_question_ids) == (
        _EXPECTED_INTERVIEW_PACK_ENTRY_ORDER
    )
    assert [question.id for question in interview_step.questions] == [
        "ctx_interview_evidence",
        "ctx_interview_communication_sla",
        "ctx_interview_core_questions",
        "ctx_interview_scorecard_template",
        "ctx_interview_stage_owners",
        "ctx_interview_stages",
        "ctx_interview_compliance_notes",
    ]
    assert questions["ctx_interview_stage_owners"].answer_type is AnswerType.NUMBER
    assert questions["ctx_interview_stage_owners"].min_value == 0.0
    assert questions["ctx_interview_stage_owners"].max_value == 7.0
    assert questions["ctx_interview_stages"].answer_type is AnswerType.NUMBER
    assert questions["ctx_interview_core_questions"].options == [
        "Motivation und Wechselgrund",
        "relevante Praxiserfahrung",
        "kritische Situation",
        "Zusammenarbeit",
        "fachlicher Deep Dive",
        "Arbeitsprobe",
        "Sonstiges",
    ]


def test_question_pack_json_loader_preserves_entry_order(tmp_path: Path) -> None:
    path = _write_question_pack_json(tmp_path, _synthetic_question_pack_payload())

    pack = load_question_pack_from_json(
        path,
        expected_pack_key="test.synthetic",
    )

    assert tuple(entry.question.id for entry in pack.entries) == (
        "ctx_loader_first",
        "ctx_loader_second",
    )


def test_question_pack_json_loader_rejects_missing_required_fields(
    tmp_path: Path,
) -> None:
    path = _write_question_pack_json(tmp_path, {"description": "Incomplete pack."})

    with pytest.raises(QuestionPackDataError, match="pack_key"):
        load_question_pack_from_json(path)


def test_question_pack_json_loader_rejects_duplicate_question_ids(
    tmp_path: Path,
) -> None:
    payload = _synthetic_question_pack_payload()
    entries = payload["entries"]
    assert isinstance(entries, list)
    assert isinstance(entries[1], dict)
    question = entries[1]["question"]
    assert isinstance(question, dict)
    question["id"] = "ctx_loader_first"
    path = _write_question_pack_json(tmp_path, payload)

    with pytest.raises(QuestionPackDataError, match="duplicates 'ctx_loader_first'"):
        load_question_pack_from_json(path)


def test_question_pack_json_loader_rejects_noncanonical_metadata(
    tmp_path: Path,
) -> None:
    payload = _synthetic_question_pack_payload()
    entries = payload["entries"]
    assert isinstance(entries, list)
    assert isinstance(entries[0], dict)
    question = entries[0]["question"]
    assert isinstance(question, dict)
    question["fact_key"] = "company.not_canonical"
    path = _write_question_pack_json(tmp_path, payload)

    with pytest.raises(QuestionPackDataError, match="fact_key is not canonical"):
        load_question_pack_from_json(path)


def test_company_pack_entries_have_adaptive_metadata() -> None:
    questions = _company_registry_questions()
    canonical_targets = set(QUESTION_IMPACT_TARGETS)

    assert set(questions) == set(_EXPECTED_COMPANY_METADATA)
    for question_id, (
        expected_targets,
        expected_cost,
        expected_score,
    ) in _EXPECTED_COMPANY_METADATA.items():
        question = questions[question_id]

        assert question.rationale and question.rationale.strip()
        assert question.impact_targets == expected_targets
        assert set(question.impact_targets) <= canonical_targets
        assert question.acquisition_cost == expected_cost
        assert question.info_gain_score == expected_score

        if question.priority == "core":
            assert question.info_gain_score is not None
        else:
            assert question.priority == "standard"
            if question.info_gain_score is None:
                assert not _question_is_adaptive_essential(question)


def test_role_tasks_pack_contains_moved_work_context_questions() -> None:
    questions = _registry_questions_for_step(STEP_KEY_ROLE_TASKS)
    canonical_targets = set(QUESTION_IMPACT_TARGETS)

    for question_id, (
        expected_targets,
        expected_cost,
        expected_score,
    ) in _EXPECTED_ROLE_WORK_CONTEXT_METADATA.items():
        question = questions[question_id]

        assert question.rationale and question.rationale.strip()
        assert question.impact_targets == expected_targets
        assert set(question.impact_targets) <= canonical_targets
        assert question.acquisition_cost == expected_cost
        assert question.info_gain_score == expected_score


def test_registry_pack_entries_have_priority_metadata_contract() -> None:
    canonical_targets = set(QUESTION_IMPACT_TARGETS)

    for pack in QUESTION_PACK_REGISTRY.values():
        for entry in pack.entries:
            question = entry.question

            assert question.group_key
            assert question.rationale and question.rationale.strip()
            assert question.impact_targets
            assert set(question.impact_targets) <= canonical_targets
            assert question.acquisition_cost in {"low", "medium", "high"}

            if question.priority == "core":
                assert question.info_gain_score is not None
                assert 0.0 <= question.info_gain_score <= 1.0
                assert _question_is_adaptive_essential(question)


def test_compiler_injects_selected_digital_product_packs() -> None:
    profile = classify_occupation_context(
        job=JobAdExtract(job_title="Software Developer", remote_policy="Remote")
    )
    base_plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="role_tasks",
                title_de="Rolle",
                questions=[_question("base_role", "Was sind die Hauptaufgaben?")],
            )
        ]
    )

    compiled = compile_question_plan(base_plan=base_plan, profile=profile)
    question_ids = [q.id for step in compiled.plan.steps for q in step.questions]

    assert "base_role" in question_ids
    assert "ctx_digital_ownership" in question_ids
    assert "ctx_tech_stack_must" in question_ids
    assert "ctx_remote_geography" in question_ids
    fact_by_question_id = {
        q.id: q.fact_key for step in compiled.plan.steps for q in step.questions
    }
    assert fact_by_question_id["ctx_digital_ownership"] == (
        FactKey.ROLE_RESPONSIBILITIES.value
    )
    assert fact_by_question_id["ctx_tech_stack_must"] == FactKey.ROLE_TECH_STACK.value
    assert fact_by_question_id["ctx_remote_geography"] == (
        FactKey.COMPANY_REMOTE_POLICY.value
    )
    assert "family.digital_product" in compiled.provenance.selected_pack_keys
    assert compiled.provenance.base_question_count == 1
    assert compiled.provenance.compiled_question_count > 1


def test_compiler_suppresses_irrelevant_driving_question_for_digital_role() -> None:
    profile = classify_occupation_context(
        job=JobAdExtract(job_title="Software Developer", remote_policy="Remote")
    )
    base_plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="skills",
                title_de="Skills",
                questions=[
                    _question("driving_license", "Welche Führerscheinklasse ist nötig?")
                ],
            )
        ]
    )

    compiled = compile_question_plan(base_plan=base_plan, profile=profile)
    question_ids = [q.id for step in compiled.plan.steps for q in step.questions]

    assert "driving_license" not in question_ids
    assert compiled.provenance.suppressed_question_ids == ["driving_license"]


def test_compiler_demotes_irrelevant_question_when_confidence_is_low() -> None:
    profile = classify_occupation_context(job=JobAdExtract(job_title="Software"))
    profile.confidence = 0.5
    profile.driving_relevance = RelevanceLevel.IRRELEVANT
    base_plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="skills",
                title_de="Skills",
                questions=[
                    _question("driving_license", "Welche Führerscheinklasse ist nötig?")
                ],
            )
        ]
    )

    compiled = compile_question_plan(base_plan=base_plan, profile=profile)
    questions = [q for step in compiled.plan.steps for q in step.questions]
    demoted = next(q for q in questions if q.id == "driving_license")

    assert demoted.priority == "detail"
    assert compiled.provenance.demoted_question_ids == ["driving_license"]


def test_compiler_injects_skill_group_pack_and_esco_concept_questions() -> None:
    profile = classify_occupation_context(job=JobAdExtract(job_title="Data Engineer"))
    context = OccupationQuestionContext(
        occupation_uri="uri:occupation:data-engineer",
        preferred_label="Data engineer",
        isco_code="2511",
        nace_codes=["J62"],
        regulated_profession=True,
        skill_groups=["digital_data_ai"],
        essential_skills=[
            OccupationQuestionConcept(
                uri="uri:skill:python",
                label="Python",
                concept_type="skill",
                relation="essential",
                skill_group="digital_data_ai",
                reuse_level="occupation-specific",
            )
        ],
    )
    base_plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="skills",
                title_de="Skills",
                questions=[_question("base_skill", "Welche Skills fehlen?")],
            )
        ]
    )

    compiled = compile_question_plan(
        base_plan=base_plan,
        profile=profile,
        question_context=context,
        ui_mode="standard",
    )
    questions = {q.id: q for step in compiled.plan.steps for q in step.questions}
    question_ids = list(questions)
    esco_question_ids = [
        question_id
        for question_id in question_ids
        if question_id.startswith("ctx_esco_essential_skill_")
    ]

    assert len(question_ids) == len(set(question_ids))
    assert "ctx_sg_digital_data_ai" in question_ids
    assert "ctx_regulated_requirements" in question_ids
    assert len(esco_question_ids) == 1
    assert questions["base_skill"].group_key == "application_context"
    assert questions["ctx_sg_digital_data_ai"].group_key == "digital_data_ai"
    assert questions["ctx_regulated_requirements"].group_key == "licenses"
    assert questions[esco_question_ids[0]].group_key == "digital_data_ai"
    assert questions[esco_question_ids[0]].priority == "core"
    assert "SKILL_GROUP:digital_data_ai" in compiled.provenance.resolved_module_keys
    assert "ISCO4:2511" in compiled.provenance.resolved_module_keys
    assert compiled.provenance.source_uris_by_question_id[esco_question_ids[0]] == [
        "uri:skill:python"
    ]


def test_compiler_keeps_esco_concept_candidates_independent_of_ui_mode() -> None:
    profile = classify_occupation_context(job=JobAdExtract(job_title="Data Engineer"))
    context = OccupationQuestionContext(
        occupation_uri="uri:occupation:data-engineer",
        preferred_label="Data engineer",
        essential_skills=[
            OccupationQuestionConcept(
                uri=f"uri:skill:{index}",
                label=f"Skill {index}",
                concept_type="skill",
                relation="essential",
            )
            for index in range(5)
        ],
    )

    compiled = compile_question_plan(
        base_plan=QuestionPlan(steps=[]),
        profile=profile,
        question_context=context,
        ui_mode="quick",
    )
    esco_questions = [
        q
        for step in compiled.plan.steps
        for q in step.questions
        if q.id.startswith("ctx_esco_")
    ]

    assert len(esco_questions) == 5


def test_compiler_injects_routing_facet_questions() -> None:
    profile = classify_occupation_context(
        job=JobAdExtract(job_title="Operations Lead", contract_type="freelance"),
        answers={
            FactKey.INTAKE_HIRING_REASON.value: "replacement",
            FactKey.INTAKE_URGENCY.value: "high",
            FactKey.INTAKE_HIRING_VOLUME.value: 2,
            FactKey.INTAKE_SEARCH_CONFIDENTIALITY.value: "high",
            FactKey.INTAKE_ROLE_DEFINITION_MATURITY.value: "low",
            FactKey.TEAM_LEADERSHIP_SCOPE.value: "fachliche_fuehrung",
            FactKey.COMPANY_WORK_ARRANGEMENT.value: "remote_cross_border",
        },
    )

    compiled = compile_question_plan(base_plan=QuestionPlan(steps=[]), profile=profile)
    questions = {q.id: q for step in compiled.plan.steps for q in step.questions}

    assert "ctx_hiring_replacement_gap" in questions
    assert "ctx_interview_urgency_tradeoffs" in questions
    assert "ctx_confidential_external_narrative" in questions
    assert "ctx_multi_hire_calibration" in questions
    assert "ctx_low_maturity_role_assumptions" in questions
    assert "ctx_leadership_reporting_detail" in questions
    assert "ctx_contract_constraints" in questions
    assert "ctx_company_allowed_regions_timezones" in questions
    assert questions["ctx_company_allowed_regions_timezones"].fact_key == (
        FactKey.COMPANY_ALLOWED_REGIONS_TIMEZONES.value
    )
    assert "facet.international_context" in compiled.provenance.selected_pack_keys


def test_context_heavy_standard_scope_prioritizes_company_metadata() -> None:
    answers = {
        FactKey.INTAKE_HIRING_REASON.value: "replacement",
        FactKey.INTAKE_URGENCY.value: "high",
        FactKey.INTAKE_HIRING_VOLUME.value: 3,
        FactKey.INTAKE_SEARCH_CONFIDENTIALITY.value: "high",
        FactKey.INTAKE_ROLE_DEFINITION_MATURITY.value: "low",
        FactKey.TEAM_LEADERSHIP_SCOPE.value: "disziplinarische_fuehrung",
        FactKey.COMPANY_WORK_ARRANGEMENT.value: "remote_cross_border",
    }
    intake_facts = {
        FactKey.TEAM_LEADERSHIP_SCOPE.value: "disziplinarische_fuehrung",
        FactKey.COMPANY_WORK_ARRANGEMENT.value: "remote_cross_border",
        FactKey.COMPANY_REMOTE_POLICY.value: "remote_cross_border",
    }
    profile = classify_occupation_context(
        job=JobAdExtract(
            job_title="Operations Lead",
            contract_type="freelance",
            remote_policy="remote_cross_border",
        ),
        answers=answers,
    )
    compiled = compile_question_plan(base_plan=QuestionPlan(steps=[]), profile=profile)

    limits = compute_adaptive_question_limits(
        plan=compiled.plan,
        ui_mode="standard",
        answers=answers,
        answer_meta={},
        job_extract=None,
        intake_facts=intake_facts,
    )
    selected = select_questions_for_step_scope_from_plan(
        compiled.plan,
        STEP_KEY_COMPANY,
        question_limits=limits,
        answers=answers,
        answer_meta={},
        job_extract=None,
        intake_facts=intake_facts,
    )
    selected_ids = [question.id for question in selected]

    assert len(selected_ids) == limits[STEP_KEY_COMPANY]["limit"]
    assert "ctx_leadership_reporting_detail" in selected_ids
    assert "ctx_low_maturity_role_assumptions" in selected_ids
    assert "ctx_confidential_external_narrative" in selected_ids
    assert "ctx_company_role_business_impact" not in selected_ids


def test_skills_heavy_standard_scope_prioritizes_skill_metadata_and_expert_depth() -> None:
    profile = classify_occupation_context(
        job=JobAdExtract(
            job_title="Senior Data Engineer",
            remote_policy="Remote",
            tech_stack=["Python", "SQL"],
        )
    )
    context = OccupationQuestionContext(
        occupation_uri="uri:occupation:data-engineer",
        preferred_label="Data engineer",
        regulated_profession=True,
        skill_groups=[
            ESCO_QUESTION_SKILL_GROUP_DIGITAL_DATA_AI,
            ESCO_QUESTION_SKILL_GROUP_TOOLS_METHODS,
            ESCO_QUESTION_SKILL_GROUP_REGULATION_SAFETY,
        ],
        essential_skills=[
            OccupationQuestionConcept(
                uri="uri:skill:python",
                label="Python",
                concept_type="skill",
                relation="essential",
                skill_group=ESCO_QUESTION_SKILL_GROUP_DIGITAL_DATA_AI,
                reuse_level="occupation-specific",
            )
        ],
    )
    compiled = compile_question_plan(
        base_plan=QuestionPlan(steps=[]),
        profile=profile,
        question_context=context,
        ui_mode="standard",
    )

    standard_limits = compute_adaptive_question_limits(
        plan=compiled.plan,
        ui_mode="standard",
        answers={},
        answer_meta={},
        job_extract=None,
    )
    standard_selected = select_questions_for_step_scope_from_plan(
        compiled.plan,
        STEP_KEY_SKILLS,
        question_limits=standard_limits,
        answers={},
        answer_meta={},
        job_extract=None,
    )
    standard_ids = [question.id for question in standard_selected]

    assert len(standard_ids) == standard_limits[STEP_KEY_SKILLS]["limit"]
    assert "ctx_tech_stack_must" in standard_ids
    assert "ctx_regulated_requirements" in standard_ids
    assert "ctx_sg_digital_data_ai" not in standard_ids
    assert "ctx_skills_free_text_reason" not in standard_ids

    expert_limits = compute_adaptive_question_limits(
        plan=compiled.plan,
        ui_mode="expert",
        answers={},
        answer_meta={},
        job_extract=None,
    )
    expert_selected = select_questions_for_step_scope_from_plan(
        compiled.plan,
        STEP_KEY_SKILLS,
        question_limits=expert_limits,
        answers={},
        answer_meta={},
        job_extract=None,
    )
    skills_step = next(
        step for step in compiled.plan.steps if step.step_key == STEP_KEY_SKILLS
    )

    assert len(expert_selected) == len(skills_step.questions)
    expert_ids = [question.id for question in expert_selected]
    assert "ctx_sg_digital_data_ai" in expert_ids
    assert "ctx_skills_free_text_reason" in expert_ids
