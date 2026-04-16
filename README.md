# Cognitive Staffing – Vacancy Intake Wizard (Streamlit + OpenAI API)

Dieses Repo enthält eine Streamlit-Webapp, die Line Manager strukturiert durch ein Vacancy Intake führt.

## Features

- Intake-Start direkt auf der Landingpage mit integriertem Jobspec-Intake in **drei klaren Start-Phasen**: **Phase A (Quelle & Datenschutz)**, **Phase B (Extraktion prüfen)**, **Phase C (ESCO-Suche)**.
- Upload von Jobspec/Job Ad als **PDF**, **DOCX** oder **TXT** (alternativ: Text einfügen).
- Entkoppeltes Quellenhandling im Intake: Upload-Text und manuelle Eingabe überschreiben sich nicht; die aktive Quelle wird zur Analyse genutzt.
- LLM-gestützte **Extraktion** der Jobspec in ein strukturiertes Schema (Structured Outputs) und automatische Erzeugung eines dynamischen Frageplans.
- Wizard mit Fortschrittsanzeige und drei Ansichtsmodi (`quick`, `standard`, `expert`) für die sichtbaren Navigationsschritte: Start, Unternehmen, Rolle & Aufgaben, Skills, Benefits, Interviewprozess und Summary.
- Der Ansichtsmodus (gespeicherte Werte: `quick`, `standard`, `expert`; Anzeige: `schnell`, `ausführlich`, `vollumfänglich`) ist global über das Sidebar-**Präferenz-Center** steuerbar und zusätzlich im Start-Schritt direkt unter dem Jobspec-Upload. Beim Wechsel greift sofort die adaptive Fragenbegrenzung (Neuberechnung der sichtbaren Fragen pro Step). In jedem Schritt wird der aktive Modus als sichtbare Caption angezeigt, damit reduzierte Frageanzahl nachvollziehbar bleibt. `schnell`/`ausführlich`: Detailgruppen standardmäßig kompakt. `vollumfänglich`: Detailgruppen standardmäßig geöffnet.
- Die vormals getrennte Ansicht **Identifizierte Informationen** ist in den Start-Schritt integriert (eine Wizard-Stufe weniger): Nach der Analyse erscheinen dort direkt die editierbare Übersicht, Gaps/Annahmen und der Übergang von Phase B zu Phase C bzw. in den nächsten Fachschritt; es gibt **keinen separaten sichtbaren Review-Wizard-Schritt** mehr.
- Finaler **Recruiting Brief** mit Export als JSON, Markdown und DOCX.
- **Summary-Workspace** als einheitliche Readiness-Ansicht ohne separate Tabs.
- Die **Readiness-Ansicht** aktualisiert den **Recruiting Brief** beim Betreten automatisch (falls veraltet/fehlend), zeigt den Brief ohne zusätzlichen Expander und platziert den Faktenbereich darunter vor der **„next best action“**.
- Die Verfügbarkeit von CTAs in der Summary folgt einer Kombination aus **fachlichen Voraussetzungen** (Prerequisites) und **kurzen Freshness-Checks** auf die zugrunde liegenden Inhalte.
- Unterhalb der Readiness-CTA stehen kompakt nebeneinander die **Generate-Buttons** für Stellenanzeige, HR-Sheet, Fachbereich-Sheet, Boolean String und Arbeitsvertrag; darunter folgt der Ergebnisbereich (volle Breite).
- **Action Hub in der Readiness-Ansicht** mit kanonischen Artefakt-IDs (`brief`, `job_ad`, `interview_hr`, `interview_fach`, `boolean_search`, `employment_contract`) und fokussiertem Primärpfad (Recruiting Brief → Folgeartefakte → Export).
- Der Artefaktbereich wurde auf eine scannbare Einzeldarstellung konsolidiert (keine doppelten Ergebnisblöcke); weitere Ergebnisse werden sekundär umgeschaltet.
- Beim Job-Ad-Generator liegen **Selection Matrix** und **Job-Ad-Editor** gebündelt im erweiterten Bereich (UI-Modus `expert`), inkl. optionalem Logo-Upload sowie Styleguide-/Change-Request-Bausteinen.
- Der Salary Forecast ist in **Rolle & Aufgaben** als kompakte Seitenleiste rechts neben der Vergleichstabelle umgesetzt: Dort können **Suchradius (km)**, **Remote Share (%)** und **Erfahrung** gesetzt werden; per **„Prognose aktualisieren“** wird eine schlichte LLM-basierte EUR-Gehaltsprognose auf Basis von Jobtitel, Seniorität, Standort und aktuell ausgewählten Rollen/Aufgaben erzeugt.
- In **Benefits & Rahmenbedingungen** wird der Salary-Forecast direkt im Schritt (ohne zusätzliche Grafiken) unter dem **Minimalprofil** angezeigt; erkannte Benefits können ein-/abgewählt werden. Zusammen mit Suchradius, Remote-Anteil und Erfahrung fließen sie per **„Prognose aktualisieren“** in die Gehaltsprognose ein.
- ESCO-Integration in **Start · Phase C (ESCO-Suche)** ohne Expander mit Occupation-Picker, direkter Bestätigung via **„Speichern“** und 3-spaltiger Trefferübersicht; diese Bestätigung erfolgt vor der Weiterarbeit im integrierten Unternehmens-/Teamkontext sowie im Skills-Schritt und dient dort als Downstream-Grundlage. Zusätzlich gibt es einen expandierbaren Occupation-Detailbereich (u. a. Preferred/Alternative Labels, Description, Scope Note, ISCO-08, Regulated Profession sowie Skill-/Knowledge-Relationen) sowie optionales Laden von Occupation-Titelvarianten in mehreren Sprachen.
- Degradiertes Verhalten bei ESCO-Ausfall: Bei temporären ESCO-Fehlern (z. B. 5xx/Netzwerk) bleibt der Wizard bedienbar, zeigt verständliche Hinweise und bietet „manuell fortfahren“ sowie „später erneut versuchen“ statt eines harten Abbruchs.
- Skills-Mapping als geführter 4-Schritt-Flow: (1) extrahierte Jobspec-Phrasen, (2) ESCO-Normalisierung über Occupation-Relationen, (3) sichtbare Essential/Optional-Bestätigung, (4) dedizierter Bereich „Not normalized yet“ mit Optionen „Keep free text“, Retry-Suche und Attach an Occupation.
- Optionales NACE/EURES-Mapping im Unternehmensschritt als Grundlage für spätere Country-/Occupation-Kontexte; die Summary-Readiness bewertet den bestätigten semantischen Anker (ESCO) und NACE separat.
- Unternehmensschritt mit Homepage-Enrichment (Beta): Die aus dem Jobspec extrahierte Arbeitgeber-URL kann per Buttons für **Über uns**, **Impressum** und **Vision/Mission** analysiert werden; essenzielle Textausschnitte werden rechts angezeigt, mit offenen Wizard-Fragen abgeglichen, im Session-State gespeichert und in die Brief-Generierung im Summary-Schritt eingespeist.
- Der Unternehmensschritt umfasst neben dem Unternehmenskontext auch den Teamkontext inkl. Team-Fragen und enthält dafür ein zweizoniges **Role-context enrichment (ESCO)**-Muster: links klar als **Inferred suggestion/context** markierte Hinweise (inkl. Match-Provenance/-Confidence, falls vorhanden), rechts der Bereich **Confirmed input** aus der kanonischen Team-Notiz. Die Übernahme erfolgt gesammelt über eine eindeutige Aktion „Ausgewählte Vorschläge als confirmed selection übernehmen“.
- Primäre Fakten-Tabelle in der Summary (Bereich/Feld/Wert/Quelle/Status) unterhalb des Recruiting Briefs mit 2/3-Tabellenbereich und 1/3 Filterspalte (Suche/Status), plus sekundärer Kompaktüberblick und ESCO Mapping Report (JSON/CSV-Export).
- In den Schritten **Rolle & Aufgaben** sowie **Skills & Anforderungen** läuft die Übernahme über „**Vergleichen & übernehmen**“-Tabellen: Vorschläge aus Jobspec, ESCO und AI werden nebeneinander gestellt und selektiv übernommen; im Skills-Schritt zusätzlich mit Quellen-Badges (`Jobspec`, `ESCO essential`, `ESCO optional`, `AI suggestion`) und kanonischer Semantik mit **Inferred suggestion/context** und **confirmed selection** (`Confirm essential as confirmed selection`, `Confirm optional as confirmed selection`).
- Session-basiertes LLM-Response-Caching mit Cache-Hinweisen in Intake/Summary (DE/EN), inkl. Cache-Status für Folgeartefakte.

## Wizard-Flow (implementiert)

1. **Start**
   - Phase A: Quelle, Consent, optionale PII-Redaktion, UI-Modus (global zusätzlich über Sidebar-Präferenz-Center steuerbar)
   - Phase B: editierbare „Identifizierte Informationen“ + Gaps/Assumptions
   - Phase C: ESCO-Suche (verpflichtende Bestätigung vor „Weiter“)
2. **Unternehmen** (Unternehmenskontext plus integrierter Teamkontext/Team-Fragen inkl. ESCO-Teamkontext-Anreicherung; optionaler NACE-Code, falls Mapping geladen ist; plus Homepage-Enrichment für Über-uns/Impressum/Vision-Mission)
3. **Rolle & Aufgaben**
4. **Skills & Anforderungen**
5. **Benefits & Rahmenbedingungen**
6. **Interviewprozess**
7. **Zusammenfassung** (integrierte Readiness-Ansicht mit Fakten, Aktionen, Ergebnissen und Export)

Hinweis: Der frühere Schritt `jobspec_review` ist nur noch als Legacy-Modul vorhanden und nicht routbar.

## Voraussetzungen

- Python 3.11+
- OpenAI API Key (als Umgebungsvariable oder Streamlit Secret)

## UI-Branding

- Im Sidebar-Header wird das animierte GIF `images/animation_pulse_SingleColorHex1_7kigl22lw.gif` dargestellt.
- Im Start-Schritt wird `images/white_logo_color1_background.png` als Hero-Logo angezeigt.
- Die Theme-Farbgebung (Light/Dark) kommt aus der Streamlit-Theme-Konfiguration (`.streamlit/config.toml`); app-/site-spezifische CSS-Regeln steuern nur Layout/Struktur und keine globalen Farb-Overrides.
- Rechtstexte/Info-Seiten laufen als eigenständige Streamlit-Seiten unter `pages/`; im Wizard verbleibt nur das Präferenz-Center als Query-Parameter-View (`?page=preferences`).
- Debug-Hinweise werden in den jeweiligen Fachbereichen angezeigt (z. B. API-Usage-Expander in Intake/Summary), ohne Secrets preiszugeben.

## Unterstützte Streamlit-Komponenten (Stand Runtime)

- Breitensteuerung bei Medien nutzt die aktuelle API (`width="stretch"` / `width="content"`), nicht mehr `use_container_width=...`.
- Für eingebettete externe Inhalte ist `st.iframe(...)` der bevorzugte Weg.
- Beim Wizard-Step-Wechsel nutzt `app.py` für den Scroll-Reset die native API `st.html(...)` (ohne `st.components.v1.html(...)`). Falls die API in einer älteren Runtime nicht vorhanden ist, bleibt das Verhalten ohne zusätzlichen Fallback-Script bei normaler Streamlit-Navigation.

## Installation

```bash
python -m pip install --upgrade pip
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt -c constraints.txt
streamlit run app.py
```

Falls du ohne Constraints arbeiten willst, bleibt auch `pip install -r requirements.txt` möglich.

## ESCO API Konfiguration

Die ESCO-Basis-URL kann optional über `ESCO_API_BASE_URL` gesetzt werden (z. B. für lokale Mirror/Proxy-Setups).
Die ESCO-Version ist standardmäßig auf `v1.2.0` gepinnt und kann über `ESCO_SELECTED_VERSION` gesetzt werden.
Optional kann `ESCO_API_MODE` (`hosted` / `local`) gesetzt werden; die Client-Abstraktion bleibt für beide Modi gleich.

### Auflösungsreihenfolge

1. explizite Session-Konfiguration (`st.session_state[SSKey.ESCO_CONFIG]["base_url"]`)
2. Umgebungsvariable `ESCO_API_BASE_URL`
3. Default: `https://ec.europa.eu/esco/api/`

Versionauflösung:

1. explizite Session-Konfiguration (`st.session_state[SSKey.ESCO_CONFIG]["selected_version"]`)
2. Umgebungsvariable `ESCO_SELECTED_VERSION`
3. Default: `v1.2.0`

### Beispiel (Local Deployment)

```bash
export ESCO_API_BASE_URL="http://localhost:9000/esco/api/"
export ESCO_SELECTED_VERSION="v1.2.0"
export ESCO_API_MODE="local"
streamlit run app.py
```

### Verifikation

```bash
pip check
python -c "import openai; print(openai.__version__)"
python -c "from eures_mapping import load_national_code_lookup_from_file as f; print('ok' if callable(f) else 'fail')"
```

## OpenAI Konfiguration (Secrets, Env, UI)

Du kannst die OpenAI-Parameter entweder als Root-Level-Secrets oder in einer `[openai]`-Sektion in `.streamlit/secrets.toml` setzen.

### Priorität (exakt)

Die Auflösung erfolgt in dieser Reihenfolge:

1. `[openai]`-Sektion in `st.secrets`
2. Root-Level-Keys in `st.secrets`
3. Umgebungsvariablen (`os.getenv`)
4. harte Defaults im Code

Kurzform: **`[openai] > root-level secrets > env vars > defaults`**.

### Wichtiger Hinweis zu Streamlit-Secrets

- Root-Level-Secrets werden von Streamlit zusätzlich als Umgebungsvariablen gespiegelt.
- Werte aus der `[openai]`-Sektion werden **nicht** als Umgebungsvariablen gespiegelt.

### UI-Override via Session State

Die UI kann das aufgelöste Modell zur Laufzeit überschreiben (Session-State). Dadurch gilt für die Modellwahl:

**UI-Override > `OPENAI_MODEL` (global) > task-spezifische Modelle > `DEFAULT_MODEL`**.

- Modell-spezifische Request-Optionen werden zentral über `model_capabilities.py` definiert und in `llm_client.py` verwendet.
- Optionales task-basiertes Modell-Routing ist schlank integriert (ohne UX-Umbau): `extract_job_ad -> LIGHTWEIGHT_MODEL`, `generate_question_plan -> MEDIUM_REASONING_MODEL`, `generate_vacancy_brief -> MEDIUM_REASONING_MODEL`, `generate_job_ad -> HIGH_REASONING_MODEL`, `generate_interview_sheet_hr -> HIGH_REASONING_MODEL`, `generate_interview_sheet_hm -> HIGH_REASONING_MODEL`, `generate_boolean_search -> MEDIUM_REASONING_MODEL`, `generate_employment_contract -> HIGH_REASONING_MODEL`, `generate_requirement_gap_suggestions -> MEDIUM_REASONING_MODEL`.
- Priorität beim Modellrouting: **Session/UI-Override** > **`OPENAI_MODEL` (globaler Override)** > **task-spezifische Modell-Keys** > **`DEFAULT_MODEL`** > **zentraler finaler Fallback (`gpt-4o-mini`)**.
- Die Debug-Expander in den Wizard-Schritten zeigen zusätzlich die effektiv aufgelösten Task-Modelle an (`resolved_models`), damit Routing-Entscheidungen ohne Secret-Leak nachvollziehbar bleiben.
- OpenAI-Settings bleiben bei `REASONING_EFFORT`/`VERBOSITY` bewusst optional: wenn nicht gesetzt, werden diese Werte als `None` behandelt und nicht künstlich vorbelegt.
- Das zentrale OpenAI-Request-Timeout liegt konsistent bei **120 Sekunden** (falls `OPENAI_REQUEST_TIMEOUT` fehlt/ungültig ist).
- Für Debug/Diagnose steht eine sichere Provenance-Map (`resolved_from`) zur Verfügung, die nur die Quelle je Key (`nested_secret`/`root_secret`/`env`/`default`) ausweist – nie Secret-Inhalte.
- Für `gpt-5`, `gpt-5-mini` und `gpt-5-nano` wird `temperature` nicht automatisch mitgesendet.
- Snapshot-Varianten mit Datums-Suffixen (z. B. `gpt-5-mini-2026-01-15`) werden für `gpt-5`, `gpt-5-mini` und `gpt-5-nano` robust erkannt.
- Für `gpt-5.4*` wird `temperature` nur mitgesendet, wenn `reasoning_effort="none"` aktiv ist.
- Unterstützte `reasoning_effort`-Werte: `none`, `minimal`, `low`, `medium`, `high`, `xhigh`.
- `reasoning` und `text.verbosity` werden nur noch für tatsächlich kompatible GPT-5-Familien gesendet; Fallback-Modelle wie `gpt-4o-mini` erhalten keine GPT-5-spezifischen Felder.
- Für `gpt-5-nano` und `gpt-5.4-nano` werden die drei Kern-Prompts (`extract_job_ad`, `generate_question_plan`, `generate_vacancy_brief`) minimal mit Guardrails ergänzt (nur strukturierte Schema-Ausgabe, kein Zusatztext, keine impliziten Nebenaufgaben, fehlende Infos leer/null statt geraten).
- Mindestabhängigkeit: `openai>=2.30.0,<3.0.0`, damit `responses.parse(...)`, strukturierte `text_format`-Ausgaben, Client-`timeout` und aktuelle Request-Felder (z. B. `reasoning`, `text.verbosity`) konsistent verfügbar sind.

## OpenAI Fehlerbehandlung (UI + Logging)

- OpenAI-Fehler werden in klaren Kategorien behandelt: fehlender API-Key, Timeout, HTTP-400/inkompatible Parameter und Structured-Output-Validierungsfehler.
- Zusätzlich werden `unsupported parameter` (HTTP 400) und `APIConnectionError` separat und präzise klassifiziert.
- UI-Texte sind knapp und zweisprachig (DE/EN), damit die bestehende UX stabil bleibt und trotzdem genaueres Feedback gibt.
- Logs enthalten nur nicht-sensitive Debug-Informationen (Endpoint, Fehlerklasse, optional `status_code`), aber keine API-Keys und keine kompletten Request-Payloads.
- Optionale Fehler-Debugausgabe kann per Session-State-Flag `OPENAI_DEBUG_ERRORS` aktiviert werden und zeigt nur nicht-sensitive Hinweise.
- Interne Fehlercodes sind verfügbar (z. B. `OPENAI_AUTH`, `OPENAI_TIMEOUT`, `OPENAI_BAD_REQUEST`, `OPENAI_PARSE`, `OPENAI_SDK_UNSUPPORTED`) und werden im Debug-Modus mit ausgegeben.
- Für transiente OpenAI-Fehler (Timeout/Connection) sind automatische Wiederholversuche mit exponentiellem Backoff aktiv.

## OpenAI Smoke-Test (extract_job_ad)

Das Repo enthält einen kleinen Smoke-Test unter `scripts/openai_smoke_test.py`.

### Ziel

- Führt `extract_job_ad` mit einem kurzen Sample-Text aus.
- Trennt klar zwischen:
  - `configured_mode` (statische Testkonfiguration)
  - `effective_request_kwargs` (tatsächlich capability-gefilterte Request-Parameter)
  - `actual_response_metadata` (echte SDK-Metadaten wie `response_model_id`, `usage`, `parse_status`)
- Gibt keine Secrets (`OPENAI_API_KEY`) aus.
- Endet bei Fehlern mit **non-zero Exit Code** (CI-tauglich).

### Abgedeckte Modi

1. `gpt-5.4-nano` mit `reasoning_effort=none` und `verbosity=low`  
   Erwartung: `temperature` darf gesendet werden (hier `0.0`), Parse sollte erfolgreich sein.
2. `gpt-5-nano` mit kompatiblen Parametern  
   Erwartung: `temperature` wird **nicht** gesendet, auch wenn lokal ein Wert gesetzt ist; Parse sollte erfolgreich sein.
3. `invalid-reasoning-effort` (simuliert, kein API-Call)  
   Erwartung: ungültiger `reasoning_effort` wird capability-gated verworfen.
4. `unsupported-temperature` (simuliert, kein API-Call)  
   Erwartung: für inkompatible Modelle wird `temperature` aus den effektiven Request-Kwargs entfernt.

### Lokal ausführen

```bash
export OPENAI_API_KEY="sk-..."  # nur lokal setzen, nie committen
python scripts/openai_smoke_test.py --mode all
```

Für CI/Maschinen-Ausgabe:

```bash
python scripts/openai_smoke_test.py --mode all --json-only
```

Fail-Fast (bei erstem Fehler abbrechen):

```bash
python scripts/openai_smoke_test.py --mode all --fail-fast
```

Dry-Run für CI ohne Key (validiert nur Request-Kwargs):

```bash
python scripts/openai_smoke_test.py --mode all --ci-dry-run-if-no-key --json-only
```

Optional einzelne Modi:

```bash
python scripts/openai_smoke_test.py --mode gpt-5.4-nano
python scripts/openai_smoke_test.py --mode gpt-5-nano
```

Zusätzliche Fehlerpfad-Simulation (ohne Netzverkehr):

```bash
python scripts/openai_smoke_test.py --mode all --simulate-error timeout --json-only
python scripts/openai_smoke_test.py --mode all --simulate-error connection --json-only
```

### Typische 400er-Fehlerbilder bei falscher Parametrisierung

- `unsupported_parameter`: z. B. `temperature` wird an ein inkompatibles GPT-5 Legacy-Modell gesendet.
- `invalid_reasoning_effort`: z. B. `reasoning.effort="none"` bei einem Modell, das diesen Wert nicht unterstützt.
- `invalid_type`/`invalid_request_error`: z. B. falscher Typ in `reasoning`, `text.verbosity` oder fehlerhafte Struktur im Request-Body.

Der Smoke-Test zeigt die tatsächlich gebauten `request_kwargs`, damit sich diese Fälle schnell eingrenzen lassen.

### Hinweis zu Konfigurationsquellen (Secrets vs. Env)

Die App-Konfiguration nutzt dieselbe Priorität wie `settings_openai.py`: `st.secrets` (inkl. `openai`-Namespace) kann Umgebungsvariablen überschreiben.  
Für verlässliche lokale Verifikation daher nicht nur auf Env-Mutation verlassen, sondern die effektiven Request-Kwargs/Metadaten im Smoke-Test prüfen.

Dieser Smoke-Test ist der bevorzugte Verifikationspfad für Änderungen an Modellrouting, Capability-Gating, `reasoning_effort`, `verbosity`, `temperature` und OpenAI-Request-Building.

## EURES/NACE Mapping (optional)

- Optionaler NACE→ESCO-Lookup wird über `EURES_NACE_MAPPING_CSV` geladen.
- Ist kein Mapping geladen, bleibt der NACE-Block im Unternehmensschritt unsichtbar.
- Ist ein Mapping geladen, wird der gesetzte NACE-Code in der Summary-Readiness separat von ESCO berücksichtigt.

## Exporte

- Recruiting Brief: JSON, Markdown, DOCX
- Job-Ad-Ergebnis: DOCX, PDF (nur wenn `reportlab` verfügbar ist)
- Interview-Sheet (HR): JSON, DOCX
- Interview-Sheet (Fachbereich): JSON, DOCX
- Boolean Search Pack: JSON, Markdown
- Arbeitsvertrag (Template Draft): JSON, DOCX
- ESCO Mapping Report: CSV (UTF-8), JSON

### Strukturierter Export (Summary)

Der strukturierte Summary-Export enthält – sofern vorhanden – folgende ESCO-bezogene Felder:

- `esco_occupations`: bestätigte ESCO Occupation(s) mit `uri` und `label`
- `esco_occupation_provenance`: Explainability/Provenance zur bestätigten Occupation (`reason`, `confidence`, `provenance_categories`)
- `recommended_titles`: geladene Occupation-Titelvarianten pro Sprache
- `esco_skills_must` / `esco_skills_nice`: übernommene ESCO-Skills
- `esco_unmapped_requirement_terms` / `esco_unmapped_role_terms`: offene, nicht normalisierte Begriffe
- `esco_unmapped_term_actions`: dokumentierte Nutzerentscheidung je offenem Begriff
