from __future__ import annotations

from job_extract_evidence import format_field_evidence_snippet
from occupation_context import classify_occupation_context
from schemas import Contact, JobAdExtract, JobAdFieldEvidence, MoneyRange


def _ai_strategy_manager_extract() -> JobAdExtract:
    return JobAdExtract(
        job_title="AI Strategy / Analytics Manager (all genders)",
        remote_policy="Hybrid möglich; regelmäßige Projektpräsenz beim Kunden erforderlich.",
        travel_required="Projektmobilität innerhalb DACH erforderlich.",
        salary_range=MoneyRange(notes="Competitive package, abhängig von Erfahrung."),
        languages=["Deutsch C1", "Englisch B2"],
        responsibilities=[
            "AI-Strategien und Analytics-Roadmaps entwickeln",
            "Data-Governance-Zielbilder strukturieren",
            "Digitale Geschäftsmodelle und Operating Models bewerten",
            "Business Cases für Transformationsprogramme erstellen",
        ],
        must_have_skills=[
            "AI Strategy",
            "Analytics",
            "Data Governance",
            "Operating Model Design",
            "Digital Business Models",
            "Consulting",
            "Fachliche und disziplinarische Führung",
            "Business Case Development",
        ],
        benefits=["Weiterbildungsbudget", "Hybrid Work", "Corporate Benefits"],
        contacts=[
            Contact(
                name="Recruiting Team",
                role="Recruiting",
                email="recruiting@example.test",
            )
        ],
        field_evidence=[
            JobAdFieldEvidence(
                field_name="contacts",
                confidence=0.8,
                evidence_snippet="Kontakt: Recruiting Team, recruiting@example.test",
                needs_confirmation=True,
            )
        ],
    )


def test_ai_strategy_manager_regression_fixture_keeps_core_distinctions() -> None:
    job = _ai_strategy_manager_extract()

    assert job.job_title == "AI Strategy / Analytics Manager (all genders)"
    assert job.salary_range is not None
    assert job.salary_range.min is None
    assert job.salary_range.max is None
    assert "Competitive" in (job.salary_range.notes or "")
    assert "Projektmobilität" in (job.travel_required or "")
    assert len(job.languages) == 2
    assert job.languages == ["Deutsch C1", "Englisch B2"]
    assert "Fachliche und disziplinarische Führung" in job.must_have_skills
    assert "Hybrid Work" in job.benefits
    assert "Hybrid Work" not in job.must_have_skills
    for cluster in (
        "AI Strategy",
        "Analytics",
        "Data Governance",
        "Operating Model Design",
        "Digital Business Models",
        "Consulting",
        "Business Case Development",
    ):
        assert cluster in job.must_have_skills


def test_ai_strategy_manager_remote_plus_mobility_is_not_remote_only() -> None:
    job = _ai_strategy_manager_extract()

    profile = classify_occupation_context(job=job)

    assert profile.work_arrangement.value != "remote_global_possible"


def test_ai_strategy_manager_contact_evidence_is_redacted() -> None:
    job = _ai_strategy_manager_extract()

    snippet = format_field_evidence_snippet(
        job.field_evidence[0].model_dump(mode="json")
    )

    assert "recruiting@example.test" not in snippet
    assert "[REDACTED]" in snippet
