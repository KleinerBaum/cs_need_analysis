from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace

from constants import SSKey


SUMMARY_PATH = Path(__file__).resolve().parents[1] / "wizard_pages" / "08_summary.py"
SPEC = spec_from_file_location("wizard_pages.page_08_summary_readiness", SUMMARY_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load summary page module")
SUMMARY_MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(SUMMARY_MODULE)  # type: ignore[attr-defined]


def test_resolve_next_best_action_prefers_brief_when_not_ready(monkeypatch) -> None:
    monkeypatch.setattr(SUMMARY_MODULE, "st", SimpleNamespace(session_state={}))
    registry = [
        {
            "id": "brief",
            "title": "Brief",
            "benefit": "",
            "cta_label": "gen",
            "blocked_cta_label": None,
            "requires": (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN),
            "requirement_text": "",
            "requirement_check_fn": None,
            "generator_fn": lambda: None,
            "result_key": SSKey.BRIEF,
            "input_hints": (),
            "input_renderer": None,
        },
        {
            "id": "job_ad",
            "title": "Job ad",
            "benefit": "",
            "cta_label": "gen",
            "blocked_cta_label": None,
            "requires": (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN),
            "requirement_text": "",
            "requirement_check_fn": None,
            "generator_fn": lambda: None,
            "result_key": SSKey.JOB_AD_DRAFT_CUSTOM,
            "input_hints": (),
            "input_renderer": None,
        },
    ]
    action = SUMMARY_MODULE._resolve_next_best_action(
        registry, resolved_brief_model="gpt-5-mini"
    )
    assert action is not None
    assert action["id"] == "brief"


def test_build_artifact_status_rows_uses_requirement_checks(monkeypatch) -> None:
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "st",
        SimpleNamespace(session_state={SSKey.JOB_EXTRACT.value: {"job_title": "x"}}),
    )
    rows = SUMMARY_MODULE._build_artifact_status_rows(
        action_registry=[
            {
                "id": "job_ad",
                "title": "Job ad",
                "benefit": "",
                "cta_label": "gen",
                "blocked_cta_label": None,
                "requires": (SSKey.JOB_EXTRACT,),
                "requirement_text": "",
                "requirement_check_fn": lambda: (False, "blocked"),
                "generator_fn": lambda: None,
                "result_key": SSKey.JOB_AD_DRAFT_CUSTOM,
                "input_hints": (),
                "input_renderer": None,
            }
        ]
    )
    assert rows[0]["Voraussetzungen"] == "Offen"


def test_build_missing_critical_items_uses_fact_rows_status_order() -> None:
    vm = SimpleNamespace(
        fact_rows=[
            SUMMARY_MODULE.SummaryFactsRow("A", "f1", "—", "x", "Teilweise"),
            SUMMARY_MODULE.SummaryFactsRow("B", "f2", "—", "x", "Fehlend"),
        ]
    )
    items = SUMMARY_MODULE._build_missing_critical_items(vm)
    assert items[0].startswith("B · f2")
