from __future__ import annotations

from typing import Any

from streamlit.errors import StreamlitAPIException

import wizard_pages.base as base
from constants import SSKey, STEPS, STEP_KEY_TEAM, UI_PREFERENCE_ANSWER_MODE


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


def test_sidebar_salary_forecast_is_rendered_for_all_ui_modes(monkeypatch) -> None:
    rendered_modes: list[str] = []
    computed_modes: list[str] = []

    def _fake_compute_sidebar_salary_forecast(**_kwargs: Any) -> object:
        computed_modes.append(str(base.st.session_state[SSKey.UI_MODE.value]))
        return object()

    def _fake_render_sidebar_salary_forecast(*, forecast: object) -> None:
        del forecast
        rendered_modes.append(str(base.st.session_state[SSKey.UI_MODE.value]))

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

    assert computed_modes == ["quick", "standard", "expert"]
    assert rendered_modes == ["quick", "standard", "expert"]
