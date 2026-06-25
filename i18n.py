"""Small UI translation layer for German-source wizard copy."""

from __future__ import annotations

import base64
import json
from functools import lru_cache, wraps
from pathlib import Path
from typing import Any, Callable, Mapping

import streamlit as st

from constants import (
    DEFAULT_LANGUAGE,
    SSKey,
    UI_LANGUAGE_COOKIE_KEY,
    UI_LANGUAGE_LAST_WIDGET_KEY,
    UI_LANGUAGE_QUERY_PARAM,
    UI_LANGUAGE_STORAGE_KEY,
    UI_LANGUAGE_VALUES,
    UI_LANGUAGE_WIDGET_KEY_PAGE,
    UI_LANGUAGE_WIDGET_KEY_SIDEBAR,
    UI_LANGUAGE_WIDGET_KEYS,
    UI_PREFERENCE_UI_LANGUAGE,
)
from ui_widget_state import ensure_option_widget_state


SUPPORTED_UI_LANGUAGES = UI_LANGUAGE_VALUES
LANGUAGE_WIDGET_KEY_SIDEBAR = UI_LANGUAGE_WIDGET_KEY_SIDEBAR
LANGUAGE_WIDGET_KEY_PAGE = UI_LANGUAGE_WIDGET_KEY_PAGE
LANGUAGE_WIDGET_KEYS = UI_LANGUAGE_WIDGET_KEYS
LAST_LANGUAGE_WIDGET_KEY = UI_LANGUAGE_LAST_WIDGET_KEY
LOCALES_DIR = Path(__file__).resolve().parent / "locales"

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
    "Unsere Kompetenzen": "Our competencies",
    "Über Cognitive Staffing": "About Cognitive Staffing",
    "Über uns": "About us",
    "Impressum": "Imprint",
    "Impressum (Template)": "Imprint (template)",
    "Datenschutzrichtlinie": "Privacy policy",
    "Nutzungsbedingungen": "Terms of use",
    "Cookie Policy/Settings": "Cookie policy/settings",
    "Cookie Policy & Einstellungen": "Cookie policy & settings",
    "Erklärung zur Barrierefreiheit": "Accessibility statement",
    "Kontakt": "Contact",
    "Kontakt & Demo": "Contact & demo",
    "Rechtliches": "Legal",
    "Rechtliche Information": "Legal information",
    "Datenschutz": "Privacy",
    "Barrierefreiheit": "Accessibility",
    "Cookies & Präferenzen": "Cookies & preferences",
    "Wichtiger Hinweis": "Important note",
    "Hinweis": "Note",
    "AI-gestützte Kompetenz- und Matching-Workflows": (
        "AI-supported competency and matching workflows"
    ),
    "Rechtliche Seite · Template": "Legal page · template",
    "Diese Seite ist eine Vorlage und wird erst nach rechtlicher Prüfung verbindlich.": (
        "This page is a template and becomes binding only after legal review."
    ),
    "🟧 **Platzhalter – Fachinput fehlt**": "🟧 **Placeholder – subject-matter input missing**",
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
    "Briefing-Cockpit öffnen": "Open briefing cockpit",
    "Debug: OpenAI-Auflösung": "Debug: OpenAI resolution",
    "Nur aufgelöste Laufzeitwerte, keine Secrets.": "Resolved runtime values only, no secrets.",
    "Stellenanzeige einlesen und Intake starten": "Import job ad and start intake",
    "Anzeige hochladen oder einfügen": "Upload or paste job ad",
    "Recruiting-Briefing vor Workflow": "Recruiting brief before workflow",
    "Erst klären, welche Entscheidung ansteht. Danach den Wizard gezielt nutzen.": "Clarify the decision first. Then use the wizard with focus.",
    "Die App beginnt vor der Stellenanzeige: Aus Jobspec, Upload oder Rohtext entsteht zuerst ein prüfbarer Briefing-Stand für Search, Matching, Interview und Angebot.": "The app starts before the job ad: a jobspec, upload, or raw text first becomes a reviewable briefing status for search, matching, interviews, and offers.",
    "Erkannte Fakten, offene Lücken, ESCO-Referenzberufe und Folgefragen bleiben nachvollziehbar getrennt. Sie prüfen Werte, bevor daraus Recruiting-Unterlagen entstehen.": "Detected facts, open gaps, ESCO reference occupations, and follow-up questions stay traceably separated. You review values before recruiting outputs are created from them.",
    "Starten Sie mit einer Quelle und erhalten Sie zuerst ein Recruiting-Briefing, nicht ein Formular.": "Start with a source and get a recruiting brief first, not a form.",
    "Briefing bereits vorbereitet": "Briefing already prepared",
    "Die Einleitung ist jetzt optional. Öffnen Sie direkt den Start, prüfen Sie die erkannte Briefing-Basis und bestätigen Sie den Referenzberuf.": "The introduction is now optional. Open Start directly, review the detected briefing basis, and confirm the reference occupation.",
    "Vakanzanforderungen präzise erfassen": "Capture vacancy requirements precisely",
    "Bevor Recruiting beginnt, muss klar sein, welche Person wirklich gesucht wird.": "Before recruiting begins, it must be clear which person is really needed.",
    "Aus langjähriger Erfahrung in der Personalvermittlung zeigt sich immer wieder: Essentielle Informationen zu einer Vakanz ändern sich oft erst im laufenden Bewerbungsprozess, werden zu spät sichtbar oder fehlen vollständig. Das kann Abstimmungsschleifen, Fehlbesetzungen und hohe Folgekosten verursachen.": "Years of recruiting experience show the same pattern again and again: essential information about a vacancy often changes during the application process, appears too late, or is missing entirely. This can create alignment loops, hiring mistakes, and high downstream costs.",
    "Gerade in großen Unternehmen werden regelmäßig ähnliche Qualitäten gesucht und auf Basis derselben Stellenanzeige ausgeschrieben. Die individuellen Charakteristika einer konkreten Vakanz bleiben dabei häufig zu unscharf.": "Especially in large organizations, similar qualities are often needed and advertised from the same job ad. The individual characteristics of a specific vacancy often remain too vague.",
    "Diese App fokussiert ausschließlich den ersten Schritt jedes Recruiting-Prozesses: Der fachliche Vorgesetzte definiert, welchen Mitarbeiter er sucht. Diverse Funktionen helfen dabei, mit möglichst wenig Aufwand ein umfassendes Bild der Stelle zu erstellen. Dafür nutzt die App die europäische Berufs- und Skill-Taxonomie ESCO sowie die OpenAI-API, um den Informationsgewinnungsprozess dynamisch an die individuellen Bedürfnisse Ihrer Vakanz anzupassen.": "This app focuses exclusively on the first step of every recruiting process: the hiring manager defines which employee they are looking for. A set of focused functions helps create a comprehensive picture of the role with as little effort as possible. To do that, the app uses the European occupation and skills taxonomy ESCO as well as the OpenAI API to dynamically adapt the information-gathering process to the individual needs of your vacancy.",
    "Bereit, die Anforderungen Ihrer Vakanz richtig kennenzulernen? Probieren Sie es aus.": "Ready to properly understand the requirements of your vacancy? Try it out.",
    "Das Eisberg-Modell zeigt, welche sichtbaren und verdeckten Informationen ein gutes Recruiting-Briefing zusammenführt.": "The iceberg model shows which visible and hidden information a strong recruiting brief brings together.",
    "Von der Jobspec zum belastbaren Recruiting-Briefing": "From jobspec to reliable recruiting brief",
    "Die Stellenanzeige zeigt, was bekannt ist. Die App macht sichtbar, was für Search, Matching, Interview und Angebot wirklich entschieden werden muss.": "The job ad shows what is known. The app reveals what really needs to be decided for search, matching, interviews, and the offer.",
    "sichtbar im Jobprofil - hilfreich, aber selten entscheidungsreif": "visible in the job profile - useful, but rarely decision-ready",
    "Titel, Standort, Arbeitsmodell, Vertragsart und Startfenster werden erfasst.": "Title, location, work model, contract type, and start window are captured.",
    "Titel": "Title",
    "Vertrag": "Contract",
    "Aufgaben, Projekte und Reportinglinien sind sichtbar - Wirkung und Priorität bleiben oft offen.": "Tasks, projects, and reporting lines are visible - impact and priority often remain open.",
    "Output": "Output",
    "Skills, Erfahrung, Tools und Sprachen werden gesammelt - meist noch ohne Härtegrad.": "Skills, experience, tools, and languages are collected - usually without severity levels yet.",
    "Gehalt, Benefits, Startdatum und Interviewprozess werden genannt, aber selten verknüpft.": "Salary, benefits, start date, and interview process are stated, but rarely connected.",
    "Gehalt": "Salary",
    "oberhalb: sichtbar in Jobspec, Stellenanzeige und erstem Briefing": "above: visible in jobspec, job ad, and first briefing",
    "unterhalb: entscheidend für Search, Matching, Interview und Zusage": "below: essential for search, matching, interview, and offer acceptance",
    "AI- & ESCO-gestütztes Recruiting-Briefing": "AI- and ESCO-supported recruiting brief",
    "Die App macht verdeckte Bedarfstreiber prüfbar, priorisierbar und direkt weiterverwendbar.": "The app makes hidden need drivers reviewable, prioritizable, and directly reusable.",
    "Geprüfte Faktenbasis": "Reviewed fact base",
    "Extraktion, Fundstellen, Confidence, Gaps und Annahmen werden reviewbar, bevor daraus Entscheidungen entstehen.": "Extraction, evidence locations, confidence, gaps, and assumptions become reviewable before decisions are made from them.",
    "Evidenz": "Evidence",
    "Gaps": "Gaps",
    "Review": "Review",
    "Prioritäten & Kompromisse": "Priorities and trade-offs",
    "Must-have, Nice-to-have, trainierbare Anforderungen und KO-Kriterien werden sauber getrennt.": "Must-haves, nice-to-haves, trainable requirements, and no-go criteria are clearly separated.",
    "Trainierbar": "Trainable",
    "No-Go": "No-go",
    "Outcome-Logik": "Outcome logic",
    "Erfolg nach 30/60/90/180 Tagen, Business Impact und Entscheidungsumfang werden explizit.": "Success after 30/60/90/180 days, business impact, and decision scope become explicit.",
    "Impact": "Impact",
    "90 Tage": "90 days",
    "Erfolg": "Success",
    "Semantisches Matching": "Semantic matching",
    "ESCO-Anker, Skill-Mapping und Titelvarianten machen Anforderungen vergleichbarer und suchfähiger.": "ESCO anchors, skill mapping, and title variants make requirements more comparable and searchable.",
    "Angebots- & Marktlogik": "Offer and market logic",
    "Gehaltstreiber, Benefits, Arbeitsmodell und Startflexibilität werden als Kandidat:innenargumente nutzbar.": "Salary drivers, benefits, work model, and start flexibility become usable candidate arguments.",
    "Angebot": "Offer",
    "Motivation": "Motivation",
    "Briefing, Stellenanzeige, Suchstrings, Interview-Sheets und Scorecards entstehen aus derselben bestätigten Datenbasis.": "Briefing, job ad, search strings, interview sheets, and scorecards are created from the same confirmed data base.",
    "Search": "Search",
    "Mehr geprüfte Tiefe am Anfang = weniger Schleifen, bessere Passung und konsistentere Entscheidungen im Recruiting.": "More reviewed depth upfront = fewer loops, better fit, and more consistent recruiting decisions.",
    "Von der Jobspec zum klaren Recruiting-Bild.": "From job spec to a clear recruiting picture.",
    "Die App liest eine Stellenanzeige ein, erkennt den fachlichen Kontext und fragt nur dort nach, wo Informationen für gute Recruiting-Entscheidungen fehlen.": "The app reads a job ad, detects the professional context, and only asks where information is missing for good recruiting decisions.",
    "Warum der Intake mehr sieht": "Why the intake sees more",
    "Was passiert danach?": "What happens next?",
    "Nach dem Start": "After starting",
    "Nächster Schritt: Quelle hochladen oder Rohtext einfügen.": "Next step: upload a source or paste raw text.",
    "Für wen das Briefing-Cockpit gedacht ist": "Who the briefing cockpit is for",
    "Die erste Analyse erstellt einen Briefing-Stand, keine finale Entscheidung.": "The first analysis creates a briefing status, not a final decision.",
    "Quelle einfügen, Briefing-Stand prüfen, dann gezielt weiterarbeiten.": "Add a source, review the briefing status, then continue with focus.",
    "Was der Start vor dem Upload verspricht": "What Start promises before upload",
    "Der Start ist kein Formular. Er bereitet einen gemeinsamen Briefing-Stand für Recruiting, Hiring Team und spätere Unterlagen vor.": "Start is not a form. It prepares a shared briefing status for recruiting, the hiring team, and later outputs.",
    "Versprechen": "Promise",
    "Aus einer Jobspec entsteht zuerst ein prüfbarer Briefing-Stand, nicht sofort ein langer Fragebogen.": "A jobspec first becomes a reviewable briefing status, not a long questionnaire right away.",
    "Zielgruppe": "Audience",
    "Gebaut für Recruiting, HR und Hiring Teams, die vor Search, Matching und Interview dieselbe Grundlage brauchen.": "Built for recruiting, HR, and hiring teams that need the same basis before search, matching, and interviews.",
    "Outputs": "Outputs",
    "Rollenprofil, Lückenpriorisierung, ESCO-Anker, Folgefragen und Recruiting-Unterlagen wachsen aus derselben Quelle.": "Role profile, gap prioritization, ESCO anchor, follow-up questions, and recruiting outputs grow from the same source.",
    "Vertrauen": "Trust",
    "Quelle, erkannte Angaben und spätere Bestätigung bleiben getrennt; sensible Angaben können reduziert werden.": "Source, detected facts, and later confirmation stay separate; sensitive information can be reduced.",
    "Schon freigeschaltet": "Already unlocked",
    "Nächste Aktion: erkannte Angaben prüfen, unsichere Punkte bereinigen und den Referenzberuf bestätigen.": "Next action: review detected facts, clean up uncertain points, and confirm the reference occupation.",
    "Rollenprofil und erste Aufgabenlogik": "Role profile and first task logic",
    "Priorisierte Lücken für die nächsten Briefing-Schritte": "Prioritized gaps for the next briefing steps",
    "ESCO-Kandidaten als Referenz für Skills und Aufgaben": "ESCO candidates as reference for skills and tasks",
    "Vorbereitete Folgefragen für Company, Rolle, Skills, Benefits und Interview": "Prepared follow-up questions for company, role, skills, benefits, and interview",
    "Vom Upload zum Recruiting-Briefing": "From upload to recruiting brief",
    'Nach dem Klick auf "Analyse starten"': 'After clicking "Start analysis"',
    "Was nach dem Briefing-Start entsteht": "What the briefing start creates",
    "Text verstehen": "Understand text",
    "Upload oder Freitext wird gelesen und in ein sauberes Rollenprofil überführt.": "Upload or free text is read and converted into a clean role profile.",
    "Beruf verankern": "Anchor occupation",
    "Die App sucht den passenden ESCO-Beruf als gemeinsame Referenz.": "The app searches for the matching ESCO occupation as a shared reference.",
    "Fragen priorisieren": "Prioritize questions",
    "Nur fehlende oder unsichere Punkte werden für den Wizard vorbereitet.": "Only missing or uncertain points are prepared for the wizard.",
    "Weiterverarbeiten": "Continue processing",
    "Aufgaben, Skills, Benefits, Interview und Summary-Unterlagen bauen darauf auf.": "Tasks, skills, benefits, interview, and summary outputs build on it.",
    "Ergebnis: weniger manuelle Sortierarbeit und eine bessere Grundlage für alle Recruiting-Aktivitäten.": "Result: less manual sorting and a better foundation for all recruiting activities.",
    "1. Rollenprofil sichern": "1. Secure role profile",
    "Titel, Aufgaben, Rahmenbedingungen und Annahmen werden zu einer prüfbaren Briefing-Basis.": "Title, tasks, conditions, and assumptions become a reviewable briefing basis.",
    "2. Lücken priorisieren": "2. Prioritize gaps",
    "Die App zeigt nur Angaben, die für Search, Matching, Interview oder Angebot noch fehlen.": "The app shows only the information still missing for search, matching, interview, or offer decisions.",
    "3. Recruiting-Unterlagen vorbereiten": "3. Prepare recruiting outputs",
    "Briefing, Stellenanzeige, Interview-Sheets und Suchstrings nutzen dieselbe Faktenbasis.": "Briefing, job ad, interview sheets, and search strings use the same fact base.",
    "Eisberg-Prinzip: Sichtbare Jobspec-Daten bleiben mit verdeckten Entscheidungskriterien verbunden, damit Recruiting, Search und Interview dieselbe Briefing-Basis nutzen.": "Iceberg principle: visible jobspec data stays connected to hidden decision criteria so recruiting, search, and interviews use the same briefing basis.",
    "Technische Vertrauensbasis:": "Technical trust basis:",
    "Mehr Kontext:": "More context:",
    "Was ist ESCO?": "What is ESCO?",
    "Was bedeutet RAG?": "What does RAG mean?",
    "Warum Recruiting-Briefing?": "Why the recruiting brief?",
    "Kurzer Kontext, warum die App nicht nur sichtbare Anforderungen, sondern auch Lücken und implizite Bedarfstreiber strukturiert.": "Brief context on why the app structures not only visible requirements, but also gaps and implicit demand drivers.",
    "Datenschutz und Kontrolle": "Privacy and control",
    "Vertrauen, Datenschutz und Kontrolle": "Trust, privacy, and control",
    "Weniger Rückfragen": "Fewer follow-up questions",
    "Der Wizard fragt gezielt nach, statt ein starres Formular abzuarbeiten.": "The wizard asks targeted questions instead of running through a rigid form.",
    "Klarer Rollenanker": "Clear role anchor",
    "Jobtitel werden mit ESCO abgeglichen, damit alle Folgeschritte denselben Berufskontext nutzen.": "Job titles are matched with ESCO so every later step uses the same occupation context.",
    "Direkt nutzbare Recruiting-Unterlagen": "Ready-to-use recruiting outputs",
    "Interview- & Unterlagenlogik": "Interview and output logic",
    "Fragen, Scorecards, Briefing und Recruiting-Unterlagen basieren auf derselben geprüften Faktenlage.": "Questions, scorecards, briefing, and recruiting outputs use the same reviewed fact base.",
    "Aus dem Intake entstehen strukturierte Informationen für Recruiting, Hiring-Team und Summary.": "The intake produces structured information for recruiting, the hiring team, and the summary.",
    "1. Beruf eindeutig verankern": "1. Anchor the occupation clearly",
    "Die Rolle wird auf einen klaren ESCO-Beruf gemappt, damit alle Folgeschritte denselben Kontext nutzen.": "The role is mapped to a clear ESCO occupation so all later steps use the same context.",
    "2. Anforderungen strukturieren": "2. Structure requirements",
    "Skills, Aufgaben und Muss-/Kann-Kriterien werden normalisiert und in einen nutzbaren Plan überführt.": "Skills, tasks, and must-have/nice-to-have criteria are normalized into a usable plan.",
    "3. Recruiting-Unterlagen erzeugen": "3. Generate recruiting outputs",
    "Die App erstellt belastbare Texte, Zusammenfassungen und Recruiting-Unterlagen für Recruiting und Hiring-Team.": "The app creates robust text, summaries, and recruiting outputs for recruiting and the hiring team.",
    "Vor der Verarbeitung können sensible personenbezogene Angaben optional reduziert werden. Ziel ist ein datensparsames, nachvollziehbares Recruiting-Briefing.": "Before processing, sensitive personal information can optionally be reduced. The goal is a data-minimizing, traceable recruiting brief.",
    "Vor der Verarbeitung können sensible personenbezogene Angaben optional reduziert werden. Quelle, erkannte Angaben und spätere Bestätigung bleiben getrennt, damit die Briefing-Basis datensparsam und nachvollziehbar entsteht.": "Before processing, sensitive personal information can optionally be reduced. Source, detected facts, and later confirmation stay separate so the briefing basis is data-minimizing and traceable.",
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
    "Recruiting-Briefing vorbereiten": "Prepare recruiting brief",
    "Quelle in Briefing verwandeln": "Turn source into brief",
    "Bereitet aus der aktuell aktiven Quelle einen prüfbaren Briefing-Stand vor.": "Prepares a reviewable briefing status from the currently active source.",
    "Jobspec oder Stellenanzeige hochladen (PDF, DOCX oder TXT)": "Upload jobspec or job ad (PDF, DOCX, or TXT)",
    "Erstellt aus der aktuell aktiven Quelle eine prüfbare Briefing-Basis.": "Creates a reviewable briefing basis from the currently active source.",
    "Stellenanzeige hochladen (PDF, DOCX oder TXT)": "Upload job ad (PDF, DOCX, or TXT)",
    "Stellenanzeige oder Jobspec einfügen": "Paste job ad or jobspec",
    "Jobspec oder Rohtext für das Briefing einfügen": "Paste jobspec or raw text for the brief",
    "Quelle für die Briefing-Analyse": "Source for briefing analysis",
    "Fügen Sie hier den vollständigen Ausschreibungstext ein …": "Paste the full job ad text here ...",
    "Bitte fügen Sie hier den Text manuell ein oder laden Sie eine lesbare PDF-, DOCX- oder TXT-Datei hoch.": "Please paste the text manually here or upload a readable PDF, DOCX, or TXT file.",
    "Bitte fügen Sie hier Text ein oder laden Sie links eine Datei hoch.": "Please paste text here or upload a file on the left.",
    "Analyseergebnis": "Analysis result",
    "Erkannte Briefing-Basis": "Detected briefing basis",
    "### Briefing-Fortschritt: erkannte Basis": "### Briefing progress: detected basis",
    "### Briefing-Fortschritt: Referenzberuf bestätigen": "### Briefing progress: confirm reference occupation",
    "Die wichtigsten Angaben sind nach Themen gruppiert. Die Prüfung fokussiert auf Sicherheit, offene Punkte und direkte Korrektur.": "The most important information is grouped by topic. The review focuses on confidence, open points, and direct correction.",
    "Berufsabgleich": "Occupation matching",
    "Berufsabgleich bestätigen": "Confirm occupation match",
    "Referenzberuf für das Briefing bestätigen": "Confirm reference occupation for the brief",
    "Quelle bearbeiten": "Edit source",
    "Erkannte Angaben prüfen": "Review detected information",
    "#### Briefing-Angaben freigeben": "#### Approve briefing information",
    "Briefing-Basis prüfen": "Review briefing basis",
    "Nächste Aktion im Briefing-Cockpit": "Next action in the briefing cockpit",
    "Das Briefing-Cockpit ist vorbereitet. Prüfen Sie erkannte Angaben, bereinigen Sie Unsicherheiten und bestätigen Sie den Referenzberuf.": "The briefing cockpit is prepared. Review detected facts, clean up uncertainty, and confirm the reference occupation.",
    "Laden Sie eine Quelle hoch oder fügen Sie Text ein. Die App bereitet daraus Rollenprofil, Lückenpriorisierung, ESCO-Anker und nächste Briefing-Fragen vor.": "Upload a source or paste text. The app prepares a role profile, gap prioritization, ESCO anchor, and next briefing questions from it.",
    "Quelle oder Briefing-Steuerung anpassen": "Adjust source or briefing controls",
    "Prüfen Sie unsichere und offene Angaben, bevor daraus das Briefing wächst. Die Spalten entsprechen den nächsten Briefing-Schritten; korrigieren Sie Werte direkt in der passenden Spalte oder löschen Sie eine Zeile, wenn die Angabe nicht übernommen werden soll. Änderungen werden automatisch gespeichert.": "Review uncertain and open information before it becomes part of the brief. The columns match the next briefing steps; correct values directly in the relevant column or delete a row if the information should not be used. Changes are saved automatically.",
    "Prüfen Sie unsichere und offene Angaben, bevor daraus der nächste Briefing-Stand wächst. Die Spalten entsprechen den nächsten Briefing-Schritten; korrigieren Sie Werte direkt in der passenden Spalte oder löschen Sie eine Zeile, wenn die Angabe nicht übernommen werden soll. Änderungen werden automatisch gespeichert.": "Review uncertain and open information before the next briefing status grows from it. The columns match the next briefing steps; correct values directly in the relevant column or delete a row if the information should not be used. Changes are saved automatically.",
    "Die Briefing-Basis ist vorbereitet. Prüfen Sie unsichere und offene Punkte direkt in der Tabelle und bestätigen Sie anschließend den passenden Referenzberuf.": "The briefing basis is prepared. Review uncertain and open points directly in the table, then confirm the matching reference occupation.",
    "Nächste Aktion: unsichere und offene Punkte direkt in der Tabelle freigeben und anschließend den passenden Referenzberuf bestätigen.": "Next action: approve uncertain and open points directly in the table, then confirm the matching reference occupation.",
    "Änderungen automatisch gespeichert.": "Changes saved automatically.",
    "Optional: Im nächsten Abschnitt können Sie den Referenzberuf bestätigen, damit Aufgaben, Skills und Recruiting-Unterlagen konsistent bleiben.": "Optional: In the next section, you can confirm the reference occupation so tasks, skills, and recruiting outputs stay consistent.",
    "Wir haben die ersten Informationen zur Rolle erkannt.": "We detected the first information for this role.",
    "Wir haben die ersten Informationen zur Rolle erkannt. Prüfen Sie jetzt die Briefing-Basis, schließen Sie Lücken und bestätigen Sie den Referenzberuf.": "We detected the first information for this role. Review the briefing basis, close gaps, and confirm the reference occupation.",
    "Prüfen Sie jetzt die Briefing-Basis, schließen Sie Lücken und bestätigen Sie den Referenzberuf. Danach wird daraus ein belastbares Recruiting-Briefing.": "Review the briefing basis, close gaps, and confirm the reference occupation. Then it becomes a reliable recruiting brief.",
    "Für Recruiting, HR und Hiring Teams: Quelle hochladen oder Text einfügen. Ergebnis ist eine geprüfte Briefing-Basis mit Rollenprofil, priorisierten Lücken und nächsten Fragen.": "For recruiting, HR, and hiring teams: upload a source or paste text. The result is a reviewed briefing basis with a role profile, prioritized gaps, and next questions.",
    "#### Briefing-Steuerung": "#### Briefing controls",
    "Erweiterte Briefing-Steuerung": "Advanced briefing controls",
    "Quellenumfang": "Source length",
    "Die Quelle ist sehr kurz. Ergänzen Sie mehr Text oder prüfen Sie die erkannten Angaben im Briefing-Fortschritt genau.": "The source is very short. Add more text or review the detected information carefully in briefing progress.",
    "Manueller Fallback: Text behalten, automatische Extraktion überspringen und den Briefing-Stand selbst starten.": "Manual fallback: keep the text, skip automatic extraction, and start the briefing status yourself.",
    "Nächste Aktion: rechts Text einfügen oder eine lesbare Datei hochladen.": "Next action: paste text on the right or upload a readable file.",
    "Briefing manuell starten": "Start brief manually",
    "Nächste Aktion: Text im Feld „Quelle für die Briefing-Analyse“ manuell einfügen oder eine andere Datei hochladen.": "Next action: paste text manually in the “Source for briefing analysis” field or upload another file.",
    "Briefing-Routing vorab: Standardwerte werden verwendet.": "Briefing routing upfront: default values are used.",
    "Briefing-Routing vorab": "Briefing routing upfront",
    "Mit Unternehmenskontext weiterarbeiten": "Continue with company context",
    "Bereite Rollenprofil vor…": "Preparing role profile...",
    "Bereite Briefing-Cockpit vor…": "Preparing briefing cockpit...",
    "Priorisiere offene Briefing-Fragen…": "Prioritizing open briefing questions...",
    "Schalte nächste Briefing-Fragen frei…": "Unlocking next briefing questions...",
    "Briefing-Basis vorbereitet: Informationen erkannt und nächste Fragen priorisiert.": "Briefing basis prepared: information detected and next questions prioritized.",
    "Briefing-Cockpit vorbereitet: Rollenprofil erkannt, Lücken priorisiert und nächste Fragen freigeschaltet.": "Briefing cockpit prepared: role profile detected, gaps prioritized, and next questions unlocked.",
    "Angaben übernehmen": "Apply information",
    "Angaben übernommen.": "Information applied.",
    "Bestätigt": "Confirmed",
    "Erkannt": "Detected",
    "Vorschlag": "Suggested",
    "Annahme": "Assumption",
    "Konflikt": "Conflict",
    "Fehlt": "Missing",
    "Bestätigt · nutzen": "Confirmed · use",
    "Erkannt · prüfen": "Detected · review",
    "Vorschlag · auswählen": "Suggested · select",
    "Annahme · prüfen": "Assumption · review",
    "Konflikt · klären": "Conflict · resolve",
    "Fehlt · ergänzen": "Missing · add",
    "Quelle · ansehen": "Source · view",
    "Beleg · ansehen": "Evidence · view",
    "Quelle & Beleg · ansehen": "Source & evidence · view",
    "Cache · genutzt": "Cache · reused",
    "Quelle & Beleg": "Source & evidence",
    "Quelle & Beleg anzeigen": "Show source & evidence",
    "Beleg verfügbar": "Evidence available",
    "Cache · genutzt: Ergebnis wiederverwendet.": "Cache · reused: result reused.",
    "Aus Cache: Ergebnis wurde wiederverwendet.": "From cache: result was reused.",
    "Ein paar Informationen vorab": "A few details first",
    "Unternehmenswebsite": "Company website",
    "Hinweise aus der Website-Analyse": "Insights from website analysis",
    "Strukturierter Kontext": "Structured context",
    "Unternehmensprofil": "Company profile",
    "Team & Reporting": "Team & reporting",
    "Arbeitsmodell": "Work model",
    "Non-negotiables & Compliance": "Non-negotiables & compliance",
    "Outcome & Scope": "Outcome & scope",
    "Kurzer Live-Stand für Recruiter: Rollenauftrag, Ergebnis, erster Erfolgshorizont und harte Suchgrenzen.": (
        "Short live status for recruiters: role mandate, outcome, first success horizon, "
        "and hard search boundaries."
    ),
    "Kläre, wofür die Rolle da ist, welche Ergebnisse entstehen müssen und welche Verantwortung Recruiter vor der Suche verstanden haben müssen.": (
        "Clarify what the role is for, which outcomes must be produced, and which "
        "responsibilities recruiters must understand before search starts."
    ),
    "Priorisierung": "Prioritization",
    "Erfolg und Entscheidungsspielraum": "Success and decision scope",
    "Reiseprofil": "Travel profile",
    "Auswirkung auf Prognose": "Impact on forecast",
    "Skills präzisieren und priorisieren": "Clarify and prioritize skills",
    "Weitere AI-Vorschläge": "More AI suggestions",
    "AI-Vorschläge": "AI suggestions",
    "AI-Vorschläge ergänzen": "Add AI suggestions",
    "AI-Vorschläge ergänzt": "AI suggestions added",
    "Keine zusätzlichen AI-Vorschläge gefunden.": "No additional AI suggestions found.",
    "Noch keine AI-Vorschläge vorhanden.": "No AI suggestions yet.",
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
    "Prüfung & Export": "Review & export",
    "Unterlagenübersicht": "Recruiting outputs overview",
    "Quellen & Details prüfen": "Review sources and details",
    "Recruiting Brief": "Recruiting brief",
    "Recruiting-Unterlagen": "Recruiting outputs",
    "Unterlage": "Output",
    "Pflicht vor Recruiting-Unterlage": "Required before recruiting output",
    "Suchstrings": "Search strings",
    "Keine Suchstrings vorhanden.": "No search strings available.",
    "HR-Sheet": "HR sheet",
    "Fachbereich-Sheet": "Hiring manager sheet",
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


_TRANSLATIONS_EN.update(
    {
        "Recruiting beginnt mit Bedarfsanalyse": "Recruiting starts with need analysis",
        "Recruiting einfach vorbereiten": "Prepare recruiting simply",
        "Erst den Bedarf schärfen. Dann suchen.": "Sharpen the need first. Then search.",
        "Erst klären. Dann suchen.": "Clarify first. Then search.",
        "Der erste Recruiting-Schritt entscheidet, ob Suche, Matching, Interview und Angebot auf derselben Wahrheit arbeiten — oder später teuer nachjustieren.": "The first recruiting step decides whether search, matching, interviews, and offers work from the same truth — or need expensive corrections later.",
        "Die App macht aus einer Stellenbeschreibung eine klare Grundlage: wen suchen wir, was muss die Person können, was fehlt noch?": "The app turns a job description into a clear basis: who are we looking for, what must they be able to do, what is still missing?",
        "Aus Jobspec, Upload oder Rohtext entsteht zuerst ein prüfbares Recruiting-Briefing: Fakten, Annahmen, Lücken, ESCO-Anker und Folgefragen bleiben getrennt sichtbar.": "A jobspec, upload, or raw text first becomes a reviewable recruiting brief: facts, assumptions, gaps, ESCO anchors, and follow-up questions stay visibly separated.",
        "So starten Suche, Interview und Stellenanzeige mit denselben geprüften Fakten.": "Search, interviews, and the job ad start from the same reviewed facts.",
        "Damit werden falsche Prioritäten, schwammige Must-haves und späte Kompromisse früh geklärt — bevor Kandidat:innen, Fachbereich und Recruiting Zeit verlieren.": "This clarifies wrong priorities, vague must-haves, and late trade-offs early — before candidates, the business team, and recruiting lose time.",
        "Sie behalten Kontrolle: erst prüfen, dann weiterverwenden.": "You stay in control: review first, reuse later.",
        "Starten Sie mit einer Quelle. Die App baut daraus kein Formular, sondern eine entscheidungsfähige Briefing-Basis.": "Start with a source. The app turns it into a decision-ready briefing basis, not a form.",
        "Typische Bedarfsanalyse vs. AI- & ESCO-Briefing": "Typical need analysis vs. AI and ESCO briefing",
        "Warum das wichtig ist": "Why this matters",
        "Das Eisberg-Modell trennt sichtbare Jobspec-Daten von verdeckten Entscheidungstreibern und macht beides für Recruiting-Unterlagen nutzbar.": "The iceberg model separates visible jobspec data from hidden decision drivers and makes both usable for recruiting outputs.",
        "Sichtbare Anforderungen und versteckte Erwartungen werden getrennt geprüft.": "Visible requirements and hidden expectations are reviewed separately.",
        "Fokus": "Focus",
        "Schritt 1": "Step 1",
        "Bedarf klären, bevor Recruiting startet": "Clarify the need before recruiting starts",
        "Klarheit": "Clarity",
        "Rolle": "Role",
        "Was soll die Person leisten?": "What should this person achieve?",
        "Abgleich": "Alignment",
        "Anforderungen": "Requirements",
        "Was ist wirklich wichtig?": "What really matters?",
        "Ergebnis": "Result",
        "Unterlagen": "Outputs",
        "Briefing, Anzeige, Interviewhilfe": "Brief, job ad, interview aid",
        "Risiko": "Risk",
        "Späte Korrektur": "Late correction",
        "falsche Suchrichtung, Rework, Frust": "wrong search direction, rework, frustration",
        "5 Unterlagen": "5 outputs",
        "Briefing, Anzeige, Interviews, Suchstrings": "brief, job ad, interviews, search strings",
        "Falsche Suchrichtung": "Wrong search direction",
        "Unklare Must-haves erzeugen Treffer, die fachlich wirken, aber am Auftrag vorbeigehen.": "Unclear must-haves produce matches that look relevant but miss the mandate.",
        "Demotivation im Prozess": "Demotivation in the process",
        "Kandidat:innen erleben wechselnde Kriterien, Fachbereiche verlieren Vertrauen in die Shortlist.": "Candidates experience shifting criteria, while business teams lose trust in the shortlist.",
        "Teure Schleifen": "Expensive loops",
        "Interviewfragen, Stellenanzeige, Gehaltsrahmen und Suchstrings müssen nachträglich korrigiert werden.": "Interview questions, job ad, salary frame, and search strings need later correction.",
        "Interaktive App-Schicht": "Interactive app layer",
        "Container, Columns, Tabs, Popovers, Session State und AppTest bilden den Wizard-Rahmen.": "Containers, columns, tabs, popovers, Session State, and AppTest form the wizard shell.",
        "OpenAI + strukturierte Outputs": "OpenAI + structured outputs",
        "Extraktion und Textgenerierung": "Extraction and text generation",
        "Zentrale LLM-Schicht mit Modell-Routing, Schema-Ausgabe, Caching, Fallbacks und sicherem Error-Mapping.": "Central LLM layer with model routing, schema output, caching, fallbacks, and safe error mapping.",
        "Arbeitsmarkt-Semantik": "Labour-market semantics",
        "EU-Berufs- und Skill-Taxonomie, Live-/Offline-Fallbacks, optionale Retrieval-Schicht und Explainability-Metadaten.": "EU occupation and skills taxonomy, live/offline fallbacks, optional retrieval layer, and explainability metadata.",
        "Pydantic + State Contracts": "Pydantic + state contracts",
        "Verlässliche Datenform": "Reliable data shape",
        "Schemas, kanonische Session-State-Keys und Fact-Registry verhindern driftende Felder und implizite Annahmen.": "Schemas, canonical Session State keys, and the fact registry prevent drifting fields and implicit assumptions.",
        "Daten sichtbar machen": "Making data visible",
        "Interaktive Visualisierungen, KPI-Übersichten und strukturierte Tabellen machen Fortschritt und Abdeckung prüfbar.": "Interactive visualizations, KPI overviews, and structured tables make progress and coverage reviewable.",
        "DOCX / PDF / Excel Export": "DOCX / PDF / Excel export",
        "Recruiting-Unterlagen rausgeben": "Export recruiting outputs",
        "python-docx, ReportLab, pdfplumber und openpyxl decken Upload, Vorschau und Download-Unterlagen ab.": "python-docx, ReportLab, pdfplumber, and openpyxl cover upload, preview, and download outputs.",
        "ESCO ist die mehrsprachige EU-Klassifikation für Berufe, Skills und Kompetenzen. In der App dient sie als Referenzanker, damit Rollenprofile, Skills und Suchlogik vergleichbarer werden.": "ESCO is the multilingual EU classification for occupations, skills, and competences. In the app, it acts as a reference anchor so role profiles, skills, and search logic become more comparable.",
        "Wichtig: ESCO liefert Orientierung, aber keine automatische Knockout-Entscheidung.": "Important: ESCO provides orientation, not an automatic knockout decision.",
        "RAG verbindet Retrieval mit Generierung: Die App kann relevante ESCO-Kontexte suchen und erst danach Vorschläge formulieren.": "RAG combines retrieval with generation: the app can search relevant ESCO context before formulating suggestions.",
        "Wichtig: Treffer bleiben als Quelle/Fallback nachvollziehbar, statt als harte Wahrheit zu erscheinen.": "Important: hits remain traceable as source/fallback instead of appearing as hard truth.",
        "Welche OpenAI-Tools nutzt die App?": "Which OpenAI tools does the app use?",
        "Die App nutzt OpenAI zentral für strukturierte Jobspec-Extraktion, Folgefragen, Briefing- und Unterlagenentwürfe — mit Schema-Prüfung, Modellfähigkeits-Checks, Retry/Fallback und Nutzungsmetadaten.": "The app uses OpenAI centrally for structured jobspec extraction, follow-up questions, and brief/output drafts — with schema checks, model-capability checks, retry/fallback, and usage metadata.",
        "Wichtig: Erkannte Werte bleiben prüfbar; bestätigte Fakten steuern die finalen Outputs.": "Important: detected values stay reviewable; confirmed facts control the final outputs.",
        "Technische Vertrauensbasis": "Technical trust basis",
        "Recruiting-Cycle-Visualisierung ist in dieser Umgebung nicht verfügbar.": "The recruiting-cycle visualization is not available in this environment.",
        "Der Recruiting-Cycle kippt im ersten Schritt": "The recruiting cycle tilts in the first step",
        "Preparation ist kein Vorwort. Es ist der Kontrollpunkt, an dem Bedarf, Kompromisse und Erfolgskriterien festgelegt werden.": "Preparation is not a preface. It is the control point where need, trade-offs, and success criteria are defined.",
        "Wenn der Bedarf unscharf bleibt, optimiert jeder spätere Schritt auf eine andere Wahrheit. Die App zieht diese Wahrheit nach vorn.": "If the need stays vague, every later step optimizes for a different truth. The app pulls that truth forward.",
        "Fokus: Bedarfsanalyse": "Focus: need analysis",
        "Das Eisberg-Modell zeigt, welche sichtbaren Jobspec-Daten und verdeckten Entscheidungskriterien hier zusammengeführt werden.": "The iceberg model shows which visible jobspec data and hidden decision criteria are brought together here.",
        "Eisberg-Prinzip: Sichtbare Jobspec-Daten bleiben mit verdeckten Entscheidungskriterien verbunden, damit Recruiting, Suche und Interview dieselbe Briefing-Basis nutzen.": "Iceberg principle: visible jobspec data stays connected to hidden decision criteria so recruiting, search, and interviews use the same briefing basis.",
        "Technologie, die das Briefing belastbar macht": "Technology that makes the brief reliable",
        "Mehr zur Methode": "More on the method",
        "Technische Insights": "Technical insights",
        "Unter der Oberfläche arbeitet die App wie ein kuratierter Recruiting-Stack: schlank im UI, streng bei Daten, nachvollziehbar bei AI.": "Below the surface, the app works like a curated recruiting stack: lean in the UI, strict with data, traceable with AI.",
        "entscheidet die Qualität der nächsten 6 Schritte": "decides the quality of the next 6 steps",
        "Phase": "Phase",
        "Wirkung": "Impact",
        "Bedarfsanalyse": "Need analysis",
        "Talent Sourcing": "Talent sourcing",
        "Applicant Screening": "Applicant screening",
        "Interview & Selection": "Interview & selection",
        "Job Offer & Negotiation": "Job offer & negotiation",
        "Smooth Onboarding": "Smooth onboarding",
        "Feedback & Evolution": "Feedback & evolution",
        "Rolle, Muss-Kriterien, Kompromisse und Erfolg werden entschieden.": "Role, must-have criteria, trade-offs, and success are decided.",
        "Suchstrings und Ansprache funktionieren nur mit klarem Zielprofil.": "Search strings and outreach only work with a clear target profile.",
        "CVs werden gegen bestätigte Anforderungen statt gegen Bauchgefühl geprüft.": "CVs are reviewed against confirmed requirements instead of gut feeling.",
        "Interviewfragen prüfen beobachtbares Verhalten und echte Erfolgskriterien.": "Interview questions check observable behavior and real success criteria.",
        "Gehalt, Benefits und Motivation sind mit dem Bedarf verknüpft.": "Salary, benefits, and motivation are linked to the need.",
        "Die ersten 30/60/90 Tage folgen aus dem Rollenauftrag.": "The first 30/60/90 days follow from the role mandate.",
        "Erkenntnisse verbessern das nächste Briefing statt nur den nächsten Prozess.": "Insights improve the next brief, not just the next process.",
        "Vor Recruiting": "Before recruiting",
        "Markt aktivieren": "Activate the market",
        "Auswahl schärfen": "Sharpen selection",
        "Entscheidung vorbereiten": "Prepare decision",
        "Zusage sichern": "Secure acceptance",
        "Wirksamkeit erzeugen": "Create effectiveness",
        "Lernen": "Learning",
        "Suche": "Search",
        "Vorbereitung": "Preparation",
        "Matching": "Matching",
        "Die Stellenanzeige zeigt, was bekannt ist. Die App macht sichtbar, was für Suche, Matching, Interview und Angebot wirklich entschieden werden muss.": "The job ad shows what is known. The app reveals what really needs to be decided for search, matching, interviews, and the offer.",
        "unterhalb: entscheidend für Suche, Matching, Interview und Zusage": "below: essential for search, matching, interview, and offer acceptance",
        "Extraktion, Fundstellen, Confidence, Gaps und Annahmen werden prüfbar, bevor daraus Entscheidungen entstehen.": "Extraction, evidence locations, confidence, gaps, and assumptions become reviewable before decisions are made from them.",
        "Prüfung": "Review",
        "Gebaut für Recruiting, HR und Hiring Teams, die vor Suche, Matching und Interview dieselbe Grundlage brauchen.": "Built for recruiting, HR, and hiring teams that need the same basis before search, matching, and interviews.",
        "Die App zeigt nur Angaben, die für Suche, Matching, Interview oder Angebot noch fehlen.": "The app shows only the information still missing for search, matching, interview, or offer decisions.",
    }
)

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
    "Quelle & Beleg": "Source & evidence",
    "Beleg verfügbar": "Evidence available",
    "Bestätigt": "Confirmed",
    "Erkannt": "Detected",
    "Vorschlag": "Suggested",
    "Annahme": "Assumption",
    "Konflikt": "Conflict",
    "Fehlt": "Missing",
    "Eingabe": "Input",
    "nutzen": "use",
    "auswählen": "select",
    "klären": "resolve",
    "genutzt": "reused",
    "ansehen": "view",
    "ergänzen": "add",
    "prüfen": "review",
    "Aus Cache": "From cache",
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
    "Wir haben die ersten Informationen zu ": "We detected the first information for ",
    " erkannt.": ".",
    "Prüfen Sie jetzt die Briefing-Basis, schließen Sie Lücken und bestätigen Sie den Referenzberuf.": "Review the briefing basis, close gaps, and confirm the reference occupation.",
}

_PATCHED = False


def _supported_language(raw_language: object) -> str | None:
    language = str(raw_language or "").strip().lower()
    return language if language in SUPPORTED_UI_LANGUAGES else None


def normalize_language(raw_language: object) -> str:
    return _supported_language(raw_language) or DEFAULT_LANGUAGE


def _first_query_param_value(value: object) -> object:
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _query_param_language() -> str | None:
    try:
        query_value = _first_query_param_value(
            st.query_params.get(UI_LANGUAGE_QUERY_PARAM)
        )
    except Exception:
        return None
    return _supported_language(query_value)


def _write_language_query_param(language: str) -> None:
    try:
        st.query_params[UI_LANGUAGE_QUERY_PARAM] = language
    except Exception:
        return


def _real_streamlit_without_script_context() -> bool:
    if getattr(st, "__name__", "") != "streamlit":
        return False
    try:
        from streamlit.runtime.scriptrunner_utils.script_run_context import (
            get_script_run_ctx,
        )

        return get_script_run_ctx() is None
    except Exception:
        return False


def _deep_get(mapping: Mapping[str, Any], dotted_key: str) -> Any | None:
    current: Any = mapping
    for part in dotted_key.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


@lru_cache(maxsize=8)
def _load_locale(language: str) -> dict[str, Any]:
    locale_path = LOCALES_DIR / f"{normalize_language(language)}.json"
    if not locale_path.is_file():
        return {}
    with locale_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Locale file must contain a JSON object: {locale_path}")
    return payload


def active_language() -> str:
    if _real_streamlit_without_script_context():
        return DEFAULT_LANGUAGE

    query_language = _query_param_language()
    if query_language:
        return query_language

    language = normalize_language(
        st.session_state.get(SSKey.LANGUAGE.value, DEFAULT_LANGUAGE)
    )
    preferences = st.session_state.get(SSKey.UI_PREFERENCES.value, {})
    if isinstance(preferences, dict):
        language = normalize_language(
            preferences.get(UI_PREFERENCE_UI_LANGUAGE, language)
        )
    return language


def tr(key: str, /, **params: Any) -> str:
    language = active_language()
    value = _deep_get(_load_locale(language), key)
    if value is None and language != DEFAULT_LANGUAGE:
        value = _deep_get(_load_locale(DEFAULT_LANGUAGE), key)
    if value is None:
        value = key
    text = str(value)
    return text.format(**params) if params else text


class _SafeFormatDict(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return ""


def tr_safe(key: str, /, *, language: str | None = None, **params: Any) -> str:
    selected_language = normalize_language(language or active_language())
    value = _deep_get(_load_locale(selected_language), key)
    if value is None and selected_language != DEFAULT_LANGUAGE:
        value = _deep_get(_load_locale(DEFAULT_LANGUAGE), key)
    if value is None:
        value = key
    text = str(value)
    return text.format_map(_SafeFormatDict(params)).strip()


def t(text: object, *, language: str | None = None) -> object:
    if not isinstance(text, str):
        return text
    selected_language = normalize_language(language or active_language())
    if selected_language != "en":
        return text
    key_value = _deep_get(_load_locale(selected_language), text)
    if isinstance(key_value, str):
        return key_value
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
    return normalized


def sync_language_state_from_request(*, session_state: Any | None = None) -> str:
    normalized = normalize_language(_query_param_language() or active_language())
    return sync_language_state(normalized, session_state=session_state)


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
    _write_language_query_param(synced_language)
    return synced_language


def sync_language_from_known_widgets(*, session_state: Any | None = None) -> str | None:
    state = session_state if session_state is not None else st.session_state
    last_widget_key = state.get(LAST_LANGUAGE_WIDGET_KEY)
    if isinstance(last_widget_key, str) and last_widget_key in LANGUAGE_WIDGET_KEYS:
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


def render_language_persistence_bridge(*, language: str | None = None) -> None:
    current_language = normalize_language(language or active_language())
    html_payload = f"""
    <!doctype html>
    <html>
      <body>
        <script>
          (function() {{
            const current = {json.dumps(current_language)};
            const supported = new Set({json.dumps(list(SUPPORTED_UI_LANGUAGES))});
            const paramName = {json.dumps(UI_LANGUAGE_QUERY_PARAM)};
            const storageKey = {json.dumps(UI_LANGUAGE_STORAGE_KEY)};
            const cookieKey = {json.dumps(UI_LANGUAGE_COOKIE_KEY)};

            function readCookie(name) {{
              const parts = document.cookie.split(";").map((value) => value.trim());
              for (const entry of parts) {{
                if (entry.startsWith(name + "=")) {{
                  return decodeURIComponent(entry.slice(name.length + 1));
                }}
              }}
              return null;
            }}

            function writeCookie(name, value) {{
              document.cookie = name + "=" + encodeURIComponent(value)
                + "; path=/; max-age=31536000; SameSite=Lax";
            }}

            function readStored() {{
              try {{
                const localValue = window.localStorage
                  ? window.localStorage.getItem(storageKey)
                  : null;
                if (supported.has(localValue)) return localValue;
              }} catch (error) {{}}
              const cookieValue = readCookie(cookieKey);
              return supported.has(cookieValue) ? cookieValue : null;
            }}

            function persist(value) {{
              try {{
                if (window.localStorage) {{
                  window.localStorage.setItem(storageKey, value);
                }}
              }} catch (error) {{}}
              writeCookie(cookieKey, value);
            }}

            const stored = readStored();
            persist(current);

            const url = new URL(window.parent.location.href);
            const urlValue = url.searchParams.get(paramName);
            if (!supported.has(urlValue) && stored && stored !== current) {{
              url.searchParams.set(paramName, stored);
              window.parent.location.replace(url.toString());
              return;
            }}

            if (urlValue !== current) {{
              url.searchParams.set(paramName, current);
              window.parent.history.replaceState({{}}, "", url.toString());
            }}
          }})();
        </script>
      </body>
    </html>
    """
    encoded_html = base64.b64encode(html_payload.encode("utf-8")).decode("ascii")
    st.iframe(f"data:text/html;base64,{encoded_html}", height=1)


def render_language_toggle(
    *,
    location: str = "sidebar",
    key: str = LANGUAGE_WIDGET_KEY_SIDEBAR,
    horizontal: bool = True,
) -> str:
    sync_language_state_from_request()
    current = active_language()
    options = list(SUPPORTED_UI_LANGUAGES)
    ensure_option_widget_state(
        key,
        options=options,
        default=current,
        session_state=st.session_state,
    )
    container = st.sidebar if location == "sidebar" else st
    selected = container.radio(
        tr("common.language"),
        options=options,
        key=key,
        horizontal=horizontal,
        format_func=lambda value: (
            f"DE · {tr('common.german')}"
            if value == "de"
            else f"EN · {tr('common.english')}"
        ),
        on_change=sync_streamlit_language_widget,
        args=(key,),
    )
    normalized = sync_language_state(selected)
    _write_language_query_param(normalized)
    render_language_persistence_bridge(language=normalized)
    return normalized


def bootstrap_public_page(
    *, page_title: str, page_icon: str, layout: str = "wide"
) -> str:
    st.set_page_config(
        page_title=str(t(page_title)),
        page_icon=page_icon,
        layout=layout,
    )
    sync_language_state_from_request()
    patch_streamlit_text()
    render_language_persistence_bridge()
    return active_language()


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
