from __future__ import annotations

from types import SimpleNamespace

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


def test_esco_client_error_is_user_safe() -> None:
    err = esco_client.EscoClientError(
        status_code=503,
        endpoint="search",
        message="ESCO service returned an error response.",
    )

    assert str(err) == "ESCO service returned an error response."
    assert "response" in err.message.lower()


def test_conversion_endpoint_must_not_be_empty() -> None:
    client = esco_client.EscoClient(session_state={SSKey.ESCO_CONFIG.value: {}})

    with pytest.raises(ValueError, match="must not be empty"):
        client.conversion("   ")


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
        "selected_version": "latest",
        "language": "de",
        "view_obsolete": False,
    }


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
