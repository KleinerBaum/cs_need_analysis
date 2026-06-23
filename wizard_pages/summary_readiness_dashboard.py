# wizard_pages/summary_readiness_dashboard.py
"""Readiness dashboard rendering helpers for the Summary page."""

from __future__ import annotations

from contextlib import nullcontext
from typing import Any, Callable

import streamlit as st

from wizard_pages.summary_readiness import SummaryViewModel


def render_summary_readiness_metrics(
    vm: SummaryViewModel,
    *,
    streamlit_module: Any = st,
) -> None:
    brief_label = {
        "current": "Aktuell",
        "stale": "Veraltet",
        "missing": "Fehlt",
        "invalid": "Ungültig",
        "blocked": "Blockiert",
    }.get(vm.status.brief_state, vm.status.brief_status_label)
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
    streamlit_module: Any = st,
) -> None:
    container = (
        streamlit_module.container(border=True)
        if hasattr(streamlit_module, "container")
        else nullcontext()
    )
    with container:
        if hasattr(streamlit_module, "markdown"):
            streamlit_module.markdown("### Bereitschaftsübersicht")
        if hasattr(streamlit_module, "columns"):
            metric_renderer(vm)
        if hasattr(streamlit_module, "caption"):
            streamlit_module.caption(
                "Diese Kennzahlen steuern die nächsten Artefakte; "
                "Detailwerte stehen im Fakten-Workspace."
            )
