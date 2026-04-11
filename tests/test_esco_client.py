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
