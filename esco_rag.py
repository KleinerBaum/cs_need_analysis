from __future__ import annotations

from dataclasses import dataclass, replace
import json
import logging
from collections.abc import Sequence
from time import perf_counter
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
    concept_type: str | None = None
    relation_type: str | None = None
    occupation_group: str | None = None
    isco_code: str | None = None
    version: str | None = None
    label_variant: str | None = None
    is_obsolete: bool | None = None
    language_fallback_used: bool | None = None
    lane: str | None = None
    score: float | None = None
    provenance: str = "openai_vector_store"


@dataclass(frozen=True, slots=True)
class EscoRagResult:
    hits: tuple[EscoRagHit, ...]
    provenance: str
    reason: str | None = None
    duration_ms: int | None = None
    search_count: int = 0


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


def _coerce_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"true", "1", "yes", "y"}:
            return True
        if normalized in {"false", "0", "no", "n"}:
            return False
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


def _item_metadata(item: dict[str, Any]) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for key in ("metadata", "attributes"):
        raw = item.get(key)
        if isinstance(raw, dict):
            metadata.update(raw)
    return metadata


def _metadata_string(
    item: dict[str, Any],
    metadata: dict[str, Any],
    *keys: str,
) -> str | None:
    for key in keys:
        value = _coerce_string(item.get(key))
        if value is not None:
            return value
        value = _coerce_string(metadata.get(key))
        if value is not None:
            return value
    return None


def _content_text(item: dict[str, Any]) -> str | None:
    raw_content = item.get("content")
    if not isinstance(raw_content, list):
        return None

    parts: list[str] = []
    for part in raw_content:
        if not isinstance(part, dict):
            continue
        if part.get("type") not in (None, "text"):
            continue
        text = _coerce_string(part.get("text"))
        if text is not None:
            parts.append(text)

    if not parts:
        return None
    return "\n\n".join(parts)


def _extract_hits(items: list[Any]) -> tuple[EscoRagHit, ...]:
    hits: list[EscoRagHit] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        metadata = _item_metadata(item)
        snippet = (
            _coerce_string(item.get("text"))
            or _coerce_string(item.get("snippet"))
            or _content_text(item)
        )
        if snippet is None:
            continue
        source_file = _metadata_string(
            item, metadata, "filename", "source_file", "file_name"
        )
        canonical_source_file, collection, language, skill_type = _infer_source_metadata(
            source_file
        )
        source_title = _metadata_string(item, metadata, "title", "source_title")
        concept_uri = _metadata_string(item, metadata, "concept_uri", "uri")
        preferred_label = _metadata_string(
            item, metadata, "preferred_label", "preferredLabel", "label"
        )
        metadata_collection = _metadata_string(item, metadata, "collection")
        metadata_language = _metadata_string(item, metadata, "language")
        metadata_skill_type = _metadata_string(item, metadata, "skill_type")
        hit = EscoRagHit(
            rank=int(item.get("rank") or index),
            snippet=snippet,
            source_file=canonical_source_file,
            collection=metadata_collection or collection,
            language=metadata_language or language,
            skill_type=metadata_skill_type or skill_type,
            concept_uri=concept_uri,
            preferred_label=preferred_label,
            source_title=source_title,
            concept_type=_metadata_string(item, metadata, "concept_type"),
            relation_type=_metadata_string(item, metadata, "relation_type"),
            occupation_group=_metadata_string(item, metadata, "occupation_group"),
            isco_code=_metadata_string(item, metadata, "isco_code"),
            version=_metadata_string(item, metadata, "version"),
            label_variant=_metadata_string(item, metadata, "label_variant"),
            is_obsolete=_coerce_bool(item.get("is_obsolete"))
            if "is_obsolete" in item
            else _coerce_bool(metadata.get("is_obsolete")),
            language_fallback_used=_coerce_bool(item.get("language_fallback_used"))
            if "language_fallback_used" in item
            else _coerce_bool(metadata.get("language_fallback_used")),
            lane=_metadata_string(item, metadata, "lane"),
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
    concept_type: str | None = None,
    relation_type: str | None = None,
    occupation_group: str | None = None,
    isco_code: str | None = None,
    version: str | None = None,
    source_file: str | None = None,
    label_variant: str | None = None,
    lane: str | None = None,
) -> dict[str, Any]:
    normalized_purpose = (purpose or "").strip()
    if not normalized_purpose:
        raise ValueError("purpose must not be empty")

    clauses = [_eq_filter("purpose", normalized_purpose)]
    optional_filters = (
        ("collection", collection),
        ("language", language),
        ("skill_type", skill_type),
        ("concept_type", concept_type),
        ("relation_type", relation_type),
        ("occupation_group", occupation_group),
        ("isco_code", isco_code),
        ("version", version),
        ("source_file", source_file),
        ("label_variant", label_variant),
        ("lane", lane),
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
    concept_type: str | None = None,
    relation_type: str | None = None,
    occupation_group: str | None = None,
    isco_code: str | None = None,
    version: str | None = None,
    source_file: str | None = None,
    label_variant: str | None = None,
    lane: str | None = None,
) -> EscoRagResult:
    started_at = perf_counter()
    settings = load_openai_settings()
    if not settings.esco_vector_store_id:
        return EscoRagResult(
            hits=(),
            provenance="openai_vector_store",
            reason="disabled",
            duration_ms=0,
        )

    if not settings.esco_rag_enabled:
        return EscoRagResult(
            hits=(),
            provenance="openai_vector_store",
            reason="disabled",
            duration_ms=0,
        )

    limit = max_results or settings.esco_rag_max_results
    client = get_openai_client(settings=settings)
    primary_filters = _build_retrieval_filters(
        purpose=purpose,
        collection=collection,
        language=language,
        skill_type=skill_type,
        concept_type=concept_type,
        relation_type=relation_type,
        occupation_group=occupation_group,
        isco_code=isco_code,
        version=version,
        source_file=source_file,
        label_variant=label_variant,
        lane=lane,
    )
    fallback_filters = _build_retrieval_filters(purpose=purpose)
    search_count = 0
    try:
        response = client.vector_stores.search(
            vector_store_id=settings.esco_vector_store_id,
            query=query,
            max_num_results=limit,
            rewrite_query=False,
            filters=primary_filters,
        )
        search_count += 1
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
            search_count += 1
            data = response.model_dump() if hasattr(response, "model_dump") else {}
            items = data.get("data") if isinstance(data, dict) else []
    except Exception:
        LOGGER.warning("ESCO RAG retrieval failed", exc_info=True)
        return EscoRagResult(
            hits=(),
            provenance="openai_vector_store",
            reason="error",
            duration_ms=int((perf_counter() - started_at) * 1000),
            search_count=search_count,
        )

    hits = _extract_hits(items if isinstance(items, list) else [])
    return EscoRagResult(
        hits=hits,
        provenance="openai_vector_store",
        reason=None,
        duration_ms=int((perf_counter() - started_at) * 1000),
        search_count=search_count,
    )


def retrieve_esco_context_multi(
    queries: Sequence[str],
    *,
    purpose: str,
    max_results: int | None = None,
    collection: str | None = None,
    language: str | None = None,
    skill_type: str | None = None,
    concept_type: str | None = None,
    relation_type: str | None = None,
    occupation_group: str | None = None,
    isco_code: str | None = None,
    version: str | None = None,
    source_file: str | None = None,
    label_variant: str | None = None,
    lane: str | None = None,
) -> EscoRagResult:
    normalized_queries = [
        query.strip()
        for query in dict.fromkeys(str(item or "").strip() for item in queries)
        if query.strip()
    ]
    if not normalized_queries:
        return EscoRagResult(hits=(), provenance="openai_vector_store", reason="empty_query")

    collected: list[EscoRagHit] = []
    first_reason: str | None = None
    total_duration_ms = 0
    total_search_count = 0
    seen: set[tuple[str, str, str | None]] = set()
    for query in normalized_queries:
        result = retrieve_esco_context(
            query,
            purpose=purpose,
            max_results=max_results,
            collection=collection,
            language=language,
            skill_type=skill_type,
            concept_type=concept_type,
            relation_type=relation_type,
            occupation_group=occupation_group,
            isco_code=isco_code,
            version=version,
            source_file=source_file,
            label_variant=label_variant,
            lane=lane,
        )
        if result.reason is not None and first_reason is None:
            first_reason = result.reason
        total_duration_ms += int(result.duration_ms or 0)
        total_search_count += int(result.search_count or 0)
        for hit in result.hits:
            key = (hit.source_file, hit.snippet, hit.concept_uri)
            if key in seen:
                continue
            seen.add(key)
            collected.append(hit)

    ranked = sorted(
        collected,
        key=lambda hit: (-(hit.score if hit.score is not None else 0.0), hit.rank),
    )
    limit = max_results or len(ranked)
    return EscoRagResult(
        hits=tuple(
            replace(hit, rank=index)
            for index, hit in enumerate(ranked[:limit], start=1)
        ),
        provenance="openai_vector_store_multi",
        reason=None if ranked else first_reason,
        duration_ms=total_duration_ms,
        search_count=total_search_count,
    )


def build_esco_rag_evidence_payload(result: EscoRagResult) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for hit in result.hits:
        payload.append(
            {
                "rank": hit.rank,
                "snippet": hit.snippet,
                "source_file": hit.source_file,
                "source_title": hit.source_title or "",
                "collection": hit.collection,
                "language": hit.language,
                "skill_type": hit.skill_type,
                "concept_uri": hit.concept_uri or "",
                "preferred_label": hit.preferred_label or "",
                "score": hit.score,
                "version": hit.version or "",
                "lane": hit.lane or "",
                "provenance": hit.provenance,
            }
        )
    return payload


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
                "source_file": hit.source_file,
                "source_title": hit.source_title or "",
                "concept_uri": hit.concept_uri or uri or "",
            }
        )
    return suggestions
