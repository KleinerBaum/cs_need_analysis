from __future__ import annotations

import csv
from pathlib import Path

from scripts.run_quality_evals import (
    evaluate_fixture_row,
    evaluate_run,
    load_fixture_rows,
    main,
    summarize_results,
)


def test_evaluate_run_returns_core_metrics() -> None:
    summary = evaluate_run(
        [
            {
                "correct": 1,
                "hallucinated": False,
                "latency_ms": 100,
                "cost_usd": 0.01,
                "esco_top1": 1,
            },
            {
                "correct": 0,
                "hallucinated": True,
                "latency_ms": 300,
                "cost_usd": 0.03,
                "esco_top1": 0,
            },
        ]
    )

    assert summary == {
        "accuracy": 0.5,
        "hallucination_rate": 0.5,
        "avg_latency_ms": 200,
        "avg_cost_usd": 0.02,
        "esco_top1": 0.5,
    }


def test_quality_fixture_rows_pass_thresholds() -> None:
    rows = load_fixture_rows(Path("evals"))
    results = [evaluate_fixture_row(row) for row in rows]
    summaries = summarize_results(results)

    assert len(rows) >= 6
    assert {summary["scope"] for summary in summaries} == {
        "overall",
        "extraction",
        "esco_mapping",
        "retrieval_faithfulness",
    }
    assert all(summary["passed_thresholds"] for summary in summaries)


def test_quality_eval_runner_writes_csv_and_json(tmp_path: Path) -> None:
    csv_path = tmp_path / "summary.csv"
    json_path = tmp_path / "summary.json"

    exit_code = main(
        [
            "--fixtures",
            "evals",
            "--output",
            str(csv_path),
            "--json-output",
            str(json_path),
            "--enforce-thresholds",
            "--json-only",
        ]
    )

    assert exit_code == 0
    assert json_path.exists()
    with csv_path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["scope"] == "overall"
    assert rows[0]["passed_thresholds"] == "True"


def test_hallucinated_extraction_row_fails() -> None:
    result = evaluate_fixture_row(
        {
            "id": "bad_extraction",
            "task": "extraction",
            "expected": {"job_title": "Data Analyst", "must_have_skills": ["SQL"]},
            "candidate": {
                "job_title": "Data Analyst",
                "must_have_skills": ["SQL", "SAP"],
            },
            "no_extra_fields": ["must_have_skills"],
            "prohibited_terms": ["SAP"],
            "metrics": {"latency_ms": 10, "cost_usd": 0.0},
        }
    )

    assert result.correct == 1.0
    assert result.hallucinated is True
    assert "must_have_skills_extra_items" in result.failure_reasons
