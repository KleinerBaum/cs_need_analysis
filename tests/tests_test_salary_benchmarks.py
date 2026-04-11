from pathlib import Path

from salary.benchmarks import (
    build_benchmark_index,
    load_benchmark_csv,
    lookup_benchmark,
    resolve_salary_benchmark_path,
)


def test_load_benchmark_csv_parses_demo_dataset() -> None:
    rows = load_benchmark_csv(Path("data/salary_benchmarks/demo_de.csv"))

    assert len(rows) >= 8
    assert rows[0].dataset_version == "demo_v1"
    assert rows[0].country_code == "DE"


def test_lookup_benchmark_returns_latest_year_when_year_missing() -> None:
    rows = load_benchmark_csv(Path("data/salary_benchmarks/demo_de.csv"))
    index = build_benchmark_index(rows)

    row = lookup_benchmark(
        index,
        occupation_id="title::software-engineer",
        region_id="DE",
    )

    assert row is not None
    assert row.year == 2025
    assert row.p50 == 71000


def test_lookup_benchmark_exact_year_match() -> None:
    rows = load_benchmark_csv(Path("data/salary_benchmarks/demo_de.csv"))
    index = build_benchmark_index(rows)

    row = lookup_benchmark(
        index,
        occupation_id="title::software-engineer",
        region_id="DE",
        year=2024,
    )

    assert row is not None
    assert row.year == 2024
    assert row.p50 == 68000


def test_lookup_benchmark_falls_back_to_de_region() -> None:
    rows = load_benchmark_csv(Path("data/salary_benchmarks/demo_de.csv"))
    index = build_benchmark_index(rows)

    row = lookup_benchmark(
        index,
        occupation_id="title::sales-manager",
        region_id="DE-HH",
    )

    assert row is not None
    assert row.region_id == "DE"
    assert row.occupation_id == "title::sales-manager"


def test_lookup_benchmark_falls_back_to_any_occupation() -> None:
    rows = load_benchmark_csv(Path("data/salary_benchmarks/demo_de.csv"))
    index = build_benchmark_index(rows)

    row = lookup_benchmark(
        index,
        occupation_id="title::unknown-role",
        region_id="DE-BY",
    )

    assert row is not None
    assert row.occupation_id == "ANY"
    assert row.region_id == "DE"


def test_lookup_benchmark_returns_none_for_missing_year_in_fallback_chain() -> None:
    rows = load_benchmark_csv(Path("data/salary_benchmarks/demo_de.csv"))
    index = build_benchmark_index(rows)

    row = lookup_benchmark(
        index,
        occupation_id="title::unknown-role",
        region_id="DE-BY",
        year=2017,
    )

    assert row is None


def test_resolve_salary_benchmark_path_env_override(monkeypatch) -> None:
    monkeypatch.setenv("SALARY_BENCHMARK_PATH", "/tmp/bench.csv")

    resolved = resolve_salary_benchmark_path()

    assert resolved == Path("/tmp/bench.csv")
