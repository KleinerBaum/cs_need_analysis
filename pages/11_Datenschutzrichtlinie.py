# pages/03_Datenschutzrichtlinie.py
from __future__ import annotations

import streamlit as st

from site_ui import PROFILE, inject_site_styles, render_callout, render_cta, render_hero, render_meta_line


st.set_page_config(page_title="Datenschutzrichtlinie", page_icon="🔒", layout="wide")
inject_site_styles()

render_hero(
    title="Datenschutzrichtlinie",
    lead=(
        "Der Schutz personenbezogener Daten ist uns wichtig. Auf dieser Seite informieren wir darüber, "
        "welche Daten bei der Nutzung unserer Website und App verarbeitet werden, zu welchen Zwecken dies geschieht "
        "und welche Rechte betroffene Personen haben."
    ),
    eyebrow="Datenschutz",
)
render_meta_line(f"Stand: {PROFILE.last_updated}")

render_callout(
    "Hinweis",
    (
        "Bitte gleichen Sie diese Seite vor Veröffentlichung mit den tatsächlich eingesetzten Dienstleistern, "
        "Kontaktwegen, Speicherfristen und internen Prozessen ab."
    ),
    tone="warning",
)

st.markdown("## 1. Verantwortlicher")
st.markdown(
    f"""
**{PROFILE.legal_entity}**  
{PROFILE.street}  
{PROFILE.postal_code} {PROFILE.city}  
{PROFILE.country}

**E-Mail:** {PROFILE.email}  
**Telefon:** {PROFILE.phone}  
**Website:** {PROFILE.website}
"""
)

st.markdown("## 2. Datenschutzkontakt")
st.markdown(
    f"""
Fragen zum Datenschutz können an folgende Stelle gerichtet werden:

**E-Mail:** {PROFILE.privacy_email}  
**Datenschutzbeauftragte Person / Stelle:** {PROFILE.dpo_name}
"""
)

st.markdown("## 3. Welche Daten wir verarbeiten")
st.markdown(
    """
Je nach Nutzung der Website und App können insbesondere folgende Daten verarbeitet werden:

- technische Zugriffsdaten und Protokolldaten,
- Kontakt- und Kommunikationsdaten,
- Inhalte, die Nutzerinnen und Nutzer aktiv eingeben oder hochladen,
- Nutzungs- und Einstellungsdaten,
- Einwilligungs- und Präferenzdaten, soweit einschlägig,
- organisationsbezogene Informationen im Rahmen der App-Nutzung.
"""
)

st.markdown("## 4. Zwecke der Verarbeitung")
st.markdown(
    """
Wir verarbeiten Daten insbesondere zu folgenden Zwecken:

- Bereitstellung und Betrieb der Website und App,
- Bearbeitung von Anfragen,
- strukturierte Aufbereitung von Recruiting- und Stelleninformationen,
- Generierung von Folgeartefakten innerhalb der Anwendung,
- Gewährleistung von IT-Sicherheit, Fehleranalyse und Missbrauchsprävention,
- Nachweis- und Dokumentationspflichten.
"""
)

st.markdown("## 5. Besondere Hinweise zu HR-Inhalten")
st.markdown(
    """
Unsere Anwendung kann zur Verarbeitung von Stelleninformationen, Jobspecs und vergleichbaren Dokumenten genutzt werden.  
Bitte laden Sie nur solche Inhalte hoch oder übermitteln Sie nur solche Informationen, deren Verarbeitung zulässig, erforderlich und intern freigegeben ist.

Besonders sensible personenbezogene Daten sollten nur dann verarbeitet werden, wenn hierfür eine tragfähige rechtliche Grundlage und ein geeigneter organisatorischer Rahmen bestehen.
"""
)

st.markdown("## 6. Rechtsgrundlagen")
st.markdown(
    """
Die Verarbeitung erfolgt – je nach Fallgestaltung – insbesondere auf Grundlage von:

- Art. 6 Abs. 1 lit. a DSGVO,
- Art. 6 Abs. 1 lit. b DSGVO,
- Art. 6 Abs. 1 lit. c DSGVO,
- Art. 6 Abs. 1 lit. f DSGVO.

Soweit besondere Kategorien personenbezogener Daten betroffen sind, gelten zusätzlich die hierfür einschlägigen spezialgesetzlichen und datenschutzrechtlichen Anforderungen.
"""
)

st.markdown("## 7. Empfänger und eingesetzte Dienstleister")
for provider in PROFILE.service_providers:
    st.markdown(f"- {provider}")

st.markdown(
    """
Sofern externe technische Dienstleister oder KI-Dienste eingebunden sind, erfolgt dies nur im Rahmen der jeweils vorgesehenen technischen, organisatorischen und vertraglichen Vorkehrungen.
"""
)

st.markdown("## 8. Speicherung und Löschung")
st.markdown(
    """
Wir speichern personenbezogene Daten nur so lange, wie dies für die jeweiligen Zwecke erforderlich ist oder gesetzliche Aufbewahrungspflichten dies verlangen.

Soweit Inhalte innerhalb der Anwendung verarbeitet werden, sollte die Verarbeitung auf das erforderliche Maß begrenzt und organisatorisch kontrolliert werden. Exportierte Dokumente und Folgeartefakte unterliegen zusätzlich den Regeln der jeweiligen Nutzerorganisation.
"""
)

st.markdown("## 9. Cookies und ähnliche Technologien")
st.markdown(
    """
Wir verwenden Cookies und vergleichbare Technologien nur im jeweils erforderlichen Umfang.  
Soweit nicht unbedingt erforderliche Technologien eingesetzt werden, erfolgt dies nur auf der Grundlage einer wirksamen Einwilligung oder einer sonst einschlägigen Rechtsgrundlage.

Weitere Informationen finden Sie in unserer Cookie Policy.
"""
)

st.markdown("## 10. Ihre Rechte")
st.markdown(
    """
Betroffene Personen haben im Rahmen der gesetzlichen Voraussetzungen insbesondere das Recht auf:

- Auskunft,
- Berichtigung,
- Löschung,
- Einschränkung der Verarbeitung,
- Datenübertragbarkeit,
- Widerspruch,
- Widerruf erteilter Einwilligungen mit Wirkung für die Zukunft,
- Beschwerde bei einer zuständigen Aufsichtsbehörde.
"""
)

st.markdown("## 11. Datensicherheit")
st.markdown(
    """
Wir treffen angemessene technische und organisatorische Maßnahmen, um personenbezogene Daten vor Verlust, Manipulation, unberechtigtem Zugriff und sonstigen Risiken zu schützen.

Dazu gehören insbesondere Maßnahmen zur Zugriffskontrolle, zur Begrenzung unnötiger Datenverarbeitung, zur sicheren Konfiguration der eingesetzten Systeme und zur nachvollziehbaren Steuerung sensibler Prozesse.
"""
)

render_cta(
    "Fragen zum Datenschutz",
    f"Für datenschutzbezogene Anliegen erreichen Sie uns unter **{PROFILE.privacy_email}**.",
)
