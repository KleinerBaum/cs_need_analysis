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
    assert "--cs-app-bg: var(--background-color, Canvas);" in css
    assert "--cs-app-text: var(--text-color, CanvasText);" in css
    assert "--cs-app-surface: var(" in css
    assert "--cs-app-border: var(" in css
    assert ':root[data-theme="light"] .stApp' in css
    assert "--cs-step-background-image: url(\"data:image/png;base64,dark2\");" in css
    assert "--cs-step-background-image: url(\"data:image/png;base64,light\");" in css
    assert "[data-theme=\"dark\"]" not in css
    assert "[data-testid=\"stAppViewContainer" in css
    assert "background: var(--cs-app-bg) !important;" in css
    assert "background: transparent !important;" in css
