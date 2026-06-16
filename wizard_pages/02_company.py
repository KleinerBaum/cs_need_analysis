# wizard_pages/02_company.py
from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter
from typing import Any

import streamlit as st

from constants import (
    FactKey,
    SSKey,
    WEBSITE_RESEARCH_HOMEPAGE_URL,
    WEBSITE_RESEARCH_OPEN_QUESTION_MATCHES,
    WEBSITE_RESEARCH_SECTIONS,
    WEBSITE_SECTION_FACTS,
    WEBSITE_SECTION_FETCHED_AT,
    WEBSITE_SECTION_SOURCE_URL,
    WEBSITE_SECTION_SUMMARY,
    WEBSITE_TOPIC_ABOUT,
    WEBSITE_TOPIC_IMPRINT,
    WEBSITE_TOPIC_VISION_MISSION,
)
from homepage_research import (
    PAGE_KEYWORDS as _PAGE_KEYWORDS,
    WEBSITE_TOPIC_LABELS as _TOPIC_LABELS,
    build_open_question_match_options as _build_open_question_match_options,
    derive_insights_from_open_questions as _derive_insights_from_open_questions,
    derive_topic_facts as _derive_topic_facts,
    extract_essential_sentences as _extract_essential_sentences,
    extract_imprint_facts as _extract_imprint_facts,
    extract_links as _extract_links,
    fetch_url_text as _fetch_url_text,
    find_candidate_url as _find_candidate_url,
    find_candidate_urls as _find_candidate_urls,
    normalize_company_website_research_payload as _normalize_company_website_research_payload,
    normalize_research_facts as _normalize_research_facts,
    normalize_url as _normalize_url,
    strip_html as _strip_html,
)
from schemas import JobAdExtract, QuestionPlan
from ui_components import (
    has_meaningful_value,
    render_error_banner,
    render_question_step,
    ReviewRenderContext,
    resolve_standard_review_mode,
    render_standard_step_review,
)
from ui_layout import render_step_shell, responsive_three_columns, responsive_two_columns
from usage_events import record_enrichment_timed, record_homepage_fetch_failed
from wizard_pages.base import WizardContext, WizardPage, guard_job_and_plan, nav_buttons
from wizard_pages.fact_inputs import (
    compact_text,
    fact_value,
    persist_compact_object,
    persist_fact,
    render_multiselect_fact,
    render_number_fact,
    render_select_fact,
    render_text_area_fact,
    render_text_fact,
    split_lines,
)


_LEADERSHIP_LABELS = {
    "individual_contributor": "Individual Contributor",
    "fachliche_fuehrung": "Fachliche Führung",
    "disziplinarische_fuehrung": "Disziplinarische Führung",
    "beides": "Fachlich und disziplinarisch",
    "unklar": "Noch unklar",
}
_WORK_ARRANGEMENT_LABELS = {
    "onsite": "Vor Ort",
    "hybrid": "Hybrid",
    "remote_country": "Remote im Land",
    "remote_cross_border": "Remote grenzüberschreitend",
    "unknown": "Noch unklar",
}
_CEFR_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")


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
    normalized_homepage = _normalize_url(homepage_url)
    if not normalized_homepage:
        st.session_state[SSKey.COMPANY_WEBSITE_LAST_ERROR.value] = (
            "Keine valide Homepage-URL gefunden."
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
    try:
        resolved_homepage, homepage_html = _fetch_url_text(normalized_homepage)
        links = _extract_links(resolved_homepage, homepage_html)
        keywords = _PAGE_KEYWORDS.get(topic_key, ())
        candidate_urls = _find_candidate_urls(links, keywords)
        if not candidate_urls:
            fallback = _find_candidate_url(links, keywords) or resolved_homepage
            candidate_urls = [fallback]
        if resolved_homepage not in candidate_urls:
            candidate_urls.append(resolved_homepage)

        best_payload: tuple[str, str, list[str], dict[str, str]] | None = None
        for candidate_url in candidate_urls[:5]:
            resolved_topic_url, topic_html = _fetch_url_text(candidate_url)
            text = _strip_html(topic_html)
            summary = _extract_essential_sentences(text)
            facts = _derive_topic_facts(topic_key, text, topic_html)
            payload_score = len(summary) * 2 + len(facts)
            if best_payload is None or payload_score > (
                len(best_payload[2]) * 2 + len(best_payload[3])
            ):
                best_payload = (resolved_topic_url, topic_html, summary, facts)
        if best_payload is None:
            raise RuntimeError("Keine verwertbaren Inhalte auf der Firmenhomepage gefunden.")

        resolved_topic_url, _, summary, facts = best_payload
        research_raw = st.session_state.get(SSKey.COMPANY_WEBSITE_RESEARCH.value, {})
        normalized_research = _normalize_company_website_research_payload(research_raw)
        research = normalized_research if isinstance(normalized_research, dict) else {}
        sections_raw = research.get(WEBSITE_RESEARCH_SECTIONS, {})
        sections = sections_raw if isinstance(sections_raw, dict) else {}
        sections[topic_key] = {
            WEBSITE_SECTION_SOURCE_URL: resolved_topic_url,
            WEBSITE_SECTION_SUMMARY: summary,
            WEBSITE_SECTION_FACTS: facts,
            WEBSITE_SECTION_FETCHED_AT: datetime.now(UTC).isoformat(),
        }
        research[WEBSITE_RESEARCH_HOMEPAGE_URL] = resolved_homepage
        research[WEBSITE_RESEARCH_SECTIONS] = sections
        research[WEBSITE_RESEARCH_OPEN_QUESTION_MATCHES] = _derive_insights_from_open_questions(
            _collect_open_questions(plan),
            sections,
        )
        st.session_state[SSKey.COMPANY_WEBSITE_RESEARCH.value] = (
            _normalize_company_website_research_payload(research)
        )
        st.session_state[SSKey.COMPANY_WEBSITE_LAST_ERROR.value] = None
        record_enrichment_timed(
            st.session_state,
            stage="homepage_research",
            path=topic_key,
            duration_ms=int((perf_counter() - started_at) * 1000),
            result_count=len(summary) + len(facts),
        )
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
            f"Homepage konnte nicht verarbeitet werden: {error_type}"
        )


def _render_website_enrichment(job: JobAdExtract, plan: QuestionPlan) -> None:
    st.markdown("### Unternehmenswebsite")
    extracted_homepage = _normalize_url(job.company_website or "")
    manual_homepage_raw = str(
        st.session_state.get(SSKey.COMPANY_WEBSITE_MANUAL_URL.value, "")
    ).strip()
    manual_homepage = _normalize_url(manual_homepage_raw)
    homepage = extracted_homepage or manual_homepage
    left_col, right_col = responsive_two_columns(gap="large")
    with left_col:
        st.write("**Unternehmenswebsite**")
        if extracted_homepage:
            st.code(extracted_homepage, language="text")
        else:
            st.info("Keine Unternehmenswebsite in der Anzeige erkannt.")
            st.text_input(
                "Unternehmenswebsite",
                key=SSKey.COMPANY_WEBSITE_MANUAL_URL.value,
                placeholder="https://www.beispiel.de",
            )
            if manual_homepage:
                st.caption("Manuell erfasste URL wird für die Analyse verwendet.")

        button_col_1, button_col_2, button_col_3 = responsive_three_columns(gap="small")
        with button_col_1:
            if st.button("Über-uns-Seite auswerten", width="stretch"):
                _run_website_research(
                    homepage_url=homepage, topic_key=WEBSITE_TOPIC_ABOUT, plan=plan
                )
        with button_col_2:
            if st.button("Impressum auswerten", width="stretch"):
                _run_website_research(
                    homepage_url=homepage, topic_key=WEBSITE_TOPIC_IMPRINT, plan=plan
                )
        with button_col_3:
            if st.button(
                "Vision/Mission auswerten",
                width="stretch",
            ):
                _run_website_research(
                    homepage_url=homepage,
                    topic_key=WEBSITE_TOPIC_VISION_MISSION,
                    plan=plan,
                )

        error_text = st.session_state.get(SSKey.COMPANY_WEBSITE_LAST_ERROR.value)
        if isinstance(error_text, str) and error_text.strip():
            st.warning(error_text)

    with right_col:
        research_raw = st.session_state.get(SSKey.COMPANY_WEBSITE_RESEARCH.value, {})
        research = research_raw if isinstance(research_raw, dict) else {}
        sections = research.get(WEBSITE_RESEARCH_SECTIONS, {})
        section_payload = sections if isinstance(sections, dict) else {}
        if not section_payload:
            st.caption("Noch keine Website-Analyse durchgeführt.")
        for topic_key, topic_label in _TOPIC_LABELS.items():
            payload_raw = section_payload.get(topic_key, {})
            payload = payload_raw if isinstance(payload_raw, dict) else {}
            summary = payload.get(WEBSITE_SECTION_SUMMARY, [])
            facts = _normalize_research_facts(payload.get(WEBSITE_SECTION_FACTS, {}))
            if not isinstance(summary, list) or not summary:
                continue
            with st.container(border=True):
                st.write(f"**{topic_label}**")
                source_url = str(payload.get(WEBSITE_SECTION_SOURCE_URL) or "").strip()
                if source_url:
                    st.caption(f"Quelle: {source_url}")
                if facts:
                    for label, value in facts.items():
                        if label.startswith("fact_"):
                            st.write(f"- **{value}**")
                        else:
                            st.write(f"- **{label}:** {value}")
                for line in summary:
                    st.write(f"- {str(line).strip()}")

        matches_raw = research.get(WEBSITE_RESEARCH_OPEN_QUESTION_MATCHES, [])
        matches = [
            match for match in (matches_raw if isinstance(matches_raw, list) else [])
            if isinstance(match, dict)
        ]
        match_options = _build_open_question_match_options(matches)
        if match_options:
            st.markdown("### Hinweise aus der Website-Analyse")
            st.caption(
                "Die Website-Analyse soll offene Fragen abkürzen, nicht fachliche Entscheidungen ersetzen."
            )
            selected_matches_raw = st.session_state.get(
                SSKey.COMPANY_WEBSITE_SELECTED_MATCHES.value, []
            )
            selected_matches = (
                selected_matches_raw if isinstance(selected_matches_raw, list) else []
            )
            selected_option_ids = [
                str(item.get("option_id") or "").strip()
                for item in selected_matches
                if isinstance(item, dict)
            ]
            valid_option_ids = {item["option_id"] for item in match_options}
            default_selected_ids = [
                option_id
                for option_id in selected_option_ids
                if option_id in valid_option_ids
            ]
            options_map = {item["option_id"]: item for item in match_options}
            option_ids = [item["option_id"] for item in match_options]
            option_labels = {item["option_id"]: item["display_label"] for item in match_options}
            if hasattr(st, "pills"):
                selected_ids = st.pills(
                    "Welche Website-Hinweise sollen wir für offene Fragen vormerken?",
                    options=option_ids,
                    default=default_selected_ids,
                    selection_mode="multi",
                    format_func=lambda value: option_labels.get(value, value),
                    key="company.website.match_selection.pills",
                )
            else:
                selected_ids = st.multiselect(
                    "Welche Website-Hinweise sollen wir für offene Fragen vormerken?",
                    options=option_ids,
                    default=default_selected_ids,
                    format_func=lambda value: option_labels.get(value, value),
                    key="company.website.match_selection.multiselect",
                )
            selected_ids = selected_ids if isinstance(selected_ids, list) else []
            resolved_selection = [
                {
                    "option_id": option_id,
                    "question_id": options_map[option_id]["question_id"],
                    "question_label": options_map[option_id]["question_label"],
                    "source_topic": options_map[option_id]["source_topic"],
                    "source_label": options_map[option_id]["source_label"],
                    "match_tokens": options_map[option_id]["match_tokens"],
                    "display_label": options_map[option_id]["display_label"],
                }
                for option_id in selected_ids
                if option_id in options_map
            ]
            st.session_state[SSKey.COMPANY_WEBSITE_SELECTED_MATCHES.value] = (
                resolved_selection
            )
            st.caption(
                f"Ausgewählt: {len(resolved_selection)}/{len(match_options)} Hinweise"
            )
            if resolved_selection:
                with st.expander("Ausgewählte Hinweise (Details)", expanded=False):
                    for item in resolved_selection:
                        tokens = str(item.get("match_tokens") or "").strip()
                        if tokens:
                            st.caption(
                                f"{str(item.get('display_label') or '').strip()} · Treffer: {tokens}"
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


def _render_language_fact(
    *,
    fact_key: FactKey,
    title: str,
    default_context: str,
) -> None:
    current_raw = fact_value(fact_key, {})
    current = current_raw if isinstance(current_raw, dict) else {}
    language = st.text_input(
        f"{title}: Sprache",
        value=compact_text(current.get("language")),
        placeholder="Deutsch, Englisch, ...",
        key=f"fact_input.{fact_key.value}.language",
    )
    current_level = compact_text(current.get("level")) or "B2"
    if current_level not in _CEFR_LEVELS:
        current_level = "B2"
    level = st.selectbox(
        f"{title}: Mindestniveau",
        options=_CEFR_LEVELS,
        index=_CEFR_LEVELS.index(current_level),
        key=f"fact_input.{fact_key.value}.level",
    )
    context = st.text_input(
        f"{title}: Kontext",
        value=compact_text(current.get("context") or default_context),
        key=f"fact_input.{fact_key.value}.context",
    )
    persist_compact_object(
        fact_key,
        {
            "language": language,
            "level": level,
            "context": context,
        },
    )


def _render_structured_company_context(job: JobAdExtract) -> None:
    st.markdown("### Strukturierter Kontext")
    st.caption(
        "Diese Angaben werden als kanonische Fakten gespeichert und in Folgefragen, Summary und Exporten genutzt."
    )

    with st.container(border=True):
        st.markdown("#### Unternehmensprofil")
        left, right = responsive_two_columns(gap="large")
        with left:
            render_text_area_fact(
                FactKey.COMPANY_EMPLOYER_PITCH,
                "Wie würden Sie das Unternehmen in 1-2 Sätzen für Kandidat:innen beschreiben?",
                height=110,
            )
            render_text_fact(
                FactKey.COMPANY_BUSINESS_UNIT,
                "In welchem Geschäfts- oder Produktbereich sitzt die Rolle?",
                default=job.department_name or "",
            )
        with right:
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

    with st.container(border=True):
        st.markdown("#### Team & Reporting")
        col_team, col_scope, col_size = responsive_three_columns(gap="large")
        with col_team:
            render_text_fact(
                FactKey.TEAM_NAME,
                "Welches Team nimmt die Person auf?",
                default=job.department_name or "",
            )
        with col_scope:
            render_select_fact(
                FactKey.TEAM_LEADERSHIP_SCOPE,
                "Welche Führungsverantwortung hat die Rolle?",
                options=tuple(_LEADERSHIP_LABELS),
                default="individual_contributor",
                labels=_LEADERSHIP_LABELS,
            )
        with col_size:
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

    with st.container(border=True):
        st.markdown("#### Arbeitsmodell")
        arrangement_col, days_col = responsive_two_columns(gap="large")
        with arrangement_col:
            render_select_fact(
                FactKey.COMPANY_WORK_ARRANGEMENT,
                "Welches Arbeitsmodell gilt für diese Rolle?",
                options=tuple(_WORK_ARRANGEMENT_LABELS),
                default="unknown",
                labels=_WORK_ARRANGEMENT_LABELS,
            )
        with days_col:
            render_number_fact(
                FactKey.COMPANY_OFFICE_DAYS_PER_WEEK,
                "Wie viele Tage pro Woche vor Ort?",
                min_value=0,
                max_value=5,
                default=0,
            )
        allowed_regions = st.text_area(
            "Zulässige Regionen oder Zeitzonen",
            value="\n".join(split_lines(fact_value(FactKey.COMPANY_ALLOWED_REGIONS_TIMEZONES, []))),
            placeholder="z. B. Deutschland\nDACH\nCET +/- 2h",
            height=90,
            key=f"fact_input.{FactKey.COMPANY_ALLOWED_REGIONS_TIMEZONES.value}",
        )
        region_values = split_lines(allowed_regions)
        persist_fact(FactKey.COMPANY_ALLOWED_REGIONS_TIMEZONES, region_values)
        lang_left, lang_right = responsive_two_columns(gap="large")
        with lang_left:
            _render_language_fact(
                fact_key=FactKey.COMPANY_LANGUAGE_INTERNAL,
                title="Interne Arbeitssprache",
                default_context="interne Zusammenarbeit",
            )
        with lang_right:
            _render_language_fact(
                fact_key=FactKey.COMPANY_LANGUAGE_EXTERNAL,
                title="Externe Kommunikationssprache",
                default_context="Kund:innen / Partner",
            )

    with st.container(border=True):
        st.markdown("#### Non-negotiables & Compliance")
        render_multiselect_fact(
            FactKey.COMPANY_NON_NEGOTIABLES,
            "Welche Rahmenbedingungen sind nicht verhandelbar?",
            options=[
                "Standort",
                "Arbeitszeit",
                "Gehalt",
                "Vertragsart",
                "Sprache",
                "Zertifikat/Nachweis",
                "Reisebereitschaft",
                "Schicht/Rufbereitschaft",
                "Sonstiges",
            ],
        )
        compliance_col, tariff_col = responsive_two_columns(gap="large")
        with compliance_col:
            render_multiselect_fact(
                FactKey.COMPANY_COMPLIANCE_CONTEXT,
                "Welche regulatorischen oder betrieblichen Besonderheiten sind relevant?",
                options=[
                    "Regulierte Branche",
                    "Datenschutz",
                    "Arbeitssicherheit",
                    "Zertifizierungen",
                    "Betriebsrat",
                    "Öffentlicher Sektor",
                    "Sonstiges",
                ],
            )
        with tariff_col:
            render_text_fact(
                FactKey.COMPANY_TARIFF_CONTEXT,
                "Tarifbindung / Betriebsvereinbarung / besondere Vorgaben",
            )


def render(ctx: WizardContext) -> None:
    preflight = guard_job_and_plan(ctx)
    if preflight is None:
        return
    job, plan = preflight
    step_company = next((s for s in plan.steps if s.step_key == "company"), None)

    def _render_extracted_slot() -> None:
        extracted_rows = [
            ("Unternehmen", job.company_name),
            ("Marke/Brand", job.brand_name),
            ("Homepage", job.company_website),
            ("Ort", job.location_city),
            ("Remote Policy", job.remote_policy),
        ]
        shown = False
        for label, value in extracted_rows:
            if has_meaningful_value(value):
                st.write(f"**{label}:** {str(value).strip()}")
                shown = True
        if not shown:
            st.info(
                "Keine verlässlichen Werte erkannt. Details siehe Gaps/Assumptions."
            )

    def _render_main_slot() -> None:
        render_error_banner()
        _render_structured_company_context(job)
        st.divider()
        _render_website_enrichment(job, plan)
        if step_company is None or not step_company.questions:
            st.info(
                "Für diesen Abschnitt wurden keine spezifischen Fragen erzeugt. Du kannst trotzdem weitergehen."
            )
        else:
            render_question_step(step_company)


    render_step_shell(
        title=_format_company_header(job),
        subtitle=_format_company_subheader(job)
        or (
            "Hier schärfst du das Bild hinter der Vakanz: Unternehmen, Markt, "
            "Positionierung und Arbeitskontext."
        ),
        outcome_text=(
            "Ein klarer Company-Kontext (Mission, Markt, Brand, Rahmenbedingungen), "
            "den Recruiting und Kandidat:innen einheitlich nutzen."
        ),
        step=step_company,
        extracted_from_jobspec_slot=_render_extracted_slot,
        extracted_from_jobspec_label="Aus Jobspec extrahiert (Company & Location)",
        main_content_slot=_render_main_slot,
        review_slot=lambda: render_standard_step_review(
            step_company,
            render_mode=resolve_standard_review_mode(context=ReviewRenderContext.STEP_FORM),
        ),
        footer_slot=lambda: nav_buttons(ctx),
    )


PAGE = WizardPage(
    key="company",
    title_de="Unternehmen",
    icon="🏢",
    render=render,
    requires_jobspec=True,
)
