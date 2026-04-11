from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from constants import SSKey
from schemas import VacancyBrief


SUMMARY_PATH = Path(__file__).resolve().parents[1] / "wizard_pages" / "08_summary.py"
SPEC = spec_from_file_location("wizard_pages.page_08_summary_consistency", SUMMARY_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load summary page module")
SUMMARY_MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(SUMMARY_MODULE)  # type: ignore[attr-defined]


def _valid_brief_payload() -> dict[str, Any]:
    return VacancyBrief(
        one_liner="Kurzpitch",
        hiring_context="Kontext",
        role_summary="Rollenbild",
        job_ad_draft="Draft",
    ).model_dump(mode="json")


def _meta() -> Any:
    return SUMMARY_MODULE.SummaryMeta(
        role_label="Engineer",
        company_label="ACME",
        country_label="DE",
        selected_occupation_title="Occupation",
        nace_code="6201",
        nace_mapped_esco_uri="esco:1",
        readiness_items=[],
    )


def test_stale_model_mismatch_is_consistent_across_summary_and_gating(
    monkeypatch,
) -> None:
    fake_st = SimpleNamespace(
        session_state={
            SSKey.BRIEF.value: _valid_brief_payload(),
            SSKey.SUMMARY_LAST_MODELS.value: {"draft_model": "gpt-4o-mini"},
            SSKey.JOB_EXTRACT.value: {"job_title": "Engineer"},
            SSKey.QUESTION_PLAN.value: {"steps": []},
        }
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)

    status = SUMMARY_MODULE._build_summary_status(
        answers={},
        meta=_meta(),
        resolved_brief_model="gpt-5-mini",
    )
    assert status.brief_state == "stale"
    assert status.ready_for_follow_ups is False

    requirement_ok, requirement_message = SUMMARY_MODULE._get_brief_requirement_status(
        "gpt-5-mini"
    )
    assert requirement_ok is False
    assert requirement_message == "Recruiting Brief ist veraltet."

    brief_state, _, cta_label = SUMMARY_MODULE._get_brief_status(
        primary_action={
            "id": "brief",
            "title": "Recruiting Brief",
            "benefit": "desc",
            "cta_label": "Generate",
            "blocked_cta_label": None,
            "requires": (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN),
            "requirement_text": "Jobspec vorhanden",
            "requirement_check_fn": None,
            "generator_fn": lambda: None,
            "result_key": SSKey.BRIEF,
            "input_hints": (),
            "input_renderer": None,
        },
        resolved_brief_model="gpt-5-mini",
    )
    assert brief_state == "stale"
    assert cta_label == "Recruiting Brief aktualisieren"


def test_stale_fingerprint_mismatch_is_consistent(monkeypatch) -> None:
    fake_st = SimpleNamespace(
        session_state={
            SSKey.BRIEF.value: _valid_brief_payload(),
            SSKey.SUMMARY_LAST_MODELS.value: {"draft_model": "gpt-5-mini"},
            SSKey.SUMMARY_INPUT_FINGERPRINT.value: "current",
            SSKey.SUMMARY_LAST_BRIEF_FINGERPRINT.value: "old",
            SSKey.JOB_EXTRACT.value: {"job_title": "Engineer"},
            SSKey.QUESTION_PLAN.value: {"steps": []},
        }
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)

    status = SUMMARY_MODULE._build_summary_status(
        answers={},
        meta=_meta(),
        resolved_brief_model="gpt-5-mini",
    )
    assert status.brief_state == "stale"

    requirement_ok, requirement_message = SUMMARY_MODULE._get_brief_requirement_status(
        "gpt-5-mini"
    )
    assert requirement_ok is False
    assert "passt nicht mehr" in requirement_message
