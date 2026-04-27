from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace
from typing import Literal, cast
from urllib.error import HTTPError

import pytest

from constants import SSKey
import esco_client


def test_injects_esco_config_into_query(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_cached_get_json(**kwargs):
        captured.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(esco_client, "_cached_get_json", fake_cached_get_json)

    client = esco_client.EscoClient(
        session_state={
            SSKey.ESCO_CONFIG.value: {
                "base_url": "https://example.test/esco/",
                "selected_version": "v1.2.3",
                "language": "en",
                "view_obsolete": True,
            }
        }
    )

    payload = client.search(text="developer", type="occupation")

    assert payload == {"ok": True}
    assert captured["base_url"] == "https://example.test/esco/"
    assert captured["endpoint"] == "search"
    assert captured["cache_selected_version"] == "v1.2.3"
    assert captured["cache_language"] == "en"
    assert captured["cache_view_obsolete"] is True
    assert captured["query_items"] == (
        ("language", "en"),
        ("selectedVersion", "v1.2.3"),
        ("text", "developer"),
        ("type", "occupation"),
        ("viewObsolete", "true"),
    )


def test_explicit_query_params_override_config_defaults(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_cached_get_json(**kwargs):
        captured.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(esco_client, "_cached_get_json", fake_cached_get_json)

    client = esco_client.EscoClient(
        session_state={
            SSKey.ESCO_CONFIG.value: {
                "selected_version": "latest",
                "language": "de",
                "view_obsolete": False,
            }
        }
    )

    payload = client.terms(
        uri="https://data.europa.eu/esco/occupation/test",
        type="occupation",
        language="en",
        selectedVersion="v1.2.3",
        viewObsolete="true",
    )

    assert payload == {"ok": True}
    query_items = cast(tuple[tuple[str, str], ...], captured["query_items"])
    assert ("language", "en") in query_items
    assert ("selectedVersion", "v1.2.3") in query_items
    assert ("viewObsolete", "true") in query_items


def test_esco_client_error_is_user_safe() -> None:
    err = esco_client.EscoClientError(
        status_code=503,
        endpoint="search",
        message="ESCO service returned an error response.",
    )

    assert str(err) == "ESCO service returned an error response."
    assert "response" in err.message.lower()


def test_cached_get_json_retries_retryable_http_errors(monkeypatch) -> None:
    attempts = {"count": 0}
    sleeps: list[float] = []

    class _Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> Literal[False]:
            return False

        def read(self) -> bytes:
            return b'{"ok": true}'

    def fake_urlopen(_request, timeout):
        del timeout
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise HTTPError(
                url="https://example.test/esco/terms",
                code=500,
                msg="server error",
                hdrs=None,
                fp=BytesIO(b""),
            )
        return _Response()

    monkeypatch.setattr(esco_client, "urlopen", fake_urlopen)
    monkeypatch.setattr(
        esco_client.time, "sleep", lambda seconds: sleeps.append(seconds)
    )
    esco_client.clear_esco_cache()

    payload = esco_client._cached_get_json(
        base_url="https://example.test/esco/",
        endpoint="terms",
        query_items=(("type", "occupation"),),
        cache_selected_version="latest",
        cache_language="de",
        cache_view_obsolete=False,
        timeout_seconds=1.0,
    )

    assert payload == {"ok": True}
    assert attempts["count"] == 3
    assert sleeps == [0.25, 0.5]


def test_cached_get_json_raises_controlled_error_after_last_retry_on_5xx(
    monkeypatch, caplog
) -> None:
    attempts = {"count": 0}
    sleeps: list[float] = []

    def fake_urlopen(_request, timeout):
        del timeout
        attempts["count"] += 1
        raise HTTPError(
            url="https://example.test/esco/terms",
            code=503,
            msg="server error",
            hdrs=None,
            fp=BytesIO(b""),
        )

    monkeypatch.setattr(esco_client, "urlopen", fake_urlopen)
    monkeypatch.setattr(
        esco_client.time, "sleep", lambda seconds: sleeps.append(seconds)
    )
    esco_client.clear_esco_cache()

    with pytest.raises(esco_client.EscoClientError) as exc_info:
        esco_client._cached_get_json(
            base_url="https://example.test/esco/",
            endpoint="terms",
            query_items=(("type", "occupation"),),
            cache_selected_version="latest",
            cache_language="de",
            cache_view_obsolete=False,
            timeout_seconds=1.0,
        )

    err = exc_info.value
    assert err.status_code == 503
    assert err.endpoint == "terms"
    assert "vorübergehend nicht verfügbar" in str(err)
    assert attempts["count"] == 3
    assert sleeps == [0.25, 0.5]
    assert any(
        "event=external_provider_error provider=esco endpoint=terms status=503"
        in record.message
        for record in caplog.records
    )


def test_cached_get_json_handles_400_as_request_error_without_retries(
    monkeypatch, caplog
) -> None:
    attempts = {"count": 0}
    sleeps: list[float] = []

    def fake_urlopen(_request, timeout):
        del timeout
        attempts["count"] += 1
        raise HTTPError(
            url="https://example.test/esco/terms",
            code=400,
            msg="bad request",
            hdrs=None,
            fp=BytesIO(b'{"message":"Invalid selectedVersion for endpoint"}'),
        )

    monkeypatch.setattr(esco_client, "urlopen", fake_urlopen)
    monkeypatch.setattr(
        esco_client.time, "sleep", lambda seconds: sleeps.append(seconds)
    )
    esco_client.clear_esco_cache()

    with pytest.raises(esco_client.EscoClientError) as exc_info:
        esco_client._cached_get_json(
            base_url="https://example.test/esco/",
            endpoint="terms",
            query_items=(("type", "occupation"), ("selectedVersion", "v9")),
            cache_selected_version="latest",
            cache_language="de",
            cache_view_obsolete=False,
            timeout_seconds=1.0,
        )

    err = exc_info.value
    assert err.status_code == 400
    assert (
        str(err)
        == "ESCO request parameters are not supported for this endpoint/version."
    )
    assert attempts["count"] == 1
    assert sleeps == []
    assert any(
        "event=external_provider_request_error provider=esco endpoint=terms status=400"
        in record.message
        for record in caplog.records
    )


def test_conversion_endpoint_must_not_be_empty() -> None:
    client = esco_client.EscoClient(session_state={SSKey.ESCO_CONFIG.value: {}})

    with pytest.raises(ValueError, match="must not be empty"):
        client.conversion("   ")


def test_conversion_uses_split_endpoint_paths(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_cached_get_json(**kwargs):
        captured.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(esco_client, "_cached_get_json", fake_cached_get_json)
    client = esco_client.EscoClient(session_state={SSKey.ESCO_CONFIG.value: {}})

    payload = client.conversion("skill", uri="legacy:123")

    assert payload == {"ok": True}
    assert captured["endpoint"] == "conversion/skill"
    query_items = cast(tuple[tuple[str, str], ...], captured["query_items"])
    assert ("uri", "legacy:123") in query_items


def test_default_config_is_used_when_session_state_is_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        esco_client,
        "st",
        SimpleNamespace(session_state={}),
    )

    client = esco_client.EscoClient()
    config = client._esco_config()

    assert config == {
        "base_url": "https://ec.europa.eu/esco/api/",
        "selected_version": "v1.2.0",
        "language": "de",
        "view_obsolete": False,
        "api_mode": "hosted",
    }


def test_esco_config_prefers_env_base_url_when_session_value_missing(
    monkeypatch,
) -> None:
    monkeypatch.setenv("ESCO_API_BASE_URL", "https://env.example/esco/")

    client = esco_client.EscoClient(session_state={SSKey.ESCO_CONFIG.value: {}})

    assert client._esco_config()["base_url"] == "https://env.example/esco/"


def test_esco_config_uses_env_selected_version(monkeypatch) -> None:
    monkeypatch.setenv("ESCO_SELECTED_VERSION", "v1.3.0")
    client = esco_client.EscoClient(session_state={SSKey.ESCO_CONFIG.value: {}})
    assert client._esco_config()["selected_version"] == "v1.3.0"


def test_esco_config_prefers_session_base_url_over_env(monkeypatch) -> None:
    monkeypatch.setenv("ESCO_API_BASE_URL", "https://env.example/esco/")
    client = esco_client.EscoClient(
        session_state={SSKey.ESCO_CONFIG.value: {"base_url": "https://session/esco/"}}
    )

    assert client._esco_config()["base_url"] == "https://session/esco/"


def test_get_occupation_skill_group_share_uses_dedicated_endpoint(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_cached_get_json(**kwargs):
        captured.update(kwargs)
        return {"_embedded": {"results": []}}

    monkeypatch.setattr(esco_client, "_cached_get_json", fake_cached_get_json)
    client = esco_client.EscoClient(session_state={SSKey.ESCO_CONFIG.value: {}})

    payload = client.get_occupation_skill_group_share(occupation_uri="uri:occupation:1")

    assert payload == {"_embedded": {"results": []}}
    assert captured["endpoint"] == "resource/occupationSkillsGroupShare"
    query_items = cast(tuple[tuple[str, str], ...], captured["query_items"])
    assert ("uri", "uri:occupation:1") in query_items


def test_get_occupation_skill_group_share_propagates_client_errors(monkeypatch) -> None:
    expected_error = esco_client.EscoClientError(
        status_code=503,
        endpoint="resource/occupationSkillsGroupShare",
        message="Der ESCO-Dienst ist aktuell vorübergehend nicht verfügbar.",
    )

    def fake_cached_get_json(**_kwargs):
        raise expected_error

    monkeypatch.setattr(esco_client, "_cached_get_json", fake_cached_get_json)
    client = esco_client.EscoClient(session_state={SSKey.ESCO_CONFIG.value: {}})

    with pytest.raises(esco_client.EscoClientError) as exc_info:
        client.get_occupation_skill_group_share(occupation_uri="uri:occupation:1")

    assert exc_info.value is expected_error


def test_supports_endpoint_returns_false_for_404(monkeypatch) -> None:
    def fake_urlopen(_request, timeout):
        del timeout
        raise HTTPError(
            url="https://example.test/esco/resource/occupationSkillsGroupShare",
            code=404,
            msg="not found",
            hdrs=None,
            fp=BytesIO(b""),
        )

    monkeypatch.setattr(esco_client, "urlopen", fake_urlopen)
    esco_client.clear_esco_cache()
    client = esco_client.EscoClient(session_state={SSKey.ESCO_CONFIG.value: {}})

    assert client.supports_endpoint("resource/occupationSkillsGroupShare") is False


def test_supports_endpoint_returns_false_for_hosted_blocklist_without_probe(
    monkeypatch,
) -> None:
    def fail_if_called(**_kwargs):
        raise AssertionError("_cached_endpoint_support should not be called")

    monkeypatch.setattr(esco_client, "_cached_endpoint_support", fail_if_called)
    client = esco_client.EscoClient(
        session_state={SSKey.ESCO_CONFIG.value: {"api_mode": "hosted"}}
    )

    assert client.supports_endpoint("resource/occupationSkillsGroupShare") is False


def test_supports_endpoint_still_probes_blocklisted_endpoint_for_local_mode(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_cached_endpoint_support(**kwargs):
        captured.update(kwargs)
        return True

    monkeypatch.setattr(esco_client, "_cached_endpoint_support", fake_cached_endpoint_support)
    client = esco_client.EscoClient(
        session_state={SSKey.ESCO_CONFIG.value: {"api_mode": "local"}}
    )

    assert client.supports_endpoint("resource/occupationSkillsGroupShare") is True
    assert captured["endpoint"] == "resource/occupationSkillsGroupShare"
    assert captured["api_mode"] == "local"


def test_supports_endpoint_uses_capability_cache_per_version(monkeypatch) -> None:
    calls: list[float] = []

    class _Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> Literal[False]:
            del exc_type, exc, tb
            return False

        def read(self) -> bytes:
            return b"{}"

    def fake_urlopen(_request, timeout):
        calls.append(timeout)
        return _Response()

    monkeypatch.setattr(esco_client, "urlopen", fake_urlopen)
    esco_client.clear_esco_cache()
    client_v1 = esco_client.EscoClient(
        session_state={
            SSKey.ESCO_CONFIG.value: {
                "selected_version": "v1.2.0",
                "api_mode": "local",
            }
        }
    )
    client_v2 = esco_client.EscoClient(
        session_state={
            SSKey.ESCO_CONFIG.value: {
                "selected_version": "v1.3.0",
                "api_mode": "local",
            }
        }
    )

    assert client_v1.supports_endpoint("resource/occupationSkillsGroupShare") is True
    assert client_v1.supports_endpoint("resource/occupationSkillsGroupShare") is True
    assert client_v2.supports_endpoint("resource/occupationSkillsGroupShare") is True
    assert len(calls) == 2


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("false", False),
        ("0", False),
        ("true", True),
        ("1", True),
    ],
)
def test_view_obsolete_string_values_are_coerced(
    raw_value: str, expected: bool
) -> None:
    client = esco_client.EscoClient(
        session_state={SSKey.ESCO_CONFIG.value: {"view_obsolete": raw_value}}
    )

    config = client._esco_config()

    assert config["view_obsolete"] is expected


def test_negative_cache_stores_non_retryable_4xx_and_suppresses_followups(
    monkeypatch,
) -> None:
    call_counter = {"count": 0}

    def fake_cached_get_json(**_kwargs):
        call_counter["count"] += 1
        raise esco_client.EscoClientError(
            status_code=404,
            endpoint="resource/related",
            message="Not found",
        )

    monkeypatch.setattr(esco_client, "_cached_get_json", fake_cached_get_json)
    now = {"value": 1_000.0}
    monkeypatch.setattr(esco_client.time, "time", lambda: now["value"])
    session_state = {
        SSKey.ESCO_CONFIG.value: {
            "base_url": "https://example.test/esco/",
            "selected_version": "v1.2.0",
            "language": "de",
            "view_obsolete": False,
        },
        SSKey.ESCO_NEGATIVE_CACHE.value: {},
    }
    client = esco_client.EscoClient(session_state=session_state)

    with pytest.raises(esco_client.EscoClientError) as first_exc:
        client.resource_related(uri="occupation:test", relation="hasEssentialSkill")
    assert first_exc.value.from_negative_cache is False
    assert call_counter["count"] == 1
    assert len(session_state[SSKey.ESCO_NEGATIVE_CACHE.value]) == 1

    with pytest.raises(esco_client.EscoClientError) as second_exc:
        client.resource_related(uri="occupation:test", relation="hasEssentialSkill")
    assert second_exc.value.from_negative_cache is True
    assert second_exc.value.suppressed_repeat_count == 1
    assert call_counter["count"] == 1


def test_negative_cache_expires_and_allows_network_calls_again(monkeypatch) -> None:
    call_counter = {"count": 0}

    def fake_cached_get_json(**_kwargs):
        call_counter["count"] += 1
        raise esco_client.EscoClientError(
            status_code=400,
            endpoint="terms",
            message="Bad request",
        )

    monkeypatch.setattr(esco_client, "_cached_get_json", fake_cached_get_json)
    now = {"value": 2_000.0}
    monkeypatch.setattr(esco_client.time, "time", lambda: now["value"])
    session_state = {
        SSKey.ESCO_CONFIG.value: {
            "base_url": "https://example.test/esco/",
            "selected_version": "v1.2.0",
            "language": "de",
            "view_obsolete": False,
        },
        SSKey.ESCO_NEGATIVE_CACHE.value: {},
    }
    client = esco_client.EscoClient(session_state=session_state)

    with pytest.raises(esco_client.EscoClientError):
        client.terms(uri="occupation:test", type="occupation")
    assert call_counter["count"] == 1

    now["value"] += esco_client.ESCO_NEGATIVE_CACHE_TTL_SECONDS + 1
    with pytest.raises(esco_client.EscoClientError) as exc_info:
        client.terms(uri="occupation:test", type="occupation")
    assert exc_info.value.from_negative_cache is False
    assert call_counter["count"] == 2
