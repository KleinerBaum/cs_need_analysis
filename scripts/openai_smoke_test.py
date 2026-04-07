"""Smoke-Test für die OpenAI-Integration (extract_job_ad).

Der Test trennt klar zwischen:
- configured_mode: statische Testkonfiguration
- effective_request_kwargs: tatsächlich gesendete/simulierte Request-Parameter
- actual_response_metadata: echte SDK-Antwortmetadaten

Keine Secrets werden ausgegeben.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from dataclasses import asdict, dataclass
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SAMPLE_JOB_TEXT = (
    "Wir suchen eine:n Python Data Analyst (m/w/d) in Berlin. "
    "Aufgaben: KPI-Reporting, SQL-Abfragen, Dashboarding in Power BI. "
    "Must-have: Python, SQL, Kommunikation mit Stakeholdern. "
    "Nice-to-have: Erfahrung mit Recruiting-Analytics."
)


@dataclass(frozen=True)
class SmokeMode:
    """Defines one smoke-test execution profile."""

    name: str
    model: str
    reasoning_effort: str
    verbosity: str
    temperature: float | None


SMOKE_MODES: dict[str, SmokeMode] = {
    "gpt-5.4-nano": SmokeMode(
        name="gpt-5.4-nano",
        model="gpt-5.4-nano",
        reasoning_effort="none",
        verbosity="low",
        temperature=0.0,
    ),
    "gpt-5-nano": SmokeMode(
        name="gpt-5-nano",
        model="gpt-5-nano",
        reasoning_effort="low",
        verbosity="low",
        temperature=0.7,
    ),
}


@dataclass(frozen=True)
class ModeResult:
    """Serializable outcome for one smoke mode."""

    mode: str
    configured_mode: dict[str, Any]
    effective_request_kwargs: dict[str, Any]
    actual_response_metadata: dict[str, Any]
    fields_preview: dict[str, Any] | None


def _usage_to_dict(usage: Any) -> dict[str, Any] | None:
    if usage is None:
        return None
    if hasattr(usage, "model_dump"):
        return usage.model_dump()  # type: ignore[no-any-return]
    if isinstance(usage, dict):
        return usage
    return {"repr": repr(usage)}


def _looks_like_api_key(text: str | None) -> bool:
    return bool(text and text.strip().startswith("sk-"))


def _has_api_key() -> bool:
    return _looks_like_api_key(os.getenv("OPENAI_API_KEY"))


def run_mode(mode: SmokeMode, *, dry_run: bool) -> ModeResult:
    """Execute one API smoke run and return a safe report payload."""
    from openai import OpenAI
    from llm_client import build_extract_job_ad_messages, build_responses_request_kwargs
    from schemas import JobAdExtract

    request_kwargs = build_responses_request_kwargs(
        model=mode.model,
        store=False,
        maybe_temperature=mode.temperature,
        reasoning_effort=mode.reasoning_effort,
        verbosity=mode.verbosity,
    )

    if dry_run:
        return ModeResult(
            mode=mode.name,
            configured_mode=asdict(mode),
            effective_request_kwargs=request_kwargs,
            actual_response_metadata={
                "parse_status": "dry_run",
                "response_model_id": None,
                "usage": None,
            },
            fields_preview=None,
        )

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    if not hasattr(client, "responses") or not hasattr(client.responses, "parse"):
        raise RuntimeError("OpenAI SDK does not provide responses.parse(...).")

    messages = build_extract_job_ad_messages(SAMPLE_JOB_TEXT, language="de")
    response = client.responses.parse(
        input=messages,
        text_format=JobAdExtract,
        **request_kwargs,
    )

    parsed = response.output_parsed
    parse_status = "ok" if parsed is not None else "empty"

    return ModeResult(
        mode=mode.name,
        configured_mode=asdict(mode),
        effective_request_kwargs=request_kwargs,
        actual_response_metadata={
            "response_id": getattr(response, "id", None),
            "response_model_id": getattr(response, "model", None),
            "usage": _usage_to_dict(getattr(response, "usage", None)),
            "parse_status": parse_status,
        },
        fields_preview={
            "job_title": parsed.job_title,
            "location_city": parsed.location_city,
            "must_have_skills_count": len(parsed.must_have_skills),
        }
        if parsed is not None
        else None,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run OpenAI extract_job_ad smoke test")
    parser.add_argument(
        "--mode",
        choices=["all", *SMOKE_MODES.keys()],
        default="all",
        help="Smoke mode to run (default: all)",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop after the first failing mode and return non-zero.",
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Print only JSON output (CI-friendly).",
    )
    parser.add_argument(
        "--ci-dry-run-if-no-key",
        action="store_true",
        help=(
            "If no OPENAI_API_KEY is available, only validate request kwargs "
            "without performing API calls."
        ),
    )
    return parser.parse_args()


def _result_failed(result: ModeResult) -> bool:
    return result.actual_response_metadata.get("parse_status") == "error"


def main() -> None:
    from llm_client import build_extract_job_ad_messages, build_responses_request_kwargs

    args = parse_args()
    selected_modes = (
        list(SMOKE_MODES.values()) if args.mode == "all" else [SMOKE_MODES[args.mode]]
    )

    api_key_available = _has_api_key()
    dry_run = args.ci_dry_run_if_no_key and not api_key_available

    summary: list[dict[str, Any]] = []
    had_failure = False

    for mode in selected_modes:
        try:
            result = run_mode(mode, dry_run=dry_run)
        except Exception as exc:  # noqa: BLE001
            had_failure = True
            error_result = ModeResult(
                mode=mode.name,
                configured_mode=asdict(mode),
                effective_request_kwargs=build_responses_request_kwargs(
                    model=mode.model,
                    store=False,
                    maybe_temperature=mode.temperature,
                    reasoning_effort=mode.reasoning_effort,
                    verbosity=mode.verbosity,
                ),
                actual_response_metadata={
                    "parse_status": "error",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "response_model_id": None,
                    "usage": None,
                },
                fields_preview=None,
            )
            summary.append(asdict(error_result))
            if args.fail_fast:
                break
            continue

        if _result_failed(result):
            had_failure = True
            if args.fail_fast:
                summary.append(asdict(result))
                break

        summary.append(asdict(result))

    report = {
        "sample_text_chars": len(SAMPLE_JOB_TEXT),
        "api_key_available": api_key_available,
        "dry_run": dry_run,
        "notes": [
            "Configured mode values are explicit test inputs.",
            "Effective request kwargs show capability-filtered request payload.",
            "Actual response metadata comes from OpenAI SDK response objects.",
            "st.secrets/openai secrets can override environment variables in app runtime; env mutation alone may not reflect effective app config.",
        ],
        "modes": summary,
        "message_template_preview": build_extract_job_ad_messages(
            "<sample>",
            language="de",
        ),
    }

    if args.json_only:
        print(json.dumps(report, ensure_ascii=False))
    else:
        print(
            f"Smoke test completed: modes={len(summary)}, failures={'yes' if had_failure else 'no'}, dry_run={dry_run}"
        )
        print(json.dumps(report, indent=2, ensure_ascii=False))

    if had_failure:
        sys.exit(1)


if __name__ == "__main__":
    main()
