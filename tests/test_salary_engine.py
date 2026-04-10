from salary.engine import compute_salary_forecast, estimate_salary_baseline
from salary.types import SalaryScenarioOverrides
from schemas import JobAdExtract, MoneyRange, RecruitmentStep


def test_estimate_salary_baseline_uses_range_average() -> None:
    job = JobAdExtract(
        job_title="Data Scientist",
        salary_range=MoneyRange(min=70000, max=90000, currency="EUR", period="yearly"),
    )

    assert estimate_salary_baseline(job) == 80000


def test_compute_salary_forecast_returns_expected_shape() -> None:
    job = JobAdExtract(
        job_title="Principal Engineer",
        seniority_level="Principal",
        remote_policy="Remote-first",
        location_country="Deutschland",
        must_have_skills=["Python", "Go", "Kubernetes", "AWS", "Security"],
        recruitment_steps=[
            RecruitmentStep(name="Screen"),
            RecruitmentStep(name="Tech"),
            RecruitmentStep(name="Final"),
        ],
        salary_range=MoneyRange(min=95000, max=125000, currency="EUR", period="yearly"),
    )

    snapshot = compute_salary_forecast(job_extract=job, answers={"team_size": 8})

    assert snapshot.forecast.p10 > 0
    assert snapshot.forecast.p50 >= snapshot.forecast.p10
    assert snapshot.forecast.p90 >= snapshot.forecast.p50
    assert snapshot.currency == "EUR"
    assert snapshot.period == "yearly"
    assert snapshot.location == "Deutschland"
    assert snapshot.must_have_count == 5
    assert snapshot.answers_count == 1
    assert 0.35 <= snapshot.quality.value <= 1.0
    assert snapshot.quality.kind == "confidence_score"
    assert snapshot.drivers
    assert snapshot.provenance.engine


def test_compute_salary_forecast_applies_scenario_overrides() -> None:
    job = JobAdExtract(job_title="Engineer", location_country="Deutschland")

    baseline = compute_salary_forecast(job_extract=job, answers={})
    boosted = compute_salary_forecast(
        job_extract=job,
        answers={},
        scenario_overrides=SalaryScenarioOverrides(
            requirements_multiplier_delta=0.1,
            seniority_multiplier_delta=0.1,
            location_multiplier_factor=1.1,
            confidence_delta=10,
        ),
    )

    assert boosted.forecast.p50 > baseline.forecast.p50
    assert boosted.quality.value >= baseline.quality.value
