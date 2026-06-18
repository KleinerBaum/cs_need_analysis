from __future__ import annotations

from job_extract_evidence import (
    add_field_evidence_columns,
    field_evidence_caption_text,
    format_field_evidence_confidence,
    format_field_evidence_snippet,
    job_extract_field_evidence_by_name,
)
from schemas import JobAdExtract, JobAdFieldEvidence


def test_job_extract_field_evidence_by_name_indexes_model_entries() -> None:
    extract = JobAdExtract(
        field_evidence=[
            JobAdFieldEvidence(
                field_name="job_title",
                confidence=0.7,
                evidence_snippet="Data Engineer",
            )
        ]
    )

    evidence_by_field = job_extract_field_evidence_by_name(extract)

    assert evidence_by_field["job_title"]["confidence"] == 0.7
    assert evidence_by_field["job_title"]["evidence_snippet"] == "Data Engineer"


def test_format_field_evidence_confidence_clamps_and_marks_confirmation() -> None:
    assert (
        format_field_evidence_confidence(
            {"confidence": 2.0, "needs_confirmation": True}
        )
        == "100% · prüfen"
    )
    assert format_field_evidence_confidence({"confidence": -1.0}) == "0%"
    assert format_field_evidence_confidence({"confidence": "not-a-number"}) == ""


def test_format_field_evidence_snippet_redacts_and_truncates() -> None:
    snippet = format_field_evidence_snippet(
        {
            "evidence_snippet": (
                "Kontakt recruiting@example.com sucht Senior Data Engineer "
                "für die Plattform."
            )
        },
        max_chars=48,
    )

    assert "recruiting@example.com" not in snippet
    assert snippet.startswith("Kontakt [REDACTED] sucht Senior Data Engineer")
    assert snippet.endswith("…")
    assert len(snippet) <= 48


def test_add_field_evidence_columns_only_when_any_row_has_evidence() -> None:
    rows = [{"field": "job_title", "value": "Data Engineer"}]

    assert add_field_evidence_columns(rows, {}) is rows

    enriched = add_field_evidence_columns(
        rows,
        {
            "job_title": {
                "confidence": 0.82,
                "evidence_snippet": "Senior Data Engineer gesucht.",
                "needs_confirmation": True,
            }
        },
    )

    assert enriched == [
        {
            "field": "job_title",
            "value": "Data Engineer",
            "confidence": "82% · prüfen",
            "evidence": "Senior Data Engineer gesucht.",
        }
    ]


def test_field_evidence_caption_text_combines_confidence_and_snippet() -> None:
    assert field_evidence_caption_text(
        "job_title",
        {
            "job_title": {
                "confidence": 0.82,
                "evidence_snippet": "Senior Data Engineer gesucht.",
                "needs_confirmation": True,
            }
        },
    ) == "Evidence: 82% · prüfen · Senior Data Engineer gesucht."
