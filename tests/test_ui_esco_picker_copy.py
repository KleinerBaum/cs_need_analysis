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
        self.text_input_labels: list[str] = []
        self.selectbox_labels: list[str] = []
        self.button_labels: list[str] = []
        self.expander_labels: list[str] = []
        self.expander_calls: list[tuple[str, bool | None]] = []
        self.captions: list[str] = []
        self.container_calls: list[dict[str, Any]] = []
        self.markdown_calls: list[str] = []
        self.text_input_value = ""
        self.selectbox_value: int | None = None

    def text_input(self, label: str, **__: Any) -> str:
        self.text_input_labels.append(label)
        return self.text_input_value

    def selectbox(self, label: str, **__: Any) -> int | None:
        self.selectbox_labels.append(label)
        return self.selectbox_value

    def multiselect(self, label: str, **__: Any) -> list[int]:
        self.selectbox_labels.append(label)
        return []

    def expander(self, label: str, **__: Any) -> _NoopContext:
        self.expander_labels.append(label)
        self.expander_calls.append((label, __.get("expanded")))
        return _NoopContext()

    def container(self, **kwargs: Any) -> _NoopContext:
        self.container_calls.append(kwargs)
        return _NoopContext()

    def caption(self, message: str) -> None:
        self.captions.append(message)

    def markdown(self, message: str, *_: Any, **__: Any) -> None:
        self.markdown_calls.append(message)

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

    assert fake_st.text_input_labels == ["ESCO Suche"]
    assert fake_st.selectbox_labels == ["Top-Vorschlag auswählen"]
    assert fake_st.container_calls == []
    assert fake_st.expander_labels == ["Preview vor Apply"]
    assert fake_st.expander_calls == [("Preview vor Apply", False)]
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

    assert fake_st.text_input_labels == ["ESCO Suche"]
    assert fake_st.selectbox_labels == ["Choose semantic occupation"]
    assert fake_st.container_calls == []
    assert fake_st.expander_labels == ["Preview semantic anchor"]
    assert fake_st.expander_calls == [("Preview semantic anchor", False)]
    assert fake_st.button_labels == ["Use as semantic anchor"]
    assert "Confirm occupation for downstream suggestions" in fake_st.captions


def test_render_esco_picker_card_anchor_card_uses_compact_occupation_copy(
    monkeypatch,
) -> None:
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(ui_components, "st", fake_st)

    ui_components.render_esco_picker_card(
        concept_type="occupation",
        target_state_key="esco.occupation",
        layout_variant="anchor_card",
    )

    assert fake_st.text_input_labels == ["Suchbegriff für Berufsabgleich"]
    assert fake_st.selectbox_labels == ["ESCO-Beruf auswählen"]
    assert fake_st.container_calls == [{"border": True}]
    assert (
        "Der Begriff steuert nur die ESCO-Suche; deine Rollenbeschreibung "
        "und spätere Antworten bleiben unverändert."
    ) in fake_st.captions


def test_render_esco_picker_card_anchor_card_does_not_change_skill_picker(
    monkeypatch,
) -> None:
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(ui_components, "st", fake_st)

    ui_components.render_esco_picker_card(
        concept_type="skill",
        target_state_key="esco.skill",
        layout_variant="anchor_card",
    )

    assert fake_st.text_input_labels == ["ESCO Suche"]
    assert fake_st.selectbox_labels == ["Top-Vorschlag auswählen"]
    assert fake_st.container_calls == []


class _FakeEscoClient:
    def suggest2(self, **__: Any) -> dict[str, Any]:
        return {}

    def search(self, **__: Any) -> dict[str, Any]:
        return {}


def test_render_esco_picker_card_results_overview_uses_candidate_cards(
    monkeypatch,
) -> None:
    fake_st = _FakeStreamlit()
    fake_st.text_input_value = "Data"
    fake_st.selectbox_value = 1
    fake_st.session_state[ui_components.SSKey.UI_MODE.value] = "expert"
    monkeypatch.setattr(ui_components, "st", fake_st)
    monkeypatch.setattr(ui_components, "EscoClient", _FakeEscoClient)
    monkeypatch.setattr(
        ui_components,
        "_extract_esco_suggestions",
        lambda *_args, **_kwargs: [
            {
                "title": "Data Engineer",
                "uri": "https://example.test/occupation/1",
                "type": "occupation",
                "source": "auto",
            },
            {
                "title": "Data Analyst",
                "uri": "https://example.test/occupation/2",
                "type": "occupation",
                "source": "manual",
            },
            {
                "title": "Business Analyst",
                "uri": "https://example.test/occupation/3",
                "type": "occupation",
                "source": "auto",
            },
        ],
    )

    ui_components.render_esco_picker_card(
        concept_type="occupation",
        target_state_key="esco.occupation",
        show_apply_button=False,
    )

    assert "**Vorschläge**" in fake_st.markdown_calls
    assert "**1. Data Engineer**" in fake_st.markdown_calls
    assert "**2. Data Analyst**" in fake_st.markdown_calls
    assert fake_st.captions.count("Alternative") == 2
    assert fake_st.captions.count("Ausgewählt") == 1
    assert any(
        "Data Analyst · https://example.test/occupation/2 · manual" in caption
        for caption in fake_st.captions
    )
    assert fake_st.container_calls == [
        {"border": True},
        {"border": True},
        {"border": True},
    ]
