from __future__ import annotations

from typing import Any

import ui_source_pills
from ui_widget_state import ensure_multiselect_widget_state, ensure_option_widget_state


def test_ensure_option_widget_state_initializes_invalid_value() -> None:
    session_state: dict[str, Any] = {"language": "fr"}

    value = ensure_option_widget_state(
        "language",
        options=("de", "en"),
        default="en",
        session_state=session_state,
    )

    assert value == "en"
    assert session_state["language"] == "en"


def test_ensure_multiselect_widget_state_filters_invalid_values() -> None:
    session_state: dict[str, Any] = {"skills": ["Python", "Missing", "Python"]}

    value = ensure_multiselect_widget_state(
        "skills",
        options=["Python", "SQL"],
        default=["SQL"],
        session_state=session_state,
    )

    assert value == ["Python"]
    assert session_state["skills"] == ["Python"]


def test_source_pills_initializes_state_without_widget_default(monkeypatch) -> None:
    class FakeStreamlit:
        def __init__(self) -> None:
            self.session_state: dict[str, Any] = {}
            self.multiselect_kwargs: dict[str, Any] = {}

        def multiselect(self, _label: str, **kwargs: Any) -> list[str]:
            self.multiselect_kwargs = kwargs
            return list(self.session_state[str(kwargs["key"])])

    fake_st = FakeStreamlit()
    monkeypatch.setattr(ui_source_pills, "st", fake_st)

    selected = ui_source_pills.render_multi_select_pills(
        "Skills",
        options=["Python", "SQL"],
        default=["SQL", "Missing"],
        key="skills",
    )

    assert selected == ["SQL"]
    assert fake_st.session_state["skills"] == ["SQL"]
    assert "default" not in fake_st.multiselect_kwargs
