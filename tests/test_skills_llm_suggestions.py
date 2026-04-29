from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace

SKILLS_PATH = Path(__file__).resolve().parents[1] / "wizard_pages" / "05_skills.py"
SPEC = spec_from_file_location("wizard_pages.page_05_skills", SKILLS_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load skills page module")
SKILLS_MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(SKILLS_MODULE)  # type: ignore[attr-defined]


def test_merge_llm_skill_suggestions_dedupes_against_existing_esco_titles() -> None:
    merged = SKILLS_MODULE._merge_llm_skill_suggestions(
        llm_skills=[
            {
                "label": "Python",
                "importance": "high",
                "rationale": "relevant",
                "evidence": "jobspec",
            },
            {
                "label": "Data Governance",
                "importance": "medium",
                "rationale": "relevant",
                "evidence": "answers",
            },
            {
                "label": "data governance",
                "importance": "low",
                "rationale": "duplicate",
                "evidence": "llm",
            },
        ],
        blocked_labels=["Python", "Stakeholder Management"],
    )

    assert merged == [
        {
            "label": "Data Governance",
            "uri": "",
            "source": "AI suggestion",
            "importance": "medium",
            "rationale": "relevant",
            "evidence": "answers",
        }
    ]


def test_save_selected_skill_suggestions_merges_without_duplicates() -> None:
    setattr(
        SKILLS_MODULE,
        "st",
        SimpleNamespace(session_state={"cs.skills.selected": ["Python"]}),
    )

    added = SKILLS_MODULE._save_selected_skill_suggestions(["python", "SQL"])

    assert added == 1
    assert SKILLS_MODULE.st.session_state["cs.skills.selected"] == ["Python", "SQL"]


def test_merge_llm_skill_suggestions_handles_empty_result() -> None:
    merged = SKILLS_MODULE._merge_llm_skill_suggestions(
        llm_skills=[],
        blocked_labels=["Python"],
    )

    assert merged == []


def test_merge_llm_skill_suggestions_dedupes_by_uri() -> None:
    merged = SKILLS_MODULE._merge_llm_skill_suggestions(
        llm_skills=[
            {"label": "Skill A", "uri": "uri:1", "source": "AI suggestion"},
            {"label": "Skill B", "uri": "uri:1", "source": "ESCO RAG"},
        ],
        blocked_labels=[],
    )
    assert len(merged) == 1
    assert merged[0]["label"] == "Skill A"
