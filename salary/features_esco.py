"""Pure ESCO-to-salary feature adapter utilities."""

from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

from salary.types import SalaryEscoContext


def normalize_esco_uri(uri: str) -> str:
    """Return a stable canonical ESCO URI representation."""

    raw_uri = str(uri or "").strip()
    if not raw_uri:
        return ""

    parsed = urlsplit(raw_uri)
    if not parsed.scheme or not parsed.netloc:
        return raw_uri

    normalized_path = parsed.path.rstrip("/")
    if not normalized_path:
        normalized_path = "/"

    return urlunsplit(
        (
            parsed.scheme.casefold(),
            parsed.netloc.casefold(),
            normalized_path,
            "",
            "",
        )
    )


def extract_esco_context(
    *,
    occupation_selected: dict | None,
    skills_must: list[dict],
    skills_nice: list[dict],
    esco_config: dict | None,
) -> SalaryEscoContext:
    """Build strict salary ESCO context from session-state shaped payloads."""

    occupation_uri = _extract_uri_from_payload(occupation_selected)
    must_uris = _extract_uris_from_payloads(skills_must)
    nice_uris = _extract_uris_from_payloads(skills_nice)

    selected_version = ""
    if isinstance(esco_config, dict):
        selected_version = str(esco_config.get("selected_version") or "").strip()

    return SalaryEscoContext(
        occupation_uri=occupation_uri or None,
        skill_uris_must=must_uris,
        skill_uris_nice=nice_uris,
        esco_version=selected_version or None,
    )


def compute_esco_skill_coverage_signals(esco_context: SalaryEscoContext) -> list[str]:
    """Derive stable feature signals for salary quality/provenance logic."""

    version = (esco_context.esco_version or "").strip() or "none"
    return [
        f"esco_occupation_present={str(bool(esco_context.occupation_uri)).lower()}",
        f"esco_skills_must_count={len(esco_context.skill_uris_must)}",
        f"esco_skills_nice_count={len(esco_context.skill_uris_nice)}",
        f"esco_version={version}",
    ]


def _extract_uri_from_payload(payload: dict | None) -> str:
    if not isinstance(payload, dict):
        return ""
    return normalize_esco_uri(str(payload.get("uri") or ""))


def _extract_uris_from_payloads(payloads: list[dict]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()

    for item in payloads:
        if not isinstance(item, dict):
            continue
        uri = normalize_esco_uri(str(item.get("uri") or ""))
        if not uri or uri in seen:
            continue
        deduped.append(uri)
        seen.add(uri)

    return deduped
