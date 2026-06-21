"""Guarded homepage fetch and extraction helpers for company enrichment."""

from __future__ import annotations

import html
import ipaddress
import logging
import re
import socket
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha1
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from constants import (
    INTAKE_FACTS,
    FactKey,
    FactValueType,
    WEBSITE_RESEARCH_HOMEPAGE_URL,
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
HOMEPAGE_FETCH_MAX_REDIRECTS = 3
USER_AGENT = "cs-need-analysis/1.0 (+https://example.invalid)"
ALLOWED_CONTENT_TYPE_PREFIXES: tuple[str, ...] = (
    "text/html",
    "text/plain",
    "application/xhtml+xml",
)
REDIRECT_STATUS_CODES = frozenset({301, 302, 303, 307, 308})
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
_FACT_DEFS_BY_KEY = {fact.fact_key: fact for fact in INTAKE_FACTS}
_POSITIONING_TERMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Marktposition", ("führend", "leader", "marktführer", "market leader")),
    ("Produkt", ("produkt", "platform", "plattform", "lösung", "solution")),
    ("Wachstum", ("wachstum", "growth", "skalier", "expand")),
    ("Stabilität", ("gegründet", "seit ", "weltweit", "global", "employees")),
    ("Technologie", ("technolog", "cloud", "software", "digital", "ki", " ai ")),
    ("Mission", ("mission", "vision", "purpose", "leitbild", "werte")),
    ("Kundennutzen", ("kund", "client", "customer", "nutzen")),
)
_COMPLIANCE_TERMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Regulierte Branche", ("reguliert", "regulated", "bank", "finance", "healthcare")),
    ("Datenschutz", ("datenschutz", "privacy", "gdpr", "dsgvo")),
    ("Arbeitssicherheit", ("arbeitssicherheit", "occupational safety")),
    ("Zertifizierungen", ("zertifiz", "certified", "iso ")),
    ("Betriebsrat", ("betriebsrat", "works council")),
    ("Öffentlicher Sektor", ("public sector", "öffentlicher sektor", "government")),
)
_TECH_TERMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("AI", (" künstliche intelligenz", " artificial intelligence", " ai ", " ki ")),
    ("Cloud", (" cloud",)),
    ("Data", (" data", "daten", "analytics")),
    ("SAP", (" sap",)),
    ("Salesforce", ("salesforce",)),
    ("AWS", (" aws", "amazon web services")),
    ("Azure", (" azure", "microsoft cloud")),
    ("Python", (" python",)),
    ("Java", (" java",)),
    ("Kubernetes", ("kubernetes", " k8s")),
)
_DOMAIN_TERMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Consulting", ("beratung", "consulting")),
    ("Automotive", ("automotive", "mobilität", "mobility")),
    ("Financial Services", ("financial services", "bank", "versicherung", "insurance")),
    ("Healthcare", ("healthcare", "gesundheit", "pharma")),
    ("Public Sector", ("public sector", "öffentlicher sektor", "government")),
    ("Retail", ("retail", "handel", "e-commerce")),
    ("Energy", ("energie", "energy", "utilities")),
    ("Telecommunications", ("telekommunikation", "telecommunications", "telco")),
)
_BENEFIT_TERMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Homeoffice", ("homeoffice", "remote work", "mobiles arbeiten")),
    ("Flexible Arbeitszeiten", ("flexible arbeitszeiten", "flexitime")),
    ("Weiterbildung", ("weiterbildung", "learning", "training", "development")),
    ("Betriebliche Altersvorsorge", ("altersvorsorge", "pension")),
    ("Gesundheitsangebote", ("gesundheit", "health benefit", "wellbeing")),
    ("Jobticket", ("jobticket", "public transport")),
    ("Urlaub", ("urlaub", "vacation", "annual leave")),
)
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


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, *_args: object, **_kwargs: object) -> None:
        return None


_NO_REDIRECT_OPENER = build_opener(_NoRedirectHandler)


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
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    if not _has_supported_port(parsed):
        return ""
    if _is_disallowed_hostname(parsed.hostname or ""):
        return ""
    return urlunparse(
        (
            scheme,
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
    normalized_url = _validate_public_target(
        url,
        error_code="invalid_or_disallowed_url",
    )

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

    final_url, response = _open_validated_response(normalized_url, timeout_sec)
    with response:
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


def build_website_fact_candidates(raw_research: Any) -> list[dict[str, Any]]:
    """Build deterministic, type-compatible FactKey candidates from website research."""

    normalized_research = normalize_company_website_research_payload(raw_research)
    if not isinstance(normalized_research, Mapping):
        return []

    sections_raw = normalized_research.get(WEBSITE_RESEARCH_SECTIONS, {})
    sections = sections_raw if isinstance(sections_raw, Mapping) else {}
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    homepage_url = normalize_url(
        str(normalized_research.get(WEBSITE_RESEARCH_HOMEPAGE_URL) or "")
    )
    if homepage_url:
        _append_fact_candidate(
            candidates,
            seen,
            fact_key=FactKey.COMPANY_COMPANY_WEBSITE,
            value=homepage_url,
            source_topic="homepage",
            evidence_snippet=homepage_url,
            confidence=0.9,
        )

    section_texts = _collect_section_texts(sections)
    all_text = " ".join(section_texts.values())
    lowered_all_text = f" {all_text.casefold()} "

    imprint_section = sections.get(WEBSITE_TOPIC_IMPRINT)
    imprint_facts = _section_facts(imprint_section)
    company_name = imprint_facts.get("Firma")
    if company_name:
        _append_fact_candidate(
            candidates,
            seen,
            fact_key=FactKey.COMPANY_COMPANY_NAME,
            value=company_name,
            source_topic=WEBSITE_TOPIC_IMPRINT,
            evidence_snippet=f"Firma: {company_name}",
            confidence=0.85,
        )
    address = imprint_facts.get("Anschrift")
    city = _extract_city_from_address(address)
    if city:
        _append_fact_candidate(
            candidates,
            seen,
            fact_key=FactKey.COMPANY_LOCATION_CITY,
            value=city,
            source_topic=WEBSITE_TOPIC_IMPRINT,
            evidence_snippet=f"Anschrift: {address}",
            confidence=0.75,
        )
    if _contains_any(lowered_all_text, (" deutschland ", " germany ", ".de ")):
        _append_fact_candidate(
            candidates,
            seen,
            fact_key=FactKey.COMPANY_LOCATION_COUNTRY,
            value="Deutschland",
            source_topic=WEBSITE_TOPIC_IMPRINT if address else "homepage",
            evidence_snippet=address or homepage_url,
            confidence=0.65,
        )

    for topic_key in (WEBSITE_TOPIC_ABOUT, WEBSITE_TOPIC_VISION_MISSION):
        summary = _section_summary(sections.get(topic_key))
        if not summary:
            continue
        _append_fact_candidate(
            candidates,
            seen,
            fact_key=FactKey.COMPANY_EMPLOYER_PITCH,
            value=summary[0],
            source_topic=topic_key,
            evidence_snippet=summary[0],
            confidence=0.7,
        )

    positioning = _match_terms(lowered_all_text, _POSITIONING_TERMS)
    if positioning:
        _append_fact_candidate(
            candidates,
            seen,
            fact_key=FactKey.COMPANY_ROLE_RELEVANT_POSITIONING,
            value=positioning,
            source_topic=_best_source_topic(section_texts, _POSITIONING_TERMS),
            evidence_snippet=_first_evidence_sentence(sections, positioning),
            confidence=0.65,
        )

    compliance = _match_terms(lowered_all_text, _COMPLIANCE_TERMS)
    if compliance:
        _append_fact_candidate(
            candidates,
            seen,
            fact_key=FactKey.COMPANY_COMPLIANCE_CONTEXT,
            value=compliance,
            source_topic=_best_source_topic(section_texts, _COMPLIANCE_TERMS),
            evidence_snippet=_first_evidence_sentence(sections, compliance),
            confidence=0.65,
        )

    work_arrangement = _derive_work_arrangement(lowered_all_text)
    if work_arrangement:
        _append_fact_candidate(
            candidates,
            seen,
            fact_key=FactKey.COMPANY_WORK_ARRANGEMENT,
            value=work_arrangement,
            source_topic="homepage",
            evidence_snippet=_first_evidence_sentence(
                sections, ("hybrid", "remote", "homeoffice", "vor ort")
            ),
            confidence=0.7,
        )

    office_days = _derive_office_days(all_text)
    if office_days is not None:
        _append_fact_candidate(
            candidates,
            seen,
            fact_key=FactKey.COMPANY_OFFICE_DAYS_PER_WEEK,
            value=office_days,
            source_topic="homepage",
            evidence_snippet=_first_evidence_sentence(sections, (str(office_days),)),
            confidence=0.75,
        )

    allowed_regions = _derive_allowed_regions(lowered_all_text)
    if allowed_regions:
        _append_fact_candidate(
            candidates,
            seen,
            fact_key=FactKey.COMPANY_ALLOWED_REGIONS_TIMEZONES,
            value=allowed_regions,
            source_topic="homepage",
            evidence_snippet=_first_evidence_sentence(sections, allowed_regions),
            confidence=0.65,
        )

    language_object = _derive_language_object(lowered_all_text)
    if language_object:
        _append_fact_candidate(
            candidates,
            seen,
            fact_key=FactKey.COMPANY_LANGUAGE_INTERNAL,
            value=language_object,
            source_topic="homepage",
            evidence_snippet=_first_evidence_sentence(
                sections, ("sprache", "language", "deutsch", "english", "englisch")
            ),
            confidence=0.65,
        )

    tech_stack = _match_terms(lowered_all_text, _TECH_TERMS)
    if tech_stack:
        _append_fact_candidate(
            candidates,
            seen,
            fact_key=FactKey.ROLE_TECH_STACK,
            value=tech_stack,
            source_topic=_best_source_topic(section_texts, _TECH_TERMS),
            evidence_snippet=_first_evidence_sentence(sections, tech_stack),
            confidence=0.6,
        )

    domain_expertise = _match_terms(lowered_all_text, _DOMAIN_TERMS)
    if domain_expertise:
        _append_fact_candidate(
            candidates,
            seen,
            fact_key=FactKey.ROLE_DOMAIN_EXPERTISE,
            value=domain_expertise,
            source_topic=_best_source_topic(section_texts, _DOMAIN_TERMS),
            evidence_snippet=_first_evidence_sentence(sections, domain_expertise),
            confidence=0.6,
        )

    benefits = _match_terms(lowered_all_text, _BENEFIT_TERMS)
    if benefits:
        _append_fact_candidate(
            candidates,
            seen,
            fact_key=FactKey.BENEFITS_BENEFITS,
            value=benefits,
            source_topic=_best_source_topic(section_texts, _BENEFIT_TERMS),
            evidence_snippet=_first_evidence_sentence(sections, benefits),
            confidence=0.6,
        )

    return candidates


def _append_fact_candidate(
    candidates: list[dict[str, Any]],
    seen: set[tuple[str, str, str]],
    *,
    fact_key: FactKey,
    value: Any,
    source_topic: str,
    evidence_snippet: str | None,
    confidence: float,
) -> None:
    fact_def = _FACT_DEFS_BY_KEY.get(fact_key)
    if fact_def is None:
        return
    normalized_value = _normalize_candidate_value(value, fact_def.value_type)
    if normalized_value is None:
        return
    source_topic = str(source_topic or "homepage").strip() or "homepage"
    identity = (fact_key.value, source_topic, repr(normalized_value))
    if identity in seen:
        return
    seen.add(identity)
    candidate_hash = sha1("|".join(identity).encode("utf-8")).hexdigest()[:12]
    candidates.append(
        {
            "candidate_id": f"{fact_key.value}:{source_topic}:{candidate_hash}",
            "fact_key": fact_key.value,
            "fact_label": fact_def.label,
            "value_type": fact_def.value_type.value,
            "value": normalized_value,
            "source_topic": source_topic,
            "source_label": _source_label(source_topic),
            "evidence_snippet": _compact_text(evidence_snippet),
            "confidence": max(0.0, min(1.0, float(confidence))),
        }
    )


def _normalize_candidate_value(value: Any, value_type: FactValueType) -> Any | None:
    if value_type in {FactValueType.STRING, FactValueType.DATE_STRING}:
        return _compact_text(value)
    if value_type == FactValueType.STRING_LIST:
        return _normalize_string_list(value)
    if value_type == FactValueType.INTEGER:
        return _normalize_integer(value)
    if value_type == FactValueType.BOOLEAN:
        return _normalize_boolean(value)
    if value_type in {FactValueType.OBJECT, FactValueType.MONEY_RANGE}:
        return _normalize_object(value)
    if value_type == FactValueType.OBJECT_LIST:
        return _normalize_object_list(value)
    return None


def _normalize_string_list(value: Any) -> list[str] | None:
    raw_items = (
        value
        if isinstance(value, list)
        else str(value or "").replace(";", "\n").replace(",", "\n").splitlines()
    )
    output: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        text = _compact_text(item)
        key = text.casefold() if text else ""
        if not text or key in seen:
            continue
        seen.add(key)
        output.append(text)
    return output or None


def _normalize_integer(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    match = re.search(r"\d+", str(value or "").replace(".", "").replace(",", ""))
    return int(match.group(0)) if match else None


def _normalize_boolean(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    lowered = str(value or "").strip().casefold()
    if lowered in {"true", "yes", "ja", "1"}:
        return True
    if lowered in {"false", "no", "nein", "0"}:
        return False
    return None


def _normalize_object(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    cleaned = {
        str(key): item
        for key, item in value.items()
        if _compact_text(item) or isinstance(item, (bool, int, float))
    }
    return cleaned or None


def _normalize_object_list(value: Any) -> list[dict[str, Any]] | None:
    if not isinstance(value, list):
        return None
    output = [
        item
        for item in (_normalize_object(raw_item) for raw_item in value)
        if item is not None
    ]
    return output or None


def _collect_section_texts(sections: Mapping[Any, Any]) -> dict[str, str]:
    output: dict[str, str] = {}
    for topic_key, section in sections.items():
        if not isinstance(section, Mapping):
            continue
        summary_text = " ".join(_section_summary(section))
        fact_text = " ".join(
            f"{label}: {value}" for label, value in _section_facts(section).items()
        )
        output[str(topic_key)] = f"{summary_text} {fact_text}".strip()
    return output


def _section_summary(section: Any) -> list[str]:
    if not isinstance(section, Mapping):
        return []
    summary = section.get(WEBSITE_SECTION_SUMMARY, [])
    if not isinstance(summary, list):
        return []
    return [_compact_text(item) for item in summary if _compact_text(item)]


def _section_facts(section: Any) -> dict[str, str]:
    if not isinstance(section, Mapping):
        return {}
    return normalize_research_facts(section.get(WEBSITE_SECTION_FACTS, {}))


def _extract_city_from_address(address: str | None) -> str | None:
    if not address:
        return None
    match = re.search(r"\b\d{4,5}\s+([A-ZÄÖÜ][\wÄÖÜäöüß .-]{2,40})", address)
    if not match:
        return None
    return _compact_text(match.group(1).split(",", 1)[0])


def _derive_work_arrangement(lowered_text: str) -> str | None:
    if _contains_any(lowered_text, (" hybrid", "hybrides", "hybrid work")):
        return "hybrid"
    if _contains_any(lowered_text, (" remote", "homeoffice", "mobiles arbeiten")):
        return "remote_country"
    if _contains_any(lowered_text, (" vor ort", "onsite", "on-site")):
        return "onsite"
    return None


def _derive_office_days(text: str) -> int | None:
    match = re.search(
        r"(\d)\s*(?:tage|days)\s*(?:pro|per)?\s*(?:woche|week)?.{0,30}(?:büro|office|vor ort|onsite)",
        text,
        flags=re.I,
    )
    if not match:
        return None
    return max(0, min(5, int(match.group(1))))


def _derive_allowed_regions(lowered_text: str) -> list[str] | None:
    regions: list[str] = []
    for label, tokens in (
        ("Deutschland", (" deutschland ", " germany ")),
        ("DACH", (" dach ",)),
        ("EU", (" eu ", " european union ", " europäische union ")),
        ("CET", (" cet ", " mez ")),
    ):
        if _contains_any(lowered_text, tokens):
            regions.append(label)
    return regions or None


def _derive_language_object(lowered_text: str) -> dict[str, str] | None:
    if not _contains_any(lowered_text, ("sprache", "language", "sprachen")):
        return None
    languages: list[str] = []
    if _contains_any(lowered_text, (" deutsch", " german")):
        languages.append("Deutsch")
    if _contains_any(lowered_text, (" englisch", " english")):
        languages.append("Englisch")
    if not languages:
        return None
    return {
        "language": ", ".join(languages),
        "level": "B2",
        "context": "Website-Hinweis",
    }


def _match_terms(
    lowered_text: str, term_groups: tuple[tuple[str, tuple[str, ...]], ...]
) -> list[str] | None:
    matches = [
        label for label, tokens in term_groups if _contains_any(lowered_text, tokens)
    ]
    return matches or None


def _best_source_topic(
    section_texts: Mapping[str, str],
    term_groups: tuple[tuple[str, tuple[str, ...]], ...],
) -> str:
    for topic_key, text in section_texts.items():
        lowered = f" {text.casefold()} "
        if any(_contains_any(lowered, tokens) for _, tokens in term_groups):
            return topic_key
    return "homepage"


def _first_evidence_sentence(
    sections: Mapping[Any, Any], needles: Any
) -> str | None:
    raw_needles = needles if isinstance(needles, (list, tuple, set)) else [needles]
    normalized_needles = [
        str(needle).casefold()
        for needle in raw_needles
        if str(needle or "").strip()
    ]
    for section in sections.values():
        for sentence in _section_summary(section):
            lowered = sentence.casefold()
            if any(needle in lowered for needle in normalized_needles):
                return sentence
    return None


def _contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    return any(token in text for token in tokens)


def _source_label(source_topic: str) -> str:
    if source_topic == "homepage":
        return "Homepage"
    return WEBSITE_TOPIC_LABELS.get(source_topic, "Website")


def _compact_text(value: Any) -> str | None:
    text = " ".join(str(value or "").split()).strip()
    return text or None


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


def _open_validated_response(
    initial_url: str,
    timeout_sec: float,
) -> tuple[str, Any]:
    current_url = initial_url
    for redirect_count in range(HOMEPAGE_FETCH_MAX_REDIRECTS + 1):
        current_url = _validate_public_target(
            current_url,
            error_code=(
                "invalid_or_disallowed_url"
                if redirect_count == 0
                else "invalid_or_disallowed_redirect"
            ),
        )
        request = Request(current_url, headers={"User-Agent": USER_AGENT})
        _log_fetch_event("request", current_url, cache_hit=False)
        try:
            response = _open_url(request, timeout_sec)
        except HTTPError as exc:
            if not _is_redirect_status(exc.code):
                raise
            try:
                if redirect_count >= HOMEPAGE_FETCH_MAX_REDIRECTS:
                    raise HomepageFetchError("too_many_redirects") from exc
                current_url = _validated_redirect_target(current_url, exc)
            finally:
                _close_response(exc)
            continue

        status_code = _response_status_code(response)
        if _is_redirect_status(status_code):
            try:
                if redirect_count >= HOMEPAGE_FETCH_MAX_REDIRECTS:
                    raise HomepageFetchError("too_many_redirects")
                current_url = _validated_redirect_target(current_url, response)
            finally:
                _close_response(response)
            continue

        try:
            final_url = _validate_public_target(
                _response_url(response) or current_url,
                error_code="invalid_or_disallowed_redirect",
            )
        except HomepageFetchError:
            _close_response(response)
            raise
        return final_url, response

    raise HomepageFetchError("too_many_redirects")


def _open_url(request: Request, timeout_sec: float) -> Any:
    return _NO_REDIRECT_OPENER.open(request, timeout=timeout_sec)


def _validate_public_target(raw_url: str, *, error_code: str) -> str:
    normalized = normalize_url(raw_url)
    if not normalized:
        raise HomepageFetchError(error_code)
    parsed = urlparse(normalized)
    hostname = parsed.hostname or ""
    if not _hostname_resolves_public(hostname):
        raise HomepageFetchError(error_code)
    return normalized


def _validated_redirect_target(current_url: str, response: object) -> str:
    location = _response_header(response, "Location") or _response_header(
        response, "URI"
    )
    if not location:
        raise HomepageFetchError("invalid_or_disallowed_redirect")
    return _validate_public_target(
        urljoin(current_url, location),
        error_code="invalid_or_disallowed_redirect",
    )


def _response_url(response: object) -> str:
    geturl = getattr(response, "geturl", None)
    if not callable(geturl):
        return ""
    return str(geturl() or "").strip()


def _response_status_code(response: object) -> int | None:
    getcode = getattr(response, "getcode", None)
    value = getcode() if callable(getcode) else None
    if value is None:
        value = getattr(response, "status", None)
    if value is None:
        value = getattr(response, "code", None)
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _is_redirect_status(status_code: int | None) -> bool:
    return status_code in REDIRECT_STATUS_CODES


def _response_header(response: object, name: str) -> str:
    headers = getattr(response, "headers", None)
    if headers is None:
        info = getattr(response, "info", None)
        headers = info() if callable(info) else None
    if headers is None:
        return ""
    get = getattr(headers, "get", None)
    if not callable(get):
        return ""
    return str(get(name, "") or "").strip()


def _close_response(response: object) -> None:
    close = getattr(response, "close", None)
    if callable(close):
        close()


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


def _has_supported_port(parsed: Any) -> bool:
    try:
        port = parsed.port
    except ValueError:
        return False
    if port is None:
        return True
    scheme = str(parsed.scheme or "").lower()
    return (scheme == "http" and port == 80) or (scheme == "https" and port == 443)


def _hostname_resolves_public(hostname: str) -> bool:
    normalized = hostname.strip().strip("[]")
    if _is_disallowed_hostname(normalized):
        return False
    try:
        infos = socket.getaddrinfo(normalized, None, type=socket.SOCK_STREAM)
    except OSError:
        return False

    addresses: set[ipaddress.IPv4Address | ipaddress.IPv6Address] = set()
    for info in infos:
        sockaddr = info[4] if len(info) > 4 else ()
        if not sockaddr:
            continue
        raw_address = str(sockaddr[0]).split("%", 1)[0]
        try:
            addresses.add(ipaddress.ip_address(raw_address))
        except ValueError:
            return False
    return bool(addresses) and all(
        _is_public_ip_address(address) for address in addresses
    )


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
    return not _is_public_ip_address(address)


def _is_public_ip_address(
    address: ipaddress.IPv4Address | ipaddress.IPv6Address,
) -> bool:
    return (
        address.is_global
        and not address.is_private
        and not address.is_loopback
        and not address.is_link_local
        and not address.is_multicast
        and not address.is_reserved
        and not address.is_unspecified
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
        parsed.hostname or "",
        cache_hit,
        "" if bytes_read is None else bytes_read,
    )
