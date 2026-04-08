from __future__ import annotations

from types import SimpleNamespace

from constants import SSKey
import state


def test_reset_vacancy_clears_progressive_disclosure_state(
    monkeypatch,
) -> None:
    fake_session_state = {
        SSKey.SOURCE_TEXT.value: "Jobspec",
        SSKey.SOURCE_FILE_META.value: {"name": "input.pdf"},
        SSKey.JOB_EXTRACT.value: {"job_title": "Engineer"},
        SSKey.QUESTION_PLAN.value: {"steps": []},
        SSKey.QUESTION_LIMITS.value: {"company": 3},
        SSKey.ANSWERS.value: {"q1": "value"},
        SSKey.ANSWER_META.value: {"q1": {"touched": True}},
        SSKey.UI_MODE.value: "expert",
        SSKey.OPEN_GROUPS.value: {"company": {"Details": True}},
        SSKey.BRIEF.value: {"one_liner": "x"},
        SSKey.JOBAD_CACHE_HIT.value: {"hit": True},
        SSKey.SUMMARY_CACHE_HIT.value: True,
        SSKey.SUMMARY_LAST_MODE.value: "custom",
        SSKey.SUMMARY_LAST_MODELS.value: {"summary": "gpt"},
        SSKey.SUMMARY_SELECTIONS.value: {"a": 1},
        SSKey.JOB_AD_DRAFT_CUSTOM.value: "draft",
        SSKey.JOB_AD_LAST_USAGE.value: {"tokens": 12},
        SSKey.LAST_ERROR.value: "error",
        SSKey.CURRENT_STEP.value: "summary",
    }
    monkeypatch.setattr(
        state,
        "st",
        SimpleNamespace(session_state=fake_session_state),
    )

    state.reset_vacancy()

    assert fake_session_state[SSKey.SOURCE_TEXT.value] == ""
    assert fake_session_state[SSKey.QUESTION_PLAN.value] is None
    assert fake_session_state[SSKey.ANSWERS.value] == {}
    assert fake_session_state[SSKey.ANSWER_META.value] == {}
    assert fake_session_state[SSKey.UI_MODE.value] == "standard"
    assert fake_session_state[SSKey.OPEN_GROUPS.value] == {}
    assert fake_session_state[SSKey.CURRENT_STEP.value] == "landing"
