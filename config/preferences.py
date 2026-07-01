"""Canonical constants for page routing, labels, preference keys, and legal sections.
Keep UI labels, session keys, logic, exports, and analytics tags aligned here.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, List

import streamlit as st

from constants import APP_NAME as APP_NAME, APP_TAGLINE as APP_TAGLINE

PAGE_ROUTE_TYPE_FILE = "file"
PAGE_ROUTE_TYPE_QUERY_PARAM = "query_param"
PREFERENCE_CENTER_QUERY_PARAM = "page"
PREFERENCE_CENTER_QUERY_VALUE = "preferences"

SESSION_KEYS = {
    "preferences": "cs_preferences",
    "wizard_context": "cs_wizard_context",
}

PREFERENCE_KEYS = {
    "ui_language": "ui_language",
    "response_mode": "response_mode",
    "info_depth": "info_depth",
    "privacy_mode": "privacy_mode",
    "accessibility_mode": "accessibility_mode",
    "output_format": "output_format",
    "include_sources": "include_sources",
    "reuse_profile_context": "reuse_profile_context",
}

DEFAULT_PREFERENCES: Dict[str, Any] = {
    PREFERENCE_KEYS["ui_language"]: "de",
    PREFERENCE_KEYS["response_mode"]: "advisory",
    PREFERENCE_KEYS["info_depth"]: "hoch",
    PREFERENCE_KEYS["privacy_mode"]: "balanced",
    PREFERENCE_KEYS["accessibility_mode"]: "standard",
    PREFERENCE_KEYS["output_format"]: "cards",
    PREFERENCE_KEYS["include_sources"]: True,
    PREFERENCE_KEYS["reuse_profile_context"]: True,
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
    route_type: str = PAGE_ROUTE_TYPE_FILE
    query_params: Dict[str, str] | None = None


PAGE_DEFS: List[PageDef] = [
    PageDef("competencies", "Unsere Kompetenzen", "pages/01_Unsere_Kompetenzen.py", "main", True),
    PageDef("about", "Über Cognitive Staffing", "pages/02_Über_Cognitive_Staffing.py", "main", True),
    PageDef("imprint", "Impressum", "pages/03_Impressum.py", "main", True),
    PageDef(
        "preference_center",
        "Präferenz-Center",
        "app.py",
        "preferences",
        False,
        PAGE_ROUTE_TYPE_QUERY_PARAM,
        {PREFERENCE_CENTER_QUERY_PARAM: PREFERENCE_CENTER_QUERY_VALUE},
    ),
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


def get_preferences() -> Dict[str, Any]:
    ensure_preference_state()
    return st.session_state[SESSION_KEYS["preferences"]]


def update_preference(key: str, value: Any) -> None:
    ensure_preference_state()
    st.session_state[SESSION_KEYS["preferences"]][key] = value


def build_runtime_context() -> Dict[str, Any]:
    prefs = get_preferences()
    return {
        "ui": {
            "language": prefs[PREFERENCE_KEYS["ui_language"]],
            "accessibility_mode": prefs[PREFERENCE_KEYS["accessibility_mode"]],
            "output_format": prefs[PREFERENCE_KEYS["output_format"]],
        },
        "retrieval": {
            "reuse_profile_context": prefs[PREFERENCE_KEYS["reuse_profile_context"]],
        },
        "generation": {
            "response_mode": prefs[PREFERENCE_KEYS["response_mode"]],
            "info_depth": prefs[PREFERENCE_KEYS["info_depth"]],
            "include_sources": prefs[PREFERENCE_KEYS["include_sources"]],
            "privacy_mode": prefs[PREFERENCE_KEYS["privacy_mode"]],
        },
        "storage": {
            "language_preference": True,
            "session_preferences": True,
            "draft_recovery_metadata": True,
            "analytics": False,
            "marketing": False,
        },
    }
