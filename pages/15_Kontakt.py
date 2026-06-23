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
    render_callout,
    render_cards,
    render_cta,
    render_hero,
    render_meta_line,
)


PREFIX = "public_pages.contact"
POLICY_LABEL_KEYS = {
    "Impressum": "policy_links.imprint",
    "Datenschutzrichtlinie": "policy_links.privacy",
    "Nutzungsbedingungen": "policy_links.terms",
    "Cookie Policy Settings": "policy_links.cookies",
    "Erklärung zur Barrierefreiheit": "policy_links.accessibility",
}


def _copy(key: str, **params: object) -> str:
    return tr(f"{PREFIX}.{key}", **params)


def _legal_policy_links() -> tuple[tuple[str, str], ...]:
    return (
        ("pages/03_Impressum.py", "Impressum"),
        ("pages/11_Datenschutzrichtlinie.py", "Datenschutzrichtlinie"),
        ("pages/12_Nutzungsbedingungen.py", "Nutzungsbedingungen"),
        ("pages/13_Cookie_Policy_Settings.py", "Cookie Policy Settings"),
        ("pages/14_Erklaerung_zur_Barrierefreiheit.py", "Erklärung zur Barrierefreiheit"),
    )


bootstrap_public_page(page_title=_copy("title"), page_icon="✉️")
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
        {
            "title": _copy(f"cards.{key}.title"),
            "body": _copy(f"cards.{key}.body"),
        }
        for key in ("decision_makers", "hr", "it")
    ],
    columns=3,
)

col_left, col_right = st.columns([1.05, 1.15], gap="large")

with col_left:
    st.markdown(_copy("reach.heading"))
    st.markdown(
        _copy(
            "reach.body",
            email=PROFILE.email,
            phone=PROFILE.phone,
            legal_entity=PROFILE.legal_entity,
            street=localized_profile_value(PROFILE.street),
            postal_code=localized_profile_value(PROFILE.postal_code),
            city=localized_profile_value(PROFILE.city),
            country=localized_profile_value(PROFILE.country),
        )
    )

    render_callout(
        _copy("privacy_notice.title"),
        _copy("privacy_notice.body"),
    )

with col_right:
    st.markdown(_copy("form.heading"))
    with st.form("contact_form", clear_on_submit=False):
        name = st.text_input(_copy("form.name"))
        company = st.text_input(_copy("form.company"))
        email = st.text_input(_copy("form.email"))
        topic = st.selectbox(
            _copy("form.topic"),
            options=[
                _copy("form.topic_options.demo"),
                _copy("form.topic_options.product"),
                _copy("form.topic_options.technical"),
                _copy("form.topic_options.partnership"),
                _copy("form.topic_options.other"),
            ],
        )
        message = st.text_area(
            _copy("form.message"),
            placeholder=_copy("form.message_placeholder"),
            height=160,
        )
        submitted = st.form_submit_button(_copy("form.submit"))

    if submitted:
        st.success(_copy("form.success"))
        st.code(
            _copy(
                "form.summary",
                name=name,
                company=company,
                email=email,
                topic=topic,
                message=message,
            ),
            language="text",
        )

render_cta(
    _copy("cta.title"),
    _copy("cta.body", email=PROFILE.email),
)

st.markdown(_copy("policy_links.heading"))
for page_path, label in _legal_policy_links():
    st.page_link(page_path, label=_copy(POLICY_LABEL_KEYS[label]))
