from __future__ import annotations

from typing import Any

import ui_components


class _NoopContext:
    def __enter__(self) -> "_NoopContext":
        return self

    def __exit__(self, *_: object) -> bool:
        return False


class _FakeStreamlit:
    def __init__(self) -> None:
        self.session_state: dict[str, Any] = {}
        self.captions: list[str] = []
        self.checkbox_values: dict[str, bool] = {}
        self.button_values: dict[str, bool] = {}

    def markdown(self, *_: Any, **__: Any) -> None:
        return None

    def caption(self, message: str) -> None:
        self.captions.append(message)

    def checkbox(self, _: str, *, key: str, value: bool) -> bool:
        return self.checkbox_values.get(key, value)

    def button(self, _: str, *, key: str) -> bool:
        return self.button_values.get(key, False)

    def expander(self, *_: Any, **__: Any) -> _NoopContext:
        return _NoopContext()

    def write(self, *_: Any, **__: Any) -> None:
        return None

    def columns(self, count: int, **_: Any) -> list[_NoopContext]:
        return [_NoopContext() for _ in range(count)]


def test_render_compact_requirement_source_column_shows_custom_empty_message(
    monkeypatch,
) -> None:
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(ui_components, "st", fake_st)

    selected = ui_components.render_compact_requirement_source_column(
        title="ESCO",
        entries=[],
        source_badge="ESCO",
        selected_set=set(),
        select_key_prefix="board.select.ESCO",
        add_key_prefix="board.add.ESCO",
        empty_message="Keine ESCO-Vorschläge.",
    )

    assert selected == []
    assert fake_st.captions == ["Keine ESCO-Vorschläge."]


def test_render_compact_requirement_board_collects_selected_labels(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(ui_components, "st", fake_st)

    saved: list[str] = []
    selected = ui_components.render_compact_requirement_board(
        title_jobspec="Aus Jobspec extrahiert",
        jobspec_items=[{"label": "SQL"}],
        title_esco="ESCO",
        esco_items=[{"label": "Python"}],
        title_llm="AI-Vorschläge",
        llm_items=[{"label": "Teamfähigkeit", "rationale": "x", "evidence": "y"}],
        selected_labels=["Python"],
        selection_state_key="skills.bulk",
        save_callback=saved.append,
        key_prefix="skills.board",
    )

    assert selected == ["Python"]
    assert fake_st.session_state["skills.bulk"] == ["Python"]
    assert saved == []
