from components.layout import SectionBlock, render_standard_page

render_standard_page(
    eyebrow="Leistungsprofil",
    title="Unsere Kompetenzen",
    intro=[
        "Diese Seite beschreibt, welche Teile des Vacancy-Intake wir fachlich und technisch abdecken.",
        "Der Fokus liegt auf nachvollziehbaren Entscheidungen statt auf generischen Claims.",
    ],
    sections=[
        SectionBlock(
            "Was wir tun",
            [
                "Wir strukturieren die Bedarfsklärung, sichern Eingaben über feste Modelle und erzeugen anschlussfähige Recruiting-Artefakte."
            ],
        ),
        SectionBlock(
            "Wie wir es tun",
            [
                "Wir kombinieren geführte Eingaben, ESCO/EURES-Anreicherung und validierte LLM-Outputs mit klaren Fallbacks."
            ],
        ),
        SectionBlock(
            "Für wen",
            [
                "Für Recruiting-, Hiring- und Fachbereiche, die Rollenanforderungen gemeinsam und revisionsfähig abstimmen müssen."
            ],
        ),
        SectionBlock(
            "Woran Ergebnisse messbar sind",
            [
                "Messbar sind Vollständigkeit kritischer Felder, Konsistenz über Schritte und Qualität der exportierten Ergebnisartefakte."
            ],
        ),
        SectionBlock(
            "Governance / Compliance",
            [
                "Verarbeitungspfade bleiben transparent; sensible Inhalte sollen minimiert und nicht in Debug-Ansichten repliziert werden."
            ],
        ),
    ],
    placeholders=[
        (
            "Fehlende Business-Inputs",
            [
                "Verbindliche KPI-Schwellen (z. B. Time-to-Shortlist, Akzeptanzquote)",
                "Freigegebene Branchen-/Rollensegmente mit Priorisierung",
            ],
        )
    ],
    trust_heading="Vertrauen & Nachvollziehbarkeit",
    trust_details=[
        "Die Seite wird als fachliche Orientierung gepflegt und bei Prozessänderungen versioniert."
    ],
    footer_classification="Produktinformation",
)
