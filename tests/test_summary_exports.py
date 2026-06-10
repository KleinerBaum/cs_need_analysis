from __future__ import annotations

from schemas import (
    BooleanSearchChannelQueries,
    BooleanSearchPack,
    JobAdExtract,
    VacancyBrief,
    VacancyStructuredData,
)
from summary_exports import (
    boolean_search_pack_to_markdown,
    brief_to_markdown,
    build_summary_input_fingerprint,
)


def _fingerprint(*, answers: dict[str, object]) -> str:
    return build_summary_input_fingerprint(
        job=JobAdExtract(
            job_title="Data Engineer",
            company_name="ACME GmbH",
            location_country="DE",
        ),
        answers=answers,
        selected_role_tasks=["Build data products"],
        selected_skills=["Python", "SQL"],
        selected_benefits=["Mentoring"],
        esco_occupation_selected={"uri": "uri:occ:1", "title": "Data Engineer"},
        esco_match_explainability={
            "reason": "Anker bestätigt",
            "confidence": "high",
            "provenance": ["exact label match"],
        },
        esco_selected_skills_must=[{"uri": "uri:skill:python", "title": "Python"}],
        esco_selected_skills_nice=[],
    )


def test_build_summary_input_fingerprint_is_stable_and_sensitive_to_inputs() -> None:
    baseline = _fingerprint(answers={"team_size": 5})

    assert baseline == _fingerprint(answers={"team_size": 5})
    assert baseline != _fingerprint(answers={"team_size": 10})
    assert len(baseline) == 64


def test_brief_to_markdown_exports_primary_sections() -> None:
    brief = VacancyBrief(
        one_liner="One line",
        hiring_context="Context",
        role_summary="Summary",
        top_responsibilities=["Build pipelines"],
        must_have=["Python"],
        nice_to_have=["SQL"],
        dealbreakers=["No cloud experience"],
        interview_plan=["HR screen"],
        evaluation_rubric=["Technical depth"],
        risks_open_questions=["Budget open"],
        job_ad_draft="Draft text",
        structured_data=VacancyStructuredData(
            job_extract={"job_title": "Data Engineer"},
            answers={},
        ),
    )

    markdown = brief_to_markdown(brief)

    assert markdown.startswith("# Recruiting Brief – Data Engineer")
    assert "## Top Responsibilities\n- Build pipelines" in markdown
    assert "## Job Ad Draft (DE)\nDraft text" in markdown


def test_boolean_search_pack_to_markdown_formats_channel_queries() -> None:
    channel = BooleanSearchChannelQueries(
        broad=["site:linkedin.com/in Python"],
        focused=[],
        fallback=["Data Engineer Berlin"],
    )
    pack = BooleanSearchPack(
        role_title="Data Engineer",
        target_locations=["Berlin"],
        seniority_terms=["Senior"],
        must_have_terms=["Python"],
        exclusion_terms=[],
        google=channel,
        linkedin=channel,
        xing=channel,
        channel_limitations=["LinkedIn search syntax varies"],
        usage_notes=["Start broad, then tighten"],
    )

    markdown = boolean_search_pack_to_markdown(pack)

    assert markdown.startswith("# Boolean Search Pack")
    assert "**Role Title:** Data Engineer" in markdown
    assert "- `site:linkedin.com/in Python`" in markdown
    assert "### Focused\n- —" in markdown
    assert "## Usage Notes\n- Start broad, then tighten" in markdown
