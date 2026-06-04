from components import design_system


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
