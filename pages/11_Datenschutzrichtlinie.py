from components.layout import SectionBlock, render_standard_page

render_standard_page(
    eyebrow="Rechtliche Information",
    title="Datenschutzrichtlinie (Template)",
    intro=[
        "Diese Datenschutzrichtlinie ist eine Vorlage und wird derzeit rechtlich geprüft.",
        "Sie beschreibt den vorgesehenen Informationsrahmen, nicht den finalen Rechtsstand.",
    ],
    sections=[
        SectionBlock(
            "Anwendungsbereich",
            ["Erfasst wird die Verarbeitung im Rahmen der Nutzung dieser Anwendung."],
        ),
        SectionBlock(
            "Pflichtinformationen",
            [
                "Rechtsgrundlagen, Datenkategorien, Empfänger und Speicherfristen werden nach juristischer Freigabe finalisiert."
            ],
        ),
        SectionBlock(
            "Rollen / Verantwortlichkeiten",
            [
                "Rollen von Verantwortlichem, Auftragsverarbeitern und ggf. gemeinsamen Verantwortlichen werden konkret benannt."
            ],
        ),
        SectionBlock(
            "Fristen, Rechte, Kontaktwege",
            [
                "Auskunfts-, Berichtigungs-, Lösch- und Widerspruchswege inklusive Fristen folgen mit Freigabe."
            ],
        ),
        SectionBlock(
            "Update-/Versionshinweis",
            ["Änderungen werden mit Versionsstand und Gültigkeitsdatum dokumentiert."],
        ),
    ],
    placeholders=[
        (
            "Fehlende Datenschutz-Inputs",
            [
                "Verzeichnis der Verarbeitungstätigkeiten",
                "DPO-/Privacy-Kontakt und Meldestrecken für Betroffenenanfragen",
            ],
        )
    ],
    trust_heading="Prüfstatus",
    trust_details=[
        "Die finale Fassung wird erst nach rechtlicher und organisatorischer Abstimmung veröffentlicht."
    ],
    legal_template=True,
    footer_classification="Rechtliche Seite · Template",
)
