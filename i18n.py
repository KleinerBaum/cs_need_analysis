"""Small UI translation layer for German-source wizard copy."""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable

import streamlit as st

from constants import SSKey, UI_PREFERENCE_UI_LANGUAGE


SUPPORTED_UI_LANGUAGES = ("de", "en")

_TRANSLATIONS_EN: dict[str, str] = {
    "Start": "Start",
    "Unternehmen": "Company",
    "Rolle & Aufgaben": "Role & tasks",
    "Skills & Anforderungen": "Skills & requirements",
    "Benefits & Rahmenbedingungen": "Benefits & conditions",
    "Interviewprozess": "Interview process",
    "Zusammenfassung": "Summary",
    "schnell": "quick",
    "ausführlich": "standard",
    "vollumfänglich": "full",
    "Schnell": "Quick",
    "Ausführlich": "Standard",
    "Vollumfänglich": "Full",
    "Prozess": "Process",
    "Sprache": "Language",
    "Sprache für Vorschläge": "Language for suggestions",
    "Alternative Sprache": "Fallback language",
    "Wie weit möchten Sie ins Detail gehen?": "How much detail do you want?",
    "Detailgrad aktiv: **Schnell** (`quick`)": "Active detail level: **Quick** (`quick`)",
    "Detailgrad aktiv: **Ausführlich** (`standard`)": "Active detail level: **Standard** (`standard`)",
    "Detailgrad aktiv: **Vollumfänglich** (`expert`)": "Active detail level: **Full** (`expert`)",
    "Der Modus steuert, wie viele Fragen im aktuellen Schritt sichtbar sind.": "The mode controls how many questions are visible in the current step.",
    "Antwortmodus": "Response mode",
    "Informationstiefe": "Information depth",
    "ESCO-Matching-Strenge": "ESCO matching strictness",
    "Regionaler Fokus": "Regional focus",
    "Confidence-Schwelle für Treffer": "Confidence threshold for matches",
    "PII-Reduktion": "PII reduction",
    "Details standardmäßig öffnen": "Open details by default",
    "Details kompakt anzeigen": "Show details compactly",
    "Präferenz-Center": "Preference center",
    "Globale Einstellungen gelten wizard-weit.": "Global settings apply across the wizard.",
    "Advanced / Bestehende Detail-Einstellungen": "Advanced / existing detail settings",
    "← Zurück zum Wizard": "Back to wizard",
    "Globale Steuerung für den aktuellen Wizard-Kontext.": "Global controls for the current wizard context.",
    "Seiten": "Pages",
    "Reset Vacancy": "Reset vacancy",
    "← Zurück": "Back",
    "Weiter →": "Next",
    "Bitte zuerst im Start-Schritt eine Analyse durchführen.": "Please run an analysis in the Start step first.",
    "Zur Startseite": "Go to start page",
    "Debug: OpenAI-Auflösung": "Debug: OpenAI resolution",
    "Nur aufgelöste Laufzeitwerte, keine Secrets.": "Resolved runtime values only, no secrets.",
    "Stellenanzeige einlesen und Intake starten": "Import job ad and start intake",
    "Von der Jobspec zum klaren Recruiting-Bild.": "From job spec to a clear recruiting picture.",
    "Die App liest eine Stellenanzeige ein, erkennt den fachlichen Kontext und fragt nur dort nach, wo Informationen für gute Recruiting-Entscheidungen fehlen.": "The app reads a job ad, detects the professional context, and only asks where information is missing for good recruiting decisions.",
    "Warum der Intake mehr sieht": "Why the intake sees more",
    "Was passiert danach?": "What happens next?",
    "Datenschutz und Kontrolle": "Privacy and control",
    "Weniger Rückfragen": "Fewer follow-up questions",
    "Der Wizard fragt gezielt nach, statt ein starres Formular abzuarbeiten.": "The wizard asks targeted questions instead of running through a rigid form.",
    "Klarer Rollenanker": "Clear role anchor",
    "Jobtitel werden mit ESCO abgeglichen, damit alle Folgeschritte denselben Berufskontext nutzen.": "Job titles are matched with ESCO so every later step uses the same occupation context.",
    "Direkt nutzbare Outputs": "Ready-to-use outputs",
    "Aus dem Intake entstehen strukturierte Informationen für Recruiting, Hiring-Team und Summary.": "The intake produces structured information for recruiting, the hiring team, and the summary.",
    "1. Beruf eindeutig verankern": "1. Anchor the occupation clearly",
    "Die Rolle wird auf einen klaren ESCO-Beruf gemappt, damit alle Folgeschritte denselben Kontext nutzen.": "The role is mapped to a clear ESCO occupation so all later steps use the same context.",
    "2. Anforderungen strukturieren": "2. Structure requirements",
    "Skills, Aufgaben und Muss-/Kann-Kriterien werden normalisiert und in einen nutzbaren Plan überführt.": "Skills, tasks, and must-have/nice-to-have criteria are normalized into a usable plan.",
    "3. Recruiting-Artefakte erzeugen": "3. Generate recruiting artifacts",
    "Die App erstellt belastbare Texte, Zusammenfassungen und Folge-Outputs für Recruiting und Hiring-Team.": "The app creates robust text, summaries, and follow-up outputs for recruiting and the hiring team.",
    "Vor der Verarbeitung können sensible personenbezogene Angaben optional reduziert werden. Ziel ist eine datensparsame, nachvollziehbare Nutzung im Vacancy Intake.": "Before processing, sensitive personal information can optionally be reduced. The goal is data-minimizing, traceable use in vacancy intake.",
    "Start ist gesperrt, bis die Einwilligung bestätigt wurde. Start is blocked until consent is confirmed.": "Start is blocked until consent is confirmed.",
    "Wenn für eure Organisation Designated Content freigegeben ist, können diese Inhalte von OpenAI zu Entwicklungszwecken genutzt werden (inkl. Training, Evaluierung, Tests). Ihr müsst Endnutzende informieren und – falls erforderlich – Einwilligungen einholen.": "If designated content is enabled for your organization, this content may be used by OpenAI for development purposes, including training, evaluation, and testing. You must inform end users and obtain consent where required.",
    "Offen kommunizierbar": "Can be communicated openly",
    "Intern begrenzt": "Limited internally",
    "Vertraulich / neutralisieren": "Confidential / neutralize",
    "Noch unklar": "Still unclear",
    "Ersatz / Backfill": "Replacement / backfill",
    "Wachstum": "Growth",
    "Neue Rolle / Neuaufbau": "New role / build-up",
    "Interne Nachfolge": "Internal succession",
    "Vertrauliche Suche": "Confidential search",
    "Planbar": "Plannable",
    "Relevant": "Relevant",
    "Dringend": "Urgent",
    "Kritisch / sofort": "Critical / immediate",
    "Intern kalibriert": "Internally calibrated",
    "Teilweise kalibriert": "Partly calibrated",
    "Noch unscharf": "Still vague",
    "Auswahl übernehmen": "Apply selection",
    "Auswahl verwerfen": "Discard selection",
    "Legacy-URI migrieren": "Migrate legacy URI",
    "ESCO-Konfiguration aktualisiert. Cache wurde invalidiert.": "ESCO configuration updated. Cache was invalidated.",
}

_PHRASE_TRANSLATIONS_EN: dict[str, str] = {
    "Globale Voreinstellung für Detailgruppen in allen Wizard-Schritten.": "Global default for detail groups in all wizard steps.",
    "Schritt-spezifische Anzeige: Aktiv hält Detailgruppen standardmäßig geschlossen.": "Step-specific display: enabled keeps detail groups closed by default.",
    "Deaktiviert öffnet Detailgruppen standardmäßig.": "Disabled opens detail groups by default.",
    "Bitte explizit auswählen.": "Please choose explicitly.",
    "Legacy-URI erkannt.": "Legacy URI detected.",
    "Bitte migrieren, damit aktuelle ESCO-Daten konsistent geladen werden.": "Please migrate so current ESCO data can be loaded consistently.",
    "Nicht angegeben": "Not specified",
    "Offen": "Open",
    "Teilweise": "Partial",
    "Vollständig": "Complete",
}

_PATCHED = False


def normalize_language(raw_language: object) -> str:
    language = str(raw_language or "de").strip().lower()
    return language if language in SUPPORTED_UI_LANGUAGES else "de"


def active_language() -> str:
    language = normalize_language(st.session_state.get(SSKey.LANGUAGE.value, "de"))
    preferences = st.session_state.get(SSKey.UI_PREFERENCES.value, {})
    if isinstance(preferences, dict):
        language = normalize_language(
            preferences.get(UI_PREFERENCE_UI_LANGUAGE, language)
        )
    return language


def t(text: object, *, language: str | None = None) -> object:
    if not isinstance(text, str):
        return text
    selected_language = normalize_language(language or active_language())
    if selected_language != "en":
        return text
    translated = _TRANSLATIONS_EN.get(text)
    if translated is not None:
        return translated
    output = text
    for source, target in _PHRASE_TRANSLATIONS_EN.items():
        output = output.replace(source, target)
    return output


def sync_language_state(language: object, *, session_state: Any | None = None) -> str:
    normalized = normalize_language(language)
    state = session_state if session_state is not None else st.session_state
    state[SSKey.LANGUAGE.value] = normalized
    preferences = state.get(SSKey.UI_PREFERENCES.value, {})
    if isinstance(preferences, dict):
        updated_preferences = dict(preferences)
        updated_preferences[UI_PREFERENCE_UI_LANGUAGE] = normalized
        state[SSKey.UI_PREFERENCES.value] = updated_preferences
    config = state.get(SSKey.ESCO_CONFIG.value, {})
    if isinstance(config, dict):
        fallback_language = "en" if normalized == "de" else "de"
        state[SSKey.ESCO_CONFIG.value] = {
            **config,
            "language": normalized,
            "fallback_language": fallback_language,
        }
    return normalized


def _translate_first_string_arg(args: tuple[Any, ...]) -> tuple[Any, ...]:
    if args and isinstance(args[0], str):
        return (t(args[0]), *args[1:])
    return args


def _translate_label_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    translated = dict(kwargs)
    for key in ("label", "help", "placeholder"):
        if isinstance(translated.get(key), str):
            translated[key] = t(translated[key])
    return translated


def _wrap_text_method(method: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(method)
    def wrapped(self: Any, *args: Any, **kwargs: Any) -> Any:
        return method(self, *_translate_first_string_arg(args), **_translate_label_kwargs(kwargs))

    return wrapped


def _wrap_tabs(method: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(method)
    def wrapped(self: Any, tabs: Any, *args: Any, **kwargs: Any) -> Any:
        if isinstance(tabs, (list, tuple)):
            tabs = [t(item) if isinstance(item, str) else item for item in tabs]
        return method(self, tabs, *args, **_translate_label_kwargs(kwargs))

    return wrapped


def patch_streamlit_text() -> None:
    """Patch Streamlit label rendering once so legacy German labels respect UI language."""

    global _PATCHED
    if _PATCHED:
        return
    try:
        from streamlit.delta_generator import DeltaGenerator
    except Exception:
        return

    text_methods = (
        "title",
        "header",
        "subheader",
        "caption",
        "markdown",
        "info",
        "warning",
        "success",
        "error",
        "button",
        "toggle",
        "checkbox",
        "radio",
        "selectbox",
        "select_slider",
        "slider",
        "text_input",
        "text_area",
        "file_uploader",
        "page_link",
        "expander",
        "metric",
        "multiselect",
    )
    for name in text_methods:
        method = getattr(DeltaGenerator, name, None)
        if method is not None and not getattr(method, "_cs_i18n_patched", False):
            wrapped = _wrap_text_method(method)
            setattr(wrapped, "_cs_i18n_patched", True)
            setattr(DeltaGenerator, name, wrapped)

    tabs_method = getattr(DeltaGenerator, "tabs", None)
    if tabs_method is not None and not getattr(tabs_method, "_cs_i18n_patched", False):
        wrapped_tabs = _wrap_tabs(tabs_method)
        setattr(wrapped_tabs, "_cs_i18n_patched", True)
        setattr(DeltaGenerator, "tabs", wrapped_tabs)

    _PATCHED = True
