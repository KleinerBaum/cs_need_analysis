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

    result = esco_rag.retrieve_esco_context(
        "python",
        purpose="skills",
        collection="skills",
    )

    assert result.reason is None
    assert len(result.hits) == 1
    assert result.hits[0].source_file == "skills.jsonl"
    assert result.hits[0].collection == "unknown"
    assert result.hits[0].language == "unknown"
    assert result.hits[0].skill_type == "unknown"
    assert calls["max_num_results"] == 3
    assert calls["filters"]["type"] == "and"


def test_build_retrieval_filters_minimal() -> None:
    filters = esco_rag._build_retrieval_filters(purpose="skills")

    assert filters == {"type": "eq", "key": "purpose", "value": "skills"}


def test_build_retrieval_filters_with_optional_metadata() -> None:
    filters = esco_rag._build_retrieval_filters(
        purpose="skills",
        collection="skills",
        language="de",
        skill_type="essential",
    )

    assert filters["type"] == "and"
    assert filters["filters"] == [
        {"type": "eq", "key": "purpose", "value": "skills"},
        {"type": "eq", "key": "collection", "value": "skills"},
        {"type": "eq", "key": "language", "value": "de"},
        {"type": "eq", "key": "skill_type", "value": "essential"},
    ]


def test_retrieve_esco_context_retries_without_hard_metadata_filters(monkeypatch) -> None:
    settings = SimpleNamespace(
        esco_vector_store_id="vs_123",
        esco_rag_enabled=True,
        esco_rag_max_results=3,
    )
    search_calls: list[dict[str, object]] = []

    class _VectorStores:
        def search(self, **kwargs):
            search_calls.append(kwargs)
            if len(search_calls) == 1:
                return _FakeResponse({"data": []})
            return _FakeResponse(
                {
                    "data": [
                        {
                            "text": "Fallback skill hit",
                            "filename": "skills_essential_en.md",
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

    result = esco_rag.retrieve_esco_context(
        "python",
        purpose="skills",
        collection="skills",
    )

    assert result.reason is None
    assert len(result.hits) == 1
    assert len(search_calls) == 2
    assert search_calls[0]["filters"]["type"] == "and"
    assert search_calls[1]["filters"] == {
        "type": "eq",
        "key": "purpose",
        "value": "skills",
    }


def test_extract_hits_infers_known_filename_metadata() -> None:
    hits = esco_rag._extract_hits(
        [
            {
                "text": "Skill row",
                "filename": "skills_essential_en.md",
                "concept_uri": "http://data.europa.eu/esco/skill/123",
                "preferred_label": "Python",
                "score": 0.88,
            }
        ]
    )

    assert hits[0].source_file == "skills_essential_en.md"
    assert hits[0].collection == "skills"
    assert hits[0].language == "en"
    assert hits[0].skill_type == "essential"
    assert hits[0].concept_uri == "http://data.europa.eu/esco/skill/123"
    assert hits[0].preferred_label == "Python"


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
