"""Kleiner Smoke-Test für die OpenAI-Integration (extract_job_ad).

Führt zwei vordefinierte Modi aus und zeigt:
- aufgelöstes Modell
- gesendete Request-Parameter (sanitisiert)
- Response-Metadaten (Usage, Parse-Status)

Keine Secrets werden ausgegeben.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from typing import Any

from llm_client import (
    build_extract_job_ad_messages,
    build_responses_request_kwargs,
    extract_job_ad,
)

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


def _usage_to_dict(usage: Any) -> dict[str, Any] | None:
    if usage is None:
        return None
    if hasattr(usage, "model_dump"):
        return usage.model_dump()  # type: ignore[no-any-return]
    if isinstance(usage, dict):
        return usage
    return {"repr": repr(usage)}


def _set_runtime_env(mode: SmokeMode) -> dict[str, str | None]:
    previous: dict[str, str | None] = {
        "REASONING_EFFORT": os.getenv("REASONING_EFFORT"),
        "VERBOSITY": os.getenv("VERBOSITY"),
    }
    os.environ["REASONING_EFFORT"] = mode.reasoning_effort
    os.environ["VERBOSITY"] = mode.verbosity
    return previous


def _restore_runtime_env(previous: dict[str, str | None]) -> None:
    for key, value in previous.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def run_mode(mode: SmokeMode) -> dict[str, Any]:
    """Execute one API smoke run and return a safe report payload."""

    previous = _set_runtime_env(mode)
    try:
        request_kwargs = build_responses_request_kwargs(
            model=mode.model,
            store=False,
            maybe_temperature=mode.temperature,
            reasoning_effort=mode.reasoning_effort,
            verbosity=mode.verbosity,
        )

        parsed, usage = extract_job_ad(
            SAMPLE_JOB_TEXT,
            model=mode.model,
            store=False,
            temperature=mode.temperature,
        )

        return {
            "mode": mode.name,
            "resolved_model": mode.model,
            "request_kwargs": request_kwargs,
            "response_model": type(parsed).__name__,
            "parse_status": "ok" if parsed is not None else "empty",
            "usage": _usage_to_dict(usage),
            "fields_preview": {
                "job_title": parsed.job_title,
                "location_city": parsed.location_city,
                "must_have_skills_count": len(parsed.must_have_skills),
            },
        }
    except Exception as exc:  # noqa: BLE001 - smoke-report should surface raw error
        return {
            "mode": mode.name,
            "resolved_model": mode.model,
            "request_kwargs": request_kwargs,
            "parse_status": "error",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    finally:
        _restore_runtime_env(previous)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run OpenAI extract_job_ad smoke test")
    parser.add_argument(
        "--mode",
        choices=["all", *SMOKE_MODES.keys()],
        default="all",
        help="Smoke mode to run (default: all)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    selected_modes = (
        list(SMOKE_MODES.values()) if args.mode == "all" else [SMOKE_MODES[args.mode]]
    )

    report = {
        "sample_text_chars": len(SAMPLE_JOB_TEXT),
        "modes": [run_mode(mode) for mode in selected_modes],
        "message_template_preview": build_extract_job_ad_messages(
            "<sample>",
            language="de",
        ),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
