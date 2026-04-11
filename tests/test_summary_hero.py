from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace

from constants import SSKey
from schemas import JobAdExtract, VacancyBrief


SUMMARY_PATH = Path(__file__).resolve().parents[1] / "wizard_pages" / "08_summary.py"
SPEC = spec_from_file_location("wizard_pages.page_08_summary_hero", SUMMARY_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load summary page module")
SUMMARY_MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(SUMMARY_MODULE)  # type: ignore[attr-defined]


def _build_valid_brief_payload() -> dict[str, object]:
    return VacancyBrief(
        one_liner="Kurzpitch",
        hiring_context="Kontext",
        role_summary="Rollenbild",
        job_ad_draft="Draft",
    ).model_dump(mode="json")


def _build_job() -> JobAdExtract:
    return JobAdExtract(
        job_title="Senior Data Engineer",
        company_name="Cognitive Staffing GmbH",
        location_country="Deutschland",
    )


def test_summary_hero_status_complete_data(monkeypatch) -> None:
    fake_st = SimpleNamespace(
        session_state={
            SSKey.BRIEF.value: _build_valid_brief_payload(),
            SSKey.COMPANY_NACE_CODE.value: "62.01",
            SSKey.SUMMARY_DIRTY.value: False,
        }
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "get_esco_occupation_selected",
        lambda: {"title": "Data engineer"},
    )

    status = SUMMARY_MODULE._build_summary_status(job=_build_job(), answers={"a": "b"})

    assert status["brief_state"] == "ready"
    assert status["esco_ready"] is True
    assert status["nace_ready"] is True
    assert status["ready_for_follow_ups"] is True
    assert "Senior Data Engineer" in SUMMARY_MODULE._build_summary_headline(status)


def test_summary_hero_status_missing_esco_and_nace(monkeypatch) -> None:
    fake_st = SimpleNamespace(
        session_state={
            SSKey.BRIEF.value: _build_valid_brief_payload(),
            SSKey.COMPANY_NACE_CODE.value: "",
            SSKey.SUMMARY_DIRTY.value: False,
        }
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)
    monkeypatch.setattr(SUMMARY_MODULE, "get_esco_occupation_selected", lambda: None)

    status = SUMMARY_MODULE._build_summary_status(job=_build_job(), answers={})
    subheader = SUMMARY_MODULE._build_summary_subheader(status)

    assert status["esco_ready"] is False
    assert status["nace_ready"] is False
    assert "ESCO/NACE: Nicht gesetzt · Nicht gesetzt" in subheader


def test_summary_hero_status_missing_brief(monkeypatch) -> None:
    fake_st = SimpleNamespace(
        session_state={
            SSKey.COMPANY_NACE_CODE.value: "62.01",
            SSKey.SUMMARY_DIRTY.value: False,
        }
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "get_esco_occupation_selected",
        lambda: {"title": "Data engineer"},
    )

    status = SUMMARY_MODULE._build_summary_status(job=_build_job(), answers={})

    assert status["brief_state"] == "missing"
    assert status["next_step"] == "Recruiting Brief generieren"
    assert status["ready_for_follow_ups"] is False


def test_summary_hero_status_stale_brief_text_path(monkeypatch) -> None:
    fake_st = SimpleNamespace(
        session_state={
            SSKey.BRIEF.value: _build_valid_brief_payload(),
            SSKey.COMPANY_NACE_CODE.value: "62.01",
            SSKey.SUMMARY_DIRTY.value: True,
        }
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "get_esco_occupation_selected",
        lambda: {"title": "Data engineer"},
    )

    status = SUMMARY_MODULE._build_summary_status(job=_build_job(), answers={"x": "y"})
    subheader = SUMMARY_MODULE._build_summary_subheader(status)

    assert status["brief_state"] == "stale"
    assert status["next_step"] == "Recruiting Brief aktualisieren"
    assert "Brief: Recruiting Brief ist veraltet." in subheader
