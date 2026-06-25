#!/usr/bin/env python
"""Run deterministic quality evals for extraction, ESCO, and retrieval outputs."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sys
from statistics import mean
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


QUALITY_THRESHOLDS: dict[str, dict[str, float]] = {
    "overall": {
        "accuracy_min": 0.90,
        "hallucination_rate_max": 0.02,
        "avg_latency_ms_max": 4_000.0,
        "avg_cost_usd_max": 0.01,
        "esco_top1_min": 0.95,
    },
    "extraction": {
        "accuracy_min": 0.90,
        "hallucination_rate_max": 0.0,
        "avg_latency_ms_max": 4_000.0,
        "avg_cost_usd_max": 0.01,
    },
    "esco_mapping": {
        "accuracy_min": 0.95,
        "hallucination_rate_max": 0.0,
        "esco_top1_min": 1.0,
        "avg_latency_ms_max": 1_500.0,
    },
    "retrieval_faithfulness": {
        "accuracy_min": 0.90,
        "hallucination_rate_max": 0.0,
        "avg_latency_ms_max": 4_000.0,
        "avg_cost_usd_max": 0.01,
    },
}


@dataclass(frozen=True)
class EvalResult:
    id: str
    task: str
    correct: float
    hallucinated: bool
    latency_ms: float
    cost_usd: float
    esco_top1: float
    failure_reasons: tuple[str, ...] = ()


def evaluate_run(rows: list[Mapping[str, float | int | bool]]) -> dict[str, float]:
    """Aggregate eval rows using the stable quality metrics."""

    if not rows:
        return {
            "accuracy": 0.0,
            "hallucination_rate": 0.0,
            "avg_latency_ms": 0.0,
            "avg_cost_usd": 0.0,
            "esco_top1": 0.0,
        }
    return {
        "accuracy": round(mean(float(r["correct"]) for r in rows), 4),
        "hallucination_rate": round(mean(bool(r["hallucinated"]) for r in rows), 4),
        "avg_latency_ms": round(mean(float(r["latency_ms"]) for r in rows), 2),
        "avg_cost_usd": round(mean(float(r["cost_usd"]) for r in rows), 4),
        "esco_top1": round(mean(float(r["esco_top1"]) for r in rows), 4),
    }


def load_fixture_rows(fixtures_path: Path) -> list[dict[str, Any]]:
    """Load JSONL fixture rows from one file or all JSONL files in a directory."""

    paths = (
        [fixtures_path]
        if fixtures_path.is_file()
        else sorted(path for path in fixtures_path.glob("*.jsonl") if path.is_file())
    )
    rows: list[dict[str, Any]] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSONL row {path}:{line_number}") from exc
                if not isinstance(row, dict):
                    raise ValueError(f"Fixture row must be an object: {path}:{line_number}")
                resolved_path = path.resolve()
                try:
                    fixture_path = str(resolved_path.relative_to(ROOT))
                except ValueError:
                    fixture_path = str(resolved_path)
                row.setdefault("_fixture_path", fixture_path)
                row.setdefault("_line_number", line_number)
                rows.append(row)
    return rows


def evaluate_fixture_row(row: Mapping[str, Any]) -> EvalResult:
    task = str(row.get("task") or "").strip()
    if task == "extraction":
        correct, hallucinated, reasons = _evaluate_extraction(row)
        esco_top1 = 1.0
    elif task == "esco_mapping":
        correct, hallucinated, reasons, esco_top1 = _evaluate_esco_mapping(row)
    elif task == "retrieval_faithfulness":
        correct, hallucinated, reasons = _evaluate_retrieval_faithfulness(row)
        esco_top1 = 1.0
    else:
        raise ValueError(f"Unsupported eval task {task!r} in row {row.get('id')!r}")

    metrics = _as_mapping(row.get("metrics"))
    return EvalResult(
        id=str(row.get("id") or ""),
        task=task,
        correct=round(correct, 4),
        hallucinated=hallucinated,
        latency_ms=_metric_float(metrics, "latency_ms"),
        cost_usd=_cost_usd(metrics),
        esco_top1=round(esco_top1, 4),
        failure_reasons=tuple(reasons),
    )


def summarize_results(results: list[EvalResult]) -> list[dict[str, Any]]:
    scopes = ["overall", *sorted({result.task for result in results})]
    summaries: list[dict[str, Any]] = []
    for scope in scopes:
        scoped_results = (
            results if scope == "overall" else [r for r in results if r.task == scope]
        )
        metric_rows = [
            {
                "correct": result.correct,
                "hallucinated": result.hallucinated,
                "latency_ms": result.latency_ms,
                "cost_usd": result.cost_usd,
                "esco_top1": result.esco_top1,
            }
            for result in scoped_results
        ]
        summary = evaluate_run(metric_rows)
        failures = _threshold_failures(scope, summary)
        summaries.append(
            {
                "scope": scope,
                "rows": len(scoped_results),
                **summary,
                "passed_thresholds": not failures,
                "threshold_failures": "; ".join(failures),
            }
        )
    return summaries


def write_summary_csv(path: Path, summaries: list[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "scope",
        "rows",
        "accuracy",
        "hallucination_rate",
        "avg_latency_ms",
        "avg_cost_usd",
        "esco_top1",
        "passed_thresholds",
        "threshold_failures",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summaries)


def _evaluate_extraction(row: Mapping[str, Any]) -> tuple[float, bool, list[str]]:
    expected = _as_mapping(row.get("expected"))
    candidate = _candidate_payload(row)
    if not expected:
        return 0.0, True, ["missing_expected"]
    if not candidate:
        return 0.0, True, ["missing_candidate"]

    field_scores: list[float] = []
    reasons: list[str] = []
    for field_name, expected_value in expected.items():
        actual_value = candidate.get(field_name)
        score = _field_match_score(expected_value, actual_value)
        field_scores.append(score)
        if score < 1.0:
            reasons.append(f"{field_name}_mismatch")

    hallucinated = _contains_prohibited_terms(row, candidate)
    for field_name in row.get("no_extra_fields", []):
        if not isinstance(field_name, str):
            continue
        extras = _unexpected_list_items(candidate.get(field_name), expected.get(field_name))
        if extras:
            hallucinated = True
            reasons.append(f"{field_name}_extra_items")
    if hallucinated and not any(reason.endswith("prohibited_term") for reason in reasons):
        reasons.append("hallucinated_content")
    return mean(field_scores), hallucinated, reasons


def _evaluate_esco_mapping(
    row: Mapping[str, Any],
) -> tuple[float, bool, list[str], float]:
    expected = _as_mapping(row.get("expected"))
    candidate = _candidate_payload(row)
    expected_uri = str(expected.get("top_uri") or expected.get("uri") or "").strip()
    allowed_uris = {
        str(uri).strip()
        for uri in expected.get("allowed_uris", [expected_uri])
        if str(uri).strip()
    }
    top_uri = _top_candidate_uri(candidate)
    esco_top1 = 1.0 if expected_uri and top_uri == expected_uri else 0.0
    hallucinated = not top_uri or (bool(allowed_uris) and top_uri not in allowed_uris)
    reasons: list[str] = []
    if esco_top1 < 1.0:
        reasons.append("esco_top1_mismatch")
    if hallucinated:
        reasons.append("esco_uri_not_allowed")
    return esco_top1, hallucinated, reasons, esco_top1


def _evaluate_retrieval_faithfulness(
    row: Mapping[str, Any],
) -> tuple[float, bool, list[str]]:
    expected = _as_mapping(row.get("expected"))
    candidate = _candidate_payload(row)
    answer_text = str(candidate.get("answer") or "")
    expected_claims = [str(item) for item in expected.get("supported_claims", [])]
    if not expected_claims:
        return 0.0, True, ["missing_supported_claims"]

    answer_normalized = _normalize(answer_text)
    covered_claims = [
        claim for claim in expected_claims if _normalize(claim) in answer_normalized
    ]
    score = len(covered_claims) / len(expected_claims)
    reasons: list[str] = []
    if score < 1.0:
        reasons.append("missing_supported_claim")

    context_ids = _context_ids(row)
    cited_context_ids = {
        str(item).strip()
        for item in candidate.get("cited_context_ids", [])
        if str(item).strip()
    }
    unsupported_citations = cited_context_ids - context_ids
    unsupported_claims = [
        str(item).strip()
        for item in candidate.get("unsupported_claims", [])
        if str(item).strip()
    ]
    hallucinated = bool(
        unsupported_citations
        or unsupported_claims
        or _contains_prohibited_terms(row, candidate)
    )
    if unsupported_citations:
        reasons.append("unsupported_citation")
    if unsupported_claims:
        reasons.append("unsupported_claim")
    if hallucinated and not reasons:
        reasons.append("hallucinated_content")
    return score, hallucinated, reasons


def _threshold_failures(scope: str, summary: Mapping[str, Any]) -> list[str]:
    thresholds = QUALITY_THRESHOLDS.get(scope, {})
    failures: list[str] = []
    for key, threshold in thresholds.items():
        if key.endswith("_min"):
            metric = key.removesuffix("_min")
            if float(summary.get(metric, 0.0)) < threshold:
                failures.append(f"{metric}<{threshold}")
        elif key.endswith("_max"):
            metric = key.removesuffix("_max")
            if float(summary.get(metric, 0.0)) > threshold:
                failures.append(f"{metric}>{threshold}")
    return failures


def _candidate_payload(row: Mapping[str, Any]) -> Mapping[str, Any]:
    for key in ("candidate", "actual", "prediction"):
        payload = row.get(key)
        if isinstance(payload, Mapping):
            return payload
    return {}


def _field_match_score(expected: Any, actual: Any) -> float:
    if isinstance(expected, list):
        expected_values = {_normalize(item) for item in expected if _normalize(item)}
        actual_values = {_normalize(item) for item in _as_list(actual) if _normalize(item)}
        if not expected_values:
            return 1.0
        return len(expected_values & actual_values) / len(expected_values)
    if expected is None:
        return 1.0 if actual in (None, "", []) else 0.0
    return 1.0 if _normalize(expected) == _normalize(actual) else 0.0


def _unexpected_list_items(actual: Any, expected: Any) -> set[str]:
    expected_values = {_normalize(item) for item in _as_list(expected) if _normalize(item)}
    actual_values = {_normalize(item) for item in _as_list(actual) if _normalize(item)}
    return actual_values - expected_values


def _contains_prohibited_terms(row: Mapping[str, Any], candidate: Mapping[str, Any]) -> bool:
    candidate_text = _normalize(json.dumps(candidate, ensure_ascii=False, sort_keys=True))
    for term in row.get("prohibited_terms", []):
        if _normalize(term) and _normalize(term) in candidate_text:
            return True
    return False


def _top_candidate_uri(candidate: Mapping[str, Any]) -> str:
    candidates = candidate.get("candidates")
    if isinstance(candidates, list) and candidates:
        first = candidates[0]
        if isinstance(first, Mapping):
            return str(first.get("uri") or first.get("conceptUri") or "").strip()
    return str(candidate.get("uri") or candidate.get("conceptUri") or "").strip()


def _context_ids(row: Mapping[str, Any]) -> set[str]:
    input_payload = _as_mapping(row.get("input"))
    contexts = input_payload.get("contexts", [])
    context_ids: set[str] = set()
    if isinstance(contexts, list):
        for context in contexts:
            if isinstance(context, Mapping):
                context_id = str(context.get("id") or "").strip()
                if context_id:
                    context_ids.add(context_id)
    return context_ids


def _metric_float(metrics: Mapping[str, Any], key: str) -> float:
    value = metrics.get(key, 0.0)
    return float(value) if isinstance(value, (int, float)) else 0.0


def _cost_usd(metrics: Mapping[str, Any]) -> float:
    explicit_cost = metrics.get("cost_usd")
    if isinstance(explicit_cost, (int, float)):
        return float(explicit_cost)
    input_tokens = _metric_float(metrics, "input_tokens")
    output_tokens = _metric_float(metrics, "output_tokens")
    input_rate = _metric_float(metrics, "input_token_cost_per_1m_usd")
    output_rate = _metric_float(metrics, "output_token_cost_per_1m_usd")
    return ((input_tokens * input_rate) + (output_tokens * output_rate)) / 1_000_000


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]


def _normalize(value: Any) -> str:
    return " ".join(str(value or "").casefold().replace(":", " ").split())


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=ROOT / "evals",
        help="JSONL fixture file or directory containing JSONL fixture files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "reports" / "evals" / "summary.csv",
        help="CSV summary output path.",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=None,
        help="Optional JSON detail output path.",
    )
    parser.add_argument(
        "--enforce-thresholds",
        action="store_true",
        help="Exit non-zero when any configured threshold fails.",
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Print only JSON report to stdout.",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    fixture_rows = load_fixture_rows(args.fixtures)
    results = [evaluate_fixture_row(row) for row in fixture_rows]
    summaries = summarize_results(results)
    write_summary_csv(args.output, summaries)

    report = {
        "fixture_count": len(fixture_rows),
        "thresholds": QUALITY_THRESHOLDS,
        "summary_csv": str(args.output),
        "summaries": summaries,
        "results": [asdict(result) for result in results],
    }
    if args.json_output is not None:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    if args.json_only:
        print(json.dumps(report, ensure_ascii=False))
    else:
        overall = next(item for item in summaries if item["scope"] == "overall")
        print(
            "Quality evals completed: "
            f"fixtures={len(fixture_rows)}, "
            f"accuracy={overall['accuracy']}, "
            f"hallucination_rate={overall['hallucination_rate']}, "
            f"passed={overall['passed_thresholds']}"
        )
        print(f"CSV summary: {args.output}")

    failed = [summary for summary in summaries if not summary["passed_thresholds"]]
    return 1 if args.enforce_thresholds and failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
