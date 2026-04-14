from components.layout import SectionBlock, render_standard_page

render_standard_page(
    eyebrow="Kontakt & Support",
    title="Kontakt",
    intro=[
        "Diese Seite beschreibt, welche Kontaktwege für welche Anliegen vorgesehen sind.",
        "Konkrete Kontaktadressen werden erst nach organisatorischer Freigabe ergänzt.",
    ],
    sections=[
        SectionBlock(
            "Anfrageart",
            [
                "Anfragen werden nach Fachfrage, Betriebsstörung, Datenschutzanliegen oder rechtlichem Hinweis unterschieden."
            ],
        ),
        SectionBlock(
            "Routing-Logik",
            [
                "Jede Anfrageart wird an das zuständige Team geroutet; Eskalationen folgen einer definierten Prioritätslogik."
            ],
        ),
        SectionBlock(
            "Datenschutzbezug",
            [
                "Für Anfragen mit Personenbezug gelten minimierte Datenerhebung und zweckgebundene Verarbeitung."
            ],
        ),
        SectionBlock(
            "Erwartete Reaktionszeit",
            [
                "Zielwerte werden nach Finalisierung der Supportprozesse transparent ausgewiesen."
            ],
        ),
    ],
    placeholders=[
        (
            "Fehlende Kontaktangaben",
            [
                "Veröffentlichbare E-Mail-Adressen/Servicekanäle",
                "SLA-Matrix nach Anfrageart",
            ],
        )
    ],
    trust_heading="Hinweis zur Verbindlichkeit",
    trust_details=[
        "Die Prozessbeschreibung ist vorläufig, bis organisatorische Freigaben vorliegen."
    ],
    footer_classification="Kontaktseite",
)
