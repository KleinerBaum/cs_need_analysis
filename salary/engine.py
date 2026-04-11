"""Domain salary forecast engine without UI dependencies."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from schemas import JobAdExtract

from salary.benchmarks import (
    build_benchmark_index,
    load_benchmark_csv,
    lookup_benchmark,
    resolve_salary_benchmark_path,
)
from salary.features_esco import compute_esco_skill_coverage_signals
from salary.mapping import infer_occupation_id, infer_region_id
from salary.skill_premiums import compute_skill_premium_delta
from salary.types import (
    SalaryEscoContext,
    SalaryForecastBand,
    SalaryForecastDriver,
    SalaryForecastProvenance,
    SalaryForecastQuality,
    SalaryForecastResult,
    SalaryScenarioInputs,
    SalaryScenarioOverrides,
)


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


@lru_cache(maxsize=1)
def _load_benchmark_index_cached() -> Any:
    rows = load_benchmark_csv(resolve_salary_benchmark_path())
    return build_benchmark_index(rows)


def _radius_multiplier(search_radius_km: int) -> float:
    """Simple v1 search-radius heuristic.

    - <= 20km: tighter local market, slight uplift.
    - 21-50km: neutral baseline.
    - > 50km: broader candidate pool, small discount.
    """

    if search_radius_km <= 20:
        return 1.02
    if search_radius_km <= 50:
        return 1.0
    if search_radius_km <= 100:
        return 0.98
    return 0.96


def _driver_from_delta(
    *, key: str, label: str, eur_delta: float, category: str, detail: str
) -> SalaryForecastDriver:
    direction = "neutral"
    if eur_delta > 0:
        direction = "up"
    elif eur_delta < 0:
        direction = "down"
    return SalaryForecastDriver(
        key=key,
        label=label,
        direction=direction,
        impact=round(abs(eur_delta), 0),
        impact_eur=round(abs(eur_delta), 0),
        category=category,
        detail=detail,
    )


def compute_salary_forecast(
    job_extract: JobAdExtract,
    answers: dict,
    scenario_overrides: SalaryScenarioOverrides | None = None,
    *,
    esco_context: SalaryEscoContext | None = None,
    scenario_inputs: SalaryScenarioInputs | None = None,
) -> SalaryForecastResult:
    """Compute salary forecast from normalized job extract and wizard answers."""

    overrides = scenario_overrides or SalaryScenarioOverrides()
    must_have_count = len(job_extract.must_have_skills)
    interview_steps = len(job_extract.recruitment_steps)
    answers_count = _count_meaningful_answers(answers)
    responsibilities_count = len(job_extract.responsibilities)
    requirements_density = (
        must_have_count + len(job_extract.certifications) + len(job_extract.languages)
    )

    effective_location_country = (
        scenario_inputs.location_country_override
        if scenario_inputs and scenario_inputs.location_country_override
        else job_extract.location_country
    ) or ""
    location_city = (
        scenario_inputs.location_city_override
        if scenario_inputs and scenario_inputs.location_city_override
        else job_extract.location_city
    )
    region_id = infer_region_id(effective_location_country, location_city)
    occupation_id = infer_occupation_id(esco_context, job_extract.job_title)

    benchmark_index = _load_benchmark_index_cached()
    benchmark_row = lookup_benchmark(
        benchmark_index,
        occupation_id=occupation_id,
        region_id=region_id,
    )

    base_salary = estimate_salary_baseline(job_extract)
    answers_based_spread = 0.08 + min(
        0.14, max(0.0, (10 - min(answers_count, 10)) * 0.012)
    )
    spread_factor = min(
        0.35, max(0.03, answers_based_spread + overrides.spread_factor_delta)
    )

    if benchmark_row is not None:
        baseline_band = SalaryForecastBand(
            p10=round(benchmark_row.p10, 0),
            p50=round(benchmark_row.p50, 0),
            p90=round(benchmark_row.p90, 0),
        )
        fallback_path = "benchmark"
    else:
        baseline_band = SalaryForecastBand(
            p10=round(max(35_000.0, base_salary * (1 - spread_factor)), 0),
            p50=round(max(35_000.0, base_salary), 0),
            p90=round(base_salary * (1 + spread_factor), 0),
        )
        fallback_path = "heuristic_baseline_spread_v1"

    baseline_p50 = baseline_band.p50

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
    location_multiplier = _location_salary_multiplier(effective_location_country)
    title_multiplier = _title_salary_multiplier(job_extract.job_title or "")

    search_radius_km = scenario_inputs.search_radius_km if scenario_inputs else 50
    radius_multiplier = _radius_multiplier(search_radius_km)

    requirements_delta = baseline_p50 * (
        requirements_multiplier + overrides.requirements_multiplier_delta
    )
    seniority_delta = baseline_p50 * (
        seniority_multiplier + overrides.seniority_multiplier_delta
    )
    remote_delta = baseline_p50 * (
        remote_multiplier + overrides.remote_multiplier_delta
    )
    interview_delta = baseline_p50 * (
        interview_multiplier + overrides.interview_multiplier_delta
    )
    location_delta = baseline_p50 * (
        (location_multiplier * overrides.location_multiplier_factor) - 1.0
    )
    title_delta = baseline_p50 * (
        (title_multiplier * overrides.title_multiplier_factor) - 1.0
    )
    radius_delta = baseline_p50 * (radius_multiplier - 1.0)
    skill_premium_delta, top_premium_skills = compute_skill_premium_delta(
        esco_context,
        job_extract,
        baseline_p50=baseline_p50,
    )

    total_adjustment = (
        requirements_delta
        + seniority_delta
        + remote_delta
        + interview_delta
        + location_delta
        + title_delta
        + radius_delta
        + skill_premium_delta
    )

    forecast = SalaryForecastBand(
        p10=round(max(35_000.0, baseline_band.p10 + total_adjustment), 0),
        p50=round(max(35_000.0, baseline_band.p50 + total_adjustment), 0),
        p90=round(max(35_000.0, baseline_band.p90 + total_adjustment), 0),
    )

    confidence_base = (
        35
        + min(30, answers_count * 3)
        + (20 if benchmark_row is not None else 0)
        + min(8, requirements_density)
        + min(7, responsibilities_count)
        + (8 if esco_context and esco_context.occupation_uri else 0)
        + min(8, (len(esco_context.skill_uris_must) if esco_context else 0))
    )
    confidence = min(100, max(30, int(confidence_base + overrides.confidence_delta)))
    quality_value = round(confidence / 100.0, 2)

    location_parts = [
        part
        for part in (location_city, effective_location_country)
        if isinstance(part, str) and part
    ]
    location = ", ".join(location_parts) or "Nicht angegeben"
    seniority_label = job_extract.seniority_level or "Nicht angegeben"
    job_title = job_extract.job_title or "Nicht angegeben"
    salary_range_currency = (
        job_extract.salary_range.currency if job_extract.salary_range else None
    )
    salary_range_period = (
        job_extract.salary_range.period if job_extract.salary_range else None
    )
    currency = salary_range_currency or "EUR"
    period = salary_range_period or "yearly"
    if benchmark_row is not None:
        if not salary_range_currency:
            currency = benchmark_row.currency or currency
        if not salary_range_period:
            period = benchmark_row.period or period

    esco_signals = compute_esco_skill_coverage_signals(
        esco_context or SalaryEscoContext()
    )

    drivers: list[SalaryForecastDriver] = [
        _driver_from_delta(
            key="requirements_density",
            label="Anforderungsdichte",
            eur_delta=requirements_delta,
            category="requirements",
            detail=f"{requirements_density} Anforderungen/Zertifikate/Sprachen berücksichtigt.",
        ),
        _driver_from_delta(
            key="seniority",
            label="Seniorität",
            eur_delta=seniority_delta,
            category="role",
            detail=f"Ausprägung: {seniority_label}.",
        ),
        _driver_from_delta(
            key="remote_policy",
            label="Remote-Policy",
            eur_delta=remote_delta,
            category="market",
            detail=f"Remote-Regel erkannt: {bool('remote' in remote_policy)}.",
        ),
        _driver_from_delta(
            key="interview_process",
            label="Interviewprozess",
            eur_delta=interview_delta,
            category="process",
            detail=f"{interview_steps} Interview-Schritte berücksichtigt.",
        ),
        _driver_from_delta(
            key="search_radius",
            label="Suchradius",
            eur_delta=radius_delta,
            category="market",
            detail=f"Radius-Heuristik v1: {search_radius_km}km -> Faktor {radius_multiplier:.2f}.",
        ),
        _driver_from_delta(
            key="esco_skill_premiums",
            label="ESCO Skill-Premiums",
            eur_delta=skill_premium_delta,
            category="skills",
            detail=(
                "Top-Premium-Skills: " + ", ".join(top_premium_skills)
                if top_premium_skills
                else "Keine konfigurierten Skill-Premiums gematcht."
            ),
        ),
        _driver_from_delta(
            key="location",
            label="Standort",
            eur_delta=location_delta,
            category="market",
            detail=f"Standortfaktor für {location}: {(location_multiplier * overrides.location_multiplier_factor):.2f}.",
        ),
        _driver_from_delta(
            key="job_title",
            label="Jobtitel",
            eur_delta=title_delta,
            category="role",
            detail=f"Titelfaktor für {job_title}: {(title_multiplier * overrides.title_multiplier_factor):.2f}.",
        ),
    ]

    benchmark_version = "internal_heuristic_baseline_2026_01"
    benchmark_year = 2026
    benchmark_source_label = "internal_heuristic_baseline"
    if benchmark_row is not None:
        benchmark_version = benchmark_row.dataset_version
        benchmark_year = benchmark_row.year
        benchmark_source_label = benchmark_row.source_label

    return SalaryForecastResult(
        forecast=forecast,
        currency=currency,
        period=period,
        quality=SalaryForecastQuality(
            kind="data_quality_score",
            value=quality_value,
            signals=[
                f"benchmark_hit={str(benchmark_row is not None).lower()}",
                f"fallback_path={fallback_path}",
                f"occupation_id={occupation_id}",
                f"region_id={region_id}",
                f"answers_count={answers_count}",
                *esco_signals,
            ],
        ),
        drivers=drivers,
        provenance=SalaryForecastProvenance(
            engine="benchmark_salary_engine_v1",
            benchmark_version=benchmark_version,
            occupation_mapping="esco_uri_or_title_v1",
            region_mapping="country_city_region_v1_de_seed",
            benchmark_year=benchmark_year,
            benchmark_source_label=benchmark_source_label,
            occupation_id=occupation_id,
            region_id=region_id,
        ),
        answers_count=answers_count,
        must_have_count=must_have_count,
        interview_steps=interview_steps,
        location=location,
        seniority=seniority_label,
        job_title=job_title,
        base_salary=round(base_salary, 0),
        salary_multiplier=round((forecast.p50 / baseline_p50), 3)
        if baseline_p50
        else 1.0,
        spread_factor=spread_factor,
    )
