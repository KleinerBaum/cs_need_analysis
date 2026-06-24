"""UI mode and preference constants."""

from __future__ import annotations

from typing import Final

from _constants.wizard import (
    STEP_KEY_BENEFITS,
    STEP_KEY_COMPANY,
    STEP_KEY_INTERVIEW,
    STEP_KEY_ROLE_TASKS,
    STEP_KEY_SKILLS,
)

UI_MODE_VALUES: Final[tuple[str, str, str]] = ("quick", "standard", "expert")
UI_MODE_DEFAULT: Final[str] = "standard"
UI_MODE_DISPLAY_LABELS: Final[dict[str, str]] = {
    "quick": "schnell",
    "standard": "ausführlich",
    "expert": "vollumfänglich",
}
UI_DETAILS_DEFAULT_BY_MODE_TEXT: Final[str] = (
    f"{UI_MODE_DISPLAY_LABELS['quick'].capitalize()}/"
    f"{UI_MODE_DISPLAY_LABELS['standard'].capitalize()}: "
    "Detailgruppen standardmäßig kompakt. "
    f"{UI_MODE_DISPLAY_LABELS['expert'].capitalize()}: "
    "Detailgruppen standardmäßig geöffnet."
)
UI_MODE_HELP_TEXT: Final[str] = UI_DETAILS_DEFAULT_BY_MODE_TEXT
UI_GLOBAL_DETAILS_TOGGLE_LABEL: Final[str] = "Details standardmäßig öffnen"
UI_GLOBAL_DETAILS_TOGGLE_HELP: Final[str] = (
    "Globale Voreinstellung für Detailgruppen in allen Wizard-Schritten. "
    f"{UI_DETAILS_DEFAULT_BY_MODE_TEXT}"
)
UI_STEP_COMPACT_TOGGLE_LABEL: Final[str] = "Details kompakt anzeigen"
UI_STEP_COMPACT_TOGGLE_HELP: Final[str] = (
    "Schritt-spezifische Anzeige: Aktiv hält Detailgruppen standardmäßig geschlossen. "
    "Deaktiviert öffnet Detailgruppen standardmäßig."
)
UI_PREFERENCE_ANSWER_MODE: Final[str] = "answer_mode"
UI_PREFERENCE_INFORMATION_DEPTH: Final[str] = "information_depth"
UI_PREFERENCE_ESCO_MATCHING_STRICTNESS: Final[str] = "esco_matching_strictness"
UI_PREFERENCE_REGIONAL_FOCUS: Final[str] = "regional_focus"
UI_PREFERENCE_SHOW_SOURCES_DEFAULT: Final[str] = "show_sources_default"
UI_PREFERENCE_CONFIDENCE_THRESHOLD: Final[str] = "confidence_threshold"
UI_PREFERENCE_PII_REDUCTION: Final[str] = "pii_reduction"
UI_PREFERENCE_DETAILS_EXPANDED_DEFAULT: Final[str] = "details_expanded_default"
UI_PREFERENCE_STEP_COMPACT: Final[str] = "step_compact"
UI_PREFERENCE_UI_LANGUAGE: Final[str] = "ui_language"
UI_PREFERENCE_WIZARD_DESIGN: Final[str] = "wizard_design"
UI_LANGUAGE_VALUES: Final[tuple[str, str]] = ("de", "en")
UI_LANGUAGE_QUERY_PARAM: Final[str] = "lang"
UI_LANGUAGE_STORAGE_KEY: Final[str] = "cs.ui_language"
UI_LANGUAGE_COOKIE_KEY: Final[str] = "cs_ui_language"
UI_LANGUAGE_WIDGET_KEY_SIDEBAR: Final[str] = "sidebar.ui_language"
UI_LANGUAGE_WIDGET_KEY_PAGE: Final[str] = "page.ui_language"
UI_LANGUAGE_WIDGET_KEYS: Final[tuple[str, str]] = (
    UI_LANGUAGE_WIDGET_KEY_SIDEBAR,
    UI_LANGUAGE_WIDGET_KEY_PAGE,
)
UI_LANGUAGE_LAST_WIDGET_KEY: Final[str] = "cs.language.last_widget_key"

UI_MODE_PRIORITY_TIERS: Final[dict[str, tuple[str, ...]]] = {
    "quick": ("core",),
    "standard": ("core", "standard"),
    "expert": ("core", "standard", "detail"),
}
UI_MODE_QUESTION_LIMIT_RATIOS: Final[dict[str, float]] = {
    "quick": 0.20,
    "standard": 0.35,
    "expert": 1.00,
}
UI_MODE_STEP_QUESTION_CAPS: Final[dict[str, dict[str, int]]] = {
    "quick": {
        STEP_KEY_COMPANY: 1,
        STEP_KEY_ROLE_TASKS: 2,
        STEP_KEY_SKILLS: 2,
        STEP_KEY_BENEFITS: 1,
        STEP_KEY_INTERVIEW: 1,
    },
    "standard": {
        STEP_KEY_COMPANY: 4,
        STEP_KEY_ROLE_TASKS: 5,
        STEP_KEY_SKILLS: 4,
        STEP_KEY_BENEFITS: 3,
        STEP_KEY_INTERVIEW: 3,
    },
    "expert": {},
}

UI_WIZARD_DESIGN_CLASSIC: Final[str] = "classic"
UI_WIZARD_DESIGN_FOCUS: Final[str] = "focus"
UI_WIZARD_DESIGN_DEFAULT: Final[str] = UI_WIZARD_DESIGN_CLASSIC
UI_WIZARD_DESIGN_VALUES: Final[tuple[str, str]] = (
    UI_WIZARD_DESIGN_CLASSIC,
    UI_WIZARD_DESIGN_FOCUS,
)
UI_WIZARD_DESIGN_DISPLAY_LABELS: Final[dict[str, str]] = {
    UI_WIZARD_DESIGN_CLASSIC: "Klassisch",
    UI_WIZARD_DESIGN_FOCUS: "Fokus",
}
