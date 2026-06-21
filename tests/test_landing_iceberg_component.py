from __future__ import annotations

from pathlib import Path

import pytest

from components.iceberg_need_analysis import (
    DEFAULT_CONTENT_PATH,
    DEFAULT_IMAGE_PATH,
    build_iceberg_need_analysis_html,
    load_iceberg_content,
)


def test_intro_and_landing_pages_use_current_iframe_api_without_expander() -> None:
    landing_page = Path("wizard_pages/00_landing.py").read_text(encoding="utf-8")
    intro_page = Path("wizard_pages/00_intro.py").read_text(encoding="utf-8")

    for page in (intro_page, landing_page):
        assert "streamlit.components.v1" not in page
        assert "components.html" not in page
        assert "st.iframe(" in page
    assert 'with st.expander("Warum Need Analysis?"' not in landing_page


def test_landing_page_shows_explainer_before_intake() -> None:
    landing_page = Path("wizard_pages/00_landing.py").read_text(encoding="utf-8")

    render_body = landing_page.split("def render(ctx: WizardContext) -> None:", 1)[1]
    assert render_body.index("_render_landing_explainer_sections()") < render_body.index(
        "render_jobad_intake"
    )


def test_iceberg_content_loads_required_sections() -> None:
    content = load_iceberg_content()

    assert DEFAULT_CONTENT_PATH.exists()
    assert DEFAULT_IMAGE_PATH.exists()
    assert set(content) >= {"surface", "deep", "kpis"}
    assert set(content["surface"]) >= {"headline", "subline", "groups"}
    assert set(content["deep"]) >= {"headline", "subline", "groups"}
    for section_key in ("surface", "deep"):
        assert len(content[section_key]["groups"]) >= 3
        for group in content[section_key]["groups"]:
            assert set(group) >= {"title", "body", "items"}
            assert isinstance(group["items"], list)
    assert len(content["kpis"]) == 6


def test_iceberg_html_embeds_png_and_overlay_selectors() -> None:
    html = build_iceberg_need_analysis_html()

    assert "data:image/png;base64," in html
    assert 'class="ina-stage"' in html
    assert 'class="ina-guides"' in html
    assert "ina-waterline" in html
    assert "ina-split-line" not in html
    assert 'class="ina-zone-label surface"' in html
    assert 'class="ina-zone-label deep"' in html
    assert 'class="ina-surface-grid"' in html
    assert 'class="ina-deep-grid"' in html
    assert "ina-surface" in html
    assert "ina-deep" in html
    assert 'class="ina-group-items"' in html
    assert "Prioritäten &amp; Erfolgskriterien" in html
    assert "Scorecard" in html
    assert 'class="ina-kpi-bar"' in html


def test_iceberg_html_escapes_content(tmp_path: Path) -> None:
    image_path = tmp_path / "clean.png"
    image_path.write_bytes(b"png")

    html = build_iceberg_need_analysis_html(
        image_path=image_path,
        content={
            "surface": {
                "headline": "<script>alert(1)</script>",
                "subline": "A & B",
                "groups": [
                    {
                        "title": "Surface",
                        "body": "Rolle < Tasks",
                        "items": ["<b>unsafe item</b>"],
                    }
                ],
            },
            "deep": {
                "headline": "AI",
                "subline": "Precise",
                "groups": [
                    {
                        "title": "Insights",
                        "body": "Needs",
                        "items": [],
                    }
                ],
            },
            "kpis": ["<b>unsafe</b>"],
        },
    )

    assert "<script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "A &amp; B" in html
    assert "Rolle &lt; Tasks" in html
    assert "&lt;b&gt;unsafe item&lt;/b&gt;" in html
    assert "&lt;b&gt;unsafe&lt;/b&gt;" in html


def test_iceberg_html_includes_css_motion_controls() -> None:
    html = build_iceberg_need_analysis_html()

    assert "@keyframes inaFadeIn" in html
    assert "@keyframes inaWaterGlow" in html
    assert "@keyframes inaDeepPulse" in html
    assert "@media (prefers-reduced-motion: reduce)" in html


def test_iceberg_html_includes_mobile_stacked_layout_rules() -> None:
    html = build_iceberg_need_analysis_html()

    assert "@media (max-width: 980px)" in html
    assert "grid-template-columns: minmax(0, 1fr);" in html
    assert "position: relative;" in html
    assert ".ina-stage::after,\n        .ina-guides,\n        .ina-zone-label" in html
    assert ".ina-bg" in html
    assert "aspect-ratio: 1672 / 941;" in html
    assert "order: 6;" in html
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in html


def test_iceberg_html_requires_core_content_sections() -> None:
    with pytest.raises(ValueError, match="Missing iceberg content section: deep"):
        build_iceberg_need_analysis_html(
            content={
                "surface": {
                    "headline": "Left",
                    "subline": "Sub",
                    "groups": [{"title": "Surface", "body": "Body", "items": []}],
                },
                "kpis": [],
            }
        )


def test_iceberg_html_requires_groups_as_array() -> None:
    with pytest.raises(ValueError, match="Iceberg section groups must be a JSON array."):
        build_iceberg_need_analysis_html(
            content={
                "surface": {"headline": "Surface", "subline": "Sub", "groups": "bad"},
                "deep": {"headline": "Deep", "subline": "Sub", "groups": []},
                "kpis": [],
            }
        )


def test_iceberg_html_requires_group_items_as_array() -> None:
    with pytest.raises(ValueError, match="Iceberg group items must be a JSON array."):
        build_iceberg_need_analysis_html(
            content={
                "surface": {
                    "headline": "Surface",
                    "subline": "Sub",
                    "groups": [{"title": "Surface", "body": "Body", "items": "bad"}],
                },
                "deep": {"headline": "Deep", "subline": "Sub", "groups": []},
                "kpis": [],
            }
        )
