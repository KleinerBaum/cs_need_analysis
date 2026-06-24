# ui_esco_picker.py
"""ESCO picker UI helpers."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from typing import Any, Literal

import streamlit as st

from constants import SSKey
from esco_client import EscoClient, EscoClientError
from esco_semantics import sync_esco_semantic_state
from i18n import active_language
from schemas import EscoBreadcrumbNode, EscoConceptRef
from ui_inputs import _inject_esco_single_select_pills_css, _set_session_flag_true
from ux_copy_contract import esco_ui_copy


def _esco_copy(key: str, **params: Any) -> str:
    return esco_ui_copy(key, language=active_language(), **params)

def _normalize_target_state_key(target_state_key: SSKey | str) -> str:
    if isinstance(target_state_key, SSKey):
        return target_state_key.value
    return str(target_state_key).strip()


def _clean_esco_occupation_query(query_text: str) -> str:
    cleaned = re.sub(r"\s*\([^()]*\)\s*$", "", query_text).strip()
    return cleaned if cleaned != query_text.strip() else ""


def _infer_applied_provenance_categories(
    *,
    query_text: str,
    selected_payload: list[dict[str, str]],
    selected_index: int | None,
    allow_multi: bool,
) -> list[str]:
    categories: list[str] = []
    normalized_query = query_text.strip().casefold()
    normalized_titles = [
        str(item.get("title", "")).strip().casefold() for item in selected_payload
    ]

    if normalized_query and any(
        normalized_query in title or title in normalized_query
        for title in normalized_titles
        if title
    ):
        categories.append("exact label match")

    if any(
        str(item.get("source", "auto")).strip().lower() == "manual"
        for item in selected_payload
    ):
        categories.append("synonym/hidden-term match")

    if not allow_multi and selected_index is not None and selected_index > 0:
        categories.append("manually selected by user")

    if not categories:
        categories.append("exact label match")
    return categories


def _extract_esco_suggestions(
    payload: dict[str, Any],
    *,
    concept_type: Literal["occupation", "skill"],
    source: Literal["auto", "manual"],
) -> list[dict[str, str]]:
    seen_uris: set[str] = set()
    collected: list[dict[str, str]] = []

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            uri_raw = node.get("uri")
            title_raw = (
                node.get("title")
                or node.get("preferredLabel")
                or node.get("label")
                or node.get("name")
            )
            type_raw = (
                node.get("type")
                or node.get("conceptType")
                or node.get("className")
                or concept_type
            )
            if isinstance(uri_raw, str) and isinstance(title_raw, str):
                uri = uri_raw.strip()
                title = title_raw.strip()
                if uri and title and uri not in seen_uris:
                    seen_uris.add(uri)
                    collected.append(
                        {
                            "uri": uri,
                            "title": title,
                            "type": str(type_raw or concept_type).strip().lower()
                            or concept_type,
                            "source": source,
                        }
                    )
            for value in node.values():
                _walk(value)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(payload)

    unknown_types = {"", "unknown", "other"}

    def _matches_concept(item: dict[str, str]) -> bool:
        item_type = item.get("type", "").strip().lower()
        uri = item.get("uri", "").strip().lower()
        if item_type == concept_type:
            return True
        if concept_type == "occupation":
            return item_type in unknown_types and "/occupation/" in uri
        if concept_type == "skill":
            return item_type in unknown_types and "/skill/" in uri
        return False

    normalized: list[dict[str, str]] = []
    for item in collected:
        entry = dict(item)
        if not entry.get("type"):
            entry["type"] = concept_type
        if _matches_concept(entry):
            if entry["type"] in unknown_types:
                entry["type"] = concept_type
            normalized.append(entry)
        elif entry.get("type", "").strip().lower() in unknown_types:
            entry["type"] = concept_type
            normalized.append(entry)
    return normalized


def _normalize_esco_breadcrumb_nodes(
    payload: dict[str, Any],
) -> list[EscoBreadcrumbNode]:
    nodes: list[EscoBreadcrumbNode] = []
    seen: set[str] = set()

    def _append_candidate(uri_raw: Any, title_raw: Any, type_raw: Any) -> None:
        if not isinstance(uri_raw, str) or not isinstance(title_raw, str):
            return
        uri = uri_raw.strip()
        title = title_raw.strip()
        if not uri or not title or uri in seen:
            return
        try:
            node = EscoBreadcrumbNode.model_validate(
                {
                    "uri": uri,
                    "title": title,
                    "type": str(type_raw).strip().lower() if type_raw else None,
                }
            )
        except Exception:
            return
        seen.add(node.uri)
        nodes.append(node)

    def _walk(value: Any) -> None:
        if isinstance(value, dict):
            _append_candidate(
                value.get("uri"),
                value.get("title")
                or value.get("preferredLabel")
                or value.get("label")
                or value.get("name"),
                value.get("type"),
            )
            for nested in value.values():
                _walk(nested)
        elif isinstance(value, list):
            for nested in value:
                _walk(nested)

    _walk(payload)
    return nodes


def _build_esco_concept_id(concept: dict[str, Any], index: int) -> str:
    uri = str(concept.get("uri") or "").strip()
    if uri:
        uri_suffix = uri.rstrip("/").rsplit("/", 1)[-1]
        normalized_suffix = re.sub(r"[^a-zA-Z0-9._-]+", "-", uri_suffix).strip("-")
        if normalized_suffix:
            return normalized_suffix

    title = str(concept.get("title") or "").strip() or "untitled"
    stable_source = f"{title.lower()}::{index}"
    digest = hashlib.sha1(stable_source.encode("utf-8")).hexdigest()[:12]
    return f"fallback-{digest}"


def _render_esco_taxonomy_breadcrumb(
    *,
    session_key: str,
    concept: dict[str, Any],
    concept_id: str,
    auto_load: bool = False,
    in_expander: bool = True,
    title: str | None = None,
    show_title: bool = True,
) -> None:
    concept_uri = str(concept.get("uri") or "").strip()
    concept_title = str(concept.get("title") or "—").strip()
    resolved_title = title or _esco_copy("taxonomy_title")

    expander_key = f"{session_key}.esco_picker.taxonomy.open.{concept_id}"
    fetch_key = f"{session_key}.esco_picker.taxonomy.fetch.{concept_id}"
    cache_key = f"{session_key}.esco_picker.taxonomy.cache.{concept_id}"
    loaded_key = f"{session_key}.esco_picker.taxonomy.loaded.{concept_id}"
    error_key = f"{session_key}.esco_picker.taxonomy.error.{concept_id}"
    uri_key = f"{session_key}.esco_picker.taxonomy.uri.{concept_id}"

    def _load_taxonomy() -> None:
        if not concept_uri:
            st.session_state[error_key] = _esco_copy("taxonomy_missing_uri")
            st.session_state[loaded_key] = False
            st.session_state.pop(cache_key, None)
            return
        try:
            payload = EscoClient().resource_related(
                uri=concept_uri,
                relation="hasBroaderTransitive",
            )
            normalized_nodes = _normalize_esco_breadcrumb_nodes(payload)
            st.session_state[cache_key] = [
                node.model_dump() for node in normalized_nodes
            ]
            st.session_state[loaded_key] = True
            st.session_state.pop(error_key, None)
        except EscoClientError as exc:
            st.session_state[error_key] = str(exc)
            st.session_state[loaded_key] = False

    def _render_content() -> None:
        cache_hit_for_uri = st.session_state.get(uri_key) == concept_uri
        if not cache_hit_for_uri:
            st.session_state.pop(cache_key, None)
            st.session_state.pop(error_key, None)
            st.session_state[loaded_key] = False
            st.session_state[uri_key] = concept_uri

        if auto_load and not bool(st.session_state.get(loaded_key, False)):
            _load_taxonomy()
        elif not auto_load and st.button(_esco_copy("load_taxonomy"), key=fetch_key):
            if not concept_uri:
                st.session_state[error_key] = _esco_copy("taxonomy_missing_uri")
                st.session_state[loaded_key] = False
                st.session_state.pop(cache_key, None)
                return
            _load_taxonomy()

        cached_nodes_raw = st.session_state.get(cache_key, [])
        cached_nodes: list[EscoBreadcrumbNode] = []
        if isinstance(cached_nodes_raw, list):
            for item in cached_nodes_raw:
                try:
                    cached_nodes.append(EscoBreadcrumbNode.model_validate(item))
                except Exception:
                    continue

        fetch_error = st.session_state.get(error_key)
        if isinstance(fetch_error, str) and fetch_error.strip():
            st.warning(_esco_copy("taxonomy_load_failed", error=fetch_error))
            return

        if not cached_nodes:
            if bool(st.session_state.get(loaded_key, False)):
                st.caption(_esco_copy("no_broader_relation"))
                return
            st.caption(_esco_copy("taxonomy_not_loaded"))
            return

        breadcrumb_nodes = list(reversed(cached_nodes))
        breadcrumb_nodes.append(
            EscoBreadcrumbNode.model_validate(
                {
                    "uri": concept_uri,
                    "title": concept_title or "—",
                    "type": concept.get("type"),
                }
            )
        )
        titles = [node.title for node in breadcrumb_nodes if node.title.strip()]
        if not titles:
            st.caption(_esco_copy("no_taxonomy"))
            return

        st.write(" → ".join(titles))

    if in_expander and show_title:
        with st.expander(
            resolved_title, expanded=bool(st.session_state.get(expander_key, False))
        ):
            st.session_state[expander_key] = True
            _render_content()
    else:
        if show_title:
            st.markdown(f"**{resolved_title}**")
        _render_content()


def render_esco_picker_card(
    *,
    concept_type: Literal["occupation", "skill"],
    target_state_key: SSKey | str,
    allow_multi: bool = False,
    enable_preview: bool = False,
    apply_label: str | None = None,
    preview_label: str | None = None,
    selection_label: str | None = None,
    confirmation_helper_text: str | None = None,
    secondary_action_label: str | None = None,
    secondary_action_key: str | None = None,
    secondary_action_disabled: bool = False,
    secondary_action_on_click: Callable[[], None] | None = None,
    show_results_overview: bool = True,
    auto_apply_single_select: bool = False,
    show_apply_button: bool = True,
    query_label: str | None = None,
    query_placeholder: str | None = None,
    confirmed_summary_label: str | None = None,
    show_confirmed_summary: bool = True,
    taxonomy_auto_load: bool = False,
    taxonomy_in_expander: bool = True,
    taxonomy_title: str | None = None,
    layout_variant: Literal["default", "anchor_card", "secondary_anchor"] = "default",
) -> None:
    session_key = _normalize_target_state_key(target_state_key)
    if not session_key:
        st.error(_esco_copy("config_invalid"))
        return

    base_key = f"{session_key}.esco_picker"
    query_key = f"{base_key}.query"
    submit_flag_key = f"{base_key}.submit_enter"
    options_state_key = f"{base_key}.options"
    selected_key = f"{base_key}.selected"
    preview_key = f"{base_key}.preview"
    applied_meta_key = f"{base_key}.applied_meta"
    apply_button_key = f"{base_key}.apply"
    auto_apply_value_key = f"{base_key}.auto_apply_value"

    ui_mode = str(st.session_state.get(SSKey.UI_MODE.value, "standard")).strip().lower()
    if ui_mode not in {"quick", "standard", "expert"}:
        ui_mode = "standard"

    use_anchor_card = (
        layout_variant == "anchor_card"
        and concept_type == "occupation"
        and not allow_multi
    )
    use_secondary_anchor_card = (
        layout_variant == "secondary_anchor"
        and concept_type == "occupation"
        and not allow_multi
    )
    resolved_query_label = (
        _esco_copy("anchor_query")
        if use_anchor_card
        else (
            _esco_copy("context_query")
            if use_secondary_anchor_card
            else (query_label or _esco_copy("default_query"))
        )
    )
    query_text = st.text_input(
        resolved_query_label,
        key=query_key,
        placeholder=query_placeholder or _esco_copy("query_placeholder"),
        on_change=_set_session_flag_true,
        args=(submit_flag_key,),
    ).strip()
    if use_anchor_card:
        st.caption(_esco_copy("anchor_helper"))

    suggestions: list[dict[str, str]] = []
    used_fallback_path = False
    used_cleaned_query_fallback = False
    if len(query_text) >= 2:
        client = EscoClient()
        try:
            suggestions = _extract_esco_suggestions(
                client.suggest2(text=query_text, type=concept_type, limit=12),
                concept_type=concept_type,
                source="auto",
            )
            if not suggestions:
                used_fallback_path = True
                suggestions = _extract_esco_suggestions(
                    client.search(text=query_text, type=concept_type, limit=12),
                    concept_type=concept_type,
                    source="manual",
                )
            cleaned_query = (
                _clean_esco_occupation_query(query_text)
                if concept_type == "occupation"
                else ""
            )
            if not suggestions and len(cleaned_query) >= 2:
                used_cleaned_query_fallback = True
                suggestions = _extract_esco_suggestions(
                    client.suggest2(text=cleaned_query, type=concept_type, limit=12),
                    concept_type=concept_type,
                    source="auto",
                )
                if not suggestions:
                    suggestions = _extract_esco_suggestions(
                        client.search(text=cleaned_query, type=concept_type, limit=12),
                        concept_type=concept_type,
                        source="manual",
                    )
        except EscoClientError as exc:
            st.warning(_esco_copy("search_unavailable", error=exc))

    st.session_state[options_state_key] = suggestions
    options = st.session_state.get(options_state_key, [])
    options = options if isinstance(options, list) else []
    if len(query_text) >= 2 and not options:
        st.info(_esco_copy("no_match"))
        if ui_mode == "expert":
            esco_config = st.session_state.get(SSKey.ESCO_CONFIG.value, {})
            resolved_config = esco_config if isinstance(esco_config, dict) else {}
            language = str(resolved_config.get("language") or "de")
            selected_version = str(resolved_config.get("selected_version") or "latest")
            st.caption(
                _esco_copy(
                    "diagnostics",
                    language=language,
                    selected_version=selected_version,
                    fallback_used=_esco_copy("yes") if used_fallback_path else _esco_copy("no"),
                    cleaned_query_fallback_used=(
                        _esco_copy("yes")
                        if used_cleaned_query_fallback
                        else _esco_copy("no")
                    ),
                )
            )

    def _label_for_option(item: dict[str, str]) -> str:
        return item.get("title", "—")

    option_labels = [_label_for_option(item) for item in options]
    selected_payload: list[dict[str, str]] = []
    selected_index: int | None = None

    def _render_selection_controls() -> None:
        nonlocal selected_payload, selected_index
        if allow_multi:
            resolved_selection_label = selection_label or _esco_copy("suggestions")
            selected_indices = st.multiselect(
                resolved_selection_label,
                options=list(range(len(options))),
                format_func=lambda idx: option_labels[idx],
                key=selected_key,
            )
            selected_payload = [
                options[idx] for idx in selected_indices if idx < len(options)
            ]
            return

        resolved_selection_label = selection_label or (
            _esco_copy("select_reference")
            if use_anchor_card
            else (
                _esco_copy("select_context")
                if use_secondary_anchor_card
                else _esco_copy("select_top")
            )
        )
        if hasattr(st, "pills"):
            _inject_esco_single_select_pills_css()
            selected_index = st.pills(
                resolved_selection_label,
                options=list(range(len(options))),
                format_func=lambda idx: option_labels[idx],
                selection_mode="single",
                default=0 if options else None,
                key=selected_key,
            )
        else:
            selected_index = st.selectbox(
                resolved_selection_label,
                options=list(range(len(options))),
                format_func=lambda idx: option_labels[idx],
                index=0 if options else None,
                key=selected_key,
                placeholder=_esco_copy("no_suggestions"),
            )
            if options and show_results_overview:
                overview_columns = st.columns(3, gap="small")
                for idx, concept in enumerate(options[:3]):
                    with overview_columns[idx % 3]:
                        concept_title = (
                            str(concept.get("title") or "—").strip() or "—"
                        )
                        status_label = (
                            _esco_copy("selected")
                            if idx == selected_index
                            else _esco_copy("alternative")
                        )
                        with st.container(border=True):
                            st.markdown(f"**{idx + 1}. {concept_title}**")
                            st.caption(status_label)
        if selected_index is not None and selected_index < len(options):
            selected_payload = [options[selected_index]]

    if use_anchor_card:
        with st.container(border=True):
            _render_selection_controls()
    else:
        _render_selection_controls()

    enter_submit = bool(st.session_state.get(submit_flag_key, False))
    if enter_submit:
        st.session_state[submit_flag_key] = False
        if options:
            selected_payload = [options[0]] if not allow_multi else selected_payload
            st.info(_esco_copy("top_match_enter"))

    if enable_preview:
        resolved_preview_label = preview_label or _esco_copy("preview_before_apply")
        with st.expander(
            resolved_preview_label,
            expanded=bool(st.session_state.get(preview_key, False)),
        ):
            st.session_state[preview_key] = True
            if not selected_payload:
                st.caption(_esco_copy("no_preview_selection"))
            else:
                st.markdown(_esco_copy("preview_selection"))
                for concept in selected_payload:
                    if ui_mode == "expert":
                        st.caption(
                            f"{concept.get('title', '—')} · URI: {concept.get('uri', '—')} · "
                            f"{_esco_copy('source')}: {concept.get('source', 'auto')}"
                        )
                    else:
                        st.write(f"- {concept.get('title', '—')}")

    if confirmation_helper_text:
        st.caption(confirmation_helper_text)

    resolved_apply_label = apply_label or _esco_copy("apply")
    secondary_clicked = False
    apply_clicked = False
    if auto_apply_single_select and not allow_multi:
        previous_auto_value = st.session_state.get(auto_apply_value_key)
        current_auto_value = ""
        if selected_payload:
            current_auto_value = str(selected_payload[0].get("uri") or "").strip()
        if current_auto_value and current_auto_value != previous_auto_value:
            apply_clicked = True
            st.session_state[auto_apply_value_key] = current_auto_value
    if show_apply_button:
        if secondary_action_label:
            apply_col, secondary_col = st.columns([1, 1], gap="small")
            with apply_col:
                if st.button(resolved_apply_label, key=apply_button_key):
                    apply_clicked = True
            with secondary_col:
                secondary_clicked = st.button(
                    secondary_action_label,
                    key=secondary_action_key or f"{base_key}.secondary_action",
                    disabled=secondary_action_disabled,
                )
        else:
            if st.button(resolved_apply_label, key=apply_button_key):
                apply_clicked = True

    if apply_clicked or (enter_submit and bool(options)):
        try:
            validated = [
                EscoConceptRef.model_validate(
                    {
                        "uri": item["uri"],
                        "title": item["title"],
                        "type": item["type"],
                    }
                ).model_dump()
                for item in selected_payload
            ]
        except Exception:
            st.warning(_esco_copy("validate_failed"))
            return

        if allow_multi:
            st.session_state[session_key] = validated
        else:
            st.session_state[session_key] = validated[0] if validated else None
        if session_key == SSKey.ESCO_OCCUPATION_SELECTED.value:
            st.session_state[SSKey.ESCO_SELECTED_OCCUPATION_URI.value] = (
                str(validated[0].get("uri") or "").strip() if validated else ""
            )
            st.session_state[SSKey.ESCO_PRIMARY_ANCHOR.value] = (
                {
                    **validated[0],
                    "reason": None,
                    "selected_as": "primary",
                }
                if validated
                else None
            )
            sync_esco_semantic_state(st.session_state)

        st.session_state[applied_meta_key] = {
            "version": (st.session_state.get(SSKey.ESCO_CONFIG.value, {}) or {}).get(
                "selected_version", "latest"
            ),
            "source": ", ".join(
                sorted({item.get("source", "auto") for item in selected_payload})
            )
            if selected_payload
            else "auto",
            "provenance_categories": _infer_applied_provenance_categories(
                query_text=query_text,
                selected_payload=selected_payload,
                selected_index=selected_index,
                allow_multi=allow_multi,
            ),
        }

    if secondary_clicked and secondary_action_on_click is not None:
        secondary_action_on_click()

    stored = st.session_state.get(session_key)
    current_entries: list[dict[str, Any]] = []
    if allow_multi and isinstance(stored, list):
        for entry in stored:
            try:
                current_entries.append(
                    EscoConceptRef.model_validate(entry).model_dump()
                )
            except Exception:
                continue
    elif isinstance(stored, dict):
        try:
            current_entries = [EscoConceptRef.model_validate(stored).model_dump()]
        except Exception:
            current_entries = []

    if not current_entries or not show_confirmed_summary:
        return

    applied_meta = st.session_state.get(applied_meta_key, {})
    version = (
        applied_meta.get("version", "latest")
        if isinstance(applied_meta, dict)
        else "latest"
    )
    source = (
        applied_meta.get("source", "auto") if isinstance(applied_meta, dict) else "auto"
    )

    if use_anchor_card:
        for idx, concept in enumerate(current_entries):
            concept_id = _build_esco_concept_id(concept, idx)
            with st.container(border=True):
                summary_col, taxonomy_col = st.columns([0.9, 1.4], gap="medium")
                with summary_col:
                    st.markdown(_esco_copy("confirmed_reference"))
                    st.markdown(f"**{concept['title']}**")
                    if ui_mode == "expert":
                        st.caption(
                            f"URI: {concept['uri']} · Version: {version} · "
                            f"{_esco_copy('source')}: {source}"
                        )
                with taxonomy_col:
                    st.markdown(_esco_copy("catalog_position"))
                    _render_esco_taxonomy_breadcrumb(
                        session_key=session_key,
                        concept=concept,
                        concept_id=concept_id,
                        auto_load=taxonomy_auto_load,
                        in_expander=False,
                        title=taxonomy_title,
                        show_title=False,
                    )
        return

    st.markdown(f"**{confirmed_summary_label or _esco_copy('confirmed_selection')}**")
    for idx, concept in enumerate(current_entries):
        concept_id = _build_esco_concept_id(concept, idx)
        if ui_mode == "expert":
            st.caption(
                f"{concept['title']} · URI: {concept['uri']} · Version: {version} · "
                f"{_esco_copy('source')}: {source}"
            )
        else:
            st.write(f"- {concept['title']}")
        _render_esco_taxonomy_breadcrumb(
            session_key=session_key,
            concept=concept,
            concept_id=concept_id,
            auto_load=taxonomy_auto_load,
            in_expander=taxonomy_in_expander,
            title=taxonomy_title,
        )
