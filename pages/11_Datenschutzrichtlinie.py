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
    localized_profile_value,
    profile_last_updated_label,
    render_callout,
    render_cta,
    render_hero,
    render_meta_line,
)


PREFIX = "public_pages.privacy"


def _copy(key: str, **params: object) -> str:
    return tr(f"{PREFIX}.{key}", **params)


bootstrap_public_page(page_title=_copy("title"), page_icon="🔒")
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

st.markdown(_copy("controller.heading"))
st.markdown(
    _copy(
        "controller.body",
        legal_entity=PROFILE.legal_entity,
        street=localized_profile_value(PROFILE.street),
        postal_code=localized_profile_value(PROFILE.postal_code),
        city=localized_profile_value(PROFILE.city),
        country=localized_profile_value(PROFILE.country),
        email=PROFILE.email,
        phone=PROFILE.phone,
        website=PROFILE.website,
    )
)

st.markdown(_copy("privacy_contact.heading"))
st.markdown(
    _copy(
        "privacy_contact.body",
        privacy_email=PROFILE.privacy_email,
        dpo_name=localized_profile_value(PROFILE.dpo_name),
    )
)

st.markdown(_copy("processed_data.heading"))
st.markdown(_copy("processed_data.body"))

st.markdown(_copy("purposes.heading"))
st.markdown(_copy("purposes.body"))

st.markdown(_copy("hr_content.heading"))
st.markdown(_copy("hr_content.body"))

st.markdown(_copy("legal_basis.heading"))
st.markdown(_copy("legal_basis.body"))

st.markdown(_copy("recipients.heading"))
for key in ("hosting", "ai", "email", "consent"):
    st.markdown(f"- {_copy(f'recipients.providers.{key}')}")

st.markdown(_copy("recipients.body"))

st.markdown(_copy("retention.heading"))
st.markdown(_copy("retention.body"))

st.markdown(_copy("cookies.heading"))
st.markdown(_copy("cookies.body"))

st.markdown(_copy("rights.heading"))
st.markdown(_copy("rights.body"))

st.markdown(_copy("security.heading"))
st.markdown(_copy("security.body"))

render_cta(
    _copy("cta.title"),
    _copy("cta.body", privacy_email=PROFILE.privacy_email),
)
