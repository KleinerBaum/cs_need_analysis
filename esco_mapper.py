"""URI-first ESCO canonical mapper."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Literal, Mapping

from constants import DEFAULT_ESCO_SELECTED_VERSION
from esco_client import EscoClient

EscoConceptKind = Literal["occupation", "skill"]

_MAX_QUERY_LENGTH = 140
_DEFAULT_LANGUAGE = "de"
_DEFAULT_LIMIT = 10
_DEFAULT_HYDRATION_LIMIT = 5

_DE_TO_EN_EXPANSIONS: dict[str, tuple[str, ...]] = {
    "datenanalyst": ("data analyst",),
    "datenanalystin": ("data analyst",),
    "dateningenieur": ("data engineer",),
    "entwickler": ("developer",),
    "entwicklerin": ("developer",),
    "krankenpfleger": ("nurse",),
    "krankenschwester": ("nurse",),
    "pflegefachkraft": ("nurse",),
    "personalreferent": ("hr specialist",),
    "personalreferentin": ("hr specialist",),
    "projektmanager": ("project manager",),
    "projektmanagerin": ("project manager",),
    "rekrutierer": ("recruiter",),
    "rekrutiererin": ("recruiter",),
    "softwareentwickler": ("software developer",),
    "softwareentwicklerin": ("software developer",),
}
_EN_TO_DE_EXPANSIONS: dict[str, tuple[str, ...]] = {
    "data analyst": ("Datenanalyst",),
    "data engineer": ("Dateningenieur",),
    "developer": ("Entwickler",),
    "hr specialist": ("Personalreferent",),
    "nurse": ("Pflegefachkraft",),
    "project manager": ("Projektmanager",),
    "recruiter": ("Rekrutierer",),
    "software developer": ("Softwareentwickler",),
}


@dataclass(frozen=True, slots=True)
class EscoSearchCandidate:
    uri: str
    preferred_label: str
    kind: EscoConceptKind
    rank: int
    query: str
    language: str
    selected_version: str
    raw_score: float | None = None


@dataclass(frozen=True, slots=True)
class EscoMappedConcept:
    uri: str
    preferred_label: str
    kind: EscoConceptKind
    language: str
    selected_version: str
    confidence: float
    query: str
    rank: int
    raw_score: float | None = None
    source: str = "search+resource"
    resource: Mapping[str, Any] | None = None

    def to_persistence_dict(self) -> dict[str, Any]:
        """Return the URI-first payload stored by UI/state/export callers."""

        payload: dict[str, Any] = {
            "uri": self.uri,
            "preferred_label": self.preferred_label,
            "preferredLabel": self.preferred_label,
            "title": self.preferred_label,
            "type": self.kind,
            "language": self.language,
            "selectedVersion": self.selected_version,
            "confidence": self.confidence,
            "source": self.source,
        }
        if self.raw_score is not None:
            payload["raw_score"] = self.raw_score
        return payload


def expand_esco_query(text: str, *, language: str = _DEFAULT_LANGUAGE) -> tuple[str, ...]:
    """Build deterministic bilingual search variants without using deprecated suggest."""

    cleaned = _clean_query(text)
    if not cleaned:
        return ()

    variants: list[str] = [cleaned]
    without_parentheses = _strip_trailing_parenthetical(cleaned)
    if without_parentheses and without_parentheses != cleaned:
        variants.append(without_parentheses)

    normalized_language = str(language or _DEFAULT_LANGUAGE).strip().lower()
    lookup_texts = [cleaned, without_parentheses]
    if normalized_language.startswith("de"):
        _append_dictionary_expansions(
            variants,
            lookup_texts=lookup_texts,
            dictionary=_DE_TO_EN_EXPANSIONS,
        )
    elif normalized_language.startswith("en"):
        _append_dictionary_expansions(
            variants,
            lookup_texts=lookup_texts,
            dictionary=_EN_TO_DE_EXPANSIONS,
        )
    else:
        _append_dictionary_expansions(
            variants,
            lookup_texts=lookup_texts,
            dictionary={**_DE_TO_EN_EXPANSIONS, **_EN_TO_DE_EXPANSIONS},
        )
    return tuple(_dedupe_preserve_order(variants))


def map_esco_concepts(
    text: str,
    *,
    kind: EscoConceptKind = "occupation",
    language: str = _DEFAULT_LANGUAGE,
    selected_version: str = DEFAULT_ESCO_SELECTED_VERSION,
    limit: int = _DEFAULT_LIMIT,
    hydration_limit: int = _DEFAULT_HYDRATION_LIMIT,
    client: EscoClient | None = None,
) -> list[EscoMappedConcept]:
    """Map free text to canonical ESCO resources via /search then /resource/*."""

    if kind not in {"occupation", "skill"}:
        raise ValueError("kind must be 'occupation' or 'skill'")

    mapper_client = client or EscoClient()
    normalized_language = str(language or _DEFAULT_LANGUAGE).strip().lower() or "de"
    normalized_version = (
        str(selected_version or DEFAULT_ESCO_SELECTED_VERSION).strip()
        or DEFAULT_ESCO_SELECTED_VERSION
    )
    candidates = _search_candidates(
        mapper_client,
        text=text,
        kind=kind,
        language=normalized_language,
        selected_version=normalized_version,
        limit=limit,
    )
    ranked_candidates = sorted(
        candidates,
        key=lambda item: _candidate_confidence(text, item.preferred_label, item),
        reverse=True,
    )

    mapped: list[EscoMappedConcept] = []
    seen_uris: set[str] = set()
    for candidate in ranked_candidates[: max(1, hydration_limit)]:
        if candidate.uri in seen_uris:
            continue
        seen_uris.add(candidate.uri)
        resource = _hydrate_resource(
            mapper_client,
            uri=candidate.uri,
            kind=kind,
            language=normalized_language,
            selected_version=normalized_version,
        )
        preferred_label = _preferred_label(resource) or candidate.preferred_label
        mapped.append(
            EscoMappedConcept(
                uri=_resource_uri(resource) or candidate.uri,
                preferred_label=preferred_label,
                kind=kind,
                language=normalized_language,
                selected_version=normalized_version,
                confidence=_candidate_confidence(text, preferred_label, candidate),
                query=candidate.query,
                rank=candidate.rank,
                raw_score=candidate.raw_score,
                resource=resource,
            )
        )

    return sorted(mapped, key=lambda item: item.confidence, reverse=True)


def map_esco_concept(
    text: str,
    *,
    kind: EscoConceptKind = "occupation",
    language: str = _DEFAULT_LANGUAGE,
    selected_version: str = DEFAULT_ESCO_SELECTED_VERSION,
    limit: int = _DEFAULT_LIMIT,
    client: EscoClient | None = None,
) -> EscoMappedConcept | None:
    mapped = map_esco_concepts(
        text,
        kind=kind,
        language=language,
        selected_version=selected_version,
        limit=limit,
        hydration_limit=1,
        client=client,
    )
    return mapped[0] if mapped else None


def _search_candidates(
    client: EscoClient,
    *,
    text: str,
    kind: EscoConceptKind,
    language: str,
    selected_version: str,
    limit: int,
) -> list[EscoSearchCandidate]:
    candidates: list[EscoSearchCandidate] = []
    seen: set[str] = set()
    for query_text in expand_esco_query(text, language=language):
        payload = client.search(
            text=query_text,
            type=kind,
            limit=limit,
            language=language,
            selectedVersion=selected_version,
        )
        for rank, item in enumerate(_extract_search_items(payload, kind=kind), start=1):
            uri = _resource_uri(item)
            label = _preferred_label(item)
            if not uri or not label or uri in seen:
                continue
            seen.add(uri)
            candidates.append(
                EscoSearchCandidate(
                    uri=uri,
                    preferred_label=label,
                    kind=kind,
                    rank=rank,
                    query=query_text,
                    language=language,
                    selected_version=selected_version,
                    raw_score=_numeric_score(item),
                )
            )
    return candidates


def _hydrate_resource(
    client: EscoClient,
    *,
    uri: str,
    kind: EscoConceptKind,
    language: str,
    selected_version: str,
) -> dict[str, Any]:
    if kind == "occupation":
        return client.resource_occupation(
            uri=uri,
            language=language,
            selectedVersion=selected_version,
        )
    return client.resource_skill(
        uri=uri,
        language=language,
        selectedVersion=selected_version,
    )


def _extract_search_items(
    payload: Mapping[str, Any],
    *,
    kind: EscoConceptKind,
) -> list[Mapping[str, Any]]:
    collected: list[Mapping[str, Any]] = []

    embedded = payload.get("_embedded")
    if isinstance(embedded, Mapping):
        for key in ("results", "items"):
            value = embedded.get(key)
            if isinstance(value, list):
                collected.extend(item for item in value if isinstance(item, Mapping))
    for key in ("results", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            collected.extend(item for item in value if isinstance(item, Mapping))
    if _resource_uri(payload):
        collected.append(payload)

    seen: set[str] = set()
    filtered: list[Mapping[str, Any]] = []
    for item in collected:
        uri = _resource_uri(item)
        if not uri or uri in seen:
            continue
        item_type = _concept_type(item)
        if item_type and item_type != kind:
            if f"/{kind}/" not in uri.lower():
                continue
        seen.add(uri)
        filtered.append(item)
    return filtered


def _resource_uri(item: Mapping[str, Any]) -> str:
    uri = item.get("uri") or item.get("conceptUri")
    if isinstance(uri, str) and uri.strip():
        return uri.strip()
    links = item.get("_links")
    if isinstance(links, Mapping):
        self_link = links.get("self")
        if isinstance(self_link, Mapping):
            href = self_link.get("href") or self_link.get("uri")
            if isinstance(href, str) and href.strip():
                return href.strip()
    return ""


def _preferred_label(item: Mapping[str, Any]) -> str:
    for key in ("preferredLabel", "preferred_label", "title", "label", "name"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    preferred_label = item.get("preferredLabel")
    if isinstance(preferred_label, Mapping):
        for value in preferred_label.values():
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def _concept_type(item: Mapping[str, Any]) -> str:
    raw = item.get("type") or item.get("conceptType") or item.get("className")
    return str(raw or "").strip().lower()


def _numeric_score(item: Mapping[str, Any]) -> float | None:
    for key in ("score", "_score", "searchScore"):
        value = item.get(key)
        if isinstance(value, (int, float)):
            return max(0.0, min(float(value), 1.0))
        if isinstance(value, str):
            try:
                return max(0.0, min(float(value), 1.0))
            except ValueError:
                continue
    return None


def _candidate_confidence(
    input_text: str,
    preferred_label: str,
    candidate: EscoSearchCandidate,
) -> float:
    normalized_input = _normalize_for_score(input_text)
    normalized_label = _normalize_for_score(preferred_label)
    normalized_query = _normalize_for_score(candidate.query)
    if not normalized_input or not normalized_label:
        return 0.0

    label_similarity = SequenceMatcher(None, normalized_input, normalized_label).ratio()
    query_similarity = SequenceMatcher(None, normalized_query, normalized_label).ratio()
    token_overlap = _token_overlap(normalized_input, normalized_label)
    raw_score = candidate.raw_score if candidate.raw_score is not None else 0.5
    rank_score = 1.0 / max(candidate.rank, 1)
    confidence = (
        (0.45 * label_similarity)
        + (0.25 * query_similarity)
        + (0.15 * token_overlap)
        + (0.10 * raw_score)
        + (0.05 * rank_score)
    )
    return round(max(0.0, min(confidence, 1.0)), 3)


def _token_overlap(left: str, right: str) -> float:
    left_tokens = set(left.split())
    right_tokens = set(right.split())
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _append_dictionary_expansions(
    variants: list[str],
    *,
    lookup_texts: list[str],
    dictionary: Mapping[str, tuple[str, ...]],
) -> None:
    normalized_lookup = [_normalize_for_score(text) for text in lookup_texts if text]
    exact_matched: set[str] = set()
    for lookup in normalized_lookup:
        for key, expansions in dictionary.items():
            if lookup == _normalize_for_score(key):
                variants.extend(expansions)
                exact_matched.add(lookup)
    for lookup in normalized_lookup:
        if lookup in exact_matched:
            continue
        for key, expansions in dictionary.items():
            normalized_key = _normalize_for_score(key)
            if lookup != normalized_key and normalized_key in lookup:
                variants.extend(expansions)


def _clean_query(text: str) -> str:
    compact = " ".join(str(text or "").split())
    return compact[:_MAX_QUERY_LENGTH].strip()


def _strip_trailing_parenthetical(text: str) -> str:
    return re.sub(r"\s*\([^()]*\)\s*$", "", text).strip()


def _normalize_for_score(text: str) -> str:
    normalized = str(text or "").casefold()
    normalized = re.sub(r"[^a-z0-9äöüß]+", " ", normalized)
    return " ".join(normalized.split())


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        normalized = _normalize_for_score(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(value)
    return deduped
