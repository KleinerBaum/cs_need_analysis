from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace

from constants import SSKey


SUMMARY_PATH = Path(__file__).resolve().parents[1] / "wizard_pages" / "08_summary.py"
SPEC = spec_from_file_location("wizard_pages.page_08_summary_invalid", SUMMARY_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load summary page module")
SUMMARY_MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(SUMMARY_MODULE)  # type: ignore[attr-defined]


def test_build_summary_artifact_state_handles_invalid_brief_payload(
    monkeypatch,
) -> None:
    fake_st = SimpleNamespace(
        session_state={
            SSKey.BRIEF.value: {"one_liner": 123},
            SSKey.SUMMARY_LAST_BRIEF_FINGERPRINT.value: "fp-old",
        }
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)

    artifacts = SUMMARY_MODULE._build_summary_artifact_state(
        selected_role_tasks=["Task"],
        selected_skills=["Skill"],
        input_fingerprint="fp-new",
    )

    assert artifacts.brief is None
    assert artifacts.is_dirty is True


def test_canonical_brief_status_reports_invalid_before_stale(monkeypatch) -> None:
    fake_st = SimpleNamespace(
        session_state={
            SSKey.BRIEF.value: {"one_liner": 123},
            SSKey.SUMMARY_DIRTY.value: True,
            SSKey.SUMMARY_LAST_MODELS.value: {"draft_model": "gpt-4o-mini"},
            SSKey.SUMMARY_INPUT_FINGERPRINT.value: "new",
            SSKey.SUMMARY_LAST_BRIEF_FINGERPRINT.value: "old",
        }
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)

    status = SUMMARY_MODULE._resolve_canonical_brief_status(
        resolved_brief_model="gpt-5-mini"
    )

    assert status.state == "invalid"
    assert status.ready_for_follow_ups is False
