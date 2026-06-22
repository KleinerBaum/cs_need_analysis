from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal

from constants import SSKey
from schemas import CompanyWebsiteResearch, JobAdExtract, QuestionPlan


SUMMARY_PATH = Path(__file__).resolve().parents[1] / "wizard_pages" / "08_summary.py"
SPEC = spec_from_file_location("wizard_pages.page_08_summary_entry", SUMMARY_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load summary page module")
SUMMARY_MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(SUMMARY_MODULE)  # type: ignore[attr-defined]


class _NoopContext:
    def __enter__(self) -> "_NoopContext":
        return self

    def __exit__(self, *_: object) -> Literal[False]:
        return False


class _FakeStreamlit:
    def __init__(self, session_state: dict[str, Any]):
        self.session_state = session_state
        self.warning_calls: list[str] = []
        self.info_calls: list[str] = []

    def warning(self, text: str, **_: Any) -> None:
        self.warning_calls.append(text)

    def info(self, text: str, **_: Any) -> None:
        self.info_calls.append(text)

    def button(self, *_: Any, **__: Any) -> bool:
        return False


class _FakeCtx:
    def __init__(self) -> None:
        self.goto_calls: list[str] = []

    def goto(self, step: str) -> None:
        self.goto_calls.append(step)


class _GapActionFakeStreamlit:
    def __init__(self) -> None:
        self.session_state: dict[str, Any] = {}
        self.rerun_called = False

    def markdown(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def caption(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def container(self, **_kwargs: Any) -> _NoopContext:
        return _NoopContext()

    def button(self, *_args: Any, **_kwargs: Any) -> bool:
        return True

    def success(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def rerun(self) -> None:
        self.rerun_called = True


def test_render_entry_without_brief_still_renders_summary(monkeypatch) -> None:
    session_state = {
        SSKey.JOB_EXTRACT.value: JobAdExtract(job_title="Engineer").model_dump(
            mode="json"
        ),
        SSKey.QUESTION_PLAN.value: QuestionPlan.model_validate(
            {"steps": []}
        ).model_dump(mode="json"),
    }
    fake_st = _FakeStreamlit(session_state)
    fake_ctx = _FakeCtx()

    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)
    monkeypatch.setattr(SUMMARY_MODULE, "render_error_banner", lambda: None)
    monkeypatch.setattr(SUMMARY_MODULE, "nav_buttons", lambda *_, **__: None)
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "load_openai_settings",
        lambda: SimpleNamespace(default_model="gpt-5-mini"),
    )
    monkeypatch.setattr(SUMMARY_MODULE, "get_model_override", lambda: None)
    monkeypatch.setattr(
        SUMMARY_MODULE, "resolve_model_for_task", lambda *_, **__: "gpt-5-mini"
    )
    monkeypatch.setattr(SUMMARY_MODULE, "_build_action_registry", lambda **_: [])
    render_events: list[str] = []
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "render_output_header",
        lambda title, *_args, **_kwargs: render_events.append(str(title)),
    )
    monkeypatch.setattr(SUMMARY_MODULE, "_render_esco_coverage_kpis", lambda: None)
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "_render_summary_facts_matrix",
        lambda _vm: render_events.append("facts"),
    )
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "_render_summary_critical_gaps_table",
        lambda _vm, **_kwargs: render_events.append("gaps"),
    )
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "_render_summary_artifact_grid",
        lambda **_kwargs: render_events.append("grid"),
    )
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "_render_summary_output_workspace",
        lambda **_kwargs: render_events.append("output"),
    )

    called_generate = {"count": 0}

    def _should_not_run(*_: Any, **__: Any) -> None:
        called_generate["count"] += 1

    monkeypatch.setattr(SUMMARY_MODULE, "generate_vacancy_brief", _should_not_run)

    SUMMARY_MODULE.render(fake_ctx)

    assert called_generate["count"] == 0, (
        "Expected no auto-generation at summary entry; actual generator call count > 0"
    )
    assert render_events == [
        "Alles bereit für Recruiting und Hiring-Team",
        "gaps",
        "grid",
        "facts",
        "output",
    ]
    assert fake_st.info_calls == []


def test_summary_critical_gap_action_sets_deep_link_target(monkeypatch) -> None:
    fake_st = _GapActionFakeStreamlit()
    fake_ctx = _FakeCtx()
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "_build_summary_critical_gap_rows",
        lambda _vm: [
            {
                "_id": "gap1",
                "Schritt": "Skills & Anforderungen",
                "Feld": "Must-have Skills",
                "Status": "Fehlend",
                "Pflichtigkeit": "Pflicht vor Summary",
                "Aktion": "Noch offen.",
                "target_step": "skills",
                "target_section": "source_comparison",
                "target_fact_key": "skills.must_have_skills",
                "target_question_id": "",
            }
        ],
    )

    SUMMARY_MODULE._render_summary_critical_gaps_table(
        SimpleNamespace(fact_rows=[]),
        ctx=fake_ctx,
    )

    assert fake_ctx.goto_calls == ["skills"]
    assert fake_st.session_state[SSKey.NAV_DEEP_LINK_TARGET.value] == {
        "target_step": "skills",
        "target_section": "source_comparison",
        "target_fact_key": "skills.must_have_skills",
        "target_question_id": "",
        "label": "Must-have Skills",
        "source": "summary_critical_gap",
    }
    assert fake_st.rerun_called is True


def test_summary_entry_dirty_state_reports_stale_brief_message(monkeypatch) -> None:
    session_state = {
        SSKey.BRIEF.value: {
            "one_liner": "Kurzpitch",
            "hiring_context": "Kontext",
            "role_summary": "Rollenbild",
            "job_ad_draft": "Draft",
        },
        SSKey.SUMMARY_INPUT_FINGERPRINT.value: "new",
        SSKey.SUMMARY_LAST_BRIEF_FINGERPRINT.value: "old",
    }
    monkeypatch.setattr(SUMMARY_MODULE, "st", _FakeStreamlit(session_state))

    ok, reason = SUMMARY_MODULE._get_brief_requirement_status("gpt-5-mini")

    assert ok is False
    assert reason == "Recruiting Brief ist veraltet."


def test_summary_normalizes_legacy_website_research_before_validation() -> None:
    payload = {
        "homepage_url": "https://example.com",
        "sections": {
            "about": {
                "source_url": "https://example.com/about",
                "summary": ["Example summary"],
                "facts": ["Gegründet: 2001"],
                "fetched_at": "2026-06-10T00:00:00+00:00",
            }
        },
        "open_question_matches": [],
    }

    normalized = SUMMARY_MODULE._normalize_company_website_research_payload(payload)
    research = CompanyWebsiteResearch.model_validate(normalized)

    assert research.sections["about"].facts == {"Gegründet": "2001"}


def test_build_summary_view_model_tolerates_legacy_invalid_job_extract(
    monkeypatch,
) -> None:
    fake_st = _FakeStreamlit(
        {
            SSKey.JOB_EXTRACT.value: {"legacy_payload": True},
            SSKey.QUESTION_PLAN.value: {"steps": []},
        }
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)

    vm = SUMMARY_MODULE._build_summary_view_model()

    assert vm is None
