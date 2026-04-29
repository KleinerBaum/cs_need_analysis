from __future__ import annotations

from settings_openai import DEFAULT_TIMEOUT_SECONDS, load_openai_settings


def test_openai_settings_esco_rag_defaults_without_env(monkeypatch) -> None:
    monkeypatch.delenv("ESCO_VECTOR_STORE_ID", raising=False)
    monkeypatch.delenv("ESCO_RAG_ENABLED", raising=False)
    monkeypatch.delenv("ESCO_RAG_MAX_RESULTS", raising=False)

    settings = load_openai_settings()

    assert settings.esco_vector_store_id is None
    assert settings.esco_rag_enabled is False
    assert settings.esco_rag_max_results == 8


def test_openai_settings_esco_rag_env_resolution(monkeypatch) -> None:
    monkeypatch.setenv("ESCO_VECTOR_STORE_ID", "vs_abc123")
    monkeypatch.setenv("ESCO_RAG_ENABLED", "true")
    monkeypatch.setenv("ESCO_RAG_MAX_RESULTS", "12")

    settings = load_openai_settings()

    assert settings.esco_vector_store_id == "vs_abc123"
    assert settings.esco_rag_enabled is True
    assert settings.esco_rag_max_results == 12


def test_openai_settings_esco_rag_disabled_when_vector_store_missing(monkeypatch) -> None:
    monkeypatch.delenv("ESCO_VECTOR_STORE_ID", raising=False)
    monkeypatch.setenv("ESCO_RAG_ENABLED", "true")

    settings = load_openai_settings()

    assert settings.esco_vector_store_id is None
    assert settings.esco_rag_enabled is False


def test_openai_settings_timeout_still_uses_default(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_REQUEST_TIMEOUT", "")

    settings = load_openai_settings()

    assert settings.openai_request_timeout == DEFAULT_TIMEOUT_SECONDS
