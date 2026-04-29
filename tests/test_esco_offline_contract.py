from __future__ import annotations

from pathlib import Path

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
    assert isinstance(search_payload.get("_embedded", {}).get("results", []), list)

    terms_payload = client.terms(uri="occ:1", type="occupation")
    assert isinstance(terms_payload.get("_embedded", {}).get("results", []), list)

    occupation_payload = client.resource_occupation(uri="occ:1")
    assert isinstance(occupation_payload, dict)
    assert occupation_payload.get("uri") == "occ:1"

    related_payload = client.resource_related(uri="occ:1", relation="hasEssentialSkill")
    assert isinstance(related_payload.get("_embedded", {}).get("results", []), list)
