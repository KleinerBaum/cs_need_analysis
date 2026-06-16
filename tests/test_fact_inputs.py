from __future__ import annotations

from types import SimpleNamespace

from constants import FactKey, SSKey
import state
from wizard_pages import fact_inputs


def test_persist_fact_writes_answer_and_canonical_intake_fact(monkeypatch) -> None:
    session_state = {
        SSKey.ANSWERS.value: {},
        SSKey.ANSWER_META.value: {},
        SSKey.INTAKE_FACTS.value: {},
        SSKey.INTAKE_FACT_EVIDENCE.value: {},
        SSKey.USAGE_EVENTS.value: [],
    }
    fake_st = SimpleNamespace(session_state=session_state)
    monkeypatch.setattr(state, "st", fake_st)
    monkeypatch.setattr(fact_inputs, "st", fake_st)

    value = {"eligible": True, "ote_min": 90000, "currency": "EUR"}

    fact_inputs.persist_fact(FactKey.BENEFITS_VARIABLE_PAY, value)

    assert session_state[SSKey.ANSWERS.value][FactKey.BENEFITS_VARIABLE_PAY.value] == value
    assert session_state[SSKey.INTAKE_FACTS.value][FactKey.BENEFITS_VARIABLE_PAY.value] == value
    assert session_state[SSKey.ANSWER_META.value][FactKey.BENEFITS_VARIABLE_PAY.value]["touched"] is True


def test_persist_compact_object_drops_empty_strings_but_keeps_false(monkeypatch) -> None:
    session_state = {
        SSKey.ANSWERS.value: {},
        SSKey.ANSWER_META.value: {},
        SSKey.INTAKE_FACTS.value: {},
        SSKey.INTAKE_FACT_EVIDENCE.value: {},
        SSKey.USAGE_EVENTS.value: [],
    }
    fake_st = SimpleNamespace(session_state=session_state)
    monkeypatch.setattr(state, "st", fake_st)
    monkeypatch.setattr(fact_inputs, "st", fake_st)

    value = fact_inputs.persist_compact_object(
        FactKey.ROLE_TRAVEL_PROFILE,
        {"required": False, "frequency": "", "percent": 0},
    )

    assert value == {"required": False, "percent": 0}
    assert session_state[SSKey.INTAKE_FACTS.value][FactKey.ROLE_TRAVEL_PROFILE.value] == value
