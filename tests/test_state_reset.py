from __future__ import annotations

from types import SimpleNamespace

from constants import SSKey
import state


RESET_EXPECTATIONS: dict[SSKey, object] = {
    SSKey.SOURCE_TEXT: "",
    SSKey.SOURCE_FILE_META: {},
    SSKey.JOB_EXTRACT: None,
    SSKey.QUESTION_PLAN: None,
    SSKey.QUESTION_LIMITS: {},
    SSKey.ANSWERS: {},
    SSKey.ANSWER_META: {},
    SSKey.UI_MODE: "standard",
    SSKey.OPEN_GROUPS: {},
    SSKey.BRIEF: None,
    SSKey.JOBAD_CACHE_HIT: {},
    SSKey.SUMMARY_CACHE_HIT: False,
    SSKey.SUMMARY_LAST_MODE: None,
    SSKey.SUMMARY_LAST_MODELS: {},
    SSKey.SUMMARY_SELECTIONS: {},
    SSKey.SUMMARY_STYLEGUIDE_BLOCKS: [],
    SSKey.SUMMARY_CHANGE_REQUEST_BLOCKS: [],
    SSKey.SUMMARY_STYLEGUIDE_TEXT: "",
    SSKey.SUMMARY_CHANGE_REQUEST_TEXT: "",
    SSKey.SUMMARY_LOGO: None,
    SSKey.JOB_AD_DRAFT_CUSTOM: None,
    SSKey.JOB_AD_LAST_USAGE: {},
    SSKey.INTERVIEW_PREP_HR: None,
    SSKey.INTERVIEW_PREP_HR_LAST_USAGE: {},
    SSKey.INTERVIEW_PREP_HR_CACHE_HIT: False,
    SSKey.INTERVIEW_PREP_HR_LAST_MODE: None,
    SSKey.INTERVIEW_PREP_HR_LAST_MODELS: {},
    SSKey.INTERVIEW_PREP_FACH: None,
    SSKey.INTERVIEW_PREP_FACH_LAST_USAGE: {},
    SSKey.INTERVIEW_PREP_FACH_CACHE_HIT: False,
    SSKey.INTERVIEW_PREP_FACH_LAST_MODE: None,
    SSKey.INTERVIEW_PREP_FACH_LAST_MODELS: {},
    SSKey.BOOLEAN_SEARCH_STRING: None,
    SSKey.BOOLEAN_SEARCH_LAST_USAGE: {},
    SSKey.BOOLEAN_SEARCH_CACHE_HIT: False,
    SSKey.BOOLEAN_SEARCH_LAST_MODE: None,
    SSKey.BOOLEAN_SEARCH_LAST_MODELS: {},
    SSKey.EMPLOYMENT_CONTRACT_DRAFT: None,
    SSKey.EMPLOYMENT_CONTRACT_LAST_USAGE: {},
    SSKey.EMPLOYMENT_CONTRACT_CACHE_HIT: False,
    SSKey.EMPLOYMENT_CONTRACT_LAST_MODE: None,
    SSKey.EMPLOYMENT_CONTRACT_LAST_MODELS: {},
    SSKey.LAST_ERROR: None,
}


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

    for key, expected in RESET_EXPECTATIONS.items():
        assert fake_session_state[key.value] == expected
    assert fake_session_state[SSKey.CURRENT_STEP.value] == "landing"


def test_init_session_state_and_reset_vacancy_share_same_defaults(monkeypatch) -> None:
    fake_session_state: dict[str, object] = {}
    monkeypatch.setattr(
        state,
        "load_openai_settings",
        lambda: SimpleNamespace(openai_model="gpt-5-mini"),
    )
    monkeypatch.setattr(
        state,
        "st",
        SimpleNamespace(session_state=fake_session_state),
    )

    state.init_session_state()

    initialized_defaults = {
        key.value: fake_session_state[key.value] for key in RESET_EXPECTATIONS
    }
    fake_session_state[SSKey.SOURCE_TEXT.value] = "filled"
    fake_session_state[SSKey.INTERVIEW_PREP_HR.value] = {"blocks": []}

    state.reset_vacancy()

    for key, expected in RESET_EXPECTATIONS.items():
        assert fake_session_state[key.value] == expected
        assert initialized_defaults[key.value] == expected


def test_init_session_state_uses_env_esco_api_base_url(monkeypatch) -> None:
    fake_session_state: dict[str, object] = {}
    monkeypatch.setenv("ESCO_API_BASE_URL", "https://env.example/esco/")
    monkeypatch.setattr(
        state,
        "load_openai_settings",
        lambda: SimpleNamespace(openai_model="gpt-5-mini"),
    )
    monkeypatch.setattr(
        state,
        "st",
        SimpleNamespace(session_state=fake_session_state),
    )

    state.init_session_state()

    assert fake_session_state[SSKey.ESCO_CONFIG.value]["base_url"] == (
        "https://env.example/esco/"
    )
