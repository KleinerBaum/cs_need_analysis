from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any, Literal

from constants import SSKey
from schemas import JobAdExtract, QuestionPlan


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


def test_render_entry_does_not_auto_generate_recruiting_brief(monkeypatch) -> None:
    """Expected vs Actual: Beim Entry ohne Brief kein Auto-Generate; stattdessen Hinweis + return."""
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
    monkeypatch.setattr(SUMMARY_MODULE, "load_openai_settings", lambda: object())
    monkeypatch.setattr(SUMMARY_MODULE, "get_model_override", lambda: None)
    monkeypatch.setattr(
        SUMMARY_MODULE, "resolve_model_for_task", lambda **_: "gpt-5-mini"
    )
    monkeypatch.setattr(SUMMARY_MODULE, "_render_summary_hero", lambda **_: None)
    monkeypatch.setattr(
        SUMMARY_MODULE, "_render_summary_facts_section", lambda *_: None
    )
    monkeypatch.setattr(
        SUMMARY_MODULE, "_render_summary_processing_hub", lambda **_: None
    )
    monkeypatch.setattr(SUMMARY_MODULE, "_build_action_registry", lambda **_: [])

    called_generate = {"count": 0}

    def _should_not_run(*_: Any, **__: Any) -> None:
        called_generate["count"] += 1

    monkeypatch.setattr(SUMMARY_MODULE, "generate_vacancy_brief", _should_not_run)

    SUMMARY_MODULE.render(fake_ctx)

    assert called_generate["count"] == 0, (
        "Expected no auto-generation at summary entry; actual generator call count > 0"
    )
    assert any(
        "Noch kein Recruiting Brief verfügbar" in msg for msg in fake_st.info_calls
    )
