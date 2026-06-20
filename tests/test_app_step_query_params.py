from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import app
from constants import WIZARD_STEP_QUERY_PARAM


class _FakeQueryParams(dict[str, Any]):
    pass


class _FakeStreamlit:
    def __init__(self, query_params: dict[str, Any]) -> None:
        self.query_params = _FakeQueryParams(query_params)


class _FakeContext:
    def __init__(self) -> None:
        self.pages = [
            SimpleNamespace(key="landing"),
            SimpleNamespace(key="company"),
            SimpleNamespace(key="skills"),
        ]
        self.goto_calls: list[str] = []

    def goto(self, key: str) -> None:
        self.goto_calls.append(key)


def test_consume_wizard_step_query_param_navigates_and_clears_only_step(
    monkeypatch,
) -> None:
    fake_st = _FakeStreamlit(
        {
            WIZARD_STEP_QUERY_PARAM: "skills",
            "page": "preferences",
        }
    )
    ctx = _FakeContext()
    monkeypatch.setattr(app, "st", fake_st)

    app._consume_wizard_step_query_param(ctx)

    assert ctx.goto_calls == ["skills"]
    assert WIZARD_STEP_QUERY_PARAM not in fake_st.query_params
    assert fake_st.query_params["page"] == "preferences"


def test_consume_wizard_step_query_param_clears_invalid_stale_step(
    monkeypatch,
) -> None:
    fake_st = _FakeStreamlit({WIZARD_STEP_QUERY_PARAM: "legacy_team"})
    ctx = _FakeContext()
    monkeypatch.setattr(app, "st", fake_st)

    app._consume_wizard_step_query_param(ctx)

    assert ctx.goto_calls == []
    assert WIZARD_STEP_QUERY_PARAM not in fake_st.query_params


def test_consume_wizard_step_query_param_uses_first_repeated_value(monkeypatch) -> None:
    fake_st = _FakeStreamlit({WIZARD_STEP_QUERY_PARAM: ["company", "skills"]})
    ctx = _FakeContext()
    monkeypatch.setattr(app, "st", fake_st)

    app._consume_wizard_step_query_param(ctx)

    assert ctx.goto_calls == ["company"]
