# wizard_pages/00_landing.py
from __future__ import annotations

import streamlit as st
from constants import APP_TITLE
from wizard_pages.jobad_intake import render_jobad_intake
from wizard_pages.base import (
    LANDING_SECTION_IDS,
    LANDING_STYLE_TOKENS,
    WizardContext,
    WizardPage,
    render_esco_language_toggle,
    render_landing_css,
)

LANDING_COPY: dict[str, object] = {
    "hero_headline": "Der optimale Recruiting-Prozess wird nicht erst in der Jobanzeige gut, sondern startet mit der umfassenden Aufnahme aller jobspezifischen Anforderungen.",
    "hero_subheadline": "",
    "hero_supporting_paragraph": "",
    "primary_cta": "Geben Sie uns ein paar Informationen zu Ihrer Vakanz",
    "secondary_cta_hint": "",
    "next_step_line": "",
    "before_start_title": "",
    "before_start_bullets": (),
    "cta_reassurance": "",
    "cta_helper": "",
    "cta_microcopy": "",
    "value_cards": (),
    "importance_title": "Der optimale Recruiting-Prozess wird nicht erst in der Jobanzeige gut, sondern startet mit der umfassenden Aufnahme aller jobspezifischen Anforderungen.",
    "flow_title": "So funktioniert der Ablauf",
    "flow_steps": (
        (
            "1. Upload starten",
            "Laden Sie Stellenanzeige, Rollenprofil oder Jobspec hoch.",
        ),
        (
            "2. Lücken erkennen",
            "Die App extrahiert Kerndaten und markiert fehlende Informationen.",
        ),
        (
            "3. Antworten schärfen",
            "Sie beantworten gezielte Rückfragen zu Rolle, Team, Skills und Prozess.",
        ),
        (
            "4. Briefing erzeugen",
            "Sie erhalten ein konsistentes Recruiting-Briefing für HR und Fachbereich.",
        ),
    ),
    "security_title": "Datenschutz und Kontrolle",
    "security_body": (
        "Vor der Verarbeitung können sensible personenbezogene Angaben optional reduziert werden. "
        "Ziel ist eine datensparsame, nachvollziehbare Nutzung im Vacancy Intake."
    ),
    "consent_warning": (
        "Start ist gesperrt, bis die Einwilligung bestätigt wurde. "
        "Start is blocked until consent is confirmed."
    ),
    "consent_details_inline": (
        "Wenn für eure Organisation Designated Content freigegeben ist, können diese Inhalte "
        "von OpenAI zu Entwicklungszwecken genutzt werden (inkl. Training, Evaluierung, Tests). "
        "Ihr müsst Endnutzende informieren und – falls erforderlich – Einwilligungen einholen."
    ),
}


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
    st.title(str(LANDING_COPY["hero_headline"]))
    hero_subheadline = str(LANDING_COPY["hero_subheadline"])
    if hero_subheadline:
        st.subheader(hero_subheadline)
    st.markdown(str(LANDING_COPY["hero_supporting_paragraph"]))

    st.markdown(
        f'<section id="{LANDING_SECTION_IDS["importance"]}" class="landing-section">',
        unsafe_allow_html=True,
    )
    st.subheader(str(LANDING_COPY["importance_title"]))
    st.divider()
    st.badge("Klassische Bedarfsanalyse")
    st.subheader("Klassische Bedarfsanalyse")
    st.markdown(
        "Als langjähriger Personalvermittler ist mir die Suche nach der eierlegenden Wollmilchsau bestens bekannt. Unklare Anforderungen führen nicht nur für Personalvermittler zu unpräzisem Sourcing und Diskussionen über die falschen Profile. Unklare Anforderungen führen von den Verantwortlichen unbemerkt dazu, dass das Interesse des perfekten Kandidaten nicht geweckt wird, z.B. indem das essentielle Benefit nicht bekannt gegeben wird. Merklicher wird es für die Verantwortlichen, wenn unpassende Profile vorgestellt werden, Prozesse aufgrund ihrer Länge scheitern oder schlimmstenfalls der Mitarbeiter nach 6 Monaten Probe kündigt, da die Anforderungen in der Realität nicht mit den Vorstellungen des Mitarbeiters übereinstimmen. Der Prozess muss dann komplett neu gestartet werden, was allen Beteiligten nicht nur Zeit kostet, sondern auch viele Dollars"
    )
    st.image("images/iceberg v1.png", width="stretch")
    st.divider()
    cognitive_col, rag_col = st.columns(2, gap="large")
    with cognitive_col:
        st.badge("Cognitive Staffing")
        st.subheader("Wie profitieren Sie von Cognitive Staffing?")
        st.markdown(
            "- **Berufserkennung:** Nach Eingabe eines Stellen- oder Tätigkeitsnamens schlägt die App passende ESCO-Occupations vor. So werden verschiedene Bezeichnungen (z.B. „Full Stack Entwickler“, „Cloud-Engineer“) auf einen eindeutigen Beruf zusammengeführt.\n"
            "- **Skill-Vorschläge:** Sobald ein ESCO-Beruf bestätigt ist, lädt die App die zugehörigen Essential/Nice-to-have Skills. Diese fließen in die KI-gestützte Anforderungsanalyse und Text-Generierung ein.\n"
            "- **KI-Unterstützung (RAG):** Wir nutzen ESCO-Daten in einem Retrieval-Augmented-Generation-Ansatz (RAG). Das bedeutet: Beim Generieren von Texten (z.B. vorgeschlagene Aufgaben oder Umschreibungen) werden relevante ESCO-Beschreibungen und Skill-Listen aus der Wissensdatenbank abgerufen und als Faktenbasis eingesetzt. Dadurch erhält die KI konkreten Kontext statt nur freier Texte.\n"
            "- **Anforderungsnormalisierung:** Unbekannte oder freie Stichworte in einer Stellenanzeige können durch ESCO-Skills ergänzt oder abgeglichen werden. Die App ermöglicht, fehlende Skills zuzuordnen oder als unternehmensspezifisch zu belassen."
        )
    with rag_col:
        st.badge("RAG + LLM")
        st.subheader(
            "Der Retrieval-Augmented-Generation-Ansatz (RAG) in Kombination mit LLM-gestützen Prompts bietet diverse Option zur Weiterverarbeitung der gesammelten Daten:"
        )
        st.markdown(
            "a) Messerscharf formulierte Aufgaben, Must-haves und Nice-to-have Skills und (lokalen und zielgruppenorientierten) Benefits; b) Erwartungsmanagement der Einstellenden durch Gehaltsprognosen, die basierend auf allen eingegebenen Parametern berechnet werden; c) Automatisierung und Optimierung des internen Kommunikationsprozesses; d) Automatisierung und Optimierung diverser Sourcing-Schritte, beginnend bei der Erstellung der Jobad über das Generieren von Boolean-Searchstrings bis hin zur Erstellung des Arbeitsvertrags im Corporate Design"
        )
    st.markdown("</section>", unsafe_allow_html=True)

    st.divider()
    render_jobad_intake(ctx, title=str(LANDING_COPY["primary_cta"]))


PAGE = WizardPage(
    key="landing",
    title_de="Start",
    icon="🏁",
    render=render,
    requires_jobspec=False,
)
