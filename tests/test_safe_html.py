from __future__ import annotations

import safe_html


def test_render_static_html_prefers_streamlit_html() -> None:
    calls: list[str] = []

    class _FakeStreamlit:
        def html(self, html: str) -> None:
            calls.append(html)

        def markdown(self, *_args: object, **_kwargs: object) -> None:
            raise AssertionError("markdown fallback should not be used when html exists")

    safe_html.render_static_html("<div>ok</div>", streamlit_module=_FakeStreamlit())

    assert calls == ["<div>ok</div>"]


def test_render_static_html_keeps_markdown_fallback() -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    class _FakeStreamlit:
        def markdown(self, html: str, **kwargs: object) -> None:
            calls.append((html, kwargs))

    safe_html.render_static_html("<div>ok</div>", streamlit_module=_FakeStreamlit())

    assert calls == [("<div>ok</div>", {"unsafe_allow_html": True})]
