from __future__ import annotations

import logging
from types import SimpleNamespace

import esco_rag


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def model_dump(self):
        return self._payload


def test_retrieve_esco_context_disabled_when_vector_store_missing(monkeypatch) -> None:
    settings = SimpleNamespace(
        esco_vector_store_id=None,
        esco_rag_enabled=True,
        esco_rag_max_results=8,
    )
    monkeypatch.setattr(esco_rag, "load_openai_settings", lambda: settings)

    result = esco_rag.retrieve_esco_context("python", purpose="skills")

    assert result.reason == "disabled"
    assert result.hits == ()


def test_retrieve_esco_context_success(monkeypatch) -> None:
    settings = SimpleNamespace(
        esco_vector_store_id="vs_123",
        esco_rag_enabled=True,
        esco_rag_max_results=3,
    )
    calls: dict[str, object] = {}

    class _VectorStores:
        def search(self, **kwargs):
            calls.update(kwargs)
            return _FakeResponse(
                {
                    "data": [
                        {
                            "text": "Essential skill: Python",
                            "filename": "skills.jsonl",
                            "title": "Python skill",
                            "score": 0.95,
                            "rank": 1,
                        }
                    ]
                }
            )

    monkeypatch.setattr(esco_rag, "load_openai_settings", lambda: settings)
    monkeypatch.setattr(
        esco_rag,
        "get_openai_client",
        lambda *, settings: SimpleNamespace(vector_stores=_VectorStores()),
    )

    result = esco_rag.retrieve_esco_context("python", purpose="skills")

    assert result.reason is None
    assert len(result.hits) == 1
    assert result.hits[0].source_file == "skills.jsonl"
    assert calls["max_num_results"] == 3


def test_retrieve_esco_context_error_fallback_and_no_sensitive_logging(
    monkeypatch, caplog
) -> None:
    settings = SimpleNamespace(
        esco_vector_store_id="vs_123",
        esco_rag_enabled=True,
        esco_rag_max_results=3,
    )

    class _VectorStores:
        def search(self, **kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr(esco_rag, "load_openai_settings", lambda: settings)
    monkeypatch.setattr(
        esco_rag,
        "get_openai_client",
        lambda *, settings: SimpleNamespace(vector_stores=_VectorStores()),
    )

    with caplog.at_level(logging.WARNING):
        result = esco_rag.retrieve_esco_context(
            "john.doe@example.com salary", purpose="skills"
        )

    assert result.reason == "error"
    assert all("john.doe@example.com" not in rec.message for rec in caplog.records)
