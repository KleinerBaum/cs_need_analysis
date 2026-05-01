from __future__ import annotations

from types import SimpleNamespace

from constants import SSKey
import state


def test_esco_loaders_tolerate_missing_session_keys(monkeypatch) -> None:
    monkeypatch.setattr(state, "st", SimpleNamespace(session_state={}))

    assert state.get_esco_occupation_selected() is None
    assert state.get_esco_occupation_payload() is None
    assert state.get_esco_occupation_candidates() == []
    assert state.get_esco_skills_mapping_report() is None
    assert state.get_esco_anchor_status().status_reason == "anchor_not_confirmed"


def test_sync_esco_shared_state_updates_canonical_fields(monkeypatch) -> None:
    fake_state = {
        SSKey.ESCO_OCCUPATION_SELECTED.value: {
            "uri": "http://data.europa.eu/esco/occupation/123",
            "title": "Data Scientist",
            "type": "occupation",
        },
        SSKey.ESCO_SKILLS_SELECTED_MUST.value: [
            {"uri": "http://data.europa.eu/esco/skill/a", "title": "Python"},
        ],
        SSKey.ESCO_SKILLS_SELECTED_NICE.value: [
            {"uri": "http://data.europa.eu/esco/skill/b", "title": "Docker"},
        ],
        SSKey.ESCO_UNMAPPED_REQUIREMENT_TERMS.value: ["PySpark", "PySpark"],
        SSKey.JOB_EXTRACT.value: {
            "must_have_skills": ["Python", "SQL"],
            "nice_to_have_skills": ["Docker"],
        },
    }
    monkeypatch.setattr(state, "st", SimpleNamespace(session_state=fake_state))

    snapshot = state.sync_esco_shared_state()

    assert snapshot.selected_occupation_uri.endswith("/123")
    assert snapshot.essential_total == 2
    assert snapshot.essential_covered == 1
    assert snapshot.optional_total == 1
    assert snapshot.optional_covered == 1
    selected_uri = str(fake_state[SSKey.ESCO_SELECTED_OCCUPATION_URI.value])
    assert selected_uri.endswith("/123")
    assert fake_state[SSKey.ESCO_UNMAPPED_REQUIREMENT_TERMS.value] == ["PySpark"]


def test_esco_loaders_return_model_dump_payloads(monkeypatch) -> None:
    fake_state = {
        SSKey.ESCO_OCCUPATION_SELECTED.value: {
            "uri": "http://data.europa.eu/esco/occupation/123",
            "title": "Data Scientist",
            "type": "occupation",
            "code": "2511",
        },
        SSKey.ESCO_OCCUPATION_CANDIDATES.value: [
            {
                "uri": "http://data.europa.eu/esco/occupation/123",
                "title": "Data Scientist",
                "type": "occupation",
                "score": 0.94,
            },
            {"legacy": "entry"},
        ],
        SSKey.ESCO_SKILLS_MAPPING_REPORT.value: {
            "mapped_count": 2,
            "unmapped_terms": ["PySpark"],
            "collisions": ["Python"],
            "notes": ["Used exact label fallback."],
        },
        SSKey.ESCO_OCCUPATION_PAYLOAD.value: {
            "uri": "http://data.europa.eu/esco/occupation/123",
            "preferredLabel": "Data Scientist",
            "description": "Builds data products.",
        },
    }
    monkeypatch.setattr(state, "st", SimpleNamespace(session_state=fake_state))

    assert state.get_esco_occupation_selected() == {
        "uri": "http://data.europa.eu/esco/occupation/123",
        "title": "Data Scientist",
        "type": "occupation",
        "code": "2511",
    }
    assert state.get_esco_occupation_candidates() == [
        {
            "uri": "http://data.europa.eu/esco/occupation/123",
            "title": "Data Scientist",
            "type": "occupation",
            "score": 0.94,
        }
    ]
    assert state.get_esco_occupation_payload() == {
        "uri": "http://data.europa.eu/esco/occupation/123",
        "preferredLabel": "Data Scientist",
        "description": "Builds data products.",
    }
    assert state.get_esco_skills_mapping_report() == {
        "mapped_count": 2,
        "unmapped_terms": ["PySpark"],
        "collisions": ["Python"],
        "notes": ["Used exact label fallback."],
    }




def test_get_esco_occupation_selected_migrates_legacy_payload(monkeypatch) -> None:
    fake_state = {
        SSKey.ESCO_OCCUPATION_SELECTED.value: {
            "uri": "http://data.europa.eu/esco/occupation/legacy-1",
            "preferredLabel": "Legacy Occupation",
        }
    }
    monkeypatch.setattr(state, "st", SimpleNamespace(session_state=fake_state))

    selected = state.get_esco_occupation_selected()

    assert selected == {
        "uri": "http://data.europa.eu/esco/occupation/legacy-1",
        "title": "Legacy Occupation",
        "type": "occupation",
        "code": None,
    }
    assert fake_state[SSKey.ESCO_OCCUPATION_SELECTED.value]["type"] == "occupation"

def test_get_esco_anchor_status_handles_missing_selected_payload(monkeypatch) -> None:
    fake_state = {
        SSKey.ESCO_SELECTED_OCCUPATION_URI.value: "http://data.europa.eu/esco/occupation/123",
        SSKey.ESCO_OCCUPATION_SELECTED.value: {"legacy": "invalid"},
    }
    monkeypatch.setattr(state, "st", SimpleNamespace(session_state=fake_state))

    status = state.get_esco_anchor_status()

    assert status.anchor_confirmed is True
    assert status.selected_occupation is None
    assert status.status_reason == "anchor_confirmed_invalid_payload"
