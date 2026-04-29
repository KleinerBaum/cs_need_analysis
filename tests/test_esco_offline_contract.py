from __future__ import annotations

from pathlib import Path

import pytest

import esco_client
from esco_client import EscoClient


def _write_minimal_index(tmp_path: Path) -> Path:
    from scripts.build_esco_index import build_index

    src = tmp_path / "src"
    src.mkdir()
    (src / "occupations_en.csv").write_text("conceptUri,code\nocc:1,111\n", encoding="utf-8")
    (src / "skills_en.csv").write_text("conceptUri,code\nskill:1,222\n", encoding="utf-8")
    (src / "labels_en.csv").write_text(
        "conceptUri,language,preferredLabel\nocc:1,de,Softwareentwickler\nskill:1,de,Python\n",
        encoding="utf-8",
    )
    (src / "broaderRelationsSkillPillar.csv").write_text(
        "conceptUri,broaderUri,relationType\nocc:1,skill:1,hasEssentialSkill\n",
        encoding="utf-8",
    )
    out = tmp_path / "index"
    build_index(source_dir=src, out_dir=out, version="vtest")
    return out


def test_offline_mode_contract_shapes(tmp_path: Path) -> None:
    index_root = _write_minimal_index(tmp_path)
    session_state = {
        "cs.esco_config": {
            "data_source_mode": "offline_index",
            "index_storage_path": str(index_root),
            "index_version": "vtest",
            "language": "de",
            "selected_version": "vtest",
        }
    }
    client = EscoClient(session_state=session_state)

    search_payload = client.search(text="Software", type="occupation", limit=5)
    search_results = search_payload.get("_embedded", {}).get("results", [])
    assert isinstance(search_results, list)
    assert search_results
    first_search = search_results[0]
    assert first_search.get("uri") == "occ:1"
    assert first_search.get("title") == "Softwareentwickler"
    assert first_search.get("label") == "Softwareentwickler"
    assert first_search.get("preferredLabel") == "Softwareentwickler"
    assert first_search.get("conceptType") == "occupation"

    terms_payload = client.terms(uri="occ:1", type="occupation")
    terms_results = terms_payload.get("_embedded", {}).get("results", [])
    assert isinstance(terms_results, list)
    assert terms_results
    first_term = terms_results[0]
    assert first_term.get("uri") == "occ:1"
    assert first_term.get("title") == "Softwareentwickler"
    assert first_term.get("label") == "Softwareentwickler"
    assert first_term.get("preferredLabel") == "Softwareentwickler"
    assert first_term.get("conceptType") == "occupation"

    occupation_payload = client.resource_occupation(uri="occ:1")
    assert isinstance(occupation_payload, dict)
    assert occupation_payload.get("uri") == "occ:1"
    assert occupation_payload.get("title") == "Softwareentwickler"
    assert occupation_payload.get("label") == "Softwareentwickler"
    assert occupation_payload.get("preferredLabel") == "Softwareentwickler"
    assert occupation_payload.get("conceptType") == "occupation"

    related_payload = client.resource_related(uri="occ:1", relation="hasEssentialSkill")
    related_results = related_payload.get("_embedded", {}).get("results", [])
    assert isinstance(related_results, list)
    assert related_results
    first_related = related_results[0]
    assert first_related.get("uri") == "skill:1"
    assert first_related.get("title") == "Python"
    assert first_related.get("label") == "Python"
    assert first_related.get("preferredLabel") == "Python"
    assert first_related.get("conceptType") == "skill"


def test_offline_mode_skill_detail_does_not_call_live_api(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    index_root = _write_minimal_index(tmp_path)
    session_state = {
        "cs.esco_config": {
            "data_source_mode": "offline_index",
            "index_storage_path": str(index_root),
            "index_version": "vtest",
            "language": "de",
            "selected_version": "vtest",
        }
    }
    client = EscoClient(session_state=session_state)
    call_counter = {"count": 0}

    def fail_if_live_api_called(**_kwargs):
        call_counter["count"] += 1
        raise AssertionError("_cached_get_json should not be called in offline_index mode")

    monkeypatch.setattr(esco_client, "_cached_get_json", fail_if_live_api_called)

    skill_payload = client.resource_skill(uri="skill:1")

    assert skill_payload.get("uri") == "skill:1"
    assert skill_payload.get("title") == "Python"
    assert skill_payload.get("label") == "Python"
    assert skill_payload.get("preferredLabel") == "Python"
    assert skill_payload.get("conceptType") == "skill"
    assert call_counter["count"] == 0


def test_offline_mode_suggest2_does_not_call_live_api(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    index_root = _write_minimal_index(tmp_path)
    session_state = {
        "cs.esco_config": {
            "data_source_mode": "offline_index",
            "index_storage_path": str(index_root),
            "index_version": "vtest",
            "language": "de",
            "selected_version": "vtest",
        }
    }
    client = EscoClient(session_state=session_state)
    call_counter = {"count": 0}

    def fail_if_live_api_called(**_kwargs):
        call_counter["count"] += 1
        raise AssertionError("_cached_get_json should not be called in offline_index mode")

    monkeypatch.setattr(esco_client, "_cached_get_json", fail_if_live_api_called)

    suggest_payload = client.suggest2(text="Py", type="skill", limit=5)
    results = suggest_payload.get("_embedded", {}).get("results", [])
    assert isinstance(results, list)
    assert any(item.get("uri") == "skill:1" for item in results if isinstance(item, dict))
    skill_result = next(
        (item for item in results if isinstance(item, dict) and item.get("uri") == "skill:1"),
        {},
    )
    assert skill_result.get("title") == "Python"
    assert skill_result.get("label") == "Python"
    assert skill_result.get("preferredLabel") == "Python"
    assert skill_result.get("conceptType") == "skill"
    assert call_counter["count"] == 0


def test_offline_mode_still_rejects_unsupported_endpoint_without_live_api(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    index_root = _write_minimal_index(tmp_path)
    session_state = {
        "cs.esco_config": {
            "data_source_mode": "offline_index",
            "index_storage_path": str(index_root),
            "index_version": "vtest",
            "language": "de",
            "selected_version": "vtest",
        }
    }
    client = EscoClient(session_state=session_state)
    call_counter = {"count": 0}

    def fail_if_live_api_called(**_kwargs):
        call_counter["count"] += 1
        raise AssertionError("_cached_get_json should not be called in offline_index mode")

    monkeypatch.setattr(esco_client, "_cached_get_json", fail_if_live_api_called)

    with pytest.raises(esco_client.EscoClientError) as exc_info:
        client.conversion("skill", uri="legacy:123")

    assert (
        str(exc_info.value)
        == "The requested ESCO endpoint is not available in offline_index mode."
    )
    assert exc_info.value.endpoint == "conversion/skill"
    assert call_counter["count"] == 0
