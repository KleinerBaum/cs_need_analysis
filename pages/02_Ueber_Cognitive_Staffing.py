from components.layout import SectionBlock, render_standard_page

render_standard_page(
    eyebrow="Unternehmen",
    title="Über Cognitive Staffing",
    intro=[
        "Cognitive Staffing entwickelt strukturierte Workflows für präzise Rollenklärung im Recruiting.",
        "Diese Übersicht dokumentiert den aktuellen Zielzustand und offene Punkte transparent.",
    ],
    sections=[
        SectionBlock(
            "Mission",
            [
                "Wir reduzieren Interpretationsspielräume im Hiring-Prozess durch klare, belastbare Intake-Strukturen."
            ],
        ),
        SectionBlock(
            "Differenzierung",
            [
                "Der Ansatz verbindet strukturierte Datenerfassung, externe Klassifikationen und modellgestützte Assistenz mit prüfbaren Ergebnissen."
            ],
        ),
        SectionBlock(
            "Zielgruppen",
            [
                "Adressiert werden interne Recruiting-Teams, HR-Operations und Fachbereiche mit wiederkehrendem Rollenbedarf."
            ],
        ),
        SectionBlock(
            "Prinzipien",
            [
                "Priorisiert werden Nachvollziehbarkeit, Datenminimierung und konkrete Entscheidungsunterstützung."
            ],
        ),
        SectionBlock(
            "Roadmap",
            [
                "Kurzfristig liegt der Schwerpunkt auf Stabilität, Qualitätssicherung und klaren Exportpfaden für Folgeprozesse."
            ],
        ),
    ],
    placeholders=[
        (
            "Fehlende Unternehmensangaben",
            [
                "Veröffentlichbare Unternehmenshistorie und Rechtsformangabe",
                "Offizielle Roadmap-Termine mit Verantwortlichkeiten",
            ],
        )
    ],
    trust_heading="Hinweis zur Einordnung",
    trust_details=[
        "Diese Seite ist eine Produkt-/Unternehmensübersicht und ersetzt keine vertragliche Zusicherung."
    ],
    footer_classification="Unternehmensprofil",
)
