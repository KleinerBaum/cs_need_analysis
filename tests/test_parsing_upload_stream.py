from __future__ import annotations

import io

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
