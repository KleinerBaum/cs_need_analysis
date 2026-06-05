#!/usr/bin/env python
"""Smoke-check ESCO release/runtime combinations without logging sensitive data."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from constants import (
    DEFAULT_ESCO_INDEX_STORAGE_PATH,
    ESCO_API_MODES,
    ESCO_DATA_SOURCE_MODES,
    ESCO_RELEASE_LANE_SELECTED_VERSION,
    ESCO_RELEASE_LANES,
    SSKey,
)


def _extract_results(payload: dict[str, Any]) -> list[dict[str, Any]]:
    embedded = payload.get("_embedded")
    if isinstance(embedded, dict):
        for value in embedded.values():
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    for key in ("results", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _first_uri(payload: dict[str, Any]) -> str:
    for item in _extract_results(payload):
        uri = str(item.get("uri") or "").strip()
        if uri:
            return uri
    return ""


def _safe_count(payload: dict[str, Any]) -> int:
    results = _extract_results(payload)
    if results:
        return len(results)
    total = payload.get("total")
    return int(total) if isinstance(total, int) else 0


def _check_combo(
    *,
    release_lane: str,
    api_mode: str,
    data_source_mode: str,
    dry_run_if_unavailable: bool,
) -> dict[str, Any]:
    from esco_client import EscoClient, EscoClientError

    selected_version = ESCO_RELEASE_LANE_SELECTED_VERSION[release_lane]
    session_state: dict[str, object] = {
        SSKey.ESCO_CONFIG.value: {
            "release_lane": release_lane,
            "selected_version": selected_version,
            "api_mode": api_mode,
            "data_source_mode": data_source_mode,
            "language": "de",
            "fallback_language": "en",
            "view_obsolete": False,
            "index_storage_path": DEFAULT_ESCO_INDEX_STORAGE_PATH,
            "index_version": selected_version,
        },
        SSKey.ESCO_LAST_DATA_SOURCE.value: "",
        SSKey.ESCO_NEGATIVE_CACHE.value: {},
    }
    client = EscoClient(session_state=session_state, timeout_seconds=6.0)
    result: dict[str, Any] = {
        "release_lane": release_lane,
        "selected_version": selected_version,
        "api_mode": api_mode,
        "data_source_mode": data_source_mode,
        "status": "ok",
        "endpoints": {},
    }

    try:
        suggest_payload = client.suggest2(
            text="Softwareentwickler",
            type="occupation",
            limit=3,
        )
        result["endpoints"]["suggest2"] = {"count": _safe_count(suggest_payload)}
        search_payload = client.search(
            text="Softwareentwickler",
            type="occupation",
            limit=3,
        )
        result["endpoints"]["search"] = {"count": _safe_count(search_payload)}
        occupation_uri = _first_uri(suggest_payload) or _first_uri(search_payload)
        if not occupation_uri:
            result["status"] = "skipped"
            result["reason"] = "no_occupation_result"
            return result
        terms_payload = client.terms(
            uri=occupation_uri,
            type="occupation",
            limit=3,
        )
        result["endpoints"]["terms"] = {"count": _safe_count(terms_payload)}
        occupation_payload = client.resource_occupation(uri=occupation_uri)
        result["endpoints"]["resource/occupation"] = {
            "available": bool(occupation_payload)
        }
        related_payload = client.resource_related(
            uri=occupation_uri,
            relation="hasEssentialSkill",
            limit=3,
        )
        result["endpoints"]["resource/related"] = {
            "count": _safe_count(related_payload)
        }
        result["actual_data_source"] = str(
            session_state.get(SSKey.ESCO_LAST_DATA_SOURCE.value) or ""
        )
    except EscoClientError as exc:
        if dry_run_if_unavailable:
            result["status"] = "skipped"
            result["reason"] = exc.message
            result["endpoint"] = exc.endpoint
            return result
        result["status"] = "failed"
        result["reason"] = exc.message
        result["endpoint"] = exc.endpoint
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=["all", "hosted", "local"],
        default="all",
        help="Limit API mode combinations.",
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Emit only JSON output.",
    )
    parser.add_argument(
        "--ci-dry-run-if-unavailable",
        action="store_true",
        help="Skip unavailable combinations instead of failing.",
    )
    args = parser.parse_args()
    if args.json_only:
        logging.disable(logging.CRITICAL)
        logging.getLogger().setLevel(logging.CRITICAL)
        logging.getLogger("streamlit").setLevel(logging.CRITICAL)
        logging.getLogger("esco_client").setLevel(logging.CRITICAL)

    api_modes = ESCO_API_MODES if args.mode == "all" else (args.mode,)
    results = [
        _check_combo(
            release_lane=release_lane,
            api_mode=api_mode,
            data_source_mode=data_source_mode,
            dry_run_if_unavailable=args.ci_dry_run_if_unavailable,
        )
        for release_lane in ESCO_RELEASE_LANES
        for api_mode in api_modes
        for data_source_mode in ESCO_DATA_SOURCE_MODES
    ]
    print(json.dumps({"results": results}, ensure_ascii=False, indent=2))
    if args.json_only:
        return 0 if all(item["status"] != "failed" for item in results) else 1
    failed = [item for item in results if item["status"] == "failed"]
    skipped = [item for item in results if item["status"] == "skipped"]
    ok_count = len(results) - len(failed) - len(skipped)
    print(f"ESCO smoke: {ok_count} ok, {len(skipped)} skipped, {len(failed)} failed")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
