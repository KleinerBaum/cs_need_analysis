from __future__ import annotations

import io

import docx
import pytest

import parsing
from parsing import extract_docx_preview_blocks, extract_text_from_uploaded_file


class _FakeUpload:
    def __init__(self, payload: bytes, *, name: str = "jobspec.txt") -> None:
        self.name = name
        self.type = "text/plain"
        self.size = len(payload)
        self._stream = io.BytesIO(payload)

    def seek(self, pos: int) -> int:
        return self._stream.seek(pos)

    def read(self) -> bytes:
        return self._stream.read()


def _docx_payload(build_fn) -> bytes:
    document = docx.Document()
    build_fn(document)
    out = io.BytesIO()
    document.save(out)
    return out.getvalue()


def test_extract_text_from_uploaded_file_is_stable_across_multiple_reads() -> None:
    upload = _FakeUpload(b"Senior Data Engineer\nPython")

    first_text, first_meta = extract_text_from_uploaded_file(upload)
    second_text, second_meta = extract_text_from_uploaded_file(upload)

    assert first_text == "Senior Data Engineer\nPython"
    assert second_text == first_text
    assert first_meta == second_meta


def test_extract_text_from_uploaded_file_raises_on_empty_payload() -> None:
    upload = _FakeUpload(b"")

    with pytest.raises(ValueError, match="Datei enthält keinen auslesbaren Inhalt"):
        extract_text_from_uploaded_file(upload)


def test_extract_text_from_uploaded_file_reads_docx_tables() -> None:
    buf = io.BytesIO()
    doc = docx.Document()
    table = doc.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Nur"
    table.rows[0].cells[1].text = "Tabelle"
    doc.save(buf)

    upload = _FakeUpload(
        buf.getvalue(),
        name="jobspec.docx",
    )

    text, _meta = extract_text_from_uploaded_file(upload)

    assert text == "Nur\nTabelle"


def test_extract_text_from_uploaded_file_reads_docx_headers_and_footers() -> None:
    def _build(document: docx.Document) -> None:
        document.sections[0].header.paragraphs[0].text = "Senior AI Consultant"
        document.add_paragraph("Main body requirements")
        document.sections[0].footer.paragraphs[0].text = "Reference R001"

    upload = _FakeUpload(_docx_payload(_build), name="jobspec.docx")

    text, _meta = extract_text_from_uploaded_file(upload)

    assert "Senior AI Consultant" in text
    assert "Main body requirements" in text
    assert "Reference R001" in text


def test_extract_docx_preview_blocks_preserves_body_order() -> None:
    def _build(document: docx.Document) -> None:
        document.add_heading("Senior Data Engineer", level=1)
        document.add_paragraph("Build reliable data products.")
        table = document.add_table(rows=1, cols=2)
        table.rows[0].cells[0].text = "Python"
        table.rows[0].cells[1].text = "Airflow"

    blocks = extract_docx_preview_blocks(_docx_payload(_build))

    assert blocks[0] == {
        "type": "heading",
        "text": "Senior Data Engineer",
        "level": 1,
    }
    assert blocks[1] == {
        "type": "paragraph",
        "text": "Build reliable data products.",
        "level": 0,
    }
    assert blocks[2] == {"type": "table", "rows": [["Python", "Airflow"]]}


def test_extract_text_from_uploaded_file_pdf_without_ocr_has_specific_error(
    monkeypatch,
) -> None:
    upload = _FakeUpload(b"%PDF-1.4", name="scan.pdf")

    monkeypatch.setattr(parsing, "_extract_pdf", lambda _raw: ("", True))

    with pytest.raises(
        ValueError, match="PDF enthält keinen Textlayer \\(OCR fehlt\\)"
    ):
        extract_text_from_uploaded_file(upload)
