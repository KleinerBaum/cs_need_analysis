"""Canonical constants for page routing, labels, preference keys, and legal sections.
Keep UI labels, session keys, logic, exports, and analytics tags aligned here.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, List

import streamlit as st

from constants import APP_NAME as APP_NAME, APP_TAGLINE as APP_TAGLINE

SESSION_KEYS = {
    "preferences": "cs_preferences",
    "cookie_consent": "cs_cookie_consent",
    "wizard_context": "cs_wizard_context",
}

PREFERENCE_KEYS = {
    "ui_language": "ui_language",
    "response_mode": "response_mode",
    "info_depth": "info_depth",
    "esco_match_strictness": "esco_match_strictness",
    "privacy_mode": "privacy_mode",
    "accessibility_mode": "accessibility_mode",
    "regional_focus": "regional_focus",
    "output_format": "output_format",
    "include_sources": "include_sources",
    "reuse_profile_context": "reuse_profile_context",
}

COOKIE_CATEGORIES = {
    "essential": "Technisch erforderlich",
    "analytics": "Analytics",
    "personalization": "Personalisierung",
    "marketing": "Marketing",
}

DEFAULT_PREFERENCES: Dict[str, Any] = {
    PREFERENCE_KEYS["ui_language"]: "de",
    PREFERENCE_KEYS["response_mode"]: "balanced",
    PREFERENCE_KEYS["info_depth"]: "standard",
    PREFERENCE_KEYS["esco_match_strictness"]: 70,
    PREFERENCE_KEYS["privacy_mode"]: "balanced",
    PREFERENCE_KEYS["accessibility_mode"]: "standard",
    PREFERENCE_KEYS["regional_focus"]: "DACH",
    PREFERENCE_KEYS["output_format"]: "cards",
    PREFERENCE_KEYS["include_sources"]: True,
    PREFERENCE_KEYS["reuse_profile_context"]: True,
}

DEFAULT_COOKIE_CONSENT: Dict[str, bool] = {
    "essential": True,
    "analytics": False,
    "personalization": True,
    "marketing": False,
}

LEGAL_SECTION_KEYS = {
    "privacy": "privacy",
    "terms": "terms",
    "cookies": "cookies",
    "accessibility": "accessibility",
    "imprint": "imprint",
}

@dataclass(frozen=True)
class PageDef:
    key: str
    title: str
    path: str
    nav_group: str
    is_main_nav: bool = True


PAGE_DEFS: List[PageDef] = [
    PageDef("competencies", "Unsere Kompetenzen", "pages/01_Unsere_Kompetenzen.py", "main", True),
    PageDef("about", "Über Cognitive Staffing", "pages/02_Ueber_Cognitive_Staffing.py", "main", True),
    PageDef("imprint", "Impressum", "pages/03_Impressum.py", "main", True),
    PageDef("preference_center", "Präferenz-Center", "pages/10_Praeferenz_Center.py", "preferences", False),
    PageDef("privacy", "Datenschutzrichtlinie", "pages/11_Datenschutzrichtlinie.py", "legal", False),
    PageDef("terms", "Nutzungsbedingungen", "pages/12_Nutzungsbedingungen.py", "legal", False),
    PageDef("cookies", "Cookie Policy/Settings", "pages/13_Cookie_Policy_Settings.py", "legal", False),
    PageDef("accessibility", "Erklärung zur Barrierefreiheit", "pages/14_Erklaerung_zur_Barrierefreiheit.py", "legal", False),
    PageDef("contact", "Kontakt", "pages/15_Kontakt.py", "legal", False),
]

PAGE_LOOKUP: Dict[str, PageDef] = {page.key: page for page in PAGE_DEFS}


def ensure_preference_state() -> None:
    preferences = st.session_state.get(SESSION_KEYS["preferences"])
    if not isinstance(preferences, dict):
        preferences = {}
    st.session_state[SESSION_KEYS["preferences"]] = {
        **deepcopy(DEFAULT_PREFERENCES),
        **preferences,
    }

    cookie_consent = st.session_state.get(SESSION_KEYS["cookie_consent"])
    if not isinstance(cookie_consent, dict):
        cookie_consent = {}
    st.session_state[SESSION_KEYS["cookie_consent"]] = {
        **deepcopy(DEFAULT_COOKIE_CONSENT),
        **cookie_consent,
        "essential": True,
    }


def get_preferences() -> Dict[str, Any]:
    ensure_preference_state()
    return st.session_state[SESSION_KEYS["preferences"]]


def get_cookie_consent() -> Dict[str, bool]:
    ensure_preference_state()
    return st.session_state[SESSION_KEYS["cookie_consent"]]


def update_preference(key: str, value: Any) -> None:
    ensure_preference_state()
    st.session_state[SESSION_KEYS["preferences"]][key] = value


def update_cookie(category: str, value: bool) -> None:
    if category not in COOKIE_CATEGORIES:
        raise KeyError(f"Unknown cookie category: {category}")
    ensure_preference_state()
    if category == "essential":
        st.session_state[SESSION_KEYS["cookie_consent"]][category] = True
        return
    st.session_state[SESSION_KEYS["cookie_consent"]][category] = value


def build_runtime_context() -> Dict[str, Any]:
    prefs = get_preferences()
    consent = get_cookie_consent()
    return {
        "ui": {
            "language": prefs[PREFERENCE_KEYS["ui_language"]],
            "accessibility_mode": prefs[PREFERENCE_KEYS["accessibility_mode"]],
            "output_format": prefs[PREFERENCE_KEYS["output_format"]],
        },
        "retrieval": {
            "regional_focus": prefs[PREFERENCE_KEYS["regional_focus"]],
            "esco_match_strictness": prefs[PREFERENCE_KEYS["esco_match_strictness"]],
            "reuse_profile_context": prefs[PREFERENCE_KEYS["reuse_profile_context"]],
        },
        "generation": {
            "response_mode": prefs[PREFERENCE_KEYS["response_mode"]],
            "info_depth": prefs[PREFERENCE_KEYS["info_depth"]],
            "include_sources": prefs[PREFERENCE_KEYS["include_sources"]],
            "privacy_mode": prefs[PREFERENCE_KEYS["privacy_mode"]],
        },
        "consent": consent,
    }
