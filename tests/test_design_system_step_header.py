from components import design_system
from wizard_pages import base


def test_build_step_header_html_is_single_safe_block() -> None:
    html = design_system._build_step_header_html(
        title="Titel",
        subtitle="Untertitel",
        outcome="Ergebnis",
        meta_items=[("📌", "Status", "✅ Fertig")],
    )

    assert html.count("<section class=\"cs-step-header\">") == 1
    assert "</section>" in html
    assert "&lt;li class=\"cs-meta-item\"&gt;" not in html
    assert "&lt;span class=\"cs-meta-label\"&gt;" not in html
    assert ">neutral<" not in html
    assert ">warning<" not in html


def test_render_html_block_prefers_streamlit_html(monkeypatch) -> None:
    calls: list[str] = []

    class _FakeStreamlit:
        def html(self, html: str) -> None:
            calls.append(html)

        def markdown(self, *_: object, **__: object) -> None:
            raise AssertionError("markdown fallback should not be used when html exists")

    monkeypatch.setattr(design_system, "st", _FakeStreamlit())

    design_system._render_html_block("<div>ok</div>")

    assert calls == ["<div>ok</div>"]


def test_render_ui_styles_uses_streamlit_theme_tokens(monkeypatch) -> None:
    calls: list[str] = []

    class _FakeStreamlit:
        def html(self, html: str) -> None:
            calls.append(html)

    monkeypatch.setattr(design_system, "st", _FakeStreamlit())

    design_system.render_ui_styles()

    css = calls[0]
    assert "--cs-font-sans:" in css
    assert "--cs-bg: var(--background-color, #F6F8FB);" in css
    assert "--cs-surface: var(--secondary-background-color, #FFFFFF);" in css
    assert "--cs-focus-ring:" in css
    assert ".stMainBlockContainer" in css
    assert "background: var(--cs-bg);" in css


def test_render_ui_styles_scopes_metric_styles_for_sidebar(monkeypatch) -> None:
    calls: list[str] = []

    class _FakeStreamlit:
        def html(self, html: str) -> None:
            calls.append(html)

    monkeypatch.setattr(design_system, "st", _FakeStreamlit())

    design_system.render_ui_styles()

    css = calls[0]
    assert '[data-testid="stMetric"] {' in css
    assert '[data-testid="stSidebar"] [data-testid="stMetric"] {' in css
    assert "--cs-sidebar-bg:" in css
    assert "--cs-sidebar-surface:" in css
    assert "--cs-sidebar-text:" in css
    assert "--cs-sidebar-text-muted:" in css
    assert '[data-testid="stSidebarContent"] {' in css
    assert "background: var(--cs-sidebar-bg) !important;" in css
    assert "background: var(--cs-sidebar-surface);" in css
    assert "border: 1px solid var(--cs-sidebar-border);" in css
    assert "color: var(--cs-sidebar-surface-text) !important;" in css
    assert '[data-testid="stSidebar"] [data-testid="stExpander"] {' in css
    assert '[data-testid="stSidebar"] [data-testid="stProgress"] > div > div {' in css
    assert '[data-testid="stButton"] button {' in css
    assert '[data-testid="stAlert"] {' in css
    assert '[data-testid="stTabs"] button' in css


def test_render_landing_css_uses_theme_tokens(monkeypatch) -> None:
    calls: list[str] = []

    class _FakeStreamlit:
        def markdown(self, html: str, **_: object) -> None:
            calls.append(html)

    monkeypatch.setattr(base, "st", _FakeStreamlit())

    base.render_landing_css(base.LANDING_STYLE_TOKENS)

    css = calls[0]
    assert ".landing-hero" in css
    assert "background: var(--cs-surface);" in css
    assert "border: 1px solid var(--cs-border);" in css
    assert "color: var(--cs-text-muted);" in css
    assert "box-shadow: var(--cs-shadow-md);" in css


def test_build_process_progress_html_escapes_labels_and_starts_with_company() -> None:
    html = design_system._build_process_progress_html(
        [
            {
                "label": "Unternehmen <script>",
                "status": "complete",
                "count": "1/1",
                "current": False,
            },
            {
                "label": "Rolle & Aufgaben",
                "status": "partial",
                "count": "1/3",
                "current": True,
            },
        ],
        aria_label="Prozess <Fortschritt>",
    )

    assert html.count("<li class=\"cs-process-progress-item\"") == 2
    assert "Unternehmen &lt;script&gt;" in html
    assert "Prozess &lt;Fortschritt&gt;" in html
    assert "data-status=\"complete\"" in html
    assert "data-current=\"true\"" in html
    assert html.find("Unternehmen") < html.find("Rolle &amp; Aufgaben")
