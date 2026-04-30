from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from typing import Any

from llm_client import get_openai_client
from settings_openai import load_openai_settings

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class EscoRagHit:
    rank: int
    snippet: str
    source_file: str
    collection: str
    language: str
    skill_type: str
    concept_uri: str | None = None
    preferred_label: str | None = None
    source_title: str | None = None
    score: float | None = None
    provenance: str = "openai_vector_store"


@dataclass(frozen=True, slots=True)
class EscoRagResult:
    hits: tuple[EscoRagHit, ...]
    provenance: str
    reason: str | None = None


def _coerce_string(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return None


def _coerce_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


_KNOWN_FILENAME_METADATA: dict[str, tuple[str, str, str]] = {
    "occupation_profiles_de.md": ("occupations", "de", "unknown"),
    "occupation_profiles_en.md": ("occupations", "en", "unknown"),
    "skills_essential_de.md": ("skills", "de", "essential"),
    "skills_essential_en.md": ("skills", "en", "essential"),
    "skills_optional_de.md": ("skills", "de", "optional"),
    "skills_optional_en.md": ("skills", "en", "optional"),
    "skills_transversal_de.md": ("skills", "de", "transversal"),
    "skills_transversal_en.md": ("skills", "en", "transversal"),
    "digcompskillscollection_de.md": ("skills", "de", "digital"),
    "transversalskillscollection_de.md": ("skills", "de", "transversal"),
    "languageskillscollection_de.md": ("skills", "de", "language"),
    "researchskillscollection_de.md": ("skills", "de", "research"),
    "researchoccupationscollection_de.md": ("occupations", "de", "research"),
    "skillgroups_de.md": ("taxonomy", "de", "unknown"),
    "iscogroups_de.md": ("taxonomy", "de", "unknown"),
    "dictionary_de.md": ("dictionary", "de", "unknown"),
}


def _infer_source_metadata(source_file: str | None) -> tuple[str, str, str, str]:
    normalized = (source_file or "").strip()
    filename = normalized.rsplit("/", maxsplit=1)[-1].lower() if normalized else ""
    metadata = _KNOWN_FILENAME_METADATA.get(filename)
    if metadata is None:
        return normalized or "unknown", "unknown", "unknown", "unknown"
    collection, language, skill_type = metadata
    return normalized or filename, collection, language, skill_type


def _extract_hits(items: list[Any]) -> tuple[EscoRagHit, ...]:
    hits: list[EscoRagHit] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        snippet = _coerce_string(item.get("text")) or _coerce_string(item.get("snippet"))
        if snippet is None:
            continue
        source_file = _coerce_string(item.get("filename")) or _coerce_string(
            item.get("source_file")
        )
        canonical_source_file, collection, language, skill_type = _infer_source_metadata(
            source_file
        )
        source_title = _coerce_string(item.get("title")) or _coerce_string(
            item.get("source_title")
        )
        concept_uri = _coerce_string(item.get("concept_uri")) or _coerce_string(
            item.get("uri")
        )
        preferred_label = _coerce_string(item.get("preferred_label")) or _coerce_string(
            item.get("label")
        )
        hit = EscoRagHit(
            rank=int(item.get("rank") or index),
            snippet=snippet,
            source_file=canonical_source_file,
            collection=collection,
            language=language,
            skill_type=skill_type,
            concept_uri=concept_uri,
            preferred_label=preferred_label,
            source_title=source_title,
            score=_coerce_float(item.get("score")),
        )
        hits.append(hit)
    return tuple(hits)


def _eq_filter(key: str, value: str) -> dict[str, str]:
    return {"type": "eq", "key": key, "value": value}


def _build_retrieval_filters(
    *,
    purpose: str,
    collection: str | None = None,
    language: str | None = None,
    skill_type: str | None = None,
) -> dict[str, Any]:
    normalized_purpose = (purpose or "").strip()
    if not normalized_purpose:
        raise ValueError("purpose must not be empty")

    clauses = [_eq_filter("purpose", normalized_purpose)]
    optional_filters = (
        ("collection", collection),
        ("language", language),
        ("skill_type", skill_type),
    )
    for key, value in optional_filters:
        normalized = _coerce_string(value)
        if normalized is None:
            continue
        clauses.append(_eq_filter(key, normalized))

    if len(clauses) == 1:
        return clauses[0]
    return {"type": "and", "filters": clauses}


def retrieve_esco_context(
    query: str,
    *,
    purpose: str,
    max_results: int | None = None,
    collection: str | None = None,
    language: str | None = None,
    skill_type: str | None = None,
) -> EscoRagResult:
    settings = load_openai_settings()
    if not settings.esco_vector_store_id:
        return EscoRagResult(hits=(), provenance="openai_vector_store", reason="disabled")

    if not settings.esco_rag_enabled:
        return EscoRagResult(hits=(), provenance="openai_vector_store", reason="disabled")

    limit = max_results or settings.esco_rag_max_results
    client = get_openai_client(settings=settings)
    primary_filters = _build_retrieval_filters(
        purpose=purpose,
        collection=collection,
        language=language,
        skill_type=skill_type,
    )
    fallback_filters = _build_retrieval_filters(purpose=purpose)
    try:
        response = client.vector_stores.search(
            vector_store_id=settings.esco_vector_store_id,
            query=query,
            max_num_results=limit,
            rewrite_query=False,
            filters=primary_filters,
        )
        data = response.model_dump() if hasattr(response, "model_dump") else {}
        items = data.get("data") if isinstance(data, dict) else []

        has_optional_metadata_filters = primary_filters != fallback_filters
        if has_optional_metadata_filters and not items:
            response = client.vector_stores.search(
                vector_store_id=settings.esco_vector_store_id,
                query=query,
                max_num_results=limit,
                rewrite_query=False,
                filters=fallback_filters,
            )
            data = response.model_dump() if hasattr(response, "model_dump") else {}
            items = data.get("data") if isinstance(data, dict) else []
    except Exception:
        LOGGER.warning("ESCO RAG retrieval failed", exc_info=True)
        return EscoRagResult(hits=(), provenance="openai_vector_store", reason="error")

    hits = _extract_hits(items if isinstance(items, list) else [])
    return EscoRagResult(hits=hits, provenance="openai_vector_store", reason=None)


def extract_skill_suggestions(result: EscoRagResult) -> list[dict[str, str]]:
    suggestions: list[dict[str, str]] = []
    for hit in result.hits:
        snippet = hit.snippet.strip()
        if not snippet:
            continue
        payload: dict[str, Any] | None = None
        if snippet.startswith("{"):
            try:
                parsed = json.loads(snippet)
                if isinstance(parsed, dict):
                    payload = parsed
            except Exception:
                payload = None

        if payload is not None:
            label = _coerce_string(
                payload.get("label") or payload.get("preferredLabel") or payload.get("title")
            )
            uri = _coerce_string(payload.get("uri"))
        else:
            label = snippet.split("|")[0].strip()
            uri = None
        if not label:
            continue
        suggestions.append(
            {
                "label": label,
                "uri": uri or "",
                "source": "ESCO RAG",
                "rationale": f"RAG hit #{hit.rank}",
                "evidence": snippet,
            }
        )
    return suggestions
