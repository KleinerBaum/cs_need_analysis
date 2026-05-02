# wizard_pages/00_landing.py
from __future__ import annotations

import streamlit as st
from content.start_page import START_PAGE_COPY
from constants import APP_TITLE
from wizard_pages.jobad_intake import (
    _has_completed_landing_analysis,
    render_jobad_intake,
)
from wizard_pages.base import (
    LANDING_SECTION_IDS,
    LANDING_STYLE_TOKENS,
    WizardContext,
    WizardPage,
    render_esco_language_toggle,
    render_landing_css,
)

def _render_landing_explainer_sections() -> None:
    st.markdown(
        f'<section id="{LANDING_SECTION_IDS["flow"]}" class="landing-section">',
        unsafe_allow_html=True,
    )
    st.subheader(str(START_PAGE_COPY["flow_title"]))
    flow_steps = START_PAGE_COPY.get("flow_steps", ())
    if isinstance(flow_steps, tuple):
        for step_title, step_body in flow_steps:
            st.markdown(f"**{step_title}**")
            st.markdown(step_body)
    st.markdown("</section>", unsafe_allow_html=True)
    with st.expander("Details & Hintergrundwissen", expanded=False):
        st.markdown(
            f'<section id="{LANDING_SECTION_IDS["importance"]}" class="landing-section">',
            unsafe_allow_html=True,
        )
        st.subheader(str(START_PAGE_COPY["importance_title"]))

        st.markdown("#### Was ist ESCO?")
        st.markdown(
            "ESCO ist die europäische Klassifikation für Berufe und Skills. "
            "Die App nutzt ESCO, um unterschiedliche Jobtitel konsistent zu verankern."
        )

        st.markdown("#### Wie nutzt die App RAG?")
        st.markdown(
            "- **Berufserkennung:** Nach Eingabe eines Stellen- oder Tätigkeitsnamens schlägt die App passende ESCO-Occupations vor. So werden verschiedene Bezeichnungen (z.B. „Full Stack Entwickler“, „Cloud-Engineer“) auf einen eindeutigen Beruf zusammengeführt.\n"
            "- **Skill-Vorschläge:** Sobald ein ESCO-Beruf bestätigt ist, lädt die App die zugehörigen Essential/Nice-to-have Skills. Diese fließen in die KI-gestützte Anforderungsanalyse und Text-Generierung ein.\n"
            "- **KI-Unterstützung (RAG):** Wir nutzen ESCO-Daten in einem Retrieval-Augmented-Generation-Ansatz (RAG). Das bedeutet: Beim Generieren von Texten (z.B. vorgeschlagene Aufgaben oder Umschreibungen) werden relevante ESCO-Beschreibungen und Skill-Listen aus der Wissensdatenbank abgerufen und als Faktenbasis eingesetzt. Dadurch erhält die KI konkreten Kontext statt nur freier Texte.\n"
            "- **Anforderungsnormalisierung:** Unbekannte oder freie Stichworte in einer Stellenanzeige können durch ESCO-Skills ergänzt oder abgeglichen werden. Die App ermöglicht, fehlende Skills zuzuordnen oder als unternehmensspezifisch zu belassen."
        )
        st.caption(
            "Dieser Dienst stützt sich auf die ESCO-Klassifikation der Europäischen Kommission."
        )

        st.markdown("#### Welche Artefakte entstehen?")
        st.markdown(
            "- **a) Präzise Formulierungen:** Messerscharf formulierte Aufgaben, Must-haves, Nice-to-have Skills sowie lokale und zielgruppenorientierte Benefits.\n"
            "- **b) Erwartungsmanagement:** Gehaltsprognosen für Einstellende, basierend auf allen eingegebenen Parametern.\n"
            "- **c) Interne Kommunikation:** Automatisierung und Optimierung interner Kommunikationsprozesse.\n"
            "- **d) Sourcing-Automatisierung:** Optimierung von Sourcing-Schritten von der Jobad-Erstellung über Boolean-Searchstrings bis zur Vertragserstellung im Corporate Design."
        )

    with st.expander("Klassische Bedarfsanalyse", expanded=False):
        st.markdown(
            "Als langjähriger Personalvermittler ist mir die Suche nach der eierlegenden Wollmilchsau bestens bekannt. Unklare Anforderungen führen nicht nur für Personalvermittler zu unpräzisem Sourcing und Diskussionen über die falschen Profile. Unklare Anforderungen führen von den Verantwortlichen unbemerkt dazu, dass das Interesse des perfekten Kandidaten nicht geweckt wird, z.B. indem das essentielle Benefit nicht bekannt gegeben wird. Merklicher wird es für die Verantwortlichen, wenn unpassende Profile vorgestellt werden, Prozesse aufgrund ihrer Länge scheitern oder schlimmstenfalls der Mitarbeiter nach 6 Monaten Probe kündigt, da die Anforderungen in der Realität nicht mit den Vorstellungen des Mitarbeiters übereinstimmen. Der Prozess muss dann komplett neu gestartet werden, was allen Beteiligten nicht nur Zeit kostet, sondern auch viele Dollars"
        )
        _, image_col, _ = st.columns((1, 3, 1))
        with image_col:
            st.image("images/iceberg v1.png", width="stretch")
    st.markdown("</section>", unsafe_allow_html=True)


def render(ctx: WizardContext) -> None:
    render_landing_css(LANDING_STYLE_TOKENS)
    title_col, language_col = st.columns((1.7, 0.3), gap="small")
    with title_col:
        st.markdown(
            f'<span class="landing-app-title">{APP_TITLE}</span>',
            unsafe_allow_html=True,
        )
    with language_col:
        render_esco_language_toggle()
    _, logo_col, _ = st.columns((1, 2, 1))
    with logo_col:
        _, centered_logo_col, _ = st.columns((1, 1, 1))
        with centered_logo_col:
            st.image("images/white_logo_color1_background.png", width=320)
    st.title(str(START_PAGE_COPY["hero_headline"]))
    hero_subheadline = str(START_PAGE_COPY["hero_subheadline"])
    if hero_subheadline:
        st.subheader(hero_subheadline)
    st.markdown(str(START_PAGE_COPY["hero_supporting_paragraph"]))

    st.markdown("### Einstiegsoptionen")
    st.caption("Jobspec hochladen · Text einfügen · Jetzt analysieren")
    render_jobad_intake(ctx, title=str(START_PAGE_COPY["primary_cta"]))

    if _has_completed_landing_analysis():
        with st.expander("Über diesen Prozess", expanded=False):
            _render_landing_explainer_sections()
    else:
        _render_landing_explainer_sections()


PAGE = WizardPage(
    key="landing",
    title_de="Start",
    icon="🏁",
    render=render,
    requires_jobspec=False,
)
