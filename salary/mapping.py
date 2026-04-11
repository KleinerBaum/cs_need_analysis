"""Deterministic salary mapping helpers (pure domain module)."""

from __future__ import annotations

import re
import unicodedata

from salary.types import SalaryEscoContext

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")

_COUNTRY_ALIASES: dict[str, str] = {
    "de": "DE",
    "deutschland": "DE",
    "germany": "DE",
    "deu": "DE",
    "ch": "CH",
    "schweiz": "CH",
    "switzerland": "CH",
    "usa": "US",
    "us": "US",
    "united states": "US",
    "vereinigte staaten": "US",
}

_DE_CITY_TO_REGION_ID: dict[str, str] = {
    "berlin": "DE-BE",
    "munchen": "DE-BY",
    "muenchen": "DE-BY",
    "nurnberg": "DE-BY",
    "nuernberg": "DE-BY",
    "augsburg": "DE-BY",
    "hamburg": "DE-HH",
    "bremen": "DE-HB",
    "hannover": "DE-NI",
    "dusseldorf": "DE-NW",
    "duesseldorf": "DE-NW",
    "koln": "DE-NW",
    "koeln": "DE-NW",
    "dortmund": "DE-NW",
    "essen": "DE-NW",
    "frankfurt": "DE-HE",
    "wiesbaden": "DE-HE",
    "stuttgart": "DE-BW",
    "karlsruhe": "DE-BW",
    "mannheim": "DE-BW",
    "freiburg": "DE-BW",
    "mainz": "DE-RP",
    "saarbrucken": "DE-SL",
    "saarbruecken": "DE-SL",
    "dresden": "DE-SN",
    "leipzig": "DE-SN",
    "magdeburg": "DE-ST",
    "erfurt": "DE-TH",
    "potsdam": "DE-BB",
    "schwerin": "DE-MV",
    "kiel": "DE-SH",
}


def normalize_token(s: str) -> str:
    """Return a stable, case-insensitive token suitable for deterministic mapping."""

    if not s:
        return ""
    normalized = unicodedata.normalize("NFKD", s)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    compact = _NON_ALNUM_RE.sub(" ", ascii_text.lower()).strip()
    return re.sub(r"\s+", " ", compact)


def infer_region_id(country: str | None, city: str | None) -> str:
    """Infer a deterministic region id from country + city.

    Germany uses a seeded mapping to Bundesland ids (e.g., ``DE-BE``).
    Unknown German cities fall back to ``DE``.
    """

    normalized_country = normalize_token(country or "")
    country_id = _COUNTRY_ALIASES.get(normalized_country)
    if country_id is None and normalized_country:
        country_id = normalized_country.upper()

    if country_id == "DE":
        normalized_city = normalize_token(city or "")
        if normalized_city:
            mapped = _DE_CITY_TO_REGION_ID.get(normalized_city)
            if mapped is not None:
                return mapped
        return "DE"

    if country_id:
        return country_id
    return "DE"


def infer_occupation_id(
    esco_context: SalaryEscoContext | None, job_title: str | None
) -> str:
    """Infer deterministic occupation mapping id.

    Preferred mapping is the ESCO URI, then normalized job title.
    """

    occupation_uri = (esco_context.occupation_uri if esco_context else None) or ""
    if occupation_uri.strip():
        return f"esco::{occupation_uri.strip()}"

    normalized_title = normalize_token(job_title or "")
    if not normalized_title:
        return "title::unknown"
    return f"title::{normalized_title}"
