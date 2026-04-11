from salary.engine import compute_salary_forecast, estimate_salary_baseline
from salary.types import (
    SalaryEscoContext,
    SalaryScenarioInputs,
    SalaryScenarioOverrides,
)
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
    assert 0.3 <= snapshot.quality.value <= 1.0
    assert snapshot.quality.kind == "data_quality_score"
    assert snapshot.drivers
    assert snapshot.provenance.engine == "benchmark_salary_engine_v1"


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


def test_compute_salary_forecast_uses_benchmark_baseline_when_hit() -> None:
    job = JobAdExtract(
        job_title="Software Engineer",
        location_country="Deutschland",
    )

    snapshot = compute_salary_forecast(
        job_extract=job,
        answers={"team_size": 8, "budget_owner": True},
        scenario_inputs=SalaryScenarioInputs(location_city_override="Berlin"),
        esco_context=SalaryEscoContext(
            occupation_uri=(
                "http://data.europa.eu/esco/occupation/"
                "41b0f2f6-5122-4c00-a8fd-11be7b5af50c"
            )
        ),
    )

    assert snapshot.provenance.benchmark_version == "demo_v1"
    assert snapshot.provenance.benchmark_year == 2025
    assert snapshot.provenance.benchmark_source_label == "demo_synthetic_reference"
    assert any(signal == "benchmark_hit=true" for signal in snapshot.quality.signals)
    assert any(
        signal == "fallback_path=benchmark" for signal in snapshot.quality.signals
    )


def test_compute_salary_forecast_uses_heuristic_fallback_when_benchmark_misses(
    monkeypatch,
) -> None:
    job = JobAdExtract(
        job_title="Very Specific New Role",
        location_country="Schweiz",
        must_have_skills=["TensorRT", "Rust"],
    )

    monkeypatch.setattr("salary.engine._load_benchmark_index_cached", lambda: {})

    snapshot = compute_salary_forecast(
        job_extract=job,
        answers={},
        esco_context=SalaryEscoContext(
            occupation_uri="http://data.europa.eu/esco/occupation/non-existent"
        ),
    )

    assert (
        snapshot.provenance.benchmark_version == "internal_heuristic_baseline_2026_01"
    )
    assert snapshot.provenance.benchmark_source_label == "internal_heuristic_baseline"
    assert any(signal == "benchmark_hit=false" for signal in snapshot.quality.signals)
    assert any(
        signal == "fallback_path=heuristic_baseline_spread_v1"
        for signal in snapshot.quality.signals
    )
