"""Mode-aware trust grammar for external and enrichment-derived values."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

import streamlit as st

from constants import (
    DEFAULT_ESCO_DATA_SOURCE_MODE,
    ESCO_DATA_SOURCE_LIVE_API,
    ESCO_DATA_SOURCE_OFFLINE_INDEX,
    FactResolutionStatus,
    FactSourceType,
    SSKey,
    UI_MODE_DEFAULT,
)
from i18n import active_language
from ui_badges import render_provenance_badge, render_source_evidence_popover
from ux_copy_contract import trust_grammar_copy

TRUST_STATE_DETECTED: Final[str] = "detected"
TRUST_STATE_SUGGESTED: Final[str] = "suggested"
TRUST_STATE_CONFIRMED: Final[str] = "confirmed"
TRUST_STATE_ASSUMED: Final[str] = "assumed"
TRUST_STATE_CONFLICTED: Final[str] = "conflicted"
TRUST_STATE_MISSING: Final[str] = "missing"
TRUST_STATE_FALLBACK: Final[str] = "fallback"
TRUST_STATE_EVIDENCE: Final[str] = "evidence"
TRUST_STATES: Final[frozenset[str]] = frozenset(
    {
        TRUST_STATE_DETECTED,
        TRUST_STATE_SUGGESTED,
        TRUST_STATE_CONFIRMED,
        TRUST_STATE_ASSUMED,
        TRUST_STATE_CONFLICTED,
        TRUST_STATE_MISSING,
        TRUST_STATE_FALLBACK,
        TRUST_STATE_EVIDENCE,
    }
)
TRUST_METADATA_KEYS: Final[tuple[str, ...]] = (
    "attempted_source",
    "final_source",
    "fallback_reason",
    "endpoint",
    "version",
    "data_source_mode",
)


@dataclass(frozen=True)
class TrustIndicatorPayload:
    state: str
    label: str
    action: str
    source_label: str
    badge_text: str
    hint: str
    metadata: dict[str, str]


def _trust_language(language: str | None = None) -> str:
    if language:
        return str(language).strip().lower() or "de"
    try:
        return active_language()
    except Exception:
        return "de"


def _normalize_ui_mode(ui_mode: str | None = None) -> str:
    normalized = str(
        ui_mode
        if ui_mode is not None
        else st.session_state.get(SSKey.UI_MODE.value, UI_MODE_DEFAULT)
    ).strip().lower()
    return normalized if normalized in {"quick", "standard", "expert"} else UI_MODE_DEFAULT


def normalize_trust_state(state: str | None) -> str:
    normalized = str(state or "").strip().lower()
    return normalized if normalized in TRUST_STATES else TRUST_STATE_EVIDENCE


def trust_state_for_fact_status(
    resolution_status: str,
    *,
    source_type: str = "",
    confirmed: bool | None = None,
) -> str:
    status = str(resolution_status or "").strip()
    if confirmed is True or status == FactResolutionStatus.CONFIRMED.value:
        return TRUST_STATE_CONFIRMED
    if status == FactResolutionStatus.CONFLICTED.value:
        return TRUST_STATE_CONFLICTED
    if status == FactResolutionStatus.MISSING.value:
        return TRUST_STATE_MISSING
    if status == FactResolutionStatus.ASSUMED.value:
        return TRUST_STATE_ASSUMED
    if status == FactResolutionStatus.INFERRED.value:
        if source_type in {FactSourceType.ESCO.value, FactSourceType.LLM.value}:
            return TRUST_STATE_SUGGESTED
        return TRUST_STATE_DETECTED
    if source_type == FactSourceType.MANUAL.value:
        return TRUST_STATE_CONFIRMED
    return TRUST_STATE_EVIDENCE


def _source_display_label(
    *,
    source_type: str = "",
    source_label: str = "",
    language: str,
) -> str:
    normalized_type = str(source_type or "").strip().lower()
    if normalized_type:
        label = trust_grammar_copy(f"sources.{normalized_type}", language=language)
        if label != f"sources.{normalized_type}":
            return label
    return str(source_label or "").strip()


def _metadata_display_value(key: str, value: object, *, language: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if key in {"attempted_source", "final_source", "data_source_mode"}:
        label = trust_grammar_copy(f"sources.{text}", language=language)
        if label != f"sources.{text}":
            return label
    return text


def _sanitized_metadata(
    metadata: Mapping[str, object] | None,
    *,
    language: str,
) -> dict[str, str]:
    if not isinstance(metadata, Mapping):
        return {}
    sanitized: dict[str, str] = {}
    for key in TRUST_METADATA_KEYS:
        value = _metadata_display_value(key, metadata.get(key), language=language)
        if value:
            sanitized[key] = value
    return sanitized


def build_trust_indicator_payload(
    state: str,
    *,
    source_type: str = "",
    source_label: str = "",
    hint: str = "",
    metadata: Mapping[str, object] | None = None,
    language: str | None = None,
) -> TrustIndicatorPayload:
    resolved_language = _trust_language(language)
    resolved_state = normalize_trust_state(state)
    label = trust_grammar_copy(
        f"states.{resolved_state}.label",
        language=resolved_language,
    )
    action = trust_grammar_copy(
        f"states.{resolved_state}.action",
        language=resolved_language,
    )
    resolved_source_label = _source_display_label(
        source_type=source_type,
        source_label=source_label,
        language=resolved_language,
    )
    badge_parts = [label, action, resolved_source_label]
    resolved_hint = str(hint or "").strip() or trust_grammar_copy(
        f"hints.{resolved_state}",
        language=resolved_language,
    )
    return TrustIndicatorPayload(
        state=resolved_state,
        label=label,
        action=action,
        source_label=resolved_source_label,
        badge_text=" · ".join(part for part in badge_parts if part),
        hint=resolved_hint,
        metadata=_sanitized_metadata(metadata, language=resolved_language),
    )


def render_trust_indicator(
    *,
    state: str,
    source_type: str = "",
    source_label: str = "",
    hint: str = "",
    evidence: Mapping[str, object] | None = None,
    metadata: Mapping[str, object] | None = None,
    ui_mode: str | None = None,
    language: str | None = None,
    streamlit_module: Any | None = None,
) -> TrustIndicatorPayload:
    st_module = streamlit_module or st
    resolved_language = _trust_language(language)
    payload = build_trust_indicator_payload(
        state,
        source_type=source_type,
        source_label=source_label,
        hint=hint,
        metadata=metadata,
        language=resolved_language,
    )
    render_provenance_badge(
        label=payload.badge_text,
        needs_confirmation=payload.state
        in {
            TRUST_STATE_ASSUMED,
            TRUST_STATE_CONFLICTED,
            TRUST_STATE_FALLBACK,
            TRUST_STATE_MISSING,
        },
        language=resolved_language,
        streamlit_module=st_module,
    )

    mode = _normalize_ui_mode(ui_mode)
    if mode in {"standard", "expert"} and payload.hint and hasattr(st_module, "caption"):
        st_module.caption(payload.hint)

    if mode == "expert":
        if evidence:
            render_source_evidence_popover(
                evidence,
                trigger_label=trust_grammar_copy(
                    "evidence_trigger",
                    language=resolved_language,
                ),
                language=resolved_language,
                streamlit_module=st_module,
            )
        if payload.metadata:
            expander = getattr(st_module, "expander", None)
            detail_context = (
                expander(
                    trust_grammar_copy("details_title", language=resolved_language),
                    expanded=False,
                )
                if callable(expander)
                else None
            )
            if detail_context is not None:
                with detail_context:
                    for key in TRUST_METADATA_KEYS:
                        value = payload.metadata.get(key)
                        if not value:
                            continue
                        label = trust_grammar_copy(
                            f"metadata.{key}",
                            language=resolved_language,
                        )
                        st_module.caption(f"{label}: {value}")
    return payload


def build_esco_lookup_trust_payload(
    *,
    config: Mapping[str, object] | None = None,
    metadata: Mapping[str, object] | None = None,
    language: str | None = None,
) -> TrustIndicatorPayload:
    resolved_language = _trust_language(language)
    resolved_config = config if isinstance(config, Mapping) else {}
    resolved_metadata = metadata if isinstance(metadata, Mapping) else {}
    configured_mode = str(
        resolved_config.get("data_source_mode") or DEFAULT_ESCO_DATA_SOURCE_MODE
    ).strip()
    attempted_source = str(resolved_metadata.get("attempted_source") or "").strip()
    final_source = str(resolved_metadata.get("final_source") or "").strip()
    fallback_reason = str(resolved_metadata.get("fallback_reason") or "").strip()

    if (
        attempted_source == ESCO_DATA_SOURCE_LIVE_API
        and final_source == ESCO_DATA_SOURCE_OFFLINE_INDEX
    ):
        state = TRUST_STATE_FALLBACK
        hint_key = "esco_lookup_fallback_hint"
    elif final_source:
        state = TRUST_STATE_EVIDENCE
        hint_key = (
            "esco_lookup_offline_hint"
            if final_source == ESCO_DATA_SOURCE_OFFLINE_INDEX
            else "esco_lookup_live_first_hint"
        )
    else:
        state = TRUST_STATE_MISSING
        hint_key = "esco_lookup_missing_hint"

    merged_metadata = dict(resolved_metadata)
    if configured_mode and "data_source_mode" not in merged_metadata:
        merged_metadata["data_source_mode"] = configured_mode
    if fallback_reason:
        merged_metadata["fallback_reason"] = fallback_reason

    return build_trust_indicator_payload(
        state,
        source_type=final_source if final_source else "",
        hint=trust_grammar_copy(hint_key, language=resolved_language),
        metadata=merged_metadata,
        language=resolved_language,
    )


def render_esco_lookup_trust_indicator(
    *,
    config: Mapping[str, object] | None = None,
    metadata: Mapping[str, object] | None = None,
    ui_mode: str | None = None,
    language: str | None = None,
    streamlit_module: Any | None = None,
) -> TrustIndicatorPayload:
    resolved_config = config
    if resolved_config is None:
        raw_config = st.session_state.get(SSKey.ESCO_CONFIG.value, {})
        resolved_config = raw_config if isinstance(raw_config, Mapping) else {}
    resolved_metadata = metadata
    if resolved_metadata is None:
        raw_metadata = st.session_state.get(SSKey.ESCO_LOOKUP_METADATA.value, {})
        resolved_metadata = raw_metadata if isinstance(raw_metadata, Mapping) else {}
    details_metadata = dict(resolved_metadata)
    if (
        isinstance(resolved_config, Mapping)
        and "data_source_mode" not in details_metadata
        and resolved_config.get("data_source_mode")
    ):
        details_metadata["data_source_mode"] = resolved_config["data_source_mode"]
    payload = build_esco_lookup_trust_payload(
        config=resolved_config,
        metadata=resolved_metadata,
        language=language,
    )
    return render_trust_indicator(
        state=payload.state,
        source_label=payload.source_label,
        hint=payload.hint,
        metadata=details_metadata,
        ui_mode=ui_mode,
        language=language,
        streamlit_module=streamlit_module,
    )
