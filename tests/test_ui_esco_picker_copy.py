from __future__ import annotations

from typing import Any
from typing import Literal

import ui_components
import ui_esco_picker


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
        self.columns_calls: list[tuple[Any, str | None]] = []
        self.markdown_calls: list[str] = []
        self.write_calls: list[Any] = []
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

    def columns(self, spec: Any, **kwargs: Any) -> list[_NoopContext]:
        self.columns_calls.append((spec, kwargs.get("gap")))
        count = spec if isinstance(spec, int) else len(spec)
        return [_NoopContext() for _ in range(count)]

    def caption(self, message: str) -> None:
        self.captions.append(message)

    def markdown(self, message: str, *_: Any, **__: Any) -> None:
        self.markdown_calls.append(message)

    def write(self, *messages: Any, **__: Any) -> None:
        self.write_calls.extend(messages)

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
    monkeypatch.setattr(ui_esco_picker, "st", fake_st)
    assert ui_components.render_esco_picker_card is ui_esco_picker.render_esco_picker_card

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
    monkeypatch.setattr(ui_esco_picker, "st", fake_st)

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
    monkeypatch.setattr(ui_esco_picker, "st", fake_st)

    ui_components.render_esco_picker_card(
        concept_type="occupation",
        target_state_key="esco.occupation",
        layout_variant="anchor_card",
    )

    assert fake_st.text_input_labels == ["Suchbegriff für Berufsabgleich"]
    assert fake_st.selectbox_labels == ["Referenzberuf auswählen"]
    assert fake_st.container_calls == [{"border": True}]
    assert (
        "Der Begriff steuert nur den Berufsabgleich; deine Rollenbeschreibung "
        "und spätere Antworten bleiben unverändert."
    ) in fake_st.captions


def test_render_esco_picker_card_anchor_card_uses_english_copy(
    monkeypatch,
) -> None:
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(ui_esco_picker, "st", fake_st)
    monkeypatch.setattr(ui_esco_picker, "active_language", lambda: "en")

    ui_components.render_esco_picker_card(
        concept_type="occupation",
        target_state_key="esco.occupation",
        layout_variant="anchor_card",
        enable_preview=True,
    )

    assert fake_st.text_input_labels == ["Search term for occupation matching"]
    assert fake_st.selectbox_labels == ["Select reference occupation"]
    assert (
        "The term controls only occupation matching; your role description and later "
        "answers remain unchanged."
    ) in fake_st.captions
    assert fake_st.expander_labels == ["Preview before apply"]


def test_render_esco_picker_card_anchor_card_bundles_confirmed_summary_and_breadcrumb(
    monkeypatch,
) -> None:
    fake_st = _FakeStreamlit()
    fake_st.session_state["esco.occupation"] = {
        "uri": "https://example.test/occupation/1",
        "title": "Data Engineer",
        "type": "occupation",
    }
    monkeypatch.setattr(ui_esco_picker, "st", fake_st)

    ui_components.render_esco_picker_card(
        concept_type="occupation",
        target_state_key="esco.occupation",
        layout_variant="anchor_card",
    )

    assert fake_st.container_calls == [{"border": True}, {"border": True}]
    assert "**Bestätigter Referenzberuf**" in fake_st.markdown_calls
    assert "### Data Engineer" in fake_st.markdown_calls
    assert "**Position im Berufsverzeichnis**" in fake_st.markdown_calls
    assert "**Bestätigte ESCO-Auswahl**" not in fake_st.markdown_calls
    assert "**Taxonomie/Breadcrumb**" not in fake_st.markdown_calls
    assert "- Data Engineer" not in fake_st.write_calls
    assert not any("URI:" in caption for caption in fake_st.captions)


def test_render_esco_picker_card_anchor_card_shows_metadata_only_in_expert(
    monkeypatch,
) -> None:
    fake_st = _FakeStreamlit()
    fake_st.session_state[ui_esco_picker.SSKey.UI_MODE.value] = "expert"
    fake_st.session_state["esco.occupation"] = {
        "uri": "https://example.test/occupation/1",
        "title": "Data Engineer",
        "type": "occupation",
    }
    fake_st.session_state["esco.occupation.esco_picker.applied_meta"] = {
        "version": "v1.2.3",
        "source": "manual",
    }
    monkeypatch.setattr(ui_esco_picker, "st", fake_st)

    ui_components.render_esco_picker_card(
        concept_type="occupation",
        target_state_key="esco.occupation",
        layout_variant="anchor_card",
    )

    assert (
        "URI: https://example.test/occupation/1 · Version: v1.2.3 · Quelle: manual"
        in fake_st.captions
    )


def test_render_esco_picker_card_anchor_card_does_not_change_skill_picker(
    monkeypatch,
) -> None:
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(ui_esco_picker, "st", fake_st)

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


def test_render_esco_picker_card_retries_occupation_query_without_context(
    monkeypatch,
) -> None:
    class _RecordingEscoClient:
        calls: list[tuple[str, str, str]] = []

        def suggest2(self, **query: Any) -> dict[str, Any]:
            text = str(query.get("text") or "")
            concept_type = str(query.get("type") or "")
            self.calls.append(("suggest2", text, concept_type))
            if text == "Data Engineer":
                return {
                    "uri": "https://example.test/occupation/1",
                    "title": "Data Engineer",
                    "type": "occupation",
                }
            return {}

        def search(self, **query: Any) -> dict[str, Any]:
            text = str(query.get("text") or "")
            concept_type = str(query.get("type") or "")
            self.calls.append(("search", text, concept_type))
            return {}

    fake_st = _FakeStreamlit()
    fake_st.text_input_value = "Data Engineer (Analytics, Berlin)"
    monkeypatch.setattr(ui_esco_picker, "st", fake_st)
    monkeypatch.setattr(ui_esco_picker, "EscoClient", _RecordingEscoClient)

    ui_components.render_esco_picker_card(
        concept_type="occupation",
        target_state_key="esco.occupation",
        show_apply_button=False,
    )

    assert _RecordingEscoClient.calls == [
        ("suggest2", "Data Engineer (Analytics, Berlin)", "occupation"),
        ("search", "Data Engineer (Analytics, Berlin)", "occupation"),
        ("suggest2", "Data Engineer", "occupation"),
    ]
    assert fake_st.session_state["esco.occupation.esco_picker.options"] == [
        {
            "uri": "https://example.test/occupation/1",
            "title": "Data Engineer",
            "type": "occupation",
            "source": "auto",
        }
    ]


def test_render_esco_picker_card_does_not_clean_skill_queries(monkeypatch) -> None:
    class _RecordingEscoClient:
        calls: list[tuple[str, str, str]] = []

        def suggest2(self, **query: Any) -> dict[str, Any]:
            self.calls.append(
                (
                    "suggest2",
                    str(query.get("text") or ""),
                    str(query.get("type") or ""),
                )
            )
            return {}

        def search(self, **query: Any) -> dict[str, Any]:
            self.calls.append(
                (
                    "search",
                    str(query.get("text") or ""),
                    str(query.get("type") or ""),
                )
            )
            return {}

    fake_st = _FakeStreamlit()
    fake_st.text_input_value = "Python (Backend)"
    monkeypatch.setattr(ui_esco_picker, "st", fake_st)
    monkeypatch.setattr(ui_esco_picker, "EscoClient", _RecordingEscoClient)

    ui_components.render_esco_picker_card(
        concept_type="skill",
        target_state_key="esco.skill",
        show_apply_button=False,
    )

    assert _RecordingEscoClient.calls == [
        ("suggest2", "Python (Backend)", "skill"),
        ("search", "Python (Backend)", "skill"),
    ]


def test_render_esco_picker_card_results_overview_uses_three_candidate_columns(
    monkeypatch,
) -> None:
    fake_st = _FakeStreamlit()
    fake_st.text_input_value = "Data"
    fake_st.selectbox_value = 1
    fake_st.session_state[ui_esco_picker.SSKey.UI_MODE.value] = "expert"
    monkeypatch.setattr(ui_esco_picker, "st", fake_st)
    monkeypatch.setattr(ui_esco_picker, "EscoClient", _FakeEscoClient)
    monkeypatch.setattr(
        ui_esco_picker,
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

    assert "**Vorschläge**" not in fake_st.markdown_calls
    assert "**1. Data Engineer**" in fake_st.markdown_calls
    assert "**2. Data Analyst**" in fake_st.markdown_calls
    assert fake_st.captions.count("Alternative") == 2
    assert fake_st.captions.count("Ausgewählt") == 1
    assert not any("https://example.test" in caption for caption in fake_st.captions)
    assert fake_st.columns_calls == [(3, "small")]
    assert fake_st.container_calls == [
        {"border": True},
        {"border": True},
        {"border": True},
    ]
