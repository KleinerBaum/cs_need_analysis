from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
import sys

from constants import (
    AnswerType,
    FactKey,
    SSKey,
    STEP_KEY_COMPANY,
    STEP_KEY_INTRO,
    STEP_KEY_LANDING,
    STEP_KEY_SUMMARY,
)
from question_progress import build_step_scope_progress_labels
from schemas import JobAdExtract, Question, QuestionDependency, QuestionPlan, QuestionStep


BASE_PATH = Path(__file__).resolve().parents[1] / "wizard_pages" / "base.py"
SPEC = spec_from_file_location("wizard_pages.base_progress_for_tests", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load base module")
BASE_MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = BASE_MODULE
SPEC.loader.exec_module(BASE_MODULE)  # type: ignore[attr-defined]

UI_LAYOUT_PATH = Path(__file__).resolve().parents[1] / "ui_layout.py"
UI_LAYOUT_SPEC = spec_from_file_location("ui_layout_progress_for_tests", UI_LAYOUT_PATH)
if UI_LAYOUT_SPEC is None or UI_LAYOUT_SPEC.loader is None:
    raise RuntimeError("Could not load ui_layout module")
UI_LAYOUT_MODULE = module_from_spec(UI_LAYOUT_SPEC)
sys.modules[UI_LAYOUT_SPEC.name] = UI_LAYOUT_MODULE
UI_LAYOUT_SPEC.loader.exec_module(UI_LAYOUT_MODULE)  # type: ignore[attr-defined]


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


def test_sidebar_progress_counts_jobspec_covered_company_questions(monkeypatch) -> None:
    company_question = Question(
        id="company_q_name",
        label="Wie heißt das Unternehmen?",
        answer_type=AnswerType.SHORT_TEXT,
        required=True,
    )
    employment_question = Question(
        id="company_q_contract",
        label="Was ist die Art des Arbeitsvertrags?",
        answer_type=AnswerType.SHORT_TEXT,
        required=True,
    )
    city_question = Question(
        id="company_q_city",
        label="In welcher Stadt befindet sich das Unternehmen?",
        answer_type=AnswerType.SHORT_TEXT,
        required=True,
    )
    plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="company",
                title_de="Company",
                questions=[company_question, employment_question, city_question],
            )
        ]
    )
    monkeypatch.setattr(
        BASE_MODULE,
        "st",
        SimpleNamespace(
            session_state={
                SSKey.QUESTION_PLAN.value: plan.model_dump(mode="json"),
                SSKey.ANSWERS.value: {},
                SSKey.ANSWER_META.value: {},
                SSKey.JOB_EXTRACT.value: JobAdExtract(
                    company_name="Rheinbahn",
                    employment_type="Unbefristeter Arbeitsvertrag",
                ).model_dump(mode="json"),
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

    assert statuses[0]["answered"] == 2
    assert statuses[0]["total"] == 3
    assert statuses[0]["payload"]["missing_essential_ids"] == ["company_q_city"]


def test_sidebar_progress_uses_adaptive_selection_instead_of_prefix_slice(
    monkeypatch,
) -> None:
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
    plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="company",
                title_de="Company",
                questions=[covered_detail, uncovered_core],
            )
        ]
    )
    monkeypatch.setattr(
        BASE_MODULE,
        "st",
        SimpleNamespace(
            session_state={
                SSKey.QUESTION_PLAN.value: plan.model_dump(mode="json"),
                SSKey.QUESTION_LIMITS.value: {"company": 1},
                SSKey.ANSWERS.value: {},
                SSKey.ANSWER_META.value: {},
                SSKey.INTAKE_FACTS.value: {
                    FactKey.COMPANY_COMPANY_NAME.value: "Example GmbH"
                },
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

    assert statuses[0]["answered"] == 0
    assert statuses[0]["total"] == 1
    assert statuses[0]["payload"]["missing_essential_ids"] == ["uncovered_core"]


def test_intake_process_progress_starts_with_landing_and_marks_summary_from_brief(
    monkeypatch,
) -> None:
    company_question = Question(
        id="q_company",
        label="Company",
        answer_type=AnswerType.SHORT_TEXT,
        required=True,
    )
    plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="company",
                title_de="Company",
                questions=[company_question],
            )
        ]
    )
    rendered_items: list[list[dict[str, object]]] = []
    monkeypatch.setattr(
        UI_LAYOUT_MODULE,
        "st",
        SimpleNamespace(
            session_state={
                SSKey.QUESTION_PLAN.value: plan.model_dump(mode="json"),
                SSKey.QUESTION_LIMITS.value: {},
                SSKey.BRIEF.value: {"summary": "ok"},
            }
        ),
    )
    monkeypatch.setattr(UI_LAYOUT_MODULE, "get_answers", lambda: {"q_company": "Ja"})
    monkeypatch.setattr(UI_LAYOUT_MODULE, "get_answer_meta", lambda: {})
    monkeypatch.setattr(
        UI_LAYOUT_MODULE,
        "render_process_progress",
        lambda items: rendered_items.append(list(items)),
    )

    UI_LAYOUT_MODULE.render_intake_process_progress(STEP_KEY_SUMMARY)

    assert rendered_items
    items = rendered_items[0]
    assert [item["label"] for item in items][:3] == [
        "Start",
        "Unternehmen",
        "Rolle & Aufgaben",
    ]
    assert all(item["key"] != STEP_KEY_INTRO for item in items)
    assert items[0]["key"] == STEP_KEY_LANDING
    assert items[0]["href"] == "?wizard_step=landing"
    assert items[0]["step_index"] == 1
    assert items[0]["step_total"] == len(items)
    assert items[0]["status"] == "partial"
    assert items[0]["detail"] == "Quelle & Analyse"
    assert items[1]["key"] == STEP_KEY_COMPANY
    assert items[1]["step_index"] == 2
    assert items[1]["status"] == "complete"
    assert items[1]["count"] == "1/1"
    assert items[-1]["label"] == "Zusammenfassung"
    assert items[-1]["status"] == "complete"
    assert items[-1]["current"] is True

    rendered_items.clear()
    UI_LAYOUT_MODULE.render_intake_process_progress(STEP_KEY_INTRO)
    assert rendered_items == []


def test_intake_process_progress_uses_adaptive_selection_instead_of_prefix_slice(
    monkeypatch,
) -> None:
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
    plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="company",
                title_de="Company",
                questions=[covered_detail, uncovered_core],
            )
        ]
    )
    rendered_items: list[list[dict[str, object]]] = []
    monkeypatch.setattr(
        UI_LAYOUT_MODULE,
        "st",
        SimpleNamespace(
            session_state={
                SSKey.QUESTION_PLAN.value: plan.model_dump(mode="json"),
                SSKey.QUESTION_LIMITS.value: {"company": 1},
                SSKey.INTAKE_FACTS.value: {
                    FactKey.COMPANY_COMPANY_NAME.value: "Example GmbH"
                },
                SSKey.JOB_EXTRACT.value: None,
                SSKey.BRIEF.value: None,
            }
        ),
    )
    monkeypatch.setattr(UI_LAYOUT_MODULE, "get_answers", lambda: {})
    monkeypatch.setattr(UI_LAYOUT_MODULE, "get_answer_meta", lambda: {})
    monkeypatch.setattr(
        UI_LAYOUT_MODULE,
        "render_process_progress",
        lambda items: rendered_items.append(list(items)),
    )

    UI_LAYOUT_MODULE.render_intake_process_progress(STEP_KEY_SUMMARY)

    company_item = rendered_items[0][1]
    assert company_item["status"] == "not_started"
    assert company_item["count"] == "0/1"
    assert company_item["title"] == "Unternehmen: 0/1 beantwortet"


def test_sidebar_navigation_uses_navigation_only_labels(monkeypatch) -> None:
    captured_labels: list[str] = []

    class _FakeSidebar:
        def radio(
            self,
            _label: str,
            *,
            options: list[str],
            key: str,
            format_func,
            **_kwargs: object,
        ):
            del key
            captured_labels.extend(format_func(option) for option in options)
            return options[0]

    monkeypatch.setattr(
        BASE_MODULE,
        "st",
        SimpleNamespace(
            session_state={SSKey.CURRENT_STEP.value: STEP_KEY_INTRO},
            sidebar=_FakeSidebar(),
            rerun=lambda: None,
        ),
    )
    monkeypatch.setattr(BASE_MODULE, "_ensure_salary_forecast_state_defaults", lambda: None)
    monkeypatch.setattr(BASE_MODULE, "sync_adaptive_question_limits", lambda: None)
    monkeypatch.setattr(BASE_MODULE, "get_current_ui_mode", lambda: "standard")
    monkeypatch.setattr(
        BASE_MODULE,
        "normalize_ui_preferences",
        lambda value: value if isinstance(value, dict) else {},
    )
    monkeypatch.setattr(BASE_MODULE, "_compute_sidebar_salary_forecast", lambda **_: None)
    monkeypatch.setattr(BASE_MODULE, "_render_esco_warnings_and_migration_cta", lambda: None)
    pages = [
        BASE_MODULE.WizardPage(
            key=STEP_KEY_INTRO,
            title_de="Einleitung",
            icon="ℹ️",
            render=_noop_render,
        ),
        BASE_MODULE.WizardPage(
            key="company",
            title_de="Unternehmen",
            icon="🏢",
            render=_noop_render,
        ),
        BASE_MODULE.WizardPage(
            key="summary",
            title_de="Zusammenfassung",
            icon="✅",
            render=_noop_render,
        ),
    ]

    current_page = BASE_MODULE.sidebar_navigation(BASE_MODULE.WizardContext(pages=pages))

    assert captured_labels == ["🏢 Unternehmen", "✅ Zusammenfassung"]
    assert all("/" not in label for label in captured_labels)
    assert current_page.key == STEP_KEY_INTRO
