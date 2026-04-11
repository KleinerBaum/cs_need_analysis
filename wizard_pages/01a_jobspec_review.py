from __future__ import annotations

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


def _render_esco_occupation_block(job: JobAdExtract) -> None:
    st.markdown("### ESCO Occupation")
    query_text = _build_esco_query(job)
    if not query_text:
        st.info("Kein Jobtitel vorhanden. ESCO-Zuordnung aktuell nicht möglich.")
        st.session_state[SSKey.ESCO_OCCUPATION_CANDIDATES.value] = []
        st.session_state[SSKey.ESCO_OCCUPATION_SELECTED.value] = None
        return

    st.caption(f"Suche mit: `{query_text}`")
    query_state_key = f"{SSKey.ESCO_OCCUPATION_SELECTED.value}.esco_picker.query"
    if not st.session_state.get(query_state_key):
        st.session_state[query_state_key] = query_text
    render_esco_picker_card(
        concept_type="occupation",
        target_state_key=SSKey.ESCO_OCCUPATION_SELECTED,
        enable_preview=True,
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
        st.session_state[SSKey.ESCO_OCCUPATION_TITLE_VARIANTS.value] = {}
        return

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
