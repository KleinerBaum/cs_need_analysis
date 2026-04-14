from components.layout import SectionBlock, render_standard_page

render_standard_page(
    eyebrow="Rechtliche Information",
    title="Cookie Policy / Settings (Template)",
    intro=[
        "Dieses Modul ist vorbereitet, die konkrete Ausgestaltung der Einwilligungslogik ist noch offen.",
        "Die Seite bleibt bis zur Freigabe ein Platzhalter.",
    ],
    sections=[
        SectionBlock(
            "Anwendungsbereich",
            [
                "Die Policy soll den Einsatz von Cookies und vergleichbaren Technologien in dieser Anwendung beschreiben."
            ],
        ),
        SectionBlock(
            "Pflichtinformationen",
            [
                "Kategorien, Zwecke, Speicherdauer und Drittanbieter werden nach technischer und rechtlicher Abstimmung ergänzt."
            ],
        ),
        SectionBlock(
            "Rollen / Verantwortlichkeiten",
            [
                "Verantwortlichkeiten für Consent-Management und technische Umsetzung werden benannt."
            ],
        ),
        SectionBlock(
            "Fristen, Rechte, Kontaktwege",
            [
                "Widerrufs- und Änderungswege für Einwilligungen werden nach Implementierung konkret dokumentiert."
            ],
        ),
        SectionBlock(
            "Update-/Versionshinweis",
            ["Neue Cookie-Kategorien oder Vendoren werden versioniert ausgewiesen."],
        ),
    ],
    placeholders=[
        (
            "Fehlende Cookie-Inputs",
            [
                "Aktuelle Cookie-/Storage-Inventarliste",
                "Abgestimmte Consent-Banner- und Preference-Center-Logik",
            ],
        )
    ],
    trust_heading="Prüfstatus",
    trust_details=[
        "Rechtlich verbindliche Aussagen erfolgen erst nach Review von Legal und Engineering."
    ],
    legal_template=True,
    footer_classification="Rechtliche Seite · Template",
)
