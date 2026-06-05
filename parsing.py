# parsing.py
"""Input parsing utilities (DOCX/PDF/text) and optional redaction."""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path
from typing import Any, Dict, Tuple
from xml.etree import ElementTree

import docx  # python-docx
import pdfplumber


def _normalize_text(text: str) -> str:
    # Normalize newlines and whitespace while preserving structure.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Trim trailing spaces
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return text.strip()


def extract_text_from_uploaded_file(upload: Any) -> Tuple[str, Dict[str, Any]]:
    """Extract plain text from a Streamlit UploadedFile.

    Returns:
        (text, meta)
    """
    meta: Dict[str, Any] = {
        "name": getattr(upload, "name", None),
        "type": getattr(upload, "type", None),
        "size": getattr(upload, "size", None),
    }

    try:
        upload.seek(0)
    except Exception:
        pass

    raw = upload.read()
    if not raw:
        raise ValueError("Datei enthält keinen auslesbaren Inhalt.")
    name = (meta.get("name") or "").lower()

    pdf_missing_text_layer = False
    if name.endswith(".docx"):
        try:
            text = _extract_docx(raw)
        except Exception as exc:
            raise ValueError("DOCX-Struktur nicht auslesbar.") from exc
    elif name.endswith(".pdf"):
        text, pdf_missing_text_layer = _extract_pdf(raw)
    else:
        # Try decode as utf-8 text
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("latin-1", errors="replace")

    normalized = _normalize_text(text)
    if not normalized:
        if name.endswith(".docx"):
            raise ValueError("DOCX enthält keinen auslesbaren Text.")
        if name.endswith(".pdf"):
            if pdf_missing_text_layer:
                raise ValueError("PDF enthält keinen Textlayer (OCR fehlt).")
            raise ValueError("PDF enthält keinen auslesbaren Text.")
        raise ValueError("Datei enthält keinen auslesbaren Inhalt.")

    return normalized, meta


def extract_text_from_path(path: str | Path) -> str:
    """Helper for local dev: extract text from a local file path."""
    p = Path(path)
    raw = p.read_bytes()
    if p.suffix.lower() == ".docx":
        return _normalize_text(_extract_docx(raw))
    if p.suffix.lower() == ".pdf":
        text, _missing_text_layer = _extract_pdf(raw)
        return _normalize_text(text)
    return _normalize_text(raw.decode("utf-8", errors="replace"))


def _extract_docx(raw: bytes) -> str:
    doc = docx.Document(io.BytesIO(raw))
    out_lines: list[str] = []

    def _append_text(value: str | None) -> None:
        text = (value or "").strip()
        if text:
            out_lines.append(text)

    def _append_table_text(tables: Any) -> None:
        for table in tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        _append_text(paragraph.text)
                    _append_table_text(cell.tables)

    for paragraph in doc.paragraphs:
        _append_text(paragraph.text)
    _append_table_text(doc.tables)
    for section in doc.sections:
        for part in (section.header, section.footer):
            for paragraph in part.paragraphs:
                _append_text(paragraph.text)
            _append_table_text(part.tables)

    for text in _extract_docx_ooxml_text(raw):
        _append_text(text)

    return "\n".join(dict.fromkeys(out_lines))


def _extract_docx_ooxml_text(raw: bytes) -> list[str]:
    """Read text nodes that python-docx can miss, e.g. text boxes."""

    lines: list[str] = []
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            xml_names = [
                name
                for name in archive.namelist()
                if name.startswith("word/")
                and name.endswith(".xml")
                and not name.startswith("word/_rels/")
            ]
            for name in xml_names:
                root = ElementTree.fromstring(archive.read(name))
                for text_box in root.iter(f"{namespace}txbxContent"):
                    texts = [
                        node.text.strip()
                        for node in text_box.iter(f"{namespace}t")
                        if node.text and node.text.strip()
                    ]
                    if texts:
                        lines.append(" ".join(texts))
    except (ElementTree.ParseError, KeyError, zipfile.BadZipFile):
        return []
    return lines


def _extract_pdf(raw: bytes) -> tuple[str, bool]:
    out_lines = []
    has_text_layer = False
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        for page in pdf.pages:
            if getattr(page, "chars", None):
                has_text_layer = True
            t = page.extract_text() or ""
            t = t.strip()
            if t:
                out_lines.append(t)
    return "\n\n".join(out_lines), (not has_text_layer)


_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(
    r"(\+?\d{1,3}[\s\-/]?)?(\(?\d{2,5}\)?[\s\-/]?)?\d{3,}[\s\-/]?\d{2,}(?:[\s\-/]?\d{2,})?"
)


def redact_pii(text: str, *, mask: str = "[REDACTED]") -> str:
    """Best-effort redaction to reduce accidental sharing of contact data.

    Notes:
    - This is *not* perfect. It is intended as a safety net.
    - You can disable redaction in the UI if you want to keep contact data.
    """
    # Emails first (high precision)
    text = _EMAIL_RE.sub(mask, text)

    # Phone numbers (lower precision; avoid redacting short numbers)
    def _phone_sub(m: re.Match) -> str:
        s = m.group(0)
        digits = re.sub(r"\D", "", s)
        if len(digits) < 8:
            return s
        return mask

    text = _PHONE_RE.sub(_phone_sub, text)
    return text
