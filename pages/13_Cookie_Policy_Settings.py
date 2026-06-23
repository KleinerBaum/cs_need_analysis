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
    render_cards,
    render_cta,
    render_hero,
    render_meta_line,
)


PREFIX = "public_pages.cookies"


def _copy(key: str, **params: object) -> str:
    return tr(f"{PREFIX}.{key}", **params)


bootstrap_public_page(page_title=_copy("page_title"), page_icon="🍪")
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

st.markdown(_copy("choices.heading"))
st.markdown(_copy("choices.body"))

render_cards(
    [
        {
            "title": _copy(f"categories.{key}.title"),
            "body": _copy(f"categories.{key}.body"),
        }
        for key in ("necessary", "preferences", "statistics", "external")
    ],
    columns=2,
)

st.markdown(_copy("consent.heading"))
st.markdown(_copy("consent.body"))

st.markdown(_copy("transparency.heading"))
st.markdown(_copy("transparency.body"))

st.markdown(_copy("examples.heading"))
st.markdown(_copy("examples.body"))

render_cta(
    _copy("cta.title"),
    _copy("cta.body", privacy_email=PROFILE.privacy_email),
)
