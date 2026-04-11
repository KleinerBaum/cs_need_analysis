from pathlib import Path

from salary.skill_premiums import compute_skill_premium_delta, load_skill_premiums
from salary.types import SalaryEscoContext
from schemas import JobAdExtract


def test_load_skill_premiums_demo_file() -> None:
    payload = load_skill_premiums(
        Path("data/salary_skill_premiums/demo_skill_premiums.json")
    )

    assert "skills" in payload
    assert len(payload["skills"]) >= 10


def test_compute_skill_premium_delta_supports_uri_and_label_matches() -> None:
    payload = load_skill_premiums(
        Path("data/salary_skill_premiums/demo_skill_premiums.json")
    )
    esco_context = SalaryEscoContext(
        skill_uris_must=[
            "http://data.europa.eu/esco/skill/e8cbf45f-5303-40a1-b1d5-fac14532395a"
        ]
    )
    job = JobAdExtract(job_title="Engineer", must_have_skills=["Python", "SQL"])

    delta, top_skills = compute_skill_premium_delta(
        esco_context,
        job,
        premium_config=payload,
        baseline_p50=70000,
    )

    assert delta > 0
    assert top_skills
