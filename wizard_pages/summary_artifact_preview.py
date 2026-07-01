"""Summary artifact preview and download rendering helpers."""

from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

import streamlit as st

from components.design_system import (
    render_card_start,
    render_critical_gaps,
    render_output_header,
    render_pill,
)
from document_preview import document_preview_shell
from llm_client import JobAdGenerationResult
from safe_html import render_static_html
from summary_job_ad import (
    build_publishable_job_ad_markdown,
    dedupe_preserve_order,
)
from ux_copy_contract import summary_export_copy
from wizard_pages.summary_exporters import (
    _job_ad_logo_payload,
    _job_ad_preview_html,
    _job_ad_preview_shell_options,
    _job_ad_to_docx_bytes,
    _job_ad_to_pdf_bytes,
)


def is_warning_checklist_item(item: str) -> bool:
    normalized = item.strip().lower()
    if not normalized:
        return False
    warning_tokens = ("fehlt", "nicht", "missing", "kritisch")
    return any(token in normalized for token in warning_tokens)


def render_agg_checklist_review(
    items: Sequence[str],
    *,
    streamlit_module: Any = st,
    render_pill_fn: Callable[..., None] = render_pill,
) -> None:
    if not items:
        streamlit_module.caption("Keine AGG-Checkliste hinterlegt.")
        return
    for raw_item in items:
        item = str(raw_item).strip()
        if not item:
            continue
        if is_warning_checklist_item(item):
            render_pill_fn(item, tone="warning")
        else:
            render_pill_fn(item, tone="neutral")


def render_job_ad_artifact(
    custom_job_ad_raw: dict[str, Any],
    *,
    streamlit_module: Any = st,
    render_output_header_fn: Callable[..., None] = render_output_header,
    render_card_start_fn: Callable[..., None] = render_card_start,
    job_ad_to_docx_bytes_fn: Callable[..., bytes] = _job_ad_to_docx_bytes,
    job_ad_to_pdf_bytes_fn: Callable[..., bytes | None] = _job_ad_to_pdf_bytes,
    final_export_available: bool = True,
    final_export_pause_renderer: Callable[[], None] | None = None,
    language: str | None = None,
) -> None:
    custom_job_ad = JobAdGenerationResult.model_validate(
        {
            "headline": custom_job_ad_raw.get("headline", ""),
            "target_group": custom_job_ad_raw.get("target_group", []),
            "agg_checklist": custom_job_ad_raw.get("agg_checklist", []),
            "job_ad_text": custom_job_ad_raw.get("job_ad_text", ""),
            "intro": custom_job_ad_raw.get("intro", ""),
            "responsibilities": custom_job_ad_raw.get("responsibilities", []),
            "profile": custom_job_ad_raw.get("profile", []),
            "offer": custom_job_ad_raw.get("offer", []),
            "cta": custom_job_ad_raw.get("cta", ""),
            "equal_opportunity_note": custom_job_ad_raw.get(
                "equal_opportunity_note", ""
            ),
        }
    )
    export_title = summary_export_copy("job_ad_title", language=language)
    publishable_markdown = build_publishable_job_ad_markdown(
        custom_job_ad,
        language=language,
    )
    logo_payload = _job_ad_logo_payload(custom_job_ad_raw)
    preview_options_raw = custom_job_ad_raw.get("preview_options")
    preview_options = (
        preview_options_raw if isinstance(preview_options_raw, Mapping) else {}
    )
    shell_options = _job_ad_preview_shell_options(preview_options)
    render_output_header_fn(
        custom_job_ad.headline or export_title,
        "Generierte Stellenanzeige mit Zielgruppen- und AGG-Hinweisen.",
    )
    render_card_start_fn("cs-card cs-result-card")
    streamlit_module.markdown("### Ergebnis")
    render_static_html(
        document_preview_shell(
            _job_ad_preview_html(
                custom_job_ad,
                logo_payload=logo_payload,
                language=language,
            ),
            title=export_title,
            fit_pages=True,
            **shell_options,
        ),
        streamlit_module=streamlit_module,
    )
    render_static_html("</section>", streamlit_module=streamlit_module)

    render_card_start_fn("cs-card cs-result-card")
    streamlit_module.markdown("### Prüfung")
    streamlit_module.markdown("**Zielgruppe**")
    if custom_job_ad.target_group:
        for index, group in enumerate(custom_job_ad.target_group):
            render_pill(group, tone="primary" if index == 0 else "neutral")
    else:
        streamlit_module.caption("Keine Zielgruppe hinterlegt.")
    streamlit_module.markdown("**AGG-Checkliste**")
    render_agg_checklist_review(
        custom_job_ad.agg_checklist,
        streamlit_module=streamlit_module,
    )
    critical_gaps_raw = custom_job_ad_raw.get("critical_gaps")
    critical_gaps: list[str] = []
    if isinstance(critical_gaps_raw, list):
        critical_gaps.extend(
            str(note).strip() for note in critical_gaps_raw if str(note).strip()
        )
    generation_notes = custom_job_ad_raw.get("generation_notes", [])
    if isinstance(generation_notes, list):
        critical_gaps.extend(
            str(note).strip() for note in generation_notes if str(note).strip()
        )
    critical_gaps = dedupe_preserve_order(critical_gaps)
    if critical_gaps:
        render_critical_gaps(critical_gaps, title="Kritische Lücken")
    render_static_html("</section>", streamlit_module=streamlit_module)

    render_card_start_fn("cs-card cs-result-card")
    streamlit_module.markdown("### Export")
    if not final_export_available:
        if final_export_pause_renderer is not None:
            final_export_pause_renderer()
        else:
            streamlit_module.caption("Finalexport pausiert.")
        render_static_html("</section>", streamlit_module=streamlit_module)
        return
    custom_docx = job_ad_to_docx_bytes_fn(
        custom_job_ad,
        logo_payload=logo_payload,
        language=language,
    )
    custom_pdf = job_ad_to_pdf_bytes_fn(
        custom_job_ad,
        logo_payload=logo_payload,
        language=language,
    )
    custom_md = publishable_markdown.encode("utf-8")
    export_columns = streamlit_module.columns(2)
    with export_columns[0]:
        streamlit_module.download_button(
            "Stellenanzeige herunterladen (DOCX)",
            data=custom_docx,
            file_name="stellenanzeige.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    with export_columns[1]:
        if custom_pdf is None:
            streamlit_module.caption("PDF-Export benötigt reportlab (nicht verfügbar).")
        else:
            streamlit_module.download_button(
                "Stellenanzeige herunterladen (PDF)",
                data=custom_pdf,
                file_name="stellenanzeige.pdf",
                mime="application/pdf",
            )
    with export_columns[0]:
        streamlit_module.download_button(
            "Stellenanzeige herunterladen (Markdown)",
            data=custom_md,
            file_name="stellenanzeige.md",
            mime="text/markdown",
        )
    render_static_html("</section>", streamlit_module=streamlit_module)
