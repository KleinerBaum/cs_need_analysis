"""Shared salary forecast helpers for sidebar rendering across wizard steps."""

from __future__ import annotations

from typing import Any

import streamlit as st

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
    if job.salary_range and job.salary_range.min and job.salary_range.max:
        return (job.salary_range.min + job.salary_range.max) / 2
    if job.salary_range and job.salary_range.max:
        return job.salary_range.max
    if job.salary_range and job.salary_range.min:
        return job.salary_range.min

    seniority = (job.seniority_level or "").lower()
    if "lead" in seniority or "principal" in seniority:
        return 105_000
    if "senior" in seniority:
        return 90_000
    if "junior" in seniority:
        return 60_000
    return 75_000


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


def _location_salary_multiplier(location: str) -> float:
    location_lower = location.lower()
    if any(marker in location_lower for marker in ("schweiz", "switzerland", "zurich")):
        return 1.22
    if any(
        marker in location_lower
        for marker in ("usa", "united states", "san francisco", "new york")
    ):
        return 1.28
    if any(
        marker in location_lower
        for marker in (
            "deutschland",
            "germany",
            "münchen",
            "munich",
            "berlin",
            "hamburg",
        )
    ):
        return 1.07
    if any(marker in location_lower for marker in ("eu", "europe")):
        return 1.03
    return 1.0


def _title_salary_multiplier(job_title: str) -> float:
    title = job_title.lower()
    if any(
        marker in title
        for marker in ("engineer", "entwickler", "scientist", "ai", "ml")
    ):
        return 1.08
    if any(marker in title for marker in ("director", "head", "leiter")):
        return 1.14
    if any(marker in title for marker in ("assistant", "associate", "support")):
        return 0.92
    return 1.0


def _count_meaningful_answers(answers: dict[str, Any]) -> int:
    return sum(1 for value in answers.values() if _has_meaningful_value(value))


def build_salary_forecast_snapshot(
    job: JobAdExtract, answers: dict[str, Any]
) -> dict[str, float | int | str]:
    base_salary = _estimate_salary_baseline(job)
    must_have_count = len(job.must_have_skills)
    interview_steps = len(job.recruitment_steps)
    answers_count = _count_meaningful_answers(answers)
    responsibilities_count = len(job.responsibilities)
    requirements_density = (
        must_have_count + len(job.certifications) + len(job.languages)
    )

    salary_multiplier = 1.0
    if requirements_density > 8:
        salary_multiplier += 0.09
    elif requirements_density > 4:
        salary_multiplier += 0.05

    seniority = (job.seniority_level or "").lower()
    if "lead" in seniority or "principal" in seniority:
        salary_multiplier += 0.12
    elif "senior" in seniority:
        salary_multiplier += 0.06
    elif "junior" in seniority:
        salary_multiplier -= 0.08

    remote_policy = (job.remote_policy or "").lower()
    if "remote" in remote_policy:
        salary_multiplier += 0.03
    if interview_steps >= 5:
        salary_multiplier += 0.02

    salary_multiplier *= _location_salary_multiplier(job.location_country or "")
    salary_multiplier *= _title_salary_multiplier(job.job_title or "")

    forecast_central = max(35_000.0, base_salary * salary_multiplier)
    spread_factor = 0.08 + min(0.14, max(0.0, (10 - min(answers_count, 10)) * 0.012))
    forecast_min = max(35_000.0, forecast_central * (1 - spread_factor))
    forecast_max = forecast_central * (1 + spread_factor)

    confidence = min(
        100,
        max(
            35,
            35
            + min(45, answers_count * 4)
            + (12 if bool(job.salary_range) else 0)
            + min(8, requirements_density)
            + min(8, responsibilities_count),
        ),
    )

    return {
        "forecast_min": round(forecast_min, 0),
        "forecast_central": round(forecast_central, 0),
        "forecast_max": round(forecast_max, 0),
        "confidence": int(confidence),
        "answers_count": answers_count,
        "must_have_count": must_have_count,
        "interview_steps": interview_steps,
        "location": (job.location_country or "Nicht angegeben"),
        "seniority": (job.seniority_level or "Nicht angegeben"),
        "job_title": (job.job_title or "Nicht angegeben"),
        "currency": (job.salary_range.currency if job.salary_range else None) or "EUR",
    }


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
