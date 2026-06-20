from __future__ import annotations

import base64
import json
from functools import lru_cache
from html import escape
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONTENT_PATH = ROOT_DIR / "content" / "iceberg_need_analysis.json"
DEFAULT_IMAGE_PATH = ROOT_DIR / "images" / "OpenAI eisberg.png"
COMPONENT_HEIGHT = 640


def load_iceberg_content(path: Path = DEFAULT_CONTENT_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as content_file:
        content = json.load(content_file)
    if not isinstance(content, dict):
        raise ValueError("Iceberg content must be a JSON object.")
    return content


@lru_cache(maxsize=4)
def _image_uri(image_path: str) -> str:
    path = Path(image_path)
    encoded_image = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded_image}"


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


def _group_card(group: Mapping[str, Any], class_name: str, index: int) -> str:
    title = escape(str(group.get("title", "")))
    body = escape(str(group.get("body", "")))
    items = _list_items(group.get("items", []), "group items")
    item_markup = "".join(
        f"<li>{escape(str(item))}</li>" for item in items if str(item).strip()
    )
    item_list = f'<ul class="ina-group-items">{item_markup}</ul>' if item_markup else ""
    return (
        f'<article class="ina-card {class_name}" tabindex="0" '
        f'style="--reveal-index: {index}">'
        f'<h3>{title}</h3>'
        f"<p>{body}</p>"
        f"{item_list}"
        "</article>"
    )


def _zone_header(section: Mapping[str, Any], class_name: str, index: int) -> str:
    headline = escape(str(section.get("headline", "")))
    subline = escape(str(section.get("subline", "")))
    return (
        f'<header class="ina-zone-header {class_name}" style="--reveal-index: {index}">'
        f"<h2>{headline}</h2>"
        f"<p>{subline}</p>"
        "</header>"
    )


def _zone_groups(section: Mapping[str, Any], class_name: str, start_index: int) -> str:
    groups = _list_items(section.get("groups", []), "section groups")
    cards = []
    for offset, group in enumerate(groups):
        if not isinstance(group, Mapping):
            raise ValueError("Iceberg section groups must contain JSON objects.")
        cards.append(_group_card(group, class_name, start_index + offset))
    return "".join(cards)


def _kpi_bar(content: Mapping[str, Any]) -> str:
    kpis = _list_items(content.get("kpis", []), "kpis")
    items = "".join(f"<li>{escape(str(kpi))}</li>" for kpi in kpis)
    return f'<ul class="ina-kpi-bar" style="--reveal-index: 13">{items}</ul>'


def build_iceberg_need_analysis_html(
    *,
    content: Mapping[str, Any] | None = None,
    image_path: Path = DEFAULT_IMAGE_PATH,
) -> str:
    data = content if content is not None else load_iceberg_content()
    surface = _section(data, "surface")
    deep = _section(data, "deep")
    image_src = _image_uri(str(image_path))

    return f"""
<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
    :root {{
        color-scheme: dark;
        --ina-bg: #020B16;
        --ina-card: rgba(8, 25, 42, 0.72);
        --ina-card-light: rgba(14, 38, 59, 0.74);
        --ina-card-deep: rgba(3, 17, 30, 0.78);
        --ina-stroke: rgba(255, 255, 255, 0.14);
        --ina-text: #F8FAFC;
        --ina-muted: #A8B3C2;
        --ina-amber: #FFB000;
        --ina-cyan: #2EECE8;
        --ina-line: rgba(255, 255, 255, 0.20);
    }}

    * {{
        box-sizing: border-box;
    }}

    html,
    body {{
        width: 100%;
        min-height: 100%;
        margin: 0;
        overflow: hidden;
        background: transparent;
        font-family: Inter, "IBM Plex Sans", "Source Sans 3", Arial, sans-serif;
    }}

    .ina-shell {{
        width: min(100%, 1280px);
        margin: 0 auto;
        color: var(--ina-text);
    }}

    .ina-stage {{
        position: relative;
        width: 100%;
        aspect-ratio: 1672 / 941;
        min-height: 360px;
        overflow: hidden;
        isolation: isolate;
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 8px;
        background: var(--ina-bg);
        box-shadow: 0 22px 70px rgba(0, 0, 0, 0.35);
        animation: inaFadeIn 720ms ease-out both;
    }}

    .ina-bg {{
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        object-fit: cover;
        z-index: 0;
    }}

    .ina-stage::after {{
        content: "";
        position: absolute;
        inset: 0;
        z-index: 1;
        background:
            linear-gradient(90deg, rgba(255, 176, 0, 0.12), transparent 35%, transparent 65%, rgba(46, 236, 232, 0.12)),
            linear-gradient(180deg, rgba(2, 11, 22, 0.15), transparent 46%, rgba(2, 11, 22, 0.24));
        pointer-events: none;
    }}

    .ina-guides {{
        position: absolute;
        inset: 0;
        z-index: 2;
        width: 100%;
        height: 100%;
        pointer-events: none;
    }}

    .ina-waterline {{
        stroke: rgba(255, 255, 255, 0.56);
        stroke-width: 1.8;
        filter: drop-shadow(0 0 9px rgba(46, 236, 232, 0.72));
        animation: inaWaterGlow 4.8s 1.1s ease-in-out infinite;
    }}

    .ina-zone-header,
    .ina-card,
    .ina-kpi-bar {{
        position: absolute;
        z-index: 3;
        opacity: 0;
        transform: translateY(16px);
        animation: inaReveal 620ms ease-out forwards;
        animation-delay: calc(260ms + (var(--reveal-index) * 120ms));
    }}

    .ina-zone-header {{
        width: min(37%, 430px);
    }}

    .ina-zone-header.surface {{
        top: 6%;
        left: 5.4%;
    }}

    .ina-zone-header.deep {{
        top: 51.5%;
        left: 5.4%;
    }}

    .ina-zone-header h2 {{
        margin: 0;
        font-family: "Space Grotesk", "Sora", "Inter Tight", Inter, sans-serif;
        font-size: clamp(1.45rem, 3vw, 2.75rem);
        line-height: 1.04;
        letter-spacing: 0;
    }}

    .ina-zone-header p {{
        margin: 0.45rem 0 0;
        color: var(--ina-muted);
        font-size: clamp(0.78rem, 1.45vw, 1.2rem);
        line-height: 1.25;
    }}

    .ina-zone-label {{
        position: absolute;
        left: 50%;
        z-index: 3;
        transform: translateX(-50%);
        border: 1px solid var(--ina-stroke);
        border-radius: 999px;
        padding: 0.34rem 0.78rem;
        background: rgba(2, 11, 22, 0.66);
        color: var(--ina-text);
        font-weight: 800;
        letter-spacing: 0.04em;
        font-size: clamp(0.68rem, 1vw, 0.9rem);
        backdrop-filter: blur(14px);
        opacity: 0;
        animation: inaReveal 620ms 580ms ease-out forwards;
    }}

    .ina-zone-label.surface {{
        top: 43.4%;
    }}

    .ina-zone-label.deep {{
        top: 47.6%;
    }}

    .ina-card {{
        padding: clamp(0.52rem, 1.05vw, 0.82rem);
        border: 1px solid var(--ina-stroke);
        border-radius: 8px;
        background: var(--ina-card);
        box-shadow: 0 18px 50px rgba(0, 0, 0, 0.35);
        backdrop-filter: blur(18px);
        transition: transform 180ms ease, border-color 180ms ease, box-shadow 180ms ease, background 180ms ease;
    }}

    .ina-card:hover,
    .ina-card:focus-visible {{
        transform: translateY(-3px);
        outline: none;
        border-color: rgba(255, 255, 255, 0.32);
        background: rgba(12, 34, 54, 0.82);
    }}

    .ina-card h3 {{
        margin: 0 0 0.32rem;
        font-size: clamp(0.74rem, 1vw, 0.95rem);
        line-height: 1.12;
        letter-spacing: 0;
    }}

    .ina-card p {{
        margin: 0;
        color: var(--ina-muted);
        font-size: clamp(0.6rem, 0.78vw, 0.75rem);
        line-height: 1.28;
    }}

    .ina-group-items {{
        display: flex;
        flex-wrap: wrap;
        gap: 0.22rem;
        margin: 0.42rem 0 0;
        padding: 0;
        list-style: none;
    }}

    .ina-group-items li {{
        max-width: 100%;
        padding: 0.16rem 0.36rem;
        border: 1px solid rgba(255, 255, 255, 0.14);
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.08);
        color: var(--ina-text);
        font-size: clamp(0.52rem, 0.64vw, 0.63rem);
        line-height: 1.1;
        font-weight: 700;
        overflow-wrap: anywhere;
    }}

    .ina-surface-grid,
    .ina-deep-grid {{
        position: absolute;
        left: 5.4%;
        right: 5.4%;
        z-index: 3;
        display: grid;
        gap: 0.52rem;
    }}

    .ina-surface-grid {{
        top: 20%;
        grid-template-columns: repeat(4, minmax(0, 1fr));
    }}

    .ina-deep-grid {{
        top: 58%;
        grid-template-columns: repeat(3, minmax(0, 1fr));
    }}

    .ina-surface {{
        position: relative;
        min-height: 122px;
        background: rgba(20, 41, 55, 0.72);
    }}

    .ina-deep {{
        position: relative;
        min-height: 112px;
        background: rgba(3, 17, 30, 0.80);
        animation-name: inaReveal, inaDeepPulse;
        animation-duration: 620ms, 5s;
        animation-timing-function: ease-out, ease-in-out;
        animation-fill-mode: forwards, none;
        animation-iteration-count: 1, infinite;
        animation-delay: calc(260ms + (var(--reveal-index) * 120ms)), 2s;
    }}

    .ina-surface:hover,
    .ina-surface:focus-visible {{
        box-shadow: 0 18px 50px rgba(0, 0, 0, 0.35), 0 0 28px rgba(255, 176, 0, 0.28);
    }}

    .ina-deep:hover,
    .ina-deep:focus-visible {{
        box-shadow: 0 18px 50px rgba(0, 0, 0, 0.35), 0 0 28px rgba(46, 236, 232, 0.3);
    }}

    .ina-kpi-bar {{
        left: 6.5%;
        right: 6.5%;
        bottom: 2.1%;
        display: grid;
        grid-template-columns: repeat(6, minmax(0, 1fr));
        gap: 0.45rem;
        margin: 0;
        padding: 0.55rem;
        list-style: none;
        border: 1px solid var(--ina-stroke);
        border-radius: 8px;
        background: rgba(2, 11, 22, 0.58);
        backdrop-filter: blur(16px);
    }}

    .ina-kpi-bar li {{
        min-width: 0;
        color: var(--ina-text);
        font-size: clamp(0.62rem, 1vw, 0.82rem);
        line-height: 1.2;
        text-align: center;
        font-weight: 700;
        overflow-wrap: anywhere;
    }}

    .ina-kpi-bar li:nth-child(-n+3) {{
        color: #FFE2A3;
    }}

    .ina-kpi-bar li:nth-child(n+4) {{
        color: #B7FFFF;
    }}

    @keyframes inaFadeIn {{
        from {{
            opacity: 0;
            transform: scale(0.992);
        }}
        to {{
            opacity: 1;
            transform: scale(1);
        }}
    }}

    @keyframes inaReveal {{
        to {{
            opacity: 1;
            transform: translateY(0);
        }}
    }}

    @keyframes inaWaterGlow {{
        0%,
        100% {{
            opacity: 0.58;
            filter: drop-shadow(0 0 7px rgba(46, 236, 232, 0.45));
        }}
        50% {{
            opacity: 0.96;
            filter: drop-shadow(0 0 15px rgba(46, 236, 232, 0.88));
        }}
    }}

    @keyframes inaDeepPulse {{
        0%,
        100% {{
            border-color: var(--ina-stroke);
        }}
        50% {{
            border-color: rgba(46, 236, 232, 0.34);
        }}
    }}

    @media (max-width: 980px) {{
        body {{
            overflow: auto;
        }}

        .ina-stage {{
            display: grid;
            grid-template-columns: minmax(0, 1fr);
            gap: 0.52rem;
            min-height: auto;
            padding: 0.62rem;
            aspect-ratio: auto;
            overflow: visible;
        }}

        .ina-stage::after,
        .ina-guides,
        .ina-zone-label {{
            display: none;
        }}

        .ina-bg {{
            position: relative;
            inset: auto;
            z-index: 1;
            order: 1;
            width: 100%;
            height: auto;
            max-height: 185px;
            aspect-ratio: 1672 / 941;
            border: 1px solid rgba(255, 255, 255, 0.10);
            border-radius: 8px;
            object-fit: cover;
        }}

        .ina-zone-header,
        .ina-card,
        .ina-surface-grid,
        .ina-deep-grid,
        .ina-kpi-bar {{
            position: relative;
            top: auto;
            left: auto;
            right: auto;
            bottom: auto;
            z-index: 2;
            width: auto;
            text-align: left;
        }}

        .ina-zone-header {{
            margin-top: 0.15rem;
            padding-top: 0.3rem;
            border-top: 1px solid rgba(255, 255, 255, 0.14);
        }}

        .ina-zone-header h2 {{
            font-size: clamp(1.08rem, 5.7vw, 1.42rem);
        }}

        .ina-zone-header p {{
            margin-top: 0.24rem;
            font-size: 0.8rem;
        }}

        .ina-zone-header.surface {{
            order: 2;
        }}

        .ina-surface-grid {{
            order: 3;
            display: grid;
            grid-template-columns: minmax(0, 1fr);
            gap: 0.48rem;
        }}

        .ina-zone-header.deep {{
            order: 4;
        }}

        .ina-deep-grid {{
            order: 5;
            display: grid;
            grid-template-columns: minmax(0, 1fr);
            gap: 0.48rem;
        }}

        .ina-card {{
            min-height: auto;
            padding: 0.58rem;
        }}

        .ina-card h3 {{
            margin-bottom: 0.26rem;
            font-size: 0.9rem;
        }}

        .ina-card p {{
            font-size: 0.78rem;
            line-height: 1.28;
        }}

        .ina-group-items {{
            gap: 0.24rem;
            margin-top: 0.42rem;
        }}

        .ina-group-items li {{
            font-size: 0.66rem;
        }}

        .ina-kpi-bar {{
            order: 6;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            margin-top: 0.12rem;
            padding: 0.48rem;
        }}

        .ina-kpi-bar li {{
            font-size: 0.68rem;
        }}
    }}

    @media (prefers-reduced-motion: reduce) {{
        .ina-stage,
        .ina-zone-header,
        .ina-zone-label,
        .ina-card,
        .ina-kpi-bar,
        .ina-waterline,
        .ina-deep {{
            animation: none !important;
            opacity: 1 !important;
            transform: none !important;
        }}

        .ina-card {{
            transition: none;
        }}
    }}
</style>
</head>
<body>
    <div class="ina-shell">
        <section class="ina-stage" aria-label="Eisberg-Modell klassischer und AI-gestützter Need-Analysis">
            <img class="ina-bg" src="{image_src}" alt="" aria-hidden="true">
            <svg class="ina-guides" viewBox="0 0 1920 1080" preserveAspectRatio="none" aria-hidden="true">
                <line class="ina-waterline" x1="0" y1="500" x2="1920" y2="500"></line>
            </svg>
            <div class="ina-zone-label surface">sichtbar: klassische Bedarfsanalyse</div>
            <div class="ina-zone-label deep">entscheidend: AI-gestützte Need-Analysis</div>
            {_zone_header(surface, "surface", 0)}
            <div class="ina-surface-grid">
                {_zone_groups(surface, "ina-surface", 1)}
            </div>
            {_zone_header(deep, "deep", 5)}
            <div class="ina-deep-grid">
                {_zone_groups(deep, "ina-deep", 6)}
            </div>
            {_kpi_bar(data)}
        </section>
    </div>
</body>
</html>
""".strip()
