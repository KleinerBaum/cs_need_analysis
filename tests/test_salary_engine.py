from constants import SSKey
from salary.context_defaults import sync_salary_scenario_context_defaults
from salary.engine import (
    compute_salary_forecast,
    estimate_salary_baseline,
    infer_remote_share_percent,
    normalize_seniority_level,
)
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
    assert snapshot.provenance.benchmark_sample_size == 51
    assert snapshot.provenance.occupation_id == (
        "esco::http://data.europa.eu/esco/occupation/"
        "41b0f2f6-5122-4c00-a8fd-11be7b5af50c"
    )
    assert snapshot.provenance.region_id == "DE-BE"
    assert any(signal == "benchmark_hit=true" for signal in snapshot.quality.signals)
    assert any(
        signal == "fallback_path=benchmark" for signal in snapshot.quality.signals
    )
    assert snapshot.quality.benchmark_confidence == 0.75


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


def test_benchmark_hit_has_higher_quality_than_heuristic_fallback(monkeypatch) -> None:
    benchmark_job = JobAdExtract(
        job_title="Software Engineer",
        location_country="Deutschland",
        location_city="Berlin",
    )
    benchmark = compute_salary_forecast(
        job_extract=benchmark_job,
        answers={"team_size": 8, "budget_owner": True},
    )

    monkeypatch.setattr("salary.engine._load_benchmark_index_cached", lambda: {})
    fallback = compute_salary_forecast(
        job_extract=benchmark_job,
        answers={"team_size": 8, "budget_owner": True},
    )

    assert benchmark.quality.value > fallback.quality.value
    assert benchmark.quality.benchmark_confidence is not None
    assert fallback.quality.benchmark_confidence == 0.0
    assert (
        benchmark.quality.benchmark_confidence > fallback.quality.benchmark_confidence
    )


def test_esco_skill_premium_match_increases_p50() -> None:
    job = JobAdExtract(job_title="Engineer", location_country="Deutschland")

    without_esco = compute_salary_forecast(job_extract=job, answers={})
    with_esco = compute_salary_forecast(
        job_extract=job,
        answers={},
        esco_context=SalaryEscoContext(
            skill_uris_must=[
                "http://data.europa.eu/esco/skill/e8cbf45f-5303-40a1-b1d5-fac14532395a"
            ]
        ),
    )

    assert with_esco.forecast.p50 > without_esco.forecast.p50


def test_remote_share_has_graduated_direct_effect() -> None:
    job = JobAdExtract(
        job_title="Engineer",
        location_country="Deutschland",
        remote_policy="Onsite",
    )

    low_remote = compute_salary_forecast(
        job_extract=job,
        answers={},
        scenario_inputs=SalaryScenarioInputs(remote_share_percent=0),
    )
    high_remote = compute_salary_forecast(
        job_extract=job,
        answers={},
        scenario_inputs=SalaryScenarioInputs(remote_share_percent=100),
    )

    assert high_remote.forecast.p50 > low_remote.forecast.p50


def test_remote_share_is_inferred_from_jobspec_policy_when_scenario_is_missing() -> (
    None
):
    job = JobAdExtract(
        job_title="HR Business Partner",
        location_country="United Kingdom",
        remote_policy="Primarily on-site; one remote administration day per week may be possible.",
    )

    inferred = compute_salary_forecast(job_extract=job, answers={})
    explicit = compute_salary_forecast(
        job_extract=job,
        answers={},
        scenario_inputs=SalaryScenarioInputs(remote_share_percent=20),
    )

    assert infer_remote_share_percent(job.remote_policy) == 20
    assert inferred.forecast.p50 == explicit.forecast.p50
    assert "remote_share_percent=20" in inferred.quality.signals


def test_seniority_free_text_is_normalized_for_calibration() -> None:
    assert (
        normalize_seniority_level("Experienced Professional / HR Business Partner")
        == "mid"
    )
    assert normalize_seniority_level("Principal Consultant") == "lead"
    assert normalize_seniority_level("Senior Engineer") == "senior"


def test_tasks_and_benefits_influence_forecast_drivers() -> None:
    base_job = JobAdExtract(
        job_title="HR Business Partner",
        salary_range=MoneyRange(min=70000, max=90000, currency="EUR", period="yearly"),
    )
    enriched_job = base_job.model_copy(
        update={
            "responsibilities": [
                "Advise managers",
                "Support workforce planning",
                "Coach people leaders",
            ],
            "benefits": ["Pension contribution", "Learning budget", "Health support"],
        }
    )

    base = compute_salary_forecast(job_extract=base_job, answers={})
    enriched = compute_salary_forecast(job_extract=enriched_job, answers={})
    drivers = {driver.key: driver for driver in enriched.drivers}

    assert enriched.forecast.p50 > base.forecast.p50
    assert drivers["responsibilities"].impact_eur > 0
    assert drivers["benefits"].impact_eur > 0


def test_context_defaults_seed_salary_scenario_without_overwriting_manual_edits() -> (
    None
):
    session_state = {
        SSKey.SALARY_SCENARIO_REMOTE_SHARE_PERCENT.value: 0,
        SSKey.SALARY_SCENARIO_SENIORITY_OVERRIDE.value: "",
        SSKey.SALARY_SCENARIO_CONTEXT_DEFAULTS.value: {},
    }
    job = JobAdExtract(
        remote_policy="Primarily on-site; one remote administration day per week.",
        seniority_level="Experienced Professional",
    )

    sync_salary_scenario_context_defaults(session_state, job=job)

    assert session_state[SSKey.SALARY_SCENARIO_REMOTE_SHARE_PERCENT.value] == 20
    assert session_state[SSKey.SALARY_SCENARIO_SENIORITY_OVERRIDE.value] == "mid"

    session_state[SSKey.SALARY_SCENARIO_REMOTE_SHARE_PERCENT.value] = 0
    sync_salary_scenario_context_defaults(session_state, job=job)

    assert session_state[SSKey.SALARY_SCENARIO_REMOTE_SHARE_PERCENT.value] == 0


def test_seniority_calibration_is_monotonic() -> None:
    junior = compute_salary_forecast(
        job_extract=JobAdExtract(job_title="Engineer", seniority_level="junior"),
        answers={},
    )
    mid = compute_salary_forecast(
        job_extract=JobAdExtract(job_title="Engineer", seniority_level="mid"),
        answers={},
    )
    senior = compute_salary_forecast(
        job_extract=JobAdExtract(job_title="Engineer", seniority_level="senior"),
        answers={},
    )
    lead = compute_salary_forecast(
        job_extract=JobAdExtract(job_title="Engineer", seniority_level="lead"),
        answers={},
    )

    assert (
        junior.forecast.p50 < mid.forecast.p50 < senior.forecast.p50 < lead.forecast.p50
    )


def test_high_market_location_does_not_decrease_p50() -> None:
    neutral = compute_salary_forecast(
        job_extract=JobAdExtract(job_title="Engineer", location_country="Atlantis"),
        answers={},
    )
    high_market = compute_salary_forecast(
        job_extract=JobAdExtract(job_title="Engineer", location_country="Schweiz"),
        answers={},
    )

    assert high_market.forecast.p50 >= neutral.forecast.p50
