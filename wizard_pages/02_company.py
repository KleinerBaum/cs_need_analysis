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
from ui_layout import render_step_shell, responsive_three_columns, responsive_two_columns
from wizard_pages.base import WizardContext, WizardPage, guard_job_and_plan, nav_buttons

_PAGE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "about": ("über uns", "ueber uns", "about", "unternehmen", "company"),
    "imprint": ("impressum", "imprint", "legal", "rechtliche", "kontakt"),
    "vision_mission": ("vision", "mission", "leitbild", "werte", "purpose"),
}
_TOPIC_LABELS: dict[str, str] = {
    "about": "Über uns",
    "imprint": "Impressum",
    "vision_mission": "Vision und Mission",
}
_USER_AGENT = "cs-need-analysis/1.0 (+https://example.invalid)"
_NOISE_PATTERNS: tuple[str, ...] = (
    "window.adobedatalayer",
    "adobedatalayer.push",
    "cq_analytics",
    "json.parse(",
)


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
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw_html, flags=re.I | re.S)
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


def _find_candidate_urls(
    links: list[tuple[str, str]], topic_keywords: tuple[str, ...], *, limit: int = 6
) -> list[str]:
    ranked: list[tuple[int, str]] = []
    seen: set[str] = set()
    for text, target_url in links:
        if target_url in seen:
            continue
        seen.add(target_url)
        haystack = f"{text} {target_url}".casefold()
        score = sum(1 for keyword in topic_keywords if keyword in haystack)
        if score > 0:
            ranked.append((score, target_url))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [target_url for _, target_url in ranked[:limit]]


def _contains_noise(text: str) -> bool:
    lowered = text.casefold()
    return any(pattern in lowered for pattern in _NOISE_PATTERNS)


def _is_useful_sentence(sentence: str) -> bool:
    cleaned = sentence.strip()
    if len(cleaned) < 35:
        return False
    lowered = cleaned.casefold()
    if _contains_noise(lowered):
        return False
    has_words = len(re.findall(r"[a-zäöüß]{3,}", lowered)) >= 6
    return has_words


def _sentence_score(sentence: str) -> int:
    lowered = sentence.casefold()
    score = 0
    for token in (
        "mitarbeit",
        "standort",
        "umsatz",
        "kunden",
        "projekt",
        "technolog",
        "beratung",
        "mission",
        "vision",
        "werte",
        "nachhaltig",
        "fokus",
        "industrie",
    ):
        if token in lowered:
            score += 2
    if re.search(r"\b(19|20)\d{2}\b", sentence):
        score += 1
    if re.search(r"\b\d{2,}\b", sentence):
        score += 1
    return score


def _extract_essential_sentences(text: str, *, limit: int = 4) -> list[str]:
    if not text:
        return []
    candidates = re.split(r"(?<=[.!?])\s+", text)
    scored: list[tuple[int, str]] = []
    for candidate in candidates:
        cleaned = candidate.strip().replace("•", " ").replace("·", " ")
        if not _is_useful_sentence(cleaned):
            continue
        scored.append((_sentence_score(cleaned), cleaned[:260]))
    scored.sort(key=lambda item: item[0], reverse=True)
    picked: list[str] = []
    seen: set[str] = set()
    for _, sentence in scored:
        normalized = sentence.casefold()
        if normalized in seen:
            continue
        seen.add(normalized)
        picked.append(sentence)
        if len(picked) >= limit:
            break
    return picked


def _extract_imprint_facts(raw_html: str, text: str) -> dict[str, str]:
    facts: dict[str, str] = {}
    compact = re.sub(r"\s+", " ", text)
    email_match = re.search(r"\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b", compact, flags=re.I)
    if email_match:
        facts["E-Mail"] = email_match.group(0)

    hr_match = re.search(
        r"(handelsregister(?:nummer)?|hrb|hra)\s*[:#]?\s*([a-z0-9 -]{4,})",
        compact,
        flags=re.I,
    )
    if hr_match:
        facts["Handelsregister"] = hr_match.group(0).strip(" .,;")

    management_match = re.search(
        r"(geschäftsführer(?:in)?|vorstand|vertretungsberechtigt)[^.:]{0,60}[:.]?\s*([A-ZÄÖÜ][^.;]{3,80})",
        compact,
        flags=re.I,
    )
    if management_match:
        facts["Geschäftsführung/Vorstand"] = management_match.group(0).strip(" .,;")

    address_match = re.search(
        r"([A-ZÄÖÜ][\wÄÖÜäöüß .-]{3,60}\s\d{1,4}[a-zA-Z]?,\s*\d{4,5}\s*[A-ZÄÖÜ][\wÄÖÜäöüß .-]{2,40})"
        r"|(\d{4,5}\s*[A-ZÄÖÜ][\wÄÖÜäöüß .-]{2,40},\s*[A-ZÄÖÜ][\wÄÖÜäöüß .-]{3,60}\s\d{1,4}[a-zA-Z]?)",
        compact,
    )
    if address_match:
        facts["Anschrift"] = address_match.group(0).strip(" .,;")

    company_match = re.search(
        r"(?:firma|unternehmen|gesellschaft)\s*[:.]?\s*([A-ZÄÖÜ][^.;]{3,80})",
        compact,
        flags=re.I,
    )
    if company_match:
        facts["Firma"] = company_match.group(1).strip(" .,;")

    link_emails = re.findall(r"mailto:([^\"'>\\s]+)", raw_html, flags=re.I)
    if "E-Mail" not in facts and link_emails:
        facts["E-Mail"] = str(link_emails[0]).strip()
    return facts


def _derive_topic_facts(topic_key: str, text: str, raw_html: str) -> list[str]:
    facts: list[str] = []
    compact = re.sub(r"\s+", " ", text)
    if topic_key == "imprint":
        imprint_facts = _extract_imprint_facts(raw_html, compact)
        for label in (
            "Firma",
            "Anschrift",
            "E-Mail",
            "Handelsregister",
            "Geschäftsführung/Vorstand",
        ):
            value = imprint_facts.get(label)
            if value:
                facts.append(f"{label}: {value}")
        return facts

    headcount_match = re.search(
        r"(\d{2,3}(?:[.,]\d{3})+|\d{3,6})\s+(?:mitarbeitende|mitarbeiter|employees)",
        compact,
        flags=re.I,
    )
    if headcount_match:
        facts.append(f"Mitarbeitende (Hinweis): {headcount_match.group(1)}")

    for pattern, label in (
        (
            r"(?:(?:gegründet|founded)\s*(?:im|in)?\s*((?:19|20)\d{2})|"
            r"(?:im|in)\s*(?:jahr\s*)?((?:19|20)\d{2})\s*(?:gegründet|founded))",
            "Gegründet",
        ),
        (r"(?:standorte|locations)\s*[:.]?\s*([^.;]{4,80})", "Standorte"),
        (r"(?:branchen|industr(?:y|ies)|fokus)\s*[:.]?\s*([^.;]{4,80})", "Fokus"),
    ):
        match = re.search(pattern, compact, flags=re.I)
        if match:
            matched_value = next((group for group in match.groups() if group), "")
            facts.append(f"{label}: {matched_value.strip()}")
    return facts[:4]


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
        summary = section.get("summary", [])
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
        for topic_key in ("about", "imprint", "vision_mission"):
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
        sections_raw = research.get("sections", {})
        sections = sections_raw if isinstance(sections_raw, dict) else {}
        sections[topic_key] = {
            "source_url": resolved_topic_url,
            "summary": summary,
            "facts": facts,
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
                    homepage_url=homepage, topic_key="about", plan=plan
                )
        with button_col_2:
            if st.button('Ermittle "Impressum"', width="stretch"):
                _run_website_research(
                    homepage_url=homepage, topic_key="imprint", plan=plan
                )
        with button_col_3:
            if st.button(
                'Ermittle "Vision und Mission"',
                width="stretch",
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
        if not section_payload:
            st.caption("Noch keine Analyse durchgeführt.")
        for topic_key, topic_label in _TOPIC_LABELS.items():
            payload_raw = section_payload.get(topic_key, {})
            payload = payload_raw if isinstance(payload_raw, dict) else {}
            summary = payload.get("summary", [])
            facts = payload.get("facts", [])
            if not isinstance(summary, list) or not summary:
                continue
            with st.container(border=True):
                st.write(f"**{topic_label}**")
                source_url = str(payload.get("source_url") or "").strip()
                if source_url:
                    st.caption(f"Quelle: {source_url}")
                if isinstance(facts, list) and facts:
                    for fact in facts:
                        st.write(f"- **{str(fact).strip()}**")
                for line in summary:
                    st.write(f"- {str(line).strip()}")

        matches_raw = research.get("open_question_matches", [])
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
        review_slot=lambda: render_standard_step_review(step_company),
        footer_slot=lambda: nav_buttons(ctx),
    )


PAGE = WizardPage(
    key="company",
    title_de="Unternehmen",
    icon="🏢",
    render=render,
    requires_jobspec=True,
)
