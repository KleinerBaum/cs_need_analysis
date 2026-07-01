"""Shared salary forecast sidebar renderer."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping, Sequence

import plotly.graph_objects as go  # type: ignore[import-untyped]
import streamlit as st
from streamlit.errors import StreamlitAPIException

from constants import SSKey
from salary.types import SalaryForecastDriver, SalaryForecastResult


def _hex_luminance(hex_color: str) -> float | None:
    normalized = hex_color.strip().lstrip("#")
    if len(normalized) == 3:
        normalized = "".join(char * 2 for char in normalized)
    if len(normalized) != 6:
        return None
    try:
        channels = [int(normalized[index : index + 2], 16) / 255 for index in (0, 2, 4)]
    except ValueError:
        return None

    linear_channels = [
        channel / 12.92
        if channel <= 0.03928
        else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return (
        0.2126 * linear_channels[0]
        + 0.7152 * linear_channels[1]
        + 0.0722 * linear_channels[2]
    )


def _theme_option(*option_names: str) -> str | None:
    for option_name in option_names:
        try:
            option_value = st.get_option(option_name)
        except (KeyError, RuntimeError, StreamlitAPIException):
            continue
        if option_value:
            return str(option_value)
    return None


def _plot_axis_theme_colors() -> dict[str, str]:
    theme_base = (_theme_option("theme.base") or "light").lower()
    sidebar_background = _theme_option(
        f"theme.{theme_base}.sidebar.backgroundColor",
        "theme.sidebar.backgroundColor",
        f"theme.{theme_base}.secondaryBackgroundColor",
        "theme.secondaryBackgroundColor",
        f"theme.{theme_base}.backgroundColor",
        "theme.backgroundColor",
    )
    text_color = _theme_option(
        f"theme.{theme_base}.sidebar.textColor",
        "theme.sidebar.textColor",
        f"theme.{theme_base}.textColor",
        "theme.textColor",
    )
    is_dark_background = (_hex_luminance(sidebar_background or "") or 1) < 0.45
    axis_color = text_color or ("#F9FAFB" if is_dark_background else "#262730")
    return {
        "axis": axis_color,
        "grid": "rgba(249, 250, 251, 0.28)"
        if is_dark_background
        else "rgba(38, 39, 48, 0.22)",
        "zero": "#F9FAFB" if is_dark_background else "#262730",
    }


def _apply_driver_chart_theme(fig: go.Figure) -> None:
    axis_theme = _plot_axis_theme_colors()
    fig.update_layout(
        xaxis_title=None,
        yaxis_title=None,
        margin=dict(l=4, r=4, t=4, b=4),
        height=220,
        showlegend=False,
        paper_bgcolor="rgba(0, 0, 0, 0)",
        plot_bgcolor="rgba(0, 0, 0, 0)",
        font_color=axis_theme["axis"],
    )
    fig.update_xaxes(
        tickformat=",.0f",
        tickfont=dict(color=axis_theme["axis"]),
        tickcolor=axis_theme["axis"],
        linecolor=axis_theme["axis"],
        gridcolor=axis_theme["grid"],
        zeroline=True,
        zerolinecolor=axis_theme["zero"],
        zerolinewidth=1,
    )
    fig.update_yaxes(
        tickfont=dict(color=axis_theme["axis"]),
        tickcolor=axis_theme["axis"],
        linecolor=axis_theme["axis"],
        gridcolor=axis_theme["grid"],
        zerolinecolor=axis_theme["zero"],
    )


def _format_salary(value: float, currency: str) -> str:
    return f"{int(value):,} {currency}".replace(",", ".")


def _format_delta(value: float, currency: str) -> str:
    if abs(value) < 500:
        return f"kaum Einfluss ({_format_salary(0, currency)})"
    sign = "+" if value > 0 else "-"
    return f"{sign}{_format_salary(abs(value), currency)}"


def _period_label(period: str) -> str:
    normalized = period.strip().lower()
    if normalized in {"month", "monthly", "monat", "monatlich"}:
        return "Monat"
    return "Jahr"


def _driver_label(driver: SalaryForecastDriver) -> str:
    labels = {
        "requirements_density": "Anforderungen",
        "seniority": "Erfahrung",
        "remote_policy": "Remote-Regel",
        "interview_process": "Auswahlprozess",
        "search_radius": "Suchradius",
        "esco_skill_premiums": "Besondere Skills",
        "location": "Standort",
        "job_title": "Rolle",
    }
    return labels.get(driver.key, driver.label)


def _driver_help(driver: SalaryForecastDriver) -> str:
    help_texts = {
        "requirements_density": "Mehr Muss-Anforderungen erhöhen meist die Gehaltserwartung.",
        "seniority": "Mehr Verantwortung oder Erfahrung verschiebt die Mitte nach oben.",
        "remote_policy": "Remote-Angebote können den Marktvergleich leicht verändern.",
        "interview_process": "Ein langer Auswahlprozess ist ein schwaches Signal für höhere Anforderungen.",
        "search_radius": "Ein größerer Suchradius verändert den lokalen Marktvergleich.",
        "esco_skill_premiums": "Seltene oder nachgefragte Skills können einen Aufschlag auslösen.",
        "location": "Regionale Gehaltsniveaus werden grob berücksichtigt.",
        "job_title": "Die Rollenbezeichnung steuert die passende Vergleichsgruppe.",
    }
    return help_texts.get(driver.key, driver.detail)


def _quality_label(quality_percent: int) -> str:
    if quality_percent >= 75:
        return "gute Orientierung"
    if quality_percent >= 55:
        return "brauchbare Orientierung"
    return "erste grobe Orientierung"


def _top_driver_rows(
    forecast: SalaryForecastResult, *, limit: int = 5
) -> list[dict[str, str | float]]:
    rows: list[dict[str, str | float]] = []
    for driver in forecast.drivers:
        try:
            impact_eur = float(driver.impact_eur)
        except (TypeError, ValueError):
            impact_eur = 0.0
        rows.append(
            {
                "Faktor": _driver_label(driver),
                "Einfluss": impact_eur,
                "Einschätzung": _format_delta(impact_eur, forecast.currency),
                "Hinweis": _driver_help(driver),
            }
        )
    return sorted(rows, key=lambda row: abs(float(row["Einfluss"])), reverse=True)[
        :limit
    ]


def _row_value(row: Any, field_name: str, default: Any = None) -> Any:
    if isinstance(row, Mapping):
        return row.get(field_name, default)
    return getattr(row, field_name, default)


def _group_input_rows(input_rows: Sequence[Any]) -> dict[str, list[Any]]:
    grouped: dict[str, list[Any]] = defaultdict(list)
    for row in input_rows:
        group = str(_row_value(row, "group", "Weitere Werte") or "Weitere Werte")
        grouped[group].append(row)
    return dict(grouped)


def _row_display_label(row: Any, *, strip_prefix: bool) -> str:
    row_id = str(_row_value(row, "id"))
    label = str(_row_value(row, "label", row_id))
    if not strip_prefix:
        return label
    display_value = str(_row_value(row, "display_value", "") or "").strip()
    if display_value:
        return display_value
    label_prefix = str(_row_value(row, "label_prefix", "") or "").strip()
    prefix = f"{label_prefix}:"
    if label_prefix and label.startswith(prefix):
        return label[len(prefix) :].strip()
    return label


def _ordered_prefix_groups(rows: Sequence[Any]) -> list[tuple[str, list[Any]]]:
    grouped: dict[str, list[Any]] = {}
    for row in rows:
        label_prefix = str(_row_value(row, "label_prefix", "") or "").strip()
        grouped.setdefault(label_prefix, []).append(row)
    return list(grouped.items())


def _render_sidebar_input_checkbox(
    row: Any,
    *,
    next_selections: dict[str, bool],
    strip_prefix: bool,
) -> None:
    row_id = str(_row_value(row, "id"))
    source_label = str(_row_value(row, "source_label", "") or "")
    current_value = bool(
        next_selections.get(row_id, bool(_row_value(row, "default_enabled", True)))
    )
    widget_key = f"{SSKey.SALARY_FORECAST_INPUT_SELECTIONS.value}.{row_id}"
    checked = st.checkbox(
        _row_display_label(row, strip_prefix=strip_prefix),
        value=current_value,
        key=widget_key,
        help=source_label or None,
    )
    next_selections[row_id] = bool(checked)


def _driver_summary(rows: Sequence[dict[str, str | float]]) -> str:
    strongest = [
        f"{row['Faktor']} ({row['Einschätzung']})"
        for row in rows[:3]
        if str(row.get("Faktor", "")).strip()
    ]
    if not strongest:
        return ""
    return "Stärkste Treiber: " + "; ".join(strongest) + "."


def _render_sidebar_input_selection(
    *,
    input_rows: Sequence[Any],
    input_selections: Mapping[str, bool],
) -> dict[str, bool]:
    grouped_rows = _group_input_rows(input_rows)
    next_selections = dict(input_selections)
    group_order = [
        "Rolle & Standort",
        "Aufgaben",
        "Skills",
        "Benefits",
        "Interview",
        "ESCO",
        "Szenario",
    ]
    ordered_groups = [
        group for group in group_order if group in grouped_rows
    ] + sorted(group for group in grouped_rows if group not in group_order)

    st.sidebar.markdown("**Genutzte Werte**")
    st.sidebar.caption("Aktive Werte fließen in die nächste Berechnung ein.")
    for group in ordered_groups:
        rows = grouped_rows[group]
        active_count = sum(
            1
            for row in rows
            if bool(
                next_selections.get(
                    str(_row_value(row, "id")),
                    bool(_row_value(row, "default_enabled", True)),
                )
            )
        )
        with st.sidebar.expander(
            f"{group} ({active_count}/{len(rows)} aktiv)",
            expanded=group in {"Rolle & Standort", "Skills"},
        ):
            for label_prefix, prefix_rows in _ordered_prefix_groups(rows):
                strip_prefix = bool(label_prefix and len(prefix_rows) > 1)
                if strip_prefix:
                    st.markdown(f"**{label_prefix} ({len(prefix_rows)})**")
                for row in prefix_rows:
                    _render_sidebar_input_checkbox(
                        row,
                        next_selections=next_selections,
                        strip_prefix=strip_prefix,
                    )
    st.session_state[SSKey.SALARY_FORECAST_INPUT_SELECTIONS.value] = next_selections
    return next_selections


def render_sidebar_salary_forecast(
    *,
    forecast: SalaryForecastResult | None,
    input_rows: Sequence[Any],
    input_selections: Mapping[str, bool],
    is_stale: bool,
) -> bool:
    """Render salary forecast controls in the sidebar without computing domain data."""

    st.sidebar.markdown("### Gehaltsprognose")
    status_label = (
        "Noch nicht berechnet"
        if forecast is None
        else "Neue gespeicherte Werte verfügbar"
        if is_stale
        else ""
    )
    if status_label:
        st.sidebar.caption(status_label)

    active_count = sum(
        1
        for row in input_rows
        if bool(
            input_selections.get(
                str(_row_value(row, "id")),
                bool(_row_value(row, "default_enabled", True)),
            )
        )
    )
    update_requested = st.sidebar.button(
        "Update berechnen",
        type="primary",
        disabled=not input_rows,
        help="Berechnet die Prognose mit den aktuell aktivierten Werten neu.",
    )

    if forecast is None:
        st.sidebar.info(
            "Noch kein Orientierungswert vorhanden. Wähle die relevanten Werte aus und starte die Berechnung."
        )
    else:
        period_label = _period_label(forecast.period)
        st.sidebar.metric(
            f"Orientierungswert ({period_label})",
            _format_salary(forecast.forecast.p50, forecast.currency),
        )
        st.sidebar.metric(
            "Realistische Spanne",
            (
                f"{_format_salary(forecast.forecast.p10, forecast.currency)} bis "
                f"{_format_salary(forecast.forecast.p90, forecast.currency)}"
            ),
        )
        quality_percent = int(round(float(forecast.quality.value) * 100, 0))
        st.sidebar.progress(
            quality_percent,
            text=f"Datenbasis: {quality_percent}% ({_quality_label(quality_percent)})",
        )
        st.sidebar.caption(
            f"Berechnet für {forecast.job_title}; Standort: {forecast.location}; "
            f"{forecast.must_have_count} Must-have-Skills; "
            f"{forecast.answers_count} aktive Eingaben."
        )

        st.sidebar.markdown("**Einfluss auf die Schätzung**")
        top_rows = _top_driver_rows(forecast)
        try:
            fig = go.Figure(
                go.Bar(
                    orientation="h",
                    x=[float(row["Einfluss"]) for row in reversed(top_rows)],
                    y=[str(row["Faktor"]) for row in reversed(top_rows)],
                    text=[str(row["Einschätzung"]) for row in reversed(top_rows)],
                    textposition="auto",
                    marker_color=[
                        "#2E7D32" if float(row["Einfluss"]) >= 0 else "#C62828"
                        for row in reversed(top_rows)
                    ],
                )
            )
            _apply_driver_chart_theme(fig)
            st.sidebar.plotly_chart(
                fig,
                width="stretch",
                key=f"{SSKey.SALARY_FORECAST_LAST_RESULT.value}_drivers",
            )
        except Exception:
            st.sidebar.dataframe(top_rows, width="stretch", hide_index=True)
        summary = _driver_summary(top_rows)
        if summary:
            st.sidebar.caption(summary)

    next_selections = _render_sidebar_input_selection(
        input_rows=input_rows,
        input_selections=input_selections,
    )
    active_count = sum(
        1
        for row in input_rows
        if bool(
            next_selections.get(
                str(_row_value(row, "id")),
                bool(_row_value(row, "default_enabled", True)),
            )
        )
    )
    st.sidebar.caption(f"{active_count}/{len(input_rows)} gespeicherte Werte aktiv.")
    return bool(update_requested)
