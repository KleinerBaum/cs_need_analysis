"""Data shaping helpers for the Skills selection board."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping


NormalizeTermFn = Callable[[str], str]
SkillTitleFn = Callable[[dict[str, Any]], str]
SkillUriFn = Callable[[dict[str, Any]], str]
DedupeTermsFn = Callable[[list[str]], list[str]]
FreeStatusKeyFn = Callable[[str, str], str]
HasMeaningfulValueFn = Callable[[object], bool]
DedupeSelectedSkillsFn = Callable[
    [list[dict[str, Any]], list[dict[str, Any]]],
    tuple[list[dict[str, Any]], list[dict[str, Any]]],
]


@dataclass(frozen=True)
class SkillsSourceViewData:
    jobspec_terms: list[str]
    jobspec_suggestions: list[dict[str, str]]
    llm_labels: list[str]
    esco_labels: list[str]
    deduped_must: list[dict[str, Any]]
    deduped_nice: list[dict[str, Any]]
    llm_suggested: list[Any]


def llm_skill_label(item: dict[str, Any]) -> str:
    return str(item.get("label") or item.get("title") or "").strip()


def build_skills_source_view_data(
    *,
    job: Any,
    show_esco_sections: bool,
    llm_raw: object,
    selected_must_raw: object,
    selected_nice_raw: object,
    has_meaningful_value: HasMeaningfulValueFn,
    dedupe_terms: DedupeTermsFn,
    dedupe_selected_skills_across_buckets: DedupeSelectedSkillsFn,
) -> SkillsSourceViewData:
    jobspec_terms = dedupe_terms(
        [
            *[x for x in job.must_have_skills if has_meaningful_value(x)],
            *[x for x in job.nice_to_have_skills if has_meaningful_value(x)],
            *[x for x in job.tech_stack if has_meaningful_value(x)],
        ]
    )
    jobspec_suggestions = [
        {"label": term, "source": "Jobspec"} for term in jobspec_terms
    ]

    llm_suggested = llm_raw if isinstance(llm_raw, list) else []
    llm_labels = dedupe_terms(
        [
            str(item.get("label") or "").strip()
            for item in llm_suggested
            if isinstance(item, dict)
        ]
    )

    selected_must = selected_must_raw if isinstance(selected_must_raw, list) else []
    selected_nice = selected_nice_raw if isinstance(selected_nice_raw, list) else []
    deduped_must, deduped_nice = dedupe_selected_skills_across_buckets(
        selected_must,
        selected_nice,
    )
    esco_labels = (
        dedupe_terms(
            [
                str(item.get("title") or "").strip()
                for item in (deduped_must + deduped_nice)
            ]
        )
        if show_esco_sections
        else []
    )
    return SkillsSourceViewData(
        jobspec_terms=jobspec_terms,
        jobspec_suggestions=jobspec_suggestions,
        llm_labels=llm_labels,
        esco_labels=esco_labels,
        deduped_must=deduped_must,
        deduped_nice=deduped_nice,
        llm_suggested=llm_suggested,
    )


def build_llm_skill_groups(
    *,
    llm_suggested: list[dict[str, Any]],
    tech_stack_terms: list[str],
    blocked_labels: set[str],
    normalize_term: NormalizeTermFn,
    dedupe_terms: DedupeTermsFn,
) -> dict[str, list[str]]:
    tech_stack_normalized = {normalize_term(term) for term in tech_stack_terms}
    groups: dict[str, list[str]] = {
        "Must-have": [],
        "Nice-to-have": [],
        "Tech Stack": [],
    }
    for item in llm_suggested:
        if not isinstance(item, dict):
            continue
        label = llm_skill_label(item)
        normalized = normalize_term(label)
        if not normalized or normalized in blocked_labels:
            continue
        if normalized in tech_stack_normalized:
            groups["Tech Stack"].append(label)
            continue
        importance = str(item.get("importance") or "").strip().casefold()
        target_group = "Must-have" if importance == "high" else "Nice-to-have"
        groups[target_group].append(label)
    return {title: dedupe_terms(values) for title, values in groups.items()}


def jobspec_board_items(skill_groups: Mapping[str, list[str]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for group, labels in skill_groups.items():
        status = "must" if group == "Must-have" else "nice"
        for label in labels:
            items.append(
                {
                    "label": label,
                    "importance": group,
                    "source": "Jobspec",
                    "status": status,
                }
            )
    return items


def esco_board_items(
    *,
    selected_must: list[dict[str, Any]],
    selected_nice: list[dict[str, Any]],
    recommended_must: list[dict[str, Any]],
    recommended_nice: list[dict[str, Any]],
    skill_title: SkillTitleFn,
    skill_uri: SkillUriFn,
    normalize_term: NormalizeTermFn,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for status, rows in (
        ("must", selected_must),
        ("nice", selected_nice),
        ("must", recommended_must),
        ("nice", recommended_nice),
    ):
        for item in rows:
            if not isinstance(item, dict):
                continue
            label = skill_title(item)
            uri = skill_uri(item)
            key = uri or normalize_term(label)
            if not key or key in seen:
                continue
            row = dict(item)
            row["label"] = label
            row["title"] = label
            row["status"] = status
            row["importance"] = "Must-have" if status == "must" else "Nice-to-have"
            row["source"] = str(row.get("source") or "ESCO").strip() or "ESCO"
            items.append(row)
            seen.add(key)
    return items


def llm_board_items(llm_suggested: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for item in llm_suggested:
        if not isinstance(item, dict):
            continue
        label = llm_skill_label(item)
        if not label:
            continue
        importance = str(item.get("importance") or "").strip()
        items.append(
            {
                **item,
                "label": label,
                "source": "AI",
                "status": "must" if importance.casefold() == "high" else "nice",
            }
        )
    return items


def label_lookup(
    items: list[dict[str, Any]],
    *,
    normalize_term: NormalizeTermFn,
) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for item in items:
        label = str(item.get("label") or item.get("title") or "").strip()
        normalized = normalize_term(label)
        if normalized and normalized not in lookup:
            lookup[normalized] = item
    return lookup


def status_from_candidate(item: dict[str, Any], *, fallback: str = "nice") -> str:
    status = str(item.get("status") or "").strip().casefold()
    if status in {"must", "nice"}:
        return status
    importance = str(item.get("importance") or "").strip().casefold()
    if importance in {"must-have", "must", "high", "hoch", "critical", "kritisch"}:
        return "must"
    return fallback


def count_selected_sources(
    *,
    selected_labels: list[str],
    jobspec_items: list[dict[str, Any]],
    esco_items: list[dict[str, Any]],
    llm_items: list[dict[str, Any]],
    free_statuses: Mapping[str, Mapping[str, str]],
    normalize_term: NormalizeTermFn,
    free_skill_status_key: FreeStatusKeyFn,
) -> dict[str, int]:
    jobspec_lookup = label_lookup(jobspec_items, normalize_term=normalize_term)
    esco_lookup = label_lookup(esco_items, normalize_term=normalize_term)
    llm_lookup = label_lookup(llm_items, normalize_term=normalize_term)
    counts = {"Jobspec": 0, "ESCO / Kontext": 0, "AI": 0}
    for label in selected_labels:
        normalized = normalize_term(label)
        status = free_statuses.get(free_skill_status_key(label, ""))
        source = str((status or {}).get("source") or "").strip().casefold()
        if normalized in esco_lookup or source == "esco":
            counts["ESCO / Kontext"] += 1
        elif source == "ai" or normalized in llm_lookup:
            counts["AI"] += 1
        elif source == "jobspec" or normalized in jobspec_lookup:
            counts["Jobspec"] += 1
        else:
            counts["Jobspec"] += 1
    return counts
