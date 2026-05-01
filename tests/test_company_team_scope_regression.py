from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
import sys

from constants import AnswerType, SSKey
from schemas import Question, QuestionPlan, QuestionStep
import ui_components

ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = ROOT / "wizard_pages" / "base.py"
SPEC = spec_from_file_location("wizard_pages.base_scope_regression", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load base module")
BASE_MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = BASE_MODULE
SPEC.loader.exec_module(BASE_MODULE)  # type: ignore[attr-defined]


def _noop_render(_: object) -> None:
    return None


def test_company_scope_excludes_team_questions_and_keeps_progress_denominator(monkeypatch) -> None:
    company_questions = [
        Question(
            id="company_name",
            label="Unternehmensname",
            answer_type=AnswerType.SHORT_TEXT,
            required=True,
        ),
        Question(
            id="company_website",
            label="Website",
            answer_type=AnswerType.SHORT_TEXT,
            required=False,
        ),
    ]
    team_question = Question(
        id="team_size",
        label="Teamgröße",
        answer_type=AnswerType.SHORT_TEXT,
        required=True,
    )
    company_step = QuestionStep(
        step_key="company",
        title_de="Company",
        questions=company_questions,
    )
    plan = QuestionPlan(steps=[company_step, QuestionStep(step_key="team", title_de="Team", questions=[team_question])])

    answers = {
        "company_name": "Acme GmbH",
        "team_size": "12",  # must not affect company progress/review
    }
    answer_meta: dict[str, object] = {}

    monkeypatch.setattr(
        BASE_MODULE,
        "st",
        SimpleNamespace(
            session_state={
                SSKey.QUESTION_PLAN.value: plan.model_dump(mode="json"),
                SSKey.ANSWERS.value: answers,
                SSKey.ANSWER_META.value: answer_meta,
                SSKey.JOB_EXTRACT.value: None,
                SSKey.BRIEF.value: None,
            }
        ),
    )
    statuses = BASE_MODULE._compute_step_statuses(
        [BASE_MODULE.WizardPage(key="company", title_de="Company", icon="", render=_noop_render)]
    )

    monkeypatch.setattr(ui_components, "get_answers", lambda: answers)
    monkeypatch.setattr(ui_components, "get_answer_meta", lambda: answer_meta)
    review_payload = ui_components.build_step_review_payload(company_step)

    assert {question.id for question in review_payload["visible_questions"]} == {
        "company_name",
        "company_website",
    }
    assert "team_size" not in review_payload["answered_lookup"]

    assert statuses[0]["total"] == review_payload["step_status"]["total"]
    assert statuses[0]["answered"] == review_payload["step_status"]["answered"]
