from __future__ import annotations

from typing import Any

import app
from constants import SSKey, UI_PREFERENCE_PII_REDUCTION


class _FakePreferenceStreamlit:
    def __init__(self, session_state: dict[str, Any]) -> None:
        self.session_state = session_state
        self.toggle_values: dict[str, bool] = {}

    def selectbox(
        self,
        _label: str,
        *,
        options: list[str],
        index: int,
        **_kwargs: Any,
    ) -> str:
        return options[index]

    def text_input(self, _label: str, *, value: str, **_kwargs: Any) -> str:
        return value

    def slider(self, _label: str, *, value: float, **_kwargs: Any) -> float:
        return value

    def toggle(self, label: str, *, value: bool, **_kwargs: Any) -> bool:
        self.toggle_values[label] = value
        return value

    def markdown(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def button(self, *_args: Any, **_kwargs: Any) -> bool:
        return False


def test_preference_center_defaults_pii_reduction_on_when_missing(monkeypatch) -> None:
    fake_st = _FakePreferenceStreamlit(
        {
            SSKey.UI_MODE.value: "standard",
            SSKey.UI_PREFERENCES.value: {},
        }
    )
    monkeypatch.setattr(app, "st", fake_st)

    app._render_preference_center_sidebar(key_prefix="test", show_reset_button=False)

    assert fake_st.toggle_values["PII-Reduktion"] is True
    assert fake_st.session_state[SSKey.SOURCE_REDACT_PII.value] is True
    assert (
        fake_st.session_state[SSKey.UI_PREFERENCES.value][
            UI_PREFERENCE_PII_REDUCTION
        ]
        is True
    )
