from __future__ import annotations

from difflib import SequenceMatcher
from typing import Callable, Mapping, TypedDict

import streamlit as st

from constants import SSKey
from esco_client import (
    EscoClient,
    EscoApiCapabilities,
    EscoClientError,
    ENDPOINT_OCCUPATION_SKILL_GROUP_SHARE,
    OCCUPATION_RELATION_ESSENTIAL_KNOWLEDGE,
    OCCUPATION_RELATION_ESSENTIAL_SKILL,
    OCCUPATION_RELATION_OPTIONAL_KNOWLEDGE,
    OCCUPATION_RELATION_OPTIONAL_SKILL,
    clear_esco_cache,
    is_retryable_server_status,
)
from schemas import JobAdExtract
from ui_components import render_esco_explainability, render_esco_picker_card

_OCCUPATION_DETAIL_RELATIONS: tuple[str, ...] = (
    OCCUPATION_RELATION_ESSENTIAL_SKILL,
    OCCUPATION_RELATION_OPTIONAL_SKILL,
    OCCUPATION_RELATION_ESSENTIAL_KNOWLEDGE,
    OCCUPATION_RELATION_OPTIONAL_KNOWLEDGE,
)
_DEFAULT_SUPPORTED_OCCUPATION_RELATIONS: tuple[str, ...] = (
    OCCUPATION_RELATION_ESSENTIAL_SKILL,
    OCCUPATION_RELATION_OPTIONAL_SKILL,
)

_FIELD_STATE_NOT_DELIVERED = "nicht geliefert"
_FIELD_STATE_FALLBACK_LANGUAGE = (
    "In gewählter Sprache nicht verfügbar (Fallback EN/DE genutzt)"
)
_FIELD_STATE_NOT_LOADED = "noch nicht geladen"
_FIELD_STATE_AVAILABLE = "verfügbar"
_FIELD_STATE_UNSUPPORTED = "nicht unterstützt"
_CAPABILITY_STATE_SUPPORTED = "supported"
_CAPABILITY_STATE_UNSUPPORTED = "unsupported"
_CAPABILITY_STATE_NOT_LOADED = "not loaded"


class _SkillGroupShareRow(TypedDict):
    label: str
    share_percent: float


class _CapabilityStatusRow(TypedDict):
    label: str
    state: str
    value: str


def _build_esco_query(job: JobAdExtract) -> str:
    title = (job.job_title or "").strip()
    if not title:
        return ""
    context_parts = [job.seniority_level, job.department_name, job.location_city]
    context = ", ".join(part.strip() for part in context_parts if part and part.strip())
    if not context:
        return title
    return f"{title} ({context})"


def _collect_occupation_labels(payload: object) -> list[str]:
    collected: list[str] = []
    seen: set[str] = set()

    def _append(value: object) -> None:
        if not isinstance(value, str):
            return
        normalized = value.strip()
        if not normalized:
            return
        dedupe_key = normalized.casefold()
        if dedupe_key in seen:
            return
        seen.add(dedupe_key)
        collected.append(normalized)

    def _walk(node: object) -> None:
        if isinstance(node, dict):
            _append(node.get("preferredLabel"))
            _append(node.get("preferredTerm"))
            _append(node.get("title"))
            alt_labels = (
                node.get("alternativeLabel")
                or node.get("altLabel")
                or node.get("alternativeLabels")
            )
            if isinstance(alt_labels, str):
                _append(alt_labels)
            elif isinstance(alt_labels, list):
                for alt in alt_labels:
                    _append(alt)
            for value in node.values():
                _walk(value)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(payload)
    return collected


def _load_occupation_title_variants(
    *,
    occupation_uri: str,
    languages: list[str],
    client_factory: type[EscoClient] | None = None,
) -> tuple[dict[str, list[str]], list[str]]:
    client = (client_factory or EscoClient)()
    variants: dict[str, list[str]] = {}
    warnings: list[str] = []
    for language in languages:
        try:
            payload = client.terms(
                uri=occupation_uri,
                type="occupation",
                language=language,
            )
        except EscoClientError as exc:
            fallback_language = "en" if language == "de" else "de"
            if exc.status_code is None or exc.status_code >= 500:
                try:
                    payload = client.terms(
                        uri=occupation_uri,
                        type="occupation",
                        language=fallback_language,
                    )
                except EscoClientError as fallback_exc:
                    if (
                        fallback_exc.status_code is None
                        or fallback_exc.status_code >= 500
                    ):
                        warnings.append(language)
                        continue
                    raise

                labels = _collect_occupation_labels(payload)
                if labels:
                    variants[language] = labels
                continue
            raise

        labels = _collect_occupation_labels(payload)
        if labels:
            variants[language] = labels
    return variants, warnings


def _render_esco_why_this_matters() -> None:
    st.info(
        "\n".join(
            [
                "**Warum Occupation-Bestätigung wichtig ist**",
                "",
                "- Sie reduziert Mehrdeutigkeiten beim Rollenverständnis "
                "(z. B. ähnliche Jobtitel mit unterschiedlichen Aufgaben).",
                "- Diese Auswahl wird in `wizard_pages/04_role_tasks.py`, "
                "`wizard_pages/05_skills.py` und `wizard_pages/08_summary.py` "
                "weiterverwendet.",
                "- Ihr Nutzen: schnellere, relevantere Vorschläge sowie ein "
                "klarerer Readiness- und Export-Kontext.",
            ]
        )
    )


def _render_suppressed_repeat_notice(exc: EscoClientError) -> bool:
    if not exc.from_negative_cache:
        return False
    st.caption(
        "ESCO-Anfrage kurzzeitig gedrosselt (wiederholter 4xx-Fehler). "
        f"Unterdrückte Wiederholungen: {exc.suppressed_repeat_count}."
    )
    return True


def _extract_esco_scope_note(payload: object) -> str:
    if not isinstance(payload, dict):
        return ""

    candidate_keys = ("description", "scopeNote", "definition", "note")
    collected: list[str] = []
    seen: set[str] = set()

    def _append(value: object) -> None:
        if not isinstance(value, str):
            return
        normalized = " ".join(value.split()).strip()
        if not normalized:
            return
        key = normalized.casefold()
        if key in seen:
            return
        seen.add(key)
        collected.append(normalized)

    def _walk(node: object) -> None:
        if isinstance(node, dict):
            for candidate_key in candidate_keys:
                _append(node.get(candidate_key))
            for nested in node.values():
                _walk(nested)
        elif isinstance(node, list):
            for nested in node:
                _walk(nested)

    _walk(payload)
    if not collected:
        return ""
    first_text = collected[0]
    if len(first_text) <= 280:
        return first_text
    return f"{first_text[:277].rstrip()}..."


def _normalize_text_list(value: object) -> list[str]:
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []
    if not isinstance(value, list):
        return []
    entries: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            continue
        normalized = item.strip()
        if not normalized:
            continue
        dedupe_key = normalized.casefold()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        entries.append(normalized)
    return entries


def _extract_skill_group_share_rows(payload: object) -> list[_SkillGroupShareRow]:
    if not isinstance(payload, dict):
        return []

    raw_items: list[object] = []
    embedded = payload.get("_embedded")
    if isinstance(embedded, dict):
        for key in ("results", "items", "occupationSkillsGroupShare"):
            value = embedded.get(key)
            if isinstance(value, list):
                raw_items = value
                break
        if not raw_items:
            for value in embedded.values():
                if isinstance(value, list):
                    raw_items = value
                    break
    if not raw_items:
        for key in ("results", "items", "occupationSkillsGroupShare"):
            value = payload.get(key)
            if isinstance(value, list):
                raw_items = value
                break
    if not raw_items:
        return []

    rows: list[_SkillGroupShareRow] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        label = str(
            item.get("skillGroupLabel")
            or item.get("skillGroup")
            or item.get("preferredLabel")
            or item.get("title")
            or item.get("label")
            or item.get("name")
            or ""
        ).strip()
        raw_share = item.get("share")
        if raw_share is None:
            raw_share = item.get("sharePercent")
        if raw_share is None:
            raw_share = item.get("percentage")
        if raw_share is None:
            raw_share = item.get("value")
        if not label or raw_share is None:
            continue
        try:
            share = float(raw_share)
        except (TypeError, ValueError):
            continue
        if share <= 1.0:
            share *= 100.0
        rows.append({"label": label, "share_percent": round(max(0.0, share), 2)})

    rows.sort(key=lambda row: row["share_percent"], reverse=True)
    return rows


def _collect_text_candidates(
    value: object,
    *,
    preferred_language: str | None = None,
    fallback_language: str | None = None,
) -> list[str]:
    collected: list[str] = []
    seen: set[str] = set()

    def _append_text(raw: object) -> None:
        if not isinstance(raw, str):
            return
        normalized = raw.strip()
        if not normalized:
            return
        dedupe_key = normalized.casefold()
        if dedupe_key in seen:
            return
        seen.add(dedupe_key)
        collected.append(normalized)

    def _walk(node: object) -> None:
        if isinstance(node, str):
            _append_text(node)
            return
        if isinstance(node, list):
            for item in node:
                _walk(item)
            return
        if not isinstance(node, dict):
            return

        preferred_value = node.get(preferred_language) if preferred_language else None
        fallback_value = node.get(fallback_language) if fallback_language else None
        _walk(preferred_value)
        _walk(fallback_value)

        for nested in node.values():
            _walk(nested)

    _walk(value)
    return collected


def _extract_first_text(
    payload: object,
    *keys: str,
    preferred_language: str | None = None,
    fallback_language: str | None = None,
) -> str:
    if not isinstance(payload, dict):
        return ""
    for key in keys:
        value = payload.get(key)
        text_candidates = _collect_text_candidates(
            value,
            preferred_language=preferred_language,
            fallback_language=fallback_language,
        )
        if text_candidates:
            return text_candidates[0]
    return ""


def _collect_text_for_language(value: object, language: str) -> list[str]:
    collected: list[str] = []
    seen: set[str] = set()

    def _append(raw: object) -> None:
        if not isinstance(raw, str):
            return
        normalized = raw.strip()
        if not normalized:
            return
        dedupe_key = normalized.casefold()
        if dedupe_key in seen:
            return
        seen.add(dedupe_key)
        collected.append(normalized)

    def _walk(node: object) -> None:
        if isinstance(node, str):
            _append(node)
            return
        if isinstance(node, list):
            for item in node:
                _walk(item)
            return
        if not isinstance(node, dict):
            return
        _walk(node.get(language))

    _walk(value)
    return collected


def _extract_text_field_with_state(
    payload: object,
    *,
    keys: tuple[str, ...],
    preferred_language: str,
    fallback_language: str,
) -> tuple[str, str]:
    if not isinstance(payload, dict):
        return "", _FIELD_STATE_NOT_LOADED

    key_present = False
    for key in keys:
        if key not in payload:
            continue
        key_present = True
        value = payload.get(key)
        preferred = _collect_text_for_language(value, preferred_language)
        if preferred:
            return preferred[0], _FIELD_STATE_AVAILABLE

        fallback = _collect_text_for_language(value, fallback_language)
        if fallback:
            return fallback[0], _FIELD_STATE_FALLBACK_LANGUAGE

        generic = _collect_text_candidates(value)
        if generic:
            return generic[0], _FIELD_STATE_AVAILABLE

    if key_present:
        return "", _FIELD_STATE_NOT_DELIVERED
    return "", _FIELD_STATE_NOT_DELIVERED


def _extract_related_resource_count(payload: object, relation_key: str) -> int:
    if not isinstance(payload, dict):
        return 0
    relation_data = payload.get(relation_key)
    if isinstance(relation_data, list):
        return len(relation_data)
    if isinstance(relation_data, dict):
        embedded = relation_data.get("_embedded")
        if isinstance(embedded, dict):
            for value in embedded.values():
                if isinstance(value, list):
                    return len(value)
    embedded_root = payload.get("_embedded")
    if isinstance(embedded_root, dict):
        relation_embedded = embedded_root.get(relation_key)
        if isinstance(relation_embedded, list):
            return len(relation_embedded)
        for value in embedded_root.values():
            if isinstance(value, list):
                return len(value)
    return 0


def _extract_related_resource_labels(
    payload: object,
    relation_key: str,
) -> list[str]:
    if not isinstance(payload, dict):
        return []

    candidates: list[object] = []
    relation_data = payload.get(relation_key)
    if isinstance(relation_data, list):
        candidates.extend(relation_data)
    if isinstance(relation_data, dict):
        embedded = relation_data.get("_embedded")
        if isinstance(embedded, dict):
            relation_embedded = embedded.get(relation_key)
            if isinstance(relation_embedded, list):
                candidates.extend(relation_embedded)
            for value in embedded.values():
                if isinstance(value, list):
                    candidates.extend(value)

    embedded_root = payload.get("_embedded")
    if isinstance(embedded_root, dict):
        relation_embedded = embedded_root.get(relation_key)
        if isinstance(relation_embedded, list):
            candidates.extend(relation_embedded)
        for value in embedded_root.values():
            if isinstance(value, list):
                candidates.extend(value)

    labels: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        if not isinstance(item, dict):
            continue
        raw_label = (
            item.get("title")
            or item.get("preferredLabel")
            or item.get("preferredTerm")
            or item.get("description")
        )
        if not isinstance(raw_label, str):
            continue
        label = raw_label.strip()
        if not label:
            continue
        dedupe_key = label.casefold()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        labels.append(label)
    return labels


def _supported_occupation_relations(client: EscoClient) -> tuple[str, ...]:
    supported_relations = getattr(client, "supported_occupation_relations", None)
    if callable(supported_relations):
        supported_relations = supported_relations()
    if not isinstance(supported_relations, (tuple, list)):
        return _DEFAULT_SUPPORTED_OCCUPATION_RELATIONS
    resolved = tuple(
        relation.strip()
        for relation in supported_relations
        if isinstance(relation, str) and relation.strip()
    )
    if not resolved:
        return _DEFAULT_SUPPORTED_OCCUPATION_RELATIONS
    return resolved


def _occupation_capabilities(
    client: EscoClient,
    supported_relations: tuple[str, ...],
) -> EscoApiCapabilities:
    get_capabilities = getattr(client, "get_capabilities", None)
    if callable(get_capabilities):
        try:
            capabilities = get_capabilities()
        except Exception:
            capabilities = None
        if isinstance(capabilities, EscoApiCapabilities):
            return capabilities

    supported_relation_set = set(supported_relations)
    supports_knowledge = {
        OCCUPATION_RELATION_ESSENTIAL_KNOWLEDGE,
        OCCUPATION_RELATION_OPTIONAL_KNOWLEDGE,
    }.issubset(supported_relation_set)
    supports_endpoint = getattr(client, "supports_endpoint", None)
    supports_skill_group_share = False
    if callable(supports_endpoint):
        try:
            supports_skill_group_share = bool(
                supports_endpoint(ENDPOINT_OCCUPATION_SKILL_GROUP_SHARE)
            )
        except Exception:
            supports_skill_group_share = False
    unsupported_relations = tuple(
        relation
        for relation in _OCCUPATION_DETAIL_RELATIONS
        if relation not in supported_relation_set
    )
    unsupported_endpoints = (
        frozenset()
        if supports_skill_group_share
        else frozenset({ENDPOINT_OCCUPATION_SKILL_GROUP_SHARE})
    )
    return EscoApiCapabilities(
        supported_occupation_relations=supported_relations,
        unsupported_occupation_relations=unsupported_relations,
        unsupported_endpoints=unsupported_endpoints,
        supports_occupation_knowledge_relations=supports_knowledge,
        supports_occupation_skill_group_share=supports_skill_group_share,
    )


def _capabilities_badge_text(
    *,
    capabilities: EscoApiCapabilities,
) -> str:
    supported_relation_set = set(capabilities.supported_occupation_relations)
    supports_skills = {
        OCCUPATION_RELATION_ESSENTIAL_SKILL,
        OCCUPATION_RELATION_OPTIONAL_SKILL,
    }.issubset(supported_relation_set)
    skill_groups_symbol = (
        "✅"
        if capabilities.supports_occupation_skill_group_share
        else "🚫"
    )
    skills_symbol = "✅" if supports_skills else "🚫"
    knowledge_symbol = (
        "✅" if capabilities.supports_occupation_knowledge_relations else "🚫"
    )
    return (
        "Capabilities: "
        f"Skills {skills_symbol} · "
        f"Knowledge {knowledge_symbol} · "
        f"Skill Groups {skill_groups_symbol}"
    )


def _capability_state(value: bool | None) -> str:
    if value is True:
        return _CAPABILITY_STATE_SUPPORTED
    if value is False:
        return _CAPABILITY_STATE_UNSUPPORTED
    return _CAPABILITY_STATE_NOT_LOADED


def _safe_esco_config(client: EscoClient) -> Mapping[str, object]:
    get_config = getattr(client, "_esco_config", None)
    if not callable(get_config):
        return {}
    try:
        config = get_config()
    except Exception:
        return {}
    return config if isinstance(config, Mapping) else {}


def _build_capability_status_rows(
    *,
    api_mode: str | None,
    selected_version: str | None,
    capabilities: EscoApiCapabilities | None,
) -> list[_CapabilityStatusRow]:
    supported_relations = (
        capabilities.supported_occupation_relations if capabilities is not None else ()
    )
    unsupported_relations = (
        capabilities.unsupported_occupation_relations if capabilities is not None else ()
    )
    supported_relations_text = (
        ", ".join(supported_relations) if supported_relations else "—"
    )
    unsupported_relations_text = (
        ", ".join(unsupported_relations) if unsupported_relations else "—"
    )
    return [
        {
            "label": "API mode",
            "state": (
                _CAPABILITY_STATE_SUPPORTED
                if api_mode and api_mode.strip()
                else _CAPABILITY_STATE_NOT_LOADED
            ),
            "value": api_mode.strip() if isinstance(api_mode, str) and api_mode.strip() else "—",
        },
        {
            "label": "selectedVersion",
            "state": (
                _CAPABILITY_STATE_SUPPORTED
                if selected_version and selected_version.strip()
                else _CAPABILITY_STATE_NOT_LOADED
            ),
            "value": (
                selected_version.strip()
                if isinstance(selected_version, str) and selected_version.strip()
                else "—"
            ),
        },
        {
            "label": "Supported occupation relations",
            "state": (
                _CAPABILITY_STATE_SUPPORTED
                if supported_relations
                else _CAPABILITY_STATE_NOT_LOADED
            ),
            "value": supported_relations_text,
        },
        {
            "label": "Unsupported occupation relations",
            "state": (
                _CAPABILITY_STATE_UNSUPPORTED
                if unsupported_relations
                else _CAPABILITY_STATE_NOT_LOADED
            ),
            "value": unsupported_relations_text,
        },
        {
            "label": "Skill group share support",
            "state": (
                _capability_state(capabilities.supports_occupation_skill_group_share)
                if capabilities is not None
                else _CAPABILITY_STATE_NOT_LOADED
            ),
            "value": (
                "available"
                if capabilities is not None
                and capabilities.supports_occupation_skill_group_share
                else (
                    "not supported"
                    if capabilities is not None
                    else "—"
                )
            ),
        },
        {
            "label": "Knowledge relation support",
            "state": (
                _capability_state(capabilities.supports_occupation_knowledge_relations)
                if capabilities is not None
                else _CAPABILITY_STATE_NOT_LOADED
            ),
            "value": (
                "available"
                if capabilities is not None
                and capabilities.supports_occupation_knowledge_relations
                else (
                    "expected unsupported behavior"
                    if capabilities is not None
                    else "—"
                )
            ),
        },
    ]


def _render_capability_status_panel(
    *,
    client: EscoClient,
    capabilities: EscoApiCapabilities | None,
) -> None:
    config = _safe_esco_config(client)
    api_mode = str(config.get("api_mode") or "").strip() if config else ""
    selected_version = str(config.get("selected_version") or "").strip() if config else ""
    rows = _build_capability_status_rows(
        api_mode=api_mode,
        selected_version=selected_version,
        capabilities=capabilities,
    )
    with st.expander("ESCO Capability Status", expanded=False):
        for row in rows:
            st.caption(f"{row['label']}: {row['state']} · {row['value']}")


def _load_occupation_related_with_policy(
    *,
    client: EscoClient,
    occupation_uri: str,
) -> tuple[dict[str, int], dict[str, list[str]]]:
    supported_relations = _supported_occupation_relations(client)
    counts: dict[str, int] = {}
    labels: dict[str, list[str]] = {}
    if not supported_relations:
        return counts, labels

    for relation in supported_relations:
        try:
            relation_payload = client.resource_related(
                uri=occupation_uri,
                relation=relation,
            )
        except EscoClientError as exc:
            if exc.status_code == 400:
                continue
            raise

        counts[relation] = _extract_related_resource_count(relation_payload, relation)
        relation_labels = _extract_related_resource_labels(relation_payload, relation)
        if relation_labels:
            labels[relation] = relation_labels
    return counts, labels


def _load_occupation_related_counts(
    *,
    client: EscoClient,
    occupation_uri: str,
) -> dict[str, int]:
    counts, _ = _load_occupation_related_with_policy(
        client=client,
        occupation_uri=occupation_uri,
    )
    return counts


def _load_occupation_related_data(
    *,
    client: EscoClient,
    occupation_uri: str,
) -> tuple[dict[str, int], dict[str, list[str]]]:
    return _load_occupation_related_with_policy(
        client=client,
        occupation_uri=occupation_uri,
    )


def _resolve_related_counts(
    payload: object, related_counts: object | None = None
) -> dict[str, int]:
    resolved: dict[str, int] = {}
    if isinstance(related_counts, dict):
        for relation in _OCCUPATION_DETAIL_RELATIONS:
            raw_value = related_counts.get(relation)
            if isinstance(raw_value, int):
                resolved[relation] = raw_value
        if resolved:
            return resolved

    for relation in _OCCUPATION_DETAIL_RELATIONS:
        inferred_value = _extract_related_resource_count(payload, relation)
        if isinstance(inferred_value, int):
            resolved[relation] = inferred_value
    return resolved


def _render_selected_occupation_detail(
    payload: object,
    related_counts: object | None = None,
    related_labels: object | None = None,
    supported_relations: tuple[str, ...] | None = None,
    capabilities: EscoApiCapabilities | None = None,
    skill_group_share_payload: object | None = None,
) -> None:
    if not isinstance(payload, dict):
        st.caption(_FIELD_STATE_NOT_LOADED)
        return

    configured_language = (
        str(
            (st.session_state.get(SSKey.ESCO_CONFIG.value, {}) or {}).get("language")
            or "de"
        )
        .strip()
        .lower()
    )
    preferred_language = configured_language if configured_language in {"de", "en"} else "de"
    fallback_language = "en" if preferred_language == "de" else "de"

    preferred_label, preferred_label_state = _extract_text_field_with_state(
        payload,
        keys=("preferredLabel", "title"),
        preferred_language=preferred_language,
        fallback_language=fallback_language,
    )
    alternative_labels = _normalize_text_list(
        payload.get("alternativeLabel")
        or payload.get("altLabel")
        or payload.get("altLabels")
    )
    description, description_state = _extract_text_field_with_state(
        payload,
        keys=("description",),
        preferred_language=preferred_language,
        fallback_language=fallback_language,
    )
    scope_note, scope_note_state = _extract_text_field_with_state(
        payload,
        keys=("scopeNote",),
        preferred_language=preferred_language,
        fallback_language=fallback_language,
    )
    isco_mapping, isco_mapping_state = _extract_text_field_with_state(
        payload,
        keys=("iscoGroup", "isco08", "isco08Code", "isco_code"),
        preferred_language=preferred_language,
        fallback_language=fallback_language,
    )
    regulated_text, regulated_text_state = _extract_text_field_with_state(
        payload,
        keys=("regulatedProfessionNote", "regulatedProfessionDescription"),
        preferred_language=preferred_language,
        fallback_language=fallback_language,
    )
    regulated_flag = payload.get("regulatedProfession")
    if not isinstance(payload, dict):
        regulated_value = ""
        regulated_state = _FIELD_STATE_NOT_LOADED
    elif regulated_flag is True:
        regulated_value = "Ja"
        regulated_state = _FIELD_STATE_AVAILABLE
    elif regulated_flag is False:
        regulated_value = "Nein"
        regulated_state = _FIELD_STATE_AVAILABLE
    elif "regulatedProfession" in payload:
        regulated_value = ""
        regulated_state = _FIELD_STATE_NOT_DELIVERED
    else:
        regulated_value = ""
        regulated_state = _FIELD_STATE_NOT_DELIVERED
    counts = _resolve_related_counts(payload, related_counts)
    essential_skill_count = counts.get("hasEssentialSkill", 0)
    optional_skill_count = counts.get("hasOptionalSkill", 0)
    supported_relation_set = set(supported_relations or ())
    resolved_capabilities = capabilities or EscoApiCapabilities(
        supported_occupation_relations=tuple(supported_relation_set),
        unsupported_occupation_relations=tuple(
            relation
            for relation in _OCCUPATION_DETAIL_RELATIONS
            if relation not in supported_relation_set
        ),
        unsupported_endpoints=frozenset(),
        supports_occupation_knowledge_relations={
            OCCUPATION_RELATION_ESSENTIAL_KNOWLEDGE,
            OCCUPATION_RELATION_OPTIONAL_KNOWLEDGE,
        }.issubset(supported_relation_set),
        supports_occupation_skill_group_share=True,
    )

    def _is_available(state: str, value: str) -> bool:
        return bool(value) and state in {_FIELD_STATE_AVAILABLE, _FIELD_STATE_FALLBACK_LANGUAGE}

    def _resolve_relation_state(relation_key: str) -> str:
        if relation_key not in supported_relation_set:
            return _FIELD_STATE_UNSUPPORTED
        if not isinstance(related_counts, dict):
            return _FIELD_STATE_NOT_LOADED
        if relation_key in related_counts:
            return _FIELD_STATE_AVAILABLE
        return _FIELD_STATE_NOT_DELIVERED

    essential_skill_state = _resolve_relation_state("hasEssentialSkill")
    optional_skill_state = _resolve_relation_state("hasOptionalSkill")
    essential_knowledge_count = counts.get("hasEssentialKnowledge", 0)
    optional_knowledge_count = counts.get("hasOptionalKnowledge", 0)
    essential_knowledge_state = _resolve_relation_state("hasEssentialKnowledge")
    optional_knowledge_state = _resolve_relation_state("hasOptionalKnowledge")
    alternative_label_state = (
        _FIELD_STATE_AVAILABLE if alternative_labels else _FIELD_STATE_NOT_DELIVERED
    )
    resolved_related_labels = (
        related_labels if isinstance(related_labels, dict) else {}
    )
    essential_skill_labels = _normalize_text_list(
        resolved_related_labels.get("hasEssentialSkill", [])
    )
    optional_skill_labels = _normalize_text_list(
        resolved_related_labels.get("hasOptionalSkill", [])
    )
    essential_knowledge_labels = _normalize_text_list(
        resolved_related_labels.get("hasEssentialKnowledge", [])
    )
    optional_knowledge_labels = _normalize_text_list(
        resolved_related_labels.get("hasOptionalKnowledge", [])
    )

    esco_code = str(payload.get("code") or "").strip() if isinstance(payload, dict) else ""
    nace_codes = _normalize_text_list(payload.get("naceCodes") if isinstance(payload, dict) else [])

    detail_fields = [
        ("Preferred Label", preferred_label, preferred_label_state),
        (
            "Alternative Labels",
            ", ".join(alternative_labels),
            alternative_label_state,
        ),
        ("Description", description, description_state),
        ("Scope Note", scope_note, scope_note_state),
        ("ISCO-08 Mapping", isco_mapping, isco_mapping_state),
        ("Regulated Profession", regulated_value, regulated_state),
        ("Regulated Profession Note", regulated_text, regulated_text_state),
        ("Essential skills", str(essential_skill_count), essential_skill_state),
        ("Optional skills", str(optional_skill_count), optional_skill_state),
        ("Essential knowledge", str(essential_knowledge_count), essential_knowledge_state),
        ("Optional knowledge", str(optional_knowledge_count), optional_knowledge_state),
    ]
    available_fields = sum(1 for _, value, state in detail_fields if _is_available(state, value))

    st.markdown("### ESCO Occupation-Details")
    with st.expander("Mehr Infos", expanded=False):
        st.caption(f"{available_fields}/{len(detail_fields)} Felder verfügbar")
        show_only_available = st.toggle("Nur verfügbare Felder anzeigen", value=True)

        def _render_field(label: str, value: str, state: str) -> None:
            if show_only_available and not _is_available(state, value):
                return
            st.markdown(f"**{label}**")
            if _is_available(state, value):
                st.write(value)
                if state == _FIELD_STATE_FALLBACK_LANGUAGE:
                    st.caption(_FIELD_STATE_FALLBACK_LANGUAGE)
            else:
                st.caption(state)

        st.markdown("##### Beschreibung")
        _render_field("Description", description, description_state)
        _render_field("Scope Note", scope_note, scope_note_state)
        _render_field("Regulated Profession Note", regulated_text, regulated_text_state)

        st.markdown("##### Basisdaten")
        _render_field("Preferred Label", preferred_label, preferred_label_state)
        _render_field(
            "Alternative Labels",
            ", ".join(alternative_labels),
            alternative_label_state,
        )
        _render_field("Regulated Profession", regulated_value, regulated_state)

        st.markdown("##### Klassifikation")
        _render_field("ISCO-08 Mapping", isco_mapping, isco_mapping_state)

        st.markdown("##### Relationen")
        _render_field("Essential skills", str(essential_skill_count), essential_skill_state)
        _render_field("Optional skills", str(optional_skill_count), optional_skill_state)
        _render_field(
            "Essential knowledge",
            str(essential_knowledge_count),
            essential_knowledge_state,
        )
        _render_field(
            "Optional knowledge",
            str(optional_knowledge_count),
            optional_knowledge_state,
        )

        uri = str(payload.get("uri") or "").strip() if isinstance(payload, dict) else ""
        version = str(payload.get("version") or "").strip() if isinstance(payload, dict) else ""
        source = "ESCO API"
        meta_items: list[str] = [f"Quelle: {source}"]
        if version:
            meta_items.append(f"Version: {version}")
        st.caption(" · ".join(meta_items))
        if uri:
            uri_suffix = uri.rstrip("/").rsplit("/", 1)[-1] or uri
            st.markdown(f"[ESCO URI: …{uri_suffix}]({uri})")
            if st.button("URI kopieren", key="esco.occupation.details.uri.copy"):
                st.code(uri, language="text")
                st.caption("URI zum Kopieren eingeblendet.")

    st.markdown("#### Concept overview")
    st.markdown("**Description**")
    if description:
        st.write(description)
    else:
        st.caption(description_state)
    if scope_note:
        st.markdown("**Scope note**")
        st.write(scope_note)

    st.markdown("**ESCO Code**")
    st.write(esco_code or "—")
    st.markdown("**NACE Code**")
    if nace_codes:
        for code in nace_codes:
            st.write(f"- {code}")
    else:
        st.caption("Nicht von ESCO geliefert")

    st.markdown("**Alternative Labels**")
    if alternative_labels:
        for label in alternative_labels:
            st.write(f"- {label}")
    else:
        st.caption(_FIELD_STATE_NOT_DELIVERED)

    st.markdown("#### Skills & Competences")
    skills_supported = {
        OCCUPATION_RELATION_ESSENTIAL_SKILL,
        OCCUPATION_RELATION_OPTIONAL_SKILL,
    }.issubset(supported_relation_set)
    knowledge_supported = resolved_capabilities.supports_occupation_knowledge_relations
    st.caption(
        "Skills: ✅ verfügbar" if skills_supported else "Skills: 🚫 nicht unterstützt"
    )
    if knowledge_supported:
        st.caption("Knowledge: ✅ verfügbar")
    else:
        st.caption("Knowledge: 🚫 nicht unterstützt")

    st.markdown("**Essential Skills and Competences**")
    if essential_skill_labels:
        st.write(" · ".join(essential_skill_labels))
    else:
        st.caption(f"{essential_skill_count} Treffer")

    st.markdown("**Optional Skills and Competences**")
    if optional_skill_labels:
        st.write(" · ".join(optional_skill_labels))
    else:
        st.caption(f"{optional_skill_count} Treffer")

    st.markdown("**Essential Knowledge**")
    if essential_knowledge_labels:
        st.write(" · ".join(essential_knowledge_labels))
    else:
        st.caption(f"{essential_knowledge_count} Treffer")

    st.markdown("**Optional Knowledge**")
    if optional_knowledge_labels:
        st.write(" · ".join(optional_knowledge_labels))
    else:
        st.caption(f"{optional_knowledge_count} Treffer")

    share_rows = _extract_skill_group_share_rows(skill_group_share_payload)
    left_column, center_column, right_column = st.columns([1, 2, 1])
    del left_column, right_column
    with center_column:
        if share_rows:
            st.markdown("##### Skills Group Share")
            st.vega_lite_chart(
                {
                    "mark": {"type": "bar", "cornerRadiusEnd": 4},
                    "encoding": {
                        "x": {
                            "field": "share_percent",
                            "type": "quantitative",
                            "title": "Anteil (%)",
                        },
                        "y": {
                            "field": "label",
                            "type": "nominal",
                            "sort": "-x",
                            "title": "",
                        },
                        "tooltip": [
                            {"field": "label", "type": "nominal", "title": "Gruppe"},
                            {
                                "field": "share_percent",
                                "type": "quantitative",
                                "title": "Anteil (%)",
                            },
                        ],
                    },
                    "data": {"values": share_rows},
                    "height": max(180, len(share_rows) * 34),
                },
                use_container_width=True,
            )
        else:
            st.caption("Keine Skills-Group-Share-Daten verfügbar.")


def _normalize_intent_title(query_text: str) -> str:
    normalized_query = query_text.strip()
    if "(" in normalized_query:
        normalized_query = normalized_query.split("(", 1)[0]
    return normalized_query.strip()


class _EscoExplainability(TypedDict):
    badge_label: str
    reason: str
    confidence: str
    provenance_categories: list[str]


def _infer_esco_match_explainability(
    *,
    query_text: str,
    selected: dict[str, object],
    options: list[dict[str, object]],
    applied_meta: dict[str, object],
) -> _EscoExplainability:
    selected_title = str(selected.get("title") or "").strip()
    selected_uri = str(selected.get("uri") or "").strip()
    intent_title = _normalize_intent_title(query_text)
    intent_folded = intent_title.casefold()
    selected_folded = selected_title.casefold()
    top_option = options[0] if options else {}
    top_uri = str(top_option.get("uri") or "").strip()
    top_title = str(top_option.get("title") or "").strip()
    top_folded = top_title.casefold()
    manual_override = bool(selected_uri and top_uri and selected_uri != top_uri)

    similarity = (
        SequenceMatcher(None, intent_folded, selected_folded).ratio()
        if intent_folded and selected_folded
        else 0.0
    )
    direct_match = bool(
        intent_folded
        and selected_folded
        and (intent_folded in selected_folded or selected_folded in intent_folded)
    )
    top_intent_match = bool(
        intent_folded
        and top_folded
        and (intent_folded in top_folded or top_folded in intent_folded)
    )

    provenance_raw = applied_meta.get("provenance_categories", [])
    provenance_categories = (
        [str(item).strip() for item in provenance_raw if str(item).strip()]
        if isinstance(provenance_raw, list)
        else []
    )

    if manual_override and "manually selected by user" not in provenance_categories:
        provenance_categories.append("manually selected by user")
    if direct_match and "exact label match" not in provenance_categories:
        provenance_categories.append("exact label match")
    if (
        str(applied_meta.get("source") or "").strip().lower().startswith("manual")
        and "synonym/hidden-term match" not in provenance_categories
    ):
        provenance_categories.append("synonym/hidden-term match")

    if manual_override:
        badge_label = "Manually Selected by User"
        reason = f"Auswahl weicht vom Top-Vorschlag '{top_title or '—'}' ab und wurde manuell bestätigt."
        confidence = "high"
    elif direct_match or similarity >= 0.72:
        badge_label = "Exact Label Match"
        reason = f"ESCO-Titel '{selected_title or '—'}' passt direkt zur Query-Intention '{intent_title or '—'}'."
        confidence = "high" if direct_match else "medium"
    elif top_intent_match:
        badge_label = "Synonym/Hidden-Term Match"
        reason = f"Top-Vorschlag '{top_title or '—'}' entspricht der Query-Intention; Auswahl nutzt denselben Kandidatenraum."
        confidence = "medium"
    else:
        badge_label = "Synonym/Hidden-Term Match"
        reason = f"Auswahl '{selected_title or '—'}' wurde als semantische Alternative zur Query '{intent_title or '—'}' übernommen."
        confidence = "low"
        if "synonym/hidden-term match" not in provenance_categories:
            provenance_categories.append("synonym/hidden-term match")

    return {
        "badge_label": badge_label,
        "reason": reason,
        "confidence": confidence,
        "provenance_categories": provenance_categories,
    }


def render_esco_occupation_confirmation(
    job: JobAdExtract,
    *,
    on_next: Callable[[], None] | None = None,
    show_start_context_panels: bool = True,
) -> None:
    # Mobile Verhalten (Smartphone-Breakpoints):
    # - Titel, Match-Badge und Confidence immer in separaten Zeilen/Containern rendern.
    # - ESCO-URI als kurzen Linktext darstellen; Voll-URI nur bei expliziter "Kopieren"-Aktion zeigen.
    # - Explainability-Chips kompakt halten; Zusatzinfos in "Mehr Infos" auslagern.
    query_text = _build_esco_query(job)
    if not query_text:
        st.info("Kein Jobtitel vorhanden. ESCO-Zuordnung aktuell nicht möglich.")
        st.session_state[SSKey.ESCO_OCCUPATION_CANDIDATES.value] = []
        st.session_state[SSKey.ESCO_OCCUPATION_SELECTED.value] = None
        st.session_state[SSKey.ESCO_SELECTED_OCCUPATION_URI.value] = ""
        st.session_state[SSKey.ESCO_UNMAPPED_ROLE_TERMS.value] = []
        return

    if show_start_context_panels:
        st.caption(f"Suche mit: `{query_text}`")
    query_state_key = f"{SSKey.ESCO_OCCUPATION_SELECTED.value}.esco_picker.query"
    if not st.session_state.get(query_state_key):
        st.session_state[query_state_key] = query_text
    if show_start_context_panels:
        _render_esco_why_this_matters()
    render_esco_picker_card(
        concept_type="occupation",
        target_state_key=SSKey.ESCO_OCCUPATION_SELECTED,
        enable_preview=False,
        apply_label=None,
        confirmation_helper_text="Beruf für nachgelagerte Vorschläge bestätigen",
        auto_apply_single_select=True,
        show_apply_button=False,
        show_results_overview=False,
    )
    options_state_key = f"{SSKey.ESCO_OCCUPATION_SELECTED.value}.esco_picker.options"
    options = st.session_state.get(options_state_key, [])
    st.session_state[SSKey.ESCO_OCCUPATION_CANDIDATES.value] = (
        options if isinstance(options, list) else []
    )
    if (
        len(query_text) >= 2
        and not st.session_state[SSKey.ESCO_OCCUPATION_CANDIDATES.value]
        and st.button("Später erneut versuchen", key="esco.occupation.retry_later")
    ):
        clear_esco_cache()
        st.info("Verbindung neu initialisiert. Du kannst die Suche erneut starten.")

    selected_raw = st.session_state.get(SSKey.ESCO_OCCUPATION_SELECTED.value)
    selected = selected_raw if isinstance(selected_raw, dict) else {}
    occupation_uri = str(selected.get("uri") or "").strip()
    if not occupation_uri:
        st.session_state[SSKey.ESCO_SELECTED_OCCUPATION_URI.value] = ""
        st.session_state[SSKey.ESCO_MATCH_REASON.value] = None
        st.session_state[SSKey.ESCO_MATCH_CONFIDENCE.value] = None
        st.session_state[SSKey.ESCO_MATCH_PROVENANCE.value] = []
        st.session_state[SSKey.ESCO_OCCUPATION_PAYLOAD.value] = None
        st.session_state[SSKey.ESCO_OCCUPATION_RELATED_COUNTS.value] = {}
        st.session_state[SSKey.ESCO_OCCUPATION_SKILL_GROUP_SHARE.value] = []
        st.session_state[SSKey.ESCO_OCCUPATION_TITLE_VARIANTS.value] = {}
        st.session_state[SSKey.ESCO_UNMAPPED_ROLE_TERMS.value] = [query_text]
        return
    st.session_state[SSKey.ESCO_UNMAPPED_ROLE_TERMS.value] = []
    st.session_state[SSKey.ESCO_SELECTED_OCCUPATION_URI.value] = occupation_uri

    applied_meta_key = (
        f"{SSKey.ESCO_OCCUPATION_SELECTED.value}.esco_picker.applied_meta"
    )
    applied_meta_raw = st.session_state.get(applied_meta_key, {})
    applied_meta = applied_meta_raw if isinstance(applied_meta_raw, dict) else {}
    explainability = _infer_esco_match_explainability(
        query_text=query_text,
        selected=selected,
        options=options if isinstance(options, list) else [],
        applied_meta=applied_meta,
    )
    st.session_state[SSKey.ESCO_MATCH_REASON.value] = explainability["reason"]
    st.session_state[SSKey.ESCO_MATCH_CONFIDENCE.value] = explainability["confidence"]
    st.session_state[SSKey.ESCO_MATCH_PROVENANCE.value] = explainability[
        "provenance_categories"
    ]

    client = EscoClient()
    supported_relations = _supported_occupation_relations(client)
    capabilities = _occupation_capabilities(client, supported_relations)
    capabilities_badge = _capabilities_badge_text(
        capabilities=capabilities,
    )

    if show_start_context_panels:
        selected_title = str(selected.get("title") or "—").strip() or "—"
        with st.container():
            st.markdown("**Ausgewählte Occupation**")
            st.write(selected_title)
            st.caption(capabilities_badge)
            _render_capability_status_panel(client=client, capabilities=capabilities)
            st.markdown(
                (
                    "<span style='display:inline-block;padding:0.1rem 0.5rem;"
                    "border:1px solid #999;border-radius:0.75rem;font-size:0.8rem;'>"
                    f"{explainability['badge_label']}</span>"
                ),
                unsafe_allow_html=True,
            )
            st.caption(f"Confidence: {str(explainability['confidence']).title()}")
            uri_suffix = occupation_uri.rstrip("/").rsplit("/", 1)[-1] or occupation_uri
            st.markdown(f"[ESCO URI: …{uri_suffix}]({occupation_uri})")
            if st.button("URI kopieren", key="esco.occupation.selected.uri.copy"):
                st.code(occupation_uri, language="text")
                st.caption("URI zum Kopieren eingeblendet.")
        render_esco_explainability(
            labels=explainability["provenance_categories"],
            confidence=str(explainability["confidence"]),
            reason=str(explainability["reason"]),
            caption_prefix="Occupation Explainability",
        )
    related_labels: dict[str, list[str]] = {}
    try:
        occupation_payload = client.get_occupation_detail(uri=occupation_uri)
    except EscoClientError as exc:
        if _render_suppressed_repeat_notice(exc):
            st.session_state[SSKey.ESCO_OCCUPATION_PAYLOAD.value] = None
            st.session_state[SSKey.ESCO_OCCUPATION_RELATED_COUNTS.value] = {}
            st.session_state[SSKey.ESCO_OCCUPATION_SKILL_GROUP_SHARE.value] = []
            return
        if is_retryable_server_status(exc.status_code) or exc.status_code is None:
            st.warning(
                "ESCO ist gerade nicht stabil erreichbar. "
                "Du kannst manuell fortfahren und später erneut laden."
            )
            c_manual, c_retry = st.columns(2)
            with c_manual:
                if st.button(
                    "Manuell fortfahren",
                    key="esco.occupation.manual_continue",
                ):
                    st.session_state[SSKey.ESCO_OCCUPATION_PAYLOAD.value] = None
                    st.info(
                        "Fortsetzung ohne ESCO-Details aktiviert. "
                        "Die Auswahl kann später ergänzt werden."
                    )
            with c_retry:
                if st.button("Später erneut versuchen", key="esco.occupation.retry"):
                    clear_esco_cache()
                    st.info("Bitte den Ladevorgang später erneut ausführen.")
        else:
            st.warning(f"ESCO-Occupationsdetails konnten nicht geladen werden: {exc}")
        st.session_state[SSKey.ESCO_OCCUPATION_PAYLOAD.value] = None
        st.session_state[SSKey.ESCO_OCCUPATION_RELATED_COUNTS.value] = {}
        st.session_state[SSKey.ESCO_OCCUPATION_SKILL_GROUP_SHARE.value] = []
    else:
        st.session_state[SSKey.ESCO_OCCUPATION_PAYLOAD.value] = occupation_payload
        try:
            related_counts, related_labels = _load_occupation_related_data(
                client=client,
                occupation_uri=occupation_uri,
            )
            st.session_state[SSKey.ESCO_OCCUPATION_RELATED_COUNTS.value] = related_counts
        except EscoClientError as exc:
            if _render_suppressed_repeat_notice(exc):
                st.session_state[SSKey.ESCO_OCCUPATION_RELATED_COUNTS.value] = {}
                related_labels = {}
            else:
                if is_retryable_server_status(exc.status_code) or exc.status_code is None:
                    st.warning(
                        "ESCO-Relationsdaten sind gerade nicht stabil erreichbar. "
                        "Du kannst manuell fortfahren und später erneut laden."
                    )
                else:
                    st.warning(
                        "ESCO-Relationsdaten konnten nicht vollständig geladen werden: "
                        f"{exc}"
                )
                st.session_state[SSKey.ESCO_OCCUPATION_RELATED_COUNTS.value] = {}
                related_labels = {}
        if capabilities.supports_occupation_skill_group_share:
            try:
                skill_group_share_payload = client.get_occupation_skill_group_share(
                    occupation_uri=occupation_uri
                )
                st.session_state[SSKey.ESCO_OCCUPATION_SKILL_GROUP_SHARE.value] = (
                    skill_group_share_payload
                )
            except EscoClientError as exc:
                if _render_suppressed_repeat_notice(exc):
                    st.session_state[SSKey.ESCO_OCCUPATION_SKILL_GROUP_SHARE.value] = []
                else:
                    if (
                        is_retryable_server_status(exc.status_code)
                        or exc.status_code is None
                    ):
                        st.warning(
                            "ESCO-Skillgruppen-Daten sind gerade nicht stabil erreichbar. "
                            "Du kannst manuell fortfahren und später erneut laden."
                        )
                    else:
                        st.warning(
                            "ESCO-Skillgruppen-Daten konnten nicht vollständig geladen werden: "
                            f"{exc}"
                        )
                    st.session_state[SSKey.ESCO_OCCUPATION_SKILL_GROUP_SHARE.value] = []
        else:
            st.session_state[SSKey.ESCO_OCCUPATION_SKILL_GROUP_SHARE.value] = []
            st.caption(
                "Skillgruppen-Anteil ist für die aktuelle ESCO-Version/den Modus nicht verfügbar."
            )
    if show_start_context_panels:
        _render_selected_occupation_detail(
            st.session_state.get(SSKey.ESCO_OCCUPATION_PAYLOAD.value),
            st.session_state.get(SSKey.ESCO_OCCUPATION_RELATED_COUNTS.value),
            related_labels,
            supported_relations=supported_relations,
            capabilities=capabilities,
            skill_group_share_payload=st.session_state.get(
                SSKey.ESCO_OCCUPATION_SKILL_GROUP_SHARE.value
            ),
        )

    if show_start_context_panels:
        configured_language = (
            str(
                (st.session_state.get(SSKey.ESCO_CONFIG.value, {}) or {}).get(
                    "language"
                )
                or "de"
            )
            .strip()
            .lower()
        )
        language_options = {"de": "Deutsch (DE)", "en": "English (EN)"}
        default_languages = (
            [configured_language] if configured_language in language_options else ["de"]
        )
        selected_languages = st.multiselect(
            "Bevorzugte Occupation-Titelsprachen",
            options=list(language_options.keys()),
            default=default_languages,
            format_func=lambda value: language_options[value],
            key=f"{SSKey.ESCO_OCCUPATION_TITLE_VARIANTS.value}.languages",
        )
        languages = selected_languages or default_languages

        if st.button(
            "Titel-Varianten laden",
            key=f"{SSKey.ESCO_OCCUPATION_TITLE_VARIANTS.value}.load",
        ):
            try:
                variants, warning_languages = _load_occupation_title_variants(
                    occupation_uri=occupation_uri,
                    languages=languages,
                )
            except EscoClientError as exc:
                st.warning(f"ESCO-Titelvarianten konnten nicht geladen werden: {exc}")
            else:
                st.session_state[SSKey.ESCO_OCCUPATION_TITLE_VARIANTS.value] = {
                    "uri": occupation_uri,
                    "recommended_titles": variants,
                    "warnings": warning_languages,
                }

        title_variants_raw = st.session_state.get(
            SSKey.ESCO_OCCUPATION_TITLE_VARIANTS.value
        )
        if isinstance(title_variants_raw, dict):
            variant_uri = str(title_variants_raw.get("uri") or "").strip()
            variants_by_language = title_variants_raw.get("recommended_titles", {})
            if variant_uri == occupation_uri and isinstance(variants_by_language, dict):
                warnings_raw = title_variants_raw.get("warnings", [])
                warning_languages = (
                    [str(item).strip() for item in warnings_raw if str(item).strip()]
                    if isinstance(warnings_raw, list)
                    else []
                )
                if warning_languages:
                    joined_languages = ", ".join(
                        f"{item.upper()}" for item in warning_languages
                    )
                    st.warning(
                        "Titelvarianten konnten nicht in allen Sprachen geladen werden "
                        f"({joined_languages}). Bitte später erneut versuchen."
                    )
                with st.expander("Geladene Occupation-Titelvarianten", expanded=False):
                    for language in languages:
                        labels_raw = variants_by_language.get(language, [])
                        labels = labels_raw if isinstance(labels_raw, list) else []
                        if not labels:
                            st.caption(f"{language.upper()}: keine Titel gefunden.")
                            continue
                        st.markdown(f"**{language.upper()}**")
                        for label in labels:
                            st.write(f"- {label}")

    unmapped_roles_raw = st.session_state.get(SSKey.ESCO_UNMAPPED_ROLE_TERMS.value, [])
    unmapped_roles = (
        [str(item).strip() for item in unmapped_roles_raw if str(item).strip()]
        if isinstance(unmapped_roles_raw, list)
        else []
    )
    if unmapped_roles:
        st.markdown("### Not normalized yet")
        st.caption(
            "Diese Rollenbegriffe konnten noch nicht robust auf ESCO abgebildet werden."
        )
        for term in unmapped_roles:
            st.write(f"- {term}")
