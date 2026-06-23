"""Evidence and trust rendering helpers for reviewed job extracts."""

from __future__ import annotations

from contextlib import nullcontext
from typing import Any

import streamlit as st

from job_extract_evidence import job_extract_field_evidence_by_name
from job_extract_review_helpers import JOB_EXTRACT_DISPLAY_LABELS
from schemas import JobAdExtract


def evidence_confidence(evidence: Any) -> float | None:
    if not isinstance(evidence, dict):
        return None
    try:
        return max(0.0, min(1.0, float(evidence.get("confidence"))))
    except (TypeError, ValueError):
        return None


def source_bucket_preview(items: list[str], *, limit: int = 3) -> str:
    cleaned = [item for item in items if item.strip()]
    if not cleaned:
        return "Keine"
    preview = cleaned[:limit]
    suffix = f" +{len(cleaned) - limit} weitere" if len(cleaned) > limit else ""
    return " · ".join(preview) + suffix


def render_source_bucket(
    title: str,
    items: list[str],
    caption: str,
    *,
    streamlit_module: Any = st,
) -> None:
    with streamlit_module.container(border=True):
        streamlit_module.markdown(f"**{title}**")
        streamlit_module.write(source_bucket_preview(items))
        streamlit_module.caption(caption)


def confidence_values(job: JobAdExtract) -> list[float]:
    values: list[float] = []
    for evidence in job_extract_field_evidence_by_name(job).values():
        confidence = evidence_confidence(evidence)
        if confidence is not None:
            values.append(confidence)
    return values


def render_priority_stat(
    title: str,
    value: str,
    caption: str,
    *,
    streamlit_module: Any = st,
) -> None:
    with streamlit_module.container(border=True):
        streamlit_module.markdown(f"**{title}**")
        streamlit_module.write(value or "Nicht erkannt")
        streamlit_module.caption(caption)


def render_analysis_priority_summary(
    job: JobAdExtract,
    *,
    streamlit_module: Any = st,
) -> None:
    evidence_by_field = job_extract_field_evidence_by_name(job)
    confidence_items = confidence_values(job)
    average_confidence = (
        f"{round(sum(confidence_items) / len(confidence_items) * 100):.0f}%"
        if confidence_items
        else "n/a"
    )
    uncertain_count = 0
    for evidence in evidence_by_field.values():
        if not isinstance(evidence, dict):
            continue
        confidence = evidence_confidence(evidence)
        if bool(evidence.get("needs_confirmation")) or (
            confidence is not None and confidence < 0.85
        ):
            uncertain_count += 1
    gap_count = len([gap for gap in job.gaps if str(gap).strip()])

    location = ", ".join(
        value
        for value in (
            str(job.location_city or "").strip(),
            str(job.location_country or "").strip(),
        )
        if value
    )
    location = str(job.place_of_work or "").strip() or location

    streamlit_module.markdown("#### Prüffokus")
    columns = streamlit_module.columns(4, gap="small")
    stats = (
        ("Rolle", str(job.job_title or "").strip(), "Erkannter Zieljob"),
        ("Unternehmen", str(job.company_name or "").strip(), "Quelle oder Ableitung"),
        ("Sicherheit", average_confidence, "Durchschnitt erkannter Evidenzen"),
        ("Prüfen", f"{uncertain_count} unsicher · {gap_count} offen", "Priorität vor Weiter"),
    )
    for column, (title, value, caption) in zip(columns, stats):
        with column:
            render_priority_stat(
                title,
                value,
                caption,
                streamlit_module=streamlit_module,
            )

    if location:
        streamlit_module.caption(f"Arbeitsort: {location}")


def render_job_extract_provenance_block(
    job: JobAdExtract,
    *,
    streamlit_module: Any = st,
) -> None:
    evidence_by_field = job_extract_field_evidence_by_name(job)
    upload_backed: list[str] = []
    uncertain: list[str] = []

    for field_name, evidence in evidence_by_field.items():
        if not isinstance(evidence, dict):
            continue
        label = JOB_EXTRACT_DISPLAY_LABELS.get(field_name, field_name)
        if str(evidence.get("evidence_snippet") or "").strip():
            upload_backed.append(label)
        confidence = evidence_confidence(evidence)
        if bool(evidence.get("needs_confirmation")) or (
            confidence is not None and confidence < 0.85
        ):
            uncertain.append(label)

    gaps = [str(note).strip() for note in job.gaps if str(note).strip()]
    assumptions = [
        str(note).strip() for note in job.assumptions if str(note).strip()
    ]

    streamlit_module.markdown("#### Quelle & Beleg")
    focus_specs = (
        ("Erkannt · prüfen", uncertain, "Niedrige Sicherheit oder als prüfpflichtig markiert."),
        ("Fehlt · ergänzen", gaps, "Nicht gefundene oder unklare Angaben."),
    )
    focus_columns = streamlit_module.columns(2, gap="small")
    for column, (title, items, caption) in zip(focus_columns, focus_specs):
        with column:
            render_source_bucket(
                title,
                items,
                caption,
                streamlit_module=streamlit_module,
            )

    details_context = (
        streamlit_module.expander("Quelle & Beleg anzeigen", expanded=False)
        if hasattr(streamlit_module, "expander")
        else nullcontext()
    )
    with details_context:
        streamlit_module.caption(
            "Erkannte Angaben, fehlende Punkte und Annahmen bleiben getrennt, "
            "damit nur passende Werte bestätigt werden."
        )
        columns = streamlit_module.columns(2, gap="small")
        bucket_specs = (
            (
                "Beleg verfügbar",
                upload_backed,
                "Felder mit kurzer Fundstelle aus dem hochgeladenen Text.",
            ),
            ("Annahme · prüfen", assumptions, "Dokumentierte Ableitungen vor Übernahme prüfen."),
        )
        for column, (title, items, caption) in zip(columns, bucket_specs):
            with column:
                render_source_bucket(
                    title,
                    items,
                    caption,
                    streamlit_module=streamlit_module,
                )
