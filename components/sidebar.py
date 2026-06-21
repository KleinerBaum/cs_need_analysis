from __future__ import annotations

import streamlit as st

from config.preferences import (
    PAGE_DEFS,
    build_runtime_context,
    ensure_preference_state,
)
from safe_html import render_static_html


SIDEBAR_HIDDEN_PAGE_KEYS = frozenset(
    {
        "preference_center",
        "privacy",
        "terms",
        "accessibility",
        "contact",
    }
)


def render_sidebar(current_page_key: str) -> None:
    del current_page_key
    ensure_preference_state()

    with st.sidebar:
        render_static_html(
            '<div class="cs-sidebar-title">Navigation</div>',
            streamlit_module=st,
        )

        st.markdown("#### Seiten")
        for page in PAGE_DEFS:
            if page.key not in SIDEBAR_HIDDEN_PAGE_KEYS:
                st.page_link(page.path, label=page.title)

        render_static_html(
            '<div class="cs-sidebar-gap"></div>',
            streamlit_module=st,
        )

        with st.expander("Aktiver Runtime-Kontext"):
            st.json(build_runtime_context())
