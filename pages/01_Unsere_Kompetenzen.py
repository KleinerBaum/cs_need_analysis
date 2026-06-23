# pages/01_Unsere_Kompetenzen.py
from __future__ import annotations

import streamlit as st

from i18n import (
    LANGUAGE_WIDGET_KEY_SIDEBAR,
    bootstrap_public_page,
    render_language_toggle,
    tr,
)
from site_ui import (
    PROFILE,
    inject_site_styles,
    render_callout,
    render_cards,
    render_cta,
    render_hero,
    render_meta_line,
)


PREFIX = "public_pages.competencies"


def _copy(key: str, **params: object) -> str:
    return tr(f"{PREFIX}.{key}", **params)


def _markdown(key: str) -> None:
    st.markdown(_copy(key))


bootstrap_public_page(page_title=_copy("title"), page_icon="🧠")
inject_site_styles()
render_language_toggle(location="sidebar", key=LANGUAGE_WIDGET_KEY_SIDEBAR)

render_hero(
    title=_copy("title"),
    lead=_copy("hero.lead"),
    eyebrow=_copy("hero.eyebrow"),
)
render_meta_line(_copy("meta"))

render_cards(
    [
        {"title": _copy(f"top_cards.{key}.title"), "body": _copy(f"top_cards.{key}.body")}
        for key in (
            "structured_intake",
            "dynamic_flow",
            "esco_semantics",
            "controlled_ai",
            "salary_estimation",
            "exports",
        )
    ],
    columns=3,
)

st.markdown(_copy("how.heading"))
_markdown("how.body")

for key in ("intake", "dynamic", "sharpening"):
    with st.expander(_copy(f"expanders.{key}.title"), expanded=True):
        _markdown(f"expanders.{key}.body")

st.markdown(_copy("esco.heading"))
_markdown("esco.body")
render_callout(_copy("esco.callout_title"), _copy("esco.callout_body"))

col_a, col_b = st.columns(2)
with col_a:
    _markdown("esco.column_a")
with col_b:
    _markdown("esco.column_b")
_markdown("esco.after")

st.markdown(_copy("model.heading"))
_markdown("model.body")
render_callout(_copy("model.callout_title"), _copy("model.callout_body"))

st.markdown(_copy("dynamic_flow.heading"))
_markdown("dynamic_flow.body")

st.markdown(_copy("downstream.heading"))
render_cards(
    [
        {"title": _copy(f"downstream.cards.{key}.title"), "body": _copy(f"downstream.cards.{key}.body")}
        for key in (
            "brief",
            "job_ad",
            "interview",
            "boolean",
            "exports",
        )
    ],
    columns=3,
)

st.markdown(_copy("security.heading"))
_markdown("security.body")
with st.expander(_copy("security.local_llm.title"), expanded=True):
    _markdown("security.local_llm.body")

render_cta(
    _copy("cta.title"),
    _copy("cta.body", brand=PROFILE.brand_name),
)
