"""Guarded homepage fetch and extraction helpers for company enrichment."""

from __future__ import annotations

import html
import ipaddress
import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen

from constants import (
    WEBSITE_RESEARCH_SECTIONS,
    WEBSITE_SECTION_FACTS,
    WEBSITE_SECTION_SUMMARY,
    WEBSITE_TOPIC_ABOUT,
    WEBSITE_TOPIC_IMPRINT,
    WEBSITE_TOPIC_VISION_MISSION,
)

LOGGER = logging.getLogger(__name__)

HOMEPAGE_FETCH_TIMEOUT_SEC = 8.0
HOMEPAGE_FETCH_MAX_BYTES = 1_000_000
USER_AGENT = "cs-need-analysis/1.0 (+https://example.invalid)"
ALLOWED_CONTENT_TYPE_PREFIXES: tuple[str, ...] = (
    "text/html",
    "text/plain",
    "application/xhtml+xml",
)
PAGE_KEYWORDS: dict[str, tuple[str, ...]] = {
    WEBSITE_TOPIC_ABOUT: ("über uns", "ueber uns", "about", "unternehmen", "company"),
    WEBSITE_TOPIC_IMPRINT: ("impressum", "imprint", "legal", "rechtliche", "kontakt"),
    WEBSITE_TOPIC_VISION_MISSION: ("vision", "mission", "leitbild", "werte", "purpose"),
}
WEBSITE_TOPIC_LABELS: dict[str, str] = {
    WEBSITE_TOPIC_ABOUT: "Über uns",
    WEBSITE_TOPIC_IMPRINT: "Impressum",
    WEBSITE_TOPIC_VISION_MISSION: "Vision und Mission",
}
NOISE_PATTERNS: tuple[str, ...] = (
    "window.adobedatalayer",
    "adobedatalayer.push",
    "cq_analytics",
    "json.parse(",
)


@dataclass(frozen=True)
class HomepageFetchResult:
    final_url: str
    payload: str
    content_type: str
    bytes_read: int
    cache_hit: bool = False


class HomepageFetchError(RuntimeError):
    """Raised when homepage content fails fetch guardrails."""


_FETCH_CACHE: dict[str, HomepageFetchResult] = {}


def clear_fetch_cache() -> None:
    """Clear in-process homepage fetch cache."""

    _FETCH_CACHE.clear()


def normalize_url(raw_url: str) -> str:
    raw = str(raw_url or "").strip()
    if not raw:
        return ""
    if raw.startswith("//"):
        raw = f"https:{raw}"
    if not raw.lower().startswith(("http://", "https://")):
        raw = f"https://{raw}"
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    if _is_disallowed_hostname(parsed.hostname or ""):
        return ""
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path or "",
            parsed.params or "",
            parsed.query or "",
            "",
        )
    )


def fetch_url_text(
    url: str,
    timeout_sec: float = HOMEPAGE_FETCH_TIMEOUT_SEC,
) -> tuple[str, str]:
    """Fetch text content from a public homepage URL with guardrails and cache."""

    result = fetch_url_text_result(url, timeout_sec=timeout_sec)
    return result.final_url, result.payload


def fetch_url_text_result(
    url: str,
    *,
    timeout_sec: float = HOMEPAGE_FETCH_TIMEOUT_SEC,
    max_bytes: int = HOMEPAGE_FETCH_MAX_BYTES,
) -> HomepageFetchResult:
    normalized_url = normalize_url(url)
    if not normalized_url:
        raise HomepageFetchError("invalid_or_disallowed_url")

    cached = _FETCH_CACHE.get(normalized_url)
    if cached is not None:
        _log_fetch_event("cache_hit", normalized_url, cache_hit=True)
        return HomepageFetchResult(
            final_url=cached.final_url,
            payload=cached.payload,
            content_type=cached.content_type,
            bytes_read=cached.bytes_read,
            cache_hit=True,
        )

    request = Request(normalized_url, headers={"User-Agent": USER_AGENT})
    _log_fetch_event("request", normalized_url, cache_hit=False)
    with urlopen(request, timeout=timeout_sec) as response:
        final_url = normalize_url(str(response.geturl() or normalized_url))
        if not final_url:
            raise HomepageFetchError("invalid_or_disallowed_redirect")
        content_type = _response_content_type(response)
        if not _is_allowed_content_type(content_type):
            raise HomepageFetchError("unsupported_content_type")
        encoding = response.headers.get_content_charset() or "utf-8"
        raw_payload = response.read(max_bytes + 1)
        if len(raw_payload) > max_bytes:
            raise HomepageFetchError("content_too_large")
        payload = raw_payload.decode(encoding, errors="replace")

    result = HomepageFetchResult(
        final_url=final_url,
        payload=payload,
        content_type=content_type,
        bytes_read=len(raw_payload),
        cache_hit=False,
    )
    _FETCH_CACHE[normalized_url] = result
    _log_fetch_event("success", final_url, cache_hit=False, bytes_read=result.bytes_read)
    return result


def strip_html(raw_html: str) -> str:
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw_html, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_links(base_url: str, raw_html: str) -> list[tuple[str, str]]:
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
        full_url = normalize_url(urljoin(base_url, cleaned_href))
        if not full_url:
            continue
        label = strip_html(str(text))
        links.append((label, full_url))
    return links


def find_candidate_url(
    links: list[tuple[str, str]], topic_keywords: tuple[str, ...]
) -> str | None:
    for text, target_url in links:
        haystack = f"{text} {target_url}".casefold()
        if any(keyword in haystack for keyword in topic_keywords):
            return target_url
    return None


def find_candidate_urls(
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


def contains_noise(text: str) -> bool:
    lowered = text.casefold()
    return any(pattern in lowered for pattern in NOISE_PATTERNS)


def is_useful_sentence(sentence: str) -> bool:
    cleaned = sentence.strip()
    if len(cleaned) < 35:
        return False
    lowered = cleaned.casefold()
    if contains_noise(lowered):
        return False
    has_words = len(re.findall(r"[a-zäöüß]{3,}", lowered)) >= 6
    return has_words


def sentence_score(sentence: str) -> int:
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


def extract_essential_sentences(text: str, *, limit: int = 4) -> list[str]:
    if not text:
        return []
    candidates = re.split(r"(?<=[.!?])\s+", text)
    scored: list[tuple[int, str]] = []
    for candidate in candidates:
        cleaned = candidate.strip().replace("•", " ").replace("·", " ")
        if not is_useful_sentence(cleaned):
            continue
        scored.append((sentence_score(cleaned), cleaned[:260]))
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


def extract_imprint_facts(raw_html: str, text: str) -> dict[str, str]:
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


def normalize_research_facts(raw_facts: Any) -> dict[str, str]:
    if isinstance(raw_facts, Mapping):
        return {
            str(key).strip(): str(value).strip()
            for key, value in raw_facts.items()
            if str(key).strip() and str(value).strip()
        }
    if not isinstance(raw_facts, list):
        return {}

    facts: dict[str, str] = {}
    for index, item in enumerate(raw_facts, start=1):
        text = str(item or "").strip()
        if not text:
            continue
        if ":" in text:
            label, value = text.split(":", 1)
            key = label.strip() or f"fact_{index}"
            normalized_value = value.strip()
        else:
            key = f"fact_{index}"
            normalized_value = text
        if not normalized_value:
            continue
        base_key = key
        suffix = 2
        while key in facts:
            key = f"{base_key}_{suffix}"
            suffix += 1
        facts[key] = normalized_value
    return facts


def normalize_company_website_research_payload(raw_research: Any) -> Any:
    if not isinstance(raw_research, Mapping):
        return raw_research

    research = dict(raw_research)
    sections_raw = research.get(WEBSITE_RESEARCH_SECTIONS)
    if not isinstance(sections_raw, Mapping):
        return research

    normalized_sections: dict[str, Any] = {}
    for topic_key, section_raw in sections_raw.items():
        if not isinstance(section_raw, Mapping):
            normalized_sections[str(topic_key)] = section_raw
            continue
        section = dict(section_raw)
        section[WEBSITE_SECTION_FACTS] = normalize_research_facts(
            section.get(WEBSITE_SECTION_FACTS, {})
        )
        normalized_sections[str(topic_key)] = section
    research[WEBSITE_RESEARCH_SECTIONS] = normalized_sections
    return research


def derive_topic_facts(topic_key: str, text: str, raw_html: str) -> dict[str, str]:
    facts: dict[str, str] = {}
    compact = re.sub(r"\s+", " ", text)
    if topic_key == WEBSITE_TOPIC_IMPRINT:
        imprint_facts = extract_imprint_facts(raw_html, compact)
        for label in (
            "Firma",
            "Anschrift",
            "E-Mail",
            "Handelsregister",
            "Geschäftsführung/Vorstand",
        ):
            value = imprint_facts.get(label)
            if value:
                facts[label] = value
        return facts

    headcount_match = re.search(
        r"(\d{2,3}(?:[.,]\d{3})+|\d{3,6})\s+(?:mitarbeitende|mitarbeiter|employees)",
        compact,
        flags=re.I,
    )
    if headcount_match:
        facts["Mitarbeitende (Hinweis)"] = headcount_match.group(1)

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
            facts[label] = matched_value.strip()
    return dict(list(facts.items())[:4])


def derive_insights_from_open_questions(
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


def build_open_question_match_options(
    matches: list[dict[str, str]],
    *,
    topic_labels: Mapping[str, str] | None = None,
) -> list[dict[str, str]]:
    options: list[dict[str, str]] = []
    seen_labels: dict[str, int] = {}
    labels = topic_labels or WEBSITE_TOPIC_LABELS
    for match in matches:
        question_id = str(match.get("question_id") or "").strip()
        question_label = str(match.get("question_label") or "").strip()
        if not question_id or not question_label:
            continue
        source_topic = str(match.get("source_topic") or "").strip()
        source_label = labels.get(source_topic, "Website")
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


def _response_content_type(response: object) -> str:
    headers = getattr(response, "headers", None)
    if headers is None:
        return ""
    content_type = ""
    get_content_type = getattr(headers, "get_content_type", None)
    if callable(get_content_type):
        content_type = str(get_content_type() or "")
    if not content_type and hasattr(headers, "get"):
        content_type = str(headers.get("Content-Type", "") or "").split(";", 1)[0]
    return content_type.strip().lower()


def _is_allowed_content_type(content_type: str) -> bool:
    if not content_type:
        return True
    return content_type.startswith(ALLOWED_CONTENT_TYPE_PREFIXES)


def _is_disallowed_hostname(hostname: str) -> bool:
    normalized = hostname.strip().strip("[]").casefold()
    if not normalized:
        return True
    if normalized in {"localhost", "0.0.0.0"} or normalized.endswith(".localhost"):
        return True
    try:
        address = ipaddress.ip_address(normalized)
    except ValueError:
        return False
    return (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )


def _log_fetch_event(
    event_name: str,
    url: str,
    *,
    cache_hit: bool,
    bytes_read: int | None = None,
) -> None:
    parsed = urlparse(url)
    LOGGER.info(
        "event=company_homepage_fetch status=%s host=%s cache_hit=%s bytes=%s",
        event_name,
        parsed.netloc,
        cache_hit,
        "" if bytes_read is None else bytes_read,
    )
