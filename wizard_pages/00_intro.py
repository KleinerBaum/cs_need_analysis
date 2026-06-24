from __future__ import annotations

from collections.abc import Sequence

import streamlit as st

from components.iceberg_need_analysis import (
    COMPONENT_HEIGHT,
    build_iceberg_need_analysis_html,
)
from components.recruiting_cycle import build_recruiting_cycle_figure
from content.start_page import START_PAGE_COPY
from constants import SSKey, STEP_KEY_INTRO, STEP_KEY_LANDING
from i18n import LANGUAGE_WIDGET_KEY_PAGE, render_language_toggle, t
from safe_html import escape_html_text, render_static_html
from wizard_pages.base import (
    LANDING_SECTION_IDS,
    LANDING_STYLE_TOKENS,
    WizardContext,
    WizardPage,
    render_landing_css,
)


INTRO_COPY = {
    "eyebrow": "Recruiting einfach vorbereiten",
    "headline": "Erst klären. Dann suchen.",
    "subheadline": (
        "Die App macht aus einer Stellenbeschreibung eine klare Grundlage: "
        "wen suchen wir, was muss die Person können, was fehlt noch?"
    ),
    "body": (
        (
            "So starten Suche, Interview und Stellenanzeige mit denselben geprüften Fakten."
        ),
    ),
    "closing": "Sie behalten Kontrolle: erst prüfen, dann weiterverwenden.",
    "cta": "Briefing-Cockpit öffnen",
    "skip_title": "Briefing bereits vorbereitet",
    "skip_body": (
        "Die Einleitung ist jetzt optional. Öffnen Sie direkt den Start, prüfen Sie "
        "die erkannte Briefing-Basis und bestätigen Sie den Referenzberuf."
    ),
    "iceberg_title": "Warum das wichtig ist",
    "iceberg_caption": (
        "Sichtbare Anforderungen und versteckte Erwartungen werden getrennt geprüft."
    ),
}

HERO_METRICS: tuple[tuple[str, str, str], ...] = (
    ("Klarheit", "Rolle", "Was soll die Person leisten?"),
    ("Abgleich", "Anforderungen", "Was ist wirklich wichtig?"),
    ("Ergebnis", "Unterlagen", "Briefing, Anzeige, Interviewhilfe"),
)

RISK_POINTS: tuple[tuple[str, str], ...] = (
    (
        "Falsche Suchrichtung",
        "Unklare Must-haves erzeugen Treffer, die fachlich wirken, aber am Auftrag vorbeigehen.",
    ),
    (
        "Demotivation im Prozess",
        "Kandidat:innen erleben wechselnde Kriterien, Fachbereiche verlieren Vertrauen in die Shortlist.",
    ),
    (
        "Teure Schleifen",
        "Interviewfragen, Stellenanzeige, Gehaltsrahmen und Suchstrings müssen nachträglich korrigiert werden.",
    ),
)

TECH_STACK_GROUPS: tuple[tuple[str, str, str], ...] = (
    (
        "Streamlit UI",
        "Interaktive App-Schicht",
        "Container, Columns, Tabs, Popovers, Session State und AppTest bilden den Wizard-Rahmen.",
    ),
    (
        "OpenAI + strukturierte Outputs",
        "Extraktion und Textgenerierung",
        "Zentrale LLM-Schicht mit Modell-Routing, Schema-Ausgabe, Caching, Fallbacks und sicherem Error-Mapping.",
    ),
    (
        "ESCO / EURES / RAG",
        "Arbeitsmarkt-Semantik",
        "EU-Berufs- und Skill-Taxonomie, Live-/Offline-Fallbacks, optionale Retrieval-Schicht und Explainability-Metadaten.",
    ),
    (
        "Pydantic + State Contracts",
        "Verlässliche Datenform",
        "Schemas, kanonische Session-State-Keys und Fact-Registry verhindern driftende Felder und implizite Annahmen.",
    ),
    (
        "Plotly + Pandas",
        "Daten sichtbar machen",
        "Interaktive Visualisierungen, KPI-Übersichten und strukturierte Tabellen machen Fortschritt und Abdeckung prüfbar.",
    ),
    (
        "DOCX / PDF / Excel Export",
        "Recruiting-Unterlagen rausgeben",
        "python-docx, ReportLab, pdfplumber und openpyxl decken Upload, Vorschau und Download-Unterlagen ab.",
    ),
)

INFO_POPOVERS: tuple[tuple[str, str, str], ...] = (
    (
        "Was ist ESCO?",
        "ESCO ist die mehrsprachige EU-Klassifikation für Berufe, Skills und Kompetenzen. In der App dient sie als Referenzanker, damit Rollenprofile, Skills und Suchlogik vergleichbarer werden.",
        "Wichtig: ESCO liefert Orientierung, aber keine automatische Knockout-Entscheidung.",
    ),
    (
        "Was bedeutet RAG?",
        "RAG verbindet Retrieval mit Generierung: Die App kann relevante ESCO-Kontexte suchen und erst danach Vorschläge formulieren.",
        "Wichtig: Treffer bleiben als Quelle/Fallback nachvollziehbar, statt als harte Wahrheit zu erscheinen.",
    ),
    (
        "Welche OpenAI-Tools nutzt die App?",
        "Die App nutzt OpenAI zentral für strukturierte Jobspec-Extraktion, Folgefragen, Briefing- und Unterlagenentwürfe — mit Schema-Prüfung, Modellfähigkeits-Checks, Retry/Fallback und Nutzungsmetadaten.",
        "Wichtig: Erkannte Werte bleiben prüfbar; bestätigte Fakten steuern die finalen Outputs.",
    ),
)


def _has_prepared_briefing() -> bool:
    return isinstance(st.session_state.get(SSKey.JOB_EXTRACT.value), dict)


def _render_intro_overrides() -> None:
    render_static_html(
        """
        <style>
            .intro-page {
                max-width: 1120px;
                margin: 0 auto;
            }

            .intro-page .st-emotion-cache-1dp5vir,
            .intro-page .st-emotion-cache-1v0mbdj {
                max-width: 100%;
            }

            .intro-hero {
                position: relative;
                overflow: hidden;
                border: 1px solid color-mix(in srgb, var(--cs-success) 30%, var(--cs-border));
                border-radius: 8px;
                padding: 1.65rem;
                background:
                    linear-gradient(135deg, var(--cs-surface) 0%, color-mix(in srgb, var(--cs-surface-muted) 82%, #07111F) 100%);
                box-shadow: var(--cs-shadow-sm);
            }

            .intro-hero::before {
                content: "";
                position: absolute;
                inset: -40% -20% auto 45%;
                height: 280px;
                transform: rotate(-10deg);
                background: linear-gradient(90deg, transparent, color-mix(in srgb, var(--cs-success) 18%, transparent), transparent);
                opacity: 0.78;
                pointer-events: none;
            }

            .intro-eyebrow {
                display: inline-flex;
                align-items: center;
                gap: 0.42rem;
                margin: 0 0 0.72rem 0;
                padding: 0.26rem 0.68rem;
                border: 1px solid color-mix(in srgb, var(--cs-success) 56%, var(--cs-border));
                border-radius: 999px;
                background: var(--cs-success-soft);
                color: var(--cs-text);
                font-size: 0.78rem;
                font-weight: 780;
                letter-spacing: 0.02em;
                text-transform: uppercase;
            }

            .intro-hero h1 {
                margin: 0;
                max-width: 880px;
                color: var(--cs-text);
                font-size: 3rem;
                line-height: 1.04;
                letter-spacing: 0;
            }

            .intro-hero h2 {
                max-width: 850px;
                margin: 0.82rem 0 0 0;
                color: var(--cs-text);
                font-size: 1.22rem;
                line-height: 1.32;
                font-weight: 760;
            }

            .intro-body {
                display: grid;
                gap: 0.72rem;
                max-width: 860px;
                margin: 1rem 0 1.05rem 0;
                color: var(--cs-text-muted);
                font-size: 1rem;
                line-height: 1.58;
            }

            .intro-body p {
                margin: 0;
            }

            .intro-closing {
                max-width: 860px;
                border-left: 4px solid var(--cs-success);
                background: var(--cs-success-soft);
                border-radius: 8px;
                padding: 0.78rem 0.92rem;
                margin: 0.35rem 0 1.05rem 0;
                color: var(--cs-text);
                font-weight: 760;
            }

            .intro-metric-grid {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 0.66rem;
                margin-top: 1.1rem;
            }

            .intro-metric-card,
            .intro-risk-card,
            .intro-tech-card {
                border: 1px solid var(--cs-border);
                border-radius: 8px;
                background: color-mix(in srgb, var(--cs-surface-muted) 88%, transparent);
                padding: 0.78rem 0.86rem;
            }

            .intro-metric-label,
            .intro-tech-label {
                display: block;
                margin-bottom: 0.22rem;
                color: var(--cs-text-muted);
                font-size: 0.75rem;
                font-weight: 760;
                letter-spacing: 0.04em;
                text-transform: uppercase;
            }

            .intro-metric-value,
            .intro-tech-title {
                display: block;
                color: var(--cs-text);
                font-size: 1.04rem;
                font-weight: 840;
                line-height: 1.18;
            }

            .intro-metric-caption,
            .intro-tech-body,
            .intro-risk-card p {
                display: block;
                margin: 0.32rem 0 0 0;
                color: var(--cs-text-muted);
                font-size: 0.86rem;
                line-height: 1.4;
            }

            .intro-section-card {
                border: 1px solid color-mix(in srgb, var(--cs-success) 25%, var(--cs-border));
                background: var(--cs-surface);
                border-radius: 8px;
                padding: 1.12rem;
                box-shadow: var(--cs-shadow-sm);
                margin: 0.95rem 0 1rem 0;
            }

            .intro-section-card h3,
            .intro-iceberg h3 {
                margin: 0 0 0.38rem 0;
                color: var(--cs-text);
                font-size: 1.35rem;
                line-height: 1.2;
            }

            .intro-section-copy {
                margin: 0 0 0.78rem 0;
                color: var(--cs-text-muted);
                line-height: 1.5;
            }

            .intro-risk-grid {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 0.66rem;
                margin-top: 0.66rem;
            }

            .intro-risk-card strong {
                color: var(--cs-text);
                font-size: 0.95rem;
            }

            .intro-cycle-callout {
                border: 1px solid var(--cs-success);
                background: var(--cs-success-soft);
                border-radius: 8px;
                padding: 0.72rem 0.84rem;
                color: var(--cs-text);
                font-weight: 760;
                line-height: 1.42;
            }

            .intro-process-track {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 0.72rem;
                max-width: 100%;
            }

            .intro-process-step {
                position: relative;
                border: 1px solid var(--cs-border);
                background: var(--cs-surface-muted);
                border-radius: 8px;
                padding: 0.74rem 0.76rem;
                min-height: 112px;
                overflow-wrap: anywhere;
            }

            .intro-process-step::after {
                content: "";
                position: absolute;
                top: 50%;
                right: -0.55rem;
                width: 0.36rem;
                height: 0.36rem;
                border-top: 2px solid var(--cs-success);
                border-right: 2px solid var(--cs-success);
                transform: translateY(-50%) rotate(45deg);
            }

            .intro-process-step:last-child::after {
                display: none;
            }

            .intro-process-step span {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 1.55rem;
                height: 1.55rem;
                border-radius: 999px;
                color: #FFFFFF;
                background: var(--cs-success);
                font-weight: 850;
                font-size: 0.84rem;
                margin-bottom: 0.42rem;
            }

            .intro-process-step strong {
                display: block;
                font-size: 0.95rem;
                line-height: 1.25;
                color: var(--cs-text);
            }

            .intro-process-step p {
                margin: 0.28rem 0 0 0;
                color: var(--cs-text-muted);
                font-size: 0.84rem;
                line-height: 1.36;
            }

            .intro-process-result {
                margin-top: 0.72rem;
                border-left: 4px solid var(--cs-success);
                padding: 0.62rem 0.76rem;
                background: var(--cs-success-soft);
                border-radius: 8px;
                color: var(--cs-text);
                font-weight: 720;
            }

            .intro-popover-row {
                display: flex;
                flex-wrap: wrap;
                gap: 0.42rem;
                margin: 0.75rem 0 0.35rem 0;
                color: var(--cs-text-muted);
                font-size: 0.88rem;
                font-weight: 720;
            }

            .intro-trust-note {
                margin-top: 0.72rem;
                border: 1px solid var(--cs-border);
                background: var(--cs-surface-muted);
                border-radius: 8px;
                padding: 0.72rem 0.84rem;
                color: var(--cs-text);
                line-height: 1.45;
            }

            .intro-trust-note strong {
                display: block;
                margin-bottom: 0.22rem;
                color: var(--cs-text);
            }

            .intro-tech-grid {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 0.66rem;
            }

            .intro-tech-card {
                min-height: 138px;
            }

            .intro-tech-title {
                font-size: 0.98rem;
            }

            .intro-iceberg {
                border: 1px solid color-mix(in srgb, var(--cs-success) 34%, var(--cs-border));
                background: var(--cs-surface);
                border-radius: 8px;
                box-shadow: var(--cs-shadow-sm);
                padding: 1rem;
                margin: 0.95rem 0 1rem 0;
            }

            .intro-iceberg p {
                margin: 0 0 0.78rem 0;
                color: var(--cs-text-muted);
                line-height: 1.45;
            }

            @media (max-width: 980px) {
                .intro-metric-grid,
                .intro-risk-grid,
                .intro-process-track,
                .intro-tech-grid {
                    grid-template-columns: minmax(0, 1fr);
                }

                .intro-process-step {
                    min-height: 0;
                }

                .intro-process-step::after {
                    display: none;
                }

                .intro-hero {
                    padding: 1rem;
                }

                .intro-hero h1 {
                    font-size: 2.2rem;
                }
            }
        </style>
        """,
        streamlit_module=st,
    )


def _hero_metric_grid_html() -> str:
    cards_html = "".join(
        f"""
        <div class="intro-metric-card">
            <span class="intro-metric-label">{escape_html_text(t(label))}</span>
            <span class="intro-metric-value">{escape_html_text(t(value))}</span>
            <span class="intro-metric-caption">{escape_html_text(t(caption))}</span>
        </div>
        """
        for label, value, caption in HERO_METRICS
    )
    return f'<div class="intro-metric-grid">{cards_html}</div>'

def _render_intro_hero_markup() -> None:
    body_html = "".join(
        f"<p>{escape_html_text(t(paragraph))}</p>" for paragraph in INTRO_COPY["body"]
    )
    render_static_html(
        f"""
        <section class="intro-hero">
            <div class="intro-eyebrow">{escape_html_text(t(INTRO_COPY["eyebrow"]))}</div>
            <h1>{escape_html_text(t(INTRO_COPY["headline"]))}</h1>
            <h2>{escape_html_text(t(INTRO_COPY["subheadline"]))}</h2>
            <div class="intro-body">{body_html}</div>
            <div class="intro-closing">{escape_html_text(t(INTRO_COPY["closing"]))}</div>
            {_hero_metric_grid_html()}
        </section>
        """,
        streamlit_module=st,
    )


def _render_risk_cards() -> None:
    risk_html = "".join(
        f"""
        <article class="intro-risk-card">
            <strong>{escape_html_text(t(title))}</strong>
            <p>{escape_html_text(t(body))}</p>
        </article>
        """
        for title, body in RISK_POINTS
    )
    render_static_html(f'<div class="intro-risk-grid">{risk_html}</div>', streamlit_module=st)


def _plotly_chart(figure: object | None, *, key: str) -> None:
    plotly_chart = getattr(st, "plotly_chart", None)
    if figure is None or not callable(plotly_chart):
        st.info(str(t("Recruiting-Cycle-Visualisierung ist in dieser Umgebung nicht verfügbar.")))
        return
    plotly_chart(figure, width="stretch", config={"displayModeBar": False}, key=key)


def _render_recruiting_cycle_section() -> None:
    with st.container(border=True):
        st.markdown(f"### {t('Der Recruiting-Cycle kippt im ersten Schritt')}")
        st.caption(
            str(
                t(
                    "Preparation ist kein Vorwort. Es ist der Kontrollpunkt, an dem Bedarf, Kompromisse und Erfolgskriterien festgelegt werden."
                )
            )
        )
        chart_col, copy_col = st.columns([1.25, 1], gap="medium")
        with chart_col:
            figure = build_recruiting_cycle_figure()
            _plotly_chart(figure, key="intro_recruiting_cycle")
        with copy_col:
            render_static_html(
                '<div class="intro-cycle-callout">'
                + escape_html_text(
                    t(
                        "Wenn der Bedarf unscharf bleibt, optimiert jeder spätere Schritt auf eine andere Wahrheit. Die App zieht diese Wahrheit nach vorn."
                    )
                )
                + "</div>",
                streamlit_module=st,
            )
            _render_risk_cards()


def _render_info_popovers(popovers: Sequence[tuple[str, str, str]] = INFO_POPOVERS) -> None:
    st.caption(str(t("Technische Vertrauensbasis")))
    cols = st.columns(len(popovers), gap="small")
    for col, (label, body, note) in zip(cols, popovers):
        with col:
            with st.popover(str(t(label)), width="stretch"):
                st.markdown(str(t(body)))
                st.caption(str(t(note)))


def _render_intro_flow_cards() -> None:
    flow_heading = t("Was nach dem Briefing-Start entsteht")
    flow_steps = tuple(START_PAGE_COPY["flow_steps"])
    flow_step_html = "\n".join(
        f"""
                <div class="intro-process-step">
                    <span>{index}</span>
                    <strong>{escape_html_text(t(str(step_title)))}</strong>
                    <p>{escape_html_text(t(str(step_body)))}</p>
                </div>
        """
        for index, (step_title, step_body) in enumerate(flow_steps, start=1)
    )
    flow_result = t(
        "Eisberg-Prinzip: Sichtbare Jobspec-Daten bleiben mit verdeckten Entscheidungskriterien verbunden, damit Recruiting, Suche und Interview dieselbe Briefing-Basis nutzen."
    )
    security_title = t(START_PAGE_COPY["security_title"])
    security_body = t(START_PAGE_COPY["security_body"])
    with st.container(border=True):
        render_static_html(
            f"""
            <section
                id="{escape_html_text(LANDING_SECTION_IDS["flow"], quote=True)}"
                class="intro-section-card"
            >
                <h3>{escape_html_text(t(START_PAGE_COPY["flow_title"]))}</h3>
                <p class="intro-section-copy">{escape_html_text(flow_heading)}</p>
                <div class="intro-process-track">
                    {flow_step_html}
                </div>
                <div class="intro-process-result">
                    {escape_html_text(flow_result)}
                </div>
            </section>
            """,
            streamlit_module=st,
        )
        _render_info_popovers()
        render_static_html(
            f"""
            <div class="intro-trust-note">
                <strong>{escape_html_text(security_title)}</strong>
                {escape_html_text(security_body)}
            </div>
            """,
            streamlit_module=st,
        )


def _render_technology_stack() -> None:
    card_html = "".join(
        f"""
        <article class="intro-tech-card">
            <span class="intro-tech-label">{escape_html_text(t(label))}</span>
            <span class="intro-tech-title">{escape_html_text(t(title))}</span>
            <p class="intro-tech-body">{escape_html_text(t(body))}</p>
        </article>
        """
        for label, title, body in TECH_STACK_GROUPS
    )
    with st.container(border=True):
        render_static_html(
            '<section class="intro-section-card">'
            f"<h3>{escape_html_text(t('Technologie, die das Briefing belastbar macht'))}</h3>"
            f"<p class=\"intro-section-copy\">{escape_html_text(t('Unter der Oberfläche arbeitet die App wie ein kuratierter Recruiting-Stack: schlank im UI, streng bei Daten, nachvollziehbar bei AI.'))}</p>"
            f'<div class="intro-tech-grid">{card_html}</div>'
            "</section>",
            streamlit_module=st,
        )


def _render_intro_iceberg() -> None:
    with st.container(border=True):
        st.markdown(f"### {t(INTRO_COPY['iceberg_title'])}")
        st.caption(str(t(INTRO_COPY["iceberg_caption"])))
        st.iframe(
            build_iceberg_need_analysis_html(),
            height=COMPONENT_HEIGHT,
        )


def render(ctx: WizardContext) -> None:
    render_landing_css(LANDING_STYLE_TOKENS)
    _render_intro_overrides()
    with st.container(border=True):
        render_language_toggle(location="main", key=LANGUAGE_WIDGET_KEY_PAGE)
        if _has_prepared_briefing():
            st.info(str(t(INTRO_COPY["skip_title"])))
            st.caption(str(t(INTRO_COPY["skip_body"])))
        _render_intro_hero_markup()
        if st.button(str(t(INTRO_COPY["cta"])), type="primary"):
            ctx.goto(STEP_KEY_LANDING)
            st.rerun()

    with st.expander(str(t("Mehr zur Methode")), expanded=False):
        _render_recruiting_cycle_section()
        _render_intro_flow_cards()
        _render_intro_iceberg()

    with st.expander(str(t("Technische Insights")), expanded=False):
        _render_technology_stack()


PAGE = WizardPage(
    key=STEP_KEY_INTRO,
    title_de="Einleitung",
    icon="ℹ️",
    render=render,
    requires_jobspec=False,
)
