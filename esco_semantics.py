"""Canonical ESCO semantic state and feature gates."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from typing import Any

from constants import (
    DEFAULT_ESCO_DATA_SOURCE_MODE,
    DEFAULT_ESCO_RELEASE_LANE,
    DEFAULT_ESCO_SELECTED_VERSION,
    ESCO_ANCHOR_STATE_ANCHORED,
    ESCO_ANCHOR_STATE_ANCHORED_WITH_CONTEXT,
    ESCO_ANCHOR_STATE_DEGRADED,
    ESCO_ANCHOR_STATES,
    ESCO_DATA_SOURCE_MODES,
    ESCO_RELEASE_LANE_PREVIEW,
    ESCO_RELEASE_LANE_SELECTED_VERSION,
    ESCO_RELEASE_LANE_STABLE,
    ESCO_RELEASE_LANES,
    ESCO_SECONDARY_ANCHOR_MAX,
    ESCO_SEMANTIC_EXPORT_MODE_ANCHORED,
    ESCO_SEMANTIC_EXPORT_MODE_DEGRADED,
    SSKey,
)
from schemas import EscoAnchorRef, EscoCapabilitySnapshot, EscoSemanticContext


ESCO_FEATURE_SKILLS_NORMALIZATION = "skills_normalization"
ESCO_FEATURE_INTERVIEW_PRIORITIZATION = "interview_prioritization"
ESCO_FEATURE_SEMANTIC_EXPORT = "semantic_export"
ESCO_FEATURE_MATRIX_COVERAGE = "matrix_coverage"
ESCO_FEATURE_TASK_SUGGESTIONS = "task_suggestions"


def normalize_release_lane(value: object) -> str:
    lane = str(value or "").strip().lower()
    return lane if lane in ESCO_RELEASE_LANES else DEFAULT_ESCO_RELEASE_LANE


def selected_version_for_release_lane(release_lane: str) -> str:
    lane = normalize_release_lane(release_lane)
    return ESCO_RELEASE_LANE_SELECTED_VERSION.get(lane, DEFAULT_ESCO_SELECTED_VERSION)


def infer_release_lane_from_version(selected_version: object) -> str:
    version = str(selected_version or "").strip()
    if version == ESCO_RELEASE_LANE_SELECTED_VERSION[ESCO_RELEASE_LANE_PREVIEW]:
        return ESCO_RELEASE_LANE_PREVIEW
    return ESCO_RELEASE_LANE_STABLE


def resolve_fallback_language(primary_language: object, fallback_language: object) -> str:
    primary = str(primary_language or "de").strip().lower() or "de"
    fallback = str(fallback_language or "").strip().lower()
    if fallback and fallback != primary:
        return fallback
    return "en" if primary == "de" else "de"


def normalize_anchor_ref(
    raw: object,
    *,
    selected_as: str = "primary",
    default_reason: str | None = None,
) -> dict[str, Any] | None:
    if not isinstance(raw, Mapping):
        return None
    uri = str(raw.get("uri") or "").strip()
    if not uri:
        return None
    title = str(
        raw.get("title")
        or raw.get("preferredLabel")
        or raw.get("label")
        or raw.get("name")
        or ""
    ).strip()
    normalized = {
        "uri": uri,
        "title": title,
        "type": str(raw.get("type") or "occupation").strip() or "occupation",
        "code": str(raw.get("code") or "").strip() or None,
        "reason": str(raw.get("reason") or default_reason or "").strip() or None,
        "selected_as": "secondary" if selected_as == "secondary" else "primary",
    }
    try:
        return EscoAnchorRef.model_validate(normalized).model_dump(mode="json")
    except Exception:
        return None


def _session_dict(session_state: Mapping[str, object], key: SSKey) -> dict[str, Any]:
    raw = session_state.get(key.value)
    return dict(raw) if isinstance(raw, Mapping) else {}


def _session_list(session_state: Mapping[str, object], key: SSKey) -> list[Any]:
    raw = session_state.get(key.value)
    return list(raw) if isinstance(raw, list) else []


def resolve_primary_anchor(session_state: Mapping[str, object]) -> dict[str, Any] | None:
    primary = normalize_anchor_ref(session_state.get(SSKey.ESCO_PRIMARY_ANCHOR.value))
    if primary is not None:
        return primary

    legacy_selected = normalize_anchor_ref(
        session_state.get(SSKey.ESCO_OCCUPATION_SELECTED.value)
    )
    if legacy_selected is not None:
        return legacy_selected

    legacy_uri = str(
        session_state.get(SSKey.ESCO_SELECTED_OCCUPATION_URI.value) or ""
    ).strip()
    if not legacy_uri:
        return None
    return {
        "uri": legacy_uri,
        "title": "",
        "type": "occupation",
        "code": None,
        "reason": None,
        "selected_as": "primary",
    }


def resolve_secondary_anchors(
    session_state: Mapping[str, object],
    *,
    primary_uri: str = "",
) -> list[dict[str, Any]]:
    anchors: list[dict[str, Any]] = []
    seen: set[str] = {primary_uri} if primary_uri else set()
    for item in _session_list(session_state, SSKey.ESCO_SECONDARY_ANCHORS):
        anchor = normalize_anchor_ref(
            item,
            selected_as="secondary",
            default_reason="context",
        )
        if anchor is None:
            continue
        uri = str(anchor.get("uri") or "").strip()
        if not uri or uri in seen:
            continue
        anchors.append(anchor)
        seen.add(uri)
        if len(anchors) >= ESCO_SECONDARY_ANCHOR_MAX:
            break
    return anchors


def build_capability_snapshot(
    session_state: Mapping[str, object],
    *,
    capabilities: object | None = None,
) -> dict[str, Any]:
    config = _session_dict(session_state, SSKey.ESCO_CONFIG)
    release_lane = normalize_release_lane(
        session_state.get(SSKey.ESCO_RELEASE_LANE.value)
        or config.get("release_lane")
        or infer_release_lane_from_version(config.get("selected_version"))
    )
    selected_version = str(
        config.get("selected_version") or selected_version_for_release_lane(release_lane)
    ).strip() or DEFAULT_ESCO_SELECTED_VERSION
    language = str(config.get("language") or "de").strip().lower() or "de"
    fallback_language = resolve_fallback_language(
        language,
        config.get("fallback_language"),
    )
    data_source_mode = str(
        config.get("data_source_mode") or DEFAULT_ESCO_DATA_SOURCE_MODE
    ).strip().lower()
    if data_source_mode not in ESCO_DATA_SOURCE_MODES:
        data_source_mode = DEFAULT_ESCO_DATA_SOURCE_MODE

    supported_relations = tuple(
        str(item)
        for item in getattr(capabilities, "supported_occupation_relations", ()) or ()
    )
    supports_skills = {"hasEssentialSkill", "hasOptionalSkill"}.issubset(
        set(supported_relations)
    )
    payload = {
        "release_lane": release_lane,
        "selected_version": selected_version,
        "api_mode": str(config.get("api_mode") or "hosted").strip().lower()
        or "hosted",
        "data_source_mode": data_source_mode,
        "language": language,
        "fallback_language": fallback_language,
        "view_obsolete": bool(config.get("view_obsolete", False)),
        "last_data_source": str(
            session_state.get(SSKey.ESCO_LAST_DATA_SOURCE.value) or ""
        ).strip()
        or None,
        "supports_occupation_skills": supports_skills,
        "supports_occupation_knowledge": bool(
            getattr(capabilities, "supports_occupation_knowledge_relations", False)
        ),
        "supports_skill_group_share": bool(
            getattr(capabilities, "supports_occupation_skill_group_share", False)
        ),
    }
    try:
        return EscoCapabilitySnapshot.model_validate(payload).model_dump(mode="json")
    except Exception:
        payload["api_mode"] = "hosted"
        return EscoCapabilitySnapshot.model_validate(payload).model_dump(mode="json")


def resolve_esco_semantic_context(
    session_state: Mapping[str, object],
    *,
    capabilities: object | None = None,
) -> EscoSemanticContext:
    primary_anchor = resolve_primary_anchor(session_state)
    primary_uri = str((primary_anchor or {}).get("uri") or "").strip()
    secondary_anchors = resolve_secondary_anchors(
        session_state,
        primary_uri=primary_uri,
    )
    configured_state = str(
        session_state.get(SSKey.ESCO_ANCHOR_STATE.value) or ""
    ).strip()
    if configured_state not in ESCO_ANCHOR_STATES:
        configured_state = ""

    if not primary_uri:
        anchor_state = ESCO_ANCHOR_STATE_DEGRADED
    elif secondary_anchors:
        anchor_state = ESCO_ANCHOR_STATE_ANCHORED_WITH_CONTEXT
    else:
        anchor_state = (
            configured_state
            if configured_state in {
                ESCO_ANCHOR_STATE_ANCHORED,
                ESCO_ANCHOR_STATE_ANCHORED_WITH_CONTEXT,
            }
            else ESCO_ANCHOR_STATE_ANCHORED
        )

    anchored = anchor_state in {
        ESCO_ANCHOR_STATE_ANCHORED,
        ESCO_ANCHOR_STATE_ANCHORED_WITH_CONTEXT,
    }
    semantic_export_mode = (
        ESCO_SEMANTIC_EXPORT_MODE_ANCHORED
        if anchored
        else ESCO_SEMANTIC_EXPORT_MODE_DEGRADED
    )
    context = EscoSemanticContext(
        anchor_state=anchor_state,  # type: ignore[arg-type]
        semantic_export_mode=semantic_export_mode,  # type: ignore[arg-type]
        primary_anchor=primary_anchor,
        secondary_anchors=secondary_anchors,
        capability_snapshot=build_capability_snapshot(
            session_state,
            capabilities=capabilities,
        ),
        can_use_esco_normalization=anchored,
        can_use_matrix_coverage=anchored,
        can_use_semantic_exports=anchored,
        can_use_esco_interview_prioritization=anchored,
        can_use_task_suggestions=anchored,
    )
    return context


def sync_esco_semantic_state(
    session_state: MutableMapping[str, object],
    *,
    capabilities: object | None = None,
) -> EscoSemanticContext:
    context = resolve_esco_semantic_context(
        session_state,
        capabilities=capabilities,
    )
    payload = context.model_dump(mode="json", exclude_none=True)
    primary_anchor = payload.get("primary_anchor")
    secondary_anchors = payload.get("secondary_anchors", [])
    capability_snapshot = payload.get("capability_snapshot", {})

    session_state[SSKey.ESCO_ANCHOR_STATE.value] = context.anchor_state
    session_state[SSKey.ESCO_SEMANTIC_EXPORT_MODE.value] = (
        context.semantic_export_mode
    )
    session_state[SSKey.ESCO_CAPABILITY_SNAPSHOT.value] = capability_snapshot
    session_state[SSKey.ESCO_SECONDARY_ANCHORS.value] = secondary_anchors
    if isinstance(capability_snapshot, dict):
        session_state[SSKey.ESCO_RELEASE_LANE.value] = str(
            capability_snapshot.get("release_lane") or DEFAULT_ESCO_RELEASE_LANE
        )

    if isinstance(primary_anchor, dict):
        session_state[SSKey.ESCO_PRIMARY_ANCHOR.value] = primary_anchor
        legacy = {
            "uri": str(primary_anchor.get("uri") or "").strip(),
            "title": str(primary_anchor.get("title") or "").strip(),
            "type": str(primary_anchor.get("type") or "occupation").strip()
            or "occupation",
            "code": primary_anchor.get("code"),
        }
        session_state[SSKey.ESCO_OCCUPATION_SELECTED.value] = legacy
        session_state[SSKey.ESCO_SELECTED_OCCUPATION_URI.value] = legacy["uri"]
    else:
        session_state[SSKey.ESCO_PRIMARY_ANCHOR.value] = None
        session_state[SSKey.ESCO_SELECTED_OCCUPATION_URI.value] = ""
        if context.anchor_state == ESCO_ANCHOR_STATE_DEGRADED:
            session_state[SSKey.ESCO_OCCUPATION_SELECTED.value] = None
    return context


def esco_feature_enabled(context: EscoSemanticContext, feature: str) -> bool:
    if feature == ESCO_FEATURE_SKILLS_NORMALIZATION:
        return context.can_use_esco_normalization
    if feature == ESCO_FEATURE_INTERVIEW_PRIORITIZATION:
        return context.can_use_esco_interview_prioritization
    if feature == ESCO_FEATURE_SEMANTIC_EXPORT:
        return context.can_use_semantic_exports
    if feature == ESCO_FEATURE_MATRIX_COVERAGE:
        return context.can_use_matrix_coverage
    if feature == ESCO_FEATURE_TASK_SUGGESTIONS:
        return context.can_use_task_suggestions
    return False
