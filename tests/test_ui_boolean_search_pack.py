from __future__ import annotations

from typing import Any

import ui_components
import ui_summary_artifacts
from schemas import BooleanSearchPack


class _NoopContext:
    def __enter__(self) -> "_NoopContext":
        return self

    def __exit__(self, *_: object) -> bool:
        return False


class _FakeExpander(_NoopContext):
    def __init__(self, owner: "_FakeStreamlit", label: str, expanded: bool) -> None:
        self._owner = owner
        self._label = label
        self._expanded = expanded

    def __enter__(self) -> "_FakeExpander":
        self._owner.expander_calls.append((self._label, self._expanded))
        return self


class _FakeStreamlit:
    def __init__(self) -> None:
        self.info_calls: list[str] = []
        self.code_calls: list[str] = []
        self.expander_calls: list[tuple[str, bool]] = []

    def markdown(self, *_: Any, **__: Any) -> None:
        return None

    def caption(self, *_: Any, **__: Any) -> None:
        return None

    def write(self, *_: Any, **__: Any) -> None:
        return None

    def info(self, message: str, *_: Any, **__: Any) -> None:
        self.info_calls.append(message)

    def code(self, body: str, *_: Any, **__: Any) -> None:
        self.code_calls.append(body)

    def columns(self, count: int) -> list[_NoopContext]:
        return [_NoopContext() for _ in range(count)]

    def expander(self, label: str, *, expanded: bool = False) -> _FakeExpander:
        return _FakeExpander(self, label, expanded)


def _pack(**overrides: Any) -> BooleanSearchPack:
    payload = {
        "role_title": "Data Engineer",
        "target_locations": ["Berlin"],
        "seniority_terms": ["Senior"],
        "must_have_terms": ["Python"],
        "exclusion_terms": ["intern"],
        "google": {"broad": [], "focused": [], "fallback": []},
        "linkedin": {"broad": [], "focused": [], "fallback": []},
        "xing": {"broad": [], "focused": [], "fallback": []},
        "channel_limitations": [],
        "usage_notes": [],
    }
    payload.update(overrides)
    return BooleanSearchPack.model_validate(payload)


def test_first_boolean_query_uses_priority_order() -> None:
    pack = _pack(
        linkedin={"broad": ["li-broad"], "focused": ["li-focus"], "fallback": []},
        google={"broad": ["g-broad"], "focused": [], "fallback": []},
    )

    assert ui_components._first_boolean_query(pack) == (
        "LinkedIn",
        "Focused",
        "li-focus",
    )


def test_render_boolean_search_pack_shows_empty_message(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(ui_summary_artifacts, "st", fake_st)
    assert (
        ui_components.render_boolean_search_pack
        is ui_summary_artifacts.render_boolean_search_pack
    )

    ui_components.render_boolean_search_pack(
        _pack(
            google={"broad": [], "focused": [], "fallback": ["g-x"]},
            linkedin={"broad": [], "focused": [], "fallback": ["li-x"]},
            xing={"broad": [], "focused": [], "fallback": ["x-x"]},
        )
    )

    assert "Keine Boolean-Suchstrings vorhanden." in fake_st.info_calls
    assert fake_st.code_calls == []


def test_render_boolean_search_pack_renders_visible_queries_only(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(ui_summary_artifacts, "st", fake_st)
    pack = _pack(
        google={"broad": ["g-b1", "g-b2"], "focused": ["g-f1"], "fallback": ["g-x"]},
        linkedin={"broad": ["li-b"], "focused": [], "fallback": ["li-x"]},
        xing={"broad": [], "focused": ["x-f"], "fallback": []},
    )

    ui_components.render_boolean_search_pack(pack)

    assert set(fake_st.code_calls) == {"g-b1", "g-b2", "g-f1", "li-b", "x-f"}
    assert "g-x" not in fake_st.code_calls
    assert "li-x" not in fake_st.code_calls
    assert fake_st.expander_calls == [
        ("Fokussiert", False),
        ("Fokussiert", False),
        ("Fokussiert", False),
    ]
