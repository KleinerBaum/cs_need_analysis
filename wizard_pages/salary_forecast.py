"""Shared salary forecast sidebar renderer."""

from __future__ import annotations

import plotly.graph_objects as go  # type: ignore[import-untyped]
import streamlit as st

from constants import SSKey
from salary.types import SalaryForecastDriver, SalaryForecastResult


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


def render_sidebar_salary_forecast(*, forecast: SalaryForecastResult) -> None:
    """Render a salary forecast in the sidebar without computing domain data."""
    st.session_state[SSKey.SALARY_FORECAST_LAST_RESULT.value] = forecast.model_dump(
        mode="json"
    )

    period_label = _period_label(forecast.period)

    st.sidebar.markdown("### Gehaltsprognose")
    st.sidebar.caption(
        "Aktualisiert sich automatisch mit den bisher erfassten Stelleninfos."
    )
    st.sidebar.metric(
        f"Orientierungswert ({period_label})",
        _format_salary(forecast.forecast.p50, forecast.currency),
    )
    st.sidebar.write(
        "**Realistische Spanne:** "
        f"{_format_salary(forecast.forecast.p10, forecast.currency)} bis "
        f"{_format_salary(forecast.forecast.p90, forecast.currency)}"
    )
    quality_percent = int(round(float(forecast.quality.value) * 100, 0))
    st.sidebar.progress(
        quality_percent,
        text=f"Datenbasis: {quality_percent}% ({_quality_label(quality_percent)})",
    )
    st.sidebar.caption(
        f"Berücksichtigt: {forecast.job_title}, {forecast.location}, "
        f"{forecast.must_have_count} Muss-Skills, "
        f"{forecast.answers_count} beantwortete Felder."
    )
    with st.sidebar.expander("Was verändert das Gehalt?", expanded=True):
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
            fig.update_layout(
                xaxis_title=None,
                yaxis_title=None,
                margin=dict(l=4, r=4, t=4, b=4),
                height=220,
                showlegend=False,
            )
            fig.update_xaxes(tickformat=",.0f", zeroline=True, zerolinewidth=1)
            st.plotly_chart(
                fig,
                width="stretch",
                key=f"{SSKey.SALARY_FORECAST_LAST_RESULT.value}_drivers",
            )
        except Exception:
            st.dataframe(top_rows, width="stretch", hide_index=True)
        for row in top_rows[:3]:
            st.caption(
                f"**{row['Faktor']}:** {row['Einschätzung']} - {row['Hinweis']}"
            )
    with st.sidebar.expander("Was heißt das?", expanded=False):
        st.write(
            "- Der große Wert ist die Mitte der aktuellen Schätzung.\n"
            "- Die Spanne zeigt, womit du im Markt grob rechnen solltest.\n"
            "- Skills, Anforderungen, Standort und Rolle können den Wert sofort verändern.\n"
            "- Die Prognose ist eine Orientierung und ersetzt kein externes Vergütungsbenchmarking."
        )
