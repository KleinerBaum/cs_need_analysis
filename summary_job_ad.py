"""Pure helpers for generated Summary job ads."""

from __future__ import annotations

import re

from llm_client import JobAdGenerationResult


MARKDOWN_TOKEN_RE = re.compile(r"(\*\*|__|`|^#{1,6}\s*)", re.MULTILINE)


def normalize_list_item(value: str) -> str:
    return re.sub(r"^[\-•*\d\.)\s]+", "", value).strip()


def strip_inline_markdown(value: str) -> str:
    normalized = MARKDOWN_TOKEN_RE.sub("", value)
    normalized = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", normalized)
    return normalized.strip()


def dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in values:
        normalized = strip_inline_markdown(item).strip()
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
        headline=strip_inline_markdown(job_ad.headline),
        target_group=dedupe_preserve_order(
            [*job_ad.target_group, *extracted_target_group]
        ),
        agg_checklist=dedupe_preserve_order(
            [*job_ad.agg_checklist, *extracted_checklist]
        ),
        job_ad_text=strip_inline_markdown("\n".join(body_lines).strip()),
        intro=strip_inline_markdown(job_ad.intro),
        responsibilities=dedupe_preserve_order(job_ad.responsibilities),
        profile=dedupe_preserve_order(job_ad.profile),
        offer=dedupe_preserve_order(job_ad.offer),
        cta=strip_inline_markdown(job_ad.cta),
        equal_opportunity_note=strip_inline_markdown(job_ad.equal_opportunity_note),
    )
    return normalized_job_ad, dedupe_preserve_order(extracted_notes)


def has_structured_job_ad_sections(job_ad: JobAdGenerationResult) -> bool:
    return any(
        (
            job_ad.intro.strip(),
            job_ad.responsibilities,
            job_ad.profile,
            job_ad.offer,
            job_ad.cta.strip(),
            job_ad.equal_opportunity_note.strip(),
        )
    )


def build_publishable_job_ad_markdown(job_ad: JobAdGenerationResult) -> str:
    if not has_structured_job_ad_sections(job_ad):
        return strip_inline_markdown(job_ad.job_ad_text)

    lines: list[str] = []
    headline = strip_inline_markdown(job_ad.headline)
    if headline:
        lines.extend([f"# {headline}", ""])
    if job_ad.intro.strip():
        lines.extend([strip_inline_markdown(job_ad.intro), ""])

    for heading, items in (
        ("Deine Aufgaben", job_ad.responsibilities),
        ("Dein Profil", job_ad.profile),
        ("Was wir bieten", job_ad.offer),
    ):
        clean_items = dedupe_preserve_order(items)
        if not clean_items:
            continue
        lines.extend([f"## {heading}", ""])
        lines.extend(f"- {item}" for item in clean_items)
        lines.append("")

    for value in (job_ad.cta, job_ad.equal_opportunity_note):
        clean_value = strip_inline_markdown(value)
        if clean_value:
            lines.extend([clean_value, ""])

    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines).strip()


def build_publishable_job_ad_plain_text(job_ad: JobAdGenerationResult) -> str:
    markdown = build_publishable_job_ad_markdown(job_ad)
    lines: list[str] = []
    for line in markdown.splitlines():
        if line.startswith("# "):
            lines.append(line[2:].strip())
        elif line.startswith("## "):
            lines.append(line[3:].strip())
        else:
            lines.append(line)
    return "\n".join(lines).strip()


def estimate_text_area_height(text: str) -> int:
    lines = max(1, len(text.splitlines()))
    return min(520, max(160, 40 + lines * 22))
