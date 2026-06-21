import app


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
