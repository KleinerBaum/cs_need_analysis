# parsing.py
"""Input parsing utilities (DOCX/PDF/text) and optional redaction."""

from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Any, Dict, Tuple

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

    raw = upload.read()
    name = (meta.get("name") or "").lower()

    if name.endswith(".docx"):
        text = _extract_docx(raw)
    elif name.endswith(".pdf"):
        text = _extract_pdf(raw)
    else:
        # Try decode as utf-8 text
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("latin-1", errors="replace")

    return _normalize_text(text), meta


def extract_text_from_path(path: str | Path) -> str:
    """Helper for local dev: extract text from a local file path."""
    p = Path(path)
    raw = p.read_bytes()
    if p.suffix.lower() == ".docx":
        return _normalize_text(_extract_docx(raw))
    if p.suffix.lower() == ".pdf":
        return _normalize_text(_extract_pdf(raw))
    return _normalize_text(raw.decode("utf-8", errors="replace"))


def _extract_docx(raw: bytes) -> str:
    doc = docx.Document(io.BytesIO(raw))
    paras = [p.text for p in doc.paragraphs if (p.text or "").strip()]
    return "\n".join(paras)


def _extract_pdf(raw: bytes) -> str:
    out_lines = []
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            t = t.strip()
            if t:
                out_lines.append(t)
    return "\n\n".join(out_lines)


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
