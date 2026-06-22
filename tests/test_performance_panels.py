from __future__ import annotations

from typing import Any, Callable

from constants import SSKey


class _FakeStreamlit:
    def __init__(
        self,
        session_state: dict[str, Any] | None = None,
        *,
        expose_fragment: bool = False,
    ) -> None:
        self.session_state = session_state or {}
        self.fragment_calls = 0
        if expose_fragment:
            self.fragment = self._fragment

    def _fragment(self, fn: Callable[[], None]) -> Callable[[], None]:
        self.fragment_calls += 1
        return fn


def test_fragment_pilot_is_disabled_without_available_streamlit_fragment(
    monkeypatch,
) -> None:
    import ui_layout

    fake_st = _FakeStreamlit(
        {SSKey.PERF_FRAGMENT_PILOT_ENABLED.value: True},
        expose_fragment=False,
    )
    monkeypatch.setattr(ui_layout, "st", fake_st)

    assert ui_layout.perf_fragment_pilot_enabled() is False


def test_fragment_pilot_panel_records_plain_timing_when_disabled(monkeypatch) -> None:
    import ui_layout

    fake_st = _FakeStreamlit(
        {
            SSKey.PERF_FRAGMENT_PILOT_ENABLED.value: False,
            SSKey.USAGE_EVENTS.value: [],
        },
        expose_fragment=True,
    )
    ticks = iter([10.0, 10.125])
    calls: list[str] = []
    monkeypatch.setattr(ui_layout, "st", fake_st)
    monkeypatch.setattr(ui_layout, "perf_counter", lambda: next(ticks))

    ui_layout.render_fragment_pilot_panel(
        step_key="skills",
        panel_id="salary_forecast",
        render_slot=lambda: calls.append("rendered"),
    )

    assert calls == ["rendered"]
    assert fake_st.fragment_calls == 0
    event = fake_st.session_state[SSKey.USAGE_EVENTS.value][0]
    assert event["event_type"] == "enrichment_timed"
    assert event["metadata"] == {
        "stage": "render_panel",
        "path": "skills.salary_forecast",
        "duration_ms": 125,
        "status": "success",
        "fragment_enabled": False,
    }


def test_fragment_pilot_panel_uses_fragment_and_records_flag(monkeypatch) -> None:
    import ui_layout

    fake_st = _FakeStreamlit(
        {
            SSKey.PERF_FRAGMENT_PILOT_ENABLED.value: True,
            SSKey.USAGE_EVENTS.value: [],
        },
        expose_fragment=True,
    )
    ticks = iter([4.0, 4.01])
    calls: list[str] = []
    monkeypatch.setattr(ui_layout, "st", fake_st)
    monkeypatch.setattr(ui_layout, "perf_counter", lambda: next(ticks))

    ui_layout.render_fragment_pilot_panel(
        step_key="role_tasks",
        panel_id="salary_forecast",
        render_slot=lambda: calls.append("rendered"),
    )

    assert calls == ["rendered"]
    assert fake_st.fragment_calls == 1
    event = fake_st.session_state[SSKey.USAGE_EVENTS.value][0]
    assert event["metadata"]["path"] == "role_tasks.salary_forecast"
    assert event["metadata"]["duration_ms"] == 10
    assert event["metadata"]["fragment_enabled"] is True
