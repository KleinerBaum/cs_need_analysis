"""Safe HTML builders for approximate document previews."""

from __future__ import annotations

import base64
import html
from typing import Any, Sequence

from parsing import extract_docx_preview_blocks


SUPPORTED_PREVIEW_IMAGE_MIME_TYPES = {"image/png", "image/jpeg"}


def read_upload_preview_bytes(upload: object) -> bytes | None:
    try:
        upload.seek(0)  # type: ignore[attr-defined]
    except Exception:
        pass
    try:
        raw = upload.read()  # type: ignore[attr-defined]
    except Exception:
        return None
    finally:
        try:
            upload.seek(0)  # type: ignore[attr-defined]
        except Exception:
            pass
    return raw if isinstance(raw, bytes) and raw else None


def document_preview_shell(
    inner_html: str,
    *,
    title: str = "Dokumentvorschau",
    height_px: int = 280,
    accent_color: str = "#2563eb",
    compact: bool = False,
) -> str:
    page_padding = "24px 28px" if compact else "30px 36px"
    escaped_title = html.escape(title)
    escaped_accent = _safe_css_color(accent_color)
    return f"""
        <style>
        .cs-document-preview-wrap {{
            border: 1px solid var(--cs-border);
            background: color-mix(in srgb, var(--cs-surface) 72%, #ffffff 28%);
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 12px;
        }}
        .cs-document-preview-title {{
            color: var(--cs-text);
            font-weight: 700;
            margin: 0 0 10px;
        }}
        .cs-document-preview {{
            background: #f3f4f6;
            border: 1px solid color-mix(in srgb, var(--cs-border) 70%, transparent);
            border-radius: 6px;
            height: {int(height_px)}px;
            overflow: auto;
            padding: 18px;
        }}
        .cs-document-page {{
            background: #ffffff;
            border-top: 5px solid {escaped_accent};
            color: #111827;
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.14);
            font-family: Arial, Helvetica, sans-serif;
            line-height: 1.55;
            margin: 0 auto;
            max-width: 780px;
            min-height: 240px;
            padding: {page_padding};
        }}
        .cs-document-logo {{
            display: block;
            margin: 0 0 22px;
            max-height: 58px;
            max-width: 180px;
            object-fit: contain;
        }}
        .cs-document-page h1,
        .cs-document-page h2,
        .cs-document-page h3 {{
            color: #111827;
            line-height: 1.2;
            margin: 0 0 14px;
        }}
        .cs-document-page h1 {{ font-size: 1.7rem; }}
        .cs-document-page h2 {{
            border-bottom: 1px solid #e5e7eb;
            font-size: 1.3rem;
            margin-top: 22px;
            padding-bottom: 4px;
        }}
        .cs-document-page h3 {{ font-size: 1.08rem; margin-top: 18px; }}
        .cs-document-page p {{
            margin: 0 0 12px;
            white-space: pre-wrap;
        }}
        .cs-document-page ul {{
            margin: 0 0 14px 1.2rem;
            padding: 0;
        }}
        .cs-document-page li {{
            margin: 0 0 7px;
            padding-left: 2px;
        }}
        .cs-document-page table {{
            border-collapse: collapse;
            margin: 14px 0;
            width: 100%;
        }}
        .cs-document-page td {{
            border: 1px solid #d1d5db;
            padding: 8px 10px;
            vertical-align: top;
        }}
        .cs-document-pdf-frame {{
            border: 0;
            height: 100%;
            width: 100%;
        }}
        </style>
        <div class="cs-document-preview-wrap">
            <div class="cs-document-preview-title">{escaped_title}</div>
            <div class="cs-document-preview">{inner_html}</div>
        </div>
    """


def pdf_preview_html(raw: bytes) -> str:
    encoded = base64.b64encode(raw).decode("ascii")
    return (
        '<iframe class="cs-document-pdf-frame" title="Dokumentvorschau" '
        f'src="data:application/pdf;base64,{encoded}"></iframe>'
    )


def docx_preview_html(raw: bytes) -> str:
    parts: list[str] = ['<article class="cs-document-page">']
    for block in extract_docx_preview_blocks(raw):
        block_type = block.get("type")
        if block_type == "table":
            rows = block.get("rows") if isinstance(block.get("rows"), list) else []
            parts.append("<table><tbody>")
            for row in rows:
                if not isinstance(row, list):
                    continue
                parts.append("<tr>")
                for cell in row:
                    parts.append(f"<td>{html.escape(str(cell))}</td>")
                parts.append("</tr>")
            parts.append("</tbody></table>")
            continue
        text = html.escape(str(block.get("text") or ""))
        if not text:
            continue
        level = block.get("level")
        heading_level = level if isinstance(level, int) and 1 <= level <= 3 else 0
        if block_type == "heading" and heading_level:
            parts.append(f"<h{heading_level}>{text}</h{heading_level}>")
        else:
            parts.append(f"<p>{text}</p>")
    parts.append("</article>")
    return "".join(parts)


def text_preview_html(text: str) -> str:
    lines = [
        f"<p>{html.escape(line)}</p>"
        for line in text.splitlines()
        if line.strip()
    ]
    return (
        '<article class="cs-document-page">'
        + "".join(lines or ["<p></p>"])
        + "</article>"
    )


def uploaded_document_preview_html(upload: object | None, fallback_text: str) -> str | None:
    if upload is None:
        return None
    file_name = str(getattr(upload, "name", "") or "").lower()
    raw = read_upload_preview_bytes(upload)
    if raw and file_name.endswith(".pdf"):
        inner_html = pdf_preview_html(raw)
    elif raw and file_name.endswith(".docx"):
        try:
            inner_html = docx_preview_html(raw)
        except Exception:
            inner_html = text_preview_html(fallback_text)
    else:
        inner_html = text_preview_html(fallback_text)
    return document_preview_shell(inner_html)


def logo_data_uri(logo_payload: dict[str, Any] | None) -> str:
    if not isinstance(logo_payload, dict):
        return ""
    mime_type = str(logo_payload.get("mime_type") or "").strip().lower()
    logo_bytes = logo_payload.get("bytes")
    if (
        mime_type not in SUPPORTED_PREVIEW_IMAGE_MIME_TYPES
        or not isinstance(logo_bytes, (bytes, bytearray))
        or not logo_bytes
    ):
        return ""
    encoded = base64.b64encode(bytes(logo_bytes)).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def article_preview_html(
    *,
    headline: str,
    intro: str = "",
    sections: Sequence[tuple[str, Sequence[str]]] = (),
    closing: Sequence[str] = (),
    fallback_text: str = "",
    logo_payload: dict[str, Any] | None = None,
) -> str:
    parts: list[str] = ['<article class="cs-document-page">']
    logo_uri = logo_data_uri(logo_payload)
    if logo_uri:
        parts.append(
            '<img class="cs-document-logo" alt="Logo" src="'
            f'{html.escape(logo_uri, quote=True)}">'
        )
    if headline.strip():
        parts.append(f"<h1>{html.escape(headline.strip())}</h1>")
    has_body_content = False
    if intro.strip():
        has_body_content = True
        parts.append(f"<p>{html.escape(intro.strip())}</p>")
    for heading, items in sections:
        clean_items = [str(item).strip() for item in items if str(item).strip()]
        if not clean_items:
            continue
        has_body_content = True
        parts.append(f"<h2>{html.escape(str(heading).strip())}</h2>")
        parts.append("<ul>")
        parts.extend(f"<li>{html.escape(item)}</li>" for item in clean_items)
        parts.append("</ul>")
    for value in closing:
        text = str(value or "").strip()
        if text:
            has_body_content = True
            parts.append(f"<p>{html.escape(text)}</p>")
    if not has_body_content and fallback_text.strip():
        for line in fallback_text.splitlines():
            if line.strip():
                parts.append(f"<p>{html.escape(line.strip())}</p>")
    parts.append("</article>")
    return "".join(parts)


def _safe_css_color(value: str) -> str:
    cleaned = str(value or "").strip()
    if re_match_css_color(cleaned):
        return cleaned
    return "#2563eb"


def re_match_css_color(value: str) -> bool:
    if value.startswith("#") and len(value) in {4, 7}:
        return all(char in "0123456789abcdefABCDEF" for char in value[1:])
    return value in {"#2563eb", "#111827", "#374151"}
