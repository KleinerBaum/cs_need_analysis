# pages/07_Erklaerung_zur_Barrierefreiheit.py
from __future__ import annotations

import streamlit as st

from site_ui import PROFILE, inject_site_styles, render_callout, render_cta, render_hero, render_meta_line


st.set_page_config(page_title="Erklärung zur Barrierefreiheit", page_icon="♿", layout="wide")
inject_site_styles()

render_hero(
    title="Erklärung zur Barrierefreiheit",
    lead=(
        "Wir möchten unsere Website und digitalen Inhalte möglichst barrierearm und gut zugänglich gestalten. "
        "Dabei orientieren wir uns an anerkannten Standards der digitalen Barrierefreiheit und entwickeln die Nutzbarkeit fortlaufend weiter."
    ),
    eyebrow="Barrierefreiheit",
)
render_meta_line(f"Stand: {PROFILE.last_updated}")

render_callout(
    "Rechtliche Einordnung",
    (
        "Bitte prüfen Sie vor Veröffentlichung, in welchem Umfang BITV 2.0 oder BFSG auf Ihr konkretes Angebot "
        "unmittelbar anwendbar sind. Diese Seite ist bewusst als seriöse, freiwillig nutzbare Erklärung formuliert."
    ),
    tone="warning",
)

st.markdown("## Stand der Vereinbarkeit")
st.markdown(
    """
Diese Website ist derzeit **teilweise barrierefrei**.  
Wir arbeiten fortlaufend daran, Nutzbarkeit, Verständlichkeit und technische Zugänglichkeit weiter zu verbessern.
"""
)

st.markdown("## Unser Anspruch")
st.markdown(
    """
Wir möchten, dass Inhalte möglichst verständlich, klar strukturiert und in unterschiedlichen Nutzungssituationen zugänglich sind.  
Dazu orientieren wir uns insbesondere an:
- klarer Informationsarchitektur,
- guter Lesbarkeit,
- kontrastbewusster Gestaltung,
- konsistenter Navigation,
- schrittweiser Verbesserung interaktiver Komponenten.
"""
)

st.markdown("## Bereits umgesetzte Maßnahmen")
st.markdown(
    """
- klare Überschriften- und Abschnittslogik,
- kompakte, möglichst verständliche Texte,
- konsistente Navigationsmuster,
- fortlaufende Überprüfung von Kontrasten und Darstellungslogik,
- laufende Optimierung der Bedienbarkeit in dynamischen Oberflächen.
"""
)

st.markdown("## Noch bestehende Barrieren")
st.markdown(
    """
Trotz unserer Bemühungen können derzeit noch Einschränkungen bestehen, insbesondere:
- bei einzelnen interaktiven Komponenten,
- bei Tastaturbedienung und Fokusführung,
- bei dynamisch eingeblendeten oder generierten Inhalten,
- bei Dokumenten oder exportierten Dateien,
- bei komplexeren visuellen oder datengetriebenen Darstellungen.
"""
)

st.markdown("## Feedback und Kontakt")
st.markdown(
    f"""
Wenn Sie Barrieren auf unserer Website feststellen oder Inhalte in einer besser zugänglichen Form benötigen, kontaktieren Sie uns bitte:

**E-Mail:** {PROFILE.accessibility_email}  
**Allgemeiner Kontakt:** {PROFILE.email}
"""
)

st.markdown("## Durchsetzungs- oder Schlichtungshinweise")
st.markdown(
    """
Soweit gesetzlich erforderlich oder im konkreten Anwendungsfall vorgesehen, können ergänzende Hinweise auf zuständige Schlichtungs- oder Beschwerdestellen aufgenommen werden.
"""
)

render_cta(
    "Barrieren melden",
    f"Wir freuen uns über konkrete Hinweise, damit wir die Zugänglichkeit unserer Inhalte gezielt weiter verbessern können. Kontakt: **{PROFILE.accessibility_email}**",
)
