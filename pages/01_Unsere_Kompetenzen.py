from components.layout import SectionBlock, render_standard_page

render_standard_page(
    eyebrow="Leistungsprofil",
    title="Unsere Kompetenzen",
    intro=[
        "Wir professionalisieren den ersten Schritt jedes Recruiting-Prozesses: den Vacancy Intake. Aus unstrukturierten Eingangsinformationen entsteht ein klarer, belastbarer und weiterverwendbarer Datensatz, der Suche, Auswahl und interne Abstimmung von Beginn an verbessert.",
        "Der Fokus liegt auf nachvollziehbaren Entscheidungen statt auf generischen Claims.",
    ],
    sections=[
        SectionBlock(
            "Was wir tun",
            [
                "Jede Stelle ist anders. Genau deshalb arbeitet Cognitive Staffing nicht mit einem starren Standardformular, sondern mit einem dynamischen, rollenabhängigen Fragenfluss. Unsere App führt Nutzerinnen und Nutzer mit minimalem Aufwand zu einer umfassenden, strukturierten Datengrundlage – präzise genug für Recruiting, Fachbereich und Management."
            ],
        ),
        SectionBlock(
            "Wie wir es tun",
            [
                "1. Intake statt Rätselraten
Die App startet direkt dort, wo Recruiting über Erfolg oder Reibung entscheidet: beim ersten Briefing. Jobspecs können als Text oder Datei eingebracht und zunächst strukturiert analysiert werden. So entsteht schon vor der eigentlichen Bearbeitung ein belastbarer Ausgangspunkt.

2. Dynamische Fragen statt Formular-Overkill
Auf Basis der vorhandenen Informationen erzeugt die App einen dynamischen Frageplan. Sichtbar werden genau die Fragen, die für die konkrete Stelle relevant sind. Dadurch bleibt der Prozess schlank, nachvollziehbar und deutlich nutzerfreundlicher als starre Formulare.

3. Schärfung statt Wunschprofil
Aufgaben, Anforderungen, Skills, Benefits und Gehaltslogik werden nicht nur gesammelt, sondern gegeneinander kalibriert. Das reduziert das Risiko, unrealistische Anforderungsprofile zu formulieren und verbessert die Qualität der späteren Suche.

4. Weiterverarbeitung statt Medienbruch
Am Ende steht kein isoliertes Formularergebnis, sondern eine wiederverwendbare Datensammlung. Daraus lassen sich direkt Folgeartefakte und Exporte für Recruiting und interne Prozesse erzeugen.

ESCO als semantischer Anker

Mit ESCO integrieren wir eine europaweit etablierte, maschinenlesbare Klassifikation für Berufe und Skills. ESCO beschreibt 3.039 Occupations und 13.939 Skills in 28 Sprachen und stellt diese auch über APIs bereit. Für Cognitive Staffing bedeutet das: Begriffe werden nicht nur sprachlich erfasst, sondern semantisch verankert. So entstehen konsistentere Rollenprofile, klarere Skill-Cluster und besser vergleichbare Anforderungen.

Was ESCO in der App konkret bringt

Occupation-Mapping
Stellen werden nicht nur frei beschrieben, sondern an bestätigte Occupations angebunden. Das schafft einen semantischen Anker für die gesamte weitere Bearbeitung.

Skill-Normalisierung
Extrahierte Anforderungsbegriffe werden mit ESCO-Skills abgeglichen. Dadurch lassen sich Muss-Kriterien, optionale Skills und offene Freitext-Begriffe sauber trennen.

Explainability
Die semantische Zuordnung bleibt nachvollziehbar. Begriffe werden nicht einfach „irgendwie“ übernommen, sondern mit nachvollziehbarer Herkunft und Bestätigung in den Workflow integriert.

Mehrsprachigkeit und Anschlussfähigkeit
Gerade in internationalen oder standortübergreifenden Recruiting-Setups ist es wertvoll, wenn Rollen und Skills nicht an einer einzigen Schreibweise hängen, sondern in ein sprachübergreifendes Kompetenzmodell eingebettet werden.

Verwendete KI und Modelllogik

Die App ist modellkonfigurierbar. Im aktuellen Setup wird die OpenAI-Integration aufgabenbezogen geroutet: je nach Task können unterschiedliche Modelle genutzt werden; laut aktuellem Repo reichen die Pfade bis in die GPT-5-Familie, mit einem finalen Fallback auf gpt-4o-mini. Entscheidend ist dabei nicht nur das Modell selbst, sondern die kontrollierte Erzeugung strukturierter Ergebnisse.

Warum Structured Outputs wichtig sind

Für Cognitive Staffing reicht „guter Fließtext“ nicht aus. Die App arbeitet deshalb mit strukturierten Ausgaben, die an definierte Schemata gebunden sind. Das erhöht Zuverlässigkeit, verringert Parsing-Fehler und macht Folgeprozesse robuster. Statt bloßer KI-Texte entstehen Datenobjekte, mit denen der Wizard sicher weiterarbeiten kann.

Dynamischer Fragenfluss

Der Wizard passt sich an:

die eingebrachte Jobspec,
bereits vorhandene Informationen,
den gewählten Detailgrad,
und frühere Antworten im Verlauf.

So sehen Nutzerinnen und Nutzer zuerst das Wesentliche und nur bei Bedarf zusätzliche Tiefe. Das spart Zeit, hält die Eingabequalität hoch und verhindert unnötige Komplexität. Genau dadurch bleibt der Prozess auch bei anspruchsvollen Rollen handhabbar.

Weiterverarbeitungsoptionen

Aus der finalen Datensammlung können unter anderem folgende Ergebnisse erzeugt werden:

Recruiting Brief
Job Ad
Interview Sheets für HR und Fachbereich
Boolean Search Strings
Employment Contract Draft
strukturierte Exporte in Formaten wie JSON, Markdown, DOCX, PDF sowie ESCO-Mapping-Reports

Das reduziert Medienbrüche und sorgt dafür, dass dieselbe fachliche Grundlage mehrfach genutzt werden kann.

Sicherheit

Gerade im HR-Kontext ist Datensensibilität kein Nebenthema. Deshalb ist Sicherheit für uns kein Add-on, sondern Teil der Architektur.

In einem cloudbasierten Setup unterstützen strukturierte Verarbeitung, bewusste Datenminimierung, kontrollierte Modellaufrufe und klare Exportpfade einen verantwortungsvollen Umgang mit Informationen. Besonders sensible Inhalte sollten jedoch immer nur dann verarbeitet werden, wenn hierfür eine tragfähige rechtliche und organisatorische Grundlage besteht. Die DSGVO verlangt unter anderem Datenminimierung und ein dem Risiko angemessenes Sicherheitsniveau.

Lokales LLM als Sicherheitsoption

Für besonders sensible HR-Themen kann ein lokal betriebenes LLM oder ein isoliertes On-Prem-/VPC-Setup erhebliche Vorteile bieten:

Daten verbleiben in der eigenen Infrastruktur.
Zugriffe, Logs und Speicherorte lassen sich enger kontrollieren.
Drittlandtransfers und externe API-Abhängigkeiten können reduziert werden.
Sicherheitsmaßnahmen wie Netzwerksegmentierung, Rollenrechte, interne Freigaben und eigene Aufbewahrungsregeln lassen sich konsequenter umsetzen.

Wichtig ist dabei: Ein lokales LLM ist nicht automatisch sicher. Es verschiebt Verantwortung vom externen Provider in die eigene Betriebsumgebung. Richtig umgesetzt kann es bei sensiblen HR-Prozessen aber mehr Kontrolle, mehr Nachvollziehbarkeit und oft auch mehr Akzeptanz im Unternehmen schaffen."
            ],
        ),
        SectionBlock(
            "Für wen",
            [
                "Für Recruiting-, Hiring- und Fachbereiche, die Rollenanforderungen gemeinsam und revisionsfähig abstimmen müssen."
            ],
        ),
        SectionBlock(
            "Sie möchten sehen, wie aus einem unklaren Stellenbedarf in wenigen Schritten ein belastbares Recruiting-Setup wird?",
            [
                "Dann testen Sie Cognitive Staffing und erleben Sie, wie strukturierter Vacancy Intake Recruiting von Anfang an besser macht.

Die Produktmerkmale in diesem Abschnitt stützen sich auf den aktuellen Research-Report und das Repo: Intake ab Landingpage, dynamischer Frageplan, Quick/Standard/Expert-Modi, ESCO-Mapping, Salary Forecast, Summary-Workspace und Exportpfade."
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
