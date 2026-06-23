"""Safe HTML builders for approximate document previews."""

from __future__ import annotations

import base64
import html
from typing import Any, Sequence

from parsing import extract_docx_preview_blocks, read_validated_upload_bytes


SUPPORTED_PREVIEW_IMAGE_MIME_TYPES = {"image/png", "image/jpeg"}


def read_upload_preview_bytes(upload: object) -> bytes | None:
    try:
        raw, _meta = read_validated_upload_bytes(upload)
    except ValueError:
        return None
    return raw


def document_preview_shell(
    inner_html: str,
    *,
    title: str = "Dokumentvorschau",
    height_px: int = 280,
    accent_color: str = "#2563eb",
    compact: bool = False,
    fit_pages: bool = False,
) -> str:
    page_padding = "24px 28px" if compact else "30px 36px"
    preview_height = "auto" if fit_pages else f"{int(height_px)}px"
    preview_overflow_y = "visible" if fit_pages else "auto"
    escaped_title = html.escape(title)
    escaped_accent = _safe_css_color(accent_color)
    return f"""
        <style>
        .cs-document-preview-wrap {{
            border: 1px solid var(--cs-border);
            background: var(--cs-surface);
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 12px;
            color: var(--cs-text);
        }}
        .cs-document-preview-title {{
            color: var(--cs-text);
            font-weight: 700;
            margin: 0 0 10px;
        }}
        .cs-document-preview {{
            background: color-mix(in srgb, var(--cs-surface-muted) 86%, var(--cs-bg) 14%);
            border: 1px solid color-mix(in srgb, var(--cs-border) 70%, transparent);
            border-radius: 6px;
            height: {preview_height};
            overflow-x: auto;
            overflow-y: {preview_overflow_y};
            padding: 18px;
        }}
        .cs-document-spread {{
            align-items: flex-start;
            display: flex;
            gap: 16px;
            justify-content: center;
            min-width: min-content;
        }}
        .cs-document-page {{
            aspect-ratio: 210 / 297;
            background: #ffffff;
            border-top: 5px solid {escaped_accent};
            box-sizing: border-box;
            color: #0f172a !important;
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.14);
            font-family: Arial, Helvetica, sans-serif;
            font-size: 0.78rem;
            line-height: 1.42;
            margin: 0 auto;
            max-width: 100%;
            min-height: 240px;
            padding: {page_padding};
            width: min(100%, 420px);
        }}
        .cs-document-spread .cs-document-page {{
            flex: 0 0 min(42vw, 390px);
            margin: 0;
        }}
        .cs-document-page,
        .cs-document-page * {{
            color: #0f172a !important;
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
            color: #0f172a !important;
            line-height: 1.2;
            margin: 0 0 14px;
        }}
        .cs-document-page h1 {{ font-size: 1.32rem; }}
        .cs-document-page h2 {{
            border-bottom: 1px solid #e5e7eb;
            font-size: 1rem;
            margin-top: 16px;
            padding-bottom: 4px;
        }}
        .cs-document-page h3 {{ font-size: 0.92rem; margin-top: 14px; }}
        .cs-document-page p {{
            margin: 0 0 9px;
            white-space: pre-wrap;
        }}
        .cs-document-page ul {{
            margin: 0 0 10px 1.05rem;
            padding: 0;
        }}
        .cs-document-page li {{
            margin: 0 0 5px;
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
    parts: list[str] = ['<article class="cs-document-page" style="color:#0f172a;">']
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
        '<article class="cs-document-page" style="color:#0f172a;">'
        + "".join(lines or ["<p></p>"])
        + "</article>"
    )


def markdown_article_preview_html(
    markdown: str,
    *,
    logo_payload: dict[str, Any] | None = None,
) -> str:
    blocks = _markdown_preview_blocks(markdown)
    if _should_split_markdown_preview(markdown, blocks):
        pages = _split_preview_blocks(blocks)
        page_html = "".join(
            _preview_page_html(page_blocks, logo_payload=logo_payload if index == 0 else None)
            for index, page_blocks in enumerate(pages)
        )
        return f'<div class="cs-document-spread">{page_html}</div>'
    return _preview_page_html(blocks, logo_payload=logo_payload)


def _markdown_preview_blocks(markdown: str) -> list[str]:
    blocks: list[str] = []
    in_list = False
    list_items: list[str] = []
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            if in_list:
                blocks.append(
                    "<ul>"
                    + "".join(f"<li>{html.escape(item)}</li>" for item in list_items)
                    + "</ul>"
                )
                in_list = False
                list_items = []
            continue
        if line.startswith("- "):
            in_list = True
            list_items.append(line[2:].strip())
            continue
        if in_list:
            blocks.append(
                "<ul>"
                + "".join(f"<li>{html.escape(item)}</li>" for item in list_items)
                + "</ul>"
            )
            in_list = False
            list_items = []
        if line.startswith("## "):
            blocks.append(f"<h2>{html.escape(line[3:].strip())}</h2>")
        elif line.startswith("# "):
            blocks.append(f"<h1>{html.escape(line[2:].strip())}</h1>")
        else:
            blocks.append(f"<p>{html.escape(line)}</p>")

    if in_list:
        blocks.append(
            "<ul>"
            + "".join(f"<li>{html.escape(item)}</li>" for item in list_items)
            + "</ul>"
        )
    return blocks or ["<p></p>"]


def _should_split_markdown_preview(markdown: str, blocks: Sequence[str]) -> bool:
    text_length = len(markdown.strip())
    bullet_count = sum(1 for line in markdown.splitlines() if line.strip().startswith("- "))
    return text_length > 1800 or bullet_count > 14 or len(blocks) > 9


def _split_preview_blocks(blocks: Sequence[str]) -> list[list[str]]:
    if len(blocks) <= 1:
        return [list(blocks)]
    split_at = max(1, (len(blocks) + 1) // 2)
    return [list(blocks[:split_at]), list(blocks[split_at:])]


def _preview_page_html(
    blocks: Sequence[str],
    *,
    logo_payload: dict[str, Any] | None = None,
) -> str:
    parts: list[str] = ['<article class="cs-document-page" style="color:#0f172a;">']
    logo_uri = logo_data_uri(logo_payload)
    if logo_uri:
        parts.append(
            '<img class="cs-document-logo" alt="Logo" src="'
            f'{html.escape(logo_uri, quote=True)}">'
        )
    parts.extend(blocks or ["<p></p>"])
    parts.append("</article>")
    return "".join(parts)


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
    parts: list[str] = ['<article class="cs-document-page" style="color:#0f172a;">']
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
