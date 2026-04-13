from __future__ import annotations

import io

import docx
import pytest

from parsing import extract_text_from_uploaded_file


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


def test_extract_text_from_uploaded_file_reads_docx_table_only_content() -> None:
    def _build(document) -> None:
        table = document.add_table(rows=1, cols=1)
        table.cell(0, 0).text = "Tabelleninhalt only"

    upload = _FakeUpload(_docx_payload(_build), name="jobspec.docx")

    text, _meta = extract_text_from_uploaded_file(upload)

    assert text == "Tabelleninhalt only"


def test_extract_text_from_uploaded_file_reads_docx_paragraph_and_table_content() -> (
    None
):
    def _build(document) -> None:
        document.add_paragraph("Absatzinhalt")
        table = document.add_table(rows=1, cols=1)
        table.cell(0, 0).text = "Tabelleninhalt"

    upload = _FakeUpload(_docx_payload(_build), name="jobspec.docx")

    text, _meta = extract_text_from_uploaded_file(upload)

    assert "Absatzinhalt" in text
    assert "Tabelleninhalt" in text


def test_extract_text_from_uploaded_file_rejects_empty_docx_content() -> None:
    upload = _FakeUpload(_docx_payload(lambda _document: None), name="jobspec.docx")

    with pytest.raises(ValueError, match="Datei enthält keinen auslesbaren Inhalt"):
        extract_text_from_uploaded_file(upload)
