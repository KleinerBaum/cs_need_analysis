import app
import site_ui


class _FakeColumn:
    def __enter__(self) -> "_FakeColumn":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        del exc_type, exc, tb
        return False


class _FakeSiteStreamlit:
    def __init__(self) -> None:
        self.markdown_calls: list[tuple[str, dict[str, object]]] = []

    def markdown(self, html: str, **kwargs: object) -> None:
        self.markdown_calls.append((html, kwargs))

    def columns(self, count: int):
        return [_FakeColumn() for _ in range(count)]


def test_inject_theme_styles_uses_streamlit_theme_root(monkeypatch) -> None:
    calls: list[str] = []

    class _FakeStreamlit:
        def markdown(self, html: str, **_: object) -> None:
            calls.append(html)

    monkeypatch.setattr(app, "render_ui_styles", lambda: None)
    monkeypatch.setattr(app, "st", _FakeStreamlit())
    monkeypatch.setattr(
        app,
        "_image_data_uri",
        lambda path: f"data:image/png;base64,{path.stem}",
    )

    app._inject_theme_styles()

    css = calls[0]
    assert ".stApp {" in css
    assert "--cs-app-bg: var(--background-color, #F6F8FB);" in css
    assert "--cs-app-text: var(--text-color, #142033);" in css
    assert "--cs-app-surface: var(" in css
    assert "--cs-app-border: var(" in css
    assert "--cs-step-background-image: url(\"data:image/png;base64,light\");" in css
    assert '.stApp[data-cs-theme="dark"]' in css
    assert ':root[data-cs-theme="dark"] .stApp' in css
    assert ':root[data-theme="dark"] .stApp' in css
    assert "--cs-step-background-image: url(\"data:image/png;base64,dark2\");" in css
    assert "--cs-app-bg: var(--background-color, #0B111B);" in css
    assert "--cs-app-text: var(--text-color, #F1F5F9);" in css
    assert "[data-testid=\"stAppViewContainer" in css
    assert "background-color: var(--cs-app-bg) !important;" in css
    assert "linear-gradient(" in css
    assert "background-blend-mode: normal, var(--cs-step-background-blend);" in css
    assert "max-width: min(100%, 1180px);" in css
    assert "background: transparent !important;" in css


def test_inject_runtime_theme_bridge_sets_stable_theme_attribute(monkeypatch) -> None:
    calls: list[tuple[str, int | None]] = []

    class _FakeStreamlit:
        def iframe(self, html: str, *, height: int | None = None) -> None:
            calls.append((html, height))

    monkeypatch.setattr(app, "st", _FakeStreamlit())

    app._inject_runtime_theme_bridge()

    assert len(calls) == 1
    html, height = calls[0]
    assert height == 1
    assert html.strip().startswith("<script>")
    assert 'const THEME_ATTR = "data-cs-theme";' in html
    assert "MutationObserver" in html
    assert "themeFromStorage" in html
    assert "themeFromToolbar" in html
    assert "themeFromComputedStyle" in html
    assert "node.setAttribute(THEME_ATTR, theme);" in html


def test_site_ui_render_cards_escapes_dynamic_card_text(monkeypatch) -> None:
    fake_st = _FakeSiteStreamlit()
    monkeypatch.setattr(site_ui, "st", fake_st)

    site_ui.render_cards(
        [
            {
                "title": '<script>alert("title")</script>',
                "body": 'Quote "body" & <img src=x onerror=alert(1)>',
            }
        ]
    )

    html = fake_st.markdown_calls[0][0]
    assert fake_st.markdown_calls[0][1] == {"unsafe_allow_html": True}
    assert "<script>" not in html
    assert "<img" not in html
    assert "&lt;script&gt;alert(&quot;title&quot;)&lt;/script&gt;" in html
    assert "Quote &quot;body&quot; &amp; &lt;img src=x onerror=alert(1)&gt;" in html


def test_site_ui_render_callout_escapes_dynamic_text(monkeypatch) -> None:
    fake_st = _FakeSiteStreamlit()
    monkeypatch.setattr(site_ui, "st", fake_st)

    site_ui.render_callout(
        '<b onclick="alert(1)">Warn</b>',
        "Body & <script>alert(1)</script>",
        tone="warning",
    )

    html = fake_st.markdown_calls[0][0]
    assert "<script>" not in html
    assert "<b onclick=" not in html
    assert "&lt;b onclick=&quot;alert(1)&quot;&gt;Warn&lt;/b&gt;" in html
    assert "Body &amp; &lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "cs-callout-warning" in html


def test_site_ui_render_hero_and_meta_escape_dynamic_text(monkeypatch) -> None:
    fake_st = _FakeSiteStreamlit()
    monkeypatch.setattr(site_ui, "st", fake_st)

    site_ui.render_hero(
        'Need <Analysis>',
        'Lead & "quote"',
        eyebrow='<img src=x onerror="alert(1)">',
    )
    site_ui.render_meta_line("Meta <script>alert(1)</script>")

    hero_html = fake_st.markdown_calls[0][0]
    meta_html = fake_st.markdown_calls[1][0]
    assert "<img" not in hero_html
    assert "Need &lt;Analysis&gt;" in hero_html
    assert "Lead &amp; &quot;quote&quot;" in hero_html
    assert "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;" in hero_html
    assert "<script>" not in meta_html
    assert "Meta &lt;script&gt;alert(1)&lt;/script&gt;" in meta_html
