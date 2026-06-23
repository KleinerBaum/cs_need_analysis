# wizard_pages/summary_readiness_dashboard.py
"""Readiness dashboard rendering helpers for the Summary page."""

from __future__ import annotations

from contextlib import nullcontext
from typing import Any, Callable

import streamlit as st

from wizard_pages.summary_readiness import (
    SummaryViewModel,
    _build_missing_critical_items,
    _release_gate_headline,
    _release_state_label,
)


def render_summary_readiness_metrics(
    vm: SummaryViewModel,
    *,
    streamlit_module: Any = st,
) -> None:
    brief_label = _release_state_label(vm.status.brief_state)
    metrics = (
        ("Bereitschaft", f"{vm.status.readiness_percent}%"),
        ("Kritische Fakten", vm.status.completion_text),
        ("ESCO", "Bestätigt" if vm.status.esco_ready else "Offen"),
        ("Brief", brief_label),
    )
    metric_columns = streamlit_module.columns(2)
    for index, (label, value) in enumerate(metrics):
        metric_columns[index % len(metric_columns)].metric(label, value)


def render_readiness_dashboard_header(
    vm: SummaryViewModel,
    *,
    metric_renderer: Callable[[SummaryViewModel], None],
    blocker_count: int | None = None,
    streamlit_module: Any = st,
) -> None:
    resolved_blocker_count = (
        len(_build_missing_critical_items(vm))
        if blocker_count is None
        else max(0, int(blocker_count))
    )
    container = (
        streamlit_module.container(border=True)
        if hasattr(streamlit_module, "container")
        else nullcontext()
    )
    with container:
        if hasattr(streamlit_module, "markdown"):
            streamlit_module.markdown(
                "### "
                + _release_gate_headline(
                    readiness_percent=vm.status.readiness_percent,
                    blocker_count=resolved_blocker_count,
                )
            )
        if hasattr(streamlit_module, "columns"):
            metric_renderer(vm)
        if hasattr(streamlit_module, "caption"):
            streamlit_module.caption(
                "Diese Übersicht entscheidet, welche Unterlagen exportierbar sind "
                "und welche Eingaben vorher geprüft werden müssen."
            )
