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
import time
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

REQUEST_OPTIONAL_FIELDS = ("temperature", "reasoning", "text.verbosity")
CONFIGURED_MODEL_SLOTS = (
    ("OPENAI_MODEL", "openai_model"),
    ("DEFAULT_MODEL", "default_model"),
    ("LIGHTWEIGHT_MODEL", "lightweight_model"),
    ("MEDIUM_REASONING_MODEL", "medium_reasoning_model"),
    ("HIGH_REASONING_MODEL", "high_reasoning_model"),
)


@dataclass(frozen=True)
class SmokeMode:
    """Defines one smoke-test execution profile."""

    name: str
    model: str
    reasoning_effort: str
    verbosity: str
    temperature: float | None
    call_api: bool = True


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
    "invalid-reasoning-effort": SmokeMode(
        name="invalid-reasoning-effort",
        model="gpt-5.4-nano",
        reasoning_effort="totally-invalid",
        verbosity="low",
        temperature=0.0,
        call_api=False,
    ),
    "unsupported-temperature": SmokeMode(
        name="unsupported-temperature",
        model="gpt-5-nano",
        reasoning_effort="low",
        verbosity="low",
        temperature=0.7,
        call_api=False,
    ),
}


@dataclass(frozen=True)
class ModeResult:
    """Serializable outcome for one smoke mode."""

    mode: str
    configured_mode: dict[str, Any]
    effective_request_kwargs: dict[str, Any]
    request_shape_metadata: dict[str, Any]
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


def _resolved_api_key() -> str | None:
    from settings_openai import load_openai_settings

    settings = load_openai_settings()
    if _looks_like_api_key(settings.openai_api_key):
        return settings.openai_api_key
    return None


def _has_api_key() -> bool:
    return (
        _looks_like_api_key(os.getenv("OPENAI_API_KEY"))
        or _resolved_api_key() is not None
    )


def _response_request_id(response: Any) -> str | None:
    for attr in ("_request_id", "request_id", "id"):
        value = getattr(response, attr, None)
        if isinstance(value, str) and value:
            return value
    return None


def _safe_model_name(model: str | None) -> str | None:
    candidate = (model or "").strip()
    if not candidate:
        return None
    if candidate.startswith("ft:"):
        return "fine_tuned_model"
    return candidate


def build_request_shape_metadata(
    request_kwargs: dict[str, Any],
    *,
    endpoint: str = "responses.parse",
) -> dict[str, Any]:
    """Return non-sensitive metadata about request fields and optional params."""

    text_payload = request_kwargs.get("text")
    has_text_verbosity = isinstance(text_payload, dict) and "verbosity" in text_payload
    optional_fields = {
        "temperature": "temperature" in request_kwargs,
        "reasoning": "reasoning" in request_kwargs,
        "text.verbosity": has_text_verbosity,
    }
    model = request_kwargs.get("model")

    return {
        "endpoint": endpoint,
        "model": _safe_model_name(model if isinstance(model, str) else None),
        "request_field_names": sorted(request_kwargs),
        "optional_request_fields": optional_fields,
        "included_optional_fields": [
            field for field in REQUEST_OPTIONAL_FIELDS if optional_fields[field]
        ],
        "omitted_optional_fields": [
            field for field in REQUEST_OPTIONAL_FIELDS if not optional_fields[field]
        ],
        "has_store": "store" in request_kwargs,
        "has_max_output_tokens": "max_output_tokens" in request_kwargs,
        "has_previous_response_id": "previous_response_id" in request_kwargs,
    }


def build_configured_model_request_shapes(
    *,
    maybe_temperature: float | None = 0.2,
) -> list[dict[str, Any]]:
    """Build offline request-shape metadata for configured model slots."""

    from llm_client import build_responses_request_kwargs
    from settings_openai import load_openai_settings

    settings = load_openai_settings()
    shapes: list[dict[str, Any]] = []
    for setting_key, attr_name in CONFIGURED_MODEL_SLOTS:
        model = str(getattr(settings, attr_name, "") or "").strip()
        if not model:
            continue
        request_kwargs = build_responses_request_kwargs(
            model=model,
            store=False,
            maybe_temperature=maybe_temperature,
            reasoning_effort=settings.reasoning_effort,
            verbosity=settings.verbosity,
        )
        shapes.append(
            {
                "slot": setting_key,
                "model": _safe_model_name(model),
                "configured_request_inputs": {
                    "temperature": maybe_temperature,
                    "reasoning_effort": settings.reasoning_effort,
                    "verbosity": settings.verbosity,
                },
                "request_shape_metadata": build_request_shape_metadata(request_kwargs),
            }
        )
    return shapes


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

    if dry_run or not mode.call_api:
        return ModeResult(
            mode=mode.name,
            configured_mode=asdict(mode),
            effective_request_kwargs=request_kwargs,
            request_shape_metadata=build_request_shape_metadata(request_kwargs),
            actual_response_metadata={
                "parse_status": "dry_run" if dry_run else "simulated",
                "request_id": None,
                "response_id": None,
                "response_model_id": None,
                "latency_ms": None,
                "usage": None,
            },
            fields_preview=None,
        )

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY") or _resolved_api_key())
    if not hasattr(client, "responses") or not hasattr(client.responses, "parse"):
        raise RuntimeError("OpenAI SDK does not provide responses.parse(...).")

    messages = build_extract_job_ad_messages(SAMPLE_JOB_TEXT, language="de")
    started = time.perf_counter()
    response = client.responses.parse(
        input=messages,
        text_format=JobAdExtract,
        **request_kwargs,
    )
    latency_ms = int((time.perf_counter() - started) * 1000)

    parsed = response.output_parsed
    parse_status = "ok" if parsed is not None else "empty"

    return ModeResult(
        mode=mode.name,
        configured_mode=asdict(mode),
        effective_request_kwargs=request_kwargs,
        request_shape_metadata=build_request_shape_metadata(request_kwargs),
        actual_response_metadata={
            "request_id": _response_request_id(response),
            "response_id": getattr(response, "id", None),
            "response_model_id": getattr(response, "model", None),
            "latency_ms": latency_ms,
            "usage": _usage_to_dict(getattr(response, "usage", None)),
            "parse_status": parse_status,
        },
        fields_preview=(
            {
                "job_title": parsed.job_title,
                "location_city": parsed.location_city,
                "must_have_skills_count": len(parsed.must_have_skills),
            }
            if parsed is not None
            else None
        ),
    )


def run_error_simulation(mode: str) -> dict[str, Any]:
    """Simulate timeout/connection mapping without network traffic."""
    import httpx

    from llm_client import _error_from_openai_exception
    from openai import APIConnectionError

    if mode == "timeout":
        exc: Exception = TimeoutError("simulated timeout")
    elif mode == "connection":
        request = httpx.Request("POST", "https://api.openai.com/v1/responses")
        exc = APIConnectionError(
            request=request,
            message="simulated connection issue",
        )
    else:
        raise ValueError(f"Unsupported simulation mode: {mode}")

    mapped = _error_from_openai_exception(exc, endpoint="responses.parse")
    return {
        "parse_status": "simulated_error",
        "simulation_mode": mode,
        "mapped_error_code": mapped.error_code,
        "mapped_ui_message": mapped.ui_message,
        "mapped_debug_detail": mapped.debug_detail,
    }


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
        "--dry-run",
        action="store_true",
        help="Validate request kwargs without performing API calls, even if a key is available.",
    )
    parser.add_argument(
        "--ci-dry-run-if-no-key",
        action="store_true",
        help=(
            "If no OPENAI_API_KEY is available, only validate request kwargs "
            "without performing API calls."
        ),
    )
    parser.add_argument(
        "--simulate-error",
        choices=["none", "timeout", "connection"],
        default="none",
        help="Simulate mapped OpenAI timeout/connection handling without API call.",
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
    dry_run = args.dry_run or (args.ci_dry_run_if_no_key and not api_key_available)

    summary: list[dict[str, Any]] = []
    had_failure = False

    for mode in selected_modes:
        try:
            result = run_mode(mode, dry_run=dry_run)
        except Exception as exc:  # noqa: BLE001
            had_failure = True
            request_kwargs = build_responses_request_kwargs(
                model=mode.model,
                store=False,
                maybe_temperature=mode.temperature,
                reasoning_effort=mode.reasoning_effort,
                verbosity=mode.verbosity,
            )
            error_result = ModeResult(
                mode=mode.name,
                configured_mode=asdict(mode),
                effective_request_kwargs=request_kwargs,
                request_shape_metadata=build_request_shape_metadata(request_kwargs),
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

    simulated_error: dict[str, Any] | None = None
    if args.simulate_error != "none":
        try:
            simulated_error = run_error_simulation(args.simulate_error)
        except Exception as exc:  # noqa: BLE001
            had_failure = True
            simulated_error = {
                "parse_status": "error",
                "simulation_mode": args.simulate_error,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }

    report = {
        "sample_text_chars": len(SAMPLE_JOB_TEXT),
        "api_key_available": api_key_available,
        "dry_run": dry_run,
        "notes": [
            "Configured mode values are explicit test inputs.",
            "Effective request kwargs show capability-filtered request payload.",
            "Request-shape metadata lists optional fields included or omitted after capability gating.",
            "Actual response metadata comes from OpenAI SDK response objects.",
            "st.secrets/openai secrets can override environment variables in app runtime; env mutation alone may not reflect effective app config.",
        ],
        "modes": summary,
        "configured_model_request_shapes": build_configured_model_request_shapes(),
        "simulated_error": simulated_error,
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
