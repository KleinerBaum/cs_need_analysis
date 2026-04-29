from __future__ import annotations

import json

import pytest
from openpyxl import Workbook

from esco_matrix import load_esco_matrix
from scripts.build_esco_matrix import convert_xlsx_to_matrix_json


def test_load_esco_matrix_json_parses_metadata_and_candidates(tmp_path) -> None:
    matrix_path = tmp_path / "matrix.json"
    matrix_path.write_text(
        json.dumps(
            {
                "source": "offline_build",
                "version": "2026.04",
                "records": [
                    {
                        "occupation_uri": "uri:occ:1",
                        "skill_uri": "uri:skill:python",
                        "skill_title": "Python",
                        "bucket": "must",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    lookup = load_esco_matrix(matrix_path)

    assert lookup.metadata.version == "2026.04"
    must, nice = lookup.candidates_for(occupation_uri="uri:occ:1")
    assert len(must) == 1 and nice == []
    assert must[0]["source"] == "ESCO matrix prior"


def test_load_esco_matrix_raises_on_missing_identifiers(tmp_path) -> None:
    matrix_path = tmp_path / "matrix.csv"
    matrix_path.write_text(
        "occupation_uri,skill_uri,bucket\n,uri:skill:python,must\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="occupation_uri or occupation_group"):
        load_esco_matrix(matrix_path)


def test_build_esco_matrix_from_xlsx_and_load(tmp_path) -> None:
    xlsx_path = tmp_path / "esco_matrix.xlsx"
    out_json = tmp_path / "esco_matrix.normalized.json"

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "matrix"
    sheet.append(
        [
            "occupation_group",
            "skill_group_uri",
            "skill_group_label",
            "share_percent",
        ]
    )
    sheet.append(
        [
            "251",
            "http://data.europa.eu/esco/skill-group/data-analysis",
            "Data analysis",
            62.5,
        ]
    )
    sheet.append(
        [
            "251",
            "http://data.europa.eu/esco/skill-group/collaboration",
            "Collaboration",
            30.0,
        ]
    )
    sheet.append(
        [
            "251",
            "",
            "Planning",
            20.0,
        ]
    )
    workbook.save(xlsx_path)

    payload = convert_xlsx_to_matrix_json(
        xlsx_path=xlsx_path,
        out_json_path=out_json,
        version="2026.05",
    )

    assert payload["version"] == "2026.05"
    assert len(payload["records"]) == 3
    first = payload["records"][0]
    assert first["occupation_group"] == "251"
    assert first["skill_group_uri"] == "http://data.europa.eu/esco/skill-group/data-analysis"
    assert first["skill_group_label"] == "Data analysis"
    assert first["share_percent"] == 62.5
    assert first["bucket"] == "must"
    assert first["skill_uri"] == "http://data.europa.eu/esco/skill-group/data-analysis"
    third = payload["records"][2]
    assert third["skill_group_uri"] == ""
    assert str(third["skill_group_id"]).startswith("skill-group-planning-")
    assert third["skill_uri"].startswith("urn:esco:skill-group:")

    lookup = load_esco_matrix(out_json)
    must, nice = lookup.candidates_for(occupation_uri="", occupation_group="251")
    assert len(must) == 1
    assert len(nice) == 2
    assert must[0]["uri"] == "http://data.europa.eu/esco/skill-group/data-analysis"
    assert nice[0]["uri"] == "http://data.europa.eu/esco/skill-group/collaboration"
