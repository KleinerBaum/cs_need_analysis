from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
import sys

from constants import AnswerType, FactKey, SSKey
from schemas import JobAdExtract, Question, QuestionPlan, QuestionStep
import ui_components

ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = ROOT / "wizard_pages" / "base.py"
COMPANY_PATH = ROOT / "wizard_pages" / "02_company.py"
SPEC = spec_from_file_location("wizard_pages.base_scope_regression", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load base module")
BASE_MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = BASE_MODULE
SPEC.loader.exec_module(BASE_MODULE)  # type: ignore[attr-defined]


def _load_company_module():
    spec = spec_from_file_location(
        "wizard_pages.company_question_dedupe_regression", COMPANY_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load company module")
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


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


def test_company_open_questions_filter_structured_fact_key_duplicates() -> None:
    company_module = _load_company_module()
    step = QuestionStep(
        step_key="company",
        title_de="Company",
        questions=[
            Question(
                id="ctx_team_size_direct",
                label="Wie groß ist das unmittelbare Team?",
                answer_type=AnswerType.NUMBER,
                fact_key=FactKey.TEAM_SIZE_DIRECT.value,
            ),
            Question(
                id="ctx_team_leadership_scope",
                label="Welche Führungsverantwortung hat die Rolle?",
                answer_type=AnswerType.SINGLE_SELECT,
                fact_key=FactKey.TEAM_LEADERSHIP_SCOPE.value,
            ),
            Question(
                id="ctx_company_work_arrangement",
                label="Welches Arbeitsmodell gilt für diese Rolle?",
                answer_type=AnswerType.SINGLE_SELECT,
                target_path=FactKey.COMPANY_WORK_ARRANGEMENT.value,
            ),
            Question(
                id="ctx_company_non_negotiables",
                label="Welche Rahmenbedingungen sind nicht verhandelbar?",
                answer_type=AnswerType.MULTI_SELECT,
                fact_key=FactKey.COMPANY_NON_NEGOTIABLES.value,
            ),
            Question(
                id="ctx_confidential_external_narrative",
                label="Welche Details sollen extern neutralisiert werden?",
                answer_type=AnswerType.LONG_TEXT,
                fact_key=FactKey.COMPANY_NON_NEGOTIABLES.value,
            ),
            Question(
                id="ctx_hiring_growth_context",
                label="Welcher Wachstumskontext macht die Rolle nötig?",
                answer_type=AnswerType.LONG_TEXT,
                fact_key=FactKey.COMPANY_GROWTH_CONTEXT.value,
            ),
            Question(
                id="ctx_same_label_distinct_fact",
                label="Wie groß ist das unmittelbare Team?",
                answer_type=AnswerType.LONG_TEXT,
                fact_key=FactKey.ROLE_ASSUMPTIONS.value,
            ),
        ],
    )

    filtered_step = company_module._filtered_company_open_question_step(step)

    assert filtered_step is not None
    assert [question.id for question in filtered_step.questions] == [
        "ctx_confidential_external_narrative",
        "ctx_same_label_distinct_fact",
    ]


def test_structured_company_facts_still_cover_original_step_review(monkeypatch) -> None:
    questions = [
        Question(
            id="ctx_team_size_direct",
            label="Wie groß ist das unmittelbare Team?",
            answer_type=AnswerType.NUMBER,
            fact_key=FactKey.TEAM_SIZE_DIRECT.value,
        ),
        Question(
            id="ctx_team_leadership_scope",
            label="Welche Führungsverantwortung hat die Rolle?",
            answer_type=AnswerType.SINGLE_SELECT,
            fact_key=FactKey.TEAM_LEADERSHIP_SCOPE.value,
        ),
        Question(
            id="ctx_company_work_arrangement",
            label="Welches Arbeitsmodell gilt für diese Rolle?",
            answer_type=AnswerType.SINGLE_SELECT,
            fact_key=FactKey.COMPANY_WORK_ARRANGEMENT.value,
        ),
        Question(
            id="ctx_company_non_negotiables",
            label="Welche Rahmenbedingungen sind nicht verhandelbar?",
            answer_type=AnswerType.MULTI_SELECT,
            fact_key=FactKey.COMPANY_NON_NEGOTIABLES.value,
        ),
    ]
    company_step = QuestionStep(
        step_key="company",
        title_de="Company",
        questions=questions,
    )
    intake_facts = {
        FactKey.TEAM_SIZE_DIRECT.value: 8,
        FactKey.TEAM_LEADERSHIP_SCOPE.value: "fachliche_fuehrung",
        FactKey.COMPANY_WORK_ARRANGEMENT.value: "hybrid",
        FactKey.COMPANY_NON_NEGOTIABLES.value: ["Standort"],
    }

    monkeypatch.setattr(ui_components, "get_answers", lambda: {})
    monkeypatch.setattr(ui_components, "get_answer_meta", lambda: {})
    monkeypatch.setattr(
        ui_components,
        "st",
        SimpleNamespace(
            session_state={
                SSKey.INTAKE_FACTS.value: intake_facts,
                SSKey.INTAKE_FACT_EVIDENCE.value: {},
                SSKey.UI_PREFERENCES.value: {},
                SSKey.JOB_EXTRACT.value: None,
            }
        ),
    )

    review_payload = ui_components.build_step_review_payload(company_step)

    assert review_payload["answered_lookup"] == {
        "ctx_team_size_direct": True,
        "ctx_team_leadership_scope": True,
        "ctx_company_work_arrangement": True,
        "ctx_company_non_negotiables": True,
    }
    assert review_payload["step_status"]["answered"] == 4


class _Context:
    def __enter__(self) -> "_Context":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class _CompanySectionStreamlit:
    def __init__(self) -> None:
        self.markdown_calls: list[str] = []

    def markdown(self, text: str, *_args: object, **_kwargs: object) -> None:
        self.markdown_calls.append(text)

    def text_area(self, *_args: object, **_kwargs: object) -> str:
        return ""


def test_company_context_renders_new_section_order(monkeypatch) -> None:
    company_module = _load_company_module()
    fake_st = _CompanySectionStreamlit()
    contexts = (_Context(), _Context(), _Context())

    monkeypatch.setattr(company_module, "st", fake_st)
    monkeypatch.setattr(company_module, "section_container", lambda **_kwargs: _Context())
    monkeypatch.setattr(
        company_module,
        "responsive_two_columns",
        lambda **_kwargs: contexts[:2],
    )
    monkeypatch.setattr(
        company_module,
        "responsive_three_columns",
        lambda **_kwargs: contexts,
    )
    monkeypatch.setattr(company_module, "render_text_fact", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(company_module, "render_text_area_fact", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(company_module, "render_multiselect_fact", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(company_module, "render_select_fact", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(company_module, "render_number_fact", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(company_module, "fact_value", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(company_module, "persist_fact", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        company_module,
        "render_role_context_enrichment",
        lambda **_kwargs: fake_st.markdown("#### Rollenprofil mit ESCO-Kontext ergänzen"),
    )
    monkeypatch.setattr(
        company_module,
        "_render_website_enrichment",
        lambda *_args, **_kwargs: fake_st.markdown("#### Website analysieren"),
    )

    company_module._render_company_research_and_esco(
        JobAdExtract(),
        ctx=SimpleNamespace(),
        plan=QuestionPlan(steps=[]),
    )
    company_module._render_company_context(JobAdExtract())
    company_module._render_team_context(JobAdExtract(), ctx=SimpleNamespace())

    assert fake_st.markdown_calls == [
        "#### Website analysieren",
        "#### Rollenprofil mit ESCO-Kontext ergänzen",
        "#### Arbeitgeberprofil",
        "#### Unternehmenskontext",
        "#### Team & Berichtslinie",
    ]
