# pages/02_Über_Cognitive_Staffing.py
from __future__ import annotations

import streamlit as st

from i18n import (
    LANGUAGE_WIDGET_KEY_SIDEBAR,
    bootstrap_public_page,
    render_language_toggle,
    tr,
)
from site_ui import (
    inject_site_styles,
    render_cards,
    render_cta,
    render_hero,
    render_meta_line,
)


PREFIX = "public_pages.about"


def _copy(key: str, **params: object) -> str:
    return tr(f"{PREFIX}.{key}", **params)


bootstrap_public_page(page_title=_copy("title"), page_icon="🏢")
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
        {"title": _copy(f"cards.{key}.title"), "body": _copy(f"cards.{key}.body")}
        for key in ("career", "offer", "goal")
    ],
    columns=3,
)

st.markdown(_copy("why.heading"))
st.markdown(_copy("why.body"))

render_cta(_copy("cta.title"), _copy("cta.body"))
