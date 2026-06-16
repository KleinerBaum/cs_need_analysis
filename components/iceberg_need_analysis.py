from __future__ import annotations

import base64
import json
from functools import lru_cache
from html import escape
from pathlib import Path
from typing import Any, Mapping


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONTENT_PATH = ROOT_DIR / "content" / "iceberg_need_analysis.json"
DEFAULT_IMAGE_PATH = ROOT_DIR / "images" / "OpenAI eisberg.png"
COMPONENT_HEIGHT = 760


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


def _section(content: Mapping[str, Any], side: str) -> Mapping[str, Any]:
    value = content.get(side)
    if not isinstance(value, Mapping):
        raise ValueError(f"Missing iceberg content section: {side}")
    return value


def _card(section: Mapping[str, Any], key: str, class_name: str, index: int) -> str:
    value = section.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"Missing iceberg card content: {key}")
    title = escape(str(value.get("title", "")))
    body = escape(str(value.get("body", "")))
    return (
        f'<article class="ina-card {class_name}" tabindex="0" '
        f'style="--reveal-index: {index}">'
        f'<h3>{title}</h3>'
        f"<p>{body}</p>"
        "</article>"
    )


def _side_header(section: Mapping[str, Any], class_name: str, index: int) -> str:
    headline = escape(str(section.get("headline", "")))
    subline = escape(str(section.get("subline", "")))
    return (
        f'<header class="ina-side-header {class_name}" style="--reveal-index: {index}">'
        f"<h2>{headline}</h2>"
        f"<p>{subline}</p>"
        "</header>"
    )


def _kpi_bar(content: Mapping[str, Any]) -> str:
    kpis = content.get("kpis", [])
    if not isinstance(kpis, list):
        raise ValueError("Iceberg kpis must be a JSON array.")
    items = "".join(f"<li>{escape(str(kpi))}</li>" for kpi in kpis)
    return f'<ul class="ina-kpi-bar" style="--reveal-index: 8">{items}</ul>'


def build_iceberg_need_analysis_html(
    *,
    content: Mapping[str, Any] | None = None,
    image_path: Path = DEFAULT_IMAGE_PATH,
) -> str:
    data = content if content is not None else load_iceberg_content()
    left = _section(data, "left")
    right = _section(data, "right")
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

    .ina-split-line {{
        stroke: var(--ina-line);
        stroke-width: 1.6;
        stroke-dasharray: 5 10;
        animation: inaDrawLine 880ms 650ms ease-out both;
    }}

    .ina-waterline {{
        stroke: rgba(255, 255, 255, 0.56);
        stroke-width: 1.8;
        filter: drop-shadow(0 0 9px rgba(46, 236, 232, 0.72));
        animation: inaWaterGlow 4.8s 1.1s ease-in-out infinite;
    }}

    .ina-side-header,
    .ina-card,
    .ina-kpi-bar {{
        position: absolute;
        z-index: 3;
        opacity: 0;
        transform: translateY(16px);
        animation: inaReveal 620ms ease-out forwards;
        animation-delay: calc(260ms + (var(--reveal-index) * 120ms));
    }}

    .ina-side-header {{
        top: 6.5%;
        width: 34%;
    }}

    .ina-side-header.left {{
        left: 6.6%;
    }}

    .ina-side-header.right {{
        right: 6.6%;
        text-align: right;
    }}

    .ina-side-header h2 {{
        margin: 0;
        font-family: "Space Grotesk", "Sora", "Inter Tight", Inter, sans-serif;
        font-size: clamp(1.35rem, 3vw, 2.65rem);
        line-height: 1.04;
        letter-spacing: 0;
    }}

    .ina-side-header p {{
        margin: 0.45rem 0 0;
        color: var(--ina-muted);
        font-size: clamp(0.78rem, 1.45vw, 1.2rem);
        line-height: 1.25;
    }}

    .ina-vs {{
        position: absolute;
        top: 7%;
        left: 50%;
        z-index: 3;
        transform: translateX(-50%);
        border: 1px solid var(--ina-stroke);
        border-radius: 999px;
        padding: 0.36rem 0.82rem;
        background: rgba(2, 11, 22, 0.62);
        color: var(--ina-text);
        font-weight: 800;
        letter-spacing: 0.08em;
        font-size: clamp(0.75rem, 1.2vw, 1rem);
        backdrop-filter: blur(14px);
    }}

    .ina-card {{
        width: 26%;
        min-height: 13.5%;
        padding: clamp(0.62rem, 1.55vw, 1.05rem);
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
        margin: 0 0 0.42rem;
        font-size: clamp(0.82rem, 1.4vw, 1.14rem);
        line-height: 1.12;
        letter-spacing: 0;
    }}

    .ina-card p {{
        margin: 0;
        color: var(--ina-muted);
        font-size: clamp(0.7rem, 1.08vw, 0.9rem);
        line-height: 1.36;
    }}

    .ina-surface {{
        top: 29%;
        background: var(--ina-card-light);
    }}

    .ina-deep {{
        top: 59%;
        background: var(--ina-card-deep);
        animation-name: inaReveal, inaDeepPulse;
        animation-duration: 620ms, 5s;
        animation-timing-function: ease-out, ease-in-out;
        animation-fill-mode: forwards, none;
        animation-iteration-count: 1, infinite;
        animation-delay: calc(260ms + (var(--reveal-index) * 120ms)), 2s;
    }}

    .ina-result {{
        top: 80.5%;
        width: 37%;
        min-height: 11%;
    }}

    .ina-left-card {{
        left: 7.2%;
    }}

    .ina-right-card {{
        right: 7.2%;
        text-align: right;
    }}

    .ina-left-card:hover,
    .ina-left-card:focus-visible {{
        box-shadow: 0 18px 50px rgba(0, 0, 0, 0.35), 0 0 28px rgba(255, 176, 0, 0.28);
    }}

    .ina-right-card:hover,
    .ina-right-card:focus-visible {{
        box-shadow: 0 18px 50px rgba(0, 0, 0, 0.35), 0 0 28px rgba(46, 236, 232, 0.3);
    }}

    .ina-kpi-bar {{
        left: 6.5%;
        right: 6.5%;
        bottom: 2.4%;
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

    @keyframes inaDrawLine {{
        from {{
            opacity: 0;
            stroke-dashoffset: 42;
        }}
        to {{
            opacity: 1;
            stroke-dashoffset: 0;
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

    @media (max-width: 760px) {{
        body {{
            overflow: auto;
        }}

        .ina-stage {{
            min-height: 760px;
            aspect-ratio: auto;
        }}

        .ina-side-header,
        .ina-side-header.left,
        .ina-side-header.right,
        .ina-card,
        .ina-left-card,
        .ina-right-card,
        .ina-result,
        .ina-kpi-bar {{
            left: 5%;
            right: 5%;
            width: auto;
            text-align: left;
        }}

        .ina-side-header.left {{
            top: 5%;
        }}

        .ina-side-header.right {{
            top: 15.5%;
        }}

        .ina-vs {{
            top: 12.6%;
        }}

        .ina-surface.ina-left-card {{
            top: 26%;
        }}

        .ina-surface.ina-right-card {{
            top: 38%;
        }}

        .ina-deep.ina-left-card {{
            top: 50%;
        }}

        .ina-deep.ina-right-card {{
            top: 62%;
        }}

        .ina-result.ina-left-card {{
            top: 74%;
        }}

        .ina-result.ina-right-card {{
            top: 84%;
        }}

        .ina-kpi-bar {{
            bottom: 2%;
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }}
    }}

    @media (prefers-reduced-motion: reduce) {{
        .ina-stage,
        .ina-side-header,
        .ina-card,
        .ina-kpi-bar,
        .ina-split-line,
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
        <section class="ina-stage" aria-label="Vergleich klassischer Bedarfsanalyse und AI Need-Analysis">
            <img class="ina-bg" src="{image_src}" alt="" aria-hidden="true">
            <svg class="ina-guides" viewBox="0 0 1920 1080" preserveAspectRatio="none" aria-hidden="true">
                <line class="ina-split-line" x1="960" y1="0" x2="960" y2="1080"></line>
                <line class="ina-waterline" x1="0" y1="500" x2="1920" y2="500"></line>
            </svg>
            <div class="ina-vs">VS</div>
            {_side_header(left, "left", 0)}
            {_side_header(right, "right", 1)}
            {_card(left, "surface", "ina-surface ina-left-card", 2)}
            {_card(right, "surface", "ina-surface ina-right-card", 3)}
            {_card(left, "deep", "ina-deep ina-left-card", 4)}
            {_card(right, "deep", "ina-deep ina-right-card", 5)}
            {_card(left, "result", "ina-result ina-left-card", 6)}
            {_card(right, "result", "ina-result ina-right-card", 7)}
            {_kpi_bar(data)}
        </section>
    </div>
</body>
</html>
""".strip()
