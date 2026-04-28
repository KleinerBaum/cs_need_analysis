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
EXTERNAL_PROVIDER_REQUEST_ERROR_EVENT = "external_provider_request_error"

ESCO_CACHE_TTL_SECONDS = 600
ESCO_CAPABILITY_CACHE_TTL_SECONDS = 120
ESCO_NEGATIVE_CACHE_TTL_SECONDS = 600
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_ESCO_API_BASE_URL = "https://ec.europa.eu/esco/api/"
RETRYABLE_HTTP_STATUS_CODES = frozenset({500, 502, 503, 504})
MAX_RETRIES = 2
RETRY_BACKOFF_SECONDS = 0.25
SUPPORTED_API_MODES = frozenset({"hosted", "local"})
SAFE_HTTP_ERROR_HINT_KEYS = ("message", "error", "detail", "title", "reason")
SAFE_LOG_QUERY_KEYS = frozenset(
    {"language", "selectedVersion", "type", "viewObsolete", "limit", "offset", "page"}
)
SENSITIVE_HINT_MARKERS = ("secret", "token", "password", "api_key", "authorization")
SUPPORTED_OCCUPATION_RELATIONS_BY_API_MODE: dict[str, tuple[str, ...]] = {
    "hosted": ("hasEssentialSkill", "hasOptionalSkill"),
    "local": ("hasEssentialSkill", "hasOptionalSkill"),
}
UNSUPPORTED_ENDPOINTS_BY_API_MODE: dict[str, frozenset[str]] = {
    "hosted": frozenset({"resource/occupationSkillsGroupShare"}),
    "local": frozenset(),
}


def is_retryable_server_status(status_code: int | None) -> bool:
    return status_code in RETRYABLE_HTTP_STATUS_CODES


def clear_esco_cache() -> None:
    """Clear cached ESCO GET responses."""

    _cached_get_json.clear()
    _cached_endpoint_support.clear()


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


def _extract_safe_http_error_hint(exc: HTTPError) -> str | None:
    if not hasattr(exc, "read"):
        return None
    try:
        raw_body = exc.read()
    except Exception:  # pragma: no cover - defensive read fallback
        return None
    if not raw_body:
        return None
    decoded = raw_body.decode("utf-8", errors="replace").strip()
    if not decoded:
        return None

    hint: str | None = None
    try:
        parsed = json.loads(decoded)
    except json.JSONDecodeError:
        hint = decoded
    else:
        if isinstance(parsed, dict):
            for key in SAFE_HTTP_ERROR_HINT_KEYS:
                value = parsed.get(key)
                if isinstance(value, str) and value.strip():
                    hint = value.strip()
                    break
    if not hint:
        return None

    compact_hint = " ".join(hint.split())
    if any(marker in compact_hint.lower() for marker in SENSITIVE_HINT_MARKERS):
        return None
    return compact_hint[:160]


def _safe_request_context(
    endpoint: str, query_items: tuple[tuple[str, str], ...]
) -> dict[str, object]:
    query_keys = sorted({key for key, _ in query_items})
    selected_query: dict[str, str] = {}
    for key, value in query_items:
        if key in SAFE_LOG_QUERY_KEYS and key not in selected_query:
            selected_query[key] = value
    return {
        "endpoint": endpoint,
        "query_keys": query_keys,
        "selected_query": selected_query,
    }


@dataclass(slots=True)
class EscoClientError(Exception):
    """User-safe ESCO client error payload."""

    status_code: int | None
    endpoint: str
    message: str
    suppressed_repeat_count: int = 0
    from_negative_cache: bool = False

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
            safe_hint = _extract_safe_http_error_hint(exc)
            if 400 <= exc.code < 500:
                safe_context = _safe_request_context(endpoint, query_items)
                LOGGER.warning(
                    "event=%s provider=esco endpoint=%s status=%s latency_ms=%s query_keys=%s selected_query=%s%s",
                    EXTERNAL_PROVIDER_REQUEST_ERROR_EVENT,
                    endpoint,
                    exc.code,
                    elapsed_ms,
                    safe_context["query_keys"],
                    safe_context["selected_query"],
                    (
                        f" provider_error_hint={safe_hint}"
                        if safe_hint is not None
                        else ""
                    ),
                )
                raise EscoClientError(
                    status_code=exc.code,
                    endpoint=endpoint,
                    message=(
                        "ESCO request parameters are not supported for this endpoint/version."
                    ),
                ) from exc
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


@st.cache_data(ttl=ESCO_CAPABILITY_CACHE_TTL_SECONDS, show_spinner=False)
def _cached_endpoint_support(
    *,
    base_url: str,
    endpoint: str,
    selected_version: str,
    api_mode: str,
    timeout_seconds: float,
) -> bool:
    """Best-effort endpoint capability probe per base URL + version + mode.

    The probe is conservative: network/temporary errors are treated as supported
    so feature paths remain available and can degrade gracefully during fetch.
    """

    del api_mode

    probe_query_items: tuple[tuple[str, str], ...] = (
        ("selectedVersion", selected_version),
        ("limit", "1"),
    )
    url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}?{urlencode(probe_query_items)}"
    request = Request(url, headers={"Accept": "application/json"}, method="GET")

    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # nosec B310
            status_code = int(getattr(response, "status", 200))
            return status_code < 400
    except HTTPError as exc:
        if exc.code in {400, 401, 403}:
            return True
        if exc.code == 404:
            return False
        return True
    except URLError:
        return True


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

    def supported_occupation_relations(self) -> tuple[str, ...]:
        config = self._esco_config()
        api_mode = str(config["api_mode"])
        return SUPPORTED_OCCUPATION_RELATIONS_BY_API_MODE.get(api_mode, ())

    def supports_relation(self, *, resource_type: str, relation: str) -> bool:
        normalized_resource_type = resource_type.strip().lower()
        normalized_relation = relation.strip()
        if normalized_resource_type != "occupation":
            return True
        return normalized_relation in self.supported_occupation_relations()

    def supports_endpoint(self, endpoint: str) -> bool:
        config = self._esco_config()
        api_mode = str(config["api_mode"])
        resolved_endpoint = self._resolve_endpoint(
            endpoint=endpoint, api_mode=api_mode
        )
        unsupported_endpoints = UNSUPPORTED_ENDPOINTS_BY_API_MODE.get(
            api_mode,
            frozenset(),
        )
        if resolved_endpoint in unsupported_endpoints:
            return False
        return _cached_endpoint_support(
            base_url=str(config["base_url"]),
            endpoint=resolved_endpoint,
            selected_version=str(config["selected_version"]),
            api_mode=api_mode,
            timeout_seconds=self._timeout_seconds,
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
        signature = self._build_request_signature(
            base_url=base_url,
            endpoint=resolved_endpoint,
            selected_version=selected_version,
            language=language,
            query=injected_query,
        )
        self._raise_if_negative_cached(
            signature=signature,
            endpoint=resolved_endpoint,
        )

        try:
            return _cached_get_json(
                base_url=base_url,
                endpoint=resolved_endpoint,
                query_items=query_items,
                cache_selected_version=selected_version,
                cache_language=language,
                cache_view_obsolete=view_obsolete,
                timeout_seconds=self._timeout_seconds,
            )
        except EscoClientError as exc:
            if exc.status_code is not None and 400 <= exc.status_code < 500:
                self._store_negative_cache(
                    signature=signature,
                    endpoint=resolved_endpoint,
                    status_code=exc.status_code,
                    message=exc.message,
                )
            raise

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

    @staticmethod
    def _signature_key_params(query: Mapping[str, object]) -> tuple[tuple[str, str], ...]:
        key_params = ("uri", "relation", "type", "text")
        normalized: list[tuple[str, str]] = []
        for key in key_params:
            value = query.get(key)
            if value is None:
                continue
            normalized.append((key, str(value).strip()))
        return tuple(normalized)

    def _build_request_signature(
        self,
        *,
        base_url: str,
        endpoint: str,
        selected_version: str,
        language: str,
        query: Mapping[str, object],
    ) -> str:
        key_params = self._signature_key_params(query)
        payload = {
            "base_url": base_url.rstrip("/"),
            "endpoint": endpoint.strip().strip("/"),
            "selectedVersion": selected_version.strip(),
            "language": language.strip(),
            "key_params": key_params,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    def _negative_cache_store(self) -> dict[str, dict[str, object]]:
        raw = self._session_state.get(SSKey.ESCO_NEGATIVE_CACHE.value, {})
        if isinstance(raw, dict):
            return raw
        store: dict[str, dict[str, object]] = {}
        self._session_state[SSKey.ESCO_NEGATIVE_CACHE.value] = store
        return store

    def _raise_if_negative_cached(self, *, signature: str, endpoint: str) -> None:
        store = self._negative_cache_store()
        cached_entry = store.get(signature)
        if not isinstance(cached_entry, dict):
            return
        expires_at = cached_entry.get("expires_at")
        try:
            expires_at_seconds = float(expires_at)
        except (TypeError, ValueError):
            store.pop(signature, None)
            return
        now = time.time()
        if expires_at_seconds <= now:
            store.pop(signature, None)
            return

        suppressed_count = int(cached_entry.get("suppressed_count") or 0) + 1
        cached_entry["suppressed_count"] = suppressed_count
        log_emitted = bool(cached_entry.get("suppression_log_emitted"))
        if not log_emitted:
            cached_entry["suppression_log_emitted"] = True
            LOGGER.info(
                "ESCO negative-cache suppress endpoint=%s suppressed_count=%s",
                endpoint,
                suppressed_count,
            )

        status_code_raw = cached_entry.get("status_code")
        status_code = int(status_code_raw) if isinstance(status_code_raw, int) else None
        cached_message = str(
            cached_entry.get("message")
            or "ESCO request parameters are temporarily suppressed due to recent 4xx response."
        )
        raise EscoClientError(
            status_code=status_code,
            endpoint=endpoint,
            message=cached_message,
            suppressed_repeat_count=suppressed_count,
            from_negative_cache=True,
        )

    def _store_negative_cache(
        self,
        *,
        signature: str,
        endpoint: str,
        status_code: int,
        message: str,
    ) -> None:
        store = self._negative_cache_store()
        store[signature] = {
            "status_code": status_code,
            "message": message,
            "cached_at": time.time(),
            "expires_at": time.time() + ESCO_NEGATIVE_CACHE_TTL_SECONDS,
            "suppressed_count": 0,
            "suppression_log_emitted": False,
        }
        LOGGER.debug(
            "ESCO negative-cache stored endpoint=%s status=%s ttl_seconds=%s",
            endpoint,
            status_code,
            ESCO_NEGATIVE_CACHE_TTL_SECONDS,
        )
