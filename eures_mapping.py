"""Helpers for loading EURES/NACE -> ESCO lookup mappings from CSV."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import BinaryIO


def _decode_utf8_robust(raw_bytes: bytes) -> str:
    """Decode UTF-8 payloads robustly (BOM-tolerant, replacement on invalid bytes)."""

    return raw_bytes.decode("utf-8-sig", errors="replace")


def _normalize_field(value: object) -> str:
    return str(value or "").strip()


def _read_csv_rows(csv_text: str) -> list[dict[str, str]]:
    if not csv_text.strip():
        return []
    try:
        dialect = csv.Sniffer().sniff(csv_text[:1024], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(csv_text.splitlines(), dialect=dialect)
    rows: list[dict[str, str]] = []
    for row in reader:
        if not isinstance(row, dict):
            continue
        rows.append({str(key): _normalize_field(value) for key, value in row.items()})
    return rows


def build_national_code_lookup(rows: list[dict[str, str]]) -> dict[str, str]:
    """Build `national_code -> esco_uri` from parsed CSV dict rows."""

    lookup: dict[str, str] = {}
    for row in rows:
        code = _normalize_field(row.get("national_code"))
        uri = _normalize_field(row.get("esco_uri"))
        if code and uri:
            lookup[code] = uri
    return lookup


def load_national_code_lookup_from_bytes(raw_csv: bytes) -> dict[str, str]:
    """Load mapping lookup from bytes payload."""

    csv_text = _decode_utf8_robust(raw_csv)
    rows = _read_csv_rows(csv_text)
    return build_national_code_lookup(rows)


def load_national_code_lookup_from_file(path: str | Path | BinaryIO) -> dict[str, str]:
    """Load mapping lookup from a path-like or binary file handle."""

    if hasattr(path, "read"):
        raw_csv = path.read()
        if not isinstance(raw_csv, (bytes, bytearray)):
            raise ValueError("CSV stream must return bytes.")
        return load_national_code_lookup_from_bytes(bytes(raw_csv))
    raw_csv = Path(path).read_bytes()
    return load_national_code_lookup_from_bytes(raw_csv)
