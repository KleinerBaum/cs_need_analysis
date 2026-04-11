from __future__ import annotations

from pathlib import Path

from eures_mapping import (
    load_national_code_lookup_from_bytes,
    load_national_code_lookup_from_file,
)


def test_load_national_code_lookup_from_bytes_handles_utf8_bom_and_semicolon() -> None:
    raw = (
        b"\xef\xbb\xbfnational_code;esco_uri\n"
        b"47.11;http://data.europa.eu/esco/occupation/1\n"
    )

    mapping = load_national_code_lookup_from_bytes(raw)

    assert mapping == {"47.11": "http://data.europa.eu/esco/occupation/1"}


def test_load_national_code_lookup_from_file_path_ignores_incomplete_rows(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "mapping.csv"
    csv_path.write_text(
        "national_code,esco_uri\n47.19,http://data.europa.eu/esco/occupation/2\n,missing\n",
        encoding="utf-8",
    )

    mapping = load_national_code_lookup_from_file(csv_path)

    assert mapping == {"47.19": "http://data.europa.eu/esco/occupation/2"}
