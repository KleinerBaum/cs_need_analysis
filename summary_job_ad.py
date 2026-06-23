"""Compatibility facade for generated Summary job-ad exports."""

from __future__ import annotations

from exporters.job_ad import (
    MARKDOWN_TOKEN_RE,
    LogoPayload,
    build_publishable_job_ad_markdown,
    build_publishable_job_ad_plain_text,
    dedupe_preserve_order,
    estimate_text_area_height,
    has_structured_job_ad_sections,
    job_ad_preview_html,
    job_ad_preview_shell_options,
    job_ad_to_docx_bytes,
    job_ad_to_pdf_bytes,
    normalize_list_item,
    sanitize_generated_job_ad,
    strip_inline_markdown,
)

__all__ = [
    "MARKDOWN_TOKEN_RE",
    "LogoPayload",
    "build_publishable_job_ad_markdown",
    "build_publishable_job_ad_plain_text",
    "dedupe_preserve_order",
    "estimate_text_area_height",
    "has_structured_job_ad_sections",
    "job_ad_preview_html",
    "job_ad_preview_shell_options",
    "job_ad_to_docx_bytes",
    "job_ad_to_pdf_bytes",
    "normalize_list_item",
    "sanitize_generated_job_ad",
    "strip_inline_markdown",
]
