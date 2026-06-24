from __future__ import annotations

from pathlib import Path

import pytest

from components.iceberg_need_analysis import (
    DEFAULT_CONTENT_PATH,
    DEFAULT_IMAGE_PATH,
    build_iceberg_need_analysis_html,
    load_iceberg_content,
)


def test_landing_value_cards_escape_dynamic_html(monkeypatch) -> None:
    from wizard_pages import base

    rendered_blocks: list[tuple[str, dict[str, object]]] = []

    class _FakeColumn:
        def __enter__(self) -> "_FakeColumn":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            del exc_type, exc, tb
            return False

    class _FakeStreamlit:
        def columns(self, count: int, gap: str = "small") -> list[_FakeColumn]:
            del gap
            return [_FakeColumn() for _ in range(count)]

        def markdown(self, text: str, **kwargs: object) -> None:
            rendered_blocks.append((str(text), dict(kwargs)))

    monkeypatch.setattr(base, "st", _FakeStreamlit())

    base.render_value_cards(
        value_cards=[
            (
                "<script>alert(1)</script>",
                '<img src=x onerror="alert(1)">',
            )
        ]
    )

    rendered_html = "\n".join(block for block, _kwargs in rendered_blocks)

    assert "<script>" not in rendered_html
    assert "<img" not in rendered_html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered_html
    assert "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;" in rendered_html
    assert all(kwargs.get("unsafe_allow_html") is True for _block, kwargs in rendered_blocks)


def test_intro_page_uses_current_iframe_api_without_expander() -> None:
    landing_page = Path("wizard_pages/00_landing.py").read_text(encoding="utf-8")
    intro_page = Path("wizard_pages/00_intro.py").read_text(encoding="utf-8")

    assert "streamlit.components.v1" not in intro_page
    assert "components.html" not in intro_page
    assert "st.iframe(" in intro_page
    assert "st.iframe(" not in landing_page
    assert 'with st.expander("Warum Need Analysis?"' not in landing_page


def test_landing_page_does_not_render_iceberg_explainer() -> None:
    landing_page = Path("wizard_pages/00_landing.py").read_text(encoding="utf-8")

    render_body = landing_page.split("def render(ctx: WizardContext) -> None:", 1)[1]
    assert "_render_landing_explainer_sections" not in landing_page
    assert "build_iceberg_need_analysis_html" not in landing_page
    assert "Warum Need Analysis?" not in landing_page
    assert "render_jobad_intake" in render_body


def test_landing_page_delegates_directly_to_intake() -> None:
    landing_page = Path("wizard_pages/00_landing.py").read_text(encoding="utf-8")

    assert "render_jobad_intake(ctx)" in landing_page
    assert "_render_pre_upload_cockpit" not in landing_page
    assert "_render_unlocked_briefing_panel" not in landing_page
    assert "START_PAGE_COPY" not in landing_page


def test_intro_page_uses_popovers_instead_of_external_links() -> None:
    intro_page = Path("wizard_pages/00_intro.py").read_text(encoding="utf-8")

    assert "st.popover" in intro_page
    assert "href=" not in intro_page
    assert "OpenAI API Docs" not in intro_page


def test_intro_page_owns_upload_to_briefing_flow() -> None:
    landing_page = Path("wizard_pages/00_landing.py").read_text(encoding="utf-8")
    intro_page = Path("wizard_pages/00_intro.py").read_text(encoding="utf-8")

    assert "_render_intro_flow_cards" in intro_page
    assert "START_PAGE_COPY[\"flow_title\"]" in intro_page
    assert "_render_landing_flow_cards" not in landing_page
    assert "START_PAGE_COPY[\"flow_title\"]" not in landing_page


def test_intro_page_is_compressed_and_skippable_after_briefing() -> None:
    intro_page = Path("wizard_pages/00_intro.py").read_text(encoding="utf-8")

    assert "Erst klären. Dann suchen." in intro_page
    assert "Briefing-Cockpit öffnen" in intro_page
    assert "SSKey.JOB_EXTRACT.value" in intro_page
    assert "Aus langjähriger Erfahrung" not in intro_page


def test_iceberg_content_loads_required_sections() -> None:
    content = load_iceberg_content()

    assert DEFAULT_CONTENT_PATH.exists()
    assert DEFAULT_IMAGE_PATH.exists()
    assert DEFAULT_IMAGE_PATH.name == "eisberg_need_analysis_surface_deep.png"
    assert set(content) >= {"header", "subtitle", "surface", "waterline", "deep", "footer"}
    assert set(content["surface"]) >= {"headline", "subline", "groups"}
    assert set(content["waterline"]) >= {"surface", "deep"}
    assert set(content["deep"]) >= {"headline", "subline", "groups"}
    for section_key in ("surface", "deep"):
        assert len(content[section_key]["groups"]) >= 3
        for group in content[section_key]["groups"]:
            assert set(group) >= {"title", "body", "items"}
            assert isinstance(group["items"], list)
    assert "Recruiting-Briefing" in content["header"]
    assert "weniger Schleifen" in content["footer"]


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
    assert 'class="ina-main-header"' in html
    assert 'class="ina-group-items"' in html
    assert "Von der Jobspec zum belastbaren Recruiting-Briefing" in html
    assert "Geprüfte Faktenbasis" in html
    assert "Prioritäten &amp; Kompromisse" in html
    assert "Scorecard" in html
    assert 'class="ina-footer"' in html
    assert "Mehr geprüfte Tiefe am Anfang" in html


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
                        "title": 'Surface "quoted"',
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
            "waterline": {"surface": "Surface", "deep": "Deep"},
            "footer": "<b>unsafe</b>",
        },
    )

    assert "<script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "A &amp; B" in html
    assert "Surface &quot;quoted&quot;" in html
    assert "Rolle &lt; Tasks" in html
    assert "&lt;b&gt;unsafe item&lt;/b&gt;" in html
    assert "&lt;b&gt;unsafe&lt;/b&gt;" in html


def test_iceberg_html_escapes_svg_and_attribute_payloads(tmp_path: Path) -> None:
    image_path = tmp_path / "clean.png"
    image_path.write_bytes(b"png")

    html = build_iceberg_need_analysis_html(
        image_path=image_path,
        content={
            "surface": {
                "headline": '<svg onload="alert(1)"></svg>',
                "subline": '<a href="javascript:alert(1)">bad</a>',
                "groups": [
                    {
                        "title": 'Title" autofocus onfocus="alert(1)',
                        "body": "<math><mi>x</mi></math>",
                        "items": ['<img src=x onerror="alert(1)">'],
                    }
                ],
            },
            "deep": {
                "headline": "Deep",
                "subline": "Safe",
                "groups": [
                    {
                        "title": "Context",
                        "body": "Needs",
                        "items": [],
                    }
                ],
            },
            "waterline": {"surface": "Surface", "deep": "Deep"},
            "footer": '<iframe src="javascript:alert(1)"></iframe>',
        },
    )

    assert '<svg onload="alert(1)">' not in html
    assert '<a href="javascript:alert(1)">' not in html
    assert "<math><mi>x</mi></math>" not in html
    assert '<img src=x onerror="alert(1)">' not in html
    assert '<iframe src="javascript:alert(1)">' not in html
    assert "&lt;svg onload=&quot;alert(1)&quot;&gt;&lt;/svg&gt;" in html
    assert "&lt;a href=&quot;javascript:alert(1)&quot;&gt;bad&lt;/a&gt;" in html
    assert "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;" in html


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
    assert ".ina-footer" in html


def test_iceberg_html_requires_core_content_sections() -> None:
    with pytest.raises(ValueError, match="Missing iceberg content section: deep"):
        build_iceberg_need_analysis_html(
            content={
                "surface": {
                    "headline": "Left",
                    "subline": "Sub",
                    "groups": [{"title": "Surface", "body": "Body", "items": []}],
                },
                "footer": "",
            }
        )


def test_iceberg_html_requires_groups_as_array() -> None:
    with pytest.raises(ValueError, match="Iceberg section groups must be a JSON array."):
        build_iceberg_need_analysis_html(
            content={
                "surface": {"headline": "Surface", "subline": "Sub", "groups": "bad"},
                "deep": {"headline": "Deep", "subline": "Sub", "groups": []},
                "footer": "",
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
                "footer": "",
            }
        )
