from __future__ import annotations

import streamlit as st

from config.preferences import (
    PAGE_DEFS,
    build_runtime_context,
    ensure_preference_state,
)


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
        st.markdown('<div class="cs-sidebar-title">Navigation</div>', unsafe_allow_html=True)

        st.markdown("#### Seiten")
        for page in PAGE_DEFS:
            if page.key not in SIDEBAR_HIDDEN_PAGE_KEYS:
                st.page_link(page.path, label=page.title)

        st.markdown('<div class="cs-sidebar-gap"></div>', unsafe_allow_html=True)

        with st.expander("Aktiver Runtime-Kontext"):
            st.json(build_runtime_context())
