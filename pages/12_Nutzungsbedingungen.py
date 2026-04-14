from components.layout import SectionBlock, render_standard_page

render_standard_page(
    eyebrow="Rechtliche Information",
    title="Nutzungsbedingungen (Template)",
    intro=[
        "Diese Nutzungsbedingungen liegen als Entwurf vor.",
        "Sie sind bis zur rechtlichen Freigabe nicht als verbindliche Vertragsgrundlage zu verstehen.",
    ],
    sections=[
        SectionBlock(
            "Anwendungsbereich",
            ["Die Bedingungen regeln den vorgesehenen Nutzungsrahmen der Anwendung."],
        ),
        SectionBlock(
            "Pflichtinformationen",
            [
                "Leistungsbeschreibung, zulässige Nutzung und Haftungsrahmen werden juristisch präzisiert."
            ],
        ),
        SectionBlock(
            "Rollen / Verantwortlichkeiten",
            [
                "Verantwortlichkeiten zwischen Anbieter, Organisation und Endnutzenden werden abschließend festgelegt."
            ],
        ),
        SectionBlock(
            "Fristen, Rechte, Kontaktwege",
            [
                "Meldewege bei Verstößen, Support-Kontakte und Reaktionsfenster werden konkretisiert."
            ],
        ),
        SectionBlock(
            "Update-/Versionshinweis",
            [
                "Änderungen werden mit Wirksamkeitsdatum und Versionshinweis veröffentlicht."
            ],
        ),
    ],
    placeholders=[
        (
            "Fehlende Vertragsangaben",
            [
                "Finale Haftungs- und Gewährleistungsklauseln",
                "Kündigungs- und Änderungsmechanik",
            ],
        )
    ],
    trust_heading="Prüfstatus",
    trust_details=[
        "Bis zum Abschluss der juristischen Prüfung bleibt diese Seite ein Arbeitsentwurf."
    ],
    legal_template=True,
    footer_classification="Rechtliche Seite · Template",
)
