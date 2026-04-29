from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from llm_client import get_openai_client
from settings_openai import load_openai_settings

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class EscoRagHit:
    rank: int
    snippet: str
    source_file: str | None = None
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
        source_title = _coerce_string(item.get("title")) or _coerce_string(
            item.get("source_title")
        )
        hit = EscoRagHit(
            rank=int(item.get("rank") or index),
            snippet=snippet,
            source_file=source_file,
            source_title=source_title,
            score=_coerce_float(item.get("score")),
        )
        hits.append(hit)
    return tuple(hits)


def retrieve_esco_context(
    query: str,
    *,
    purpose: str,
    max_results: int | None = None,
) -> EscoRagResult:
    settings = load_openai_settings()
    if not settings.esco_vector_store_id:
        return EscoRagResult(hits=(), provenance="openai_vector_store", reason="disabled")

    if not settings.esco_rag_enabled:
        return EscoRagResult(hits=(), provenance="openai_vector_store", reason="disabled")

    limit = max_results or settings.esco_rag_max_results
    client = get_openai_client(settings=settings)
    try:
        response = client.vector_stores.search(
            vector_store_id=settings.esco_vector_store_id,
            query=query,
            max_num_results=limit,
            rewrite_query=False,
            filters={"type": "eq", "key": "purpose", "value": purpose},
        )
    except Exception:
        LOGGER.warning("ESCO RAG retrieval failed", exc_info=True)
        return EscoRagResult(hits=(), provenance="openai_vector_store", reason="error")

    data = response.model_dump() if hasattr(response, "model_dump") else {}
    items = data.get("data") if isinstance(data, dict) else []
    hits = _extract_hits(items if isinstance(items, list) else [])
    return EscoRagResult(hits=hits, provenance="openai_vector_store", reason=None)
