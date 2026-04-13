# ui_components.py
"""Reusable Streamlit UI components."""

from __future__ import annotations

import re
import hashlib
from datetime import date
from collections.abc import Sequence
from typing import Any, Dict, Literal, Optional, TypedDict

import streamlit as st

from constants import (
    AnswerType,
    SSKey,
    UI_DETAILS_DEFAULT_BY_MODE_TEXT,
    UI_STEP_COMPACT_TOGGLE_HELP,
    UI_STEP_COMPACT_TOGGLE_LABEL,
    WIDGET_KEY_PREFIX,
)
from esco_client import EscoClient, EscoClientError
from llm_client import OpenAICallError
from question_dependencies import should_show_question
from question_progress import (
    build_answered_lookup,
    build_step_scope_progress_labels,
    compute_question_progress,
)
from schemas import (
    BooleanSearchPack,
    Contact,
    EscoBreadcrumbNode,
    EmploymentContractDraft,
    EscoConceptRef,
    InterviewPrepSheetHiringManager,
    InterviewPrepSheetHR,
    JobAdExtract,
    LanguageRequirement,
    MoneyRange,
    Question,
    QuestionOption,
    QuestionPlan,
    QuestionStep,
    RecruitmentStep,
    VacancyBrief,
    question_option_label_map,
)
from state import (
    get_answer_meta,
    get_answers,
    mark_answer_touched,
    set_answer,
    set_error,
)
from step_status import StepStatusPayload, build_step_status_payload

ESCO_EXPLAINABILITY_LABELS: tuple[str, ...] = (
    "exact label match",
    "synonym/hidden-term match",
    "derived from occupation relation",
    "manually selected by user",
)
ESCO_CONFIDENCE_BUCKETS: tuple[str, ...] = ("high", "medium", "low")


class StepReviewPayload(TypedDict):
    visible_questions: list[Question]
    answers: dict[str, Any]
    answer_meta: dict[str, Any]
    answered_lookup: dict[str, bool]
    step_status: StepStatusPayload


def build_step_review_payload(step: QuestionStep | None) -> StepReviewPayload:
    answers = get_answers()
    answer_meta = get_answer_meta()
    step_status = build_step_status_payload(
        step=step,
        answers=answers,
        answer_meta=answer_meta,
        should_show_question=should_show_question,
        step_key=step.step_key if step is not None else None,
    )
    if step is None or not step.questions:
        return {
            "visible_questions": [],
            "answers": answers,
            "answer_meta": answer_meta,
            "answered_lookup": {},
            "step_status": step_status,
        }

    visible_questions = [
        question
        for question in step.questions
        if should_show_question(question, answers, answer_meta, step.step_key)
    ]
    return {
        "visible_questions": visible_questions,
        "answers": answers,
        "answer_meta": answer_meta,
        "answered_lookup": build_answered_lookup(
            visible_questions, answers, answer_meta
        ),
        "step_status": step_status,
    }


def render_standard_step_review(step: QuestionStep | None) -> None:
    if step is None or not step.questions:
        return
    review_payload = build_step_review_payload(step)
    render_step_review_card(
        step=step,
        visible_questions=review_payload["visible_questions"],
        answers=review_payload["answers"],
        answer_meta=review_payload["answer_meta"],
        answered_lookup=review_payload["answered_lookup"],
        step_status=review_payload["step_status"],
    )


def render_recruiting_consistency_checklist(
    *,
    title: str,
    checks: Sequence[tuple[str, bool]],
    caption: str = "Kurzcheck vor dem Weitergehen",
) -> None:
    """Render a concise, state-derived readiness checklist for recruiting consistency."""

    compact_checks = [
        (label.strip(), is_ok) for label, is_ok in checks if label.strip()
    ]
    if not compact_checks:
        return

    st.markdown(f"#### {title}")
    st.caption(caption)
    for label, is_ok in compact_checks:
        token = "✅" if is_ok else "⬜"
        st.write(f"- {token} {label}")


def has_answered_question_with_keywords(
    *,
    questions: Sequence[Question],
    answered_lookup: dict[str, bool],
    keywords: Sequence[str],
) -> bool:
    """Return True if a visible question matching any keyword is answered."""

    normalized_keywords = tuple(
        keyword.strip().casefold() for keyword in keywords if keyword.strip()
    )
    if not normalized_keywords:
        return False

    for question in questions:
        question_label = question.label.strip().casefold()
        if not question_label:
            continue
        if any(keyword in question_label for keyword in normalized_keywords):
            if answered_lookup.get(question.id, False):
                return True
    return False


def _normalize_esco_explainability_label(label: str) -> str:
    normalized = " ".join(str(label or "").strip().casefold().split())
    legacy_to_canonical = {
        "matched from jobspec title": "exact label match",
        "matched from synonyms/hidden terms": "synonym/hidden-term match",
        "manual override": "manually selected by user",
        "manual selection": "manually selected by user",
        "label_exact": "exact label match",
    }
    return legacy_to_canonical.get(normalized, normalized)


def _normalize_esco_confidence(confidence: str) -> str:
    normalized = str(confidence or "").strip().lower()
    return normalized if normalized in ESCO_CONFIDENCE_BUCKETS else "low"


def render_esco_explainability(
    *,
    labels: Sequence[str],
    confidence: str,
    reason: str | None = None,
    caption_prefix: str = "ESCO Explainability",
) -> None:
    normalized_labels: list[str] = []
    seen: set[str] = set()
    for label in labels:
        canonical = _normalize_esco_explainability_label(label)
        if canonical in ESCO_EXPLAINABILITY_LABELS and canonical not in seen:
            normalized_labels.append(canonical)
            seen.add(canonical)
    normalized_confidence = _normalize_esco_confidence(confidence)
    if not normalized_labels and not reason:
        return
    badge_html = " ".join(
        (
            f"<span style='display:inline-block;padding:0.15rem 0.45rem;border-radius:0.6rem;"
            "border:1px solid #d1d5db;font-size:0.78rem;'>"
            f"{badge}</span>"
        )
        for badge in (
            [f"Confidence: {normalized_confidence.title()}"]
            + [label.title() for label in normalized_labels]
        )
    )
    if badge_html:
        st.markdown(badge_html, unsafe_allow_html=True)
    if reason:
        st.caption(f"{caption_prefix}: {reason}")


_OTHER_OPTION = "Sonstiges"
_OTHER_PREFIX = f"{_OTHER_OPTION}: "
_LANGUAGE_OPTIONS = [
    "Deutsch",
    "Englisch",
    "Französisch",
    "Spanisch",
    "Italienisch",
    "Niederländisch",
    "Polnisch",
    "Portugiesisch",
]
_CEFR_OPTIONS = ["A1", "A2", "B1", "B2", "C1", "C2"]


def _question_option_entries(question: Question) -> list[tuple[str, str]]:
    label_map = question_option_label_map(question)
    entries: list[tuple[str, str]] = []
    used_labels: set[str] = set()
    for raw_option in question.options or []:
        if isinstance(raw_option, QuestionOption):
            option_value = raw_option.value.strip()
        else:
            option_value = str(raw_option).strip()
        if not option_value:
            continue
        option_label = label_map.get(option_value, option_value).strip() or option_value
        deduped_label = option_label
        if deduped_label in used_labels:
            deduped_label = f"{option_label} ({option_value})"
        used_labels.add(deduped_label)
        entries.append((option_value, deduped_label))
    return entries


def _set_session_flag_true(flag_key: str) -> None:
    st.session_state[flag_key] = True


def _normalize_target_state_key(target_state_key: SSKey | str) -> str:
    if isinstance(target_state_key, SSKey):
        return target_state_key.value
    return str(target_state_key).strip()


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
            type_raw = node.get("type") or concept_type
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
    return [item for item in collected if item["type"] == concept_type]


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
) -> None:
    concept_uri = str(concept.get("uri") or "").strip()
    concept_title = str(concept.get("title") or "—").strip()

    expander_key = f"{session_key}.esco_picker.taxonomy.open.{concept_id}"
    fetch_key = f"{session_key}.esco_picker.taxonomy.fetch.{concept_id}"
    cache_key = f"{session_key}.esco_picker.taxonomy.cache.{concept_id}"
    loaded_key = f"{session_key}.esco_picker.taxonomy.loaded.{concept_id}"
    error_key = f"{session_key}.esco_picker.taxonomy.error.{concept_id}"
    uri_key = f"{session_key}.esco_picker.taxonomy.uri.{concept_id}"

    with st.expander(
        "Taxonomie/Breadcrumb", expanded=bool(st.session_state.get(expander_key, False))
    ):
        st.session_state[expander_key] = True

        cache_hit_for_uri = st.session_state.get(uri_key) == concept_uri
        if not cache_hit_for_uri:
            st.session_state.pop(cache_key, None)
            st.session_state.pop(error_key, None)
            st.session_state[loaded_key] = False
            st.session_state[uri_key] = concept_uri

        if st.button("Taxonomie laden", key=fetch_key):
            if not concept_uri:
                st.session_state[error_key] = "ESCO-URI fehlt für dieses Konzept."
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
            st.warning(f"Taxonomie konnte nicht geladen werden: {fetch_error}")
            return

        if not cached_nodes:
            if bool(st.session_state.get(loaded_key, False)):
                st.caption(
                    "Keine übergeordnete Relation (`hasBroaderTransitive`) für dieses ESCO-Konzept gefunden."
                )
                return
            st.caption(
                "Keine Taxonomie geladen. Öffne den Expander und klicke auf „Taxonomie laden“."
            )
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
            st.caption(
                "Keine übergeordnete Taxonomie für dieses ESCO-Konzept verfügbar."
            )
            return

        st.write(" → ".join(titles))


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
) -> None:
    session_key = _normalize_target_state_key(target_state_key)
    if not session_key:
        st.error("ESCO-Picker-Konfiguration ist ungültig (fehlender target_state_key).")
        return

    base_key = f"{session_key}.esco_picker"
    query_key = f"{base_key}.query"
    submit_flag_key = f"{base_key}.submit_enter"
    options_state_key = f"{base_key}.options"
    selected_key = f"{base_key}.selected"
    preview_key = f"{base_key}.preview"
    applied_meta_key = f"{base_key}.applied_meta"
    apply_button_key = f"{base_key}.apply"

    ui_mode = str(st.session_state.get(SSKey.UI_MODE.value, "standard")).strip().lower()
    if ui_mode not in {"quick", "standard", "expert"}:
        ui_mode = "standard"

    query_text = st.text_input(
        "ESCO Suche",
        key=query_key,
        placeholder="Begriff eingeben (z. B. Data Engineer)",
        on_change=_set_session_flag_true,
        args=(submit_flag_key,),
    ).strip()

    suggestions: list[dict[str, str]] = []
    if len(query_text) >= 2:
        client = EscoClient()
        try:
            suggestions = _extract_esco_suggestions(
                client.suggest2(text=query_text, type=concept_type, limit=12),
                concept_type=concept_type,
                source="auto",
            )
            if not suggestions:
                suggestions = _extract_esco_suggestions(
                    client.terms(text=query_text, type=concept_type, limit=12),
                    concept_type=concept_type,
                    source="manual",
                )
        except EscoClientError as exc:
            st.warning(f"ESCO-Suche aktuell nicht verfügbar: {exc}")

    st.session_state[options_state_key] = suggestions
    options = st.session_state.get(options_state_key, [])
    options = options if isinstance(options, list) else []

    def _label_for_option(item: dict[str, str]) -> str:
        title = item.get("title", "—")
        if ui_mode == "expert":
            return f"{title} · {item.get('uri', '—')} · {item.get('source', 'auto')}"
        return title

    option_labels = [_label_for_option(item) for item in options]
    selected_payload: list[dict[str, str]] = []
    selected_index: int | None = None
    if allow_multi:
        resolved_selection_label = selection_label or "Vorschläge"
        selected_indices = st.multiselect(
            resolved_selection_label,
            options=list(range(len(options))),
            format_func=lambda idx: option_labels[idx],
            key=selected_key,
        )
        selected_payload = [
            options[idx] for idx in selected_indices if idx < len(options)
        ]
    else:
        resolved_selection_label = selection_label or "Top-Vorschlag auswählen"
        selected_index = st.selectbox(
            resolved_selection_label,
            options=list(range(len(options))),
            format_func=lambda idx: option_labels[idx],
            index=0 if options else None,
            key=selected_key,
            placeholder="Keine Vorschläge verfügbar",
        )
        if selected_index is not None and selected_index < len(options):
            selected_payload = [options[selected_index]]

    enter_submit = bool(st.session_state.get(submit_flag_key, False))
    if enter_submit:
        st.session_state[submit_flag_key] = False
        if options:
            selected_payload = [options[0]] if not allow_multi else selected_payload
            st.info("Top-Treffer wurde per Enter übernommen.")

    if enable_preview:
        resolved_preview_label = preview_label or "Preview vor Apply"
        with st.expander(
            resolved_preview_label,
            expanded=bool(st.session_state.get(preview_key, False)),
        ):
            st.session_state[preview_key] = True
            if not selected_payload:
                st.caption("Noch keine Vorschläge ausgewählt.")
            else:
                st.markdown(
                    "**Inferred suggestion/context preview (not user-confirmed):**"
                )
                for concept in selected_payload:
                    if ui_mode == "expert":
                        st.caption(
                            f"{concept.get('title', '—')} · URI: {concept.get('uri', '—')} · Quelle: {concept.get('source', 'auto')}"
                        )
                    else:
                        st.write(f"- {concept.get('title', '—')}")

    if confirmation_helper_text:
        st.caption(confirmation_helper_text)

    resolved_apply_label = apply_label or "Apply"
    if st.button(resolved_apply_label, key=apply_button_key) or (
        enter_submit and bool(options)
    ):
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
            st.warning("Auswahl konnte nicht validiert werden. Bitte erneut auswählen.")
            return

        if allow_multi:
            st.session_state[session_key] = validated
        else:
            st.session_state[session_key] = validated[0] if validated else None
        if session_key == SSKey.ESCO_OCCUPATION_SELECTED.value:
            st.session_state[SSKey.ESCO_SELECTED_OCCUPATION_URI.value] = (
                str(validated[0].get("uri") or "").strip() if validated else ""
            )

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

    if not current_entries:
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

    st.markdown("**Confirmed selection · ESCO concepts**")
    for idx, concept in enumerate(current_entries):
        concept_id = _build_esco_concept_id(concept, idx)
        if ui_mode == "expert":
            st.caption(
                f"{concept['title']} · URI: {concept['uri']} · Version: {version} · Quelle: {source}"
            )
        else:
            st.write(f"- {concept['title']}")
        _render_esco_taxonomy_breadcrumb(
            session_key=session_key,
            concept=concept,
            concept_id=concept_id,
        )


def render_error_banner() -> None:
    err = st.session_state.get(SSKey.LAST_ERROR.value)
    if err:
        st.error(err)
    debug_err = st.session_state.get(SSKey.LAST_ERROR_DEBUG.value)
    if debug_err and bool(st.session_state.get(SSKey.OPENAI_DEBUG_ERRORS.value, False)):
        with st.expander("Debug (non-sensitive)", expanded=False):
            st.caption("Nur technische Metadaten, keine Inhalte (kein Prompt/PII).")
            st.code(str(debug_err))


def render_openai_error(error: OpenAICallError) -> None:
    """Persist concise user message and optional non-sensitive debug details."""

    set_error(error.ui_message)
    st.session_state[SSKey.LAST_ERROR_DEBUG.value] = None
    if bool(st.session_state.get(SSKey.OPENAI_DEBUG_ERRORS.value, False)):
        details: list[str] = ["type=OpenAICallError", "step=llm_call"]
        if error.error_code:
            details.insert(0, f"code={error.error_code}")
        st.session_state[SSKey.LAST_ERROR_DEBUG.value] = " | ".join(details)


def render_job_extract_overview(
    job: JobAdExtract,
    plan: QuestionPlan | None = None,
    show_question_limits: bool = True,
) -> None:
    st.markdown("### Identifizierte Informationen")
    _render_editable_job_extract(job)

    st.markdown("### Fehlende oder unklare Punkte")
    if job.gaps:
        st.write("\n".join([f"- {g}" for g in job.gaps]))
    else:
        st.info("Keine expliziten Gaps erkannt.")

    if show_question_limits:
        _render_question_limits_editor(plan)

    st.markdown("### Annahmen")
    if job.assumptions:
        st.write("\n".join([f"- {a}" for a in job.assumptions]))
    else:
        st.info("Keine Annahmen dokumentiert.")


def _render_compact_extract_lists(job: JobAdExtract) -> None:
    st.caption(
        "Kompaktansicht für lange Listen. Gezeigt werden zunächst die Top 5 Einträge."
    )
    _render_compact_list_table(
        label="Responsibilities",
        entries=job.responsibilities,
        key="cs.job_extract.preview.responsibilities",
    )
    _render_compact_list_table(
        label="Must-have Skills",
        entries=job.must_have_skills,
        key="cs.job_extract.preview.must_have_skills",
    )
    _render_compact_list_table(
        label="Nice-to-have Skills",
        entries=job.nice_to_have_skills,
        key="cs.job_extract.preview.nice_to_have_skills",
    )


def _render_compact_list_table(*, label: str, entries: Any, key: str) -> None:
    source = entries if isinstance(entries, list) else []
    cleaned = [str(item).strip() for item in source if has_meaningful_value(item)]
    if not cleaned:
        return

    st.markdown(f"**{label}**")
    top_five = cleaned[:5]
    st.table(
        [{"#": index + 1, "Eintrag": value} for index, value in enumerate(top_five)]
    )
    remaining = len(cleaned) - len(top_five)
    if remaining <= 0:
        return
    with st.expander(f"Alle {len(cleaned)} Einträge anzeigen", expanded=False):
        st.dataframe(
            [{"#": index + 1, "Eintrag": value} for index, value in enumerate(cleaned)],
            key=key,
            hide_index=True,
            width="stretch",
        )


def _render_editable_job_extract(job: JobAdExtract) -> None:
    st.caption(
        "Extrahierte Werte können hier direkt angepasst werden. Änderungen werden sofort gespeichert."
    )
    values = _sanitize_display_value(job.model_dump())

    core_fields = [
        "job_title",
        "company_name",
        "brand_name",
        "language_guess",
        "employment_type",
        "contract_type",
        "seniority_level",
        "start_date",
        "application_deadline",
        "job_ref_number",
        "department_name",
        "reports_to",
    ]
    location_fields = [
        "location_city",
        "location_country",
        "place_of_work",
        "remote_policy",
        "travel_required",
        "on_call",
        "direct_reports_count",
    ]
    text_fields = ["role_overview", "onboarding_notes"]
    list_fields = [
        ("responsibilities", "Responsibilities"),
        ("deliverables", "Deliverables"),
        ("success_metrics", "Success Metrics"),
        ("must_have_skills", "Must-have Skills"),
        ("nice_to_have_skills", "Nice-to-have Skills"),
        ("soft_skills", "Soft Skills"),
        ("education", "Education"),
        ("certifications", "Certifications"),
        ("languages", "Languages"),
        ("tech_stack", "Tech Stack"),
        ("domain_expertise", "Domain Expertise"),
        ("benefits", "Benefits"),
    ]

    tab_core, tab_location, tab_role, tab_skills, tab_process = st.tabs(
        ["Basis", "Standort", "Rolle", "Skills & Benefits", "Prozess"]
    )

    with tab_core:
        core_rows = [
            {"field": field, "value": values.get(field)}
            for field in core_fields
            if field in values and has_meaningful_value(values.get(field))
        ]
        if core_rows:
            core_edit = st.data_editor(
                core_rows,
                key="cs.job_extract.core",
                width="stretch",
                hide_index=True,
                num_rows="fixed",
                column_config={
                    "field": st.column_config.TextColumn("Feld", disabled=True),
                    "value": st.column_config.TextColumn("Wert"),
                },
            )
            for row in core_edit:
                field = str(row.get("field", "")).strip()
                if field:
                    values[field] = _normalize_optional_string(row.get("value"))
        else:
            st.info("Keine extrahierten Basiswerte mit Inhalt vorhanden.")

    with tab_location:
        location_rows = [
            {"field": field, "value": values.get(field)}
            for field in location_fields
            if field in values and has_meaningful_value(values.get(field))
        ]
        if location_rows:
            location_edit = st.data_editor(
                location_rows,
                key="cs.job_extract.location",
                width="stretch",
                hide_index=True,
                num_rows="fixed",
                column_config={
                    "field": st.column_config.TextColumn("Feld", disabled=True),
                    "value": st.column_config.TextColumn("Wert"),
                },
            )
            for row in location_edit:
                field = str(row.get("field", "")).strip()
                if not field:
                    continue
                if field == "direct_reports_count":
                    values[field] = _parse_optional_int(row.get("value"))
                else:
                    values[field] = _normalize_optional_string(row.get("value"))
        else:
            st.info("Keine extrahierten Standort-/Org-Werte mit Inhalt vorhanden.")

    with tab_role:
        for field in text_fields:
            if has_meaningful_value(values.get(field)):
                values[field] = (
                    st.text_area(
                        field.replace("_", " ").title(),
                        value=(values.get(field) or ""),
                        key=f"cs.job_extract.text.{field}",
                        height=130,
                    )
                    or None
                )
        for list_field, label in list_fields[:3]:
            values[list_field] = _render_list_editor(
                label=label,
                key=f"cs.job_extract.list.{list_field}",
                entries=values.get(list_field, []),
            )

    with tab_skills:
        for list_field, label in list_fields[3:]:
            values[list_field] = _render_list_editor(
                label=label,
                key=f"cs.job_extract.list.{list_field}",
                entries=values.get(list_field, []),
            )
        values["salary_range"] = _render_salary_editor(values.get("salary_range"))

    with tab_process:
        values["recruitment_steps"] = _render_recruitment_steps_editor(
            values.get("recruitment_steps", [])
        )
        values["contacts"] = _render_contacts_editor(values.get("contacts", []))

    try:
        validated = JobAdExtract.model_validate(values)
    except Exception:
        st.warning(
            "Einige Eingaben sind ungültig und wurden nicht übernommen. Bitte Felder prüfen."
        )
        return
    st.session_state[SSKey.JOB_EXTRACT.value] = validated.model_dump()


def _suggested_question_limit(step: QuestionStep) -> int:
    required_count = sum(1 for question in step.questions if question.required)
    return required_count if required_count > 0 else len(step.questions)


def _render_question_limits_editor(
    plan: QuestionPlan | None, compact: bool = False
) -> None:
    if plan is None or not plan.steps:
        return

    heading = "##### Fragen pro Step" if compact else "#### Fragen pro Step"
    st.markdown(heading)
    st.caption(
        "Wird automatisch aus Informationsgrad + Ansichtsmodus berechnet "
        f"({UI_DETAILS_DEFAULT_BY_MODE_TEXT})"
    )

    limits_raw = st.session_state.get(SSKey.QUESTION_LIMITS.value, {})
    limits: dict[str, int] = {}
    if isinstance(limits_raw, dict):
        for key, value in limits_raw.items():
            try:
                limits[str(key)] = int(value)
            except (TypeError, ValueError):
                continue

    for step in plan.steps:
        if not step.questions:
            continue
        fallback = max(1, _suggested_question_limit(step))
        current = limits.get(step.step_key, fallback)
        current = max(1, min(current, len(step.questions)))
        selected = st.number_input(
            f"{step.title_de} ({step.step_key})",
            min_value=1,
            max_value=len(step.questions),
            value=current,
            step=1,
            key=f"cs.question_limit.{step.step_key}",
            disabled=True,
            help=f"Maximal {len(step.questions)} verfügbare Fragen in diesem Step.",
        )
        limits[step.step_key] = int(selected)

    st.session_state[SSKey.QUESTION_LIMITS.value] = limits


def _normalize_optional_string(value: Any) -> str | None:
    if not has_meaningful_value(value):
        return None
    text = str(value).strip()
    return text or None


def has_meaningful_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, float):
        return not value != value

    text = str(value).strip()
    if not text:
        return False
    lowered = text.lower()
    return lowered not in {"nan", "none", "null", "n/a", "na", "-", "—"}


def _sanitize_display_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _sanitize_display_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [
            v
            for item in value
            for v in [_sanitize_display_value(item)]
            if v is not None
        ]
    return value if has_meaningful_value(value) else None


def _parse_optional_int(value: Any) -> int | None:
    normalized = _normalize_optional_string(value)
    if normalized is None:
        return None
    try:
        return int(float(normalized))
    except ValueError:
        return None


def _render_list_editor(*, label: str, key: str, entries: Any) -> list[str]:
    source = entries if isinstance(entries, list) else []
    rows = [{"value": str(item)} for item in source if has_meaningful_value(item)]
    edited_rows = st.data_editor(
        rows,
        key=key,
        width="stretch",
        hide_index=True,
        num_rows="dynamic",
        column_config={"value": st.column_config.TextColumn(label)},
    )
    return [
        value
        for row in edited_rows
        for value in [_normalize_optional_string(row.get("value"))]
        if value
    ]


def _render_salary_editor(salary_data: Any) -> dict[str, Any] | None:
    salary = MoneyRange.model_validate(salary_data or {}).model_dump()
    salary_rows = [
        {"field": field, "value": salary.get(field)}
        for field in ("min", "max", "currency", "period", "notes")
        if has_meaningful_value(salary.get(field))
    ]
    if not salary_rows:
        return None
    edited = st.data_editor(
        salary_rows,
        key="cs.job_extract.salary",
        width="stretch",
        hide_index=True,
        num_rows="fixed",
        column_config={
            "field": st.column_config.TextColumn("Salary Feld", disabled=True),
            "value": st.column_config.TextColumn("Wert"),
        },
    )
    result: dict[str, Any] = {}
    for row in edited:
        field = str(row.get("field", "")).strip()
        if not field:
            continue
        raw = row.get("value")
        if field in {"min", "max"}:
            normalized = _normalize_optional_string(raw)
            if normalized is None:
                result[field] = None
            else:
                try:
                    result[field] = float(normalized)
                except ValueError:
                    result[field] = None
        else:
            result[field] = _normalize_optional_string(raw)
    if not any(v is not None for v in result.values()):
        return None
    return MoneyRange.model_validate(result).model_dump()


def _render_recruitment_steps_editor(steps_data: Any) -> list[dict[str, Any]]:
    source = steps_data if isinstance(steps_data, list) else []
    rows = []
    for item in source:
        step = RecruitmentStep.model_validate(item)
        if not has_meaningful_value(step.name):
            continue
        rows.append({"name": step.name, "details": step.details})
    edited = st.data_editor(
        rows,
        key="cs.job_extract.recruitment_steps",
        width="stretch",
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "name": st.column_config.TextColumn("Schritt"),
            "details": st.column_config.TextColumn("Details"),
        },
    )
    result: list[dict[str, Any]] = []
    for row in edited:
        name = _normalize_optional_string(row.get("name"))
        if not name:
            continue
        result.append(
            RecruitmentStep(
                name=name,
                details=_normalize_optional_string(row.get("details")),
            ).model_dump()
        )
    return result


def _render_contacts_editor(contacts_data: Any) -> list[dict[str, Any]]:
    source = contacts_data if isinstance(contacts_data, list) else []
    rows = []
    for item in source:
        contact = Contact.model_validate(item)
        if not any(
            has_meaningful_value(value) for value in contact.model_dump().values()
        ):
            continue
        rows.append(
            {
                "name": contact.name,
                "role": contact.role,
                "email": contact.email,
                "phone": contact.phone,
            }
        )
    edited = st.data_editor(
        rows,
        key="cs.job_extract.contacts",
        width="stretch",
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "name": st.column_config.TextColumn("Name"),
            "role": st.column_config.TextColumn("Rolle"),
            "email": st.column_config.TextColumn("E-Mail"),
            "phone": st.column_config.TextColumn("Telefon"),
        },
    )
    result: list[dict[str, Any]] = []
    for row in edited:
        normalized = Contact(
            name=_normalize_optional_string(row.get("name")),
            role=_normalize_optional_string(row.get("role")),
            email=_normalize_optional_string(row.get("email")),
            phone=_normalize_optional_string(row.get("phone")),
        ).model_dump()
        if any(value is not None for value in normalized.values()):
            result.append(normalized)
    return result


def _get_step_group_rules(step_key: str) -> list[tuple[str, tuple[str, ...]]]:
    """Return ordered grouping rules per step for question rendering."""
    rules: dict[str, list[tuple[str, tuple[str, ...]]]] = {
        "company": [
            (
                "Unternehmenskontext & Business",
                (
                    "unterneh",
                    "company",
                    "markt",
                    "business",
                    "produkt",
                    "mission",
                    "strategie",
                ),
            ),
            (
                "Setup, Zusammenarbeit & Rahmen",
                (
                    "team",
                    "stakeholder",
                    "schnittstelle",
                    "zusammenarbeit",
                    "remote",
                    "standort",
                    "rahmen",
                ),
            ),
        ],
        "team": [
            (
                "Teamstruktur & Verantwortungen",
                (
                    "team",
                    "lead",
                    "reports",
                    "verantwort",
                    "rolle",
                    "hierarchie",
                    "organ",
                ),
            ),
            (
                "Arbeitsweise & Zusammenarbeit",
                (
                    "arbeits",
                    "hybrid",
                    "remote",
                    "schnittstelle",
                    "kommunikation",
                    "prozesse",
                    "kultur",
                ),
            ),
        ],
        "role_tasks": [
            (
                "Scope, Aufgaben & Deliverables",
                (
                    "aufgabe",
                    "scope",
                    "deliver",
                    "projekt",
                    "verantwort",
                    "ergebnis",
                ),
            ),
            (
                "Erfolgskriterien & Stakeholder",
                (
                    "erfolg",
                    "kpi",
                    "ziel",
                    "stakeholder",
                    "entscheidung",
                    "prior",
                ),
            ),
        ],
        "skills": [
            (
                "Must-have & Fachkompetenz",
                (
                    "must",
                    "pflicht",
                    "skill",
                    "tech",
                    "tool",
                    "erfahrung",
                    "expertise",
                ),
            ),
            (
                "Nice-to-have & Entwicklungsfelder",
                (
                    "nice",
                    "optional",
                    "plus",
                    "lernen",
                    "potenzial",
                    "entwicklung",
                    "soft",
                ),
            ),
        ],
        "benefits": [
            (
                "Kompensation & Vertragsrahmen",
                (
                    "gehalt",
                    "salary",
                    "bonus",
                    "vertrag",
                    "arbeitszeit",
                    "stunden",
                    "kondition",
                ),
            ),
            (
                "Benefits, Flexibilität & Entwicklung",
                (
                    "benefit",
                    "remote",
                    "hybrid",
                    "urlaub",
                    "learning",
                    "relocation",
                    "flex",
                ),
            ),
        ],
        "interview": [
            (
                "Interne Ansprechpartner & Prozesssteuerung",
                (
                    "ansprech",
                    "hiring manager",
                    "recruit",
                    "intern",
                    "entscheidung",
                    "freigabe",
                    "prozess",
                ),
            ),
            (
                "Kandidaten-Inputs & Deliverables",
                (
                    "cv",
                    "lebenslauf",
                    "portfolio",
                    "gehalt",
                    "case",
                    "unterlage",
                    "deliver",
                ),
            ),
            (
                "Bewerbungsschritte, Timeline & Kommunikation",
                (
                    "schritt",
                    "interview",
                    "timeline",
                    "stufe",
                    "feedback",
                    "termin",
                    "kommunikation",
                ),
            ),
        ],
    }
    return rules.get(step_key, [])


def _matches_keywords(question: Question, keywords: Sequence[str]) -> bool:
    haystack = " ".join(
        [
            (question.id or ""),
            (question.label or ""),
            (question.help or ""),
            (question.rationale or ""),
        ]
    ).lower()
    return any(keyword.lower() in haystack for keyword in keywords)


def _group_questions(
    step: QuestionStep, questions: list[Question]
) -> list[tuple[str, list[Question]]]:
    explicit_groups: dict[str, list[Question]] = {}
    explicit_order: list[str] = []
    heuristic_candidates: list[Question] = []
    for question in questions:
        if question.group_key:
            key = question.group_key.strip()
            if key:
                if key not in explicit_groups:
                    explicit_groups[key] = []
                    explicit_order.append(key)
                explicit_groups[key].append(question)
                continue
        heuristic_candidates.append(question)

    grouped: list[tuple[str, list[Question]]] = []
    for key in explicit_order:
        grouped.append((key.replace("_", " ").title(), explicit_groups[key]))

    remaining = heuristic_candidates[:]
    for group_title, keywords in _get_step_group_rules(step.step_key):
        matched = [q for q in remaining if _matches_keywords(q, keywords)]
        if matched:
            grouped.append((group_title, matched))
            remaining = [q for q in remaining if q not in matched]
    if remaining:
        grouped.append(("Weitere Fragen", remaining))
    return grouped


def _render_questions_two_columns(
    questions: list[Question], answers: Dict[str, Any]
) -> None:
    col_left, col_right = st.columns(2, gap="large")
    for index, question in enumerate(questions):
        target_col = col_left if index % 2 == 0 else col_right
        with target_col:
            _render_question(question, answers)


def _split_core_and_detail_questions(
    questions: list[Question],
) -> tuple[list[Question], list[Question]]:
    max_core_questions = 4
    if not questions:
        return [], []

    core_questions: list[Question] = []
    essential_questions = [
        question
        for question in questions
        if question.priority == "core" or question.required
    ]

    for question in essential_questions:
        if question in core_questions:
            continue
        core_questions.append(question)
        if len(core_questions) >= max_core_questions:
            break

    for question in questions:
        if len(core_questions) >= max_core_questions:
            break
        if question in core_questions:
            continue
        core_questions.append(question)

    detail_questions = [
        question for question in questions if question not in core_questions
    ]
    return core_questions, detail_questions


def render_question_step(step: QuestionStep) -> None:
    answers = get_answers()
    answer_meta = get_answer_meta()
    ui_mode_raw = st.session_state.get(SSKey.UI_MODE.value, "standard")
    ui_mode = str(ui_mode_raw).strip().lower()
    if ui_mode not in {"quick", "standard", "expert"}:
        ui_mode = "standard"
        st.session_state[SSKey.UI_MODE.value] = ui_mode

    if step.description_de:
        st.caption(step.description_de)

    limits_raw = st.session_state.get(SSKey.QUESTION_LIMITS.value, {})
    step_limit: int | None = None
    if isinstance(limits_raw, dict):
        raw_limit = limits_raw.get(step.step_key)
        if isinstance(raw_limit, (int, float, str)):
            try:
                step_limit = int(raw_limit)
            except ValueError:
                step_limit = None

    questions = _sort_questions_for_progressive_disclosure(step.questions)
    if step_limit is not None and step_limit > 0:
        questions = questions[:step_limit]
    visible_questions = [
        question
        for question in questions
        if should_show_question(question, answers, answer_meta, step.step_key)
    ]
    hidden_questions_count = len(questions) - len(visible_questions)

    core_questions, detail_questions = _split_core_and_detail_questions(
        visible_questions
    )
    answered_lookup = build_answered_lookup(visible_questions, answers, answer_meta)
    core_progress = compute_question_progress(
        core_questions, answers, answer_meta, answered_lookup=answered_lookup
    )
    detail_progress = compute_question_progress(
        detail_questions, answers, answer_meta, answered_lookup=answered_lookup
    )
    visible_progress = compute_question_progress(
        visible_questions, answers, answer_meta, answered_lookup=answered_lookup
    )
    overall_answered_lookup = build_answered_lookup(questions, answers, answer_meta)
    overall_progress = compute_question_progress(
        questions,
        answers,
        answer_meta,
        answered_lookup=overall_answered_lookup,
    )
    scope_labels = build_step_scope_progress_labels(
        visible_answered=visible_progress["answered"],
        visible_total=visible_progress["total"],
        overall_answered=overall_progress["answered"],
        overall_total=overall_progress["total"],
    )

    st.caption(
        "Minimalprofil "
        f"{core_progress['answered']}/{core_progress['total']} beantwortet"
        " · Details "
        f"{detail_progress['answered']}/{detail_progress['total']} beantwortet"
    )
    st.caption(scope_labels["visible_label"])
    if scope_labels["has_different_denominator"]:
        st.caption(scope_labels["overall_label"])

    st.markdown("#### Minimalprofil")
    st.caption(
        "Starte mit den wichtigsten Fragen. Weitere Details kannst du unten ergänzen."
    )
    if ui_mode == "expert" and hidden_questions_count > 0:
        st.caption("Weitere Detailfragen erscheinen nach relevanten Antworten.")
    core_layout_columns = 2 if len(core_questions) > 1 else 1
    if core_layout_columns == 2:
        _render_questions_two_columns(core_questions, answers)
    else:
        for question in core_questions:
            _render_question(question, answers)

    if not visible_questions:
        st.info(
            "Aktuell sind keine Fragen sichtbar. Prüfe vorherige Antworten oder fahre mit dem nächsten Schritt fort."
        )
        if hidden_questions_count > 0:
            st.caption(
                f"{hidden_questions_count} Detailfragen sind aktuell durch Abhängigkeiten ausgeblendet."
            )
    elif not detail_questions:
        return

    grouped_questions = _group_questions(step, detail_questions)
    global_details_expanded_default = _get_global_details_expanded_default(
        ui_mode=ui_mode
    )
    details_compact = _get_step_compact_preference(
        step_key=step.step_key,
        fallback_compact=not global_details_expanded_default,
    )
    details_expanded_default = not details_compact
    _ensure_step_group_state(
        step.step_key,
        grouped_questions,
        default_open=details_expanded_default,
    )
    details_compact = st.toggle(
        UI_STEP_COMPACT_TOGGLE_LABEL,
        value=details_compact,
        key=f"cs.details_compact.{step.step_key}",
        help=UI_STEP_COMPACT_TOGGLE_HELP,
    )
    _set_step_compact_preference(step_key=step.step_key, compact=details_compact)
    details_expanded_default = not details_compact

    incomplete_groups = _collect_incomplete_group_titles(
        grouped_questions, answers, answer_meta, answered_lookup
    )
    if incomplete_groups:
        st.caption(
            "Pflichtfragen offen in: " + ", ".join(dict.fromkeys(incomplete_groups))
        )

    st.markdown("#### Details")
    for group_title, group_questions in grouped_questions:
        progress = compute_question_progress(
            group_questions,
            answers,
            answer_meta,
            answered_lookup=answered_lookup,
        )
        header = (
            f"{group_title} · {progress['answered']}/{progress['total']} beantwortet"
        )
        expanded = _is_group_open(
            step_key=step.step_key,
            group_title=group_title,
            default_open=details_expanded_default,
        )
        with st.expander(header, expanded=expanded):
            if progress["required_unanswered"] > 0:
                st.caption(f"{progress['required_unanswered']} Pflichtfragen offen")
            _render_questions_two_columns(group_questions, answers)

    return


def _sort_questions_for_progressive_disclosure(
    questions: list[Question],
) -> list[Question]:
    priority_rank = {"core": 0, "standard": 1, "detail": 2}
    return sorted(
        questions,
        key=lambda question: (
            priority_rank.get(question.priority or "", 1),
            question.id,
        ),
    )


def render_step_review_card(
    step: QuestionStep,
    visible_questions: list[Question],
    answers: Dict[str, Any],
    answer_meta: dict[str, Any],
    answered_lookup: dict[str, bool] | None = None,
    step_status: StepStatusPayload | None = None,
) -> None:
    if not visible_questions:
        with st.container(border=True):
            st.markdown("#### ✅ Check answers")
            st.caption("Keine sichtbaren Fragen in diesem Schritt.")
            st.caption(
                "Hinweis: Abhängigkeiten können Detailfragen ausblenden, bis die vorausgesetzten Antworten gesetzt sind."
            )
        return

    grouped_questions = _group_questions(step, visible_questions)
    group_payload: list[tuple[str, list[tuple[str, str]]]] = []
    missing_essential_labels = (
        list(step_status["missing_essentials"]) if step_status else []
    )
    incomplete_group_titles: list[str] = []

    resolved_lookup = answered_lookup or build_answered_lookup(
        visible_questions, answers, answer_meta
    )

    for group_title, group_questions in grouped_questions:
        answered_items: list[tuple[str, str]] = []
        group_missing_essential = False
        for question in group_questions:
            if not resolved_lookup.get(question.id, False):
                if question.label in missing_essential_labels:
                    group_missing_essential = True
                continue
            value = answers.get(question.id)
            formatted = _format_answer_for_review(question, value)
            if formatted:
                answered_items.append((question.label, formatted))

        if answered_items:
            group_payload.append((group_title, answered_items))
        if group_missing_essential:
            incomplete_group_titles.append(group_title)

    with st.container(border=True):
        st.markdown("#### ✅ Check answers")
        if not group_payload and not missing_essential_labels:
            st.caption("Noch keine sichtbaren Antworten vorhanden.")
            return

        if missing_essential_labels:
            missing_groups = ", ".join(dict.fromkeys(incomplete_group_titles))
            st.warning(
                f"Essentials offen ({len(missing_essential_labels)}): "
                f"Bitte in diesen Bereichen ergänzen: {missing_groups}."
            )
            if grouped_questions and incomplete_group_titles:
                st.caption(
                    "Hinweis: Bitte prüfe zuerst die Bereiche "
                    f"{', '.join(dict.fromkeys(incomplete_group_titles))}."
                )

        for group_title, answered_items in group_payload:
            st.caption(group_title)
            for label, formatted_value in answered_items:
                st.markdown(f"- **{label}:** {formatted_value}")


def _normalize_requirement_label(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def _truncate_requirement_label(value: str, *, limit: int = 88) -> str:
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return f"{text[: max(limit - 1, 1)].rstrip()}…"


def _build_requirement_table_rows(
    *,
    source_key: str,
    entries: list[dict[str, Any]],
    selected_set: set[str],
    buffer_set: set[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in entries:
        label = str(entry.get("label") or "").strip()
        if not label:
            continue
        normalized = _normalize_requirement_label(label)
        importance = str(entry.get("importance") or "").strip()
        note_parts = [
            importance,
            str(entry.get("rationale") or "").strip(),
            str(entry.get("evidence") or "").strip(),
        ]
        notes = " | ".join(part for part in note_parts if part)
        rows.append(
            {
                "select": normalized in selected_set or normalized in buffer_set,
                "label": _truncate_requirement_label(label),
                "source": source_key,
                "notes": _truncate_requirement_label(notes, limit=120) if notes else "",
                "_full_label": label,
                "_normalized_label": normalized,
                "_importance": importance,
            }
        )
    return rows


def _is_high_importance(importance: str) -> bool:
    normalized = _normalize_requirement_label(importance)
    if not normalized:
        return False
    high_markers = {
        "hoch",
        "high",
        "sehr hoch",
        "very high",
        "critical",
        "kritisch",
    }
    return normalized in high_markers


def _render_requirement_selection_table(
    *,
    title: str,
    source_key: str,
    entries: list[dict[str, Any]],
    selected_set: set[str],
    selection_state_key: str,
    key_prefix: str,
) -> list[str]:
    table_rows = _build_requirement_table_rows(
        source_key=source_key,
        entries=entries,
        selected_set=selected_set,
        buffer_set={
            _normalize_requirement_label(str(label))
            for label in st.session_state.get(selection_state_key, [])
            if has_meaningful_value(label)
        },
    )
    if not table_rows:
        return []

    st.caption(title)
    filter_key_prefix = f"{key_prefix}.filters.{source_key.casefold()}"
    default_only_new_key = f"{filter_key_prefix}.default_only_new"
    if default_only_new_key not in st.session_state:
        st.session_state[default_only_new_key] = True
    search_term = st.text_input(
        "Suche",
        value="",
        key=f"{filter_key_prefix}.search",
        placeholder="Begriff eingeben…",
        help="Filtert Vorschläge direkt nach Bezeichnung und Hinweisen.",
    ).strip()
    filter_col_new, filter_col_long, filter_col_high = st.columns(3)
    with filter_col_new:
        only_new = st.toggle(
            "Nur neue Vorschläge",
            key=f"{filter_key_prefix}.only_new",
            value=bool(st.session_state.get(default_only_new_key, True)),
        )
    st.session_state[default_only_new_key] = False
    with filter_col_long:
        only_long_items = st.toggle(
            "Nur lange Items",
            key=f"{filter_key_prefix}.only_long",
            value=False,
        )
    with filter_col_high:
        only_ai_high = st.toggle(
            "Nur AI high-importance",
            key=f"{filter_key_prefix}.only_ai_high",
            value=False,
        )

    filtered_rows: list[dict[str, Any]] = []
    normalized_search = _normalize_requirement_label(search_term)
    for row in table_rows:
        if only_new and bool(row.get("select")):
            continue
        if only_long_items and len(str(row.get("_full_label") or "").strip()) < 48:
            continue
        if (
            only_ai_high
            and source_key.casefold() == "ai"
            and not _is_high_importance(str(row.get("_importance") or ""))
        ):
            continue
        if only_ai_high and source_key.casefold() != "ai":
            continue
        if normalized_search:
            haystack = _normalize_requirement_label(
                f"{row.get('_full_label', '')} {row.get('notes', '')}"
            )
            if normalized_search not in haystack:
                continue
        filtered_rows.append(row)

    if not filtered_rows:
        st.caption("Keine Treffer für die aktuellen Filter.")
        return []

    editor_key = f"{key_prefix}.editor.{source_key.casefold()}"
    edited_rows = st.data_editor(
        filtered_rows,
        key=editor_key,
        width="stretch",
        height=320,
        hide_index=True,
        num_rows="fixed",
        column_order=["select", "label", "source", "notes"],
        column_config={
            "select": st.column_config.CheckboxColumn("Auswahl"),
            "label": st.column_config.TextColumn("Bezeichnung", disabled=True),
            "source": st.column_config.TextColumn("Quelle", disabled=True),
            "notes": st.column_config.TextColumn("Hinweise", disabled=True),
        },
    )
    selected_labels: list[str] = []
    for row in edited_rows:
        if not bool(row.get("select")):
            continue
        label = str(row.get("_full_label") or "").strip()
        if label:
            selected_labels.append(label)

    selected_index = next(
        (index for index, row in enumerate(edited_rows) if bool(row.get("select"))), -1
    )
    if selected_index >= 0:
        selected_row = edited_rows[selected_index]
        selected_label = str(selected_row.get("_full_label") or "").strip()
        notes = str(selected_row.get("notes") or "").strip()
        with st.expander("Preview", expanded=False):
            st.write(selected_label or "Keine Details verfügbar.")
            if notes:
                st.caption(notes)
    return selected_labels


def render_compare_adopt_intro(
    *,
    adopt_target: str,
    canonical_target: str,
    source_labels: Sequence[str] = ("Jobspec", "ESCO", "AI"),
    include_inferred_confirmed_note: bool = False,
) -> None:
    badge_html = " ".join(
        (
            "<span style='display:inline-block;padding:0.15rem 0.45rem;border-radius:0.6rem;"
            "border:1px solid #d1d5db;font-size:0.78rem;'>"
            f"{badge}</span>"
        )
        for badge in (
            [f"{'/'.join(source_labels)} = Vorschläge", "Status: inferred context"]
            if source_labels
            else ["Status: inferred context"]
        )
    )
    st.markdown(badge_html, unsafe_allow_html=True)
    st.caption(
        f"Warum nebeneinander? {', '.join(source_labels)} liefern unterschiedliche Perspektiven "
        "auf denselben Bedarf und machen Lücken/Widersprüche sichtbar."
    )
    st.caption(
        f"„Übernehmen“ schreibt dedupliziert in `{canonical_target}` "
        f"(canonical selected list für {adopt_target})."
    )
    if include_inferred_confirmed_note:
        st.caption(
            "Inferred = Vorschlag/Arbeitskontext; confirmed = durch Nutzer bestätigt "
            "und für Summary/Exporte priorisiert."
        )


def render_compact_requirement_board(
    *,
    title_jobspec: str,
    jobspec_items: list[dict[str, Any]],
    title_esco: str,
    esco_items: list[dict[str, Any]],
    title_llm: str,
    llm_items: list[dict[str, Any]],
    selected_labels: list[str],
    selection_state_key: str,
    key_prefix: str,
    empty_messages: dict[str, str] | None = None,
) -> list[str]:
    selected_set = {
        _normalize_requirement_label(str(item))
        for item in selected_labels
        if has_meaningful_value(item)
    }
    board_items_all = [
        (title_jobspec, jobspec_items, "Jobspec"),
        (title_esco, esco_items, "ESCO"),
        (title_llm, llm_items, "AI"),
    ]
    board_items = [item for item in board_items_all if item[1]]
    if not board_items:
        st.caption("Keine Vorschläge.")
        st.session_state[selection_state_key] = []
        return []

    bulk_labels: list[str] = []
    if len(board_items) == 1:
        title, entries, source_badge = board_items[0]
        bulk_labels.extend(
            _render_requirement_selection_table(
                title=title,
                source_key=source_badge,
                entries=entries,
                selected_set=selected_set,
                selection_state_key=selection_state_key,
                key_prefix=key_prefix,
            )
        )
    else:
        tab_titles = [item[2] for item in board_items]
        tabs = st.tabs(tab_titles)
        for tab, (title, entries, source_badge) in zip(tabs, board_items):
            with tab:
                if entries:
                    bulk_labels.extend(
                        _render_requirement_selection_table(
                            title=title,
                            source_key=source_badge,
                            entries=entries,
                            selected_set=selected_set,
                            selection_state_key=selection_state_key,
                            key_prefix=key_prefix,
                        )
                    )
                else:
                    st.caption(
                        (empty_messages or {}).get(source_badge, "Keine Vorschläge.")
                    )

    deduped_labels: list[str] = []
    seen: set[str] = set()
    for label in bulk_labels:
        normalized = _normalize_requirement_label(label)
        if not normalized or normalized in seen:
            continue
        deduped_labels.append(label)
        seen.add(normalized)
    st.session_state[selection_state_key] = deduped_labels
    return deduped_labels


def _collect_incomplete_group_titles(
    grouped_questions: list[tuple[str, list[Question]]],
    answers: Dict[str, Any],
    answer_meta: dict[str, Any],
    answered_lookup: dict[str, bool],
) -> list[str]:
    incomplete_groups: list[str] = []
    for group_title, group_questions in grouped_questions:
        progress = compute_question_progress(
            group_questions,
            answers,
            answer_meta,
            answered_lookup=answered_lookup,
        )
        if progress["required_unanswered"] > 0:
            incomplete_groups.append(group_title)
    return incomplete_groups


def _format_answer_for_review(question: Question, value: Any) -> str:
    if _is_language_requirement_question(question):
        requirements = _coerce_language_requirements(value)
        formatted = [f"{item.language} ({item.level})" for item in requirements]
        return ", ".join(formatted)

    if question.answer_type == AnswerType.BOOLEAN:
        return "Ja" if bool(value) else "Nein"
    if question.answer_type == AnswerType.MULTI_SELECT:
        values = _coerce_multi_select_values(value)
        return ", ".join(values)
    if question.answer_type == AnswerType.SINGLE_SELECT:
        selected = _coerce_single_select_value(value)
        return selected or ""
    if question.answer_type == AnswerType.LONG_TEXT:
        text = str(value or "").strip()
        return _truncate_for_review(text, limit=140)
    if question.answer_type == AnswerType.SHORT_TEXT:
        return _truncate_for_review(str(value or "").strip(), limit=90)
    if question.answer_type == AnswerType.NUMBER:
        return str(value) if value is not None else ""
    if question.answer_type == AnswerType.DATE:
        return str(value or "")

    if isinstance(value, list):
        return ", ".join(
            str(item).strip() for item in value if has_meaningful_value(item)
        )
    if isinstance(value, str):
        return _truncate_for_review(value.strip(), limit=90)
    return str(value) if has_meaningful_value(value) else ""


def _truncate_for_review(text: str, *, limit: int) -> str:
    if len(text) <= limit:
        return text
    return f"{text[: max(limit - 1, 1)].rstrip()}…"


def _get_ui_preferences() -> dict[str, Any]:
    raw_ui_preferences = st.session_state.get(SSKey.UI_PREFERENCES.value, {})
    if isinstance(raw_ui_preferences, dict):
        return raw_ui_preferences
    return {}


def _get_global_details_expanded_default(*, ui_mode: str) -> bool:
    ui_preferences = _get_ui_preferences()
    configured = ui_preferences.get("details_expanded_default")
    if isinstance(configured, bool):
        return configured
    return ui_mode == "expert"


def _get_step_compact_preference(*, step_key: str, fallback_compact: bool) -> bool:
    ui_preferences = _get_ui_preferences()
    raw_step_compact = ui_preferences.get("step_compact", {})
    step_compact = raw_step_compact if isinstance(raw_step_compact, dict) else {}
    configured = step_compact.get(step_key)
    if isinstance(configured, bool):
        return configured
    return fallback_compact


def _set_step_compact_preference(*, step_key: str, compact: bool) -> None:
    ui_preferences = dict(_get_ui_preferences())
    raw_step_compact = ui_preferences.get("step_compact", {})
    step_compact = raw_step_compact if isinstance(raw_step_compact, dict) else {}
    updated_step_compact = dict(step_compact)
    updated_step_compact[step_key] = compact
    ui_preferences["step_compact"] = updated_step_compact
    st.session_state[SSKey.UI_PREFERENCES.value] = ui_preferences


def _ensure_step_group_state(
    step_key: str,
    grouped_questions: list[tuple[str, list[Question]]],
    *,
    default_open: bool,
) -> None:
    raw_open_groups = st.session_state.get(SSKey.OPEN_GROUPS.value, {})
    open_groups = raw_open_groups if isinstance(raw_open_groups, dict) else {}
    step_groups_raw = open_groups.get(step_key, {})
    step_groups = step_groups_raw if isinstance(step_groups_raw, dict) else {}

    changed = False
    for group_title, _ in grouped_questions:
        if group_title not in step_groups:
            step_groups[group_title] = default_open
            changed = True

    if changed:
        open_groups = dict(open_groups)
        open_groups[step_key] = step_groups
        st.session_state[SSKey.OPEN_GROUPS.value] = open_groups


def _is_group_open(step_key: str, group_title: str, *, default_open: bool) -> bool:
    raw_open_groups = st.session_state.get(SSKey.OPEN_GROUPS.value, {})
    if not isinstance(raw_open_groups, dict):
        return default_open
    step_groups = raw_open_groups.get(step_key, {})
    if not isinstance(step_groups, dict):
        return default_open
    value = step_groups.get(group_title)
    if isinstance(value, bool):
        return value
    return default_open


def _set_step_group_open_state(
    step_key: str,
    grouped_questions: list[tuple[str, list[Question]]],
    *,
    is_open: bool,
) -> None:
    raw_open_groups = st.session_state.get(SSKey.OPEN_GROUPS.value, {})
    open_groups = raw_open_groups if isinstance(raw_open_groups, dict) else {}
    step_groups_raw = open_groups.get(step_key, {})
    step_groups = step_groups_raw if isinstance(step_groups_raw, dict) else {}
    updated_groups = dict(step_groups)
    for group_title, _ in grouped_questions:
        updated_groups[group_title] = is_open

    open_groups = dict(open_groups)
    open_groups[step_key] = updated_groups
    st.session_state[SSKey.OPEN_GROUPS.value] = open_groups


def _render_question(q: Question, answers: Dict[str, Any]) -> None:
    key = WIDGET_KEY_PREFIX + q.id
    inferred_default = _infer_default_value(q)
    previous_value = answers.get(q.id, inferred_default)
    current_value = previous_value
    value: Any = None
    validation_error: str | None = None

    # Helper text for required fields
    label = q.label + (" *" if q.required else "")
    is_language_question = _is_language_requirement_question(q)

    with st.container(border=True):
        if is_language_question:
            value = _render_language_requirement_question(
                question=q,
                current_value=current_value,
                key=key,
                label=label,
            )
        elif q.answer_type == AnswerType.SHORT_TEXT:
            value = st.text_input(
                label,
                value=str(current_value or ""),
                help=q.help,
                key=key,
                placeholder=q.help or "Kurzantwort eingeben",
            )
        elif q.answer_type == AnswerType.LONG_TEXT:
            value = st.text_area(
                label,
                value=str(current_value or ""),
                help=q.help,
                key=key,
                height=140,
                placeholder=q.help or "Details ergänzen …",
            )
        elif q.answer_type == AnswerType.SINGLE_SELECT:
            option_entries = _question_option_entries(q)
            options = [value for value, _ in option_entries]
            label_by_value = {value: label for value, label in option_entries}
            value_by_label = {label: value for value, label in option_entries}
            current_value = _coerce_single_select_value(current_value)
            other_text_default = _extract_other_text(current_value)
            if other_text_default and _OTHER_OPTION not in options:
                options = [*options, _OTHER_OPTION]
                label_by_value[_OTHER_OPTION] = _OTHER_OPTION
                value_by_label[_OTHER_OPTION] = _OTHER_OPTION
            if other_text_default and current_value not in options:
                current_value = _OTHER_OPTION
            if current_value and current_value not in options:
                options = [str(current_value)] + options
                label_by_value[str(current_value)] = str(current_value)
                value_by_label[str(current_value)] = str(current_value)
            display_options = [label_by_value.get(item, item) for item in options]
            if not q.required:
                display_options = ["— Bitte wählen —", *display_options]
            selected_value = str(current_value) if current_value is not None else None
            selected_label = (
                label_by_value.get(selected_value, selected_value)
                if selected_value is not None
                else None
            )
            default_index = (
                display_options.index(selected_label)
                if selected_label in display_options
                else (0 if display_options else None)
            )
            if hasattr(st, "segmented_control") and 2 <= len(display_options) <= 5:
                value = st.segmented_control(
                    label,
                    options=display_options,
                    default=display_options[default_index]
                    if default_index is not None
                    else None,
                    key=key,
                    help=q.help,
                )
            elif len(display_options) <= 4:
                value = st.radio(
                    label,
                    options=display_options,
                    index=default_index if default_index is not None else 0,
                    horizontal=True,
                    help=q.help,
                    key=key,
                )
            else:
                value = st.selectbox(
                    label,
                    options=display_options,
                    index=default_index if default_index is not None else 0,
                    help=q.help,
                    key=key,
                )
            if value == "— Bitte wählen —":
                value = None
            elif value is not None:
                value = value_by_label.get(value, value)
            if value == _OTHER_OPTION:
                other_text = st.text_input(
                    "Bitte spezifizieren",
                    value=other_text_default,
                    key=f"{key}::other",
                    placeholder="Bitte präzisieren …",
                ).strip()
                value = f"{_OTHER_PREFIX}{other_text}" if other_text else _OTHER_OPTION
        elif q.answer_type == AnswerType.MULTI_SELECT:
            option_entries = _question_option_entries(q)
            options = [item[0] for item in option_entries]
            label_by_value = {value: label for value, label in option_entries}
            value_by_label = {label: value for value, label in option_entries}
            cur_list = _coerce_multi_select_values(current_value)
            cur_list, other_text_default = _strip_other_from_multiselect(cur_list)
            if other_text_default and _OTHER_OPTION not in options:
                options = [*options, _OTHER_OPTION]
                label_by_value[_OTHER_OPTION] = _OTHER_OPTION
                value_by_label[_OTHER_OPTION] = _OTHER_OPTION
            for v in cur_list:
                if v not in options:
                    options = [v] + options
                    label_by_value[v] = v
                    value_by_label[v] = v
            display_options = [label_by_value.get(item, item) for item in options]
            default_values = [
                label_by_value.get(v, v) for v in cur_list if v in options
            ]
            if hasattr(st, "pills") and options:
                value = (
                    st.pills(
                        label,
                        options=display_options,
                        default=default_values,
                        selection_mode="multi",
                        key=key,
                        help=q.help,
                    )
                    or []
                )
            else:
                value = st.multiselect(
                    label,
                    options=display_options,
                    default=default_values,
                    help=q.help,
                    key=key,
                )
            value = [value_by_label.get(item, item) for item in (value or [])]
            if _OTHER_OPTION in value:
                other_text = st.text_input(
                    "Bitte spezifizieren",
                    value=other_text_default,
                    key=f"{key}::other",
                    placeholder="Bitte präzisieren …",
                ).strip()
                value = [v for v in value if v != _OTHER_OPTION]
                value.append(
                    f"{_OTHER_PREFIX}{other_text}" if other_text else _OTHER_OPTION
                )
        elif q.answer_type == AnswerType.NUMBER:
            value, validation_error = _render_number_question(
                question=q,
                key=key,
                label=label,
                help_text=q.help,
                current_value=current_value,
            )
        elif q.answer_type == AnswerType.BOOLEAN:
            value = st.toggle(
                label,
                value=bool(current_value) if current_value is not None else False,
                help=q.help,
                key=key,
            )
        elif q.answer_type == AnswerType.DATE:
            d: Optional[date] = None
            if isinstance(current_value, date):
                d = current_value
            elif isinstance(current_value, str) and current_value:
                try:
                    d = date.fromisoformat(current_value)
                except Exception:
                    d = None
            picked_date = st.date_input(label, value=d, help=q.help, key=key)
            value = picked_date.isoformat() if picked_date else None
        else:
            value = st.text_input(
                label, value=str(current_value or ""), help=q.help, key=key
            )

        if q.help:
            st.caption(q.help)
        if validation_error:
            st.error(validation_error)

    # Persist answer
    mark_answer_touched(q.id, previous_value, value)
    set_answer(q.id, value)

    if st.session_state.get(SSKey.DEBUG.value) and q.rationale:
        st.caption(f"Rationale: {q.rationale}")


def _render_number_question(
    *,
    question: Question,
    key: str,
    label: str,
    help_text: str | None,
    current_value: Any,
) -> tuple[float | int, str | None]:
    min_value, max_value, step_value = _resolve_number_constraints(question)
    if min_value > max_value:
        fallback_value = min_value
        return fallback_value, (
            "Ungültige Zahlen-Konfiguration (min > max). Bitte Fragebogen prüfen. "
            "Invalid numeric configuration (min > max). Please review the question plan."
        )

    numeric_value, parse_error = _coerce_number_value(current_value)
    if numeric_value is None:
        numeric_value = min_value

    bounded_value = min(max(numeric_value, min_value), max_value)
    validation_error: str | None = None
    if parse_error:
        validation_error = (
            "Ungültiger Zahlenwert erkannt, Standardwert wurde verwendet. "
            "Invalid numeric value detected, fallback value was applied."
        )
    elif numeric_value != bounded_value:
        validation_error = (
            f"Wert muss zwischen {min_value:g} und {max_value:g} liegen. "
            f"Value must be between {min_value:g} and {max_value:g}."
        )

    integer_scale = all(
        float(x).is_integer() for x in (min_value, max_value, step_value)
    )
    if integer_scale:
        min_int = int(min_value)
        max_int = int(max_value)
        step_int = max(1, int(step_value))
        current_int = int(round(bounded_value))
        if max_int - min_int <= 200 and step_int == 1:
            return (
                st.slider(
                    label,
                    min_value=min_int,
                    max_value=max_int,
                    value=current_int,
                    step=step_int,
                    help=help_text,
                    key=key,
                ),
                validation_error,
            )
        return (
            st.number_input(
                label,
                min_value=min_int,
                max_value=max_int,
                value=current_int,
                step=step_int,
                help=help_text,
                key=key,
            ),
            validation_error,
        )

    step_float = float(step_value)
    current_float = float(bounded_value)
    return (
        st.number_input(
            label,
            min_value=float(min_value),
            max_value=float(max_value),
            value=current_float,
            step=step_float,
            help=help_text,
            key=key,
            format="%.2f",
        ),
        validation_error,
    )


def _coerce_number_value(value: Any) -> tuple[float | None, bool]:
    try:
        if value is None or value == "":
            return None, False
        return float(value), False
    except Exception:
        return None, True


def _resolve_number_constraints(question: Question) -> tuple[float, float, float]:
    if question.min_value is not None and question.max_value is not None:
        min_value = float(question.min_value)
        max_value = float(question.max_value)
    else:
        inferred_min, inferred_max = _parse_scale_bounds(
            f"{question.label} {question.help or ''}"
        )
        if inferred_min is not None and inferred_max is not None:
            min_value = float(inferred_min)
            max_value = float(inferred_max)
        else:
            min_value = 0.0
            max_value = 100.0

    step_value = float(question.step_value) if question.step_value else 1.0
    if step_value <= 0:
        step_value = 1.0
    return min_value, max_value, step_value


def _infer_default_value(q: Question) -> Any:
    if q.default is not None:
        return q.default
    if q.answer_type == AnswerType.SINGLE_SELECT:
        options = [value for value, _ in _question_option_entries(q)]
        return options[0] if options else None
    if q.answer_type == AnswerType.MULTI_SELECT:
        return []
    if q.answer_type == AnswerType.BOOLEAN:
        return False
    if q.answer_type == AnswerType.NUMBER:
        min_value, max_value, _ = _resolve_number_constraints(q)
        return (
            int((min_value + max_value) / 2)
            if float(min_value).is_integer() and float(max_value).is_integer()
            else (min_value + max_value) / 2
        )
    return None


def _is_language_requirement_question(question: Question) -> bool:
    haystack = " ".join(
        [
            question.id or "",
            question.label or "",
            question.help or "",
            question.target_path or "",
        ]
    ).lower()
    return any(term in haystack for term in ("sprache", "sprachen", "language", "cefr"))


def _coerce_language_requirements(value: Any) -> list[LanguageRequirement]:
    if isinstance(value, str):
        text = value.strip()
        if text:
            return [LanguageRequirement(language=text, level="B2")]
        return []

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        normalized: list[LanguageRequirement] = []
        for entry in value:
            if isinstance(entry, dict):
                raw_language = str(entry.get("language", "")).strip()
                raw_level = str(entry.get("level", "")).strip().upper()
                if not raw_language:
                    continue
                if raw_level not in _CEFR_OPTIONS:
                    raw_level = "B2"
                normalized.append(
                    LanguageRequirement(language=raw_language, level=raw_level)  # type: ignore[arg-type]
                )
                continue
            if isinstance(entry, str) and has_meaningful_value(entry):
                normalized.append(
                    LanguageRequirement(language=entry.strip(), level="B2")
                )
        return normalized
    return []


def _render_language_requirement_question(
    *,
    question: Question,
    current_value: Any,
    key: str,
    label: str,
) -> list[dict[str, str]]:
    rows_state_key = f"{key}::rows"
    if rows_state_key not in st.session_state:
        st.session_state[rows_state_key] = [
            item.model_dump() for item in _coerce_language_requirements(current_value)
        ] or [LanguageRequirement(language="Deutsch", level="B2").model_dump()]

    st.markdown(label)
    if question.help:
        st.caption(question.help)

    rows_raw = st.session_state.get(rows_state_key, [])
    rows = rows_raw if isinstance(rows_raw, list) else []

    new_rows: list[dict[str, str]] = []
    for index, row in enumerate(rows):
        row_data = row if isinstance(row, dict) else {}
        language = str(row_data.get("language", "Deutsch")).strip() or "Deutsch"
        level = str(row_data.get("level", "B2")).strip().upper() or "B2"
        if language not in _LANGUAGE_OPTIONS:
            language = _LANGUAGE_OPTIONS[0]
        if level not in _CEFR_OPTIONS:
            level = "B2"

        col_lang, col_level, col_remove = st.columns([2.2, 1.2, 0.8], gap="small")
        with col_lang:
            selected_language = st.selectbox(
                "Sprache",
                options=_LANGUAGE_OPTIONS,
                index=_LANGUAGE_OPTIONS.index(language),
                key=f"{key}::language::{index}",
                label_visibility="collapsed",
            )
        with col_level:
            selected_level = st.selectbox(
                "Level",
                options=_CEFR_OPTIONS,
                index=_CEFR_OPTIONS.index(level),
                key=f"{key}::level::{index}",
                label_visibility="collapsed",
            )
        with col_remove:
            remove_clicked = st.button(
                "Entfernen",
                key=f"{key}::remove::{index}",
                disabled=len(rows) <= 1,
                width="stretch",
            )
        if remove_clicked:
            continue
        new_rows.append(
            LanguageRequirement(
                language=selected_language,
                level=selected_level,  # type: ignore[arg-type]
            ).model_dump()
        )

    if st.button("Weitere Sprache hinzufügen", key=f"{key}::add"):
        new_rows.append(
            LanguageRequirement(language="Deutsch", level="B2").model_dump()
        )

    st.session_state[rows_state_key] = new_rows or [
        LanguageRequirement(language="Deutsch", level="B2").model_dump()
    ]
    return list(st.session_state[rows_state_key])


def _coerce_single_select_value(value: Any) -> str | None:
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in value:
            if isinstance(item, str) and has_meaningful_value(item):
                return item.strip()
    return None


def _coerce_multi_select_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if has_meaningful_value(value) else []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        cleaned = item.strip()
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return result


def _extract_other_text(value: str | None) -> str:
    if not isinstance(value, str):
        return ""
    if not value.startswith(_OTHER_PREFIX):
        return ""
    return value.removeprefix(_OTHER_PREFIX).strip()


def _strip_other_from_multiselect(values: list[str]) -> tuple[list[str], str]:
    cleaned_values: list[str] = []
    other_text = ""
    for entry in values:
        if entry.startswith(_OTHER_PREFIX):
            other_text = entry.removeprefix(_OTHER_PREFIX).strip()
            continue
        cleaned_values.append(entry)
    return cleaned_values, other_text


def _parse_scale_bounds(text: str) -> tuple[int | None, int | None]:
    match = re.search(r"(\d+)\s*[-–]\s*(\d+)", text)
    if not match:
        return None, None
    lower = int(match.group(1))
    upper = int(match.group(2))
    if lower > upper:
        lower, upper = upper, lower
    if upper - lower > 20:
        return None, None
    return lower, upper


def render_brief(brief: VacancyBrief) -> None:
    st.subheader("Recruiting Brief")
    st.markdown(f"**One-liner:** {brief.one_liner}")
    st.markdown("**Hiring Context**")
    st.write(brief.hiring_context)
    st.markdown("**Role Summary**")
    st.write(brief.role_summary)

    with st.expander("Top Responsibilities", expanded=False):
        for x in brief.top_responsibilities:
            st.write(f"- {x}")

    with st.expander("Must-have", expanded=False):
        for x in brief.must_have:
            st.write(f"- {x}")

    with st.expander("Nice-to-have", expanded=False):
        for x in brief.nice_to_have:
            st.write(f"- {x}")

    with st.expander("Dealbreakers", expanded=False):
        for x in brief.dealbreakers:
            st.write(f"- {x}")

    with st.expander("Interview Plan", expanded=False):
        for x in brief.interview_plan:
            st.write(f"- {x}")

    with st.expander("Evaluation Rubric", expanded=False):
        for x in brief.evaluation_rubric:
            st.write(f"- {x}")

    with st.expander("Risks / Open Questions", expanded=False):
        for x in brief.risks_open_questions:
            st.write(f"- {x}")

    with st.expander("Job Ad Draft (DE)", expanded=False):
        st.write(brief.job_ad_draft)

    with st.expander("Structured data (JSON)", expanded=False):
        st.json(brief.structured_data, expanded=False)


def render_interview_prep_hr(sheet: InterviewPrepSheetHR) -> None:
    st.markdown(
        f"**Rolle:** {sheet.role_title} · **Stage:** {sheet.interview_stage} · "
        f"**Dauer:** {sheet.duration_minutes} Min."
    )
    st.markdown("**Opening Script**")
    st.write(sheet.opening_script)

    st.markdown("**Frageblöcke**")
    if not sheet.question_blocks:
        st.info("Keine Frageblöcke vorhanden.")
    for index, block in enumerate(sheet.question_blocks, start=1):
        st.markdown(f"**{index}. {block.title}**")
        st.caption(f"Ziel: {block.objective}")
        if block.questions:
            st.write("Fragen:")
            for question in block.questions:
                st.write(f"- {question}")
        if block.follow_up_prompts:
            st.write("Follow-ups:")
            for follow_up in block.follow_up_prompts:
                st.write(f"- {follow_up}")

    st.markdown("**Knockout-Kriterien**")
    if sheet.knockout_criteria:
        for knockout_criterion in sheet.knockout_criteria:
            st.write(f"- {knockout_criterion}")
    else:
        st.info("Keine Knockout-Kriterien hinterlegt.")

    st.markdown("**Bewertungsrubrik**")
    if not sheet.evaluation_rubric:
        st.info("Keine Bewertungsrubrik vorhanden.")
    for rubric_criterion in sheet.evaluation_rubric:
        st.markdown(
            f"- **{rubric_criterion.title}** ({rubric_criterion.weight_percent} %) — "
            f"{rubric_criterion.description}"
        )
        if rubric_criterion.score_scale:
            st.caption(f"Skala: {' | '.join(rubric_criterion.score_scale)}")
        if rubric_criterion.evidence_examples:
            st.caption("Beobachtbare Evidenz:")
            for evidence in rubric_criterion.evidence_examples:
                st.write(f"  - {evidence}")

    st.markdown("**Empfehlungsoptionen**")
    if sheet.final_recommendation_options:
        for option in sheet.final_recommendation_options:
            st.write(f"- {option}")
    else:
        st.info("Keine finalen Empfehlungsoptionen hinterlegt.")


def render_interview_prep_fach(sheet: InterviewPrepSheetHiringManager) -> None:
    st.markdown(
        f"**Rolle:** {sheet.role_title} · **Stage:** {sheet.interview_stage} · "
        f"**Dauer:** {sheet.duration_minutes} Min."
    )

    st.markdown("**Kompetenzen validieren**")
    if sheet.competencies_to_validate:
        for competency in sheet.competencies_to_validate:
            st.write(f"- {competency}")
    else:
        st.info("Keine zu validierenden Kompetenzen hinterlegt.")

    st.markdown("**Frageblöcke**")
    if not sheet.question_blocks:
        st.info("Keine Frageblöcke vorhanden.")
    for index, block in enumerate(sheet.question_blocks, start=1):
        st.markdown(f"**{index}. {block.title}**")
        st.caption(f"Ziel: {block.objective}")
        if block.questions:
            st.write("Fragen:")
            for question in block.questions:
                st.write(f"- {question}")
        if block.follow_up_prompts:
            st.write("Follow-ups:")
            for follow_up in block.follow_up_prompts:
                st.write(f"- {follow_up}")

    st.markdown("**Technical Deep Dive Topics**")
    if sheet.technical_deep_dive_topics:
        for topic in sheet.technical_deep_dive_topics:
            st.write(f"- {topic}")
    else:
        st.info("Keine Deep-Dive-Themen hinterlegt.")

    st.markdown("**Case / Task Prompt**")
    if sheet.case_or_task_prompt:
        st.write(sheet.case_or_task_prompt)
    else:
        st.info("Kein Case/Task Prompt hinterlegt.")

    st.markdown("**Bewertungsrubrik**")
    if not sheet.evaluation_rubric:
        st.info("Keine Bewertungsrubrik vorhanden.")
    for criterion in sheet.evaluation_rubric:
        st.markdown(
            f"- **{criterion.title}** ({criterion.weight_percent} %) — "
            f"{criterion.description}"
        )
        if criterion.score_scale:
            st.caption(f"Skala: {' | '.join(criterion.score_scale)}")
        if criterion.evidence_examples:
            st.caption("Beobachtbare Evidenz:")
            for evidence in criterion.evidence_examples:
                st.write(f"  - {evidence}")

    st.markdown("**Debrief-Fragen**")
    if sheet.debrief_questions:
        for question in sheet.debrief_questions:
            st.write(f"- {question}")
    else:
        st.info("Keine Debrief-Fragen hinterlegt.")


def render_boolean_search_pack(pack: BooleanSearchPack) -> None:
    st.markdown(f"**Rolle:** {pack.role_title}")

    metadata_columns = st.columns(4)
    metadata_fields = [
        ("Must-have Terms", pack.must_have_terms),
        ("Seniority Terms", pack.seniority_terms),
        ("Exclusion Terms", pack.exclusion_terms),
        ("Target Locations", pack.target_locations),
    ]
    for column, (label, values) in zip(metadata_columns, metadata_fields):
        with column:
            st.markdown(f"**{label}**")
            if values:
                for value in values:
                    st.write(f"- {value}")
            else:
                st.caption("—")

    for channel_name, channel_queries in (
        ("Google", pack.google),
        ("LinkedIn", pack.linkedin),
        ("XING", pack.xing),
    ):
        st.markdown(f"**{channel_name}**")
        broad_col, focused_col, fallback_col = st.columns(3)
        for column, label, entries in (
            (broad_col, "Broad", channel_queries.broad),
            (focused_col, "Focused", channel_queries.focused),
            (fallback_col, "Fallback", channel_queries.fallback),
        ):
            with column:
                st.caption(label)
                if entries:
                    st.text_area(
                        f"{channel_name} {label}",
                        value="\n".join(entries),
                        height=120,
                        disabled=True,
                        key=f"cs.boolean_search.preview.{channel_name.lower()}.{label.lower()}",
                    )
                else:
                    st.caption("Keine Queries vorhanden.")

    st.markdown("**Channel Limitations**")
    if pack.channel_limitations:
        for limitation in pack.channel_limitations:
            st.write(f"- {limitation}")
    else:
        st.info("Keine kanalbezogenen Einschränkungen hinterlegt.")

    st.markdown("**Usage Notes**")
    if pack.usage_notes:
        for note in pack.usage_notes:
            st.write(f"- {note}")
    else:
        st.info("Keine Usage Notes hinterlegt.")


def render_employment_contract_draft(draft: EmploymentContractDraft) -> None:
    st.info(
        "Template-Draft zur Prüfung. Kein finaler Vertrag und keine Rechtsberatung."
    )
    st.markdown(
        f"**Jurisdiction:** {draft.jurisdiction} · "
        f"**Rolle:** {draft.role_title} · "
        f"**Employment Type:** {draft.employment_type} · "
        f"**Contract Type:** {draft.contract_type}"
    )

    details = [
        ("Start Date", draft.start_date),
        (
            "Probation (Monate)",
            (
                str(draft.probation_period_months)
                if draft.probation_period_months is not None
                else None
            ),
        ),
        (
            "Salary",
            (
                f"{draft.salary.min if draft.salary.min is not None else '—'} - "
                f"{draft.salary.max if draft.salary.max is not None else '—'} "
                f"{draft.salary.currency or ''} / {draft.salary.period or ''}".strip()
            ),
        ),
        ("Salary Notes", draft.salary.notes),
        (
            "Hours / Week",
            (
                str(draft.working_hours_per_week)
                if draft.working_hours_per_week is not None
                else None
            ),
        ),
        (
            "Vacation Days / Year",
            (
                str(draft.vacation_days_per_year)
                if draft.vacation_days_per_year is not None
                else None
            ),
        ),
        ("Place of Work", draft.place_of_work),
        ("Notice Period", draft.notice_period),
    ]
    meta_col_left, meta_col_right = st.columns(2)
    for index, (label, value) in enumerate(details):
        col = meta_col_left if index % 2 == 0 else meta_col_right
        with col:
            st.markdown(f"**{label}**")
            st.write(value or "—")

    st.markdown("**Missing Inputs (Pflicht-Checkliste vor Finalisierung)**")
    if draft.missing_inputs:
        st.warning(
            "Folgende Inputs fehlen noch. Bitte vor rechtlicher Finalisierung ergänzen."
        )
        for missing_input in draft.missing_inputs:
            st.write(f"- [ ] {missing_input}")
    else:
        st.success("Keine fehlenden Inputs markiert.")

    st.markdown("**Klauseln**")
    if draft.clauses:
        for clause in draft.clauses:
            required_tag = "Pflicht" if clause.required else "Optional"
            st.markdown(f"**{clause.title}** · `{required_tag}`")
            st.write(clause.clause_text)
            if clause.legal_note:
                st.caption(f"Legal note: {clause.legal_note}")
    else:
        st.info("Keine Klauseln vorhanden.")

    st.markdown("**Signature Requirements**")
    signature_requirements = list(draft.signature_requirements)
    legal_review_note = "Legal review required"
    if all(
        legal_review_note.lower() not in requirement.lower()
        for requirement in signature_requirements
    ):
        signature_requirements.append(legal_review_note)
    for requirement in signature_requirements:
        st.write(f"- {requirement}")
