"""Shared salary forecast sidebar renderer."""

from __future__ import annotations

import plotly.graph_objects as go  # type: ignore[import-untyped]
import streamlit as st

from constants import SSKey
from salary.types import SalaryForecastResult


def _format_salary(value: float, currency: str) -> str:
    return f"{int(value):,} {currency}".replace(",", ".")


def _period_label(period: str) -> str:
    normalized = period.strip().lower()
    if normalized in {"month", "monthly", "monat", "monatlich"}:
        return "Monat"
    return "Jahr"


def _drivers_rows(forecast: SalaryForecastResult) -> list[dict[str, str | float]]:
    rows: list[dict[str, str | float]] = []
    for driver in forecast.drivers:
        impact_eur_raw = getattr(driver, "impact_eur", 0.0)
        try:
            impact_eur = float(impact_eur_raw)
        except (TypeError, ValueError):
            impact_eur = 0.0
        rows.append(
            {
                "Treiber": driver.label,
                "Kategorie": driver.category or "Sonstiges",
                "Einfluss (EUR)": round(impact_eur, 2),
            }
        )
    return rows


def render_sidebar_salary_forecast(*, forecast: SalaryForecastResult) -> None:
    """Render a salary forecast in the sidebar without computing domain data."""
    st.session_state[SSKey.SALARY_FORECAST_LAST_RESULT.value] = forecast.model_dump(
        mode="json"
    )

    period_label = _period_label(forecast.period)

    st.sidebar.markdown("### 💶 Gehaltsprognose")
    st.sidebar.caption(
        "Indikative Prognose auf Basis der bisher erfassten Stelleninfos."
    )
    st.sidebar.metric(
        f"Indikative Mitte ({period_label}, p50)",
        _format_salary(forecast.forecast.p50, forecast.currency),
    )
    st.sidebar.write(
        f"**Bandbreite:** {_format_salary(forecast.forecast.p10, forecast.currency)} "
        f"– {_format_salary(forecast.forecast.p90, forecast.currency)}"
    )
    quality_percent = int(round(float(forecast.quality.value) * 100, 0))
    st.sidebar.progress(
        quality_percent,
        text=f"Datenqualität: {quality_percent}%",
    )
    st.sidebar.caption(f"Qualitätsart: `{forecast.quality.kind}`")
    st.sidebar.caption(
        "Treiber: "
        f"{forecast.must_have_count} Must-haves · "
        f"{forecast.interview_steps} Interview-Schritte · "
        f"{forecast.answers_count} beantwortete Wizard-Felder · "
        f"Standort: {forecast.location}"
    )
    st.sidebar.caption(
        "Quelle: "
        f"{forecast.provenance.benchmark_source_label or forecast.provenance.benchmark_version} "
        f"({forecast.provenance.benchmark_year or 'n/a'}) · "
        f"Mapping: occ={forecast.provenance.occupation_id or forecast.provenance.occupation_mapping}, "
        f"reg={forecast.provenance.region_id or forecast.provenance.region_mapping}"
    )
    with st.sidebar.expander("Warum?", expanded=False):
        drivers_rows = _drivers_rows(forecast)
        try:
            fig = go.Figure(
                go.Waterfall(
                    name="Einfluss",
                    orientation="v",
                    measure=["absolute", *["relative"] * len(drivers_rows), "total"],
                    x=[
                        "Basis",
                        *[
                            f"{row['Treiber']} ({row['Kategorie']})"
                            for row in drivers_rows
                        ],
                        "Final p50",
                    ],
                    y=[
                        float(forecast.base_salary),
                        *[float(row["Einfluss (EUR)"]) for row in drivers_rows],
                        0.0,
                    ],
                )
            )
            fig.update_layout(
                margin=dict(l=8, r=8, t=8, b=8),
                height=250,
                showlegend=False,
            )
            st.plotly_chart(
                fig,
                width="stretch",
                key=f"{SSKey.SALARY_FORECAST_LAST_RESULT.value}_waterfall",
            )
        except Exception:
            st.dataframe(drivers_rows, width="stretch", hide_index=True)
    with st.sidebar.expander("Annahmen & Datenqualität", expanded=False):
        st.write(
            "- Prognose ist indikativ und ersetzt kein externes Markt-Benchmarking.\n"
            "- Standort, Jobtitel, Seniorität sowie Aufgaben/Anforderungen beeinflussen die Gehaltsmitte.\n"
            "- Mehr vollständige Angaben erhöhen die Datenqualität des Ergebnisses (nicht die statistische Sicherheit)."
        )
