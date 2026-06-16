from __future__ import annotations

from typing import Any

import app


def test_reset_scroll_uses_valid_iframe_height(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    class _FakeStreamlit:
        def iframe(self, src: str, **kwargs: Any) -> None:
            calls.append((src, kwargs))

    monkeypatch.setattr(app, "st", _FakeStreamlit())

    app._reset_scroll_on_step_change()

    assert len(calls) == 1
    src, kwargs = calls[0]
    assert src.startswith("data:text/html;base64,")
    assert isinstance(kwargs["height"], int)
    assert kwargs["height"] > 0
