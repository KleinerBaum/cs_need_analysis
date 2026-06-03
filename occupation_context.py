"""Deterministic occupation context classification for question-flow control."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from schemas import (
    ClassificationEvidence,
    JobAdExtract,
    OccupationContextProfile,
    OccupationFamily,
    RelevanceLevel,
    WorkArrangement,
)


_FAMILY_KEYWORDS: tuple[tuple[OccupationFamily, tuple[str, ...]], ...] = (
    (
        OccupationFamily.CLINICAL_PHYSICIAN,
        (
            "arzt",
            "aerzt",
            "physician",
            "doctor",
            "medical doctor",
            "approbation",
            "patient",
            "facharzt",
            "clinic",
            "klinik",
        ),
    ),
    (
        OccupationFamily.NURSING_CARE,
        (
            "pflege",
            "nurse",
            "nursing",
            "registered nurse",
            "patientenversorgung",
            "station",
        ),
    ),
    (
        OccupationFamily.FIELD_SALES,
        (
            "sales representative",
            "aussendienst",
            "field sales",
            "vertriebsgebiet",
            "account executive",
            "key account",
            "kundenbesuch",
            "territory",
        ),
    ),
    (
        OccupationFamily.FIELD_SERVICE,
        (
            "field service",
            "servicetechniker",
            "elektriker",
            "electrician",
            "maintenance",
            "wartung",
            "installation",
            "stoerungsdienst",
        ),
    ),
    (
        OccupationFamily.TRANSPORT_LOGISTICS,
        (
            "fahrer",
            "driver",
            "truck",
            "lkw",
            "logistics",
            "logistik",
            "route",
            "touren",
            "warehouse",
        ),
    ),
    (
        OccupationFamily.CUSTOMER_SUPPORT,
        (
            "customer support",
            "customer service",
            "kundenservice",
            "support agent",
            "call center",
            "sla",
            "ticket",
            "escalation",
        ),
    ),
    (
        OccupationFamily.DIGITAL_PRODUCT,
        (
            "software",
            "developer",
            "entwickler",
            "app developer",
            "data engineer",
            "product manager",
            "devops",
            "cloud",
            "backend",
            "frontend",
            "python",
            "java",
            "sql",
        ),
    ),
    (
        OccupationFamily.EDUCATION_SOCIAL,
        (
            "teacher",
            "lehrer",
            "educator",
            "trainer",
            "social worker",
            "sozial",
            "paedagog",
        ),
    ),
    (
        OccupationFamily.INDUSTRIAL_SHIFT,
        (
            "production",
            "produktion",
            "machine operator",
            "maschinen",
            "schicht",
            "plant",
            "factory",
        ),
    ),
    (
        OccupationFamily.OFFICE_OPERATIONS,
        (
            "office",
            "administration",
            "assistenz",
            "backoffice",
            "operations",
            "sachbearbeitung",
        ),
    ),
)


def _walk_text_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        values: list[str] = []
        for item in value.values():
            values.extend(_walk_text_values(item))
        return values
    if isinstance(value, (list, tuple, set)):
        values = []
        for item in value:
            values.extend(_walk_text_values(item))
        return values
    return [str(value)]


def _normalize_blob(*values: Any) -> str:
    return " ".join(
        text.casefold().strip()
        for value in values
        for text in _walk_text_values(value)
        if text and str(text).strip()
    )


def _contains_any(blob: str, terms: tuple[str, ...]) -> bool:
    return any(term.casefold() in blob for term in terms)


def _evidence(
    source: str,
    signal: str,
    weight: float,
    rationale: str,
) -> ClassificationEvidence:
    return ClassificationEvidence(
        source=source,
        signal=signal,
        weight=weight,
        rationale=rationale,
    )


def _classify_family(
    *,
    blob: str,
    has_confirmed_esco: bool,
) -> tuple[OccupationFamily, float, list[ClassificationEvidence]]:
    evidence: list[ClassificationEvidence] = []
    for family, keywords in _FAMILY_KEYWORDS:
        matched = [keyword for keyword in keywords if keyword.casefold() in blob]
        if not matched:
            continue
        weight = 0.88 if has_confirmed_esco else 0.72
        evidence.append(
            _evidence(
                "esco_or_jobspec",
                ",".join(matched[:4]),
                weight,
                f"Matched deterministic keywords for {family.value}.",
            )
        )
        return family, weight, evidence
    evidence.append(
        _evidence(
            "generic_fallback",
            "no_family_keyword_match",
            0.2,
            "No deterministic family rule matched.",
        )
    )
    return OccupationFamily.UNKNOWN, 0.2, evidence


def _resolve_work_arrangement(job: JobAdExtract, blob: str) -> WorkArrangement:
    explicit = _normalize_blob(job.remote_policy, job.place_of_work)
    if _contains_any(explicit, ("global remote", "weltweit", "work from anywhere")):
        return WorkArrangement.REMOTE_GLOBAL_POSSIBLE
    if _contains_any(explicit, ("remote", "homeoffice", "home office")):
        return WorkArrangement.REMOTE_POSSIBLE
    if _contains_any(explicit, ("hybrid", "teilremote")):
        return WorkArrangement.HYBRID_POSSIBLE
    if _contains_any(explicit, ("vor ort", "onsite", "on-site", "praesenz")):
        return WorkArrangement.ONSITE_REQUIRED
    if _contains_any(blob, ("software", "developer", "data engineer", "devops")):
        return WorkArrangement.REMOTE_POSSIBLE
    if _contains_any(blob, ("patient", "pflege", "fahrer", "field service", "elektriker")):
        return WorkArrangement.ONSITE_REQUIRED
    return WorkArrangement.UNKNOWN


def _resolve_level(
    blob: str,
    *,
    required_terms: tuple[str, ...],
    high_terms: tuple[str, ...],
    irrelevant_terms: tuple[str, ...] = (),
) -> RelevanceLevel:
    if _contains_any(blob, required_terms):
        return RelevanceLevel.REQUIRED
    if _contains_any(blob, high_terms):
        return RelevanceLevel.HIGH
    if _contains_any(blob, irrelevant_terms):
        return RelevanceLevel.IRRELEVANT
    return RelevanceLevel.UNKNOWN


def _pack_keys_for_profile(
    *,
    family: OccupationFamily,
    work_arrangement: WorkArrangement,
    driving_relevance: RelevanceLevel,
    travel_relevance: RelevanceLevel,
    regulated_profession: bool | None,
    shift_oncall_relevance: RelevanceLevel,
) -> list[str]:
    keys = ["base.core", "base.interview"]
    if family != OccupationFamily.UNKNOWN:
        keys.append(f"family.{family.value}")
    if work_arrangement in {
        WorkArrangement.REMOTE_POSSIBLE,
        WorkArrangement.REMOTE_GLOBAL_POSSIBLE,
    }:
        keys.append("facet.remote_global_possible")
    if driving_relevance in {RelevanceLevel.REQUIRED, RelevanceLevel.HIGH}:
        keys.append("facet.driving_required")
    if travel_relevance in {RelevanceLevel.REQUIRED, RelevanceLevel.HIGH}:
        keys.append("facet.travel_high")
    if regulated_profession:
        keys.append("facet.regulated_profession")
    if shift_oncall_relevance in {RelevanceLevel.REQUIRED, RelevanceLevel.HIGH}:
        keys.append("facet.shift_oncall_high")
    return list(dict.fromkeys(keys))


def classify_occupation_context(
    *,
    job: JobAdExtract,
    esco_selected: dict[str, Any] | None = None,
    esco_payload: dict[str, Any] | None = None,
    esco_version: str | None = None,
    answers: dict[str, Any] | None = None,
) -> OccupationContextProfile:
    """Return an authoritative deterministic profile. This function never calls an LLM."""

    has_confirmed_esco = bool((esco_selected or {}).get("uri"))
    blob = _normalize_blob(
        job.model_dump(mode="json"),
        esco_selected or {},
        esco_payload or {},
        answers or {},
    )
    family, confidence, evidence = _classify_family(
        blob=blob,
        has_confirmed_esco=has_confirmed_esco,
    )

    work_arrangement = _resolve_work_arrangement(job, blob)
    driving_relevance = _resolve_level(
        blob,
        required_terms=("fuehrerschein", "driver license", "driving license", "lkw", "cdl"),
        high_terms=("dienstwagen", "vehicle", "fahrzeug", "kundenbesuch", "route"),
    )
    travel_relevance = _resolve_level(
        blob,
        required_terms=("reisebereitschaft", "travel required", "aussendienst"),
        high_terms=("travel", "reisen", "kundenbesuch", "gebiet", "territory"),
    )
    shift_oncall_relevance = _resolve_level(
        blob,
        required_terms=("rufbereitschaft", "on-call", "notdienst"),
        high_terms=("schicht", "shift", "nachtschicht", "weekend"),
    )
    customer_contact_relevance = _resolve_level(
        blob,
        required_terms=("patient", "kundenbesuch", "customer-facing"),
        high_terms=("kunde", "customer", "support", "sales", "service"),
    )
    language_locality_relevance = _resolve_level(
        blob,
        required_terms=("deutsch", "german", "approbation", "patient"),
        high_terms=("language", "sprache", "kundenkontakt"),
    )
    regulated_profession = (
        True
        if _contains_any(
            blob,
            (
                "approbation",
                "lizenz",
                "license",
                "certification required",
                "zertifikat",
                "sicherheits",
                "gefahrgut",
            ),
        )
        else None
    )

    if family in {
        OccupationFamily.CLINICAL_PHYSICIAN,
        OccupationFamily.NURSING_CARE,
        OccupationFamily.FIELD_SERVICE,
        OccupationFamily.TRANSPORT_LOGISTICS,
    }:
        if work_arrangement == WorkArrangement.UNKNOWN:
            work_arrangement = WorkArrangement.ONSITE_REQUIRED
    if family == OccupationFamily.DIGITAL_PRODUCT and driving_relevance == RelevanceLevel.UNKNOWN:
        driving_relevance = RelevanceLevel.IRRELEVANT
    if family in {OccupationFamily.FIELD_SALES, OccupationFamily.TRANSPORT_LOGISTICS}:
        if driving_relevance == RelevanceLevel.UNKNOWN:
            driving_relevance = RelevanceLevel.HIGH
        if travel_relevance == RelevanceLevel.UNKNOWN:
            travel_relevance = RelevanceLevel.HIGH
    if family in {OccupationFamily.CLINICAL_PHYSICIAN, OccupationFamily.NURSING_CARE}:
        regulated_profession = True
        if shift_oncall_relevance == RelevanceLevel.UNKNOWN:
            shift_oncall_relevance = RelevanceLevel.HIGH
        if customer_contact_relevance == RelevanceLevel.UNKNOWN:
            customer_contact_relevance = RelevanceLevel.REQUIRED
        if language_locality_relevance == RelevanceLevel.UNKNOWN:
            language_locality_relevance = RelevanceLevel.HIGH

    pack_keys = _pack_keys_for_profile(
        family=family,
        work_arrangement=work_arrangement,
        driving_relevance=driving_relevance,
        travel_relevance=travel_relevance,
        regulated_profession=regulated_profession,
        shift_oncall_relevance=shift_oncall_relevance,
    )
    authority_source = (
        "user_confirmed_esco"
        if has_confirmed_esco
        else "deterministic_rules"
        if family != OccupationFamily.UNKNOWN
        else "generic_fallback"
    )
    evidence.append(
        _evidence(
            "question_pack_selector",
            ",".join(pack_keys),
            min(1.0, confidence),
            "Selected deterministic question packs from family and facet rules.",
        )
    )

    return OccupationContextProfile(
        esco_version=esco_version,
        occupation_family=family,
        confidence=confidence,
        work_arrangement=work_arrangement,
        driving_relevance=driving_relevance,
        travel_relevance=travel_relevance,
        regulated_profession=regulated_profession,
        shift_oncall_relevance=shift_oncall_relevance,
        customer_contact_relevance=customer_contact_relevance,
        language_locality_relevance=language_locality_relevance,
        authority_source=authority_source,
        pack_keys=pack_keys,
        evidence=evidence,
    )


def profile_fingerprint(profile: OccupationContextProfile) -> str:
    payload = json.dumps(
        profile.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
