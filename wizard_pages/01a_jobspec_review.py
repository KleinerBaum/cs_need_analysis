from __future__ import annotations

from difflib import SequenceMatcher

import streamlit as st

from constants import SSKey
from esco_client import EscoClient, EscoClientError
from schemas import JobAdExtract, QuestionPlan
from ui_components import (
    _render_question_limits_editor,
    render_error_banner,
    render_esco_picker_card,
    render_job_extract_overview,
)
from wizard_pages.base import (
    WizardContext,
    WizardPage,
    get_current_ui_mode,
    nav_buttons,
)


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
) -> dict[str, list[str]]:
    client = EscoClient()
    variants: dict[str, list[str]] = {}
    for language in languages:
        try:
            payload = client.terms(
                uri=occupation_uri,
                type="occupation",
                language=language,
            )
        except EscoClientError as exc:
            fallback_language = "en" if language == "de" else "de"
            if exc.status_code and exc.status_code >= 500:
                payload = client.terms(
                    uri=occupation_uri,
                    type="occupation",
                    language=fallback_language,
                )
                labels = _collect_occupation_labels(payload)
                if labels:
                    variants[language] = labels
                continue
            raise

        labels = _collect_occupation_labels(payload)
        if labels:
            variants[language] = labels
    return variants


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


def _extract_first_text(payload: object, *keys: str) -> str:
    if not isinstance(payload, dict):
        return ""
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


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
    return 0


def _render_selected_occupation_detail(payload: object) -> None:
    if not isinstance(payload, dict):
        st.caption("Noch keine Occupation-Details gespeichert.")
        return

    preferred_label = _extract_first_text(payload, "preferredLabel", "title")
    alternative_labels = _normalize_text_list(
        payload.get("alternativeLabel")
        or payload.get("altLabel")
        or payload.get("altLabels")
    )
    description = _extract_first_text(payload, "description")
    scope_note = _extract_first_text(payload, "scopeNote")
    isco_mapping = _extract_first_text(
        payload, "iscoGroup", "isco08", "isco08Code", "isco_code"
    )
    regulated_text = _extract_first_text(
        payload,
        "regulatedProfessionNote",
        "regulatedProfessionDescription",
    )
    regulated_flag = payload.get("regulatedProfession")
    regulated_value = (
        "Ja" if regulated_flag is True else "Nein" if regulated_flag is False else "—"
    )
    essential_skill_count = _extract_related_resource_count(
        payload, "hasEssentialSkill"
    )
    optional_skill_count = _extract_related_resource_count(payload, "hasOptionalSkill")
    essential_knowledge_count = _extract_related_resource_count(
        payload, "hasEssentialKnowledge"
    )
    optional_knowledge_count = _extract_related_resource_count(
        payload, "hasOptionalKnowledge"
    )

    with st.expander("ESCO Occupation-Details", expanded=False):
        st.markdown("**Preferred Label**")
        st.write(preferred_label or "—")

        st.markdown("**Alternative Labels**")
        if alternative_labels:
            st.write(", ".join(alternative_labels))
        else:
            st.caption("Keine alternativen Labels verfügbar.")

        st.markdown("**Description**")
        st.write(description or "—")

        st.markdown("**Scope Note**")
        st.write(scope_note or "—")

        st.markdown("**ISCO-08 Mapping**")
        st.write(isco_mapping or "—")

        st.markdown("**Regulated Profession**")
        st.write(regulated_value)
        if regulated_text:
            st.caption(regulated_text)

        st.markdown("**Related Skills & Knowledge (Counts)**")
        st.write(f"- Essential skills: {essential_skill_count}")
        st.write(f"- Optional skills: {optional_skill_count}")
        st.write(f"- Essential knowledge: {essential_knowledge_count}")
        st.write(f"- Optional knowledge: {optional_knowledge_count}")

        links: list[str] = []
        uri = str(payload.get("uri") or "").strip()
        if uri:
            links.append(f"[ESCO Occupation URI]({uri})")
        if links:
            st.markdown(" · ".join(links))


def _render_esco_post_confirm_impact(job: JobAdExtract) -> None:
    selected_raw = st.session_state.get(SSKey.ESCO_OCCUPATION_SELECTED.value)
    selected = selected_raw if isinstance(selected_raw, dict) else {}
    occupation_uri = str(selected.get("uri") or "").strip()
    if not occupation_uri:
        return

    selected_title = str(selected.get("title") or "—").strip() or "—"
    current_job_title = str(job.job_title or "—").strip() or "—"

    st.markdown("### Wirkung der bestätigten ESCO Occupation")
    with st.container(border=True):
        st.markdown("**Normalisierte Rollenbezeichnung**")
        st.write(f"- ESCO-Auswahl: {selected_title}")
        st.write(f"- Jobspec (`job.job_title`): {current_job_title}")
        if selected_title.casefold() == current_job_title.casefold():
            st.caption("Titel sind bereits konsistent.")
        else:
            st.caption(
                "Titel weichen ab: ESCO dient als normalisierte Referenz "
                "für die Folgeschritte."
            )

        st.markdown("**Scope Note aus ESCO**")
        try:
            occupation_payload = EscoClient().resource_occupation(uri=occupation_uri)
        except EscoClientError:
            st.caption("Scope Note aktuell nicht verfügbar.")
            st.warning("ESCO-Occupationsdetails konnten nicht sicher geladen werden.")
        else:
            scope_note = _extract_esco_scope_note(occupation_payload)
            if scope_note:
                st.write(scope_note)
            else:
                st.caption("Für diese Occupation liegt keine kurze Scope Note vor.")

        st.markdown("**Impact auf Essential vs. Optional Skills**")
        st.caption(
            "In `wizard_pages/05_skills.py` lädt die Occupation relationale Skills "
            "über `hasEssentialSkill` (Must) und `hasOptionalSkill` (Nice-to-have)."
        )

        st.markdown("**Impact auf Summary & Export**")
        st.caption(
            "In `wizard_pages/08_summary.py` fließt die Occupation in die "
            "Readiness-Prüfung (`_build_country_readiness_items`) und in den "
            "Export-Payload (`_read_selected_esco_occupation`) ein."
        )


def _normalize_intent_title(query_text: str) -> str:
    normalized_query = query_text.strip()
    if "(" in normalized_query:
        normalized_query = normalized_query.split("(", 1)[0]
    return normalized_query.strip()


def _infer_esco_match_explainability(
    *,
    query_text: str,
    selected: dict[str, object],
    options: list[dict[str, object]],
    applied_meta: dict[str, object],
) -> dict[str, object]:
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

    if manual_override and "manual override" not in provenance_categories:
        provenance_categories.append("manual override")
    if direct_match and "matched from jobspec title" not in provenance_categories:
        provenance_categories.append("matched from jobspec title")
    if (
        str(applied_meta.get("source") or "").strip().lower().startswith("manual")
        and "matched from synonyms/hidden terms" not in provenance_categories
    ):
        provenance_categories.append("matched from synonyms/hidden terms")

    if manual_override:
        badge_label = "Manual Override"
        reason = f"Auswahl weicht vom Top-Vorschlag '{top_title or '—'}' ab und wurde manuell bestätigt."
        confidence = "high"
    elif direct_match or similarity >= 0.72:
        badge_label = "Jobspec-Titel Match"
        reason = f"ESCO-Titel '{selected_title or '—'}' passt direkt zur Query-Intention '{intent_title or '—'}'."
        confidence = "high" if direct_match else "medium"
    elif top_intent_match:
        badge_label = "Query-Intent Match"
        reason = f"Top-Vorschlag '{top_title or '—'}' entspricht der Query-Intention; Auswahl nutzt denselben Kandidatenraum."
        confidence = "medium"
    else:
        badge_label = "Synonym/Hidden-Term Match"
        reason = f"Auswahl '{selected_title or '—'}' wurde als semantische Alternative zur Query '{intent_title or '—'}' übernommen."
        confidence = "low"
        if "matched from synonyms/hidden terms" not in provenance_categories:
            provenance_categories.append("matched from synonyms/hidden terms")

    return {
        "badge_label": badge_label,
        "reason": reason,
        "confidence": confidence,
        "provenance_categories": provenance_categories,
    }


def _render_esco_occupation_block(job: JobAdExtract) -> None:
    st.markdown("### ESCO Occupation")
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
        enable_preview=True,
        apply_label="Use as semantic anchor",
        confirmation_helper_text="Confirm occupation for downstream suggestions",
    )
    options_state_key = f"{SSKey.ESCO_OCCUPATION_SELECTED.value}.esco_picker.options"
    options = st.session_state.get(options_state_key, [])
    st.session_state[SSKey.ESCO_OCCUPATION_CANDIDATES.value] = (
        options if isinstance(options, list) else []
    )

    selected_raw = st.session_state.get(SSKey.ESCO_OCCUPATION_SELECTED.value)
    selected = selected_raw if isinstance(selected_raw, dict) else {}
    occupation_uri = str(selected.get("uri") or "").strip()
    if not occupation_uri:
        st.session_state[SSKey.ESCO_SELECTED_OCCUPATION_URI.value] = ""
        st.session_state[SSKey.ESCO_MATCH_REASON.value] = None
        st.session_state[SSKey.ESCO_MATCH_CONFIDENCE.value] = None
        st.session_state[SSKey.ESCO_MATCH_PROVENANCE.value] = []
        st.session_state[SSKey.ESCO_OCCUPATION_PAYLOAD.value] = None
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
    st.markdown(
        (
            f"**Ausgewählte Occupation:** {selected_title} "
            f"<span style='display:inline-block;padding:0.1rem 0.5rem;border:1px solid #999;border-radius:0.75rem;font-size:0.8rem;'>"
            f"{explainability['badge_label']}</span>"
        ),
        unsafe_allow_html=True,
    )
    st.caption(
        f"{explainability['reason']} (Confidence: {explainability['confidence']})"
    )
    try:
        occupation_payload = EscoClient().get_occupation_detail(uri=occupation_uri)
    except EscoClientError as exc:
        st.warning(f"ESCO-Occupationsdetails konnten nicht geladen werden: {exc}")
        st.session_state[SSKey.ESCO_OCCUPATION_PAYLOAD.value] = None
    else:
        st.session_state[SSKey.ESCO_OCCUPATION_PAYLOAD.value] = occupation_payload
    _render_selected_occupation_detail(
        st.session_state.get(SSKey.ESCO_OCCUPATION_PAYLOAD.value)
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
            variants = _load_occupation_title_variants(
                occupation_uri=occupation_uri,
                languages=languages,
            )
        except EscoClientError as exc:
            st.warning(f"ESCO-Titelvarianten konnten nicht geladen werden: {exc}")
        else:
            st.session_state[SSKey.ESCO_OCCUPATION_TITLE_VARIANTS.value] = {
                "uri": occupation_uri,
                "recommended_titles": variants,
            }

    title_variants_raw = st.session_state.get(
        SSKey.ESCO_OCCUPATION_TITLE_VARIANTS.value
    )
    if isinstance(title_variants_raw, dict):
        variant_uri = str(title_variants_raw.get("uri") or "").strip()
        variants_by_language = title_variants_raw.get("recommended_titles", {})
        if variant_uri == occupation_uri and isinstance(variants_by_language, dict):
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

    _render_esco_post_confirm_impact(job)


def _render_extraction_quality_summary(job: JobAdExtract) -> None:
    expected_fields = [
        "job_title",
        "company_name",
        "role_overview",
        "responsibilities",
        "must_have_skills",
        "location_city",
        "employment_type",
    ]
    populated = 0
    for field_name in expected_fields:
        value = getattr(job, field_name, None)
        if isinstance(value, list):
            if any(str(item).strip() for item in value if item):
                populated += 1
            continue
        if value and str(value).strip():
            populated += 1

    quality_ratio = populated / len(expected_fields)
    if quality_ratio >= 0.75:
        quality_label = "hoch"
    elif quality_ratio >= 0.45:
        quality_label = "mittel"
    else:
        quality_label = "niedrig"

    st.caption(
        "Extraktionsqualität: "
        f"{quality_label} ({populated}/{len(expected_fields)} Kernfelder gefüllt)."
    )


def render(ctx: WizardContext) -> None:
    job_dict = st.session_state.get(SSKey.JOB_EXTRACT.value)
    plan_dict = st.session_state.get(SSKey.QUESTION_PLAN.value)

    if not job_dict or not plan_dict:
        st.warning("Bitte zuerst im Start-Schritt eine Analyse durchführen.")
        st.button("Zur Startseite", on_click=lambda: ctx.goto("landing"))
        nav_buttons(ctx, disable_next=True)
        return

    job = JobAdExtract.model_validate(job_dict)
    plan = QuestionPlan.model_validate(plan_dict)

    st.header("Identifizierte Informationen")
    st.caption(
        "Hier prüfst und ergänzt du die extrahierten Inhalte, Gaps und Assumptions, "
        "bevor du in den Schritt 'Unternehmen' wechselst."
    )
    render_error_banner()

    st.markdown(f"**Jobtitel:** {job.job_title or '—'}")
    _render_extraction_quality_summary(job)
    _render_esco_occupation_block(job)

    with st.sidebar:
        if get_current_ui_mode() == "standard":
            with st.expander("Advanced", expanded=False):
                with st.expander("Fragen pro Step", expanded=False):
                    _render_question_limits_editor(plan, compact=True)
        else:
            with st.expander("Fragen pro Step", expanded=False):
                _render_question_limits_editor(plan, compact=True)

    render_job_extract_overview(job, plan=plan, show_question_limits=False)

    st.info(
        f"QuestionPlan geladen: {sum(len(s.questions) for s in plan.steps)} Fragen in "
        f"{len(plan.steps)} Steps."
    )
    nav_buttons(ctx)


PAGE = WizardPage(
    key="jobspec_review",
    title_de="Identifizierte Informationen",
    icon="🧾",
    render=render,
    requires_jobspec=True,
)
