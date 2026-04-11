from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace

from constants import SSKey


SUMMARY_PATH = Path(__file__).resolve().parents[1] / "wizard_pages" / "08_summary.py"
SPEC = spec_from_file_location(
    "wizard_pages.page_08_summary_requirements", SUMMARY_PATH
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load summary page module")
SUMMARY_MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(SUMMARY_MODULE)  # type: ignore[attr-defined]


def test_follow_up_requirement_blocks_without_current_brief(monkeypatch) -> None:
    """Expected vs Actual: Follow-up ohne aktuellen Brief wird blockiert und klar begründet."""
    fake_st = SimpleNamespace(session_state={})
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)

    ok, reason = SUMMARY_MODULE._get_brief_requirement_status("gpt-5-mini")

    assert ok is False, f"Expected blocked follow-up without brief; actual ok={ok}"
    assert reason == "Kein Recruiting Brief vorhanden."


def test_follow_up_requirement_blocks_stale_brief(monkeypatch) -> None:
    """Expected vs Actual: Follow-up mit veraltetem Brief wird blockiert, kein Auto-Refresh."""
    fake_st = SimpleNamespace(
        session_state={
            SSKey.BRIEF.value: {
                "one_liner": "x",
                "hiring_context": "ctx",
                "role_summary": "summary",
                "job_ad_draft": "draft",
            },
            SSKey.SUMMARY_LAST_MODELS.value: {"draft_model": "gpt-4o-mini"},
        }
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)

    ok, reason = SUMMARY_MODULE._get_brief_requirement_status("gpt-5-mini")

    assert ok is False, f"Expected stale brief to be blocked; actual ok={ok}"
    assert reason == "Recruiting Brief ist veraltet."
