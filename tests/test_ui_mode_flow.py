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
