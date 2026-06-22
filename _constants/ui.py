"""UI mode and preference constants."""

from __future__ import annotations

from typing import Final

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

UI_MODE_PRIORITY_TIERS: Final[dict[str, tuple[str, ...]]] = {
    "quick": ("core",),
    "standard": ("core", "standard"),
    "expert": ("core", "standard", "detail"),
}
UI_MODE_QUESTION_LIMIT_RATIOS: Final[dict[str, float]] = {
    "quick": 0.30,
    "standard": 0.50,
    "expert": 1.00,
}
