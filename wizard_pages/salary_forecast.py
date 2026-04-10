"""Shared salary forecast sidebar renderer."""

from __future__ import annotations

import streamlit as st

from constants import SSKey
from salary.types import SalaryForecastResult


def render_sidebar_salary_forecast(*, forecast: SalaryForecastResult) -> None:
    """Render a salary forecast in the sidebar without computing domain data."""
    st.session_state[SSKey.SALARY_FORECAST_LAST_RESULT.value] = forecast.model_dump(
        mode="json"
    )

    st.sidebar.markdown("### 💶 Gehaltsvorcast")
    st.sidebar.caption("Kompakte Prognose auf Basis der bisher erfassten Stelleninfos.")
    st.sidebar.metric(
        "Prognose (Jahr, Mitte)",
        f"{int(forecast.forecast.p50):,} {forecast.currency}".replace(",", "."),
    )
    st.sidebar.write(
        f"**Bandbreite:** {int(forecast.forecast.p10):,} – {int(forecast.forecast.p90):,} {forecast.currency}".replace(
            ",", "."
        )
    )
    quality_percent = int(round(float(forecast.quality.value) * 100, 0))
    st.sidebar.progress(
        quality_percent,
        text=f"Prognose-Sicherheit: {quality_percent}%",
    )
    st.sidebar.caption(
        "Treiber: "
        f"{forecast.must_have_count} Must-haves · "
        f"{forecast.interview_steps} Interview-Schritte · "
        f"{forecast.answers_count} beantwortete Wizard-Felder · "
        f"Standort: {forecast.location}"
    )
    with st.sidebar.expander("Annahmen", expanded=False):
        st.write(
            "- Prognose ist indikativ und ersetzt kein externes Markt-Benchmarking.\n"
            "- Standort, Jobtitel, Seniorität sowie Aufgaben/Anforderungen beeinflussen die Gehaltsmitte.\n"
            "- Mehr vollständige Angaben erhöhen die Prognose-Sicherheit."
        )
