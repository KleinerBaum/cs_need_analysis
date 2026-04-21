from __future__ import annotations

from difflib import SequenceMatcher
from typing import Callable, TypedDict

import streamlit as st

from constants import SSKey
from esco_client import (
    EscoClient,
    EscoClientError,
    clear_esco_cache,
    is_retryable_server_status,
)
from schemas import JobAdExtract
from ui_components import render_esco_explainability, render_esco_picker_card

_OCCUPATION_RELATED_RELATIONS: tuple[str, ...] = (
    "hasEssentialSkill",
    "hasOptionalSkill",
    "hasEssentialKnowledge",
    "hasOptionalKnowledge",
)

_FIELD_STATE_NOT_DELIVERED = "Nicht von ESCO geliefert"
_FIELD_STATE_FALLBACK_LANGUAGE = (
    "In gewählter Sprache nicht verfügbar (Fallback EN/DE genutzt)"
)
_FIELD_STATE_NOT_LOADED = "Noch nicht geladen"
_FIELD_STATE_AVAILABLE = "verfügbar"


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


def _load_occupation_related_counts(
    *,
    client: EscoClient,
    occupation_uri: str,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for relation in _OCCUPATION_RELATED_RELATIONS:
        relation_payload = client.resource_related(uri=occupation_uri, relation=relation)
        counts[relation] = _extract_related_resource_count(relation_payload, relation)
    return counts


def _resolve_related_counts(
    payload: object, related_counts: object | None = None
) -> dict[str, int]:
    if isinstance(related_counts, dict):
        resolved: dict[str, int] = {}
        for relation in _OCCUPATION_RELATED_RELATIONS:
            raw_value = related_counts.get(relation)
            if isinstance(raw_value, int):
                resolved[relation] = raw_value
        if resolved:
            return resolved

    return {
        relation: _extract_related_resource_count(payload, relation)
        for relation in _OCCUPATION_RELATED_RELATIONS
    }


def _render_selected_occupation_detail(
    payload: object, related_counts: object | None = None
) -> None:
    if not isinstance(payload, dict):
        st.caption(_FIELD_STATE_NOT_LOADED)

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
    essential_knowledge_count = counts.get("hasEssentialKnowledge", 0)
    optional_knowledge_count = counts.get("hasOptionalKnowledge", 0)

    def _is_available(state: str, value: str) -> bool:
        return bool(value) and state in {_FIELD_STATE_AVAILABLE, _FIELD_STATE_FALLBACK_LANGUAGE}

    has_relation_counts = isinstance(related_counts, dict) and bool(related_counts)
    relation_state = _FIELD_STATE_AVAILABLE if has_relation_counts else _FIELD_STATE_NOT_LOADED
    alternative_label_state = (
        _FIELD_STATE_AVAILABLE if alternative_labels else _FIELD_STATE_NOT_DELIVERED
    )

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
        ("Essential skills", str(essential_skill_count), relation_state),
        ("Optional skills", str(optional_skill_count), relation_state),
        ("Essential knowledge", str(essential_knowledge_count), relation_state),
        ("Optional knowledge", str(optional_knowledge_count), relation_state),
    ]
    available_fields = sum(1 for _, value, state in detail_fields if _is_available(state, value))

    with st.expander("ESCO Occupation-Details", expanded=False):
        st.caption(f"{available_fields}/{len(detail_fields)} Felder verfügbar")
        show_only_available = st.toggle("Nur verfügbare Felder anzeigen", value=False)

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
        _render_field("Essential skills", str(essential_skill_count), relation_state)
        _render_field("Optional skills", str(optional_skill_count), relation_state)
        _render_field(
            "Essential knowledge",
            str(essential_knowledge_count),
            relation_state,
        )
        _render_field("Optional knowledge", str(optional_knowledge_count), relation_state)

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
    job: JobAdExtract, *, on_next: Callable[[], None] | None = None
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

    st.caption(f"Suche mit: `{query_text}`")
    query_state_key = f"{SSKey.ESCO_OCCUPATION_SELECTED.value}.esco_picker.query"
    if not st.session_state.get(query_state_key):
        st.session_state[query_state_key] = query_text
    _render_esco_why_this_matters()
    render_esco_picker_card(
        concept_type="occupation",
        target_state_key=SSKey.ESCO_OCCUPATION_SELECTED,
        enable_preview=False,
        apply_label="Speichern",
        confirmation_helper_text="Beruf für nachgelagerte Vorschläge bestätigen",
        secondary_action_label="Weiter →" if on_next is not None else None,
        secondary_action_key="cs.start.esco.next",
        secondary_action_on_click=on_next,
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

    selected_title = str(selected.get("title") or "—").strip() or "—"
    with st.container():
        st.markdown("**Ausgewählte Occupation**")
        st.write(selected_title)
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
    client = EscoClient()
    try:
        occupation_payload = client.get_occupation_detail(uri=occupation_uri)
    except EscoClientError as exc:
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
    else:
        st.session_state[SSKey.ESCO_OCCUPATION_PAYLOAD.value] = occupation_payload
        try:
            st.session_state[SSKey.ESCO_OCCUPATION_RELATED_COUNTS.value] = (
                _load_occupation_related_counts(
                    client=client,
                    occupation_uri=occupation_uri,
                )
            )
        except EscoClientError as exc:
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
    _render_selected_occupation_detail(
        st.session_state.get(SSKey.ESCO_OCCUPATION_PAYLOAD.value),
        st.session_state.get(SSKey.ESCO_OCCUPATION_RELATED_COUNTS.value),
    )

    configured_language = (
        str(
            (st.session_state.get(SSKey.ESCO_CONFIG.value, {}) or {}).get("language")
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
