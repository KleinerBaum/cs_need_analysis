"""Pure helper builders for salary scenario-lab rows."""

from __future__ import annotations

from typing import Any, TypedDict

from salary.engine import compute_salary_forecast
from salary.types import (
    SalaryForecastResult,
    SalaryScenarioInputs,
    SalaryScenarioOverrides,
)
from schemas import JobAdExtract

LOCATION_COMPARE_CITIES: tuple[str, ...] = (
    "Berlin",
    "München",
    "Hamburg",
    "Köln",
    "Frankfurt",
)
RADIUS_SWEEP_VALUES: tuple[int, ...] = (0, 10, 25, 50, 100, 200, 300, 500)
REMOTE_SHARE_SWEEP_VALUES: tuple[int, ...] = (0, 25, 50, 75, 100)
SENIORITY_SWEEP_VALUES: tuple[str, ...] = ("junior", "mid", "senior", "lead")


class ScenarioLabRow(TypedDict):
    row_id: str
    group: str
    label: str
    p10: float
    p50: float
    p90: float
    delta_p50: float
    city: str
    country: str
    radius_km: int
    remote_share_percent: int
    seniority_override: str
    skills_add: list[str]


def unique_skills(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in values:
        normalized = str(item or "").strip()
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


def build_candidate_skill_pool(
    *, job: JobAdExtract, esco_skill_titles: list[str]
) -> list[str]:
    return unique_skills(
        [
            *job.must_have_skills,
            *job.nice_to_have_skills,
            *job.tech_stack,
            *esco_skill_titles,
        ]
    )


def apply_scenario_overrides_to_job(
    *,
    job: JobAdExtract,
    skills_add: list[str],
    skills_remove: list[str],
    location_city_override: str,
    location_country_override: str,
    remote_share_percent: int,
    seniority_override: str,
) -> JobAdExtract:
    add_list = unique_skills(skills_add)
    remove_set = {skill.casefold() for skill in unique_skills(skills_remove)}
    kept_skills = [
        skill
        for skill in unique_skills([*job.must_have_skills, *add_list])
        if skill.casefold() not in remove_set
    ]
    effective_remote_policy = "Onsite"
    if remote_share_percent >= 75:
        effective_remote_policy = "Remote"
    elif remote_share_percent >= 25:
        effective_remote_policy = "Hybrid"

    return job.model_copy(
        update={
            "must_have_skills": kept_skills,
            "location_city": location_city_override or job.location_city,
            "location_country": location_country_override or job.location_country,
            "remote_policy": effective_remote_policy,
            "seniority_level": seniority_override or job.seniority_level,
        }
    )


def _to_row(
    *,
    row_id: str,
    group: str,
    label: str,
    forecast: SalaryForecastResult,
    baseline_p50: float,
    city: str = "",
    country: str = "",
    radius_km: int = 50,
    remote_share_percent: int = 0,
    seniority_override: str = "",
    skills_add: list[str] | None = None,
) -> ScenarioLabRow:
    return {
        "row_id": row_id,
        "group": group,
        "label": label,
        "p10": float(forecast.forecast.p10),
        "p50": float(forecast.forecast.p50),
        "p90": float(forecast.forecast.p90),
        "delta_p50": float(forecast.forecast.p50 - baseline_p50),
        "city": city,
        "country": country,
        "radius_km": radius_km,
        "remote_share_percent": remote_share_percent,
        "seniority_override": seniority_override,
        "skills_add": skills_add or [],
    }


def build_salary_scenario_lab_rows(
    *,
    job: JobAdExtract,
    answers: dict[str, Any],
    scenario_overrides: SalaryScenarioOverrides,
    candidate_skills: list[str],
    location_country_override: str,
    radius_km: int,
    remote_share_percent: int,
    seniority_override: str,
    top_n_skills: int = 12,
) -> list[ScenarioLabRow]:
    baseline_forecast = compute_salary_forecast(
        job_extract=job,
        answers=answers,
        scenario_overrides=scenario_overrides,
        scenario_inputs=SalaryScenarioInputs(
            location_country_override=location_country_override or job.location_country,
            search_radius_km=radius_km,
            remote_share_percent=remote_share_percent,
        ),
    )
    baseline_p50 = float(baseline_forecast.forecast.p50)
    rows: list[ScenarioLabRow] = [
        _to_row(
            row_id="baseline",
            group="baseline",
            label="Baseline",
            forecast=baseline_forecast,
            baseline_p50=baseline_p50,
            radius_km=radius_km,
            remote_share_percent=remote_share_percent,
            seniority_override=seniority_override,
        )
    ]

    skill_rows: list[ScenarioLabRow] = []
    for skill in sorted(unique_skills(candidate_skills), key=str.casefold):
        scenario_job = job.model_copy(
            update={"must_have_skills": unique_skills([*job.must_have_skills, skill])}
        )
        forecast = compute_salary_forecast(
            job_extract=scenario_job,
            answers=answers,
            scenario_overrides=scenario_overrides,
            scenario_inputs=SalaryScenarioInputs(
                location_country_override=location_country_override
                or job.location_country,
                search_radius_km=radius_km,
                remote_share_percent=remote_share_percent,
            ),
        )
        skill_rows.append(
            _to_row(
                row_id=f"skill::{skill.casefold()}",
                group="skill_delta",
                label=skill,
                forecast=forecast,
                baseline_p50=baseline_p50,
                radius_km=radius_km,
                remote_share_percent=remote_share_percent,
                seniority_override=seniority_override,
                skills_add=[skill],
            )
        )
    rows.extend(
        sorted(
            skill_rows, key=lambda row: (-row["delta_p50"], row["label"].casefold())
        )[:top_n_skills]
    )

    for city in (job.location_city or "", *LOCATION_COMPARE_CITIES):
        row_id = f"location::{city.casefold() or 'current'}"
        forecast = compute_salary_forecast(
            job_extract=job,
            answers=answers,
            scenario_overrides=scenario_overrides,
            scenario_inputs=SalaryScenarioInputs(
                location_city_override=city or job.location_city,
                location_country_override=location_country_override
                or job.location_country,
                search_radius_km=radius_km,
                remote_share_percent=remote_share_percent,
            ),
        )
        rows.append(
            _to_row(
                row_id=row_id,
                group="location_compare",
                label=city or "Aktueller Standort",
                forecast=forecast,
                baseline_p50=baseline_p50,
                city=city,
                country=location_country_override or (job.location_country or ""),
                radius_km=radius_km,
                remote_share_percent=remote_share_percent,
                seniority_override=seniority_override,
            )
        )

    for radius in RADIUS_SWEEP_VALUES:
        forecast = compute_salary_forecast(
            job_extract=job,
            answers=answers,
            scenario_overrides=scenario_overrides,
            scenario_inputs=SalaryScenarioInputs(
                location_country_override=location_country_override
                or job.location_country,
                search_radius_km=radius,
                remote_share_percent=remote_share_percent,
            ),
        )
        rows.append(
            _to_row(
                row_id=f"radius::{radius}",
                group="radius_sweep",
                label=str(radius),
                forecast=forecast,
                baseline_p50=baseline_p50,
                radius_km=radius,
                remote_share_percent=remote_share_percent,
                seniority_override=seniority_override,
            )
        )

    for share in REMOTE_SHARE_SWEEP_VALUES:
        scenario_job = apply_scenario_overrides_to_job(
            job=job,
            skills_add=[],
            skills_remove=[],
            location_city_override="",
            location_country_override="",
            remote_share_percent=share,
            seniority_override=seniority_override,
        )
        forecast = compute_salary_forecast(
            job_extract=scenario_job,
            answers=answers,
            scenario_overrides=scenario_overrides,
            scenario_inputs=SalaryScenarioInputs(
                location_country_override=location_country_override
                or job.location_country,
                search_radius_km=radius_km,
                remote_share_percent=share,
            ),
        )
        rows.append(
            _to_row(
                row_id=f"remote::{share}",
                group="remote_share_sweep",
                label=str(share),
                forecast=forecast,
                baseline_p50=baseline_p50,
                radius_km=radius_km,
                remote_share_percent=share,
                seniority_override=seniority_override,
            )
        )

    for seniority in SENIORITY_SWEEP_VALUES:
        scenario_job = job.model_copy(update={"seniority_level": seniority})
        forecast = compute_salary_forecast(
            job_extract=scenario_job,
            answers=answers,
            scenario_overrides=scenario_overrides,
            scenario_inputs=SalaryScenarioInputs(
                location_country_override=location_country_override
                or job.location_country,
                search_radius_km=radius_km,
                remote_share_percent=remote_share_percent,
            ),
        )
        rows.append(
            _to_row(
                row_id=f"seniority::{seniority}",
                group="seniority_sweep",
                label=seniority,
                forecast=forecast,
                baseline_p50=baseline_p50,
                radius_km=radius_km,
                remote_share_percent=remote_share_percent,
                seniority_override=seniority,
            )
        )

    return rows
