from components.layout import SectionBlock, render_standard_page

render_standard_page(
    eyebrow="Rechtliche Information",
    title="Erklärung zur Barrierefreiheit (Template)",
    intro=[
        "Diese Erklärung ist als Vorlage angelegt und wird schrittweise mit Prüfergebnissen ergänzt.",
        "Bis zur finalen Prüfung ist sie nicht als vollständige Konformitätserklärung zu lesen.",
    ],
    sections=[
        SectionBlock(
            "Anwendungsbereich",
            [
                "Die Erklärung bezieht sich auf die Zugänglichkeit der Webanwendung und ihrer Kernfunktionen."
            ],
        ),
        SectionBlock(
            "Pflichtinformationen",
            [
                "Konformitätsstatus, bekannte Barrieren und Ausnahmetatbestände werden nach Audit präzisiert."
            ],
        ),
        SectionBlock(
            "Rollen / Verantwortlichkeiten",
            [
                "Zuständigkeiten für Monitoring, Korrekturmaßnahmen und Kommunikation werden festgelegt."
            ],
        ),
        SectionBlock(
            "Fristen, Rechte, Kontaktwege",
            [
                "Meldeweg für Barrieren und erwartete Bearbeitungsfristen werden veröffentlicht."
            ],
        ),
        SectionBlock(
            "Update-/Versionshinweis",
            ["Fortschritte und neue Prüfstände werden mit Datum dokumentiert."],
        ),
    ],
    placeholders=[
        (
            "Fehlende Accessibility-Inputs",
            [
                "Aktueller Auditstatus nach Standard (z. B. WCAG/EN 301 549)",
                "Priorisierte Maßnahmenliste mit Zielterminen",
            ],
        )
    ],
    trust_heading="Prüfstatus",
    trust_details=[
        "Diese Seite bleibt bis zur fachlichen und rechtlichen Freigabe eine Vorlage."
    ],
    legal_template=True,
    footer_classification="Rechtliche Seite · Template",
)
