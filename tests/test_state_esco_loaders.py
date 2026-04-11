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
