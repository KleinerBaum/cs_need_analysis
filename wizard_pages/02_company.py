# wizard_pages/02_company.py
from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

import streamlit as st

from constants import (
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
    derive_topic_facts as _derive_topic_facts,
    extract_essential_sentences as _extract_essential_sentences,
    extract_imprint_facts as _extract_imprint_facts,
    extract_links as _extract_links,
    fetch_url_text as _fetch_url_text,
    find_candidate_url as _find_candidate_url,
    find_candidate_urls as _find_candidate_urls,
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
from usage_events import record_homepage_fetch_failed
from wizard_pages.base import WizardContext, WizardPage, guard_job_and_plan, nav_buttons

_TOPIC_LABELS: dict[str, str] = {
    WEBSITE_TOPIC_ABOUT: "Über uns",
    WEBSITE_TOPIC_IMPRINT: "Impressum",
    WEBSITE_TOPIC_VISION_MISSION: "Vision und Mission",
}


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


def _derive_insights_from_open_questions(
    open_questions: list[dict[str, str]], research_sections: dict[str, dict[str, Any]]
) -> list[dict[str, str]]:
    section_corpus: dict[str, str] = {}
    for topic_key, section in research_sections.items():
        if not isinstance(section, dict):
            continue
        summary = section.get(WEBSITE_SECTION_SUMMARY, [])
        if not isinstance(summary, list):
            continue
        section_corpus[topic_key] = " ".join(str(line) for line in summary).casefold()
    corpus = " ".join(section_corpus.values())
    insights: list[dict[str, str]] = []
    for question in open_questions:
        tokens = [
            token
            for token in re.findall(r"[a-zäöüß]{4,}", question["label"].casefold())
        ]
        if not tokens:
            continue
        matched_tokens = [token for token in tokens if token in corpus]
        if not matched_tokens:
            continue
        source_topic = ""
        for topic_key in (
            WEBSITE_TOPIC_ABOUT,
            WEBSITE_TOPIC_IMPRINT,
            WEBSITE_TOPIC_VISION_MISSION,
        ):
            topic_text = section_corpus.get(topic_key, "")
            if any(token in topic_text for token in matched_tokens):
                source_topic = topic_key
                break
        insights.append(
            {
                "question_id": question["id"],
                "step": question["step"],
                "question_label": question["label"],
                "source_topic": source_topic,
                "match_tokens": ", ".join(matched_tokens[:4]),
            }
        )
    return insights[:8]


def _build_open_question_match_options(
    matches: list[dict[str, str]],
) -> list[dict[str, str]]:
    options: list[dict[str, str]] = []
    seen_labels: dict[str, int] = {}
    for match in matches:
        question_id = str(match.get("question_id") or "").strip()
        question_label = str(match.get("question_label") or "").strip()
        if not question_id or not question_label:
            continue
        source_topic = str(match.get("source_topic") or "").strip()
        source_label = _TOPIC_LABELS.get(source_topic, "Website")
        base_label = f"{question_label} · Quelle: {source_label}"
        label_count = seen_labels.get(base_label, 0) + 1
        seen_labels[base_label] = label_count
        display_label = (
            base_label if label_count == 1 else f"{base_label} ({label_count})"
        )
        option_id = f"{question_id}::{source_topic or 'website'}::{label_count}"
        options.append(
            {
                "option_id": option_id,
                "question_id": question_id,
                "question_label": question_label,
                "source_topic": source_topic,
                "source_label": source_label,
                "display_label": display_label,
                "match_tokens": str(match.get("match_tokens") or "").strip(),
            }
        )
    return options


def _run_website_research(
    *,
    homepage_url: str,
    topic_key: str,
    plan: QuestionPlan,
) -> None:
    normalized_homepage = _normalize_url(homepage_url)
    if not normalized_homepage:
        st.session_state[SSKey.COMPANY_WEBSITE_LAST_ERROR.value] = (
            "Keine valide Homepage-URL gefunden."
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

        best_payload: tuple[str, str, list[str], list[str]] | None = None
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
        research = research_raw if isinstance(research_raw, dict) else {}
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
        st.session_state[SSKey.COMPANY_WEBSITE_RESEARCH.value] = research
        st.session_state[SSKey.COMPANY_WEBSITE_LAST_ERROR.value] = None
    except Exception as exc:
        error_type = type(exc).__name__
        record_homepage_fetch_failed(
            st.session_state,
            topic_key=topic_key,
            error_type=error_type,
        )
        st.session_state[SSKey.COMPANY_WEBSITE_LAST_ERROR.value] = (
            f"Homepage konnte nicht verarbeitet werden: {error_type}"
        )


def _render_website_enrichment(job: JobAdExtract, plan: QuestionPlan) -> None:
    st.markdown("### Firmen-Homepage Analyse (Beta)")
    extracted_homepage = _normalize_url(job.company_website or "")
    manual_homepage_raw = str(
        st.session_state.get(SSKey.COMPANY_WEBSITE_MANUAL_URL.value, "")
    ).strip()
    manual_homepage = _normalize_url(manual_homepage_raw)
    homepage = extracted_homepage or manual_homepage
    left_col, right_col = responsive_two_columns(gap="large")
    with left_col:
        st.write("**Extrahierte URL**")
        if extracted_homepage:
            st.code(extracted_homepage, language="text")
        else:
            st.info("Keine Homepage im Jobad erkannt.")
            st.text_input(
                "Homepage manuell eingeben",
                key=SSKey.COMPANY_WEBSITE_MANUAL_URL.value,
                placeholder="https://www.beispiel.de",
            )
            if manual_homepage:
                st.caption("Manuell erfasste URL wird für die Analyse verwendet.")

        button_col_1, button_col_2, button_col_3 = responsive_three_columns(gap="small")
        with button_col_1:
            if st.button('Ermittle "Über uns"', width="stretch"):
                _run_website_research(
                    homepage_url=homepage, topic_key=WEBSITE_TOPIC_ABOUT, plan=plan
                )
        with button_col_2:
            if st.button('Ermittle "Impressum"', width="stretch"):
                _run_website_research(
                    homepage_url=homepage, topic_key=WEBSITE_TOPIC_IMPRINT, plan=plan
                )
        with button_col_3:
            if st.button(
                'Ermittle "Vision und Mission"',
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
            st.caption("Noch keine Analyse durchgeführt.")
        for topic_key, topic_label in _TOPIC_LABELS.items():
            payload_raw = section_payload.get(topic_key, {})
            payload = payload_raw if isinstance(payload_raw, dict) else {}
            summary = payload.get(WEBSITE_SECTION_SUMMARY, [])
            facts = payload.get(WEBSITE_SECTION_FACTS, [])
            if not isinstance(summary, list) or not summary:
                continue
            with st.container(border=True):
                st.write(f"**{topic_label}**")
                source_url = str(payload.get(WEBSITE_SECTION_SOURCE_URL) or "").strip()
                if source_url:
                    st.caption(f"Quelle: {source_url}")
                if isinstance(facts, list) and facts:
                    for fact in facts:
                        st.write(f"- **{str(fact).strip()}**")
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
                "Diese Hinweise können für aktuell unbeantwortete Fragen im weiteren Prozess wiederverwendet werden."
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
                    "Hinweise auswählen",
                    options=option_ids,
                    default=default_selected_ids,
                    selection_mode="multi",
                    format_func=lambda value: option_labels.get(value, value),
                    key="company.website.match_selection.pills",
                )
            else:
                selected_ids = st.multiselect(
                    "Hinweise auswählen",
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
    return "Unternehmen"


def _format_company_subheader(job: JobAdExtract) -> str | None:
    location_city = (job.location_city or "").strip()
    remote_policy = (job.remote_policy or "").strip()

    parts = [part for part in [location_city, remote_policy] if part]
    if not parts:
        return None
    return " · ".join(parts)


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
        _render_website_enrichment(job, plan)
        if step_company is None or not step_company.questions:
            st.info(
                "Für diesen Abschnitt wurden keine spezifischen Fragen erzeugt. Du kannst trotzdem weitergehen."
            )
        else:
            render_question_step(step_company)


    render_step_shell(
        title=_format_company_header(job),
        subtitle=_format_company_subheader(job) or "Kontext zum Unternehmen und Markt.",
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
