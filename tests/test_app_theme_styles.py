import app


def test_inject_theme_styles_uses_streamlit_theme_root(monkeypatch) -> None:
    calls: list[str] = []

    class _FakeStreamlit:
        def markdown(self, html: str, **_: object) -> None:
            calls.append(html)

    monkeypatch.setattr(app, "render_ui_styles", lambda: None)
    monkeypatch.setattr(app, "st", _FakeStreamlit())

    app._inject_theme_styles()

    css = calls[0]
    assert ".stApp {" in css
    assert "--cs-app-bg: var(--background-color, Canvas);" in css
    assert "--cs-app-text: var(--text-color, CanvasText);" in css
    assert "--cs-app-surface: var(" in css
    assert "--cs-app-border: var(" in css
    assert "[data-theme=\"dark\"]" not in css
    assert "[data-testid=\"stAppViewContainer" in css
    assert "background: var(--cs-app-bg) !important;" in css
    assert "url(\"data:image/png" not in css
    assert "background: transparent !important;" in css
