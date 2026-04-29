from __future__ import annotations

import json

import pytest

from esco_matrix import load_esco_matrix


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
