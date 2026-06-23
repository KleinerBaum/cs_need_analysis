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


PREFIX = "public_pages.terms"


def _copy(key: str, **params: object) -> str:
    return tr(f"{PREFIX}.{key}", **params)


bootstrap_public_page(page_title=_copy("title"), page_icon="📄")
inject_site_styles()
render_language_toggle(location="sidebar", key=LANGUAGE_WIDGET_KEY_SIDEBAR)

render_hero(
    title=_copy("title"),
    lead=_copy("hero.lead"),
    eyebrow=_copy("hero.eyebrow"),
)
render_meta_line(profile_last_updated_label())

st.markdown(_copy("offer.heading"))
st.markdown(_copy("offer.body"))

st.markdown(_copy("no_advice.heading"))
st.markdown(_copy("no_advice.body"))

st.markdown(_copy("permitted_use.heading"))
st.markdown(_copy("permitted_use.body"))

st.markdown(_copy("user_responsibility.heading"))
st.markdown(_copy("user_responsibility.body"))

st.markdown(_copy("availability.heading"))
st.markdown(_copy("availability.body"))

st.markdown(_copy("changes.heading"))
st.markdown(_copy("changes.body"))

st.markdown(_copy("ip.heading"))
st.markdown(_copy("ip.body"))

st.markdown(_copy("liability.heading"))
st.markdown(_copy("liability.body"))

render_callout(
    _copy("callout.title"),
    _copy("callout.body"),
)

st.markdown(_copy("final.heading"))
st.markdown(_copy("final.body"))

render_cta(
    _copy("cta.title"),
    _copy("cta.body", email=PROFILE.email),
)
