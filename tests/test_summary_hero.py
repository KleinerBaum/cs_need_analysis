from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal

from constants import SSKey
from schemas import VacancyBrief


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


class _NoopContext:
    def __enter__(self) -> "_NoopContext":
        return self

    def __exit__(self, *_: object) -> Literal[False]:
        return False


class _MetricColumn:
    def __init__(self) -> None:
        self.metric_calls: list[tuple[str, str]] = []

    def metric(self, label: str, value: str) -> None:
        self.metric_calls.append((label, value))

    def __enter__(self) -> "_MetricColumn":
        return self

    def __exit__(self, *_: object) -> Literal[False]:
        return False


class _FakeStreamlit:
    def __init__(self, session_state: dict[str, Any]):
        self.session_state = session_state
        self.columns_calls: list[list[_MetricColumn]] = []

    def columns(self, count: int) -> list[_MetricColumn]:
        cols = [_MetricColumn() for _ in range(count)]
        self.columns_calls.append(cols)
        return cols

    def container(self, **_: Any) -> _NoopContext:
        return _NoopContext()


def test_summary_hero_status_complete_data(monkeypatch) -> None:
    fake_st = SimpleNamespace(session_state={SSKey.BRIEF.value: _build_valid_brief_payload()})
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)
    meta = SUMMARY_MODULE.SummaryMeta(
        role_label="Senior Data Engineer",
        company_label="Cognitive Staffing GmbH",
        country_label="Deutschland",
        selected_occupation_title="Data engineer",
        nace_code="62.01",
        nace_mapped_esco_uri="uri:occ:1",
        readiness_items=[],
    )
    status = SUMMARY_MODULE._build_summary_status(answers={"a": "b"}, meta=meta)

    assert status.brief_state == "ready"
    assert status.esco_ready is True
    assert status.nace_ready is True
    assert status.ready_for_follow_ups is True
    assert (
        SUMMARY_MODULE._build_summary_headline(meta)
        == "Senior Data Engineer bei Cognitive Staffing GmbH: Zusammenfassung"
    )


def test_summary_hero_status_missing_esco_and_nace(monkeypatch) -> None:
    fake_st = SimpleNamespace(session_state={SSKey.BRIEF.value: _build_valid_brief_payload()})
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)
    meta = SUMMARY_MODULE.SummaryMeta(
        role_label="Senior Data Engineer",
        company_label="Cognitive Staffing GmbH",
        country_label="Deutschland",
        selected_occupation_title="",
        nace_code="",
        nace_mapped_esco_uri="",
        readiness_items=[],
    )
    status = SUMMARY_MODULE._build_summary_status(answers={}, meta=meta)
    subheader = SUMMARY_MODULE._build_summary_subheader(meta, status)

    assert status.esco_ready is False
    assert status.nace_ready is False
    assert "ESCO/NACE: Nicht gesetzt · Nicht gesetzt" in subheader


def test_summary_hero_status_missing_brief(monkeypatch) -> None:
    fake_st = SimpleNamespace(session_state={})
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)
    meta = SUMMARY_MODULE.SummaryMeta(
        role_label="Senior Data Engineer",
        company_label="Cognitive Staffing GmbH",
        country_label="Deutschland",
        selected_occupation_title="Data engineer",
        nace_code="62.01",
        nace_mapped_esco_uri="uri:occ:1",
        readiness_items=[],
    )
    status = SUMMARY_MODULE._build_summary_status(answers={}, meta=meta)

    assert status.brief_state == "missing"
    assert status.next_step == "Recruiting Brief generieren"
    assert status.ready_for_follow_ups is False


def test_summary_hero_status_stale_brief_text_path(monkeypatch) -> None:
    fake_st = SimpleNamespace(
        session_state={
            SSKey.BRIEF.value: _build_valid_brief_payload(),
            SSKey.SUMMARY_DIRTY.value: True,
        }
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)
    meta = SUMMARY_MODULE.SummaryMeta(
        role_label="Senior Data Engineer",
        company_label="Cognitive Staffing GmbH",
        country_label="Deutschland",
        selected_occupation_title="Data engineer",
        nace_code="62.01",
        nace_mapped_esco_uri="uri:occ:1",
        readiness_items=[],
    )
    status = SUMMARY_MODULE._build_summary_status(answers={"x": "y"}, meta=meta)
    subheader = SUMMARY_MODULE._build_summary_subheader(meta, status)

    assert status.brief_state == "stale"
    assert status.next_step == "Recruiting Brief aktualisieren"
    assert "Brief: Recruiting Brief ist veraltet." in subheader


def test_summary_hero_meta_badges_show_dynamic_readiness(monkeypatch) -> None:
    fake_st = _FakeStreamlit(session_state={})
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)
    meta = SUMMARY_MODULE.SummaryMeta(
        role_label="Senior Data Engineer",
        company_label="Cognitive Staffing GmbH",
        country_label="Deutschland",
        selected_occupation_title="Data engineer",
        nace_code="62.01",
        nace_mapped_esco_uri="uri:occ:1",
        readiness_items=[],
    )
    status = SUMMARY_MODULE.SummaryStatus(
        completion_ratio=1.0,
        completion_text="10/10 beantwortet",
        brief_state="ready",
        brief_status_label="Aktueller Recruiting Brief vorhanden.",
        next_step="Gewünschtes Folge-Artefakt erzeugen",
        readiness_percent=100,
        ready_for_follow_ups=True,
        esco_ready=True,
        nace_ready=True,
    )
    SUMMARY_MODULE._render_summary_meta_badges(meta, status)
    metric_values = [value for col in fake_st.columns_calls[0] for _, value in col.metric_calls]
    assert "Senior Data Engineer" in metric_values
    assert "Cognitive Staffing GmbH" in metric_values
    assert "Bereit" in metric_values
