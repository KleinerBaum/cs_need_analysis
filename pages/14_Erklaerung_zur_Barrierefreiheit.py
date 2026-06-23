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
    profile_last_updated_label,
    render_callout,
    render_cta,
    render_hero,
    render_meta_line,
)


PREFIX = "public_pages.accessibility"


def _copy(key: str, **params: object) -> str:
    return tr(f"{PREFIX}.{key}", **params)


bootstrap_public_page(page_title=_copy("title"), page_icon="♿")
inject_site_styles()
render_language_toggle(location="sidebar", key=LANGUAGE_WIDGET_KEY_SIDEBAR)

render_hero(
    title=_copy("title"),
    lead=_copy("hero.lead"),
    eyebrow=_copy("hero.eyebrow"),
)
render_meta_line(profile_last_updated_label())

render_callout(
    _copy("notice.title"),
    _copy("notice.body"),
    tone="warning",
)

st.markdown(_copy("status.heading"))
st.markdown(_copy("status.body"))

st.markdown(_copy("standard.heading"))
st.markdown(_copy("standard.body"))

st.markdown(_copy("implemented.heading"))
st.markdown(_copy("implemented.body"))

st.markdown(_copy("barriers.heading"))
st.markdown(_copy("barriers.body"))

st.markdown(_copy("feedback.heading"))
st.markdown(
    _copy(
        "feedback.body",
        accessibility_email=PROFILE.accessibility_email,
        email=PROFILE.email,
    )
)

st.markdown(_copy("enforcement.heading"))
st.markdown(_copy("enforcement.body"))

render_cta(
    _copy("cta.title"),
    _copy("cta.body", accessibility_email=PROFILE.accessibility_email),
)
