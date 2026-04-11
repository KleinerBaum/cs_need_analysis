"""Salary benchmark loading and lookup utilities.

This module is domain-only and intentionally independent from Streamlit.
"""

from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Any

from schemas import StrictSchemaModel


class SalaryBenchmarkRow(StrictSchemaModel):
    """One normalized salary benchmark row."""

    dataset_version: str
    year: int
    country_code: str
    region_id: str
    occupation_id: str
    currency: str
    period: str
    n: int | None = None
    p10: float
    p50: float
    p90: float
    source_label: str


BenchmarkIndex = dict[str, dict[str, dict[int, SalaryBenchmarkRow]]]


_REQUIRED_COLUMNS = {
    "dataset_version",
    "year",
    "country_code",
    "region_id",
    "occupation_id",
    "currency",
    "period",
    "n",
    "p10",
    "p50",
    "p90",
    "source_label",
}


def _parse_int(value: str, *, field_name: str, row_num: int) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(
            f"Invalid integer for '{field_name}' at row {row_num}: {value!r}"
        ) from exc


def _parse_nullable_int(value: str, *, field_name: str, row_num: int) -> int | None:
    if value == "":
        return None
    return _parse_int(value, field_name=field_name, row_num=row_num)


def _parse_float(value: str, *, field_name: str, row_num: int) -> float:
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(
            f"Invalid float for '{field_name}' at row {row_num}: {value!r}"
        ) from exc


def load_benchmark_csv(path: Path) -> list[SalaryBenchmarkRow]:
    """Load salary benchmark rows from a local CSV file."""

    if not path.exists():
        raise FileNotFoundError(f"Benchmark CSV file does not exist: {path}")

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        header = set(reader.fieldnames or [])
        missing = sorted(_REQUIRED_COLUMNS - header)
        if missing:
            raise ValueError(
                f"Benchmark CSV missing required columns: {', '.join(missing)}"
            )

        rows: list[SalaryBenchmarkRow] = []
        for row_num, raw in enumerate(reader, start=2):
            payload: dict[str, Any] = {
                "dataset_version": (raw.get("dataset_version") or "").strip(),
                "year": _parse_int(
                    (raw.get("year") or "").strip(), field_name="year", row_num=row_num
                ),
                "country_code": (raw.get("country_code") or "").strip(),
                "region_id": (raw.get("region_id") or "").strip(),
                "occupation_id": (raw.get("occupation_id") or "").strip(),
                "currency": (raw.get("currency") or "").strip(),
                "period": (raw.get("period") or "").strip(),
                "n": _parse_nullable_int(
                    (raw.get("n") or "").strip(), field_name="n", row_num=row_num
                ),
                "p10": _parse_float(
                    (raw.get("p10") or "").strip(), field_name="p10", row_num=row_num
                ),
                "p50": _parse_float(
                    (raw.get("p50") or "").strip(), field_name="p50", row_num=row_num
                ),
                "p90": _parse_float(
                    (raw.get("p90") or "").strip(), field_name="p90", row_num=row_num
                ),
                "source_label": (raw.get("source_label") or "").strip(),
            }
            rows.append(SalaryBenchmarkRow.model_validate(payload, strict=True))
    return rows


def build_benchmark_index(rows: list[SalaryBenchmarkRow]) -> BenchmarkIndex:
    """Build an in-memory index keyed as occupation_id -> region_id -> year."""

    index: BenchmarkIndex = {}
    for row in rows:
        by_region = index.setdefault(row.occupation_id, {})
        by_year = by_region.setdefault(row.region_id, {})
        by_year[row.year] = row
    return index


def _select_row(
    by_year: dict[int, SalaryBenchmarkRow], year: int | None
) -> SalaryBenchmarkRow | None:
    if not by_year:
        return None
    if year is not None:
        return by_year.get(year)
    latest_year = max(by_year)
    return by_year[latest_year]


def _lookup_for(
    index: BenchmarkIndex, *, occupation_id: str, region_id: str, year: int | None
) -> SalaryBenchmarkRow | None:
    return _select_row(index.get(occupation_id, {}).get(region_id, {}), year=year)


def lookup_benchmark(
    index: BenchmarkIndex,
    *,
    occupation_id: str,
    region_id: str,
    year: int | None = None,
) -> SalaryBenchmarkRow | None:
    """Lookup benchmark with deterministic fallback chain.

    Fallback order:
    1) exact occupation_id + region_id
    2) same occupation_id + region_id="DE"
    3) occupation_id="ANY" + original region_id
    4) occupation_id="ANY" + region_id="DE"
    5) None

    If ``year`` is omitted, the latest available year per selected key is returned.
    """

    for occ, reg in (
        (occupation_id, region_id),
        (occupation_id, "DE"),
        ("ANY", region_id),
        ("ANY", "DE"),
    ):
        row = _lookup_for(index, occupation_id=occ, region_id=reg, year=year)
        if row is not None:
            return row
    return None


def resolve_salary_benchmark_path() -> Path:
    """Resolve the benchmark CSV path from env override or default demo dataset."""

    configured = os.getenv("SALARY_BENCHMARK_PATH")
    if configured:
        return Path(configured).expanduser()

    return (
        Path(__file__).resolve().parent.parent
        / "data"
        / "salary_benchmarks"
        / "demo_de.csv"
    )
