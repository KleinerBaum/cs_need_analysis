"""Shared salary forecast helpers for sidebar rendering across wizard steps."""

from __future__ import annotations

from typing import Any

import streamlit as st

from salary.engine import compute_salary_forecast, estimate_salary_baseline
from schemas import JobAdExtract


def _has_meaningful_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _estimate_salary_baseline(job: JobAdExtract) -> float:
    return estimate_salary_baseline(job)


def _fallback_job_from_session(
    *, answers: dict[str, Any], source_text: str
) -> JobAdExtract | None:
    seniority_hint = ""
    location_hint = ""
    job_title_hint = ""
    for key, value in answers.items():
        if not _has_meaningful_value(value):
            continue
        normalized_key = str(key).lower()
        value_text = str(value).strip()
        if not seniority_hint and "senior" in normalized_key:
            seniority_hint = value_text
        if not location_hint and (
            "location" in normalized_key or "standort" in normalized_key
        ):
            location_hint = value_text
        if not job_title_hint and (
            "job_title" in normalized_key or "rolle" in normalized_key
        ):
            job_title_hint = value_text

    source_lower = source_text.lower()
    if not seniority_hint:
        for marker in ("principal", "lead", "senior", "junior"):
            if marker in source_lower:
                seniority_hint = marker
                break
    if not job_title_hint and source_text.strip():
        first_line = source_text.strip().splitlines()[0]
        job_title_hint = first_line[:90]

    if not any((seniority_hint, location_hint, job_title_hint, source_text.strip())):
        return None

    return JobAdExtract(
        job_title=job_title_hint or None,
        location_country=location_hint or None,
        seniority_level=seniority_hint or None,
    )


def build_salary_forecast_snapshot(
    job: JobAdExtract, answers: dict[str, Any]
) -> dict[str, float | int | str]:
    return compute_salary_forecast(job_extract=job, answers=answers).model_dump()


def render_sidebar_salary_forecast(
    *,
    job: JobAdExtract | None,
    answers: dict[str, Any],
    source_text: str = "",
) -> None:
    fallback_job = _fallback_job_from_session(answers=answers, source_text=source_text)
    forecast_job = job or fallback_job
    if forecast_job is None:
        return

    forecast = build_salary_forecast_snapshot(job=forecast_job, answers=answers)

    st.sidebar.markdown("### 💶 Gehaltsvorcast")
    st.sidebar.caption("Kompakte Prognose auf Basis der bisher erfassten Stelleninfos.")
    st.sidebar.metric(
        "Prognose (Jahr, Mitte)",
        f"{int(forecast['forecast_central']):,} {forecast['currency']}".replace(
            ",", "."
        ),
    )
    st.sidebar.write(
        f"**Bandbreite:** {int(forecast['forecast_min']):,} – {int(forecast['forecast_max']):,} {forecast['currency']}".replace(
            ",", "."
        )
    )
    st.sidebar.progress(
        int(forecast["confidence"]),
        text=f"Prognose-Sicherheit: {forecast['confidence']}%",
    )
    st.sidebar.caption(
        "Treiber: "
        f"{forecast['must_have_count']} Must-haves · "
        f"{forecast['interview_steps']} Interview-Schritte · "
        f"{forecast['answers_count']} beantwortete Wizard-Felder · "
        f"Standort: {forecast['location']}"
    )
    with st.sidebar.expander("Annahmen", expanded=False):
        st.write(
            "- Prognose ist indikativ und ersetzt kein externes Markt-Benchmarking.\n"
            "- Standort, Jobtitel, Seniorität sowie Aufgaben/Anforderungen beeinflussen die Gehaltsmitte.\n"
            "- Mehr vollständige Angaben erhöhen die Prognose-Sicherheit."
        )
