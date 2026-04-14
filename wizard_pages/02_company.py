# wizard_pages/02_company.py
from __future__ import annotations

import html
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

import streamlit as st

from constants import SSKey
from schemas import JobAdExtract, QuestionPlan
from ui_components import (
    has_meaningful_value,
    render_error_banner,
    render_question_step,
    render_standard_step_review,
)
from ui_layout import render_step_shell
from wizard_pages.base import WizardContext, WizardPage, guard_job_and_plan, nav_buttons

_PAGE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "about": ("über uns", "ueber uns", "about", "unternehmen", "company"),
    "imprint": ("impressum", "imprint", "legal", "rechtliche", "kontakt"),
    "vision_mission": ("vision", "mission", "leitbild", "werte", "purpose"),
}
_USER_AGENT = "cs-need-analysis/1.0 (+https://example.invalid)"


def _normalize_url(raw_url: str) -> str:
    raw = str(raw_url or "").strip()
    if not raw:
        return ""
    if not raw.lower().startswith(("http://", "https://")):
        raw = f"https://{raw}"
    parsed = urlparse(raw)
    if not parsed.netloc:
        return ""
    return raw


def _fetch_url_text(url: str, timeout_sec: float = 8.0) -> tuple[str, str]:
    request = Request(url, headers={"User-Agent": _USER_AGENT})
    with urlopen(request, timeout=timeout_sec) as response:
        final_url = str(response.geturl() or url)
        encoding = response.headers.get_content_charset() or "utf-8"
        payload = response.read().decode(encoding, errors="replace")
    return final_url, payload


def _strip_html(raw_html: str) -> str:
    text = re.sub(r"<(script|style)[^>]*>.*?</\\1>", " ", raw_html, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_links(base_url: str, raw_html: str) -> list[tuple[str, str]]:
    matches = re.findall(
        r"<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>",
        raw_html,
        flags=re.I | re.S,
    )
    links: list[tuple[str, str]] = []
    for href, text in matches:
        cleaned_href = str(href).strip()
        if not cleaned_href or cleaned_href.startswith(("mailto:", "tel:", "#")):
            continue
        full_url = urljoin(base_url, cleaned_href)
        label = _strip_html(str(text))
        links.append((label, full_url))
    return links


def _find_candidate_url(
    links: list[tuple[str, str]], topic_keywords: tuple[str, ...]
) -> str | None:
    for text, target_url in links:
        haystack = f"{text} {target_url}".casefold()
        if any(keyword in haystack for keyword in topic_keywords):
            return target_url
    return None


def _extract_essential_sentences(text: str, *, limit: int = 4) -> list[str]:
    if not text:
        return []
    candidates = re.split(r"(?<=[.!?])\s+", text)
    picked: list[str] = []
    for candidate in candidates:
        cleaned = candidate.strip()
        if len(cleaned) < 35:
            continue
        picked.append(cleaned[:260])
        if len(picked) >= limit:
            break
    return picked


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
    corpus = " ".join(
        " ".join(section.get("summary", []) or [])
        for section in research_sections.values()
        if isinstance(section, dict)
    ).casefold()
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
        insights.append(
            {
                "question_id": question["id"],
                "step": question["step"],
                "question_label": question["label"],
                "match_tokens": ", ".join(matched_tokens[:4]),
            }
        )
    return insights[:8]


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
        return
    try:
        resolved_homepage, homepage_html = _fetch_url_text(normalized_homepage)
        links = _extract_links(resolved_homepage, homepage_html)
        keywords = _PAGE_KEYWORDS.get(topic_key, ())
        candidate_url = _find_candidate_url(links, keywords) or resolved_homepage
        resolved_topic_url, topic_html = _fetch_url_text(candidate_url)
        summary = _extract_essential_sentences(_strip_html(topic_html))
        research_raw = st.session_state.get(SSKey.COMPANY_WEBSITE_RESEARCH.value, {})
        research = research_raw if isinstance(research_raw, dict) else {}
        sections_raw = research.get("sections", {})
        sections = sections_raw if isinstance(sections_raw, dict) else {}
        sections[topic_key] = {
            "source_url": resolved_topic_url,
            "summary": summary,
            "fetched_at": datetime.now(UTC).isoformat(),
        }
        research["homepage_url"] = resolved_homepage
        research["sections"] = sections
        research["open_question_matches"] = _derive_insights_from_open_questions(
            _collect_open_questions(plan),
            sections,
        )
        st.session_state[SSKey.COMPANY_WEBSITE_RESEARCH.value] = research
        st.session_state[SSKey.COMPANY_WEBSITE_LAST_ERROR.value] = None
    except Exception as exc:
        st.session_state[SSKey.COMPANY_WEBSITE_LAST_ERROR.value] = (
            f"Homepage konnte nicht verarbeitet werden: {type(exc).__name__}"
        )


def _render_website_enrichment(job: JobAdExtract, plan: QuestionPlan) -> None:
    st.markdown("### Firmen-Homepage Analyse (Beta)")
    homepage = _normalize_url(job.company_website or "")
    left_col, right_col = st.columns([1, 1], gap="large")
    with left_col:
        st.write("**Extrahierte URL**")
        if homepage:
            st.code(homepage, language="text")
        else:
            st.info("Keine Homepage im Jobad erkannt.")

        button_col_1, button_col_2, button_col_3 = st.columns(3)
        with button_col_1:
            if st.button('Ermittle "Über uns"', use_container_width=True):
                _run_website_research(
                    homepage_url=homepage, topic_key="about", plan=plan
                )
        with button_col_2:
            if st.button('Ermittle "Impressum"', use_container_width=True):
                _run_website_research(
                    homepage_url=homepage, topic_key="imprint", plan=plan
                )
        with button_col_3:
            if st.button(
                'Ermittle "Vision und Mission"',
                use_container_width=True,
            ):
                _run_website_research(
                    homepage_url=homepage,
                    topic_key="vision_mission",
                    plan=plan,
                )

        error_text = st.session_state.get(SSKey.COMPANY_WEBSITE_LAST_ERROR.value)
        if isinstance(error_text, str) and error_text.strip():
            st.warning(error_text)

    with right_col:
        research_raw = st.session_state.get(SSKey.COMPANY_WEBSITE_RESEARCH.value, {})
        research = research_raw if isinstance(research_raw, dict) else {}
        sections = research.get("sections", {})
        section_payload = sections if isinstance(sections, dict) else {}
        topic_labels = {
            "about": "Über uns",
            "imprint": "Impressum",
            "vision_mission": "Vision und Mission",
        }
        if not section_payload:
            st.caption("Noch keine Analyse durchgeführt.")
        for topic_key, topic_label in topic_labels.items():
            payload_raw = section_payload.get(topic_key, {})
            payload = payload_raw if isinstance(payload_raw, dict) else {}
            summary = payload.get("summary", [])
            if not isinstance(summary, list) or not summary:
                continue
            with st.container(border=True):
                st.write(f"**{topic_label}**")
                source_url = str(payload.get("source_url") or "").strip()
                if source_url:
                    st.caption(f"Quelle: {source_url}")
                for line in summary:
                    st.write(f"- {str(line).strip()}")

        matches_raw = research.get("open_question_matches", [])
        matches = matches_raw if isinstance(matches_raw, list) else []
        if matches:
            st.markdown("**Abgleich mit offenen Fragen (puristisch)**")
            for match in matches:
                if not isinstance(match, dict):
                    continue
                st.write(
                    "- "
                    f"[{str(match.get('step') or '').strip()}] "
                    f"{str(match.get('question_label') or '').strip()} "
                    f"(Treffer: {str(match.get('match_tokens') or '').strip()})"
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


def _normalize_nace_lookup(raw_lookup: object) -> dict[str, str]:
    if not isinstance(raw_lookup, dict):
        return {}
    normalized: dict[str, str] = {}
    for raw_code, raw_uri in raw_lookup.items():
        code = str(raw_code or "").strip()
        uri = str(raw_uri or "").strip()
        if code and uri:
            normalized[code] = uri
    return normalized


def _render_optional_nace_section() -> None:
    nace_lookup = _normalize_nace_lookup(
        st.session_state.get(SSKey.EURES_NACE_TO_ESCO.value, {})
    )
    has_lookup = bool(nace_lookup)
    configured_source = str(
        st.session_state.get(SSKey.EURES_NACE_SOURCE.value, "") or ""
    ).strip()
    if not has_lookup and not configured_source:
        return

    st.markdown("### NACE (optional)")
    if configured_source:
        st.caption(f"Mapping-Quelle: {configured_source}")

    if not has_lookup:
        st.info(
            "NACE-Mapping ist konfiguriert, aber aktuell nicht im Session-State geladen."
        )
        return

    options = sorted(nace_lookup.keys(), key=str.casefold)
    current_code = str(st.session_state.get(SSKey.COMPANY_NACE_CODE.value, "") or "")
    default_index = options.index(current_code) + 1 if current_code in options else 0

    selected_code = st.selectbox(
        "NACE-Code für diese Vakanz",
        options=[""] + options,
        index=default_index,
        format_func=lambda value: "— nicht gesetzt —" if not value else value,
        key=f"{SSKey.COMPANY_NACE_CODE.value}.widget",
        help=(
            "Optionaler Branchen-Code. Falls gesetzt, wird die gemappte ESCO-URI im "
            "Summary-Readiness-Block berücksichtigt."
        ),
    )
    st.session_state[SSKey.COMPANY_NACE_CODE.value] = selected_code
    if selected_code:
        st.caption(f"Gemappte ESCO-URI: `{nace_lookup.get(selected_code, '')}`")


def render(ctx: WizardContext) -> None:
    preflight = guard_job_and_plan(ctx)
    if preflight is None:
        return
    job, plan = preflight
    step = next((s for s in plan.steps if s.step_key == "company"), None)

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
        _render_optional_nace_section()
        if step is None or not step.questions:
            st.info(
                "Für diesen Abschnitt wurden keine spezifischen Fragen erzeugt. Du kannst trotzdem weitergehen."
            )
            return
        render_question_step(step)

    render_step_shell(
        title=_format_company_header(job),
        subtitle=_format_company_subheader(job) or "Kontext zum Unternehmen und Markt.",
        outcome_text=(
            "Ein klarer Company-Kontext (Mission, Markt, Brand, Rahmenbedingungen), "
            "den Recruiting und Kandidat:innen einheitlich nutzen."
        ),
        step=step,
        extracted_from_jobspec_slot=_render_extracted_slot,
        extracted_from_jobspec_label="Aus Jobspec extrahiert (Company & Location)",
        main_content_slot=_render_main_slot,
        review_slot=lambda: render_standard_step_review(step),
        footer_slot=lambda: nav_buttons(ctx),
    )


PAGE = WizardPage(
    key="company",
    title_de="Unternehmen",
    icon="🏢",
    render=render,
    requires_jobspec=True,
)
