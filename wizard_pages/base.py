# wizard_pages/base.py
"""Wizard base utilities (page model + navigation helpers)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List

import streamlit as st

from constants import SSKey, STEPS


@dataclass(frozen=True)
class WizardPage:
    key: str
    title_de: str
    icon: str
    render: Callable[["WizardContext"], None]
    requires_jobspec: bool = False

    @property
    def label(self) -> str:
        return f"{self.icon} {self.title_de}" if self.icon else self.title_de


@dataclass
class WizardContext:
    pages: List[WizardPage]

    def get_current_page_key(self) -> str:
        return st.session_state.get(SSKey.CURRENT_STEP.value, STEPS[0].key)

    def goto(self, key: str) -> None:
        st.session_state[SSKey.CURRENT_STEP.value] = key
        st.rerun()

    def next(self) -> None:
        cur = self.get_current_page_key()
        keys = [p.key for p in self.pages]
        if cur in keys:
            i = keys.index(cur)
            if i < len(keys) - 1:
                self.goto(keys[i + 1])

    def prev(self) -> None:
        cur = self.get_current_page_key()
        keys = [p.key for p in self.pages]
        if cur in keys:
            i = keys.index(cur)
            if i > 0:
                self.goto(keys[i - 1])


def sidebar_navigation(ctx: WizardContext) -> WizardPage:
    pages = ctx.pages
    cur_key = ctx.get_current_page_key()
    options = [p.key for p in pages]
    format_map = {p.key: p.label for p in pages}

    def _format(k: str) -> str:
        return format_map.get(k, k)

    selected = st.sidebar.radio(
        "Wizard",
        options=options,
        index=options.index(cur_key) if cur_key in options else 0,
        format_func=_format,
    )
    if selected != cur_key:
        st.session_state[SSKey.CURRENT_STEP.value] = selected
        st.rerun()

    current_page = next(p for p in pages if p.key == selected)
    return current_page


def nav_buttons(ctx: WizardContext, *, disable_next: bool = False, disable_prev: bool = False) -> None:
    c1, c2, c3 = st.columns([1, 1, 3])
    with c1:
        st.button("← Zurück", on_click=ctx.prev, disabled=disable_prev)
    with c2:
        st.button("Weiter →", on_click=ctx.next, disabled=disable_next)
    with c3:
        st.caption("Fortschritt wird automatisch in dieser Session gespeichert.")
