from __future__ import annotations

from pathlib import Path

import pytest

from components.iceberg_need_analysis import (
    DEFAULT_CONTENT_PATH,
    DEFAULT_IMAGE_PATH,
    build_iceberg_need_analysis_html,
    load_iceberg_content,
)


def test_landing_page_uses_current_iframe_api() -> None:
    landing_page = Path("wizard_pages/00_landing.py").read_text(encoding="utf-8")

    assert "streamlit.components.v1" not in landing_page
    assert "components.html" not in landing_page
    assert "st.iframe(" in landing_page


def test_iceberg_content_loads_required_sections() -> None:
    content = load_iceberg_content()

    assert DEFAULT_CONTENT_PATH.exists()
    assert DEFAULT_IMAGE_PATH.exists()
    assert set(content) >= {"left", "right", "kpis"}
    for side in ("left", "right"):
        assert set(content[side]) >= {"headline", "subline", "surface", "deep", "result"}
        for card_key in ("surface", "deep", "result"):
            assert set(content[side][card_key]) >= {"title", "body"}
    assert len(content["kpis"]) == 6


def test_iceberg_html_embeds_png_and_overlay_selectors() -> None:
    html = build_iceberg_need_analysis_html()

    assert "data:image/png;base64," in html
    assert 'class="ina-stage"' in html
    assert 'class="ina-guides"' in html
    assert "ina-split-line" in html
    assert "ina-waterline" in html
    assert "ina-surface ina-left-card" in html
    assert "ina-deep ina-right-card" in html
    assert 'class="ina-kpi-bar"' in html


def test_iceberg_html_escapes_content(tmp_path: Path) -> None:
    image_path = tmp_path / "clean.png"
    image_path.write_bytes(b"png")

    html = build_iceberg_need_analysis_html(
        image_path=image_path,
        content={
            "left": {
                "headline": "<script>alert(1)</script>",
                "subline": "A & B",
                "surface": {"title": "Surface", "body": "Rolle < Tasks"},
                "deep": {"title": "Deep", "body": "Risk"},
                "result": {"title": "Result", "body": "Partial"},
            },
            "right": {
                "headline": "AI",
                "subline": "Precise",
                "surface": {"title": "Context", "body": "Goals"},
                "deep": {"title": "Insights", "body": "Needs"},
                "result": {"title": "Result", "body": "Better"},
            },
            "kpis": ["<b>unsafe</b>"],
        },
    )

    assert "<script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "A &amp; B" in html
    assert "Rolle &lt; Tasks" in html
    assert "&lt;b&gt;unsafe&lt;/b&gt;" in html


def test_iceberg_html_includes_css_motion_controls() -> None:
    html = build_iceberg_need_analysis_html()

    assert "@keyframes inaFadeIn" in html
    assert "@keyframes inaWaterGlow" in html
    assert "@keyframes inaDeepPulse" in html
    assert "@media (prefers-reduced-motion: reduce)" in html


def test_iceberg_html_includes_mobile_stacked_layout_rules() -> None:
    html = build_iceberg_need_analysis_html()

    assert "@media (max-width: 760px)" in html
    assert "grid-template-columns: minmax(0, 1fr);" in html
    assert "position: relative;" in html
    assert ".ina-stage::after,\n        .ina-guides,\n        .ina-vs" in html
    assert ".ina-bg" in html
    assert "aspect-ratio: 1672 / 941;" in html
    assert "order: 10;" in html
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in html


def test_iceberg_html_requires_core_content_sections() -> None:
    with pytest.raises(ValueError, match="Missing iceberg content section: right"):
        build_iceberg_need_analysis_html(
            content={
                "left": {
                    "headline": "Left",
                    "subline": "Sub",
                    "surface": {"title": "Surface", "body": "Body"},
                    "deep": {"title": "Deep", "body": "Body"},
                    "result": {"title": "Result", "body": "Body"},
                },
                "kpis": [],
            }
        )
