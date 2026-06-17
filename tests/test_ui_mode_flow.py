from __future__ import annotations

from typing import Any

from streamlit.errors import StreamlitAPIException

import wizard_pages.base as base
from constants import (
    SSKey,
    STEPS,
    STEP_KEY_TEAM,
    UI_PREFERENCE_ANSWER_MODE,
    UI_PREFERENCE_INFORMATION_DEPTH,
)
from schemas import JobAdExtract


class _LockedSessionState(dict[str, Any]):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.locked_keys: set[str] = set()

    def __setitem__(self, key: str, value: Any) -> None:
        if key in self.locked_keys:
            raise StreamlitAPIException(
                f"Widget key '{key}' cannot be mutated post-render."
            )
        super().__setitem__(key, value)


class _FakeStreamlit:
    def __init__(self, session_state: _LockedSessionState) -> None:
        self.session_state = session_state
        self.sidebar = self

    def selectbox(
        self,
        _label: str,
        *,
        options: list[str],
        key: str,
        index: int | None = None,
        on_change: Any | None = None,
        **_kwargs: Any,
    ) -> str:
        if key not in self.session_state:
            fallback_index = index if index is not None else 0
            self.session_state[key] = options[fallback_index]
        self.session_state.locked_keys.add(key)
        if on_change is not None:
            on_change()
        return str(self.session_state[key])

    def radio(
        self,
        _label: str,
        *,
        options: list[str],
        key: str,
        **_kwargs: Any,
    ) -> str:
        if key not in self.session_state:
            self.session_state[key] = options[0]
        return str(self.session_state[key])


def test_render_ui_mode_selector_does_not_mutate_widget_bound_mode_key(
    monkeypatch,
) -> None:
    session_state = _LockedSessionState(
        {
            SSKey.UI_MODE.value: "standard",
            SSKey.UI_PREFERENCES.value: {UI_PREFERENCE_ANSWER_MODE: "balanced"},
        }
    )
    fake_st = _FakeStreamlit(session_state)
    monkeypatch.setattr(base, "st", fake_st)
    monkeypatch.setattr(base, "sync_adaptive_question_limits", lambda: None)

    selected_mode = base.render_ui_mode_selector(widget_key=SSKey.UI_MODE.value)

    assert selected_mode == "standard"
    assert session_state[SSKey.UI_MODE.value] == "standard"
    assert (
        session_state[SSKey.UI_PREFERENCES.value][UI_PREFERENCE_ANSWER_MODE]
        == "balanced"
    )
    assert (
        session_state[SSKey.UI_PREFERENCES.value][UI_PREFERENCE_INFORMATION_DEPTH]
        == "standard"
    )


def test_render_ui_mode_selector_derives_legacy_preference_metadata(monkeypatch) -> None:
    session_state = _LockedSessionState(
        {
            SSKey.UI_MODE.value: "expert",
            SSKey.UI_PREFERENCES.value: {
                UI_PREFERENCE_ANSWER_MODE: "balanced",
                UI_PREFERENCE_INFORMATION_DEPTH: "standard",
            },
        }
    )
    fake_st = _FakeStreamlit(session_state)
    monkeypatch.setattr(base, "st", fake_st)
    monkeypatch.setattr(base, "sync_adaptive_question_limits", lambda: None)

    selected_mode = base.render_ui_mode_selector(widget_key=SSKey.UI_MODE.value)

    assert selected_mode == "expert"
    assert (
        session_state[SSKey.UI_PREFERENCES.value][UI_PREFERENCE_ANSWER_MODE]
        == "advisory"
    )
    assert (
        session_state[SSKey.UI_PREFERENCES.value][UI_PREFERENCE_INFORMATION_DEPTH]
        == "hoch"
    )


def test_visible_step_set_for_ui_mode_navigation_excludes_team_step() -> None:
    visible_step_keys = [step.key for step in STEPS]

    assert STEP_KEY_TEAM not in visible_step_keys
    assert visible_step_keys == [
        "landing",
        "company",
        "role_tasks",
        "skills",
        "benefits",
        "interview",
        "summary",
    ]


def test_set_current_step_records_step_entered_once(monkeypatch) -> None:
    session_state = _LockedSessionState({SSKey.CURRENT_STEP.value: "landing"})
    fake_st = _FakeStreamlit(session_state)
    monkeypatch.setattr(base, "st", fake_st)

    base.set_current_step("company")
    base.set_current_step("company")

    assert session_state[SSKey.USAGE_EVENTS.value] == [
        {
            "event_type": "step_entered",
            "occurred_at": session_state[SSKey.USAGE_EVENTS.value][0]["occurred_at"],
            "metadata": {"step_key": "company"},
        }
    ]


def test_sidebar_salary_forecast_is_rendered_for_all_ui_modes(monkeypatch) -> None:
    rendered_modes: list[str] = []
    computed_modes: list[str] = []

    def _fake_compute_sidebar_salary_forecast(**_kwargs: Any) -> object:
        computed_modes.append(str(base.st.session_state[SSKey.UI_MODE.value]))
        return object()

    def _fake_render_sidebar_salary_forecast(**_kwargs: Any) -> bool:
        rendered_modes.append(str(base.st.session_state[SSKey.UI_MODE.value]))
        return False

    monkeypatch.setattr(base, "sync_adaptive_question_limits", lambda: None)
    monkeypatch.setattr(
        base,
        "_compute_step_statuses",
        lambda _pages: [
            {
                "key": "landing",
                "status": "not_started",
                "answered": 0,
                "total": 0,
                "payload": {},
            }
        ],
    )
    monkeypatch.setattr(base, "_render_esco_warnings_and_migration_cta", lambda: None)
    monkeypatch.setattr(
        base, "_compute_sidebar_salary_forecast", _fake_compute_sidebar_salary_forecast
    )
    monkeypatch.setattr(
        base, "render_sidebar_salary_forecast", _fake_render_sidebar_salary_forecast
    )

    ctx = base.WizardContext(
        pages=[
            base.WizardPage(
                key="landing",
                title_de="Start",
                icon="",
                render=lambda _ctx: None,
            )
        ]
    )

    for mode in ("quick", "standard", "expert"):
        session_state = _LockedSessionState(
            {
                SSKey.CURRENT_STEP.value: "landing",
                SSKey.NAV_SELECTED.value: "landing",
                SSKey.NAV_SYNC_PENDING.value: False,
                SSKey.UI_MODE.value: mode,
                SSKey.JOB_EXTRACT.value: {"job_title": "Friseurmeisterin"},
                SSKey.ANSWERS.value: {"job_title": "Friseurmeisterin"},
                SSKey.SOURCE_TEXT.value: "",
            }
        )
        monkeypatch.setattr(base, "st", _FakeStreamlit(session_state))

        current_page = base.sidebar_navigation(ctx)

        assert current_page.key == "landing"

    assert computed_modes == []
    assert rendered_modes == ["quick", "standard", "expert"]


def test_sidebar_salary_input_selections_default_active_and_persist(
    monkeypatch,
) -> None:
    session_state = _LockedSessionState(
        {
            SSKey.JOB_EXTRACT.value: {"job_title": "Engineer"},
            SSKey.ROLE_TASKS_SELECTED.value: ["Build APIs"],
            SSKey.SALARY_FORECAST_INPUT_SELECTIONS.value: {},
        }
    )
    monkeypatch.setattr(base, "st", _FakeStreamlit(session_state))

    rows = base._build_sidebar_salary_input_rows()
    selections = base._sync_sidebar_salary_input_selections(rows)

    assert rows
    assert all(selections[row.id] is True for row in rows)

    first_row_id = rows[0].id
    session_state[SSKey.SALARY_FORECAST_INPUT_SELECTIONS.value][first_row_id] = False
    persisted = base._sync_sidebar_salary_input_selections(rows)

    assert persisted[first_row_id] is False


def test_sidebar_salary_fingerprint_changes_with_selection(monkeypatch) -> None:
    session_state = _LockedSessionState(
        {
            SSKey.JOB_EXTRACT.value: {"job_title": "Engineer"},
            SSKey.ROLE_TASKS_SELECTED.value: ["Build APIs"],
            SSKey.SALARY_FORECAST_INPUT_SELECTIONS.value: {},
        }
    )
    monkeypatch.setattr(base, "st", _FakeStreamlit(session_state))

    rows = base._build_sidebar_salary_input_rows()
    selections = base._sync_sidebar_salary_input_selections(rows)
    first = base._sidebar_salary_fingerprint(rows=rows, selections=selections)
    selections[rows[0].id] = False
    second = base._sidebar_salary_fingerprint(rows=rows, selections=selections)

    assert second != first


def test_sidebar_salary_job_excludes_disabled_inputs(monkeypatch) -> None:
    session_state = _LockedSessionState({})
    monkeypatch.setattr(base, "st", _FakeStreamlit(session_state))
    disabled = base.SalarySidebarInputRow(
        id="python",
        group="Skills",
        label="Must-have: Python",
        value="Python",
        target="must_have_skills",
        source_label="test",
    )
    enabled = base.SalarySidebarInputRow(
        id="go",
        group="Skills",
        label="Must-have: Go",
        value="Go",
        target="must_have_skills",
        source_label="test",
    )

    job, answers = base._sidebar_job_and_answers(
        base_job=JobAdExtract(job_title="Engineer", must_have_skills=["Legacy"]),
        rows=[disabled, enabled],
        selections={"python": False, "go": True},
        source_text="",
    )

    assert job is not None
    assert job.must_have_skills == ["Go"]
    assert "python" not in answers
    assert answers["go"] == "Go"


def test_compute_sidebar_salary_forecast_passes_esco_and_scenario(
    monkeypatch,
) -> None:
    from salary.types import SalaryEscoContext, SalaryScenarioInputs

    captured: dict[str, Any] = {}

    def _fake_compute_salary_forecast(**kwargs: Any) -> object:
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(
        "salary.engine.compute_salary_forecast", _fake_compute_salary_forecast
    )
    esco_context = SalaryEscoContext(occupation_uri="https://example.test/occ")
    scenario_inputs = SalaryScenarioInputs(remote_share_percent=75)

    result = base._compute_sidebar_salary_forecast(
        job=JobAdExtract(job_title="Engineer"),
        answers={"skill": "Python"},
        source_text="",
        esco_context=esco_context,
        scenario_inputs=scenario_inputs,
    )

    assert result is not None
    assert captured["esco_context"] == esco_context
    assert captured["scenario_inputs"] == scenario_inputs
