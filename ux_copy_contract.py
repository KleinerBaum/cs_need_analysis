from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from constants import (
    DEFAULT_LANGUAGE,
    SUMMARY_ACTIVE_ARTIFACT_IDS,
    STEP_KEY_BENEFITS,
    STEP_KEY_COMPANY,
    STEP_KEY_INTERVIEW,
    STEP_KEY_LANDING,
    STEP_KEY_ROLE_TASKS,
    STEP_KEY_SKILLS,
    STEP_KEY_SUMMARY,
)

SUPPORTED_COPY_LANGUAGES = {"de", "en"}


@dataclass(frozen=True)
class VacancyCopyContext:
    role_title: str = ""
    company_name: str = ""
    location: str = ""
    department: str = ""
    work_model: str = ""
    seniority_level: str = ""
    readiness_score: int | None = None
    open_questions_count: int | None = None
    critical_gaps_count: int | None = None


@dataclass(frozen=True)
class StepCopy:
    headline: str
    subheadline: str
    value_line: str = ""
    primary_cta: str = ""
    secondary_cta: str = ""


class _SafeTemplateDict(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return ""


_COPY: dict[str, dict[str, dict[str, str]]] = {
    "de": {
        STEP_KEY_LANDING: {
            "headline": "Vom Rollenbedarf zum Recruiting-Briefing.",
            "subheadline": (
                "Für Recruiting, HR und Hiring Teams, die vor Search, Matching, "
                "Interview und Angebot eine gemeinsame Entscheidungsbasis brauchen. "
                "Laden Sie eine Jobspec hoch oder fügen Sie Rohtext ein; die App "
                "zeigt zuerst, was belastbar ist und welche Lücken den Prozess bremsen."
            ),
            "value_line": (
                "Ergebnis: ein Briefing-Cockpit mit Rollenprofil, Prioritäten, "
                "offenen Fragen, ESCO-Anker und vorbereiteten Recruiting-Outputs."
            ),
            "headline_after_analysis": (
                "Briefing-Cockpit für {role_title} ist vorbereitet."
            ),
            "subheadline_after_analysis": (
                "Nächste Aktion: erkannte Angaben prüfen, unsichere Punkte bereinigen "
                "und den Referenzberuf bestätigen."
            ),
            "value_line_after_analysis": (
                "Schon freigeschaltet: Rollenprofil, Lückenpriorisierung, "
                "ESCO-Kandidaten und nächste Briefing-Fragen."
            ),
            "primary_cta": "Quelle in Briefing verwandeln",
            "secondary_cta": "Beispiel ansehen",
        },
        STEP_KEY_COMPANY: {
            "headline": "{company_name} als Arbeitgeber für {role_title} einordnen",
            "subheadline": (
                "Klären Sie Unternehmenskontext, Teamstruktur und Positionierung, "
                "damit Recruiting und Kandidat:innen verstehen, warum diese Rolle relevant ist."
            ),
            "value_line": "Hilft zu erklären, warum diese Rolle existiert.",
            "primary_cta": "Unternehmenskontext speichern",
            "secondary_cta": "Website-Funde prüfen",
        },
        STEP_KEY_ROLE_TASKS: {
            "headline": "Klären, wofür {role_title} wirklich verantwortlich ist",
            "subheadline": (
                "Priorisieren Sie Aufgaben, Ergebnisse und Erfolgskriterien, damit Recruiting "
                "nicht nur Tätigkeiten sucht, sondern die richtige Wirkung."
            ),
            "value_line": "Verhindert, dass Recruiting nur nach Titeln sucht.",
            "primary_cta": "Aufgaben speichern",
            "secondary_cta": "Erfolgskriterien prüfen",
        },
        STEP_KEY_SKILLS: {
            "headline": "Must-haves von Nice-to-haves trennen",
            "subheadline": (
                "Erstellen Sie eine prüfbare Skill-Liste für Matching, Interviewfragen, "
                "Gehaltsprognose und die finale Stellenanzeige."
            ),
            "value_line": "Trennt echte Anforderungen von Wunschlisten.",
            "primary_cta": "Skills speichern",
            "secondary_cta": "Offene Begriffe prüfen",
        },
        STEP_KEY_BENEFITS: {
            "headline": "Das Angebot für {role_title} klar und überzeugend formulieren",
            "subheadline": (
                "Erfassen Sie Gehalt, Arbeitsmodell, Benefits und Startbedingungen, "
                "damit Kandidat:innen früh verstehen, warum sich die Rolle lohnt."
            ),
            "value_line": "Macht das Angebot vergleichbar und verhandelbar.",
            "primary_cta": "Angebot speichern",
            "secondary_cta": "Rahmenbedingungen prüfen",
        },
        STEP_KEY_INTERVIEW: {
            "headline": "Einen fairen Interviewprozess für {role_title} planen",
            "subheadline": (
                "Definieren Sie Interviewstufen, Verantwortlichkeiten, Scorecards und "
                "Nachweise, damit jede Entscheidung nachvollziehbar bleibt."
            ),
            "value_line": "Sorgt für faire, konsistente Bewertung.",
            "primary_cta": "Interviewprozess speichern",
            "secondary_cta": "Bewertungskriterien prüfen",
        },
        STEP_KEY_SUMMARY: {
            "headline_default": "Das Recruiting-Briefing für {role_title} ist zu {readiness_score}% bereit",
            "headline_gap": "Noch {critical_gaps_count} Release-Blocker offen",
            "headline_ready": "Bereit für Recruiting, Interviews und Active Sourcing",
            "subheadline_default": (
                "Prüfen Sie offene Lücken, übernehmen Sie finale Anpassungen und "
                "erstellen Sie die passenden Recruiting-Unterlagen für Recruiting, "
                "HR und Active Sourcing."
            ),
            "subheadline_gap": (
                "Klären oder aktualisieren Sie die blockierenden Punkte, bevor Sie "
                "Stellenanzeige, Interviewleitfaden oder Suchstrings final exportieren."
            ),
            "subheadline_ready": (
                "Alle wichtigen Fakten sind geprüft. Erstellen Sie jetzt Stellenanzeige, "
                "HR-Sheet und Suchstrings."
            ),
            "value_line": "Erstellt direkt nutzbare Unterlagen für HR, Recruiting und Sourcing.",
            "primary_cta": "Recruiting-Unterlagen erstellen",
            "secondary_cta": "Lücken prüfen",
        },
    },
    "en": {
        STEP_KEY_LANDING: {
            "headline": "Turn role need into a recruiting brief.",
            "subheadline": (
                "For recruiting, HR, and hiring teams that need a shared decision basis "
                "before search, matching, interviews, and offers. Upload a jobspec or "
                "paste raw text; the app first shows what is reliable and which gaps "
                "slow the process down."
            ),
            "value_line": (
                "Result: a recruiting brief cockpit with a role profile, priorities, open "
                "questions, ESCO anchor, and prepared recruiting outputs."
            ),
            "headline_after_analysis": (
                "Briefing cockpit for {role_title} is prepared."
            ),
            "subheadline_after_analysis": (
                "Next action: review detected facts, clean up uncertain points, and "
                "confirm the reference occupation."
            ),
            "value_line_after_analysis": (
                "Already unlocked: role profile, gap prioritization, ESCO candidates, "
                "and next briefing questions."
            ),
            "primary_cta": "Turn source into brief",
            "secondary_cta": "See example",
        },
        STEP_KEY_COMPANY: {
            "headline": "Position {company_name} as the employer for {role_title}",
            "subheadline": (
                "Clarify company context, team structure, and positioning so recruiting "
                "and candidates understand why this role matters."
            ),
            "value_line": "Helps explain why this role exists.",
            "primary_cta": "Save company context",
            "secondary_cta": "Review website findings",
        },
        STEP_KEY_ROLE_TASKS: {
            "headline": "Clarify what {role_title} is truly responsible for",
            "subheadline": (
                "Prioritize tasks, outcomes, and success criteria so recruiting looks for "
                "the right impact, not just a list of activities."
            ),
            "value_line": "Prevents recruiting from searching by title alone.",
            "primary_cta": "Save role scope",
            "secondary_cta": "Review success criteria",
        },
        STEP_KEY_SKILLS: {
            "headline": "Separate must-haves from nice-to-haves",
            "subheadline": (
                "Build a testable skill list for matching, interview questions, salary "
                "forecasting, and the final job ad."
            ),
            "value_line": "Separates real requirements from wish lists.",
            "primary_cta": "Save skills",
            "secondary_cta": "Review open terms",
        },
        STEP_KEY_BENEFITS: {
            "headline": "Describe the offer for {role_title} clearly and convincingly",
            "subheadline": (
                "Capture salary, work model, benefits, and start conditions so candidates "
                "understand early why the role is worth considering."
            ),
            "value_line": "Makes the offer comparable and negotiable.",
            "primary_cta": "Save offer details",
            "secondary_cta": "Review conditions",
        },
        STEP_KEY_INTERVIEW: {
            "headline": "Plan a fair interview process for {role_title}",
            "subheadline": (
                "Define interview stages, responsibilities, scorecards, and evidence so "
                "every decision stays transparent."
            ),
            "value_line": "Supports fair and consistent evaluation.",
            "primary_cta": "Save interview plan",
            "secondary_cta": "Review scorecards",
        },
        STEP_KEY_SUMMARY: {
            "headline_default": "The recruiting brief for {role_title} is {readiness_score}% ready",
            "headline_gap": "{critical_gaps_count} release blockers still open",
            "headline_ready": "Ready for recruiting, interviews, and active sourcing",
            "subheadline_default": (
                "Review remaining gaps, apply final adjustments, and generate the right "
                "recruiting outputs for recruiting, HR, and active sourcing."
            ),
            "subheadline_gap": (
                "Clarify or refresh the blocking items before releasing a job ad, "
                "interview guide, or search strings as final exports."
            ),
            "subheadline_ready": (
                "All important facts are checked. Generate the job ad, HR sheet, and search strings now."
            ),
            "value_line": "Creates directly usable material for HR, recruiting, and sourcing.",
            "primary_cta": "Generate recruiting outputs",
            "secondary_cta": "Review gaps",
        },
    },
}


ARTIFACT_LABELS: dict[str, dict[str, str]] = {
    "de": {
        "brief": "Recruiting Brief",
        "job_ad": "Stellenanzeige",
        "interview_hr": "HR-Sheet",
        "interview_fach": "Fachbereich-Sheet",
        "boolean_search": "Suchstrings",
    },
    "en": {
        "brief": "Recruiting brief",
        "job_ad": "Job ad",
        "interview_hr": "HR sheet",
        "interview_fach": "Hiring manager sheet",
        "boolean_search": "Boolean search",
    },
}

SUMMARY_UI_COPY: dict[str, dict[str, Any]] = {
    "de": {
        "artifact_status": {
            "current": "Aktuell",
            "stale": "Veraltet",
            "missing": "Fehlt",
            "invalid": "Ungültig",
            "blocked": "Wartet",
            "open": "Offen",
            "ready": "Bereit",
            "met": "Erfüllt",
        },
        "brief_status": {
            "blocked_message": (
                "Jobspec oder Wizard-Plan fehlt. Der Recruiting Brief kann noch "
                "nicht erstellt werden."
            ),
            "blocked_cta": "Recruiting Brief vorbereiten",
            "missing_message": (
                "Recruiting Brief fehlt. Erstellen Sie ihn, bevor Sie Folgeunterlagen "
                "oder Exporte freigeben."
            ),
            "missing_cta": "Recruiting Brief erstellen",
            "invalid_message": (
                "Recruiting Brief ist ungültig. Erstellen Sie ihn neu, bevor Sie "
                "exportieren."
            ),
            "invalid_cta": "Recruiting Brief neu erstellen",
            "dirty_message": (
                "Recruiting Brief ist veraltet. Aktualisieren Sie ihn vor Export "
                "oder Folgeunterlagen."
            ),
            "stale_model_message": (
                "Recruiting Brief wurde mit einem anderen Modell erstellt. "
                "Aktualisieren Sie ihn vor Export oder Folgeunterlagen."
            ),
            "missing_snapshot_message": (
                "Recruiting Brief hat keinen aktuellen Eingabe-Snapshot. "
                "Aktualisieren Sie ihn vor Export oder Folgeunterlagen."
            ),
            "stale_input_message": (
                "Recruiting Brief passt nicht mehr zu den aktuellen Eingaben. "
                "Aktualisieren Sie ihn vor Export oder Folgeunterlagen."
            ),
            "stale_cta": "Recruiting Brief aktualisieren",
            "current_message": "Recruiting Brief ist aktuell und als Grundlage verwendbar.",
            "current_cta": "Brief aktualisieren",
            "short_stale": "Recruiting Brief ist veraltet.",
        },
        "release_state": {
            "current": "Aktuell und exportierbar",
            "ready": "Bereit zur Erstellung",
            "stale": "Veraltet - vor Export aktualisieren",
            "missing": "Fehlt - zuerst erstellen",
            "invalid": "Ungültig - neu erstellen",
            "blocked": "Blockiert - Grundlagen klären",
            "open": "Offen",
            "fallback": "Status offen",
        },
        "release_gate": {
            "next_step": "Nächster Schritt: {next_step}",
            "blocker": "Blocker: {reason}",
            "todo": "To do: {next_step}",
            "more_blockers": "Weitere {count} Blocker im Fakten-Workspace prüfen.",
            "release_gate": "Release Gate: {status}",
            "status": "Status: {status}",
            "prerequisites": "Voraussetzungen: {text}",
            "prerequisite": "Voraussetzung: {marker} {text}",
            "state_label_warning_one": "1 Warnung",
            "state_label_warning_many": "{count} Warnungen",
            "state_label_blockers": "{count} Blocker",
            "next_exportable": "Kann exportiert oder bei Änderungen aktualisiert werden.",
            "next_create": "{artifact_label} erstellen.",
            "missing_prerequisite_reason": "Jobspec oder Wizard-Plan fehlt.",
            "missing_prerequisite_next": (
                "Start-Schritt abschließen und Summary erneut öffnen."
            ),
            "brief_missing_or_not_ready": "Recruiting Brief fehlt oder ist noch nicht bereit.",
            "brief_missing_or_not_ready_cta": "Recruiting Brief erstellen",
            "sourcing_ready_reason": (
                "Recruiting Brief ist verfügbar, nächster Schritt ist eine Sourcing-Unterlage."
            ),
            "fallback_next_reason": (
                "Nächster verfügbarer Schritt basierend auf dem aktuellen Status."
            ),
            "safe_brief_reason": "Brief als sicherer Startpunkt.",
            "action_prefix": "Aktion: {label}",
            "no_next_step": "Aktuell ist kein nächster Schritt verfügbar.",
            "critical_gap_success": (
                "Keine kritischen Fakten-Blocker erkannt. Prüfen Sie jetzt die "
                "Unterlagenkarten."
            ),
            "critical_gap_title": "Fakten-Blocker vor Export (Top 5)",
        },
        "final_export": {
            "title": "Finalexport pausiert",
            "blockers": "Blockierende Punkte",
            "next_action": "Nächste Aktion",
            "preview": "Vorschau bleibt verfügbar.",
            "draft": "Entwurf speichern",
            "draft_help": (
                "Speichert den aktuellen Arbeitsstand als Entwurf-JSON. "
                "Das ist kein finaler Export."
            ),
            "fallback_blocker": "Finaler Download ist erst nach Freigabe verfügbar.",
            "expert_details": "Sichere Expert-Details",
            "override_available": (
                "Expert Override verfügbar: nur nicht-kritische Warnungen blockieren "
                "den Finalexport."
            ),
            "override_hidden": (
                "Kein Override verfügbar: kritische Release-Blocker müssen zuerst "
                "behoben werden."
            ),
            "summary_ready": "Finalexport bereit.",
            "summary_stale": "Finalexport pausiert: Ergebnis zuerst neu erstellen.",
            "summary_warning": (
                "Finalexport pausiert: Warnungen prüfen; Expert Override möglich."
            ),
            "summary_blocked": "Finalexport pausiert: Blocker zuerst beheben.",
            "summary_draft": "Entwurf kann erstellt werden; Finalexport folgt nach Freigabe.",
            "summary_preview": "Vorschau bleibt verfügbar; Entwurf braucht mehr Basiskontext.",
            "summary_open": "Status offen.",
            "expert_override_active": (
                "Expert Override aktiv: Finalexport trotz nicht-kritischer Warnungen verfügbar."
            ),
            "heading": "Finalexport",
            "caption": (
                "Lade die freigegebenen Finalexporte direkt herunter. JSON-Vorschau "
                "und Debug-Details sind standardmäßig eingeklappt."
            ),
            "download_json": "JSON herunterladen",
            "download_markdown": "Markdown herunterladen",
            "download_docx": "DOCX herunterladen",
            "download_pdf": "PDF herunterladen",
        },
        "live_preview": {
            "title": "Live-Preview: Folgeunterlagen",
            "notice_with_detail": "Preview, kein finaler Export. {notice}",
            "notice_default": "Preview, kein finaler Export. Es wird kein Artefakt generiert.",
            "empty": "Noch nicht genug Eingaben für eine belastbare Vorschau.",
            "panel_title": "Live-Preview: Folgeunterlagen",
            "panel_caption": (
                "Kurze Vorschau, warum die aktuellen Angaben später Brief, Anzeige, "
                "Suche und Interview-Sheets verändern."
            ),
            "show_preview": "Preview anzeigen",
        },
        "workspace": {
            "outputs_heading": "Recruiting-Unterlagen",
            "outputs_caption": (
                "Wähle eine Unterlage, schärfe die wichtigsten Einflussfaktoren und "
                "generiere direkt aus den aktuellen Daten."
            ),
            "reserved_slot": "Reservierter Slot",
            "not_active": "Noch nicht aktiv",
            "job_ad_description": "Zielgruppenorientierte Stellenanzeige mit AGG-Check.",
            "interview_group_title": "Interview-Vorbereitungssheet",
            "interview_group_description": (
                "HR- oder Fachbereich-Sheet mit Fragen und Bewertungslogik."
            ),
            "interview_group_cta": "Interview-Sheet erstellen",
            "boolean_description": (
                "Kanal-spezifische Suchstrings für aktive Sourcing-Recherche."
            ),
            "reserved_export_title": "Weitere Exportformate",
            "reserved_export_description": "Reserviert für zusätzliche Download-Abläufe.",
            "reserved_templates_title": "Weitere Vorlagen",
            "reserved_templates_description": (
                "Reserviert für künftige Hiring-Team-Unterlagen."
            ),
            "job_ad_prepare": "Stellenanzeige vorbereiten",
            "job_ad_prepare_caption": "Welche Informationen sollen in die Stellenanzeige einfließen?",
            "show_config": "Konfigurationspanel anzeigen",
            "show_config_help": (
                "Blendet Auswahl, Spracheinstellungen und Optimierung für die "
                "Stellenanzeige ein oder aus."
            ),
            "config_hidden": (
                "Panel ausgeblendet. Nutze „Stellenanzeige vorbereiten“ in der Job-Ad-Karte."
            ),
            "more_outputs_heading": "Weitere Recruiting-Unterlagen",
            "more_outputs_caption": (
                "Nachgelagerte Unterlagen bauen auf einem aktuellen Recruiting Brief auf."
            ),
            "export_heading": "Export",
            "export_caption": (
                "Exportfreigabe im Bereich **Brief & Export**: erst prüfen, dann JSON, "
                "Markdown, DOCX oder ESCO-Mapping herunterladen."
            ),
            "export_ready": (
                "Bereit zur Prüfung: Ein gültiger Recruiting Brief ist vorhanden. "
                "Exportieren Sie nur, wenn die Release Gate Karten keine Blocker zeigen."
            ),
            "export_blocked": (
                "Blockiert: Erstellen Sie zuerst den Recruiting Brief. Danach werden "
                "Exportformate freigegeben."
            ),
            "pipeline_heading": "Unterlagen-Pipeline",
            "pipeline_caption": (
                "Release-Status je Unterlage: bereit, offen oder durch konkrete Punkte blockiert."
            ),
            "workspaces_heading": "Arbeitsbereiche",
            "workspaces_note": (
                "Details sind nach Aufgabe getrennt, damit Fakten und Exporte nicht doppelt erscheinen."
            ),
            "tabs_brief": "Brief",
            "tabs_facts": "Fakten",
            "tabs_export": "Export",
            "tabs_tech": "Technik",
            "no_valid_brief": "Noch kein gültiger Recruiting Brief verfügbar.",
            "brief_preview_caption": (
                "Kompakte Vorschau ohne Export-JSON. Downloads liegen im Export-Arbeitsbereich."
            ),
            "export_blocked_no_brief": (
                "Export blockiert: Erstellen oder aktualisieren Sie zuerst den Recruiting Brief."
            ),
            "tech_heading": "Technik",
            "tech_caption": "Technische Vorschauen und Statusdaten bleiben hier gebündelt.",
            "structured_export_preview": "Strukturierte Exportvorschau",
            "output_status": "Unterlagenstatus",
            "enrichment_timing": "Anreicherungs-Laufzeiten",
            "no_timing": "Noch keine Timing-Daten für Enrichment-Pfade verfügbar.",
            "result_heading": "Ergebnis",
            "existing_results": "Vorhandene Ergebnisse",
            "stale_result": (
                "Dieses Ergebnis basiert auf älteren Fakten oder Optionen. Bitte neu generieren."
            ),
            "no_result": "Für diese Unterlage liegt noch kein Ergebnis vor.",
            "status_line": "Status: {status}",
            "release_gate_line": "Release Gate: {status}",
            "status_and_prerequisites": (
                "Status: {status} · Voraussetzungen: {prerequisites}"
            ),
            "input_heading": "Eingaben",
            "prepare_in_panel": "Vorbereitung im separaten Panel unterhalb der Aktionskarten.",
            "placeholder_cta": "{label} (Platzhalter)",
            "refinement_heading": "### Anpassungswünsche",
            "refinement_label": "Was soll am Ergebnis angepasst werden?",
            "refinement_placeholder": (
                "z. B. kürzer, stärker auf Senior-Profile, mehr Interviewfragen zu "
                "Stakeholder-Management …"
            ),
            "apply_changes": "Anpassungen übernehmen",
            "secondary_results": "Weitere Ergebnisse",
            "open_focus": "Als Fokus öffnen: {artifact_label}",
            "no_more_outputs": "Noch keine weiteren Recruiting-Unterlagen vorhanden.",
            "result_focus": "Ergebnis-Fokus",
            "document_column": "Dokument",
            "processing_hub_title": "Processing Hub",
            "processing_hub_subtitle": (
                "Primärer Pfad kompakt: Recruiting Brief → weitere Recruiting-Unterlagen → Export."
            ),
            "pipeline_overview_heading": "Unterlagenübersicht",
            "pipeline_document_column": "Unterlage",
            "pipeline_status_column": "Status",
            "pipeline_prerequisites_column": "Voraussetzungen",
            "pipeline_action_column": "Primäre Aktion",
            "pipeline_line": (
                "**Pipeline:** `Recruiting Brief` → `HR-Sheet/Fachbereich-Sheet` → "
                "`Suchstrings` → `Export`  \n"
                "Status Recruiting Brief: {status} · {label}"
            ),
            "details_heading": "Details: {artifact_label}{suffix}",
        },
        "action_registry": {
            "brief_benefit": (
                "Verdichtet Jobspec und Wizard-Antworten zu einem sofort nutzbaren Recruiting Brief."
            ),
            "brief_cta": "Recruiting Brief erstellen",
            "brief_requirement": "Jobspec und Wizard-Plan sind vorhanden",
            "brief_hint_job": "Extrahierte Jobspec-Daten",
            "brief_hint_answers": "Strukturierte Wizard-Antworten",
            "draft_model": "Entwurfsmodell: {model}",
            "job_ad_benefit": (
                "Erstellt eine zielgruppenorientierte Stellenanzeige mit nachvollziehbarer AGG-Checkliste."
            ),
            "job_ad_cta": "Stellenanzeige erstellen",
            "hr_benefit": (
                "Liefert ein strukturiertes HR-Interviewblatt mit Leitfaden und Bewertungsrubrik."
            ),
            "hr_cta": "HR-Sheet erstellen",
            "hr_blocked_cta": "Recruiting Brief erstellen und danach HR-Sheet erstellen",
            "brief_required": "Aktueller Recruiting Brief ist erforderlich",
            "current_brief_hint": "Aktueller Recruiting Brief (kein automatischer Fallback)",
            "critical_must_haves": "Kritische Must-haves",
            "hr_model": "HR-Sheet-Modell: {model}",
            "fach_benefit": (
                "Liefert ein fachliches Interviewblatt für Vertiefungen und konsistente Bewertung."
            ),
            "fach_cta": "Fachbereich-Sheet erstellen",
            "fach_blocked_cta": (
                "Recruiting Brief erstellen und danach Fachbereich-Sheet erstellen"
            ),
            "must_haves_tasks": "Must-have-Skills und Top-Aufgaben",
            "fach_model": "Fachbereich-Sheet-Modell: {model}",
            "boolean_benefit": (
                "Erstellt kanal-spezifische Suchstrings für Google, LinkedIn und XING."
            ),
            "boolean_cta": "Suchstrings erstellen",
            "boolean_blocked_cta": (
                "Recruiting Brief erstellen und danach Suchstrings erstellen"
            ),
            "skills_hint": "Must-have- und Nice-to-have-Skills",
            "boolean_model": "Suchstrings-Modell: {model}",
        },
    },
    "en": {
        "artifact_status": {
            "current": "Current",
            "stale": "Stale",
            "missing": "Missing",
            "invalid": "Invalid",
            "blocked": "Waiting",
            "open": "Open",
            "ready": "Ready",
            "met": "Met",
        },
        "brief_status": {
            "blocked_message": (
                "Jobspec or wizard plan is missing. The recruiting brief cannot be "
                "created yet."
            ),
            "blocked_cta": "Prepare recruiting brief",
            "missing_message": (
                "Recruiting brief is missing. Create it before releasing follow-up "
                "outputs or exports."
            ),
            "missing_cta": "Create recruiting brief",
            "invalid_message": (
                "Recruiting brief is invalid. Regenerate it before exporting."
            ),
            "invalid_cta": "Regenerate recruiting brief",
            "dirty_message": (
                "Recruiting brief is stale. Update it before export or follow-up outputs."
            ),
            "stale_model_message": (
                "Recruiting brief was created with a different model. Update it before "
                "export or follow-up outputs."
            ),
            "missing_snapshot_message": (
                "Recruiting brief has no current input snapshot. Update it before "
                "export or follow-up outputs."
            ),
            "stale_input_message": (
                "Recruiting brief no longer matches the current inputs. Update it before "
                "export or follow-up outputs."
            ),
            "stale_cta": "Update recruiting brief",
            "current_message": "Recruiting brief is current and can be used as the basis.",
            "current_cta": "Update brief",
            "short_stale": "Recruiting brief is stale.",
        },
        "release_state": {
            "current": "Current and exportable",
            "ready": "Ready to generate",
            "stale": "Stale - update before export",
            "missing": "Missing - create first",
            "invalid": "Invalid - regenerate",
            "blocked": "Blocked - clarify basics",
            "open": "Open",
            "fallback": "Status open",
        },
        "release_gate": {
            "next_step": "Next step: {next_step}",
            "blocker": "Blocker: {reason}",
            "todo": "To do: {next_step}",
            "more_blockers": "Review {count} more blockers in the facts workspace.",
            "release_gate": "Release gate: {status}",
            "status": "Status: {status}",
            "prerequisites": "Prerequisites: {text}",
            "prerequisite": "Prerequisite: {marker} {text}",
            "state_label_warning_one": "1 warning",
            "state_label_warning_many": "{count} warnings",
            "state_label_blockers": "{count} blockers",
            "next_exportable": "Can be exported or updated when inputs change.",
            "next_create": "Create {artifact_label}.",
            "missing_prerequisite_reason": "Jobspec or wizard plan is missing.",
            "missing_prerequisite_next": "Complete Start and reopen Summary.",
            "brief_missing_or_not_ready": "Recruiting brief is missing or not ready yet.",
            "brief_missing_or_not_ready_cta": "Create recruiting brief",
            "sourcing_ready_reason": (
                "Recruiting brief is available; the next step is a sourcing output."
            ),
            "fallback_next_reason": "Next available step based on the current status.",
            "safe_brief_reason": "Brief as the safe starting point.",
            "action_prefix": "Action: {label}",
            "no_next_step": "No next step is available right now.",
            "critical_gap_success": (
                "No critical fact blockers detected. Review the recruiting output cards now."
            ),
            "critical_gap_title": "Fact blockers before export (top 5)",
        },
        "final_export": {
            "title": "Final export paused",
            "blockers": "Blocking items",
            "next_action": "Next action",
            "preview": "Preview remains available.",
            "draft": "Save draft",
            "draft_help": (
                "Saves the current working state as draft JSON. This is not a final export."
            ),
            "fallback_blocker": "Final download is available only after release approval.",
            "expert_details": "Safe expert details",
            "override_available": (
                "Expert override available: only non-critical warnings block final export."
            ),
            "override_hidden": (
                "No override available: critical release blockers must be fixed first."
            ),
            "summary_ready": "Final export ready.",
            "summary_stale": "Final export paused: regenerate the result first.",
            "summary_warning": "Final export paused: review warnings; expert override is possible.",
            "summary_blocked": "Final export paused: fix blockers first.",
            "summary_draft": "Draft can be generated; final export follows release approval.",
            "summary_preview": "Preview remains available; draft generation needs more base context.",
            "summary_open": "Status open.",
            "expert_override_active": (
                "Expert override active: final export is available despite non-critical warnings."
            ),
            "heading": "Final export",
            "caption": (
                "Download approved final exports directly. JSON preview and debug details "
                "are collapsed by default."
            ),
            "download_json": "Download JSON",
            "download_markdown": "Download Markdown",
            "download_docx": "Download DOCX",
            "download_pdf": "Download PDF",
        },
        "live_preview": {
            "title": "Live preview: recruiting outputs",
            "notice_with_detail": "Preview, not a final export. {notice}",
            "notice_default": "Preview, not a final export. No artifact is generated.",
            "empty": "Not enough input yet for a reliable preview.",
            "panel_title": "Live preview: recruiting outputs",
            "panel_caption": (
                "Short preview of how the current inputs will later change the brief, "
                "job ad, search, and interview sheets."
            ),
            "show_preview": "Show preview",
        },
        "workspace": {
            "outputs_heading": "Recruiting outputs",
            "outputs_caption": (
                "Choose an output, sharpen the most important drivers, and generate it "
                "directly from the current data."
            ),
            "reserved_slot": "Reserved slot",
            "not_active": "Not active yet",
            "job_ad_description": "Target-group-oriented job ad with AGG check.",
            "interview_group_title": "Interview preparation sheet",
            "interview_group_description": (
                "HR or hiring manager sheet with questions and evaluation logic."
            ),
            "interview_group_cta": "Create interview sheet",
            "boolean_description": (
                "Channel-specific search strings for active sourcing research."
            ),
            "reserved_export_title": "More export formats",
            "reserved_export_description": "Reserved for additional download flows.",
            "reserved_templates_title": "More templates",
            "reserved_templates_description": (
                "Reserved for future hiring-team outputs."
            ),
            "job_ad_prepare": "Prepare job ad",
            "job_ad_prepare_caption": "Which information should flow into the job ad?",
            "show_config": "Show configuration panel",
            "show_config_help": (
                "Shows or hides selection, language settings, and optimization for the job ad."
            ),
            "config_hidden": "Panel hidden. Use “Prepare job ad” in the job-ad card.",
            "more_outputs_heading": "Further recruiting outputs",
            "more_outputs_caption": (
                "Downstream outputs build on a current recruiting brief."
            ),
            "export_heading": "Export",
            "export_caption": (
                "Release approval in **Brief & export**: review first, then download JSON, "
                "Markdown, DOCX, or ESCO mapping."
            ),
            "export_ready": (
                "Ready for review: a valid recruiting brief is available. Export only "
                "when the release gate cards show no blockers."
            ),
            "export_blocked": (
                "Blocked: create the recruiting brief first. Export formats are released after that."
            ),
            "pipeline_heading": "Output pipeline",
            "pipeline_caption": (
                "Release status for each output: ready, open, or blocked by concrete items."
            ),
            "workspaces_heading": "Workspaces",
            "workspaces_note": (
                "Details are separated by task so facts and exports do not appear twice."
            ),
            "tabs_brief": "Brief",
            "tabs_facts": "Facts",
            "tabs_export": "Export",
            "tabs_tech": "Technical",
            "no_valid_brief": "No valid recruiting brief available yet.",
            "brief_preview_caption": (
                "Compact preview without export JSON. Downloads are in the export workspace."
            ),
            "export_blocked_no_brief": (
                "Export blocked: create or update the recruiting brief first."
            ),
            "tech_heading": "Technical",
            "tech_caption": "Technical previews and status data stay bundled here.",
            "structured_export_preview": "Structured export preview",
            "output_status": "Output status",
            "enrichment_timing": "Enrichment timings",
            "no_timing": "No timing data for enrichment paths available yet.",
            "result_heading": "Result",
            "existing_results": "Existing results",
            "stale_result": (
                "This result is based on older facts or options. Please regenerate it."
            ),
            "no_result": "No result is available for this output yet.",
            "status_line": "Status: {status}",
            "release_gate_line": "Release gate: {status}",
            "status_and_prerequisites": (
                "Status: {status} · Prerequisites: {prerequisites}"
            ),
            "input_heading": "Inputs",
            "prepare_in_panel": "Preparation is in the separate panel below the action cards.",
            "placeholder_cta": "{label} (placeholder)",
            "refinement_heading": "### Change requests",
            "refinement_label": "What should be adjusted in the result?",
            "refinement_placeholder": (
                "e.g. shorter, more focused on senior profiles, more interview questions "
                "about stakeholder management ..."
            ),
            "apply_changes": "Apply changes",
            "secondary_results": "More results",
            "open_focus": "Open as focus: {artifact_label}",
            "no_more_outputs": "No further recruiting outputs available yet.",
            "result_focus": "Result focus",
            "document_column": "Document",
            "processing_hub_title": "Processing hub",
            "processing_hub_subtitle": (
                "Compact primary path: recruiting brief → further recruiting outputs → export."
            ),
            "pipeline_overview_heading": "Output overview",
            "pipeline_document_column": "Output",
            "pipeline_status_column": "Status",
            "pipeline_prerequisites_column": "Prerequisites",
            "pipeline_action_column": "Primary action",
            "pipeline_line": (
                "**Pipeline:** `Recruiting brief` → `HR sheet/hiring manager sheet` → "
                "`Boolean search` → `Export`  \n"
                "Recruiting brief status: {status} · {label}"
            ),
            "details_heading": "Details: {artifact_label}{suffix}",
        },
        "action_registry": {
            "brief_benefit": (
                "Condenses the jobspec and wizard answers into a directly usable recruiting brief."
            ),
            "brief_cta": "Create recruiting brief",
            "brief_requirement": "Jobspec and wizard plan are available",
            "brief_hint_job": "Extracted jobspec data",
            "brief_hint_answers": "Structured wizard answers",
            "draft_model": "Draft model: {model}",
            "job_ad_benefit": (
                "Creates a target-group-oriented job ad with a traceable AGG checklist."
            ),
            "job_ad_cta": "Create job ad",
            "hr_benefit": (
                "Provides a structured HR interview sheet with guide and evaluation rubric."
            ),
            "hr_cta": "Create HR sheet",
            "hr_blocked_cta": "Create recruiting brief, then create HR sheet",
            "brief_required": "Current recruiting brief is required",
            "current_brief_hint": "Current recruiting brief (no automatic fallback)",
            "critical_must_haves": "Critical must-haves",
            "hr_model": "HR sheet model: {model}",
            "fach_benefit": (
                "Provides a hiring manager interview sheet for deep dives and consistent evaluation."
            ),
            "fach_cta": "Create hiring manager sheet",
            "fach_blocked_cta": (
                "Create recruiting brief, then create hiring manager sheet"
            ),
            "must_haves_tasks": "Must-have skills and top tasks",
            "fach_model": "Hiring manager sheet model: {model}",
            "boolean_benefit": (
                "Creates channel-specific search strings for Google, LinkedIn, and XING."
            ),
            "boolean_cta": "Create Boolean search",
            "boolean_blocked_cta": (
                "Create recruiting brief, then create Boolean search"
            ),
            "skills_hint": "Must-have and nice-to-have skills",
            "boolean_model": "Boolean search model: {model}",
        },
    },
}

SUMMARY_EXPORT_COPY: dict[str, dict[str, str]] = {
    "de": {
        "brief_title": "Recruiting Brief - {role_title}",
        "one_liner": "Kurzprofil",
        "hiring_context": "Einstellungskontext",
        "role_summary": "Rollenzusammenfassung",
        "top_responsibilities": "Wichtigste Aufgaben",
        "must_have": "Must-have",
        "nice_to_have": "Nice-to-have",
        "candidate_value": "Candidate Value",
        "salary_caveat": "Vergütungshinweis",
        "dealbreakers": "Ausschlusskriterien",
        "interview_plan": "Interviewplan",
        "evaluation_rubric": "Bewertungsrubrik",
        "risks_open_questions": "Risiken / offene Fragen",
        "job_ad_draft": "Stellenanzeigenentwurf (DE)",
        "boolean_title": "Suchstrings",
        "role_title": "Rolle",
        "must_have_terms": "Must-have-Begriffe",
        "seniority_terms": "Senioritätsbegriffe",
        "exclusion_terms": "Ausschlussbegriffe",
        "target_locations": "Zielregionen",
        "broad": "Breit",
        "focused": "Fokussiert",
        "fallback": "Fallback",
        "channel_limitations": "Kanalgrenzen",
        "usage_notes": "Nutzungshinweise",
        "empty": "—",
    },
    "en": {
        "brief_title": "Recruiting brief - {role_title}",
        "one_liner": "One-liner",
        "hiring_context": "Hiring context",
        "role_summary": "Role summary",
        "top_responsibilities": "Top responsibilities",
        "must_have": "Must-have",
        "nice_to_have": "Nice-to-have",
        "candidate_value": "Candidate value",
        "salary_caveat": "Compensation note",
        "dealbreakers": "Dealbreakers",
        "interview_plan": "Interview plan",
        "evaluation_rubric": "Evaluation rubric",
        "risks_open_questions": "Risks / open questions",
        "job_ad_draft": "Job ad draft",
        "boolean_title": "Boolean search",
        "role_title": "Role title",
        "must_have_terms": "Must-have terms",
        "seniority_terms": "Seniority terms",
        "exclusion_terms": "Exclusion terms",
        "target_locations": "Target locations",
        "broad": "Broad",
        "focused": "Focused",
        "fallback": "Fallback",
        "channel_limitations": "Channel limitations",
        "usage_notes": "Usage notes",
        "empty": "—",
    },
}

SUMMARY_PREVIEW_COPY: dict[str, dict[str, Any]] = {
    "de": {
        "notice": (
            "Live-Vorschau aus aktuellen Eingaben. Kein finaler Export und keine "
            "Artefaktgenerierung."
        ),
        "role_fallback": "Rolle",
        "at_company": "{role_title} bei {company}",
        "salary_from": "ab {amount}",
        "salary_to": "bis {amount}",
        "timeline": {
            "30_days": "30 Tage",
            "60_days": "60 Tage",
            "90_days": "90 Tage",
            "180_days": "180 Tage",
        },
        "decision_scope": {
            "keine_eigenen_entscheidungen": "keine eigenen Entscheidungen",
            "fachliche_empfehlungen": "fachliche Empfehlungen",
            "eigenstaendige_fachentscheidungen": "eigenständige Fachentscheidungen",
            "budget_personal_oder_prioritaeten": "Budget, Personal oder Prioritäten",
        },
        "prefix": {
            "role": "Rolle: {value}",
            "why_role": "Wofür die Rolle da ist: {value}",
            "outputs": "Outputs: {value}",
            "tasks": "Aufgaben: {value}",
            "must_have": "Must-have: {value}",
            "candidate_value": "Candidate Value: {value}",
            "search_core": "Suchkern: {value}",
            "location_filter": "Standortfilter: {value}",
            "remote_signal": "Remote-Signal: {value}",
            "non_negotiable": "Nicht verhandelbar: {value}",
            "decision_scope": "Entscheidungsspielraum: {value}",
            "open_clarify": "Offen klären: {value}",
            "skill_missing": "Skill-Auswahl schärfen, um Trefferrauschen zu senken.",
            "success": "Erfolg erkennen: {value}",
            "validate_responsibility": "Verantwortung validieren: {value}",
            "validate": "Validieren: {value}",
            "work_sample": "Arbeitsprobe/Evidenz: {value}",
            "stages": "Stufen: {value}",
            "scorecard": "Scorecard: {value}",
            "core_questions": "Kernfragen: {value}",
            "first_success": "Erster Erfolgshorizont: {value}",
            "top_tasks": "Top-Aufgaben: {value}",
            "offer": "Angebot: {value}",
        },
        "fragments": {
            "brief": {
                "title": "Recruiting Brief",
            },
            "job_ad": {
                "title": "Job-Ad-Richtung",
                "summary": "Welche Signale später die Anzeige prägen.",
            },
            "boolean_search": {
                "title": "Boolean-Relevanz",
                "summary": "Welche Eingaben den Suchstring scharf oder breit machen.",
            },
            "interview_hr": {
                "title": "HR-Sheet-Folgen",
                "summary": "Welche Antworten später HR-Fragen, Prozess und Evidenz lenken.",
            },
            "interview_fach": {
                "title": "Fachbereich-Sheet-Folgen",
                "summary": "Welche Antworten später fachliche Fragen, Scorecard und Evidenz lenken.",
            },
        },
    },
    "en": {
        "notice": (
            "Live preview from current inputs. Not a final export and no artifact generation."
        ),
        "role_fallback": "role",
        "at_company": "{role_title} at {company}",
        "salary_from": "from {amount}",
        "salary_to": "up to {amount}",
        "timeline": {
            "30_days": "30 days",
            "60_days": "60 days",
            "90_days": "90 days",
            "180_days": "180 days",
        },
        "decision_scope": {
            "keine_eigenen_entscheidungen": "no independent decisions",
            "fachliche_empfehlungen": "functional recommendations",
            "eigenstaendige_fachentscheidungen": "independent functional decisions",
            "budget_personal_oder_prioritaeten": "budget, people, or priorities",
        },
        "prefix": {
            "role": "Role: {value}",
            "why_role": "Why the role exists: {value}",
            "outputs": "Outputs: {value}",
            "tasks": "Tasks: {value}",
            "must_have": "Must-have: {value}",
            "candidate_value": "Candidate value: {value}",
            "search_core": "Search core: {value}",
            "location_filter": "Location filter: {value}",
            "remote_signal": "Remote signal: {value}",
            "non_negotiable": "Non-negotiable: {value}",
            "decision_scope": "Decision scope: {value}",
            "open_clarify": "Clarify: {value}",
            "skill_missing": "Sharpen skill selection to reduce search noise.",
            "success": "Recognize success: {value}",
            "validate_responsibility": "Validate responsibility: {value}",
            "validate": "Validate: {value}",
            "work_sample": "Work sample/evidence: {value}",
            "stages": "Stages: {value}",
            "scorecard": "Scorecard: {value}",
            "core_questions": "Core questions: {value}",
            "first_success": "First success horizon: {value}",
            "top_tasks": "Top tasks: {value}",
            "offer": "Offer: {value}",
        },
        "fragments": {
            "brief": {
                "title": "Recruiting brief",
            },
            "job_ad": {
                "title": "Job-ad direction",
                "summary": "Which signals will shape the job ad later.",
            },
            "boolean_search": {
                "title": "Boolean relevance",
                "summary": "Which inputs make the search string sharp or broad.",
            },
            "interview_hr": {
                "title": "HR sheet impact",
                "summary": "Which answers will steer HR questions, process, and evidence.",
            },
            "interview_fach": {
                "title": "Hiring manager sheet impact",
                "summary": "Which answers will steer domain questions, scorecard, and evidence.",
            },
        },
    },
}

ESCO_UI_COPY: dict[str, dict[str, str]] = {
    "de": {
        "load_taxonomy": "Taxonomie laden",
        "taxonomy_title": "Taxonomie/Breadcrumb",
        "taxonomy_missing_uri": "ESCO-URI fehlt für dieses Konzept.",
        "taxonomy_load_failed": "Taxonomie konnte nicht geladen werden: {error}",
        "no_broader_relation": (
            "Keine übergeordnete Relation (`hasBroaderTransitive`) für dieses "
            "ESCO-Konzept gefunden."
        ),
        "taxonomy_not_loaded": "Taxonomie ist noch nicht geladen.",
        "no_taxonomy": "Keine übergeordnete Taxonomie für dieses ESCO-Konzept verfügbar.",
        "config_invalid": (
            "ESCO-Picker-Konfiguration ist ungültig (fehlender target_state_key)."
        ),
        "anchor_query": "Suchbegriff für Berufsabgleich",
        "context_query": "Suchbegriff für Kontextrolle",
        "default_query": "ESCO Suche",
        "query_placeholder": "Begriff eingeben (z. B. Data Engineer)",
        "anchor_helper": (
            "Der Begriff steuert nur den Berufsabgleich; deine Rollenbeschreibung "
            "und spätere Antworten bleiben unverändert."
        ),
        "search_unavailable": "ESCO-Suche aktuell nicht verfügbar: {error}",
        "no_match": (
            "Der Begriff wurde gesucht, aber es wurde kein passender Beruf gefunden. "
            "Bitte Sprache umschalten (DE/EN), einen kürzeren Suchbegriff ohne "
            "Klammer-Kontext testen oder die Einstellungen prüfen."
        ),
        "diagnostics": (
            "Diagnose: language={language} · selected_version={selected_version} · "
            "fallback_used={fallback_used} · cleaned_query_fallback_used={cleaned_query_fallback_used}"
        ),
        "yes": "ja",
        "no": "nein",
        "suggestions": "Vorschläge",
        "select_reference": "Referenzberuf auswählen",
        "select_context": "Kontextrolle auswählen",
        "select_top": "Top-Vorschlag auswählen",
        "no_suggestions": "Keine Vorschläge verfügbar",
        "selected": "Ausgewählt",
        "alternative": "Alternative",
        "top_match_enter": "Top-Treffer wurde per Enter übernommen.",
        "preview_before_apply": "Preview vor Apply",
        "no_preview_selection": "Noch keine Vorschläge ausgewählt.",
        "preview_selection": "**Vorschau der Auswahl (noch nicht bestätigt):**",
        "validate_failed": "Auswahl konnte nicht validiert werden. Bitte erneut auswählen.",
        "apply": "Apply",
        "confirmed_reference": "**Bestätigter Referenzberuf**",
        "catalog_position": "**Position im Berufsverzeichnis**",
        "confirmed_selection": "Bestätigte ESCO-Auswahl",
        "source": "Quelle",
    },
    "en": {
        "load_taxonomy": "Load taxonomy",
        "taxonomy_title": "Taxonomy/breadcrumb",
        "taxonomy_missing_uri": "ESCO URI is missing for this concept.",
        "taxonomy_load_failed": "Taxonomy could not be loaded: {error}",
        "no_broader_relation": (
            "No broader relation (`hasBroaderTransitive`) found for this ESCO concept."
        ),
        "taxonomy_not_loaded": "Taxonomy is not loaded yet.",
        "no_taxonomy": "No broader taxonomy available for this ESCO concept.",
        "config_invalid": "ESCO picker configuration is invalid (missing target_state_key).",
        "anchor_query": "Search term for occupation matching",
        "context_query": "Search term for context role",
        "default_query": "ESCO search",
        "query_placeholder": "Enter term (e.g. data engineer)",
        "anchor_helper": (
            "The term controls only occupation matching; your role description and later "
            "answers remain unchanged."
        ),
        "search_unavailable": "ESCO search is currently unavailable: {error}",
        "no_match": (
            "The term was searched, but no matching occupation was found. Switch language "
            "(DE/EN), try a shorter term without parenthetical context, or check settings."
        ),
        "diagnostics": (
            "Diagnostics: language={language} · selected_version={selected_version} · "
            "fallback_used={fallback_used} · cleaned_query_fallback_used={cleaned_query_fallback_used}"
        ),
        "yes": "yes",
        "no": "no",
        "suggestions": "Suggestions",
        "select_reference": "Select reference occupation",
        "select_context": "Select context role",
        "select_top": "Select top suggestion",
        "no_suggestions": "No suggestions available",
        "selected": "Selected",
        "alternative": "Alternative",
        "top_match_enter": "Top match was applied via Enter.",
        "preview_before_apply": "Preview before apply",
        "no_preview_selection": "No suggestions selected yet.",
        "preview_selection": "**Selection preview (not confirmed yet):**",
        "validate_failed": "Selection could not be validated. Please select again.",
        "apply": "Apply",
        "confirmed_reference": "**Confirmed reference occupation**",
        "catalog_position": "**Position in the occupation catalog**",
        "confirmed_selection": "Confirmed ESCO selection",
        "source": "Source",
    },
}

TRUST_GRAMMAR_COPY: dict[str, dict[str, Any]] = {
    "de": {
        "states": {
            "detected": {"label": "Erkannt", "action": "prüfen"},
            "suggested": {"label": "Vorschlag", "action": "auswählen"},
            "confirmed": {"label": "Bestätigt", "action": "nutzen"},
            "assumed": {"label": "Annahme", "action": "prüfen"},
            "conflicted": {"label": "Konflikt", "action": "klären"},
            "missing": {"label": "Fehlt", "action": "ergänzen"},
            "fallback": {"label": "Fallback", "action": "prüfen"},
            "evidence": {"label": "Beleg", "action": "ansehen"},
        },
        "hints": {
            "detected": "Automatisch erkannt; bitte bei Bedarf prüfen.",
            "suggested": "Vorschlag aus Kontext oder externer Quelle; erst nach Auswahl verbindlich.",
            "confirmed": "Bestätigt und für die nächsten Schritte nutzbar.",
            "assumed": "Annahme; vor Export prüfen.",
            "conflicted": "Abweichende Quellen; bitte klären.",
            "missing": "Noch nicht vorhanden.",
            "fallback": "Live-Abfrage nicht belastbar; Offline-Index wurde genutzt.",
            "evidence": "Beleg ist verfügbar.",
        },
        "details_title": "Trust-Details",
        "evidence_trigger": "Quelle & Beleg",
        "no_details": "Keine weiteren Trust-Details verfügbar.",
        "unknown": "unbekannt",
        "metadata": {
            "attempted_source": "Versuchte Quelle",
            "final_source": "Genutzte Quelle",
            "fallback_reason": "Fallback-Grund",
            "endpoint": "ESCO-Endpunkt",
            "version": "Version",
            "data_source_mode": "Konfigurierter Modus",
        },
        "sources": {
            "live_api": "Live-API",
            "offline_index": "Offline-Index",
            "hybrid": "Hybrid",
            "esco": "ESCO",
            "jobspec": "Jobspec",
            "homepage": "Website",
            "llm": "AI",
            "manual": "Eingabe",
        },
        "esco_lookup_live_first_hint": "ESCO nutzt die Live-API zuerst; der Offline-Index dient als Fallback.",
        "esco_lookup_fallback_hint": "Live-Abfrage fehlgeschlagen; Ergebnis stammt aus dem Offline-Index.",
        "esco_lookup_offline_hint": "ESCO nutzt den Offline-Index gemäß Konfiguration.",
        "esco_lookup_missing_hint": "Noch keine ESCO-Abfrage in dieser Sitzung.",
    },
    "en": {
        "states": {
            "detected": {"label": "Detected", "action": "review"},
            "suggested": {"label": "Suggested", "action": "select"},
            "confirmed": {"label": "Confirmed", "action": "use"},
            "assumed": {"label": "Assumed", "action": "review"},
            "conflicted": {"label": "Conflict", "action": "resolve"},
            "missing": {"label": "Missing", "action": "add"},
            "fallback": {"label": "Fallback", "action": "review"},
            "evidence": {"label": "Evidence", "action": "view"},
        },
        "hints": {
            "detected": "Detected automatically; review if needed.",
            "suggested": "Suggested from context or an external source; binding only after selection.",
            "confirmed": "Confirmed and usable for next steps.",
            "assumed": "Assumption; review before export.",
            "conflicted": "Sources differ; resolve before relying on it.",
            "missing": "Not available yet.",
            "fallback": "Live lookup was not reliable; the offline index was used.",
            "evidence": "Evidence is available.",
        },
        "details_title": "Trust details",
        "evidence_trigger": "Source & evidence",
        "no_details": "No further trust details available.",
        "unknown": "unknown",
        "metadata": {
            "attempted_source": "Attempted source",
            "final_source": "Used source",
            "fallback_reason": "Fallback reason",
            "endpoint": "ESCO endpoint",
            "version": "Version",
            "data_source_mode": "Configured mode",
        },
        "sources": {
            "live_api": "Live API",
            "offline_index": "Offline index",
            "hybrid": "Hybrid",
            "esco": "ESCO",
            "jobspec": "Jobspec",
            "homepage": "Website",
            "llm": "AI",
            "manual": "Input",
        },
        "esco_lookup_live_first_hint": "ESCO uses the live API first; the offline index is available as fallback.",
        "esco_lookup_fallback_hint": "Live lookup failed; the result comes from the offline index.",
        "esco_lookup_offline_hint": "ESCO uses the offline index according to configuration.",
        "esco_lookup_missing_hint": "No ESCO lookup has run in this session yet.",
    },
}

SALARY_UI_COPY: dict[str, dict[str, str]] = {
    "de": {
        "forecast_heading": "Gehaltsprognose (indikativ)",
        "forecast_year": "Gehaltsprognose (Jahr)",
        "empty": "Noch keine Gehaltsprognose vorhanden.",
        "main_caveat": "Bandbreite und p50 sind indikative Richtwerte (kein Garantiewert).",
        "quality_caveat": (
            "Datenqualität: {quality}% - signalisiert Datenabdeckung und Mapping-Treffer, "
            "nicht Prognosegenauigkeit."
        ),
        "context_caveat": (
            "Kontext: indikative Prognose basierend auf den gewählten Angaben.\n\n"
            "Fehlende Inputs können die Prognosequalität reduzieren."
        ),
        "unavailable": "Die Gehaltsprognose ist vorübergehend nicht verfügbar. Bitte versuche es in Kürze erneut.",
    },
    "en": {
        "forecast_heading": "Salary forecast (indicative)",
        "forecast_year": "Salary forecast (year)",
        "empty": "No salary forecast available yet.",
        "main_caveat": "Range and p50 are indicative guide values, not guarantees.",
        "quality_caveat": (
            "Data quality: {quality}% - indicates data coverage and mapping matches, "
            "not forecast accuracy."
        ),
        "context_caveat": (
            "Context: indicative forecast based on the selected inputs.\n\n"
            "Missing inputs can reduce forecast quality."
        ),
        "unavailable": "The salary forecast is temporarily unavailable. Please try again shortly.",
    },
}


def _normalize_language(language: str | None) -> str:
    normalized = str(language or DEFAULT_LANGUAGE).strip().lower()
    if normalized not in SUPPORTED_COPY_LANGUAGES:
        return DEFAULT_LANGUAGE
    return normalized


def _clean_value(value: str, *, fallback: str) -> str:
    cleaned = str(value or "").strip()
    return cleaned or fallback


def _build_template_context(
    context: VacancyCopyContext | None,
    *,
    language: str,
) -> dict[str, Any]:
    ctx = context or VacancyCopyContext()
    if language == "de":
        role_fallback = "diese Rolle"
        company_fallback = "das Unternehmen"
        location_fallback = "dem relevanten Standort"
    else:
        role_fallback = "this role"
        company_fallback = "the company"
        location_fallback = "the relevant location"

    return {
        "role_title": _clean_value(ctx.role_title, fallback=role_fallback),
        "company_name": _clean_value(ctx.company_name, fallback=company_fallback),
        "location": _clean_value(ctx.location, fallback=location_fallback),
        "department": str(ctx.department or "").strip(),
        "work_model": str(ctx.work_model or "").strip(),
        "seniority_level": str(ctx.seniority_level or "").strip(),
        "readiness_score": 0 if ctx.readiness_score is None else int(ctx.readiness_score),
        "open_questions_count": 0
        if ctx.open_questions_count is None
        else int(ctx.open_questions_count),
        "critical_gaps_count": 0
        if ctx.critical_gaps_count is None
        else int(ctx.critical_gaps_count),
    }


def _safe_format(template: str, values: Mapping[str, Any]) -> str:
    return template.format_map(_SafeTemplateDict(values)).strip()


def _copy_tree_value(
    tree: Mapping[str, Any],
    dotted_key: str,
    *,
    language: str | None = None,
) -> Any:
    normalized_language = _normalize_language(language)
    current: Any = tree.get(normalized_language, tree[DEFAULT_LANGUAGE])
    for part in dotted_key.split("."):
        if not isinstance(current, Mapping) or part not in current:
            current = tree[DEFAULT_LANGUAGE]
            for fallback_part in dotted_key.split("."):
                if not isinstance(current, Mapping) or fallback_part not in current:
                    return dotted_key
                current = current[fallback_part]
            return current
        current = current[part]
    return current


def copy_contract_value(
    tree: Mapping[str, Any],
    dotted_key: str,
    *,
    language: str | None = None,
    **params: Any,
) -> str:
    value = _copy_tree_value(tree, dotted_key, language=language)
    text = str(value)
    return _safe_format(text, params) if params else text


def artifact_label(artifact_id: Any, *, language: str | None = None) -> str:
    if not isinstance(artifact_id, str):
        return ""
    normalized = artifact_id.strip()
    if not normalized:
        return ""
    labels = ARTIFACT_LABELS.get(_normalize_language(language), ARTIFACT_LABELS[DEFAULT_LANGUAGE])
    return labels.get(normalized, normalized)


def summary_ui_copy(
    key: str,
    *,
    language: str | None = None,
    **params: Any,
) -> str:
    return copy_contract_value(SUMMARY_UI_COPY, key, language=language, **params)


def summary_export_copy(
    key: str,
    *,
    language: str | None = None,
    **params: Any,
) -> str:
    return copy_contract_value(SUMMARY_EXPORT_COPY, key, language=language, **params)


def summary_preview_copy(
    key: str,
    *,
    language: str | None = None,
    **params: Any,
) -> str:
    return copy_contract_value(SUMMARY_PREVIEW_COPY, key, language=language, **params)


def esco_ui_copy(
    key: str,
    *,
    language: str | None = None,
    **params: Any,
) -> str:
    return copy_contract_value(ESCO_UI_COPY, key, language=language, **params)


def trust_grammar_copy(
    key: str,
    *,
    language: str | None = None,
    **params: Any,
) -> str:
    return copy_contract_value(TRUST_GRAMMAR_COPY, key, language=language, **params)


def salary_ui_copy(
    key: str,
    *,
    language: str | None = None,
    **params: Any,
) -> str:
    return copy_contract_value(SALARY_UI_COPY, key, language=language, **params)


def active_artifact_label_ids() -> set[str]:
    return set(SUMMARY_ACTIVE_ARTIFACT_IDS)


def _resolve_summary_copy(
    templates: Mapping[str, str],
    values: Mapping[str, Any],
) -> StepCopy:
    critical_gaps = int(values.get("critical_gaps_count", 0) or 0)
    readiness_score = int(values.get("readiness_score", 0) or 0)

    if critical_gaps > 0:
        headline_key = "headline_gap"
        subheadline_key = "subheadline_gap"
    elif readiness_score >= 100:
        headline_key = "headline_ready"
        subheadline_key = "subheadline_ready"
    else:
        headline_key = "headline_default"
        subheadline_key = "subheadline_default"

    return StepCopy(
        headline=_safe_format(templates[headline_key], values),
        subheadline=_safe_format(templates[subheadline_key], values),
        value_line=_safe_format(templates.get("value_line", ""), values),
        primary_cta=_safe_format(templates.get("primary_cta", ""), values),
        secondary_cta=_safe_format(templates.get("secondary_cta", ""), values),
    )


def _resolve_landing_copy(
    templates: Mapping[str, str],
    values: Mapping[str, Any],
    context: VacancyCopyContext | None,
) -> StepCopy:
    has_role_title = bool(context and str(context.role_title or "").strip())
    suffix = "_after_analysis" if has_role_title else ""

    return StepCopy(
        headline=_safe_format(templates[f"headline{suffix}"], values),
        subheadline=_safe_format(templates[f"subheadline{suffix}"], values),
        value_line=_safe_format(templates.get(f"value_line{suffix}", ""), values),
        primary_cta=_safe_format(templates.get("primary_cta", ""), values),
        secondary_cta=_safe_format(templates.get("secondary_cta", ""), values),
    )


def build_step_copy(
    step_key: str,
    *,
    language: str | None = None,
    context: VacancyCopyContext | None = None,
) -> StepCopy:
    normalized_language = _normalize_language(language)
    templates = _COPY.get(normalized_language, _COPY[DEFAULT_LANGUAGE]).get(step_key)
    if templates is None:
        templates = _COPY[DEFAULT_LANGUAGE][STEP_KEY_LANDING]

    values = _build_template_context(context, language=normalized_language)

    if step_key == STEP_KEY_SUMMARY:
        return _resolve_summary_copy(templates, values)
    if step_key == STEP_KEY_LANDING:
        return _resolve_landing_copy(templates, values, context)

    return StepCopy(
        headline=_safe_format(templates["headline"], values),
        subheadline=_safe_format(templates["subheadline"], values),
        value_line=_safe_format(templates.get("value_line", ""), values),
        primary_cta=_safe_format(templates.get("primary_cta", ""), values),
        secondary_cta=_safe_format(templates.get("secondary_cta", ""), values),
    )
