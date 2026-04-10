"""Domain salary forecast engine without UI dependencies."""

from __future__ import annotations

from typing import Any

from schemas import JobAdExtract

from salary.types import SalaryForecastResult, SalaryScenarioOverrides


def _has_meaningful_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _count_meaningful_answers(answers: dict[str, Any]) -> int:
    return sum(1 for value in answers.values() if _has_meaningful_value(value))


def estimate_salary_baseline(job: JobAdExtract) -> float:
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


def compute_salary_forecast(
    job_extract: JobAdExtract,
    answers: dict,
    scenario_overrides: SalaryScenarioOverrides | None = None,
) -> SalaryForecastResult:
    """Compute salary forecast from normalized job extract and wizard answers."""

    overrides = scenario_overrides or SalaryScenarioOverrides()
    base_salary = estimate_salary_baseline(job_extract)
    must_have_count = len(job_extract.must_have_skills)
    interview_steps = len(job_extract.recruitment_steps)
    answers_count = _count_meaningful_answers(answers)
    responsibilities_count = len(job_extract.responsibilities)
    requirements_density = (
        must_have_count + len(job_extract.certifications) + len(job_extract.languages)
    )

    requirements_multiplier = 0.0
    if requirements_density > 8:
        requirements_multiplier = 0.09
    elif requirements_density > 4:
        requirements_multiplier = 0.05

    seniority = (job_extract.seniority_level or "").lower()
    seniority_multiplier = 0.0
    if "lead" in seniority or "principal" in seniority:
        seniority_multiplier = 0.12
    elif "senior" in seniority:
        seniority_multiplier = 0.06
    elif "junior" in seniority:
        seniority_multiplier = -0.08

    remote_policy = (job_extract.remote_policy or "").lower()
    remote_multiplier = 0.03 if "remote" in remote_policy else 0.0
    interview_multiplier = 0.02 if interview_steps >= 5 else 0.0

    additive_multiplier = (
        1.0
        + requirements_multiplier
        + seniority_multiplier
        + remote_multiplier
        + interview_multiplier
        + overrides.requirements_multiplier_delta
        + overrides.seniority_multiplier_delta
        + overrides.remote_multiplier_delta
        + overrides.interview_multiplier_delta
    )

    location_multiplier = (
        _location_salary_multiplier(job_extract.location_country or "")
        * overrides.location_multiplier_factor
    )
    title_multiplier = (
        _title_salary_multiplier(job_extract.job_title or "")
        * overrides.title_multiplier_factor
    )

    salary_multiplier = additive_multiplier * location_multiplier * title_multiplier

    forecast_central = max(35_000.0, base_salary * salary_multiplier)
    spread_factor = (
        0.08
        + min(0.14, max(0.0, (10 - min(answers_count, 10)) * 0.012))
        + overrides.spread_factor_delta
    )
    spread_factor = min(0.35, max(0.03, spread_factor))

    forecast_min = max(35_000.0, forecast_central * (1 - spread_factor))
    forecast_max = forecast_central * (1 + spread_factor)

    confidence_base = (
        35
        + min(45, answers_count * 4)
        + (12 if bool(job_extract.salary_range) else 0)
        + min(8, requirements_density)
        + min(8, responsibilities_count)
    )
    confidence = min(100, max(35, int(confidence_base + overrides.confidence_delta)))

    return SalaryForecastResult(
        forecast_min=round(forecast_min, 0),
        forecast_central=round(forecast_central, 0),
        forecast_max=round(forecast_max, 0),
        confidence=confidence,
        answers_count=answers_count,
        must_have_count=must_have_count,
        interview_steps=interview_steps,
        location=(job_extract.location_country or "Nicht angegeben"),
        seniority=(job_extract.seniority_level or "Nicht angegeben"),
        job_title=(job_extract.job_title or "Nicht angegeben"),
        currency=(
            job_extract.salary_range.currency if job_extract.salary_range else None
        )
        or "EUR",
        base_salary=round(base_salary, 0),
        salary_multiplier=salary_multiplier,
        spread_factor=spread_factor,
    )
