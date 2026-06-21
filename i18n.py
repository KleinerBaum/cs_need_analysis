"""Small UI translation layer for German-source wizard copy."""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable

import streamlit as st

from constants import SSKey, UI_PREFERENCE_UI_LANGUAGE


SUPPORTED_UI_LANGUAGES = ("de", "en")
LANGUAGE_WIDGET_KEYS = (
    "sidebar.ui_language",
    "page.ui_language",
    f"{SSKey.ESCO_CONFIG.value}.language_choice",
    f"{SSKey.ESCO_CONFIG.value}.phase_a.language",
)
LAST_LANGUAGE_WIDGET_KEY = "cs.language.last_widget_key"

_TRANSLATIONS_EN: dict[str, str] = {
    "Einleitung": "Introduction",
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
    "niedrig": "low",
    "hoch": "high",
    "locker": "loose",
    "ausgewogen": "balanced",
    "streng": "strict",
    "standard": "standard",
    "ja": "yes",
    "nein": "no",
    "Später": "Later",
    "Nicht übernommen": "Not applied",
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
    "Zum Start": "Go to Start",
    "Debug: OpenAI-Auflösung": "Debug: OpenAI resolution",
    "Nur aufgelöste Laufzeitwerte, keine Secrets.": "Resolved runtime values only, no secrets.",
    "Stellenanzeige einlesen und Intake starten": "Import job ad and start intake",
    "Anzeige hochladen oder einfügen": "Upload or paste job ad",
    "Vakanzanforderungen präzise erfassen": "Capture vacancy requirements precisely",
    "Bevor Recruiting beginnt, muss klar sein, welche Person wirklich gesucht wird.": "Before recruiting begins, it must be clear which person is really needed.",
    "Aus langjähriger Erfahrung in der Personalvermittlung zeigt sich immer wieder: Essentielle Informationen zu einer Vakanz ändern sich oft erst im laufenden Bewerbungsprozess, werden zu spät sichtbar oder fehlen vollständig. Das kann Abstimmungsschleifen, Fehlbesetzungen und hohe Folgekosten verursachen.": "Years of recruiting experience show the same pattern again and again: essential information about a vacancy often changes during the application process, appears too late, or is missing entirely. This can create alignment loops, hiring mistakes, and high downstream costs.",
    "Gerade in großen Unternehmen werden regelmäßig ähnliche Qualitäten gesucht und auf Basis derselben Stellenanzeige ausgeschrieben. Die individuellen Charakteristika einer konkreten Vakanz bleiben dabei häufig zu unscharf.": "Especially in large organizations, similar qualities are often needed and advertised from the same job ad. The individual characteristics of a specific vacancy often remain too vague.",
    "Diese App fokussiert ausschließlich den ersten Schritt jedes Recruiting-Prozesses: Der fachliche Vorgesetzte definiert, welchen Mitarbeiter er sucht. Diverse Funktionen helfen dabei, mit möglichst wenig Aufwand ein umfassendes Bild der Stelle zu erstellen. Dafür nutzt die App die europäische Berufs- und Skill-Taxonomie ESCO sowie die OpenAI-API, um den Informationsgewinnungsprozess dynamisch an die individuellen Bedürfnisse Ihrer Vakanz anzupassen.": "This app focuses exclusively on the first step of every recruiting process: the hiring manager defines which employee they are looking for. A set of focused functions helps create a comprehensive picture of the role with as little effort as possible. To do that, the app uses the European occupation and skills taxonomy ESCO as well as the OpenAI API to dynamically adapt the information-gathering process to the individual needs of your vacancy.",
    "Bereit, die Anforderungen Ihrer Vakanz richtig kennenzulernen? Probieren Sie es aus.": "Ready to properly understand the requirements of your vacancy? Try it out.",
    "Von der Jobspec zum klaren Recruiting-Bild.": "From job spec to a clear recruiting picture.",
    "Die App liest eine Stellenanzeige ein, erkennt den fachlichen Kontext und fragt nur dort nach, wo Informationen für gute Recruiting-Entscheidungen fehlen.": "The app reads a job ad, detects the professional context, and only asks where information is missing for good recruiting decisions.",
    "Warum der Intake mehr sieht": "Why the intake sees more",
    "Was passiert danach?": "What happens next?",
    "Nach dem Start": "After starting",
    'Nach dem Klick auf "Analyse starten"': 'After clicking "Start analysis"',
    "Text verstehen": "Understand text",
    "Upload oder Freitext wird gelesen und in ein sauberes Rollenprofil überführt.": "Upload or free text is read and converted into a clean role profile.",
    "Beruf verankern": "Anchor occupation",
    "Die App sucht den passenden ESCO-Beruf als gemeinsame Referenz.": "The app searches for the matching ESCO occupation as a shared reference.",
    "Fragen priorisieren": "Prioritize questions",
    "Nur fehlende oder unsichere Punkte werden für den Wizard vorbereitet.": "Only missing or uncertain points are prepared for the wizard.",
    "Weiterverarbeiten": "Continue processing",
    "Aufgaben, Skills, Benefits, Interview- und Summary-Artefakte bauen darauf auf.": "Tasks, skills, benefits, interview, and summary artifacts build on it.",
    "Ergebnis: weniger manuelle Sortierarbeit und eine bessere Grundlage für alle Recruiting-Aktivitäten.": "Result: less manual sorting and a better foundation for all recruiting activities.",
    "Mehr Kontext:": "More context:",
    "Was ist ESCO?": "What is ESCO?",
    "Was bedeutet RAG?": "What does RAG mean?",
    "Warum Need Analysis?": "Why need analysis?",
    "Kurzer Kontext, warum die App nicht nur sichtbare Anforderungen, sondern auch Lücken und implizite Bedarfstreiber strukturiert.": "Brief context on why the app structures not only visible requirements, but also gaps and implicit demand drivers.",
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
    "Analyse starten": "Start analysis",
    "Analyseergebnis": "Analysis result",
    "Berufsabgleich": "Occupation matching",
    "Berufsabgleich bestätigen": "Confirm occupation match",
    "Quelle bearbeiten": "Edit source",
    "Erkannte Angaben prüfen": "Review detected information",
    "Angaben übernehmen": "Apply information",
    "Angaben übernommen.": "Information applied.",
    "Ein paar Informationen vorab": "A few details first",
    "Unternehmenswebsite": "Company website",
    "Hinweise aus der Website-Analyse": "Insights from website analysis",
    "Strukturierter Kontext": "Structured context",
    "Unternehmensprofil": "Company profile",
    "Team & Reporting": "Team & reporting",
    "Arbeitsmodell": "Work model",
    "Non-negotiables & Compliance": "Non-negotiables & compliance",
    "Outcome & Scope": "Outcome & scope",
    "Priorisierung": "Prioritization",
    "Erfolg und Entscheidungsspielraum": "Success and decision scope",
    "Reiseprofil": "Travel profile",
    "Auswirkung auf Prognose": "Impact on forecast",
    "Skills präzisieren und priorisieren": "Clarify and prioritize skills",
    "Weitere AI-Vorschläge": "More AI suggestions",
    "AI-Vorschläge": "AI suggestions",
    "AI-Vorschläge ergänzen": "Add AI suggestions",
    "Erkannte und ausgewählte Benefits": "Detected and selected benefits",
    "Einflussfaktoren": "Influence factors",
    "Details zu Einflussfaktoren": "Details on influence factors",
    "Variable Vergütung": "Variable compensation",
    "Arbeitszeit, Schicht und Ausgleich": "Working time, shifts, and compensation",
    "Vertrags- und Offer-Komponenten": "Contract and offer components",
    "Interne Rollen und Ansprechpartner": "Internal roles and contacts",
    "Interviewstufen": "Interview stages",
    "Stage Owner": "Stage owner",
    "Candidate Update SLA": "Candidate update SLA",
    "Assessment Evidence": "Assessment evidence",
    "Scorecard": "Scorecard",
    "Stage & Evaluation": "Stage & evaluation",
    "Interviewprozess definieren": "Define interview process",
    "Candidate Communication": "Candidate communication",
    "Readiness-Übersicht": "Readiness overview",
    "Artefaktübersicht": "Artifact overview",
    "Quellen & Details prüfen": "Review sources and details",
    "Recruiting Brief": "Recruiting brief",
    "Frageblöcke": "Question blocks",
    "Bewertungsrubrik": "Evaluation rubric",
    "Empfehlungsoptionen": "Recommendation options",
    "Kompetenzen validieren": "Validate competencies",
    "Debrief-Fragen": "Debrief questions",
    "Klauseln": "Clauses",
    "Keine Vorschläge.": "No suggestions.",
    "Keine Einträge.": "No entries.",
    "Keine Treffer für die aktuellen Filter.": "No matches for the current filters.",
    "Keine sichtbaren Fragen in diesem Schritt.": "No visible questions in this step.",
    "Antworten übernehmen": "Apply answers",
    "Antworten übernommen.": "Answers applied.",
    "Übernehmen": "Apply",
    "Weitere Sprache hinzufügen": "Add another language",
    "Taxonomie laden": "Load taxonomy",
    "Top-Treffer wurde per Enter übernommen.": "Top match was applied via Enter.",
    "Referenzberuf auswählen": "Select reference occupation",
    "Kontextrolle auswählen": "Select context role",
    "Suchbegriff für Berufsabgleich": "Search term for occupation matching",
    "Suchbegriff für Kontextrolle": "Search term for context role",
    "Bestätigter Referenzberuf": "Confirmed reference occupation",
    "Bestätigte ESCO-Auswahl": "Confirmed ESCO selection",
    "Ausgewählte Kontextrolle": "Selected context role",
    "Als Kontextanker hinzufügen": "Add as context anchor",
    "Kontextanker hinzugefügt.": "Context anchor added.",
    "Ohne bestätigten Referenzberuf fortfahren": "Continue without a confirmed reference occupation",
    "Später erneut versuchen": "Try again later",
    "URI kopieren": "Copy URI",
    "URI zum Kopieren eingeblendet.": "URI shown for copying.",
    "Mehr Details": "More details",
    "Warum Berufsabgleich?": "Why occupation matching?",
    "Warum dieser Vorschlag?": "Why this suggestion?",
    "Geladene Occupation-Titelvarianten": "Loaded occupation title variants",
    "Nur verfügbare Felder anzeigen": "Show available fields only",
    "Portal öffnen": "Open portal",
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
    "beantwortet": "answered",
    "Fehlt (essentiell)": "Missing (essential)",
    "Sicherheit": "Confidence",
    "Technische Details": "Technical details",
    "Vorschläge": "Suggestions",
    "Ausgewählt": "Selected",
    "Ausgewählte": "Selected",
    "Ausgewählter": "Selected",
    "Noch keine": "No",
    "Keine": "No",
    "Berufsabgleich": "Occupation matching",
    "Analyse läuft": "Analysis running",
    "Analyse abgeschlossen": "Analysis complete",
    "Informationen extrahiert und Fragebogen erzeugt": "information extracted and questionnaire generated",
    "Mindestens ein Ergebnis wurde aus dem Cache geladen": "At least one result was loaded from cache",
    "Die Quelle ist sehr kurz": "The source is very short",
    "Die Extraktion kann unvollstaendig sein": "Extraction may be incomplete",
    "Datei bereit": "File ready",
    "Unbekannt": "Unknown",
    "Extraktion fehlgeschlagen": "Extraction failed",
    "Zeichen": "Characters",
    "Quelle": "Source",
    "Upload": "Upload",
    "Text": "Text",
    "Manuell erfasste URL": "Manually entered URL",
    "Website-Analyse": "website analysis",
    "Arbeitsmodell": "Work model",
    "Aufgaben": "tasks",
    "Skills": "skills",
    "Benefits": "benefits",
    "Fragen": "questions",
    "Antworten": "answers",
    "Essentials offen": "Open essentials",
    "Gruppenstatus": "Group status",
    "vollständig beantwortet": "fully answered",
    "vollständig": "complete",
    "offen": "open",
    "weitere": "more",
    "Rolle": "Role",
    "Zielregionen": "Target regions",
    "Primäre Query": "Primary query",
    "Beobachtbare Evidenz": "Observable evidence",
    "Skala": "Scale",
    "Keine kritischen Lücken erkannt": "No critical gaps detected",
    "Kritische Lücken": "Critical gaps",
    "Bereit": "Ready",
    "Erfüllt": "Met",
    "Ungültig": "Invalid",
    "ungültig": "invalid",
    "Offene Lücken": "Open gaps",
    "Nächster verfügbarer Schritt": "Next available step",
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


def sync_language_from_widget_key(
    widget_key: str, *, session_state: Any | None = None
) -> str | None:
    state = session_state if session_state is not None else st.session_state
    if widget_key not in state:
        return None
    raw_language = state.get(widget_key)
    normalized = normalize_language(raw_language)
    if normalized != raw_language:
        return None
    synced_language = sync_language_state(normalized, session_state=state)
    state[LAST_LANGUAGE_WIDGET_KEY] = widget_key
    return synced_language


def sync_language_from_known_widgets(*, session_state: Any | None = None) -> str | None:
    state = session_state if session_state is not None else st.session_state
    last_widget_key = state.get(LAST_LANGUAGE_WIDGET_KEY)
    if isinstance(last_widget_key, str):
        synced_language = sync_language_from_widget_key(
            last_widget_key, session_state=state
        )
        if synced_language is not None:
            return synced_language
    for widget_key in LANGUAGE_WIDGET_KEYS:
        synced_language = sync_language_from_widget_key(
            widget_key, session_state=state
        )
        if synced_language is not None:
            return synced_language
    return None


def sync_streamlit_language_widget(widget_key: str) -> None:
    sync_language_from_widget_key(widget_key)


def _translate_first_string_arg(args: tuple[Any, ...]) -> tuple[Any, ...]:
    if args and isinstance(args[0], str):
        return (t(args[0]), *args[1:])
    return args


def _translate_label_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    translated = dict(kwargs)
    for key in ("label", "help", "placeholder"):
        if isinstance(translated.get(key), str):
            translated[key] = t(translated[key])
    options = translated.get("options")
    if (
        "format_func" not in translated
        and isinstance(options, (list, tuple))
        and all(isinstance(option, str) for option in options)
    ):
        translated["format_func"] = lambda option: t(option)
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
