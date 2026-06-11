"""Deterministic occupation context classification for question-flow control."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

from constants import (
    DEFAULT_LANGUAGE,
    ESCO_QUESTION_SKILL_GROUP_CUSTOMER_CLIENT_INTERACTION,
    ESCO_QUESTION_SKILL_GROUP_DIGITAL_DATA_AI,
    ESCO_QUESTION_SKILL_GROUP_DOCUMENTATION_REPORTING,
    ESCO_QUESTION_SKILL_GROUP_DOMAIN_KNOWLEDGE,
    ESCO_QUESTION_SKILL_GROUP_IDS,
    ESCO_QUESTION_SKILL_GROUP_LANGUAGE_COMMUNICATION,
    ESCO_QUESTION_SKILL_GROUP_LEADERSHIP_COORDINATION,
    ESCO_QUESTION_SKILL_GROUP_PHYSICAL_MANUAL_CONTEXT,
    ESCO_QUESTION_SKILL_GROUP_REGULATION_SAFETY,
    ESCO_QUESTION_SKILL_GROUP_TOOLS_METHODS,
    ESCO_QUESTION_SKILL_GROUP_TRANSVERSAL_FIT,
    OCCUPATION_QUESTION_MODULE_BASE,
    OCCUPATION_QUESTION_MODULE_ESCO_PREFIX,
    OCCUPATION_QUESTION_MODULE_ISCO1_PREFIX,
    OCCUPATION_QUESTION_MODULE_ISCO3_PREFIX,
    OCCUPATION_QUESTION_MODULE_ISCO4_PREFIX,
    OCCUPATION_QUESTION_MODULE_NACE_PREFIX,
    OCCUPATION_QUESTION_MODULE_REGULATED,
    OCCUPATION_QUESTION_MODULE_SKILL_GROUP_PREFIX,
)
from schemas import (
    ClassificationEvidence,
    JobAdExtract,
    OccupationContextProfile,
    OccupationFamily,
    OccupationQuestionConcept,
    OccupationQuestionContext,
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


def _dedupe_strings(values: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = " ".join(str(value or "").strip().split())
        key = normalized.casefold()
        if not normalized or key in seen:
            continue
        output.append(normalized)
        seen.add(key)
    return output


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value).strip()
    if isinstance(value, Mapping):
        for key in ("de", "en", "title", "label", "preferredLabel", "name", "value"):
            if key in value:
                resolved = _coerce_text(value.get(key))
                if resolved:
                    return resolved
        for candidate in value.values():
            resolved = _coerce_text(candidate)
            if resolved:
                return resolved
    if isinstance(value, (list, tuple, set)):
        for candidate in value:
            resolved = _coerce_text(candidate)
            if resolved:
                return resolved
    return str(value).strip()


def _coerce_text_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, Mapping):
        values: list[str] = []
        for candidate in value.values():
            values.extend(_coerce_text_list(candidate))
        return _dedupe_strings(values)
    if isinstance(value, (list, tuple, set)):
        values = []
        for candidate in value:
            values.extend(_coerce_text_list(candidate))
        return _dedupe_strings(values)
    text = str(value).strip()
    return [text] if text else []


def _first_field(source: Mapping[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = _coerce_text(source.get(key))
        if value:
            return value
    return ""


def _list_field(source: Mapping[str, Any], keys: tuple[str, ...]) -> list[str]:
    values: list[str] = []
    for key in keys:
        values.extend(_coerce_text_list(source.get(key)))
    return _dedupe_strings(values)


def _normalize_isco_code(value: Any) -> str:
    text = _coerce_text(value)
    if not text:
        return ""
    digits = "".join(re.findall(r"\d", text))
    if len(digits) >= 4:
        return digits[:4]
    return digits


def _isco_path(isco_code: str) -> list[str]:
    code = _normalize_isco_code(isco_code)
    if not code:
        return []
    return [code[:length] for length in (1, 2, 3, 4) if len(code) >= length]


def _capability_field(capability_snapshot: Any, field_name: str) -> str:
    if isinstance(capability_snapshot, Mapping):
        return str(capability_snapshot.get(field_name) or "").strip()
    return str(getattr(capability_snapshot, field_name, "") or "").strip()


_SKILL_GROUP_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        ESCO_QUESTION_SKILL_GROUP_DOMAIN_KNOWLEDGE,
        ("knowledge", "fachwissen", "domain", "theorie", "law", "legal", "methodology"),
    ),
    (
        ESCO_QUESTION_SKILL_GROUP_TOOLS_METHODS,
        ("tool", "software", "system", "method", "verfahren", "equipment", "machine"),
    ),
    (
        ESCO_QUESTION_SKILL_GROUP_REGULATION_SAFETY,
        ("regulation", "safety", "security", "compliance", "license", "zertifikat"),
    ),
    (
        ESCO_QUESTION_SKILL_GROUP_CUSTOMER_CLIENT_INTERACTION,
        ("customer", "client", "stakeholder", "patient", "beratung", "service"),
    ),
    (
        ESCO_QUESTION_SKILL_GROUP_DOCUMENTATION_REPORTING,
        ("document", "report", "record", "quality", "documentation", "dokument"),
    ),
    (
        ESCO_QUESTION_SKILL_GROUP_LEADERSHIP_COORDINATION,
        ("lead", "manage", "coordinate", "supervise", "planung", "führung"),
    ),
    (
        ESCO_QUESTION_SKILL_GROUP_PHYSICAL_MANUAL_CONTEXT,
        ("physical", "manual", "craft", "material", "construction", "körper"),
    ),
    (
        ESCO_QUESTION_SKILL_GROUP_DIGITAL_DATA_AI,
        ("digital", "data", "analytics", "ai", "automation", "cloud", "database"),
    ),
    (
        ESCO_QUESTION_SKILL_GROUP_LANGUAGE_COMMUNICATION,
        ("language", "communication", "sprache", "kommunikation", "presentation"),
    ),
    (
        ESCO_QUESTION_SKILL_GROUP_TRANSVERSAL_FIT,
        ("transversal", "soft", "core", "basic", "team", "problem", "learning"),
    ),
)


def map_esco_skill_group_to_canonical(value: Any) -> str:
    text = _coerce_text(value)
    if not text:
        return ""
    normalized = text.strip().casefold().replace("-", "_").replace(" ", "_")
    if normalized in ESCO_QUESTION_SKILL_GROUP_IDS:
        return normalized
    blob = " ".join(re.split(r"[^a-zA-Z0-9äöüÄÖÜß]+", text.casefold()))
    for group_id, keywords in _SKILL_GROUP_KEYWORDS:
        if any(keyword.casefold() in blob for keyword in keywords):
            return group_id
    return ""


def _concept_type(item: Mapping[str, Any]) -> str:
    blob = _normalize_blob(
        item.get("type"),
        item.get("concept_type"),
        item.get("skill_type"),
        item.get("relation"),
    )
    if "knowledge" in blob:
        return "knowledge"
    if "skill" in blob or "competence" in blob:
        return "skill"
    return "unknown"


def _concept_relation(item: Mapping[str, Any], fallback: str) -> str:
    blob = _normalize_blob(item.get("relation"), item.get("matrix_bucket"), fallback)
    if "essential" in blob or "must" in blob:
        return "essential"
    if "optional" in blob or "nice" in blob:
        return "optional"
    return fallback if fallback in {"essential", "optional"} else "unknown"


def _concept_skill_group(item: Mapping[str, Any]) -> str:
    for key in (
        "canonical_skill_group",
        "skill_group_id",
        "skill_group_label",
        "group_hint",
        "skillGroup",
        "skill_group",
    ):
        resolved = map_esco_skill_group_to_canonical(item.get(key))
        if resolved:
            return resolved
    return ""


def _concept_reuse_level(item: Mapping[str, Any]) -> str:
    return _first_field(
        item,
        (
            "reuse_level",
            "reusability_level",
            "skill_reusability",
            "skillReusabilityLevel",
            "reuseLevel",
        ),
    )


def _concept_from_item(
    item: Any,
    *,
    fallback_relation: str,
) -> OccupationQuestionConcept | None:
    if not isinstance(item, Mapping):
        return None
    uri = _first_field(item, ("uri", "concept_uri", "skill_uri", "knowledge_uri"))
    label = _first_field(
        item,
        ("title", "label", "preferredLabel", "name", "skill_title", "knowledge_title"),
    )
    if not uri and not label:
        return None
    concept_type = _concept_type(item)
    relation = _concept_relation(item, fallback_relation)
    return OccupationQuestionConcept(
        uri=uri,
        label=label or uri,
        concept_type=concept_type,  # type: ignore[arg-type]
        relation=relation,  # type: ignore[arg-type]
        source=_first_field(item, ("source", "match_method", "source_hint")) or None,
        skill_group=_concept_skill_group(item) or None,
        reuse_level=_concept_reuse_level(item) or None,
    )


def _dedupe_concepts(
    concepts: list[OccupationQuestionConcept],
) -> list[OccupationQuestionConcept]:
    output: list[OccupationQuestionConcept] = []
    seen: set[str] = set()
    for concept in concepts:
        key = concept.uri.strip() or f"label:{concept.label.casefold().strip()}"
        if not key or key in seen:
            continue
        output.append(concept)
        seen.add(key)
    return output


def build_occupation_question_context(
    *,
    esco_selected: dict[str, Any] | None = None,
    esco_payload: dict[str, Any] | None = None,
    essential_skills: list[dict[str, Any]] | None = None,
    optional_skills: list[dict[str, Any]] | None = None,
    matrix_coverage_rows: list[dict[str, Any]] | None = None,
    skill_group_share: list[dict[str, Any]] | None = None,
    capability_snapshot: Any = None,
    esco_version: str | None = None,
    source_mode: str | None = None,
    language: str = DEFAULT_LANGUAGE,
    regulated_profession: bool | None = None,
) -> OccupationQuestionContext:
    selected = esco_selected if isinstance(esco_selected, dict) else {}
    payload = esco_payload if isinstance(esco_payload, dict) else {}
    sources: tuple[Mapping[str, Any], ...] = (selected, payload)

    occupation_uri = ""
    preferred_label = ""
    for source in sources:
        occupation_uri = occupation_uri or _first_field(source, ("uri", "concept_uri"))
        preferred_label = preferred_label or _first_field(
            source,
            ("title", "preferredLabel", "label", "name"),
        )

    alternative_labels: list[str] = []
    nace_codes: list[str] = []
    isco_code = ""
    for source in sources:
        alternative_labels.extend(
            _list_field(
                source,
                (
                    "alternativeLabel",
                    "altLabel",
                    "altLabels",
                    "hiddenLabel",
                    "nonPreferredTerms",
                ),
            )
        )
        nace_codes.extend(
            _list_field(source, ("naceCodes", "nace_codes", "naceCode", "nace_code"))
        )
        if not isco_code:
            isco_code = _normalize_isco_code(
                _first_field(
                    source,
                    (
                        "occupation_group",
                        "occupationGroup",
                        "iscoGroup",
                        "isco08",
                        "isco08Code",
                        "isco_code",
                    ),
                )
            )

    if regulated_profession is None:
        for source in sources:
            raw_flag = source.get("regulatedProfession")
            if isinstance(raw_flag, bool):
                regulated_profession = raw_flag
                break

    essential_concepts = _dedupe_concepts(
        [
            concept
            for item in essential_skills or []
            if (concept := _concept_from_item(item, fallback_relation="essential"))
            is not None
        ]
    )
    optional_concepts = _dedupe_concepts(
        [
            concept
            for item in optional_skills or []
            if (concept := _concept_from_item(item, fallback_relation="optional"))
            is not None
        ]
    )
    essential_knowledge = [
        concept for concept in essential_concepts if concept.concept_type == "knowledge"
    ]
    optional_knowledge = [
        concept for concept in optional_concepts if concept.concept_type == "knowledge"
    ]
    essential_skill_concepts = [
        concept for concept in essential_concepts if concept.concept_type != "knowledge"
    ]
    optional_skill_concepts = [
        concept for concept in optional_concepts if concept.concept_type != "knowledge"
    ]

    skill_groups: list[str] = []
    reuse_levels: list[str] = []
    for concept in [*essential_concepts, *optional_concepts]:
        if concept.skill_group:
            skill_groups.append(concept.skill_group)
        if concept.reuse_level:
            reuse_levels.append(concept.reuse_level)
    for row in [*(matrix_coverage_rows or []), *(skill_group_share or [])]:
        if not isinstance(row, Mapping):
            continue
        for key in ("skill_group_id", "skill_group_label", "title", "label", "group"):
            mapped = map_esco_skill_group_to_canonical(row.get(key))
            if mapped:
                skill_groups.append(mapped)
                break

    resolved_esco_version = (
        esco_version
        or _capability_field(capability_snapshot, "selected_version")
        or None
    )
    resolved_source_mode = (
        source_mode
        or _capability_field(capability_snapshot, "data_source_mode")
        or None
    )

    return OccupationQuestionContext(
        occupation_uri=occupation_uri,
        preferred_label=preferred_label,
        alternative_labels=_dedupe_strings(alternative_labels),
        isco_code=isco_code or None,
        isco_path=_isco_path(isco_code),
        nace_codes=_dedupe_strings(nace_codes),
        regulated_profession=regulated_profession,
        essential_skill_uris=[concept.uri for concept in essential_skill_concepts if concept.uri],
        optional_skill_uris=[concept.uri for concept in optional_skill_concepts if concept.uri],
        essential_knowledge_uris=[concept.uri for concept in essential_knowledge if concept.uri],
        optional_knowledge_uris=[concept.uri for concept in optional_knowledge if concept.uri],
        essential_skills=essential_skill_concepts,
        optional_skills=optional_skill_concepts,
        essential_knowledge=essential_knowledge,
        optional_knowledge=optional_knowledge,
        skill_groups=_dedupe_strings(skill_groups),
        reuse_levels=_dedupe_strings(reuse_levels),
        esco_version=resolved_esco_version,
        source_mode=resolved_source_mode,
        language=language or DEFAULT_LANGUAGE,
    )


def resolve_question_module_keys(
    context: OccupationQuestionContext | None,
) -> tuple[list[str], dict[str, str]]:
    keys = [OCCUPATION_QUESTION_MODULE_BASE]
    skipped: dict[str, str] = {}
    if context is None:
        skipped["context"] = "missing"
        return keys, skipped

    isco_code = _normalize_isco_code(context.isco_code)
    if isco_code:
        keys.append(f"{OCCUPATION_QUESTION_MODULE_ISCO1_PREFIX}:{isco_code[:1]}")
        if len(isco_code) >= 3:
            keys.append(f"{OCCUPATION_QUESTION_MODULE_ISCO3_PREFIX}:{isco_code[:3]}")
        else:
            skipped[OCCUPATION_QUESTION_MODULE_ISCO3_PREFIX] = "isco_code_too_short"
        if len(isco_code) >= 4:
            keys.append(f"{OCCUPATION_QUESTION_MODULE_ISCO4_PREFIX}:{isco_code[:4]}")
        else:
            skipped[OCCUPATION_QUESTION_MODULE_ISCO4_PREFIX] = "isco_code_too_short"
    else:
        skipped[OCCUPATION_QUESTION_MODULE_ISCO4_PREFIX] = "missing_isco_code"

    if context.occupation_uri:
        keys.append(f"{OCCUPATION_QUESTION_MODULE_ESCO_PREFIX}:{context.occupation_uri}")
    else:
        skipped[OCCUPATION_QUESTION_MODULE_ESCO_PREFIX] = "missing_occupation_uri"

    if context.skill_groups:
        for group in context.skill_groups:
            keys.append(f"{OCCUPATION_QUESTION_MODULE_SKILL_GROUP_PREFIX}:{group}")
    else:
        skipped[OCCUPATION_QUESTION_MODULE_SKILL_GROUP_PREFIX] = "missing_skill_groups"

    if context.nace_codes:
        for nace_code in context.nace_codes:
            keys.append(f"{OCCUPATION_QUESTION_MODULE_NACE_PREFIX}:{nace_code}")
    else:
        skipped[OCCUPATION_QUESTION_MODULE_NACE_PREFIX] = "missing_nace_codes"

    if context.regulated_profession is True:
        keys.append(OCCUPATION_QUESTION_MODULE_REGULATED)
    elif context.regulated_profession is False:
        skipped[OCCUPATION_QUESTION_MODULE_REGULATED] = "not_regulated"
    else:
        skipped[OCCUPATION_QUESTION_MODULE_REGULATED] = "unknown"

    return list(dict.fromkeys(keys)), skipped


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
