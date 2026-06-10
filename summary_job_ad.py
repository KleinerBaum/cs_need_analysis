"""Pure helpers for generated Summary job ads."""

from __future__ import annotations

import re

from llm_client import JobAdGenerationResult


def normalize_list_item(value: str) -> str:
    return re.sub(r"^[\-•*\d\.)\s]+", "", value).strip()


def dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in values:
        normalized = item.strip()
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


def sanitize_generated_job_ad(
    job_ad: JobAdGenerationResult,
) -> tuple[JobAdGenerationResult, list[str]]:
    body_lines: list[str] = []
    extracted_target_group: list[str] = []
    extracted_checklist: list[str] = []
    extracted_notes: list[str] = []

    section = "body"
    for raw_line in job_ad.job_ad_text.splitlines():
        line = raw_line.strip()
        if not line:
            if section == "body":
                body_lines.append("")
            continue

        lowered = line.rstrip(":").strip().casefold()
        if lowered == "zielgruppe":
            section = "target_group"
            continue
        if lowered in {"agg-checkliste", "agg checkliste"}:
            section = "agg_checklist"
            continue

        if line.casefold().startswith("hinweis:"):
            extracted_notes.append(line.split(":", 1)[1].strip())
            continue

        normalized_item = normalize_list_item(line)
        if section == "target_group":
            if normalized_item:
                extracted_target_group.append(normalized_item)
            continue
        if section == "agg_checklist":
            if normalized_item:
                extracted_checklist.append(normalized_item)
            continue

        body_lines.append(raw_line.rstrip())

    while body_lines and not body_lines[-1].strip():
        body_lines.pop()

    normalized_job_ad = JobAdGenerationResult(
        headline=job_ad.headline.strip(),
        target_group=dedupe_preserve_order(
            [*job_ad.target_group, *extracted_target_group]
        ),
        agg_checklist=dedupe_preserve_order(
            [*job_ad.agg_checklist, *extracted_checklist]
        ),
        job_ad_text="\n".join(body_lines).strip(),
    )
    return normalized_job_ad, dedupe_preserve_order(extracted_notes)


def estimate_text_area_height(text: str) -> int:
    lines = max(1, len(text.splitlines()))
    return min(520, max(160, 40 + lines * 22))
