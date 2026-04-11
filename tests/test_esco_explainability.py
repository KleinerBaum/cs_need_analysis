from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import ui_components

JOBSPEC_PATH = (
    Path(__file__).resolve().parents[1] / "wizard_pages" / "01a_jobspec_review.py"
)
SPEC = spec_from_file_location("wizard_pages.page_01a_jobspec_review", JOBSPEC_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load jobspec review module")
JOBSPEC_MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(JOBSPEC_MODULE)  # type: ignore[attr-defined]


def test_infer_applied_provenance_categories_marks_manual_override_and_synonyms() -> (
    None
):
    categories = ui_components._infer_applied_provenance_categories(
        query_text="Data Engineer",
        selected_payload=[
            {
                "uri": "uri:2",
                "title": "Dateningenieur",
                "type": "occupation",
                "source": "manual",
            }
        ],
        selected_index=2,
        allow_multi=False,
    )

    assert "manually selected by user" in categories
    assert "synonym/hidden-term match" in categories


def test_infer_esco_match_explainability_detects_manual_override() -> None:
    explainability = JOBSPEC_MODULE._infer_esco_match_explainability(
        query_text="Data Engineer (Analytics)",
        selected={"uri": "uri:selected", "title": "Machine Learning Engineer"},
        options=[
            {"uri": "uri:top", "title": "Data Engineer"},
            {"uri": "uri:selected", "title": "Machine Learning Engineer"},
        ],
        applied_meta={"source": "auto"},
    )

    assert explainability["badge_label"] == "Manually Selected by User"
    assert explainability["confidence"] == "high"
    assert "manually selected by user" in explainability["provenance_categories"]


def test_infer_esco_match_explainability_prefers_jobspec_title_match() -> None:
    explainability = JOBSPEC_MODULE._infer_esco_match_explainability(
        query_text="Data Engineer (Berlin)",
        selected={"uri": "uri:selected", "title": "Senior Data Engineer"},
        options=[{"uri": "uri:selected", "title": "Senior Data Engineer"}],
        applied_meta={"source": "auto", "provenance_categories": []},
    )

    assert explainability["badge_label"] == "Exact Label Match"
    assert explainability["confidence"] == "high"
    assert "exact label match" in explainability["provenance_categories"]
