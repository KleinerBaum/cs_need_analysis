from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
import sys

from constants import AnswerType, SSKey
from question_progress import build_step_scope_progress_labels
from schemas import Question, QuestionDependency, QuestionPlan, QuestionStep


BASE_PATH = Path(__file__).resolve().parents[1] / "wizard_pages" / "base.py"
SPEC = spec_from_file_location("wizard_pages.base_progress_for_tests", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load base module")
BASE_MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = BASE_MODULE
SPEC.loader.exec_module(BASE_MODULE)  # type: ignore[attr-defined]


def _noop_render(_: object) -> None:
    return None


def test_sidebar_progress_keeps_visible_scope_explicit_when_overall_differs(
    monkeypatch,
) -> None:
    core_question = Question(
        id="q_core",
        label="Core",
        answer_type=AnswerType.SHORT_TEXT,
        required=True,
        priority="core",
    )
    hidden_detail_1 = Question(
        id="q_detail_1",
        label="Detail 1",
        answer_type=AnswerType.SHORT_TEXT,
        priority="detail",
        depends_on=[
            QuestionDependency(question_id="q_core", equals="Nein"),
        ],
    )
    hidden_detail_2 = Question(
        id="q_detail_2",
        label="Detail 2",
        answer_type=AnswerType.SHORT_TEXT,
        priority="detail",
        depends_on=[
            QuestionDependency(question_id="q_core", equals="Nein"),
        ],
    )
    plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="company",
                title_de="Company",
                questions=[core_question, hidden_detail_1, hidden_detail_2],
            )
        ]
    )
    monkeypatch.setattr(
        BASE_MODULE,
        "st",
        SimpleNamespace(
            session_state={
                SSKey.QUESTION_PLAN.value: plan.model_dump(mode="json"),
                SSKey.ANSWERS.value: {"q_core": "Ja"},
                SSKey.ANSWER_META.value: {},
                SSKey.JOB_EXTRACT.value: None,
                SSKey.BRIEF.value: None,
            }
        ),
    )
    pages = [
        BASE_MODULE.WizardPage(
            key="company",
            title_de="Company",
            icon="",
            render=_noop_render,
        )
    ]

    statuses = BASE_MODULE._compute_step_statuses(pages)

    assert statuses[0]["answered"] == 1
    assert statuses[0]["total"] == 1
    assert statuses[0]["payload"]["overall_answered"] == 1
    assert statuses[0]["payload"]["overall_total"] == 3

    labels = build_step_scope_progress_labels(
        visible_answered=statuses[0]["answered"],
        visible_total=statuses[0]["total"],
        overall_answered=statuses[0]["payload"]["overall_answered"],
        overall_total=statuses[0]["payload"]["overall_total"],
    )
    assert labels["visible_label"].endswith("1/1")
    assert labels["overall_label"].endswith("1/3")
    assert labels["has_different_denominator"] is True
