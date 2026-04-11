from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace

from schemas import JobAdExtract

SKILLS_PATH = Path(__file__).resolve().parents[1] / "wizard_pages" / "05_skills.py"
SPEC = spec_from_file_location("wizard_pages.page_05_skills", SKILLS_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load skills page module")
SKILLS_MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(SKILLS_MODULE)  # type: ignore[attr-defined]


def test_extract_skill_candidates_filters_non_skill_entries() -> None:
    payload = {
        "uri": "http://data.europa.eu/esco/occupation/123",
        "type": "occupation",
        "title": "Data Engineer",
        "_embedded": {
            "hasEssentialSkill": [
                {
                    "uri": "http://data.europa.eu/esco/skill/a",
                    "preferredLabel": "Python",
                    "type": "skill",
                },
                {
                    "uri": "http://data.europa.eu/esco/skill/a",
                    "preferredLabel": "Python duplicate",
                    "type": "skill",
                },
            ]
        },
    }

    extracted = SKILLS_MODULE._extract_skill_candidates(payload)

    assert extracted == [
        {
            "uri": "http://data.europa.eu/esco/skill/a",
            "title": "Python",
            "type": "skill",
        }
    ]


def test_merge_suggested_skills_dedupes_against_existing_must_and_nice() -> None:
    merged, added_count = SKILLS_MODULE._merge_suggested_skills_by_uri(
        suggested_skills=[
            {"uri": "uri:skill:must", "title": "Existing Must", "type": "skill"},
            {"uri": "uri:skill:nice", "title": "Existing Nice", "type": "skill"},
            {"uri": "uri:skill:new", "title": "Brand New", "type": "skill"},
        ],
        must_selected=[
            {"uri": "uri:skill:must", "title": "Existing Must", "type": "skill"}
        ],
        nice_selected=[
            {"uri": "uri:skill:nice", "title": "Existing Nice", "type": "skill"}
        ],
    )

    assert added_count == 1
    assert merged == [
        {"uri": "uri:skill:must", "title": "Existing Must", "type": "skill"},
        {"uri": "uri:skill:new", "title": "Brand New", "type": "skill"},
    ]


def test_build_skill_suggestion_context_normalizes_jobspec_and_esco_titles() -> None:
    setattr(
        SKILLS_MODULE,
        "st",
        SimpleNamespace(session_state={"cs.skills.selected": ["Python"]}),
    )
    job = JobAdExtract(
        must_have_skills=[" Python ", "SQL"],
        nice_to_have_skills=["sql", "Kommunikation"],
        tech_stack=[" Airflow ", "python"],
    )

    context = SKILLS_MODULE._build_skill_suggestion_context(
        job=job,
        esco_must_selected=[{"title": "Data Modeling"}],
        esco_nice_selected=[{"title": "data modeling"}, {"title": "Stakeholder Mgmt"}],
    )

    assert context["jobspec_terms"] == ["Python", "SQL", "Kommunikation", "Airflow"]
    assert context["esco_titles"] == ["Data Modeling", "Stakeholder Mgmt"]
    assert context["selected_labels"] == ["Python"]
