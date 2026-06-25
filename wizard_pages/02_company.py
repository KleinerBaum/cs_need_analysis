# wizard_pages/02_company.py
from __future__ import annotations

import json
from time import perf_counter
from typing import Any, Callable

import streamlit as st

from constants import (
    INTAKE_FACTS,
    FactKey,
    FactResolutionStatus,
    FactSourceType,
    FactValueType,
    SSKey,
    STEP_KEY_COMPANY,
    STEP_SECTION_OPEN_QUESTIONS,
    STEP_SECTION_REVIEW,
    UI_PREFERENCE_DETAILS_EXPANDED_DEFAULT,
    WEBSITE_RESEARCH_OPEN_QUESTION_MATCHES,
    WEBSITE_RESEARCH_SECTIONS,
    WEBSITE_SECTION_FACTS,
    WEBSITE_SECTION_SOURCE_URL,
    WEBSITE_SECTION_SUMMARY,
    WEBSITE_TOPIC_ABOUT,
    WEBSITE_TOPIC_IMPRINT,
    WEBSITE_TOPIC_VISION_MISSION,
)
from services.homepage import (
    WEBSITE_TOPIC_LABELS as _TOPIC_LABELS,
    HomepageResearchInvalidUrlError as _HomepageResearchInvalidUrlError,
    build_company_website_research as _build_company_website_research,
    build_open_question_match_options as _build_open_question_match_options,
    build_website_fact_candidates as _build_website_fact_candidates,
    derive_insights_from_open_questions as _derive_insights_from_open_questions,
    derive_topic_facts as _derive_topic_facts,
    extract_imprint_facts as _extract_imprint_facts,
    fetch_url_text as _fetch_url_text,
    normalize_company_website_research_payload as _normalize_company_website_research_payload,
    normalize_research_facts as _normalize_research_facts,
    normalize_url as _normalize_url,
    strip_html as _strip_html,
)
from schemas import JobAdExtract, Question, QuestionPlan, QuestionStep
from step_sections import (
    build_step_shell_section_kwargs,
    filter_open_questions_for_step,
    get_step_structured_fact_keys,
    question_canonical_fact_key,
)
from ui_components import (
    render_error_banner,
    render_next_best_question_coach,
    render_question_step,
    ReviewRenderContext,
    resolve_standard_review_mode,
    render_standard_step_review,
)
from ui_layout import (
    LazySectionConfig,
    default_secondary_section_open,
    render_jobspec_step_notes,
    render_step_shell,
    responsive_three_columns,
    responsive_two_columns,
)
from usage_events import record_enrichment_timed, record_homepage_fetch_failed
from wizard_pages.base import (
    WizardContext,
    WizardPage,
    guard_job_and_plan,
    is_focus_design_enabled,
    nav_buttons,
    resolve_dynamic_step_copy,
)
from wizard_pages.fact_inputs import (
    compact_text,
    fact_value,
    persist_fact,
    render_multiselect_fact,
    render_number_fact,
    render_select_fact,
    section_container,
    render_text_area_fact,
    render_text_fact,
    split_lines,
)
from wizard_pages.company_work_context import (
    render_non_negotiables_compliance_section,
    render_working_model_location_section,
)
from intake_facts import append_intake_fact_secondary_evidence, write_intake_fact
from state import mark_answer_touched
from wizard_pages.team_section import render_role_context_enrichment
from wizard_pages.trust_grammar import (
    render_trust_indicator,
    trust_state_for_fact_status,
)


_LEADERSHIP_LABELS = {
    "individual_contributor": "Individual Contributor",
    "fachliche_fuehrung": "Fachliche Führung",
    "disziplinarische_fuehrung": "Disziplinarische Führung",
    "beides": "Fachlich und disziplinarisch",
    "unklar": "Noch unklar",
}
_FACT_DEFS_BY_KEY = {fact.fact_key.value: fact for fact in INTAKE_FACTS}
_FACT_OPTION_VALUES = tuple(fact.fact_key.value for fact in INTAKE_FACTS)
_FACT_DISPLAY_LABELS = {
    FactKey.COMPANY_COMPANY_NAME.value: "Unternehmensname",
    FactKey.COMPANY_BRAND_NAME.value: "Marke",
    FactKey.COMPANY_COMPANY_WEBSITE.value: "Website",
    FactKey.COMPANY_LOCATION_CITY.value: "Stadt",
    FactKey.COMPANY_LOCATION_COUNTRY.value: "Land",
    FactKey.COMPANY_EMPLOYER_PITCH.value: "Unternehmensbeschreibung",
    FactKey.COMPANY_ROLE_RELEVANT_POSITIONING.value: "Positionierung",
    FactKey.COMPANY_BUSINESS_UNIT.value: "Geschäftsbereich",
    FactKey.COMPANY_HIRING_REASON.value: "Besetzungsgrund",
    FactKey.COMPANY_GROWTH_CONTEXT.value: "Wachstumskontext",
    FactKey.COMPANY_ROLE_BUSINESS_IMPACT.value: "Business Impact",
    FactKey.COMPANY_WORK_ARRANGEMENT.value: "Arbeitsmodell",
    FactKey.COMPANY_OFFICE_DAYS_PER_WEEK.value: "Bürotage pro Woche",
    FactKey.COMPANY_ALLOWED_REGIONS_TIMEZONES.value: "Regionen / Zeitzonen",
    FactKey.COMPANY_LANGUAGE_INTERNAL.value: "Interne Sprache",
    FactKey.COMPANY_LANGUAGE_EXTERNAL.value: "Externe Sprache",
    FactKey.COMPANY_NON_NEGOTIABLES.value: "Nicht verhandelbar",
    FactKey.COMPANY_COMPLIANCE_CONTEXT.value: "Compliance-Kontext",
    FactKey.COMPANY_TARIFF_CONTEXT.value: "Tarif / Vorgaben",
    FactKey.COMPANY_DEPARTMENT_NAME.value: "Abteilung",
    FactKey.COMPANY_REPORTS_TO.value: "Berichtet an",
    FactKey.COMPANY_DIRECT_REPORTS_COUNT.value: "Direct Reports",
    FactKey.TEAM_NAME.value: "Team",
    FactKey.TEAM_LEADERSHIP_SCOPE.value: "Führungsverantwortung",
    FactKey.TEAM_SIZE_DIRECT.value: "Teamgröße",
    FactKey.TEAM_STAKEHOLDERS_PRIMARY.value: "Stakeholder",
    FactKey.TEAM_SUCCESS_CONTEXT_90D.value: "Arbeitsweise im Team",
    FactKey.ROLE_TECH_STACK.value: "Tech Stack",
    FactKey.ROLE_DOMAIN_EXPERTISE.value: "Fachlicher Kontext",
    FactKey.BENEFITS_BENEFITS.value: "Benefits",
}
_FACT_OPTION_LABELS = {
    fact.fact_key.value: _FACT_DISPLAY_LABELS.get(fact.fact_key.value, fact.label)
    for fact in INTAKE_FACTS
}
_TEAM_CONTEXT_FACT_KEYS = frozenset(
    {
        FactKey.COMPANY_DEPARTMENT_NAME,
        FactKey.COMPANY_REPORTS_TO,
        FactKey.COMPANY_DIRECT_REPORTS_COUNT,
        FactKey.TEAM_NAME,
        FactKey.TEAM_LEADERSHIP_SCOPE,
        FactKey.TEAM_SIZE_DIRECT,
        FactKey.TEAM_STAKEHOLDERS_PRIMARY,
        FactKey.TEAM_SUCCESS_CONTEXT_90D,
    }
)
_COMPANY_SECTION_VALUE_STATEMENTS = {
    "Website-Funde": (
        "Website-Belege stützen die Hiring-Story; bestätigte Fakten bleiben führend."
    ),
    "Business-Kontext": (
        "Kläre den Auslöser der Einstellung und den Business Impact der Rolle."
    ),
    "Arbeitgeberprofil": (
        "Formuliere die Arbeitgeberstory, die Briefing und Anzeige tragen soll."
    ),
    "Offene Fragen": (
        "Schließe nur Kontextlücken, die durch Fakten noch nicht abgedeckt sind."
    ),
    "Team & Berichtslinie": (
        "Mache Reporting, Führung und Zusammenarbeit für Kandidat:innen greifbar."
    ),
    "Arbeitsmodell & Standort": (
        "Halte Arbeitsmodell, Ort und Mobilitätsrahmen als klare Erwartungen fest."
    ),
    "Non-negotiables / Compliance": (
        "Trenne harte Must-haves und Compliance-Grenzen von verhandelbaren Präferenzen."
    ),
    "Prüfung": (
        "Prüfe Lücken, Konflikte und Unsicherheiten vor dem nächsten Schritt."
    ),
}


def _compact_website_text(value: Any, *, max_chars: int = 150) -> str:
    text = compact_text(value)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def _company_detail_sections_expanded_by_default() -> bool:
    session_state = getattr(st, "session_state", {})
    state_get = getattr(session_state, "get", None)
    if not callable(state_get):
        return False
    if is_focus_design_enabled():
        preferences = state_get(SSKey.UI_PREFERENCES.value, {})
        if isinstance(preferences, dict):
            return bool(preferences.get(UI_PREFERENCE_DETAILS_EXPANDED_DEFAULT, False))
        return False
    ui_mode = str(state_get(SSKey.UI_MODE.value, "standard")).strip().lower()
    return ui_mode == "expert"


def _render_company_section(
    title: str,
    renderer: Callable[[], None],
    *,
    critical: bool = True,
    collapsed_label: str = "Details bearbeiten",
) -> None:
    st.markdown(f"#### {title}")
    value_statement = _COMPANY_SECTION_VALUE_STATEMENTS.get(title, "")
    if value_statement:
        st.caption(value_statement)
    if critical or _company_detail_sections_expanded_by_default():
        renderer()
        return

    expander = getattr(st, "expander", None)
    if callable(expander):
        with expander(collapsed_label, expanded=False):
            renderer()
        return
    renderer()


def _render_optional_company_detail(
    title: str,
    value_statement: str,
    renderer: Callable[[], None],
) -> None:
    if _company_detail_sections_expanded_by_default():
        st.markdown(f"##### {title}")
        st.caption(value_statement)
        renderer()
        return

    expander = getattr(st, "expander", None)
    if callable(expander):
        with expander(title, expanded=False):
            st.caption(value_statement)
            renderer()
        return

    st.caption(value_statement)
    renderer()


def _render_secondary_company_detail(
    title: str,
    renderer: Callable[[], None],
) -> None:
    if _company_detail_sections_expanded_by_default():
        renderer()
        return

    expander = getattr(st, "expander", None)
    if callable(expander):
        with expander(title, expanded=False):
            renderer()
        return
    renderer()


def _render_focus_company_drilldown(
    renderer: Callable[[], None],
    *,
    collapsed_label: str,
) -> None:
    if not is_focus_design_enabled() or _company_detail_sections_expanded_by_default():
        renderer()
        return
    expander = getattr(st, "expander", None)
    if callable(expander):
        with expander(collapsed_label, expanded=False):
            renderer()
        return
    renderer()


def _render_section_form(
    *,
    form_key: str,
    submit_label: str,
    renderer: Callable[[], None],
) -> None:
    if callable(getattr(st, "form", None)) and callable(
        getattr(st, "form_submit_button", None)
    ):
        with st.form(form_key, clear_on_submit=False):
            renderer()
            submitted = st.form_submit_button(submit_label, width="stretch")
        if submitted:
            st.success("Abschnitt gespeichert.")
        return
    renderer()


def _filtered_company_open_question_step(
    step: QuestionStep | None,
) -> QuestionStep | None:
    return filter_open_questions_for_step(step, step_key=STEP_KEY_COMPANY)


def _split_company_open_question_steps(
    step: QuestionStep | None,
) -> tuple[QuestionStep | None, QuestionStep | None]:
    if step is None:
        return None, None
    questions = list(getattr(step, "questions", []) or [])
    if not questions:
        return None, None

    company_questions: list[Question] = []
    team_questions: list[Question] = []
    for question in questions:
        if _is_team_open_question(question):
            team_questions.append(question)
        else:
            company_questions.append(question)

    return (
        _clone_question_step(step, title_de="Unternehmen", questions=company_questions),
        _clone_question_step(step, title_de="Team", questions=team_questions),
    )


def _clone_question_step(
    step: QuestionStep,
    *,
    title_de: str,
    questions: list[Question],
) -> QuestionStep | None:
    if not questions:
        return None
    return QuestionStep(
        step_key=step.step_key,
        title_de=title_de,
        description_de="",
        questions=questions,
    )


def _is_team_open_question(question: Any) -> bool:
    fact_key = _question_canonical_fact_key(question)
    if fact_key in _TEAM_CONTEXT_FACT_KEYS:
        return True
    group_key = str(getattr(question, "group_key", "") or "").casefold()
    question_id = str(getattr(question, "id", "") or "").casefold()
    label = str(getattr(question, "label", "") or "").casefold()
    haystack = f"{group_key} {question_id} {label}"
    team_markers = (
        "team",
        "stakeholder",
        "reporting",
        "reports",
        "direct report",
        "leadership",
        "führung",
        "fuehrung",
        "berichtet",
        "zusammenarbeit",
    )
    return any(marker in haystack for marker in team_markers)


def _is_structured_company_duplicate_question(question: Any) -> bool:
    question_id = str(getattr(question, "id", "") or "").strip()
    if question_id in {"ctx_confidential_external_narrative"}:
        return False
    fact_key = _question_canonical_fact_key(question)
    return fact_key in get_step_structured_fact_keys(STEP_KEY_COMPANY)


def _question_canonical_fact_key(question: Any) -> FactKey | None:
    return question_canonical_fact_key(question)


def _collect_open_questions(plan: QuestionPlan) -> list[dict[str, str]]:
    answers_raw = st.session_state.get(SSKey.ANSWERS.value, {})
    answers = answers_raw if isinstance(answers_raw, dict) else {}
    open_questions: list[dict[str, str]] = []
    for step in plan.steps:
        for question in step.questions:
            if answers.get(question.id) not in (None, "", []):
                continue
            open_questions.append(
                {"id": question.id, "step": step.step_key, "label": question.label}
            )
    return open_questions


def _run_website_research(
    *,
    homepage_url: str,
    topic_key: str,
    plan: QuestionPlan,
) -> None:
    started_at = perf_counter()
    try:
        result = _build_company_website_research(
            homepage_url=homepage_url,
            topic_key=topic_key,
            existing_research=st.session_state.get(
                SSKey.COMPANY_WEBSITE_RESEARCH.value,
                {},
            ),
            open_questions=_collect_open_questions(plan),
        )
    except _HomepageResearchInvalidUrlError:
        st.session_state[SSKey.COMPANY_WEBSITE_LAST_ERROR.value] = (
            "Homepage-Check fehlgeschlagen: Keine valide Homepage-URL gefunden. "
            "Nächste Aktion: öffentliche HTTPS-URL prüfen oder Arbeitgeberprofil unten manuell ausfüllen."
        )
        record_enrichment_timed(
            st.session_state,
            stage="homepage_research",
            path=topic_key,
            duration_ms=int((perf_counter() - started_at) * 1000),
            status="invalid_url",
        )
        record_homepage_fetch_failed(
            st.session_state,
            topic_key=topic_key,
            error_type="invalid_url",
        )
        return
    except Exception as exc:
        error_type = type(exc).__name__
        record_enrichment_timed(
            st.session_state,
            stage="homepage_research",
            path=topic_key,
            duration_ms=int((perf_counter() - started_at) * 1000),
            status="error",
            error_type=error_type,
        )
        record_homepage_fetch_failed(
            st.session_state,
            topic_key=topic_key,
            error_type=error_type,
        )
        st.session_state[SSKey.COMPANY_WEBSITE_LAST_ERROR.value] = (
            "Homepage-Check fehlgeschlagen: Die Website konnte nicht verarbeitet werden. "
            "Nächste Aktion: URL prüfen und erneut starten oder Arbeitgeberprofil unten manuell ausfüllen."
        )
        return

    st.session_state[SSKey.COMPANY_WEBSITE_RESEARCH.value] = result.research
    st.session_state[SSKey.COMPANY_WEBSITE_LAST_ERROR.value] = None
    record_enrichment_timed(
        st.session_state,
        stage="homepage_research",
        path=topic_key,
        duration_ms=int((perf_counter() - started_at) * 1000),
        result_count=result.result_count,
    )


def _dismiss_website_recovery_message() -> None:
    st.session_state[SSKey.COMPANY_WEBSITE_LAST_ERROR.value] = None


def _render_website_enrichment(job: JobAdExtract, plan: QuestionPlan) -> None:
    st.caption(
        "Prüfe öffentliche Website-Funde als zusätzliche Evidenz zur bestehenden Hiring-Story."
    )
    extracted_homepage = _normalize_url(
        str(
            fact_value(
                FactKey.COMPANY_COMPANY_WEBSITE,
                job.company_website or "",
            )
            or ""
        )
    )
    manual_homepage_raw = str(
        st.session_state.get(SSKey.COMPANY_WEBSITE_MANUAL_URL.value, "")
    ).strip()
    manual_homepage = _normalize_url(manual_homepage_raw)
    homepage = manual_homepage or extracted_homepage
    if extracted_homepage:
        st.caption(f"Website aus der Anzeige: {extracted_homepage}")
        with st.expander(
            "Andere Website verwenden",
            expanded=bool(
                str(
                    st.session_state.get(SSKey.COMPANY_WEBSITE_LAST_ERROR.value, "")
                    or ""
                ).strip()
            ),
        ):
            st.text_input(
                "Alternative Unternehmenswebsite",
                key=SSKey.COMPANY_WEBSITE_MANUAL_URL.value,
                placeholder="https://www.beispiel.de",
                help="Manuelle URL wird nur für den Website-Check verwendet.",
            )
            if manual_homepage:
                st.caption("Manuelle URL wird für die Analyse verwendet.")
    else:
        st.text_input(
            "Unternehmenswebsite",
            key=SSKey.COMPANY_WEBSITE_MANUAL_URL.value,
            placeholder="https://www.beispiel.de",
            help="Öffentliche Website, die für die Analyse verwendet werden soll.",
        )
        if manual_homepage:
            st.caption("Manuell erfasste URL wird für die Analyse verwendet.")

    button_specs = (
        (WEBSITE_TOPIC_ABOUT, "Über uns prüfen"),
        (WEBSITE_TOPIC_IMPRINT, "Impressum prüfen"),
        (WEBSITE_TOPIC_VISION_MISSION, "Vision/Werte prüfen"),
    )
    button_cols = responsive_three_columns(gap="small")
    for index, (topic_key, button_label) in enumerate(button_specs):
        with button_cols[index]:
            if st.button(
                button_label,
                width="stretch",
                key=f"company.website.research.{topic_key}",
            ):
                _run_website_research(
                    homepage_url=homepage, topic_key=topic_key, plan=plan
                )

    error_text = st.session_state.get(SSKey.COMPANY_WEBSITE_LAST_ERROR.value)
    if isinstance(error_text, str) and error_text.strip():
        with st.container(border=True):
            st.warning(error_text)
            st.caption(
                "Nächste Aktion: URL oben korrigieren und den Check erneut starten oder "
                "Arbeitgeberprofil und Business-Kontext unten direkt manuell ausfüllen."
            )
            st.caption(
                "Vorhandene Website-Funde bleiben erhalten. Website-Funde bleiben Zusatzbelege; "
                "geprüfte Fakten unten manuell erfassen oder nach Prüfung übernehmen."
            )
            st.button(
                "Fehlerhinweis ausblenden",
                key="company.website.recovery.dismiss",
                on_click=_dismiss_website_recovery_message,
            )

    research_raw = st.session_state.get(SSKey.COMPANY_WEBSITE_RESEARCH.value, {})
    research = research_raw if isinstance(research_raw, dict) else {}
    sections = research.get(WEBSITE_RESEARCH_SECTIONS, {})
    section_payload = sections if isinstance(sections, dict) else {}
    if not section_payload:
        st.caption(
            "Noch keine Website-Analyse durchgeführt. Optional URL eintragen und Check starten; sonst Business-Kontext und Arbeitgeberprofil manuell ausfüllen."
        )
        return

    result_cols = responsive_three_columns(gap="small")
    for index, (topic_key, topic_label) in enumerate(_TOPIC_LABELS.items()):
        with result_cols[index]:
            _render_website_topic_result(
                topic_key=topic_key,
                topic_label=topic_label,
                payload=section_payload.get(topic_key, {}),
            )

    _render_website_open_question_matches(research)
    _render_website_fact_review(research)


def _render_website_topic_result(
    *,
    topic_key: str,
    topic_label: str,
    payload: Any,
) -> None:
    section = payload if isinstance(payload, dict) else {}
    summary_raw = section.get(WEBSITE_SECTION_SUMMARY, [])
    summary = summary_raw if isinstance(summary_raw, list) else []
    facts = _normalize_research_facts(section.get(WEBSITE_SECTION_FACTS, {}))
    with st.container(border=True):
        st.write(f"**{topic_label}**")
        if not summary and not facts:
            st.caption("Noch nicht analysiert.")
            return
        fact_lines: list[str] = []
        for label, value in list(facts.items())[:2]:
            value_text = _compact_website_text(value, max_chars=90)
            if not value_text:
                continue
            if label.startswith("fact_"):
                fact_lines.append(value_text)
            else:
                fact_lines.append(f"{label}: {value_text}")
        if fact_lines:
            st.caption(" · ".join(fact_lines))
        summary_lines = [
            _compact_website_text(item, max_chars=130)
            for item in summary
            if _compact_website_text(item, max_chars=130)
        ]
        for line in summary_lines[:1]:
            st.write(f"- {line}")
        source_url = str(section.get(WEBSITE_SECTION_SOURCE_URL) or "").strip()
        if source_url:
            with st.expander("Quelle", expanded=False):
                st.caption(source_url)


def _render_website_open_question_matches(research: dict[str, Any]) -> None:
    matches_raw = research.get(WEBSITE_RESEARCH_OPEN_QUESTION_MATCHES, [])
    matches = matches_raw if isinstance(matches_raw, list) else []
    options = _build_open_question_match_options(matches)
    if not options:
        return

    option_by_id = {
        str(option.get("option_id") or ""): option
        for option in options
        if str(option.get("option_id") or "").strip()
    }
    if not option_by_id:
        return
    existing_raw = st.session_state.get(SSKey.COMPANY_WEBSITE_SELECTED_MATCHES.value, [])
    existing = [
        str(item)
        for item in existing_raw
        if str(item) in option_by_id
    ] if isinstance(existing_raw, list) else []
    selected = st.multiselect(
        "Website-Belege für offene Fragen",
        options=list(option_by_id),
        default=existing,
        format_func=lambda option_id: option_by_id[option_id]["display_label"],
        help=(
            "Merkt passende Website-Hinweise vor. Antworten werden erst nach "
            "Bestätigung im passenden Fragefeld gespeichert."
        ),
    )
    st.session_state[SSKey.COMPANY_WEBSITE_SELECTED_MATCHES.value] = list(selected)


def _render_website_fact_review(research: dict[str, Any]) -> None:
    candidates = _build_website_fact_candidates(research)
    if not candidates:
        return

    expander = getattr(st, "expander", None)
    if callable(expander):
        st.caption(f"{len(candidates)} Website-Belege für Fakten erkannt.")
        with expander(
            f"Belege zu Fakten zuordnen ({len(candidates)})",
            expanded=False,
        ):
            _render_website_fact_review_form(candidates)
        return

    _render_website_fact_review_form(candidates)


def _render_website_fact_review_form(candidates: list[dict[str, Any]]) -> None:
    st.caption(
        "Abweichungen werden ohne aktive Bestätigung nur als Konfliktbeleg dokumentiert."
    )
    review_raw = st.session_state.get(SSKey.COMPANY_WEBSITE_FACT_REVIEW.value, {})
    review_state = review_raw if isinstance(review_raw, dict) else {}
    next_review_state: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []

    with st.form("company.website.fact_review.form"):
        for index, candidate in enumerate(candidates, start=1):
            candidate_id = str(candidate.get("candidate_id") or "").strip()
            if not candidate_id:
                continue
            draft_raw = review_state.get(candidate_id, {})
            draft = draft_raw if isinstance(draft_raw, dict) else {}
            default_fact_key = str(
                draft.get("fact_key") or candidate.get("fact_key") or ""
            ).strip()
            if default_fact_key not in _FACT_OPTION_VALUES:
                default_fact_key = str(candidate.get("fact_key") or "").strip()
            if default_fact_key not in _FACT_OPTION_VALUES:
                continue

            candidate_value = candidate.get("value")
            draft_value = draft.get("value", candidate_value)
            value_type = _value_type_for_fact_key(default_fact_key)
            default_selected = (
                bool(draft.get("selected"))
                if "selected" in draft
                else _default_select_website_candidate(default_fact_key, draft_value)
            )

            key_col, value_col, source_col = responsive_three_columns(gap="small")
            with key_col:
                selected_fact_key = st.selectbox(
                    f"Ziel-Feld {index}",
                    options=_FACT_OPTION_VALUES,
                    index=_FACT_OPTION_VALUES.index(default_fact_key),
                    format_func=lambda value: _FACT_OPTION_LABELS.get(value, value),
                    key=f"company.website.fact_review.{candidate_id}.fact_key",
                )
            value_type = _value_type_for_fact_key(selected_fact_key)
            with value_col:
                parsed_value, parse_error = _render_website_candidate_value_input(
                    candidate_id=candidate_id,
                    label=f"Website-Wert {index}",
                    value=draft_value,
                    value_type=value_type,
                )
            with source_col:
                source_label = str(candidate.get("source_label") or "Website").strip()
                evidence = str(candidate.get("evidence_snippet") or "").strip()
                selected_fact = _coerce_fact_key(selected_fact_key)
                current_value = fact_value(selected_fact) if selected_fact is not None else None
                has_confirmed_conflict = (
                    selected_fact is not None
                    and _is_confirmed_fact_value(selected_fact)
                    and not _is_empty_fact_value(current_value)
                    and not _fact_values_equal(current_value, parsed_value)
                )
                if not _is_empty_fact_value(current_value) and _fact_values_equal(
                    current_value, parsed_value
                ):
                    candidate_status = FactResolutionStatus.CONFIRMED.value
                elif has_confirmed_conflict:
                    candidate_status = FactResolutionStatus.CONFLICTED.value
                else:
                    candidate_status = FactResolutionStatus.INFERRED.value
                render_trust_indicator(
                    state=trust_state_for_fact_status(
                        candidate_status,
                        source_type=FactSourceType.HOMEPAGE.value,
                        confirmed=(
                            candidate_status == FactResolutionStatus.CONFIRMED.value
                        ),
                    ),
                    source_type=FactSourceType.HOMEPAGE.value,
                    source_label=source_label,
                    evidence={
                        "source_type": FactSourceType.HOMEPAGE.value,
                        "source_label": source_label,
                        "resolution_status": candidate_status,
                        "confidence": candidate.get("confidence"),
                        "evidence_snippet": evidence,
                    },
                    streamlit_module=st,
                )
                override_conflict = False
                if has_confirmed_conflict:
                    override_conflict = st.checkbox(
                        "Ausnahme: bestätigten Wert durch Website-Beleg ersetzen",
                        value=bool(draft.get("override_conflict", False)),
                        key=(
                            "company.website.fact_review."
                            f"{candidate_id}.override_conflict"
                        ),
                    )
                if parse_error:
                    st.error(parse_error)
                selected = st.checkbox(
                    "Als Zusatzbeleg übernehmen",
                    value=default_selected,
                    key=f"company.website.fact_review.{candidate_id}.selected",
                )

            next_review_state[candidate_id] = {
                "fact_key": selected_fact_key,
                "value": parsed_value,
                "selected": selected,
                "override_conflict": override_conflict,
            }
            rows.append(
                {
                    "candidate": candidate,
                    "fact_key": selected_fact_key,
                    "value": parsed_value,
                    "selected": selected,
                    "override_conflict": override_conflict,
                    "parse_error": parse_error,
                }
            )

        submitted = st.form_submit_button(
            "Website-Belege übernehmen", width="stretch"
        )

    st.session_state[SSKey.COMPANY_WEBSITE_FACT_REVIEW.value] = next_review_state
    if not submitted:
        return

    saved_count = 0
    corroborated_count = 0
    conflict_count = 0
    skipped_count = 0
    for row in rows:
        if not row["selected"]:
            continue
        value = row["value"]
        if row["parse_error"] or _is_empty_fact_value(value):
            skipped_count += 1
            continue
        fact_key = _coerce_fact_key(row["fact_key"])
        if fact_key is None:
            skipped_count += 1
            continue
        result = _persist_homepage_fact_candidate(
            fact_key=fact_key,
            value=value,
            candidate=row["candidate"],
            override_conflict=bool(row["override_conflict"]),
        )
        if result == "conflicted":
            conflict_count += 1
        elif result == "corroborated":
            corroborated_count += 1
        else:
            saved_count += 1

    if saved_count:
        st.success(f"{saved_count} leere Fakten mit Website-Beleg gefüllt.")
    if corroborated_count:
        st.success(f"{corroborated_count} Website-Belege als Bestätigung ergänzt.")
    if conflict_count:
        st.warning(
            f"{conflict_count} Website-Konflikte wurden als zusätzlicher Beleg gespeichert."
        )
    if skipped_count:
        st.warning(
            f"{skipped_count} ausgewählte Kontextwerte wurden nicht gespeichert. Korrigiere den Wert oder entferne die Auswahl."
        )


def _render_website_candidate_value_input(
    *,
    candidate_id: str,
    label: str,
    value: Any,
    value_type: FactValueType,
) -> tuple[Any, str | None]:
    if value_type in {FactValueType.STRING, FactValueType.DATE_STRING}:
        current = compact_text(value)
        rendered = st.text_area(
            label,
            value=current,
            height=70,
            key=f"company.website.fact_review.{candidate_id}.value.string",
        )
        return rendered.strip(), None
    if value_type == FactValueType.STRING_LIST:
        current = "\n".join(split_lines(value))
        rendered = st.text_area(
            label,
            value=current,
            height=90,
            key=f"company.website.fact_review.{candidate_id}.value.list",
        )
        return split_lines(rendered), None
    if value_type == FactValueType.INTEGER:
        current = _coerce_int(value, default=0)
        rendered = st.number_input(
            label,
            min_value=0,
            max_value=1_000_000,
            value=current,
            step=1,
            key=f"company.website.fact_review.{candidate_id}.value.int",
        )
        return int(rendered), None
    if value_type == FactValueType.BOOLEAN:
        current = bool(value) if isinstance(value, bool) else False
        rendered = st.selectbox(
            label,
            options=[True, False],
            index=0 if current else 1,
            format_func=lambda item: "Ja" if item else "Nein",
            key=f"company.website.fact_review.{candidate_id}.value.bool",
        )
        return bool(rendered), None

    current_text = _format_jsonish_value(value)
    rendered = st.text_area(
        label,
        value=current_text,
        height=110,
        key=f"company.website.fact_review.{candidate_id}.value.json",
    )
    parsed, error = _parse_jsonish_value(rendered, value_type)
    return parsed, error


def _persist_homepage_fact_candidate(
    *,
    fact_key: FactKey,
    value: Any,
    candidate: dict[str, Any],
    override_conflict: bool = False,
) -> str:
    answers_raw = st.session_state.get(SSKey.ANSWERS.value, {})
    answers = answers_raw if isinstance(answers_raw, dict) else {}
    previous_value = fact_value(fact_key)
    source_label = str(candidate.get("source_label") or "Website-Analyse").strip()
    confidence = candidate.get("confidence")
    evidence_snippet = str(candidate.get("evidence_snippet") or "").strip() or None
    if (
        _is_confirmed_fact_value(fact_key)
        and not _is_empty_fact_value(previous_value)
        and not _fact_values_equal(previous_value, value)
    ):
        append_intake_fact_secondary_evidence(
            st.session_state,
            fact_key,
            value=value,
            source_type=FactSourceType.HOMEPAGE,
            source_label=source_label,
            confidence=confidence,
            evidence_snippet=evidence_snippet,
            confirmed=override_conflict,
            resolution_status=(
                FactResolutionStatus.CONFIRMED
                if override_conflict
                else FactResolutionStatus.CONFLICTED
            ),
        )
        if not override_conflict:
            return "conflicted"

    elif not _is_empty_fact_value(previous_value) and _fact_values_equal(
        previous_value, value
    ):
        append_intake_fact_secondary_evidence(
            st.session_state,
            fact_key,
            value=value,
            source_type=FactSourceType.HOMEPAGE,
            source_label=source_label,
            confidence=confidence,
            evidence_snippet=evidence_snippet,
            confirmed=True,
            resolution_status=FactResolutionStatus.CONFIRMED,
        )
        return "corroborated"

    mark_answer_touched(fact_key.value, previous_value, value)
    answers[fact_key.value] = value
    st.session_state[SSKey.ANSWERS.value] = answers
    write_intake_fact(
        st.session_state,
        fact_key,
        value,
        source_type=FactSourceType.HOMEPAGE,
        source_label=source_label,
        confidence=confidence,
        evidence_snippet=evidence_snippet,
        confirmed=True,
        resolution_status=FactResolutionStatus.CONFIRMED,
    )
    return "saved"


def _is_confirmed_fact_value(fact_key: FactKey) -> bool:
    evidence_raw = st.session_state.get(SSKey.INTAKE_FACT_EVIDENCE.value, {})
    evidence_state = evidence_raw if isinstance(evidence_raw, dict) else {}
    evidence = evidence_state.get(fact_key.value)
    return isinstance(evidence, dict) and bool(evidence.get("confirmed"))


def _default_select_website_candidate(fact_key: str, value: Any) -> bool:
    resolved_fact_key = _coerce_fact_key(fact_key)
    if resolved_fact_key is None:
        return False
    current = fact_value(resolved_fact_key)
    return _is_empty_fact_value(current) or _fact_values_equal(current, value)


def _value_type_for_fact_key(fact_key: str) -> FactValueType:
    fact_def = _FACT_DEFS_BY_KEY.get(fact_key)
    return fact_def.value_type if fact_def is not None else FactValueType.STRING


def _coerce_fact_key(value: Any) -> FactKey | None:
    try:
        return FactKey(str(value or "").strip())
    except ValueError:
        return None


def _coerce_int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _format_jsonish_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, indent=2)


def _parse_jsonish_value(
    value: str,
    value_type: FactValueType,
) -> tuple[Any, str | None]:
    text = value.strip()
    if not text:
        return None, None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None, "JSON prüfen: gültiges JSON eingeben oder Auswahl deaktivieren."
    if value_type == FactValueType.OBJECT_LIST and not isinstance(parsed, list):
        return None, "JSON-Liste erwartet: mit [...] eingeben oder Auswahl deaktivieren."
    if value_type != FactValueType.OBJECT_LIST and not isinstance(parsed, dict):
        return None, "JSON-Objekt erwartet: mit {...} eingeben oder Auswahl deaktivieren."
    return parsed, None


def _is_empty_fact_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) == 0
    return False


def _fact_values_equal(left: Any, right: Any) -> bool:
    return (
        json.dumps(left, ensure_ascii=False, sort_keys=True, default=str)
        == json.dumps(right, ensure_ascii=False, sort_keys=True, default=str)
    )


def _format_company_header(job: JobAdExtract) -> str:
    company_name = (job.company_name or "").strip()
    job_title = (job.job_title or "").strip()

    if company_name and job_title:
        return f"Unternehmen · {company_name} ({job_title})"
    if company_name:
        return f"Unternehmen · {company_name}"
    if job_title:
        return f"Unternehmen · Kontext für {job_title}"
    return "Unternehmenskontext klären"


def _format_company_subheader(job: JobAdExtract) -> str | None:
    location_city = (job.location_city or "").strip()
    remote_policy = (job.remote_policy or "").strip()

    parts = [part for part in [location_city, remote_policy] if part]
    if not parts:
        return None
    return " · ".join(parts)


def _render_employer_profile_section(job: JobAdExtract) -> None:
    def _render_fields() -> None:
        with section_container(border=True):
            left, right = responsive_two_columns(gap="large")
            with left:
                render_text_fact(
                    FactKey.COMPANY_COMPANY_NAME,
                    "Unternehmensname",
                    default=job.company_name or "",
                )
            with right:
                render_text_area_fact(
                    FactKey.COMPANY_EMPLOYER_PITCH,
                    "Wie würden Sie das Unternehmen in 1-2 Sätzen für Kandidat:innen beschreiben?",
                    height=110,
                )

            def _render_company_data() -> None:
                brand_col, website_col = responsive_two_columns(gap="large")
                with brand_col:
                    render_text_fact(
                        FactKey.COMPANY_BRAND_NAME,
                        "Marke / Brand",
                        default=job.brand_name or "",
                    )
                with website_col:
                    render_text_fact(
                        FactKey.COMPANY_COMPANY_WEBSITE,
                        "Unternehmenswebsite",
                        default=job.company_website or "",
                        placeholder="https://www.beispiel.de",
                    )

            _render_secondary_company_detail(
                "Sekundäre Arbeitgeberdaten",
                _render_company_data,
            )

    _render_company_section(
        "Arbeitgeberprofil",
        lambda: _render_section_form(
            form_key="company.employer_profile.form",
            submit_label="Arbeitgeberprofil speichern",
            renderer=_render_fields,
        ),
    )


def _render_business_context_section(job: JobAdExtract) -> None:
    def _render_fields() -> None:
        with section_container(border=True):
            left, right = responsive_two_columns(gap="large")
            with left:
                render_text_fact(
                    FactKey.COMPANY_HIRING_REASON,
                    "Warum wird diese Rolle jetzt besetzt?",
                    placeholder="z. B. Wachstum, Ersatz, neue Capability, Transformation",
                )
            with right:
                render_text_area_fact(
                    FactKey.COMPANY_ROLE_BUSINESS_IMPACT,
                    "Welchen Business Impact soll die Rolle für das Unternehmen haben?",
                    height=110,
                )

            def _render_secondary_business_context() -> None:
                context_left, context_right = responsive_two_columns(gap="large")
                with context_left:
                    render_text_fact(
                        FactKey.COMPANY_BUSINESS_UNIT,
                        "In welchem Geschäfts- oder Produktbereich sitzt die Rolle?",
                        default=job.department_name or "",
                    )
                    render_multiselect_fact(
                        FactKey.COMPANY_ROLE_RELEVANT_POSITIONING,
                        "Welche Positionierungsaspekte sind für diese Rolle relevant?",
                        options=[
                            "Marktposition",
                            "Produkt",
                            "Wachstum",
                            "Stabilität",
                            "Technologie",
                            "Mission",
                            "Kundennutzen",
                            "Sonstiges",
                        ],
                    )
                with context_right:
                    render_text_area_fact(
                        FactKey.COMPANY_GROWTH_CONTEXT,
                        "Welcher Markt-, Wachstums- oder Aufbaukontext ist relevant?",
                        height=100,
                    )

            _render_secondary_company_detail(
                "Sekundärer Business-Kontext",
                _render_secondary_business_context,
            )

    _render_company_section(
        "Business-Kontext",
        lambda: _render_section_form(
            form_key="company.business_context.form",
            submit_label="Business-Kontext speichern",
            renderer=_render_fields,
        ),
    )


def _render_team_reporting_section(job: JobAdExtract, *, ctx: WizardContext) -> None:
    def _render_team_reporting_fields() -> None:
        with section_container(border=True):
            team_col, reports_to_col, scope_col = responsive_three_columns(
                gap="large"
            )
            with team_col:
                render_text_fact(
                    FactKey.TEAM_NAME,
                    "Welches Team nimmt die Person auf?",
                    default=job.department_name or "",
                )
            with reports_to_col:
                render_text_fact(
                    FactKey.COMPANY_REPORTS_TO,
                    "An wen berichtet die Rolle?",
                    default=job.reports_to or "",
                )
            with scope_col:
                render_select_fact(
                    FactKey.TEAM_LEADERSHIP_SCOPE,
                    "Welche Führungsverantwortung hat die Rolle?",
                    options=tuple(_LEADERSHIP_LABELS),
                    default="individual_contributor",
                    labels=_LEADERSHIP_LABELS,
                )

            def _render_secondary_team_context() -> None:
                department_col, direct_reports_col, team_size_col = (
                    responsive_three_columns(gap="large")
                )
                with department_col:
                    render_text_fact(
                        FactKey.COMPANY_DEPARTMENT_NAME,
                        "Abteilung / Fachbereich",
                        default=job.department_name or "",
                    )
                with direct_reports_col:
                    render_number_fact(
                        FactKey.COMPANY_DIRECT_REPORTS_COUNT,
                        "Wie viele Direct Reports hat die Rolle?",
                        min_value=0,
                        max_value=500,
                        default=job.direct_reports_count or 0,
                    )
                with team_size_col:
                    render_number_fact(
                        FactKey.TEAM_SIZE_DIRECT,
                        "Wie groß ist das unmittelbare Team?",
                        min_value=0,
                        max_value=500,
                        default=job.direct_reports_count or 0,
                    )
                render_multiselect_fact(
                    FactKey.TEAM_STAKEHOLDERS_PRIMARY,
                    "Mit welchen wichtigsten Stakeholdern arbeitet die Person regelmäßig?",
                    options=[
                        "Fachbereich",
                        "Management",
                        "HR/Recruiting",
                        "Sales",
                        "Customer Success",
                        "Operations",
                        "Kund:innen",
                        "Lieferanten/Partner",
                        "Sonstiges",
                    ],
                )
                render_text_area_fact(
                    FactKey.TEAM_SUCCESS_CONTEXT_90D,
                    "Welche Arbeitsweise ist im Team nötig, um in den ersten 90 Tagen zu bestehen?",
                    height=100,
                )

            _render_secondary_company_detail(
                "Sekundäre Teamdetails",
                _render_secondary_team_context,
            )

    def _render_fields_and_optional_context() -> None:
        _render_section_form(
            form_key="company.team_reporting.form",
            submit_label="Team & Berichtslinie speichern",
            renderer=_render_team_reporting_fields,
        )
        _render_optional_company_detail(
            "Rollenprofil mit ESCO-Kontext ergänzen",
            "Optionale ESCO-Hinweise ergänzen Teamarbeit, Stakeholder und Führungslogik.",
            lambda: render_role_context_enrichment(
                step=None,
                ctx=ctx,
                adopt_context_callback=_append_context_to_team_success_fact,
                show_heading=False,
            ),
        )

    _render_company_section(
        "Team & Berichtslinie",
        _render_fields_and_optional_context,
    )


def _render_company_context(job: JobAdExtract) -> None:
    _render_business_context_section(job)
    _render_employer_profile_section(job)


def _render_team_context(job: JobAdExtract, *, ctx: WizardContext) -> None:
    _render_team_reporting_section(job, ctx=ctx)


def _append_context_to_team_success_fact(context_line: str) -> bool:
    current = str(fact_value(FactKey.TEAM_SUCCESS_CONTEXT_90D, "") or "").strip()
    addition = context_line.strip()
    if not addition:
        return False
    if addition.casefold() in current.casefold():
        return True
    updated = f"{current}\n- {addition}".strip() if current else f"- {addition}"
    persist_fact(FactKey.TEAM_SUCCESS_CONTEXT_90D, updated)
    return True


def _render_compact_open_questions(
    *,
    title: str,
    step: QuestionStep | None,
    form_key_suffix: str,
) -> None:
    st.markdown(f"##### {title}")
    if step is None or not step.questions:
        st.caption("Keine zusätzlichen offenen Fragen.")
        return
    render_question_step(
        step,
        context_mode="compact",
        form_key_suffix=form_key_suffix,
        show_next_best_question_coach=False,
    )


def _render_website_finds_section(job: JobAdExtract, plan: QuestionPlan) -> None:
    _render_company_section(
        "Website-Funde",
        lambda: _render_website_enrichment(job, plan),
        critical=False,
        collapsed_label="Website-Funde prüfen",
    )


def _render_open_questions_section(
    *,
    open_question_step: QuestionStep | None,
    company_open_question_step: QuestionStep | None,
    team_open_question_step: QuestionStep | None,
) -> None:
    def _render_questions() -> None:
        render_jobspec_step_notes(STEP_KEY_COMPANY)
        render_next_best_question_coach(open_question_step)
        _render_compact_open_questions(
            title="Business / Arbeitgeber",
            step=company_open_question_step,
            form_key_suffix="company_context",
        )
        _render_compact_open_questions(
            title="Team / Stakeholder",
            step=team_open_question_step,
            form_key_suffix="team_context",
        )

    _render_company_section(
        "Offene Fragen",
        _render_questions,
        critical=False,
        collapsed_label="Zusatzfragen anzeigen",
    )


def _render_working_model_section(job: JobAdExtract) -> None:
    _render_company_section(
        "Arbeitsmodell & Standort",
        lambda: render_working_model_location_section(
            job,
            show_heading=False,
            collapse_secondary_details=not _company_detail_sections_expanded_by_default(),
        ),
    )


def _render_compliance_section() -> None:
    _render_company_section(
        "Non-negotiables / Compliance",
        lambda: render_non_negotiables_compliance_section(
            show_heading=False,
            collapse_secondary_details=not _company_detail_sections_expanded_by_default(),
        ),
    )


def _render_company_sections(
    *,
    job: JobAdExtract,
    ctx: WizardContext,
    plan: QuestionPlan,
    open_question_step: QuestionStep | None,
    company_open_question_step: QuestionStep | None,
    team_open_question_step: QuestionStep | None,
) -> None:
    render_error_banner()
    if is_focus_design_enabled():
        _render_company_context(job)
        _render_focus_company_drilldown(
            lambda: _render_website_finds_section(job, plan),
            collapsed_label="Website-Funde prüfen",
        )
    else:
        _render_website_finds_section(job, plan)
        _render_company_context(job)
    _render_open_questions_section(
        open_question_step=open_question_step,
        company_open_question_step=company_open_question_step,
        team_open_question_step=team_open_question_step,
    )
    _render_focus_company_drilldown(
        lambda: _render_team_context(job, ctx=ctx),
        collapsed_label="Team & Berichtslinie bearbeiten",
    )
    _render_focus_company_drilldown(
        lambda: _render_working_model_section(job),
        collapsed_label="Arbeitsmodell & Standort bearbeiten",
    )
    _render_focus_company_drilldown(
        _render_compliance_section,
        collapsed_label="Non-negotiables / Compliance bearbeiten",
    )


def render(ctx: WizardContext) -> None:
    preflight = guard_job_and_plan(ctx)
    if preflight is None:
        return
    job, plan = preflight
    step_company = next(
        (s for s in plan.steps if s.step_key == STEP_KEY_COMPANY),
        None,
    )
    open_question_step = _filtered_company_open_question_step(step_company)
    company_open_question_step, team_open_question_step = (
        _split_company_open_question_steps(open_question_step)
    )

    def _render_open_questions_slot() -> None:
        _render_company_sections(
            job=job,
            ctx=ctx,
            plan=plan,
            open_question_step=open_question_step,
            company_open_question_step=company_open_question_step,
            team_open_question_step=team_open_question_step,
        )

    def _render_review_slot() -> None:
        st.markdown("#### Prüfung")
        st.caption(_COMPANY_SECTION_VALUE_STATEMENTS["Prüfung"])
        render_standard_step_review(
            step_company,
            render_mode=resolve_standard_review_mode(
                context=ReviewRenderContext.STEP_FORM
            ),
        )

    section_kwargs = build_step_shell_section_kwargs(
        step_key=STEP_KEY_COMPANY,
        renderers={
            STEP_SECTION_OPEN_QUESTIONS: _render_open_questions_slot,
            STEP_SECTION_REVIEW: _render_review_slot,
        },
    )

    step_copy = resolve_dynamic_step_copy(STEP_KEY_COMPANY, job=job)
    lazy_section_configs = {
        "review_slot": LazySectionConfig(
            label="Prüfung",
            caption=_COMPANY_SECTION_VALUE_STATEMENTS["Prüfung"],
            button_label="Prüfung öffnen",
            default_open=default_secondary_section_open(classic_default_open=True),
        ),
    }
    render_step_shell(
        title=step_copy.headline,
        subtitle=step_copy.subheadline,
        outcome_text=step_copy.value_line,
        step=step_company,
        lazy_section_configs=lazy_section_configs,
        **section_kwargs,
        footer_slot=lambda: nav_buttons(ctx),
    )


PAGE = WizardPage(
    key=STEP_KEY_COMPANY,
    title_de="Unternehmen",
    icon="🏢",
    render=render,
    requires_jobspec=True,
)
