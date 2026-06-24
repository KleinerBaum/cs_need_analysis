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
        concept_type="skill",
        version="v1.2.1",
        lane="preview",
    )

    assert filters["type"] == "and"
    assert filters["filters"] == [
        {"type": "eq", "key": "purpose", "value": "skills"},
        {"type": "eq", "key": "collection", "value": "skills"},
        {"type": "eq", "key": "language", "value": "de"},
        {"type": "eq", "key": "skill_type", "value": "essential"},
        {"type": "eq", "key": "concept_type", "value": "skill"},
        {"type": "eq", "key": "version", "value": "v1.2.1"},
        {"type": "eq", "key": "lane", "value": "preview"},
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


def test_extract_hits_reads_current_vector_store_content_shape() -> None:
    hits = esco_rag._extract_hits(
        [
            {
                "filename": "skills_essential_en.md",
                "score": 0.91,
                "content": [
                    {"type": "text", "text": "Relevant chunk"},
                    {"type": "text", "text": "Second chunk"},
                ],
                "attributes": {
                    "preferred_label": "Python",
                    "concept_uri": "http://data.europa.eu/esco/skill/123",
                },
            }
        ]
    )

    assert len(hits) == 1
    assert hits[0].snippet == "Relevant chunk\n\nSecond chunk"
    assert hits[0].source_file == "skills_essential_en.md"
    assert hits[0].preferred_label == "Python"
    assert hits[0].concept_uri == "http://data.europa.eu/esco/skill/123"


def test_extract_hits_reads_typed_metadata_from_attributes() -> None:
    hits = esco_rag._extract_hits(
        [
            {
                "text": "Skill row",
                "attributes": {
                    "source_file": "skills_custom.md",
                    "collection": "skills",
                    "language": "de",
                    "skill_type": "essential",
                    "concept_type": "skill",
                    "relation_type": "essentialSkill",
                    "occupation_group": "251",
                    "isco_code": "2512",
                    "version": "v1.2.1",
                    "label_variant": "preferred",
                    "is_obsolete": "false",
                    "language_fallback_used": "true",
                    "lane": "preview",
                },
            }
        ]
    )

    assert hits[0].source_file == "skills_custom.md"
    assert hits[0].collection == "skills"
    assert hits[0].language == "de"
    assert hits[0].skill_type == "essential"
    assert hits[0].concept_type == "skill"
    assert hits[0].relation_type == "essentialSkill"
    assert hits[0].isco_code == "2512"
    assert hits[0].version == "v1.2.1"
    assert hits[0].is_obsolete is False
    assert hits[0].language_fallback_used is True
    assert hits[0].lane == "preview"


def test_retrieve_esco_context_multi_dedupes_and_ranks(monkeypatch) -> None:
    def _fake_retrieve(query: str, **_kwargs):
        if query == "title":
            return esco_rag.EscoRagResult(
                hits=(
                    esco_rag.EscoRagHit(
                        rank=1,
                        snippet="A",
                        source_file="a.md",
                        collection="skills",
                        language="de",
                        skill_type="essential",
                        score=0.6,
                    ),
                ),
                provenance="openai_vector_store",
            )
        return esco_rag.EscoRagResult(
            hits=(
                esco_rag.EscoRagHit(
                    rank=1,
                    snippet="A",
                    source_file="a.md",
                    collection="skills",
                    language="de",
                    skill_type="essential",
                    score=0.6,
                ),
                esco_rag.EscoRagHit(
                    rank=2,
                    snippet="B",
                    source_file="b.md",
                    collection="skills",
                    language="de",
                    skill_type="optional",
                    score=0.9,
                ),
            ),
            provenance="openai_vector_store",
        )

    monkeypatch.setattr(esco_rag, "retrieve_esco_context", _fake_retrieve)

    result = esco_rag.retrieve_esco_context_multi(
        ["title", "title + skills"], purpose="skills", max_results=2
    )

    assert result.provenance == "openai_vector_store_multi"
    assert [hit.snippet for hit in result.hits] == ["B", "A"]
    assert [hit.rank for hit in result.hits] == [1, 2]


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
