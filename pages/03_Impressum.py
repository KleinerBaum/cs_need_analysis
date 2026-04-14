from components.layout import SectionBlock, render_standard_page

render_standard_page(
    eyebrow="Rechtliche Information",
    title="Impressum (Template)",
    intro=[
        "Diese Seite ist als rechtliche Vorlage vorbereitet.",
        "Verbindliche Angaben werden erst nach juristischer Freigabe ergänzt.",
    ],
    sections=[
        SectionBlock(
            "Anwendungsbereich",
            [
                "Gilt für die Nutzung dieser Anwendung und der zugehörigen Informationsseiten."
            ],
        ),
        SectionBlock(
            "Pflichtinformationen",
            [
                "Angaben zu Anbieter, Vertretung, Registerdaten und Kontakt werden nachgereicht."
            ],
        ),
        SectionBlock(
            "Rollen / Verantwortlichkeiten",
            [
                "Verantwortliche Stelle für Inhalt und Betrieb wird mit Freigabe namentlich benannt."
            ],
        ),
        SectionBlock(
            "Fristen, Rechte, Kontaktwege",
            [
                "Verbindliche Kontaktwege für rechtliche Anliegen werden nach Prüfung ergänzt."
            ],
        ),
        SectionBlock(
            "Update-/Versionshinweis",
            [
                "Versionierung erfolgt mit Datum und Änderungszusammenfassung nach jeder rechtlichen Aktualisierung."
            ],
        ),
    ],
    placeholders=[
        (
            "Fehlende Rechtsangaben",
            [
                "Firmenname und ladungsfähige Anschrift",
                "Handelsregister, USt-IdNr., vertretungsberechtigte Person(en)",
            ],
        )
    ],
    trust_heading="Rechtlicher Hinweis",
    trust_details=[
        "Bis zur Freigabe ist diese Seite nicht als abschließende Rechtsinformation zu verwenden."
    ],
    legal_template=True,
    footer_classification="Rechtliche Seite · Template",
)
