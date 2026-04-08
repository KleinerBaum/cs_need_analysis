from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from schemas import JobAdExtract, MoneyRange, RecruitmentStep


SUMMARY_PATH = Path(__file__).resolve().parents[1] / "wizard_pages" / "08_summary.py"
SPEC = spec_from_file_location("wizard_pages.page_08_summary", SUMMARY_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load summary page module")
SUMMARY_MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(SUMMARY_MODULE)  # type: ignore[attr-defined]


def test_estimate_salary_baseline_uses_range_average() -> None:
    job = JobAdExtract(
        job_title="Data Scientist",
        salary_range=MoneyRange(min=70000, max=90000, currency="EUR", period="yearly"),
    )

    assert SUMMARY_MODULE._estimate_salary_baseline(job) == 80000


def test_estimate_salary_baseline_uses_seniority_fallback() -> None:
    job = JobAdExtract(job_title="Engineer", seniority_level="Senior")

    assert SUMMARY_MODULE._estimate_salary_baseline(job) == 90000


def test_estimate_candidate_baseline_has_floor() -> None:
    job = JobAdExtract(
        must_have_skills=["Python", "SQL", "ML", "Spark", "Kubernetes", "Terraform"],
        certifications=["AWS", "GCP", "Azure"],
        languages=["Deutsch", "Englisch", "Französisch"],
    )

    baseline = SUMMARY_MODULE._estimate_candidate_baseline(job)

    assert baseline >= 8.0
    assert baseline == 55.0


def test_build_salary_forecast_snapshot_uses_job_inputs() -> None:
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
    answers = {"team_size": 8, "benefits": "Top", "work_mode": "hybrid"}

    snapshot = SUMMARY_MODULE._build_salary_forecast_snapshot(job=job, answers=answers)

    assert snapshot["forecast_min"] > 0
    assert snapshot["forecast_central"] >= snapshot["forecast_min"]
    assert snapshot["forecast_max"] >= snapshot["forecast_central"]
    assert snapshot["currency"] == "EUR"
    assert snapshot["location"] == "Deutschland"
    assert snapshot["must_have_count"] == 5
    assert snapshot["answers_count"] == 3
    assert 35 <= int(snapshot["confidence"]) <= 100
