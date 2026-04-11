from __future__ import annotations

from typing import Any
from typing import Literal

import ui_components


class _NoopContext:
    def __enter__(self) -> "_NoopContext":
        return self

    def __exit__(self, *_: object) -> Literal[False]:
        return False


class _FakeStreamlit:
    def __init__(self) -> None:
        self.session_state: dict[str, Any] = {}
        self.selectbox_labels: list[str] = []
        self.button_labels: list[str] = []
        self.expander_labels: list[str] = []
        self.captions: list[str] = []

    def text_input(self, _: str, **__: Any) -> str:
        return ""

    def selectbox(self, label: str, **__: Any) -> int | None:
        self.selectbox_labels.append(label)
        return None

    def multiselect(self, label: str, **__: Any) -> list[int]:
        self.selectbox_labels.append(label)
        return []

    def expander(self, label: str, **__: Any) -> _NoopContext:
        self.expander_labels.append(label)
        return _NoopContext()

    def caption(self, message: str) -> None:
        self.captions.append(message)

    def markdown(self, *_: Any, **__: Any) -> None:
        return None

    def write(self, *_: Any, **__: Any) -> None:
        return None

    def warning(self, *_: Any, **__: Any) -> None:
        return None

    def button(self, label: str, **__: Any) -> bool:
        self.button_labels.append(label)
        return False

    def error(self, *_: Any, **__: Any) -> None:
        return None

    def info(self, *_: Any, **__: Any) -> None:
        return None


def test_render_esco_picker_card_uses_default_copy(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(ui_components, "st", fake_st)

    ui_components.render_esco_picker_card(
        concept_type="occupation",
        target_state_key="esco.occupation",
        enable_preview=True,
    )

    assert fake_st.selectbox_labels == ["Top-Vorschlag auswählen"]
    assert fake_st.expander_labels == ["Preview vor Apply"]
    assert fake_st.button_labels == ["Apply"]


def test_render_esco_picker_card_uses_copy_overrides(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(ui_components, "st", fake_st)

    ui_components.render_esco_picker_card(
        concept_type="occupation",
        target_state_key="esco.occupation",
        enable_preview=True,
        apply_label="Use as semantic anchor",
        preview_label="Preview semantic anchor",
        selection_label="Choose semantic occupation",
        confirmation_helper_text="Confirm occupation for downstream suggestions",
    )

    assert fake_st.selectbox_labels == ["Choose semantic occupation"]
    assert fake_st.expander_labels == ["Preview semantic anchor"]
    assert fake_st.button_labels == ["Use as semantic anchor"]
    assert "Confirm occupation for downstream suggestions" in fake_st.captions
