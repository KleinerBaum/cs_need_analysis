# pages/04_Nutzungsbedingungen.py
from __future__ import annotations

import streamlit as st

from site_ui import PROFILE, inject_site_styles, render_callout, render_cta, render_hero, render_meta_line


st.set_page_config(page_title="Nutzungsbedingungen", page_icon="📄", layout="wide")
inject_site_styles()

render_hero(
    title="Nutzungsbedingungen",
    lead=(
        "Diese Nutzungsbedingungen regeln die Nutzung unserer Website und der bereitgestellten App-Funktionen. "
        "Bitte lesen Sie die folgenden Hinweise sorgfältig."
    ),
    eyebrow="Rechtliches",
)
render_meta_line(f"Stand: {PROFILE.last_updated}")

st.markdown("## 1. Gegenstand des Angebots")
st.markdown(
    """
Cognitive Staffing stellt digitale Funktionen zur strukturierten Erfassung, Aufbereitung und Weiterverarbeitung von Recruiting- und Stelleninformationen bereit.

Das Angebot dient der Unterstützung von Recruiting-, HR- und Abstimmungsprozessen. Es handelt sich nicht um ein autonom entscheidendes System.
"""
)

st.markdown("## 2. Kein Ersatz für Rechts- oder Personalberatung")
st.markdown(
    """
Die innerhalb der Anwendung erzeugten Inhalte und Ergebnisse dienen der fachlichen Unterstützung.  
Sie stellen weder Rechtsberatung noch eine verbindliche Personalentscheidung oder eine automatische Eignungsbewertung dar.

Alle Ergebnisse sind vor der weiteren Verwendung eigenverantwortlich zu prüfen.
"""
)

st.markdown("## 3. Zulässige Nutzung")
st.markdown(
    """
Die Nutzung ist nur im Einklang mit geltendem Recht und nur mit solchen Inhalten zulässig, zu deren Verarbeitung Sie berechtigt sind.

Untersagt ist insbesondere die Nutzung für:
- rechtswidrige oder diskriminierende Inhalte,
- missbräuchliche oder sicherheitsgefährdende Zwecke,
- die Verarbeitung unzulässiger oder unbefugt übermittelter Daten,
- Versuche der Manipulation, Überlastung oder Umgehung technischer Schutzmechanismen.
"""
)

st.markdown("## 4. Verantwortung der Nutzerinnen und Nutzer")
st.markdown(
    """
Nutzerinnen und Nutzer sind insbesondere dafür verantwortlich,

- nur rechtmäßig verarbeitbare Daten einzugeben,
- erzeugte Ergebnisse fachlich zu prüfen,
- interne Richtlinien und rechtliche Anforderungen einzuhalten,
- geeignete Schutzmaßnahmen im eigenen organisatorischen Umfeld sicherzustellen.
"""
)

st.markdown("## 5. Verfügbarkeit")
st.markdown(
    """
Wir bemühen uns um eine möglichst stabile und unterbrechungsfreie Bereitstellung des Angebots.  
Ein Anspruch auf permanente Verfügbarkeit besteht jedoch nicht. Wartungen, Weiterentwicklungen, technische Störungen oder externe Abhängigkeiten können zu Einschränkungen führen.
"""
)

st.markdown("## 6. Änderungen des Angebots")
st.markdown(
    """
Wir behalten uns vor, Inhalte, Funktionen und technische Ausgestaltungen anzupassen, weiterzuentwickeln, einzuschränken oder einzustellen, soweit hierfür ein sachlicher Grund besteht.
"""
)

st.markdown("## 7. Geistiges Eigentum")
st.markdown(
    """
Sämtliche Inhalte, Marken, Texte, Designs, Softwarebestandteile und sonstigen geschützten Elemente dieser Website und App bleiben – soweit nicht anders angegeben – unser Eigentum oder das Eigentum der jeweiligen Rechteinhaber.
"""
)

st.markdown("## 8. Haftung")
st.markdown(
    """
Wir haften nach Maßgabe der gesetzlichen Vorschriften.

Für automatisch oder unterstützend erzeugte Inhalte übernehmen wir keine Gewähr für Vollständigkeit, rechtliche Zulässigkeit, wirtschaftliche Eignung oder Fehlerfreiheit im Einzelfall. Nutzerinnen und Nutzer bleiben zur eigenständigen Prüfung verpflichtet.
"""
)

render_callout(
    "Wichtige Einordnung",
    (
        "Cognitive Staffing unterstützt strukturierte Entscheidungen. "
        "Die Verantwortung für fachliche, rechtliche und organisatorische Freigaben verbleibt bei den nutzenden Personen bzw. Organisationen."
    ),
)

st.markdown("## 9. Schlussbestimmungen")
st.markdown(
    """
Es gilt das Recht der Bundesrepublik Deutschland, soweit dem keine zwingenden gesetzlichen Vorschriften entgegenstehen.

Sollten einzelne Bestimmungen dieser Nutzungsbedingungen ganz oder teilweise unwirksam sein oder werden, bleibt die Wirksamkeit der übrigen Bestimmungen unberührt.
"""
)

render_cta(
    "Kontakt bei Rückfragen",
    f"Bei Fragen zu diesen Nutzungsbedingungen erreichen Sie uns unter **{PROFILE.email}**.",
)
