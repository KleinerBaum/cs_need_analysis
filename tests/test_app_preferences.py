from __future__ import annotations

from typing import Any

import app
import wizard_pages.base as base
from constants import (
    SSKey,
    UI_LANGUAGE_WIDGET_KEY_SIDEBAR,
    UI_PREFERENCE_ANSWER_MODE,
    UI_PREFERENCE_INFORMATION_DEPTH,
    UI_PREFERENCE_PII_REDUCTION,
    UI_PREFERENCE_UI_LANGUAGE,
    UI_PREFERENCE_WIZARD_DESIGN,
    UI_MODE_DEFAULT,
)


class _FakePreferenceStreamlit:
    def __init__(self, session_state: dict[str, Any]) -> None:
        self.session_state = session_state
        self.toggle_values: dict[str, bool] = {}
        self.selectbox_labels: list[str] = []
        self.radio_labels: list[str] = []

    def selectbox(
        self,
        _label: str,
        *,
        options: list[str],
        index: int,
        **_kwargs: Any,
    ) -> str:
        self.selectbox_labels.append(_label)
        return options[index]

    def radio(
        self,
        label: str,
        *,
        options: list[str],
        key: str,
        **_kwargs: Any,
    ) -> str:
        self.radio_labels.append(label)
        if key not in self.session_state:
            self.session_state[key] = options[0]
        return str(self.session_state[key])

    def text_input(self, _label: str, *, value: str, **_kwargs: Any) -> str:
        return value

    def slider(self, _label: str, *, value: float, **_kwargs: Any) -> float:
        return value

    def toggle(self, label: str, *, value: bool, **_kwargs: Any) -> bool:
        self.toggle_values[label] = value
        return value

    def markdown(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def caption(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def button(self, *_args: Any, **_kwargs: Any) -> bool:
        return False


def test_preference_center_defaults_pii_reduction_on_when_missing(monkeypatch) -> None:
    fake_st = _FakePreferenceStreamlit(
        {
            SSKey.UI_MODE.value: UI_MODE_DEFAULT,
            SSKey.AUDIENCE_MODE.value: "candidate",
            SSKey.UI_PREFERENCES.value: {},
        }
    )
    monkeypatch.setattr(app, "st", fake_st)
    monkeypatch.setattr(base, "st", fake_st)

    app._render_preference_center_sidebar(key_prefix="test", show_reset_button=False)

    assert fake_st.toggle_values["PII-Reduktion"] is True
    assert fake_st.session_state[SSKey.SOURCE_REDACT_PII.value] is True
    assert (
        fake_st.session_state[SSKey.UI_PREFERENCES.value][
            UI_PREFERENCE_PII_REDUCTION
        ]
        is True
    )
    assert (
        fake_st.session_state[SSKey.UI_PREFERENCES.value][
            UI_PREFERENCE_ANSWER_MODE
        ]
        == "balanced"
    )
    assert (
        fake_st.session_state[SSKey.UI_PREFERENCES.value][
            UI_PREFERENCE_INFORMATION_DEPTH
        ]
        == "standard"
    )
    assert (
        fake_st.session_state[SSKey.UI_PREFERENCES.value][
            UI_PREFERENCE_WIZARD_DESIGN
        ]
        == "classic"
    )
    assert "Sprache" not in fake_st.selectbox_labels
    assert "Antwortmodus" not in fake_st.selectbox_labels
    assert "Informationstiefe" not in fake_st.selectbox_labels
    assert "Ansichtsmodus" not in fake_st.radio_labels
    assert fake_st.session_state[SSKey.AUDIENCE_MODE.value] == "recruiter"


def test_pre_render_language_sync_reads_sidebar_widget(monkeypatch) -> None:
    fake_session_state = {
        UI_LANGUAGE_WIDGET_KEY_SIDEBAR: "en",
        SSKey.LANGUAGE.value: "de",
        SSKey.UI_PREFERENCES.value: {UI_PREFERENCE_UI_LANGUAGE: "de"},
        SSKey.ESCO_CONFIG.value: {"language": "de", "fallback_language": "en"},
    }
    monkeypatch.setattr(
        app,
        "st",
        type("FakeStreamlit", (), {"session_state": fake_session_state})(),
    )

    app._sync_language_before_render()

    assert fake_session_state[SSKey.LANGUAGE.value] == "en"
    assert (
        fake_session_state[SSKey.UI_PREFERENCES.value][UI_PREFERENCE_UI_LANGUAGE]
        == "en"
    )
    assert fake_session_state[SSKey.ESCO_CONFIG.value]["language"] == "de"
    assert fake_session_state[SSKey.ESCO_CONFIG.value]["fallback_language"] == "en"
