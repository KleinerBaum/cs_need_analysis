from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import streamlit as st

from constants import DEFAULT_ESCO_SELECTED_VERSION, SSKey

LOGGER = logging.getLogger(__name__)
EXTERNAL_PROVIDER_ERROR_EVENT = "external_provider_error"

ESCO_CACHE_TTL_SECONDS = 600
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_ESCO_API_BASE_URL = "https://ec.europa.eu/esco/api/"
RETRYABLE_HTTP_STATUS_CODES = frozenset({500, 502, 503, 504})
MAX_RETRIES = 2
RETRY_BACKOFF_SECONDS = 0.25
SUPPORTED_API_MODES = frozenset({"hosted", "local"})


def is_retryable_server_status(status_code: int | None) -> bool:
    return status_code in RETRYABLE_HTTP_STATUS_CODES


def clear_esco_cache() -> None:
    """Clear cached ESCO GET responses."""

    _cached_get_json.clear()


def _coerce_bool(value: object, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    return default


@dataclass(slots=True)
class EscoClientError(Exception):
    """User-safe ESCO client error payload."""

    status_code: int | None
    endpoint: str
    message: str

    def __str__(self) -> str:
        return self.message


@st.cache_data(ttl=ESCO_CACHE_TTL_SECONDS, show_spinner=False)
def _cached_get_json(
    *,
    base_url: str,
    endpoint: str,
    query_items: tuple[tuple[str, str], ...],
    cache_selected_version: str,
    cache_language: str,
    cache_view_obsolete: bool,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Cached read-only GET request.

    Extra cache_* arguments are intentionally present so cache key always includes
    selected version, language, and obsolete-view setting.
    """

    del cache_selected_version, cache_language, cache_view_obsolete

    url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    if query_items:
        url = f"{url}?{urlencode(query_items, doseq=True)}"

    request = Request(url, headers={"Accept": "application/json"}, method="GET")
    max_attempts = MAX_RETRIES + 1
    body = ""
    status_code = 200
    started = time.perf_counter()

    for attempt in range(1, max_attempts + 1):
        try:
            with urlopen(request, timeout=timeout_seconds) as response:  # nosec B310
                status_code = int(getattr(response, "status", 200))
                body = response.read().decode("utf-8")
            break
        except HTTPError as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            should_retry = (
                exc.code in RETRYABLE_HTTP_STATUS_CODES and attempt < max_attempts
            )
            LOGGER.warning(
                "ESCO request failed endpoint=%s status=%s latency_ms=%s attempt=%s/%s retry=%s",
                endpoint,
                exc.code,
                elapsed_ms,
                attempt,
                max_attempts,
                should_retry,
            )
            if should_retry:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
                continue
            LOGGER.error(
                "event=%s provider=esco endpoint=%s status=%s latency_ms=%s attempt=%s/%s",
                EXTERNAL_PROVIDER_ERROR_EVENT,
                endpoint,
                exc.code,
                elapsed_ms,
                attempt,
                max_attempts,
            )
            raise EscoClientError(
                status_code=exc.code,
                endpoint=endpoint,
                message=(
                    "Der ESCO-Dienst ist aktuell vorübergehend nicht verfügbar."
                    if is_retryable_server_status(exc.code)
                    else "ESCO service returned an error response."
                ),
            ) from exc
        except URLError as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            should_retry = attempt < max_attempts
            LOGGER.warning(
                "ESCO request failed endpoint=%s status=network_error latency_ms=%s attempt=%s/%s retry=%s",
                endpoint,
                elapsed_ms,
                attempt,
                max_attempts,
                should_retry,
            )
            if should_retry:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
                continue
            LOGGER.error(
                "event=%s provider=esco endpoint=%s status=network_error latency_ms=%s attempt=%s/%s",
                EXTERNAL_PROVIDER_ERROR_EVENT,
                endpoint,
                elapsed_ms,
                attempt,
                max_attempts,
            )
            raise EscoClientError(
                status_code=None,
                endpoint=endpoint,
                message="ESCO service is currently unreachable.",
            ) from exc

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    LOGGER.info(
        "ESCO request finished endpoint=%s status=%s latency_ms=%s",
        endpoint,
        status_code,
        elapsed_ms,
    )

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise EscoClientError(
            status_code=status_code,
            endpoint=endpoint,
            message="ESCO service returned invalid JSON.",
        ) from exc

    if not isinstance(payload, dict):
        raise EscoClientError(
            status_code=status_code,
            endpoint=endpoint,
            message="ESCO service response format is unsupported.",
        )

    return payload


class EscoClient:
    """Small ESCO API client with centralized config + query injection."""

    def __init__(
        self,
        session_state: Mapping[str, object] | None = None,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._session_state = (
            session_state if session_state is not None else st.session_state
        )
        self._timeout_seconds = timeout_seconds

    def suggest2(self, *, text: str, **query: object) -> dict[str, Any]:
        merged_query = {"text": text, **query}
        return self._get("suggest2", merged_query)

    def terms(self, **query: object) -> dict[str, Any]:
        return self._get("terms", query)

    def search(self, *, text: str, **query: object) -> dict[str, Any]:
        merged_query = {"text": text, **query}
        return self._get("search", merged_query)

    def resource_occupation(self, *, uri: str, **query: object) -> dict[str, Any]:
        merged_query = {"uri": uri, **query}
        return self._get("resource/occupation", merged_query)

    def resource_skill(self, *, uri: str, **query: object) -> dict[str, Any]:
        merged_query = {"uri": uri, **query}
        return self._get("resource/skill", merged_query)

    def resource_related(self, *, uri: str, **query: object) -> dict[str, Any]:
        merged_query = {"uri": uri, **query}
        return self._get("resource/related", merged_query)

    def get_occupation_detail(self, *, uri: str, **query: object) -> dict[str, Any]:
        return self.resource_occupation(uri=uri, **query)

    def get_skill_detail(self, *, uri: str, **query: object) -> dict[str, Any]:
        return self.resource_skill(uri=uri, **query)

    def get_occupation_essential_skills(
        self, *, occupation_uri: str, **query: object
    ) -> dict[str, Any]:
        return self.resource_related(
            uri=occupation_uri, relation="hasEssentialSkill", **query
        )

    def get_occupation_optional_skills(
        self, *, occupation_uri: str, **query: object
    ) -> dict[str, Any]:
        return self.resource_related(
            uri=occupation_uri, relation="hasOptionalSkill", **query
        )

    def get_occupation_skill_group_share(
        self, *, occupation_uri: str, **query: object
    ) -> dict[str, Any]:
        merged_query = {"uri": occupation_uri, **query}
        return self._get("resource/occupationSkillsGroupShare", merged_query)

    def get_skill_related_occupations(
        self, *, skill_uri: str, **query: object
    ) -> dict[str, Any]:
        return self.resource_related(
            uri=skill_uri, relation="isEssentialForOccupation", **query
        )

    def conversion(self, conversion_endpoint: str, **query: object) -> dict[str, Any]:
        clean_endpoint = conversion_endpoint.strip().strip("/")
        if not clean_endpoint:
            raise ValueError("conversion_endpoint must not be empty")
        return self._get(f"conversion/{clean_endpoint}", query)

    def _get(self, endpoint: str, query: Mapping[str, object]) -> dict[str, Any]:
        config = self._esco_config()
        resolved_endpoint = self._resolve_endpoint(
            endpoint=endpoint, api_mode=str(config["api_mode"])
        )
        injected_query = self._inject_default_query_params(config=config, query=query)
        query_items = self._query_items(injected_query)
        base_url = str(config["base_url"])
        selected_version = str(config["selected_version"])
        language = str(config["language"])
        view_obsolete = bool(config["view_obsolete"])

        return _cached_get_json(
            base_url=base_url,
            endpoint=resolved_endpoint,
            query_items=query_items,
            cache_selected_version=selected_version,
            cache_language=language,
            cache_view_obsolete=view_obsolete,
            timeout_seconds=self._timeout_seconds,
        )

    def _esco_config(self) -> dict[str, object]:
        raw = self._session_state.get(SSKey.ESCO_CONFIG.value, {})
        config = raw if isinstance(raw, Mapping) else {}
        session_base_url = str(config.get("base_url") or "").strip()
        env_base_url = os.getenv("ESCO_API_BASE_URL", "").strip()
        resolved_base_url = (
            session_base_url or env_base_url or DEFAULT_ESCO_API_BASE_URL
        )

        session_selected_version = str(config.get("selected_version") or "").strip()
        env_selected_version = os.getenv("ESCO_SELECTED_VERSION", "").strip()
        resolved_selected_version = (
            session_selected_version
            or env_selected_version
            or DEFAULT_ESCO_SELECTED_VERSION
        )
        api_mode = (
            str(config.get("api_mode") or os.getenv("ESCO_API_MODE", "hosted"))
            .strip()
            .lower()
        )
        if api_mode not in SUPPORTED_API_MODES:
            api_mode = "hosted"

        return {
            "base_url": resolved_base_url,
            "selected_version": resolved_selected_version,
            "language": str(config.get("language") or "de"),
            "view_obsolete": _coerce_bool(config.get("view_obsolete"), default=False),
            "api_mode": api_mode,
        }

    @staticmethod
    @lru_cache(maxsize=8)
    def _resolve_endpoint(*, endpoint: str, api_mode: str) -> str:
        clean_endpoint = endpoint.strip().strip("/")
        if api_mode == "local":
            # Future-proof indirection for local deployments; currently identical paths.
            return clean_endpoint
        return clean_endpoint

    @staticmethod
    def _inject_default_query_params(
        *,
        config: Mapping[str, object],
        query: Mapping[str, object],
    ) -> dict[str, object]:
        merged = dict(query)
        if "language" not in merged:
            merged["language"] = str(config["language"])
        if "selectedVersion" not in merged:
            merged["selectedVersion"] = str(config["selected_version"])
        if "viewObsolete" not in merged:
            merged["viewObsolete"] = (
                "true" if bool(config["view_obsolete"]) else "false"
            )
        return merged

    @staticmethod
    def _query_items(query: Mapping[str, object]) -> tuple[tuple[str, str], ...]:
        items: list[tuple[str, str]] = []
        for key in sorted(query.keys()):
            value = query[key]
            if value is None:
                continue
            if isinstance(value, (list, tuple, set)):
                for nested in value:
                    if nested is not None:
                        items.append((str(key), str(nested)))
                continue
            items.append((str(key), str(value)))
        return tuple(items)
