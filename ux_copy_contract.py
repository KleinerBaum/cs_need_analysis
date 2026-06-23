from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from constants import (
    DEFAULT_LANGUAGE,
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
                "Stellenanzeige, Interviewleitfaden, Suchstrings oder Vertrag freigeben."
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
                "Result: a briefing cockpit with a role profile, priorities, open "
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
                "interview guide, search strings, or contract."
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
