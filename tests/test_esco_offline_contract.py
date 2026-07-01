from __future__ import annotations

from pathlib import Path

import pytest

import esco_client
from esco_offline_index import read_manifest
from esco_client import EscoClient


def _write_minimal_index(tmp_path: Path) -> Path:
    from scripts.build_esco_index import build_index

    src = tmp_path / "src"
    src.mkdir()
    (src / "occupations_en.csv").write_text(
        "conceptUri,code\nocc:1,111\n", encoding="utf-8"
    )
    (src / "skills_en.csv").write_text(
        "conceptUri,code\nskill:1,222\n", encoding="utf-8"
    )
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


def test_offline_build_writes_versioned_manifest_and_normalized_artifacts(
    tmp_path: Path,
) -> None:
    index_root = _write_minimal_index(tmp_path)
    manifest_path = index_root / "indexed" / "vtest" / "manifest.json"
    normalized_dir = index_root / "normalized" / "vtest"

    assert (index_root / "indexed" / "vtest" / "esco_index.sqlite").exists()
    assert (normalized_dir / "concepts.csv").exists()
    assert (normalized_dir / "labels.csv").exists()
    assert (normalized_dir / "relations.csv").exists()

    manifest = read_manifest(manifest_path)
    assert manifest["schema_version"] == 1
    assert manifest["layout_version"] == "esco_offline_build_v1"
    assert manifest["version"] == "vtest"
    assert manifest["normalized_dir"] == "normalized/vtest"
    assert manifest["indexed_dir"] == "indexed/vtest"
    assert manifest["languages"] == ["de"]
    assert manifest["counts"] == {"concepts": 2, "labels": 2, "relations": 1}
    assert {item["name"] for item in manifest["source_files"]} == {
        "occupations_en.csv",
        "skills_en.csv",
        "labels_en.csv",
        "broaderRelationsSkillPillar.csv",
    }
    assert all(item["sha256"] for item in manifest["source_files"])


def test_offline_build_ingests_official_style_csv_bulk_files(tmp_path: Path) -> None:
    from scripts.build_esco_index import build_index

    src = tmp_path / "src"
    src.mkdir()
    (src / "occupations.csv").write_text(
        (
            "conceptUri,code,preferredLabel,altLabels\n"
            "occ:official,2512,Software Developer,Application developer|Coder\n"
        ),
        encoding="utf-8",
    )
    (src / "skills.csv").write_text(
        (
            "conceptUri,code,preferredLabel,altLabels\n"
            "skill:official,KS123,Python programming,Python|Python language\n"
        ),
        encoding="utf-8",
    )
    (src / "occupationSkillRelations.csv").write_text(
        "occupationUri,skillUri,relationType\nocc:official,skill:official,essential\n",
        encoding="utf-8",
    )

    out = tmp_path / "index"
    build_index(source_dir=src, out_dir=out, version="vbulk")
    manifest = read_manifest(out / "indexed" / "vbulk" / "manifest.json")
    client = EscoClient(
        session_state={
            "cs.esco_config": {
                "data_source_mode": "offline_index",
                "index_storage_path": str(out),
                "index_version": "vbulk",
                "language": "en",
                "selected_version": "vbulk",
            }
        }
    )

    assert manifest["counts"] == {"concepts": 2, "labels": 6, "relations": 1}
    assert {item["name"] for item in manifest["source_files"]} == {
        "occupations.csv",
        "skills.csv",
        "occupationSkillRelations.csv",
    }

    search_payload = client.search(text="Coder", type="occupation", limit=5)
    search_results = search_payload.get("_embedded", {}).get("results", [])
    assert search_results[0]["uri"] == "occ:official"
    assert search_results[0]["title"] == "Coder"

    occupation_payload = client.resource_occupation(uri="occ:official")
    assert occupation_payload["preferredLabel"] == "Software Developer"

    related_payload = client.resource_related(
        uri="occ:official",
        relation="hasEssentialSkill",
    )
    related_results = related_payload.get("_embedded", {}).get("results", [])
    assert related_results[0]["uri"] == "skill:official"
    assert related_results[0]["preferredLabel"] == "Python programming"


def test_offline_build_maps_broader_relation_csv_to_transitive_relation(
    tmp_path: Path,
) -> None:
    from scripts.build_esco_index import build_index

    src = tmp_path / "src"
    src.mkdir()
    (src / "skills.csv").write_text(
        (
            "conceptUri,code,preferredLabel\n"
            "skill:child,KS1,Python programming\n"
            "skill:parent,KS2,Programming languages\n"
        ),
        encoding="utf-8",
    )
    (src / "broaderRelationsSkillPillar.csv").write_text(
        "conceptUri,broaderUri,broaderType\nskill:child,skill:parent,skillGroup\n",
        encoding="utf-8",
    )

    out = tmp_path / "index"
    build_index(source_dir=src, out_dir=out, version="vbroader")
    client = EscoClient(
        session_state={
            "cs.esco_config": {
                "data_source_mode": "offline_index",
                "index_storage_path": str(out),
                "index_version": "vbroader",
                "language": "en",
                "selected_version": "vbroader",
            }
        }
    )

    related_payload = client.resource_related(
        uri="skill:child",
        relation="hasBroaderTransitive",
    )
    related_results = related_payload.get("_embedded", {}).get("results", [])

    assert related_results == [
        {
            "uri": "skill:parent",
            "title": "Programming languages",
            "label": "Programming languages",
            "preferredLabel": "Programming languages",
            "conceptType": "skill",
            "type": "skill",
        }
    ]


def test_offline_build_normalizes_relation_type_uris(tmp_path: Path) -> None:
    from scripts.build_esco_index import build_index

    src = tmp_path / "src"
    src.mkdir()
    (src / "occupations.csv").write_text(
        "conceptUri,code,preferredLabel\nocc:official,2512,Software Developer\n",
        encoding="utf-8",
    )
    (src / "skills.csv").write_text(
        "conceptUri,code,preferredLabel\nskill:official,KS123,Python programming\n",
        encoding="utf-8",
    )
    (src / "occupationSkillRelations.csv").write_text(
        (
            "occupationUri,skillUri,relationType\n"
            "occ:official,skill:official,"
            "http://data.europa.eu/esco/model#hasOptionalSkill\n"
        ),
        encoding="utf-8",
    )

    out = tmp_path / "index"
    build_index(source_dir=src, out_dir=out, version="vuri")
    client = EscoClient(
        session_state={
            "cs.esco_config": {
                "data_source_mode": "offline_index",
                "index_storage_path": str(out),
                "index_version": "vuri",
                "language": "en",
                "selected_version": "vuri",
            }
        }
    )

    related_payload = client.resource_related(
        uri="occ:official",
        relation="hasOptionalSkill",
    )
    related_results = related_payload.get("_embedded", {}).get("results", [])

    assert related_results
    assert related_results[0]["uri"] == "skill:official"
    assert related_results[0]["preferredLabel"] == "Python programming"


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
        raise AssertionError(
            "_cached_get_json should not be called in offline_index mode"
        )

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
        raise AssertionError(
            "_cached_get_json should not be called in offline_index mode"
        )

    monkeypatch.setattr(esco_client, "_cached_get_json", fail_if_live_api_called)

    suggest_payload = client.suggest2(text="Py", type="skill", limit=5)
    results = suggest_payload.get("_embedded", {}).get("results", [])
    assert isinstance(results, list)
    assert any(
        item.get("uri") == "skill:1" for item in results if isinstance(item, dict)
    )
    skill_result = next(
        (
            item
            for item in results
            if isinstance(item, dict) and item.get("uri") == "skill:1"
        ),
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
        raise AssertionError(
            "_cached_get_json should not be called in offline_index mode"
        )

    monkeypatch.setattr(esco_client, "_cached_get_json", fail_if_live_api_called)

    with pytest.raises(esco_client.EscoClientError) as exc_info:
        client.conversion("skill", uri="legacy:123")

    assert (
        str(exc_info.value)
        == "The requested ESCO endpoint is not available in offline_index mode."
    )
    assert exc_info.value.endpoint == "conversion/skill"
    assert call_counter["count"] == 0
