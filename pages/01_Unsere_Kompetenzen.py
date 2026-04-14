# pages/01_Unsere_Kompetenzen.py
from __future__ import annotations

import streamlit as st

from pages._site_ui import (
    PROFILE,
    inject_site_styles,
    render_callout,
    render_cards,
    render_cta,
    render_hero,
    render_meta_line,
)


st.set_page_config(page_title="Unsere Kompetenzen", page_icon="🧠", layout="wide")
inject_site_styles()

render_hero(
    title="Unsere Kompetenzen",
    lead=(
        "Wir professionalisieren den ersten Schritt jedes Recruiting-Prozesses: den Vacancy Intake. "
        "Aus unstrukturierten Eingangsinformationen entsteht ein klarer, belastbarer und weiterverwendbarer "
        "Datensatz, der Suche, Auswahl und interne Abstimmung von Beginn an verbessert."
    ),
    eyebrow="Vacancy Intake · ESCO · KI · Struktur",
)
render_meta_line(
    "Fokus: strukturierter Intake, semantische Qualität, kontrollierte KI-Nutzung, Sicherheit und Weiterverarbeitung"
)

render_cards(
    [
        {
            "title": "Strukturierter Vacancy Intake",
            "body": (
                "Wir setzen nicht erst bei der Jobanzeige an, sondern bei der Bedarfsklärung. "
                "So werden Missverständnisse, spätere Korrekturschleifen und überladene Wunschprofile früh reduziert."
            ),
        },
        {
            "title": "Dynamischer Fragenfluss",
            "body": (
                "Die App arbeitet nicht mit einem starren Standardformular. "
                "Sie leitet aus Jobspec, Rolle, Kontext und bisherigen Antworten genau die Fragen ab, die wirklich relevant sind."
            ),
        },
        {
            "title": "ESCO-gestützte Semantik",
            "body": (
                "Berufe und Skills werden nicht nur sprachlich erfasst, sondern semantisch verankert. "
                "Das verbessert Vergleichbarkeit, Klarheit und Anschlussfähigkeit in internationalen Recruiting-Kontexten."
            ),
        },
        {
            "title": "Kontrollierte KI-Unterstützung",
            "body": (
                "KI wird dort eingesetzt, wo sie Struktur schafft und Inhalte verdichtet. "
                "Nicht als Selbstzweck, sondern innerhalb eines klaren, nachvollziehbaren Workflows."
            ),
        },
        {
            "title": "Salary Estimation",
            "body": (
                "Eine indikative Gehaltsprognose macht sichtbar, wie einzelne Parameter die Vergütung beeinflussen. "
                "Dadurch werden Stellen realistischer und marktnäher formuliert."
            ),
        },
        {
            "title": "Weiterverarbeitung & Exporte",
            "body": (
                "Aus derselben Datengrundlage lassen sich Recruiting Brief, Job Ad, Interview Sheets, "
                "Boolean Search Strings und weitere Artefakte direkt ableiten."
            ),
        },
    ],
    columns=3,
)

st.markdown("## Wie die App arbeitet")
st.markdown(
    """
Die App beginnt mit einer Jobspec, einem Upload oder Freitext. Diese Ausgangsbasis wird zuerst analysiert und in eine belastbare Struktur überführt. 
Darauf aufbauend entsteht ein rollenabhängiger Frageplan, der Nutzerinnen und Nutzer Schritt für Schritt durch die weitere Präzisierung führt.

Das Ziel ist kein längerer Prozess, sondern ein besserer: weniger unnötige Fragen, weniger Interpretationsspielraum und eine deutlich höhere Wiederverwendbarkeit der Ergebnisse.
"""
)

with st.expander("1. Intake statt Rätselraten", expanded=True):
    st.markdown(
        """
Zu Beginn werden vorhandene Stelleninformationen aufgenommen und strukturiert analysiert. Die App trennt dabei bewusst zwischen Quelle, Interpretation und Bestätigung.  
So entsteht früh ein belastbarer Startpunkt für den weiteren Recruiting-Prozess.

**Mehrwert**
- weniger unklare Ausgangslagen,
- weniger Rückfragen zwischen Fachbereich und Recruiting,
- frühere Qualitätssicherung im Prozess.
"""
    )

with st.expander("2. Dynamischer Fragenfluss statt Formular-Overkill", expanded=True):
    st.markdown(
        """
Auf Basis der bereits bekannten Informationen erzeugt die App einen **dynamischen Fragenfluss**.  
Sichtbar werden zuerst die wichtigsten Themen; zusätzliche Tiefe wird nur dort geöffnet, wo Informationslücken bestehen oder Präzisierungen sinnvoll sind.

**Das bedeutet konkret**
- minimale Reibung für Fachbereiche,
- höhere Eingabequalität,
- bessere Akzeptanz im Alltag,
- klare Trennung zwischen Kerninformationen und Details.
"""
    )

with st.expander("3. Schärfung statt eierlegender Wollmilchsau", expanded=True):
    st.markdown(
        """
Aufgaben, Anforderungen, Skills, Benefits und Gehaltslogik werden nicht nur gesammelt, sondern gegeneinander kalibriert.  
Dadurch sinkt das Risiko, unrealistische Stellenprofile zu formulieren, die am Markt kaum besetzbar sind.

**Ergebnis**
- realistischere Zielprofile,
- sauberere Trennung von Must-have und Nice-to-have,
- bessere Grundlage für spätere Suche und Interviews.
"""
    )

st.markdown("## ESCO als semantischer Anker")
st.markdown(
    """
Mit ESCO integriert Cognitive Staffing eine europaweit etablierte, mehrsprachige Klassifikation für Skills, Competences, Qualifications und Occupations.  
ESCO funktioniert dabei wie ein gemeinsames semantisches Vokabular, das Begriffe nicht nur beschreibt, sondern auch in ihren Beziehungen maschinenlesbar macht.
"""
)

render_callout(
    "Warum ESCO in dieser App so wertvoll ist",
    (
        "Statt nur freie Rollen- und Skillbezeichnungen zu sammeln, kann die App Occupations und Skills semantisch verankern. "
        "Das erhöht Konsistenz, Vergleichbarkeit und die Qualität späterer Ableitungen."
    ),
)

col_a, col_b = st.columns(2)

with col_a:
    st.markdown(
        """
### Was ESCO mitbringt
- standardisierte Occupations und Skills,
- mehrsprachige Begriffe,
- API-Zugriff für technische Einbindung,
- Beziehungen zwischen Berufen, Skills und Wissensbereichen,
- maschinenlesbare Konzepte statt bloßer Stichwörter.
"""
    )

with col_b:
    st.markdown(
        """
### Mehrwert für Cognitive Staffing
- saubereres Occupation-Mapping,
- normalisierte Skill-Vorschläge,
- nachvollziehbare Herkunft von Empfehlungen,
- bessere Anschlussfähigkeit für Suche, Matching und Reporting,
- stabilere Begriffslogik über Teams und Standorte hinweg.
"""
    )

st.markdown(
    """
Gerade weil ESCO Occupations und Skills nicht nur als Wörter, sondern als verknüpfte Konzepte beschreibt, eignet sich die Klassifikation sehr gut für ein strukturiertes Vacancy Intake.
"""
)

st.markdown("## Verwendetes ChatGPT-Modell und KI-Architektur")
st.markdown(
    """
Die App nutzt die OpenAI API **aufgabenbezogen**. Das bedeutet: Nicht jede Funktion wird zwangsläufig mit demselben Modell ausgeführt.  
Je nach Task – etwa Extraktion, Frageplanung oder Artefaktgenerierung – kann unterschiedlich geroutet werden.

Wichtig ist deshalb nicht nur das Modell selbst, sondern die **kontrollierte Form der Ausgabe**:
- strukturierte Ergebnisse statt bloßer Fließtexte,
- klare Schemata statt freier Halluzinationsflächen,
- bessere Weiterverarbeitung innerhalb des Wizards.
"""
)

render_callout(
    "Wichtige Einordnung",
    (
        "Die produktive Konfiguration ist modellabhängig und deploymentabhängig. "
        "Damit bleibt die Architektur flexibel, ohne die Qualität des Workflows an ein einziges festes Modell zu ketten."
    ),
)

st.markdown("## Dynamischer Fragenfluss")
st.markdown(
    """
Der Fragenfluss passt sich an:
- die eingebrachte Jobspec,
- bereits identifizierte Informationen,
- den gewählten Detailgrad,
- frühere Antworten im Verlauf,
- und die bestätigte semantische Einordnung der Stelle.

So entsteht ein Prozess, der **adaptiv** statt starr arbeitet.  
Nutzerinnen und Nutzer sehen zuerst das Wesentliche – und nur dort mehr Tiefe, wo sie für die konkrete Vakanz tatsächlich Mehrwert schafft.
"""
)

st.markdown("## Weiterverarbeitungsoptionen")
render_cards(
    [
        {
            "title": "Recruiting Brief",
            "body": "Die konsolidierte Entscheidungsgrundlage für Recruiting, Fachbereich und Management.",
        },
        {
            "title": "Job Ad Generation",
            "body": "Aus der strukturierten Datensammlung entsteht eine konsistente, zielgruppengerechte Stellenanzeige.",
        },
        {
            "title": "Interview Sheets",
            "body": "Vorbereitungen für HR und Fachbereich mit klaren Themen, Prüfpunkten und Leitfragen.",
        },
        {
            "title": "Boolean Search Strings",
            "body": "Ableitungen für LinkedIn, Xing oder Google, damit Suchstrategien präziser und reproduzierbarer werden.",
        },
        {
            "title": "Contract Draft",
            "body": "Vorlagennahe Vertragsentwürfe auf Basis derselben strukturierten Rolle.",
        },
        {
            "title": "Exports",
            "body": "Je nach Artefakt als JSON, Markdown, DOCX, PDF oder Mapping-Report weiterverwendbar.",
        },
    ],
    columns=3,
)

st.markdown("## Sicherheit")
st.markdown(
    """
Im HR-Kontext ist Datensensibilität kein Randthema. Deshalb ist Sicherheit für uns Teil der Produktlogik – nicht bloß ein Nachgedanke.

Schon in einem cloudbasierten Setup helfen strukturierte Verarbeitung, klare Exportpfade, kontrollierte Modellaufrufe und Datenminimierung dabei, sensible Inhalte bewusster zu behandeln.
"""
)

with st.expander("Lokales LLM als Sicherheitsoption", expanded=True):
    st.markdown(
        """
Für besonders sensible HR-Themen kann ein **lokal laufendes LLM** oder ein streng isoliertes On-Prem-/VPC-Setup erhebliche Vorteile bringen:

- Daten verbleiben in der eigenen Infrastruktur,
- Zugriffe und Speicherorte sind enger kontrollierbar,
- Drittlandtransfers und externe Abhängigkeiten können reduziert werden,
- Sicherheitsregeln lassen sich unternehmensspezifisch erzwingen,
- Akzeptanz für sensible HR-Prozesse steigt oft deutlich.

**Wichtige Einordnung**  
Ein lokales LLM ist nicht automatisch sicher. Es verschiebt Verantwortung vom externen Anbieter in die eigene Umgebung.  
Richtig umgesetzt bietet es jedoch bei sensiblen Recruiting- und HR-Themen oft mehr Kontrolle, mehr Transparenz und mehr Governance.
"""
    )

render_cta(
    "Sie möchten sehen, wie aus einem unklaren Stellenbedarf ein belastbarer Recruiting-Startpunkt wird?",
    f"Testen Sie {PROFILE.brand_name} und erleben Sie, wie strukturierter Vacancy Intake Recruiting von Anfang an besser macht.",
)
