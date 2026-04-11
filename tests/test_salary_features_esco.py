"""Tests for salary ESCO feature adapters."""

from salary.features_esco import (
    compute_esco_skill_coverage_signals,
    extract_esco_context,
    normalize_esco_uri,
)


def test_normalize_esco_uri_strips_query_fragment_and_trailing_slash() -> None:
    uri = " HTTPS://DATA.EUROPA.EU/esco/occupation/1234/?selectedVersion=v1.2.0#x "

    assert normalize_esco_uri(uri) == "https://data.europa.eu/esco/occupation/1234"


def test_extract_esco_context_maps_session_payloads_and_dedupes() -> None:
    context = extract_esco_context(
        occupation_selected={
            "uri": "https://data.europa.eu/esco/occupation/abc/?foo=1",
            "title": "Data Scientist",
            "type": "occupation",
        },
        skills_must=[
            {
                "uri": "https://data.europa.eu/esco/skill/1/",
                "title": "Python",
                "type": "skill",
            },
            {
                "uri": "https://data.europa.eu/esco/skill/1",
                "title": "Python",
                "type": "skill",
            },
            {"title": "missing-uri", "type": "skill"},
        ],
        skills_nice=[
            {
                "uri": "https://data.europa.eu/esco/skill/2?x=1",
                "title": "dbt",
                "type": "skill",
            }
        ],
        esco_config={"selected_version": "v1.2.0"},
    )

    assert context.occupation_uri == "https://data.europa.eu/esco/occupation/abc"
    assert context.skill_uris_must == ["https://data.europa.eu/esco/skill/1"]
    assert context.skill_uris_nice == ["https://data.europa.eu/esco/skill/2"]
    assert context.esco_version == "v1.2.0"


def test_compute_esco_skill_coverage_signals_returns_stable_feature_strings() -> None:
    context = extract_esco_context(
        occupation_selected=None,
        skills_must=[{"uri": "https://data.europa.eu/esco/skill/m1", "title": "A"}],
        skills_nice=[{"uri": "https://data.europa.eu/esco/skill/n1", "title": "B"}],
        esco_config=None,
    )

    assert compute_esco_skill_coverage_signals(context) == [
        "esco_occupation_present=false",
        "esco_skills_must_count=1",
        "esco_skills_nice_count=1",
        "esco_version=none",
    ]
