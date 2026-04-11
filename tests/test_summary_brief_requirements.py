from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal

from constants import SSKey
from schemas import VacancyBrief


SUMMARY_PATH = Path(__file__).resolve().parents[1] / "wizard_pages" / "08_summary.py"
SPEC = spec_from_file_location(
    "wizard_pages.page_08_summary_requirements", SUMMARY_PATH
)
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
        self.last_button_kwargs: dict[str, Any] = {}

    def container(self, **_: Any) -> _NoopContext:
        return _NoopContext()

    def columns(self, n: int) -> list[_NoopContext]:
        return [_NoopContext() for _ in range(n)]

    def markdown(self, *_: Any, **__: Any) -> None:
        return None

    def caption(self, *_: Any, **__: Any) -> None:
        return None

    def info(self, *_: Any, **__: Any) -> None:
        return None

    def success(self, *_: Any, **__: Any) -> None:
        return None

    def write(self, *_: Any, **__: Any) -> None:
        return None

    def button(self, label: str, **kwargs: Any) -> bool:
        self.last_button_kwargs = {"label": label, **kwargs}
        return self.button_result


def _valid_brief_payload() -> dict[str, Any]:
    return VacancyBrief(
        one_liner="Kurzpitch",
        hiring_context="Kontext",
        role_summary="Rollenbild",
        job_ad_draft="Draft",
    ).model_dump(mode="json")


def _registry() -> list[dict[str, Any]]:
    return SUMMARY_MODULE._build_action_registry(
        resolved_brief_model="gpt-5-mini",
        resolved_job_ad_model="gpt-4o-mini",
        resolved_hr_sheet_model="gpt-5-nano",
        resolved_fach_sheet_model="gpt-5",
        resolved_boolean_search_model="gpt-5-mini",
        resolved_employment_contract_model="o3-mini",
        follow_up_requirement_check=lambda: SUMMARY_MODULE._get_brief_requirement_status(
            "gpt-5-mini"
        ),
        generate_recruiting_brief=lambda: None,
        generate_job_ad=lambda: None,
        generate_interview_prep_hr=lambda: None,
        generate_interview_prep_fach=lambda: None,
        generate_boolean_search=lambda: None,
        generate_employment_contract=lambda: None,
    )


def test_follow_up_requirement_blocks_without_current_brief(monkeypatch) -> None:
    fake_st = SimpleNamespace(session_state={})
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)

    ok, reason = SUMMARY_MODULE._get_brief_requirement_status("gpt-5-mini")

    assert ok is False
    assert reason == "Kein Recruiting Brief vorhanden."


def test_follow_up_requirement_blocks_stale_brief(monkeypatch) -> None:
    fake_st = SimpleNamespace(
        session_state={
            SSKey.BRIEF.value: _valid_brief_payload(),
            SSKey.SUMMARY_LAST_MODELS.value: {"draft_model": "gpt-4o-mini"},
        }
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)

    ok, reason = SUMMARY_MODULE._get_brief_requirement_status("gpt-5-mini")

    assert ok is False
    assert reason == "Recruiting Brief ist veraltet."


def test_follow_up_requirement_accepts_current_brief(monkeypatch) -> None:
    fake_st = SimpleNamespace(
        session_state={
            SSKey.BRIEF.value: _valid_brief_payload(),
            SSKey.SUMMARY_LAST_MODELS.value: {"draft_model": "gpt-5-mini"},
            SSKey.SUMMARY_INPUT_FINGERPRINT.value: "abc",
            SSKey.SUMMARY_LAST_BRIEF_FINGERPRINT.value: "abc",
        }
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)

    ok, reason = SUMMARY_MODULE._get_brief_requirement_status("gpt-5-mini")

    assert ok is True
    assert reason == "Aktueller Recruiting Brief vorhanden."


def test_get_brief_status_changes_primary_cta_label_by_state(monkeypatch) -> None:
    registry = _registry()
    primary_action = registry[0]
    follow_up_actions = registry[1:]
    fake_st = _FakeStreamlit(
        session_state={
            SSKey.JOB_EXTRACT.value: {"job_title": "Engineer"},
            SSKey.QUESTION_PLAN.value: {"steps": []},
        }
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)

    state, _, cta = SUMMARY_MODULE._get_brief_status(
        primary_action=primary_action,
        follow_up_actions=follow_up_actions,
    )
    assert state == "missing"
    assert cta == "Recruiting Brief generieren"

    fake_st.session_state[SSKey.BRIEF.value] = _valid_brief_payload()
    fake_st.session_state[SSKey.SUMMARY_LAST_MODELS.value] = {"draft_model": "gpt-4o-mini"}
    state, _, cta = SUMMARY_MODULE._get_brief_status(
        primary_action=primary_action,
        follow_up_actions=follow_up_actions,
    )
    assert state == "stale"
    assert cta == "Recruiting Brief aktualisieren"

    fake_st.session_state[SSKey.SUMMARY_LAST_MODELS.value] = {"draft_model": "gpt-5-mini"}
    state, _, cta = SUMMARY_MODULE._get_brief_status(
        primary_action=primary_action,
        follow_up_actions=follow_up_actions,
    )
    assert state == "current"
    assert cta == "Brief aktualisieren"


def test_render_follow_up_cards_disable_and_enable_based_on_current_brief(
    monkeypatch,
) -> None:
    registry = _registry()
    follow_up_action = next(
        action for action in registry if action["id"] == "interview_hr_sheet"
    )
    base_state = {
        SSKey.JOB_EXTRACT.value: {"job_title": "Engineer"},
        SSKey.QUESTION_PLAN.value: {"steps": []},
    }

    fake_st_blocked = _FakeStreamlit(session_state=dict(base_state))
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st_blocked)
    SUMMARY_MODULE._render_action_card(follow_up_action)
    assert fake_st_blocked.last_button_kwargs["disabled"] is True

    fake_st_enabled = _FakeStreamlit(
        session_state={
            **base_state,
            SSKey.BRIEF.value: _valid_brief_payload(),
            SSKey.SUMMARY_LAST_MODELS.value: {"draft_model": "gpt-5-mini"},
        }
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st_enabled)
    SUMMARY_MODULE._render_action_card(follow_up_action)
    assert fake_st_enabled.last_button_kwargs["disabled"] is False
