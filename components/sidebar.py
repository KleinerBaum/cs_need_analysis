from __future__ import annotations

import streamlit as st

from config.constants import COOKIE_CATEGORIES, PAGE_DEFS, PREFERENCE_KEYS
from config.preferences import (
    build_runtime_context,
    ensure_preference_state,
    get_cookie_consent,
    get_preferences,
    update_cookie,
    update_preference,
)


def render_sidebar(current_page_key: str) -> None:
    ensure_preference_state()
    prefs = get_preferences()
    consent = get_cookie_consent()

    with st.sidebar:
        st.markdown('<div class="cs-sidebar-title">Navigation</div>', unsafe_allow_html=True)

        for page in PAGE_DEFS:
            if page.key != "preference_center":
                st.page_link(page.path, label=page.title)

        st.markdown('<div class="cs-sidebar-gap"></div>', unsafe_allow_html=True)

        with st.expander("Präferenz-Center", expanded=(current_page_key == "preference_center")):
            ui_language = st.selectbox(
                "Sprache",
                options=["de", "en"],
                index=["de", "en"].index(prefs[PREFERENCE_KEYS["ui_language"]]),
                help="Steuert UI-Texte, Standard-Response-Language und Exportsprache.",
            )
            update_preference(PREFERENCE_KEYS["ui_language"], ui_language)

            response_mode = st.selectbox(
                "Antwortmodus",
                options=["compact", "balanced", "advisory"],
                index=["compact", "balanced", "advisory"].index(prefs[PREFERENCE_KEYS["response_mode"]]),
                help="Compact = schnell; Balanced = Standard; Advisory = mehr Einordnung.",
            )
            update_preference(PREFERENCE_KEYS["response_mode"], response_mode)

            info_depth = st.select_slider(
                "Informationstiefe",
                options=["light", "standard", "deep"],
                value=prefs[PREFERENCE_KEYS["info_depth"]],
            )
            update_preference(PREFERENCE_KEYS["info_depth"], info_depth)

            esco_match_strictness = st.slider(
                "ESCO-Matching-Strenge",
                min_value=0,
                max_value=100,
                step=5,
                value=int(prefs[PREFERENCE_KEYS["esco_match_strictness"]]),
                help="Niedrig = mehr Recall. Hoch = präzisere, engere Treffer.",
            )
            update_preference(PREFERENCE_KEYS["esco_match_strictness"], esco_match_strictness)

            regional_focus = st.selectbox(
                "Regionaler Fokus",
                options=["DACH", "EU", "Global"],
                index=["DACH", "EU", "Global"].index(prefs[PREFERENCE_KEYS["regional_focus"]]),
            )
            update_preference(PREFERENCE_KEYS["regional_focus"], regional_focus)

            privacy_mode = st.selectbox(
                "Privacy-Modus",
                options=["minimal", "balanced", "strict"],
                index=["minimal", "balanced", "strict"].index(prefs[PREFERENCE_KEYS["privacy_mode"]]),
                help="Strict reduziert Kontextspeicherung und fordert bewusstere Datenfreigaben.",
            )
            update_preference(PREFERENCE_KEYS["privacy_mode"], privacy_mode)

            accessibility_mode = st.selectbox(
                "Accessibility",
                options=["standard", "high_contrast", "reduced_motion"],
                index=["standard", "high_contrast", "reduced_motion"].index(prefs[PREFERENCE_KEYS["accessibility_mode"]]),
            )
            update_preference(PREFERENCE_KEYS["accessibility_mode"], accessibility_mode)

            output_format = st.selectbox(
                "Standard-Ausgabeformat",
                options=["cards", "table", "narrative"],
                index=["cards", "table", "narrative"].index(prefs[PREFERENCE_KEYS["output_format"]]),
            )
            update_preference(PREFERENCE_KEYS["output_format"], output_format)

            include_sources = st.toggle(
                "Quellen standardmäßig einblenden",
                value=bool(prefs[PREFERENCE_KEYS["include_sources"]]),
            )
            update_preference(PREFERENCE_KEYS["include_sources"], include_sources)

            reuse_profile_context = st.toggle(
                "Profilkontext wizardweit wiederverwenden",
                value=bool(prefs[PREFERENCE_KEYS["reuse_profile_context"]]),
            )
            update_preference(PREFERENCE_KEYS["reuse_profile_context"], reuse_profile_context)

            st.markdown("#### Cookies")
            for category, label in COOKIE_CATEGORIES.items():
                disabled = category == "essential"
                cookie_value = st.toggle(
                    label,
                    value=bool(consent[category]),
                    disabled=disabled,
                    key=f"cookie_toggle_{category}",
                )
                update_cookie(category, cookie_value)

            st.page_link("pages/10_Praeferenz_Center.py", label="Vollansicht öffnen")

        with st.expander("Aktiver Runtime-Kontext"):
            st.json(build_runtime_context())
