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
        self.captions: list[str] = []
        self.editor_rows_by_key: dict[str, list[dict[str, Any]]] = {}
        self.tab_titles: list[str] = []
        self.text_input_values: dict[str, str] = {}
        self.toggle_values: dict[str, bool] = {}

    def markdown(self, *_: Any, **__: Any) -> None:
        return None

    def caption(self, message: str) -> None:
        self.captions.append(message)

    def expander(self, *_: Any, **__: Any) -> _NoopContext:
        return _NoopContext()

    def write(self, *_: Any, **__: Any) -> None:
        return None

    def tabs(self, titles: list[str]) -> list[_NoopContext]:
        self.tab_titles = list(titles)
        return [_NoopContext() for _ in titles]

    def text_input(self, _: str, *, key: str, value: str = "", **__: Any) -> str:
        return self.text_input_values.get(key, value)

    def columns(self, count: int, **_: Any) -> list[_NoopContext]:
        return [_NoopContext() for _ in range(count)]

    def toggle(self, _: str, *, key: str, value: bool = False, **__: Any) -> bool:
        return self.toggle_values.get(key, value)

    def data_editor(
        self, rows: list[dict[str, Any]], *, key: str, **_: Any
    ) -> list[dict[str, Any]]:
        return self.editor_rows_by_key.get(key, rows)

    class column_config:  # noqa: N801
        @staticmethod
        def CheckboxColumn(*_: Any, **__: Any) -> object:
            return object()

        @staticmethod
        def TextColumn(*_: Any, **__: Any) -> object:
            return object()


def test_render_compact_requirement_board_handles_empty_board(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(ui_components, "st", fake_st)

    selected = ui_components.render_compact_requirement_board(
        title_jobspec="Aus Jobspec extrahiert",
        jobspec_items=[],
        title_esco="ESCO",
        esco_items=[],
        title_llm="AI-Vorschläge",
        llm_items=[],
        selected_labels=[],
        selection_state_key="skills.bulk",
        key_prefix="skills.board",
    )

    assert selected == []
    assert fake_st.captions == ["Keine Vorschläge."]


def test_render_compact_requirement_board_collects_selected_labels(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(ui_components, "st", fake_st)

    fake_st.editor_rows_by_key["skills.board.editor.jobspec"] = [
        {
            "select": True,
            "label": "SQL",
            "source": "Jobspec",
            "notes": "",
            "_full_label": "SQL",
        }
    ]
    selected = ui_components.render_compact_requirement_board(
        title_jobspec="Aus Jobspec extrahiert",
        jobspec_items=[{"label": "SQL"}],
        title_esco="ESCO",
        esco_items=[],
        title_llm="AI-Vorschläge",
        llm_items=[],
        selected_labels=[],
        selection_state_key="skills.bulk",
        key_prefix="skills.board",
    )

    assert selected == ["SQL"]
    assert fake_st.session_state["skills.bulk"] == ["SQL"]
    assert fake_st.tab_titles == []


def test_render_compact_requirement_board_filters_only_new_default_on(
    monkeypatch,
) -> None:
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(ui_components, "st", fake_st)

    selected = ui_components.render_compact_requirement_board(
        title_jobspec="Aus Jobspec extrahiert",
        jobspec_items=[{"label": "SQL"}, {"label": "Python"}],
        title_esco="ESCO",
        esco_items=[],
        title_llm="AI-Vorschläge",
        llm_items=[],
        selected_labels=["SQL"],
        selection_state_key="skills.bulk",
        key_prefix="skills.board",
    )

    assert selected == []
    assert fake_st.session_state["skills.bulk"] == []
