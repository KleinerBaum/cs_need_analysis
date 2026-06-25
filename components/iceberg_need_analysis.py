from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import streamlit as st

from i18n import active_language, t, tr_safe
from safe_html import escape_html_text

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONTENT_PATH = ROOT_DIR / "content" / "iceberg_need_analysis.json"
DEFAULT_CSS_PATH = Path(__file__).with_suffix(".css")
DEFAULT_IMAGE_PATH = ROOT_DIR / "images" / "eisberg_need_analysis_surface_deep.png"
COMPONENT_HEIGHT = 560


def _path_mtime_ns(path: Path) -> int:
    return path.stat().st_mtime_ns


@st.cache_data(show_spinner=False)
def _load_json_content(path: str, mtime_ns: int) -> dict[str, Any]:
    del mtime_ns
    with Path(path).open(encoding="utf-8") as content_file:
        content = json.load(content_file)
    if not isinstance(content, dict):
        raise ValueError("Iceberg content must be a JSON object.")
    return content


def load_iceberg_content(path: Path = DEFAULT_CONTENT_PATH) -> dict[str, Any]:
    return _load_json_content(str(path), _path_mtime_ns(path))


@st.cache_data(show_spinner=False)
def _load_text_asset(path: str, mtime_ns: int) -> str:
    del mtime_ns
    return Path(path).read_text(encoding="utf-8")


@st.cache_data(show_spinner=False)
def _image_uri(image_path: str, mtime_ns: int) -> str:
    del mtime_ns
    encoded_image = base64.b64encode(Path(image_path).read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded_image}"


def _load_iceberg_css(path: Path = DEFAULT_CSS_PATH) -> str:
    return _load_text_asset(str(path), _path_mtime_ns(path))


def _section(content: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = content.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"Missing iceberg content section: {key}")
    return value


def _list_items(value: Any, label: str) -> Sequence[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"Iceberg {label} must be a JSON array.")
    return value


def _content_text(value: object, *, translate: bool, language: str) -> object:
    return t(value, language=language) if translate else value


def _group_card(
    group: Mapping[str, Any],
    class_name: str,
    index: int,
    *,
    translate: bool,
    language: str,
) -> str:
    title = escape_html_text(
        _content_text(group.get("title", ""), translate=translate, language=language)
    )
    body = escape_html_text(
        _content_text(group.get("body", ""), translate=translate, language=language)
    )
    items = _list_items(group.get("items", []), "group items")
    item_markup = "".join(
        f"<li>{escape_html_text(_content_text(item, translate=translate, language=language))}</li>"
        for item in items
        if str(item).strip()
    )
    item_list = f'<ul class="ina-group-items">{item_markup}</ul>' if item_markup else ""
    return (
        f'<article class="ina-card {class_name}" tabindex="0" '
        f'style="--reveal-index: {index}">'
        f"<h3>{title}</h3>"
        f"<p>{body}</p>"
        f"{item_list}"
        "</article>"
    )


def _zone_header(
    section: Mapping[str, Any],
    class_name: str,
    index: int,
    *,
    translate: bool,
    language: str,
) -> str:
    headline = escape_html_text(
        _content_text(
            section.get("headline", ""), translate=translate, language=language
        )
    )
    subline = escape_html_text(
        _content_text(
            section.get("subline", ""), translate=translate, language=language
        )
    )
    return (
        f'<header class="ina-zone-header {class_name}" style="--reveal-index: {index}">'
        f"<h2>{headline}</h2>"
        f"<p>{subline}</p>"
        "</header>"
    )


def _zone_groups(
    section: Mapping[str, Any],
    class_name: str,
    start_index: int,
    *,
    translate: bool,
    language: str,
) -> str:
    groups = _list_items(section.get("groups", []), "section groups")
    cards = []
    for offset, group in enumerate(groups):
        if not isinstance(group, Mapping):
            raise ValueError("Iceberg section groups must contain JSON objects.")
        cards.append(
            _group_card(
                group,
                class_name,
                start_index + offset,
                translate=translate,
                language=language,
            )
        )
    return "".join(cards)


def _content_block(
    content: Mapping[str, Any],
    key: str,
    class_name: str,
    fallback: str = "",
    *,
    translate: bool,
    language: str,
) -> str:
    text = escape_html_text(
        _content_text(
            content.get(key, fallback), translate=translate, language=language
        )
    )
    return f'<div class="{class_name}">{text}</div>'


def _waterline_labels(
    content: Mapping[str, Any],
    *,
    translate: bool,
    language: str,
) -> str:
    waterline = content.get("waterline", {})
    if not isinstance(waterline, Mapping):
        raise ValueError("Iceberg waterline must be a JSON object.")
    surface_label = escape_html_text(
        _content_text(
            waterline.get(
                "surface",
                tr_safe("iceberg.surface_label", language=language),
            ),
            translate=translate,
            language=language,
        )
    )
    deep_label = escape_html_text(
        _content_text(
            waterline.get("deep", tr_safe("iceberg.deep_label", language=language)),
            translate=translate,
            language=language,
        )
    )
    return (
        f'<div class="ina-zone-label surface">{surface_label}</div>'
        f'<div class="ina-zone-label deep">{deep_label}</div>'
    )


def _build_iceberg_document(
    *,
    data: Mapping[str, Any],
    css: str,
    image_src: str,
    language: str,
    translate_content: bool,
) -> str:
    surface = _section(data, "surface")
    deep = _section(data, "deep")
    return f"""
<!doctype html>
<html lang="{escape_html_text(language)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
{css}
</style>
</head>
<body>
    <div class="ina-shell">
        <section class="ina-stage" aria-label="{escape_html_text(tr_safe('iceberg.aria_label', language=language))}">
            <img class="ina-bg" src="{image_src}" alt="" aria-hidden="true">
            <svg class="ina-guides" viewBox="0 0 1920 1080" preserveAspectRatio="none" aria-hidden="true">
                <line class="ina-waterline" x1="0" y1="500" x2="1920" y2="500"></line>
            </svg>
            <header class="ina-main-header" style="--reveal-index: 0">
                <h1>{escape_html_text(_content_text(data.get('header', ''), translate=translate_content, language=language))}</h1>
                <p>{escape_html_text(_content_text(data.get('subtitle', ''), translate=translate_content, language=language))}</p>
            </header>
            {_waterline_labels(data, translate=translate_content, language=language)}
            {_zone_header(surface, 'surface', 0, translate=translate_content, language=language)}
            <div class="ina-surface-grid">
                {_zone_groups(surface, 'ina-surface', 1, translate=translate_content, language=language)}
            </div>
            {_zone_header(deep, 'deep', 5, translate=translate_content, language=language)}
            <div class="ina-deep-grid">
                {_zone_groups(deep, 'ina-deep', 6, translate=translate_content, language=language)}
            </div>
            {_content_block(data, 'footer', 'ina-footer', translate=translate_content, language=language)}
        </section>
    </div>
</body>
</html>
""".strip()


@st.cache_data(show_spinner=False)
def _build_default_iceberg_need_analysis_html(
    *,
    language: str,
    content_path: str,
    content_mtime_ns: int,
    css_path: str,
    css_mtime_ns: int,
    image_path: str,
    image_mtime_ns: int,
) -> str:
    data = _load_json_content(content_path, content_mtime_ns)
    css = _load_text_asset(css_path, css_mtime_ns)
    image_src = _image_uri(image_path, image_mtime_ns)
    return _build_iceberg_document(
        data=data,
        css=css,
        image_src=image_src,
        language=language,
        translate_content=True,
    )


def build_iceberg_need_analysis_html(
    *,
    content: Mapping[str, Any] | None = None,
    image_path: Path = DEFAULT_IMAGE_PATH,
) -> str:
    language = active_language()
    image_path = Path(image_path)
    if content is None and image_path == DEFAULT_IMAGE_PATH:
        return _build_default_iceberg_need_analysis_html(
            language=language,
            content_path=str(DEFAULT_CONTENT_PATH),
            content_mtime_ns=_path_mtime_ns(DEFAULT_CONTENT_PATH),
            css_path=str(DEFAULT_CSS_PATH),
            css_mtime_ns=_path_mtime_ns(DEFAULT_CSS_PATH),
            image_path=str(DEFAULT_IMAGE_PATH),
            image_mtime_ns=_path_mtime_ns(DEFAULT_IMAGE_PATH),
        )

    data = content if content is not None else load_iceberg_content()
    css = _load_iceberg_css()
    image_src = _image_uri(str(image_path), _path_mtime_ns(image_path))
    return _build_iceberg_document(
        data=data,
        css=css,
        image_src=image_src,
        language=language,
        translate_content=content is None,
    )
