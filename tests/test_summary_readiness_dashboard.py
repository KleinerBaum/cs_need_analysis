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
    vm = SimpleNamespace(fact_rows=[])
    action = SUMMARY_MODULE._resolve_next_best_action(
        registry, resolved_brief_model="gpt-5-mini", vm=vm
    )
    assert action is not None
    assert action["id"] == "brief"


def test_resolve_next_best_action_keeps_brief_for_missing_core_context(monkeypatch) -> None:
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "st",
        SimpleNamespace(
            session_state={
                SSKey.JOB_EXTRACT.value: {"job_title": "Engineer"},
                SSKey.QUESTION_PLAN.value: {"steps": []},
            }
        ),
    )
    registry = [
        {
            "id": "brief",
            "title": "Recruiting Brief erstellen",
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
            "id": "employment_contract",
            "title": "Arbeitsvertrag erstellen",
            "benefit": "",
            "cta_label": "gen",
            "blocked_cta_label": None,
            "requires": (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN),
            "requirement_text": "",
            "requirement_check_fn": lambda: (True, ""),
            "generator_fn": lambda: None,
            "result_key": SSKey.EMPLOYMENT_CONTRACT_DRAFT,
            "input_hints": (),
            "input_renderer": None,
        },
    ]
    vm = SimpleNamespace(
        fact_rows=[
            SUMMARY_MODULE.SummaryFactsRow("Kernprofil", "Land", "Nicht angegeben", "Jobspec", "Fehlend"),
            SUMMARY_MODULE.SummaryFactsRow("Kernprofil", "Stadt", "Nicht angegeben", "Jobspec", "Fehlend"),
            SUMMARY_MODULE.SummaryFactsRow("Kernprofil", "Unternehmen", "Nicht angegeben", "Jobspec", "Fehlend"),
        ]
    )
    action = SUMMARY_MODULE._resolve_next_best_action(
        registry, resolved_brief_model="gpt-5-mini", vm=vm
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


def test_resolve_next_best_action_recommendation_priority_order(monkeypatch) -> None:
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "st",
        SimpleNamespace(
            session_state={
                SSKey.JOB_EXTRACT.value: {"job_title": "Engineer", "company_name": "Acme"},
                SSKey.QUESTION_PLAN.value: {"steps": []},
                SSKey.BRIEF.value: {"role": "Engineer"},
            }
        ),
    )
    registry = [
        {
            "id": "brief",
            "title": "Recruiting Brief erstellen",
            "benefit": "",
            "cta_label": "Brief erstellen",
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
            "title": "Stellenanzeige erstellen",
            "benefit": "",
            "cta_label": "Stellenanzeige erstellen",
            "blocked_cta_label": None,
            "requires": (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN),
            "requirement_text": "",
            "requirement_check_fn": None,
            "generator_fn": lambda: None,
            "result_key": SSKey.JOB_AD_DRAFT_CUSTOM,
            "input_hints": (),
            "input_renderer": None,
        },
        {
            "id": "employment_contract",
            "title": "Arbeitsvertrag erstellen",
            "benefit": "",
            "cta_label": "Arbeitsvertrag erstellen",
            "blocked_cta_label": None,
            "requires": (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN),
            "requirement_text": "",
            "requirement_check_fn": lambda: (True, ""),
            "generator_fn": lambda: None,
            "result_key": SSKey.EMPLOYMENT_CONTRACT_DRAFT,
            "input_hints": (),
            "input_renderer": None,
        },
    ]

    vm_missing_core = SimpleNamespace(
        fact_rows=[SUMMARY_MODULE.SummaryFactsRow("Kernprofil", "Land", "Nicht angegeben", "Jobspec", "Fehlend")]
    )
    recommendation = SUMMARY_MODULE._resolve_next_best_action_recommendation(
        registry, resolved_brief_model="gpt-5-mini", vm=vm_missing_core
    )
    assert recommendation is not None
    assert recommendation.action["id"] == "brief"
    assert recommendation.cta_label == "Unternehmenskontext vervollständigen"

    monkeypatch.setattr(
        SUMMARY_MODULE,
        "_resolve_canonical_brief_status",
        lambda resolved_brief_model: SimpleNamespace(ready_for_follow_ups=True),
    )
    vm_ready = SimpleNamespace(fact_rows=[])
    recommendation_ready = SUMMARY_MODULE._resolve_next_best_action_recommendation(
        registry, resolved_brief_model="gpt-5-mini", vm=vm_ready
    )
    assert recommendation_ready is not None
    assert recommendation_ready.action["id"] == "job_ad"
