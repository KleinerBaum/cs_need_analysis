from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal

from constants import SSKey


SUMMARY_PATH = Path(__file__).resolve().parents[1] / "wizard_pages" / "08_summary.py"
SPEC = spec_from_file_location("wizard_pages.page_08_summary_actions", SUMMARY_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load summary page module")
SUMMARY_MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(SUMMARY_MODULE)  # type: ignore[attr-defined]


class _NoopContext:
    def __enter__(self) -> "_NoopContext":
        return self

    def __exit__(self, *_: object) -> Literal[False]:
        return False


class _FakeStreamlit:
    def __init__(self, session_state: dict[str, Any], *, button_result: bool = False):
        self.session_state = session_state
        self.button_result = button_result
        self.warning_messages: list[str] = []
        self.last_button_kwargs: dict[str, Any] = {}

    def container(self, **_: Any) -> _NoopContext:
        return _NoopContext()

    def markdown(self, *_: Any, **__: Any) -> None:
        return None

    def caption(self, *_: Any, **__: Any) -> None:
        return None

    def write(self, *_: Any, **__: Any) -> None:
        return None

    def warning(self, message: str) -> None:
        self.warning_messages.append(message)

    def button(self, label: str, **kwargs: Any) -> bool:
        self.last_button_kwargs = {"label": label, **kwargs}
        return self.button_result


def test_build_action_registry_contains_expected_actions_and_requirements() -> None:
    action_registry = SUMMARY_MODULE._build_action_registry(
        resolved_brief_model="gpt-5-mini",
        resolved_job_ad_model="gpt-4o-mini",
        resolved_hr_sheet_model="gpt-5-nano",
        resolved_fach_sheet_model="gpt-5",
        resolved_boolean_search_model="gpt-5-mini",
        resolved_employment_contract_model="o3-mini",
        generate_recruiting_brief=lambda: None,
        generate_job_ad=lambda: None,
        generate_interview_prep_hr=lambda: None,
        generate_interview_prep_fach=lambda: None,
        generate_boolean_search=lambda: None,
        generate_employment_contract=lambda: None,
    )

    assert [action["id"] for action in action_registry] == [
        "recruiting_brief",
        "job_ad_generator",
        "interview_hr_sheet",
        "interview_fach_sheet",
        "boolean_search",
        "employment_contract",
    ]
    assert action_registry[0]["requires"] == (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN)
    assert action_registry[1]["requires"] == (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN)
    assert action_registry[2]["requires"] == (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN)
    assert action_registry[2]["generator_fn"] is not None
    assert action_registry[3]["requires"] == (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN)
    assert action_registry[3]["generator_fn"] is not None
    assert action_registry[4]["requires"] == (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN)
    assert action_registry[4]["generator_fn"] is not None
    assert action_registry[5]["requires"] == (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN)
    assert action_registry[5]["generator_fn"] is not None


def test_render_action_card_returns_false_when_requirements_missing(
    monkeypatch,
) -> None:
    fake_st = _FakeStreamlit(session_state={})
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)

    action = {
        "id": "recruiting_brief",
        "title": "Recruiting Brief",
        "description": "desc",
        "cta_label": "Generate",
        "requires": (SSKey.JOB_EXTRACT,),
        "generator_fn": lambda: None,
        "result_key": SSKey.BRIEF,
        "input_hints": ("hint",),
    }
    triggered = SUMMARY_MODULE._render_action_card(action)

    assert triggered is False
    assert fake_st.warning_messages
    assert fake_st.last_button_kwargs == {}


def test_render_action_card_renders_available_fach_action(monkeypatch) -> None:
    fake_st = _FakeStreamlit(
        session_state={
            SSKey.BRIEF.value: {"one_liner": "x"},
            SSKey.INTERVIEW_PREP_FACH.value: None,
        }
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)

    action = {
        "id": "interview_fach_sheet",
        "title": "Fachbereich Sheet",
        "description": "desc",
        "cta_label": "Generate",
        "requires": (SSKey.BRIEF,),
        "generator_fn": lambda: None,
        "result_key": SSKey.INTERVIEW_PREP_FACH,
        "input_hints": (),
    }
    triggered = SUMMARY_MODULE._render_action_card(action)

    assert triggered is False
    assert "disabled" not in fake_st.last_button_kwargs


def test_render_action_card_returns_button_state_for_available_action(
    monkeypatch,
) -> None:
    fake_st = _FakeStreamlit(
        session_state={SSKey.JOB_EXTRACT.value: {"job_title": "Engineer"}},
        button_result=True,
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)

    action = {
        "id": "job_ad_generator",
        "title": "Job Ad",
        "description": "desc",
        "cta_label": "Generate",
        "requires": (SSKey.JOB_EXTRACT,),
        "generator_fn": lambda: None,
        "result_key": SSKey.JOB_AD_DRAFT_CUSTOM,
        "input_hints": (),
    }
    triggered = SUMMARY_MODULE._render_action_card(action)

    assert triggered is True
    assert fake_st.last_button_kwargs["type"] == "primary"


def test_has_required_state_requires_all_truthy_values(monkeypatch) -> None:
    fake_st = SimpleNamespace(
        session_state={
            SSKey.JOB_EXTRACT.value: {"job_title": "Engineer"},
            SSKey.QUESTION_PLAN.value: None,
        }
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)

    assert (
        SUMMARY_MODULE._has_required_state((SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN))
        is False
    )
    fake_st.session_state[SSKey.QUESTION_PLAN.value] = {"steps": []}
    assert (
        SUMMARY_MODULE._has_required_state((SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN))
        is True
    )


def test_follow_up_actions_describe_explicit_brief_dependency() -> None:
    action_registry = SUMMARY_MODULE._build_action_registry(
        resolved_brief_model="gpt-5-mini",
        resolved_job_ad_model="gpt-4o-mini",
        resolved_hr_sheet_model="gpt-5-nano",
        resolved_fach_sheet_model="gpt-5",
        resolved_boolean_search_model="gpt-5-mini",
        resolved_employment_contract_model="o3-mini",
        generate_recruiting_brief=lambda: None,
        generate_job_ad=lambda: None,
        generate_interview_prep_hr=lambda: None,
        generate_interview_prep_fach=lambda: None,
        generate_boolean_search=lambda: None,
        generate_employment_contract=lambda: None,
    )

    follow_up_ids = {
        "interview_hr_sheet",
        "interview_fach_sheet",
        "boolean_search",
        "employment_contract",
    }
    for action in action_registry:
        if action["id"] in follow_up_ids:
            hints = " ".join(action["input_hints"]).lower()
            assert "explizit" in hints
