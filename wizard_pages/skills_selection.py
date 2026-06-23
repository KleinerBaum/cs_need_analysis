from __future__ import annotations

from typing import Any

from job_extract_review_helpers import has_meaningful_value


def _normalize_term(term: str) -> str:
    return " ".join(term.strip().casefold().split())


def _dedupe_terms(values: list[str]) -> list[str]:
    unique_terms: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not has_meaningful_value(value):
            continue
        normalized = _normalize_term(value)
        if not normalized or normalized in seen:
            continue
        unique_terms.append(value.strip())
        seen.add(normalized)
    return unique_terms


def _dedupe_selected_skills_across_buckets(
    must_selected: list[dict[str, Any]],
    nice_selected: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    seen_uris: set[str] = set()
    seen_labels: set[str] = set()
    deduped_must: list[dict[str, Any]] = []
    deduped_nice: list[dict[str, Any]] = []

    def _is_duplicate(item: dict[str, Any]) -> bool:
        uri = str(item.get("uri") or "").strip()
        normalized_label = _normalize_term(
            str(
                item.get("title")
                or item.get("label")
                or item.get("preferredLabel")
                or ""
            )
        )
        duplicate_uri = uri and uri in seen_uris
        duplicate_label = normalized_label and normalized_label in seen_labels
        if duplicate_uri or duplicate_label:
            return True
        if uri:
            seen_uris.add(uri)
        if normalized_label:
            seen_labels.add(normalized_label)
        return False

    for item in must_selected:
        if _is_duplicate(item):
            continue
        deduped_must.append(item)
    for item in nice_selected:
        if _is_duplicate(item):
            continue
        deduped_nice.append(item)
    return deduped_must, deduped_nice


def _merge_suggested_skills_by_uri(
    *,
    suggested_skills: list[dict[str, Any]],
    must_selected: list[dict[str, Any]],
    nice_selected: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    existing_uris = {
        str(item.get("uri") or "").strip()
        for item in (must_selected + nice_selected)
        if str(item.get("uri") or "").strip()
    }
    existing_labels = {
        _normalize_term(str(item.get("title") or item.get("label") or ""))
        for item in (must_selected + nice_selected)
        if _normalize_term(str(item.get("title") or item.get("label") or ""))
    }
    merged: list[dict[str, Any]] = list(must_selected)
    added_count = 0
    for item in suggested_skills:
        uri = str(item.get("uri") or "").strip()
        normalized_label = _normalize_term(
            str(item.get("title") or item.get("label") or "")
        )
        duplicate_uri = uri and uri in existing_uris
        duplicate_label = normalized_label and normalized_label in existing_labels
        if duplicate_uri or duplicate_label:
            continue
        if not uri and not normalized_label:
            continue
        merged.append(item)
        if uri:
            existing_uris.add(uri)
        if normalized_label:
            existing_labels.add(normalized_label)
        added_count += 1
    return merged, added_count


def _merge_llm_skill_suggestions(
    *,
    llm_skills: list[dict[str, Any]],
    blocked_labels: list[str],
) -> list[dict[str, Any]]:
    accepted: list[dict[str, Any]] = []
    seen_uris: set[str] = set()
    seen = {
        _normalize_term(label)
        for label in blocked_labels
        if has_meaningful_value(label)
    }
    for item in llm_skills:
        label = str(item.get("label") or "").strip()
        uri = str(item.get("uri") or "").strip()
        normalized = _normalize_term(label)
        if (uri and uri in seen_uris) or not normalized or normalized in seen:
            continue
        accepted.append(
            {
                "label": label,
                "uri": uri,
                "source": str(item.get("source") or "AI suggestion").strip(),
                "source_hint": str(item.get("source_hint") or "llm").strip()
                or "llm",
                "source_file": str(item.get("source_file") or "").strip(),
                "concept_uri": str(item.get("concept_uri") or uri).strip(),
                "importance": str(item.get("importance") or "").strip(),
                "rationale": str(item.get("rationale") or "").strip(),
                "evidence": str(item.get("evidence") or "").strip(),
            }
        )
        seen.add(normalized)
        if uri:
            seen_uris.add(uri)
    return accepted
