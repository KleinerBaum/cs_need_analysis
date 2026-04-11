from salary.scenario_lab_builders import (
    LOCATION_COMPARE_CITIES,
    RADIUS_SWEEP_VALUES,
    REMOTE_SHARE_SWEEP_VALUES,
    SENIORITY_SWEEP_VALUES,
    apply_scenario_overrides_to_job,
    build_candidate_skill_pool,
    build_salary_scenario_lab_rows,
)
from salary.scenarios import SALARY_SCENARIO_BASE, map_salary_scenario_to_overrides
from schemas import JobAdExtract


def _sample_job() -> JobAdExtract:
    return JobAdExtract(
        job_title="Data Engineer",
        location_city="Berlin",
        location_country="Deutschland",
        seniority_level="mid",
        must_have_skills=["Python", "SQL"],
        nice_to_have_skills=["Airflow"],
        tech_stack=["dbt", "AWS"],
    )


def test_build_candidate_skill_pool_includes_job_and_esco_inputs() -> None:
    pool = build_candidate_skill_pool(
        job=_sample_job(),
        esco_skill_titles=["Cloud Computing", "Python"],
    )

    assert "Python" in pool
    assert "SQL" in pool
    assert "Airflow" in pool
    assert "dbt" in pool
    assert "AWS" in pool
    assert "Cloud Computing" in pool
    assert pool.count("Python") == 1


def test_apply_scenario_overrides_to_job_updates_skills_and_filters() -> None:
    updated = apply_scenario_overrides_to_job(
        job=_sample_job(),
        skills_add=["Kubernetes"],
        skills_remove=["SQL"],
        location_city_override="Hamburg",
        location_country_override="Deutschland",
        remote_share_percent=80,
        seniority_override="senior",
    )

    assert "Kubernetes" in updated.must_have_skills
    assert "SQL" not in updated.must_have_skills
    assert updated.location_city == "Hamburg"
    assert updated.remote_policy == "Remote"
    assert updated.seniority_level == "senior"


def test_build_salary_scenario_lab_rows_generates_deterministic_groups() -> None:
    rows = build_salary_scenario_lab_rows(
        job=_sample_job(),
        answers={"team_size": 5},
        scenario_overrides=map_salary_scenario_to_overrides(SALARY_SCENARIO_BASE),
        candidate_skills=["Kubernetes", "Spark", "Terraform", "Databricks"],
        location_country_override="Deutschland",
        radius_km=50,
        remote_share_percent=25,
        seniority_override="",
        top_n_skills=3,
    )

    assert rows[0]["group"] == "baseline"
    assert rows[0]["row_id"] == "baseline"

    skill_rows = [row for row in rows if row["group"] == "skill_delta"]
    location_rows = [row for row in rows if row["group"] == "location_compare"]
    radius_rows = [row for row in rows if row["group"] == "radius_sweep"]
    remote_rows = [row for row in rows if row["group"] == "remote_share_sweep"]
    seniority_rows = [row for row in rows if row["group"] == "seniority_sweep"]

    assert len(skill_rows) == 3
    assert len(location_rows) == len(LOCATION_COMPARE_CITIES) + 1
    assert [row["radius_km"] for row in radius_rows] == list(RADIUS_SWEEP_VALUES)
    assert [row["remote_share_percent"] for row in remote_rows] == list(
        REMOTE_SHARE_SWEEP_VALUES
    )
    assert [row["label"] for row in seniority_rows] == list(SENIORITY_SWEEP_VALUES)

    rows_second = build_salary_scenario_lab_rows(
        job=_sample_job(),
        answers={"team_size": 5},
        scenario_overrides=map_salary_scenario_to_overrides(SALARY_SCENARIO_BASE),
        candidate_skills=["Kubernetes", "Spark", "Terraform", "Databricks"],
        location_country_override="Deutschland",
        radius_km=50,
        remote_share_percent=25,
        seniority_override="",
        top_n_skills=3,
    )

    assert rows == rows_second
