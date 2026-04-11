from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any, Literal

from constants import SSKey


SUMMARY_PATH = Path(__file__).resolve().parents[1] / "wizard_pages" / "08_summary.py"
SPEC = spec_from_file_location("wizard_pages.page_08_summary_active", SUMMARY_PATH)
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
    def __init__(self, session_state: dict[str, Any], button_results: list[bool]):
        self.session_state = session_state
        self._button_results = button_results

    def container(self, **_: Any) -> _NoopContext:
        return _NoopContext()

    def markdown(self, *_: Any, **__: Any) -> None:
        return None

    def caption(self, *_: Any, **__: Any) -> None:
        return None

    def write(self, *_: Any, **__: Any) -> None:
        return None

    def button(self, *_: Any, **__: Any) -> bool:
        return self._button_results.pop(0) if self._button_results else False


def _build_action(action_id: str, result_key: SSKey) -> dict[str, Any]:
    return {
        "id": action_id,
        "title": "Action",
        "benefit": "desc",
        "cta_label": "Run",
        "blocked_cta_label": None,
        "requires": (SSKey.JOB_EXTRACT,),
        "requirement_text": "Jobspec vorhanden",
        "requirement_check_fn": None,
        "generator_fn": lambda: None,
        "result_key": result_key,
        "input_hints": (),
        "input_renderer": None,
    }


def test_active_artifact_tracks_latest_triggered_action(monkeypatch) -> None:
    """Expected vs Actual: aktives Ergebnis priorisiert zuletzt geklickte Action."""
    fake_st = _FakeStreamlit(
        session_state={SSKey.JOB_EXTRACT.value: {"job_title": "Engineer"}},
        button_results=[True, True],
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)

    first_triggered = SUMMARY_MODULE._render_action_card(
        _build_action("job_ad_generator", SSKey.JOB_AD_DRAFT_CUSTOM)
    )
    second_triggered = SUMMARY_MODULE._render_action_card(
        _build_action("boolean_search", SSKey.BOOLEAN_SEARCH_STRING)
    )

    assert first_triggered is True
    assert second_triggered is True
    assert (
        fake_st.session_state[SSKey.SUMMARY_ACTIVE_ARTIFACT.value] == "boolean_search"
    ), "Expected latest action to be active artifact; actual active artifact differs"
