from types import SimpleNamespace

from constants import SSKey
import state
from wizard_pages.jobad_intake import _usage_has_cache_hit


def test_usage_has_cache_hit_for_dict_usage() -> None:
    assert _usage_has_cache_hit({"cached": True}) is True
    assert _usage_has_cache_hit({"cached": 0}) is False


def test_usage_has_cache_hit_for_object_usage() -> None:
    assert _usage_has_cache_hit(SimpleNamespace(cached=True)) is True
    assert _usage_has_cache_hit(SimpleNamespace(cached="")) is False


def test_usage_has_cache_hit_for_unknown_usage_type() -> None:
    assert _usage_has_cache_hit(None) is False
    assert _usage_has_cache_hit("cached") is False


def test_jobad_cache_hit_clears_on_source_fingerprint_change(monkeypatch) -> None:
    old_fingerprint = state.build_jobspec_source_fingerprint("manual", "Alter Text")
    fake_session_state = {
        SSKey.SOURCE_ACTIVE.value: "manual",
        SSKey.SOURCE_ACTIVE_FINGERPRINT.value: old_fingerprint,
        SSKey.JOB_EXTRACT.value: {"job_title": "Engineer"},
        SSKey.QUESTION_PLAN.value: {"steps": []},
        SSKey.JOBAD_CACHE_HIT.value: {"extract_job_ad": True},
    }
    monkeypatch.setattr(state, "st", SimpleNamespace(session_state=fake_session_state))

    state.apply_jobspec_source_change("manual", "Neuer Text")

    assert fake_session_state[SSKey.JOBAD_CACHE_HIT.value] == {}


def test_jobad_cache_hit_survives_same_source_fingerprint(monkeypatch) -> None:
    fingerprint = state.build_jobspec_source_fingerprint("manual", "Gleicher Text")
    fake_session_state = {
        SSKey.SOURCE_ACTIVE.value: "manual",
        SSKey.SOURCE_ACTIVE_FINGERPRINT.value: fingerprint,
        SSKey.JOB_EXTRACT.value: {"job_title": "Engineer"},
        SSKey.QUESTION_PLAN.value: {"steps": []},
        SSKey.JOBAD_CACHE_HIT.value: {"extract_job_ad": True},
    }
    monkeypatch.setattr(state, "st", SimpleNamespace(session_state=fake_session_state))

    state.apply_jobspec_source_change("text", "Gleicher Text")

    assert fake_session_state[SSKey.JOBAD_CACHE_HIT.value] == {"extract_job_ad": True}
