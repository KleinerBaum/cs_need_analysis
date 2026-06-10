from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

import wizard_pages.salary_forecast as salary_forecast


class _ThemeStreamlit:
    def __init__(self, options: dict[str, Any]) -> None:
        self._options = options

    def get_option(self, option_name: str) -> Any:
        return self._options.get(option_name)


def _patch_theme(monkeypatch, *, base: str, background: str, text: str) -> None:
    monkeypatch.setattr(
        salary_forecast,
        "st",
        _ThemeStreamlit(
            {
                "theme.base": base,
                f"theme.{base}.sidebar.backgroundColor": background,
                f"theme.{base}.sidebar.textColor": text,
            }
        ),
    )


def test_driver_chart_theme_uses_light_sidebar_contrast(monkeypatch) -> None:
    _patch_theme(
        monkeypatch, base="light", background="#12263A", text="#FFFFFF"
    )
    fig = go.Figure()

    salary_forecast._apply_driver_chart_theme(fig)

    assert fig.layout.paper_bgcolor == "rgba(0, 0, 0, 0)"
    assert fig.layout.plot_bgcolor == "rgba(0, 0, 0, 0)"
    assert fig.layout.font.color == "#FFFFFF"
    assert fig.layout.xaxis.tickfont.color == "#FFFFFF"
    assert fig.layout.xaxis.tickcolor == "#FFFFFF"
    assert fig.layout.xaxis.linecolor == "#FFFFFF"
    assert fig.layout.xaxis.gridcolor == "rgba(249, 250, 251, 0.28)"
    assert fig.layout.xaxis.zerolinecolor == "#F9FAFB"
    assert fig.layout.yaxis.tickfont.color == "#FFFFFF"
    assert fig.layout.yaxis.tickcolor == "#FFFFFF"
    assert fig.layout.yaxis.linecolor == "#FFFFFF"
    assert fig.layout.yaxis.gridcolor == "rgba(249, 250, 251, 0.28)"
    assert fig.layout.yaxis.zerolinecolor == "#F9FAFB"


def test_driver_chart_theme_uses_dark_sidebar_contrast(monkeypatch) -> None:
    _patch_theme(monkeypatch, base="dark", background="#101820", text="#F8FAFC")
    fig = go.Figure()

    salary_forecast._apply_driver_chart_theme(fig)

    assert fig.layout.paper_bgcolor == "rgba(0, 0, 0, 0)"
    assert fig.layout.plot_bgcolor == "rgba(0, 0, 0, 0)"
    assert fig.layout.font.color == "#F8FAFC"
    assert fig.layout.xaxis.tickfont.color == "#F8FAFC"
    assert fig.layout.xaxis.tickcolor == "#F8FAFC"
    assert fig.layout.xaxis.linecolor == "#F8FAFC"
    assert fig.layout.xaxis.gridcolor == "rgba(249, 250, 251, 0.28)"
    assert fig.layout.xaxis.zerolinecolor == "#F9FAFB"
    assert fig.layout.yaxis.tickfont.color == "#F8FAFC"
    assert fig.layout.yaxis.tickcolor == "#F8FAFC"
    assert fig.layout.yaxis.linecolor == "#F8FAFC"
    assert fig.layout.yaxis.gridcolor == "rgba(249, 250, 251, 0.28)"
    assert fig.layout.yaxis.zerolinecolor == "#F9FAFB"
