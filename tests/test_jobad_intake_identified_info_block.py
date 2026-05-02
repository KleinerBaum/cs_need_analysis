from __future__ import annotations

from types import SimpleNamespace
from typing import cast

from constants import SSKey
import wizard_pages.jobad_intake as jobad_intake


class _DummyColumn:
    def __enter__(self) -> "_DummyColumn":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class _FakeStreamlit:
    def __init__(
        self,
        *,
        session_state: dict[str, object],
        button_returns: dict[str, bool] | None = None,
    ) -> None:
        self.session_state = session_state
        self._button_returns = button_returns or {}
        self.button_disabled: dict[str, bool] = {}
        self.captions: list[str] = []
        self.successes: list[str] = []
        self.expanders: list[str] = []
        self.rerun_called = False
        self.column_config = SimpleNamespace(
            TextColumn=lambda *args, **kwargs: None,
        )

    def markdown(self, *_args, **_kwargs) -> None:
        return None

    def caption(self, text: str, *_args, **_kwargs) -> None:
        self.captions.append(text)

    def data_editor(self, rows, **_kwargs):
        return rows

    def columns(self, spec, **_kwargs):
        if isinstance(spec, int):
            count = spec
        else:
            count = len(spec)
        return tuple(_DummyColumn() for _ in range(count))

    def write(self, *_args, **_kwargs) -> None:
        return None

    def info(self, *_args, **_kwargs) -> None:
        return None

    def success(self, text: str, *_args, **_kwargs) -> None:
        self.successes.append(text)

    def expander(self, label: str, expanded: bool = False):
        self.expanders.append(label)
        return _DummyColumn()

    def button(self, _label: str, *, key: str, disabled: bool = False) -> bool:
        self.button_disabled[key] = disabled
        if disabled:
            return False
        return self._button_returns.get(key, False)

    def rerun(self) -> None:
        self.rerun_called = True


def _minimal_identified_info_state() -> dict[str, object]:
    return {
        SSKey.JOB_EXTRACT.value: {"job_title": "Data Engineer"},
        SSKey.QUESTION_PLAN.value: {"steps": []},
        SSKey.ESCO_SELECTED_OCCUPATION_URI.value: "",
    }


def test_identified_info_next_is_enabled_without_esco_anchor(monkeypatch) -> None:
    fake_st = _FakeStreamlit(session_state=_minimal_identified_info_state())
    next_calls = {"count": 0}
    ctx = cast(
        jobad_intake.WizardContext,
        SimpleNamespace(
            prev=lambda: None,
            next=lambda: next_calls.__setitem__("count", next_calls["count"] + 1),
        ),
    )

    monkeypatch.setattr(jobad_intake, "st", fake_st)
    monkeypatch.setattr(jobad_intake, "get_esco_occupation_selected", lambda: None)
    monkeypatch.setattr(jobad_intake, "has_confirmed_esco_anchor", lambda: False)
    overview_calls: list[dict[str, object]] = []

    def _capture_overview(*_args, **kwargs) -> None:
        overview_calls.append(kwargs)

    monkeypatch.setattr(jobad_intake, "render_job_extract_overview", _capture_overview)

    jobad_intake._render_identified_information_block(ctx)

    assert "Analyse abgeschlossen" in fake_st.successes
    assert (
        "Extrahierte Werte und dynamische Rückfragen wurden vorbereitet. "
        "Prüfen Sie die Angaben und bestätigen Sie anschließend den ESCO-Anker."
        in fake_st.captions
    )
    assert "Technische Details zur Analyse" in fake_st.expanders
    assert "cs.jobspec.ident_info.next" not in fake_st.button_disabled
    assert (
        "Optional: In Phase C können Sie einen semantischen ESCO-Anker bestätigen."
        in fake_st.captions
    )
    assert overview_calls
    assert overview_calls[0].get("mode") == "compact"
    assert next_calls["count"] == 0
    assert fake_st.rerun_called is False


def test_identified_info_next_uses_selected_occupation_fallback(monkeypatch) -> None:
    fake_st = _FakeStreamlit(
        session_state=_minimal_identified_info_state(),
        button_returns={},
    )
    next_calls = {"count": 0}
    ctx = cast(
        jobad_intake.WizardContext,
        SimpleNamespace(
            prev=lambda: None,
            next=lambda: next_calls.__setitem__("count", next_calls["count"] + 1),
        ),
    )

    monkeypatch.setattr(jobad_intake, "st", fake_st)
    monkeypatch.setattr(
        jobad_intake,
        "get_esco_occupation_selected",
        lambda: {
            "uri": "http://data.europa.eu/esco/occupation/123",
            "title": "Data Scientist",
            "type": "occupation",
        },
    )
    monkeypatch.setattr(jobad_intake, "has_confirmed_esco_anchor", lambda: True)

    jobad_intake._render_identified_information_block(ctx)

    assert "cs.jobspec.ident_info.next" not in fake_st.button_disabled
    assert "ESCO-Anker bestätigt: Data Scientist" in fake_st.successes
    assert next_calls["count"] == 0
    assert fake_st.rerun_called is False


def test_has_completed_landing_analysis_requires_both_dicts(monkeypatch) -> None:
    fake_st = _FakeStreamlit(
        session_state={
            SSKey.JOB_EXTRACT.value: {"job_title": "Data Engineer"},
            SSKey.QUESTION_PLAN.value: None,
        }
    )
    monkeypatch.setattr(jobad_intake, "st", fake_st)

    assert jobad_intake._has_completed_landing_analysis() is False


def test_has_completed_landing_analysis_true_when_both_dicts(monkeypatch) -> None:
    fake_st = _FakeStreamlit(session_state=_minimal_identified_info_state())
    monkeypatch.setattr(jobad_intake, "st", fake_st)

    assert jobad_intake._has_completed_landing_analysis() is True
