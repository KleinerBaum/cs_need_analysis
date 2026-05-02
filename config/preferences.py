"""Canonical constants for page routing, labels, preference keys, and legal sections.
Keep UI labels, session keys, logic, exports, and analytics tags aligned here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from constants import APP_NAME, APP_TAGLINE

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
