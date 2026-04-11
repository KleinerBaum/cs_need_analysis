# Cognitive Staffing – Vacancy Intake Wizard (Streamlit + OpenAI API)

Dieses Repo enthält eine Streamlit-Webapp, die Line Manager strukturiert durch ein Vacancy Intake führt.

## Features

- Intake-Start direkt auf der Landingpage mit integriertem Jobspec-Intake (Upload/Text + Analyse-Button) und separater Consent-Bestätigung (Checkbox) zum Content-Sharing-Hinweis.
- Upload von Jobspec/Job Ad als **PDF**, **DOCX** oder **TXT** (alternativ: Text einfügen).
- Entkoppeltes Quellenhandling im Intake: Upload-Text und manuelle Eingabe überschreiben sich nicht; die aktive Quelle wird zur Analyse genutzt.
- LLM-gestützte **Extraktion** der Jobspec in ein strukturiertes Schema (Structured Outputs) und automatische Erzeugung eines dynamischen Frageplans.
- Wizard mit Fortschrittsanzeige und drei Ansichtsmodi (`quick`, `standard`, `expert`) für die Schritte Unternehmen, Team, Rolle & Aufgaben, Skills, Benefits, Interviewprozess und Summary.
- Im Schritt **Identifizierte Informationen** werden die angezeigten Fragen pro Step automatisch und laufend neu bestimmt (basierend auf vorhandenen Informationen aus Jobspec + bisherigen Antworten sowie dem Ansichtsmodus `quick`/`standard`/`expert`).
- Finaler **Recruiting Brief** mit Export als JSON, Markdown und DOCX.
- **Action Hub** in der Summary für Folgeartefakte inkl. kanonischer Artefakt-IDs (`brief`, `job_ad`, `interview_hr`, `interview_fach`, `boolean_search`, `employment_contract`).
  - Recruiting Brief
  - Job-Ad-Generator (mit Zielgruppe + AGG-Checkliste)
  - Interview-Vorbereitungssheet (HR)
  - Interview-Vorbereitungssheet (Fachbereich)
  - Boolean Search Pack (Google/LinkedIn/XING, Broad/Focused/Fallback)
  - Arbeitsvertrag (Template Draft)
- Der Ergebnisbereich wird primär über das aktive Artefakt gesteuert (fokussierte Darstellung + sekundäres Umschalten auf weitere Ergebnisse); Export liegt in einem separaten Sekundär-Expander.
- Beim Job-Ad-Generator stehen zusätzlich eine Selection Matrix, ein Job-Ad-Editor sowie optionaler Logo-Upload und Styleguide-/Change-Request-Bausteine zur Verfügung.
- Der Salary Forecast wird in den Schritten Rolle & Aufgaben, Skills & Anforderungen sowie Benefits & Rahmenbedingungen als standardmäßig geöffnete Sektion angezeigt.
- ESCO-Integration im Jobspec-Review mit Occupation-Picker, Preview und optionalem Laden von Occupation-Titelvarianten in mehreren Sprachen.
- Skills-Mapping gegen ESCO inkl. Must-/Nice-to-have-Zuordnung, relationalen Occupation-Skill-Vorschlägen und on-demand Skill-Details.
- Optionales NACE/EURES-Mapping im Unternehmensschritt als Grundlage für spätere Country-/Occupation-Kontexte.
- Primäre Fakten-Tabelle in der Summary (Bereich/Feld/Wert/Quelle/Status) inkl. Such-/Statusfilter, plus sekundärer Kompaktüberblick und ESCO Mapping Report (JSON/CSV-Export).
- In den Schritten Rolle & Aufgaben und Skills & Anforderungen werden Vorschläge aus Jobspec, ESCO und AI nebeneinander dargestellt und können gezielt übernommen werden.
- Session-basiertes LLM-Response-Caching mit Cache-Hinweisen in Intake/Summary (DE/EN), inkl. Cache-Status für Folgeartefakte.

## Voraussetzungen

- Python 3.11+
- OpenAI API Key (als Umgebungsvariable oder Streamlit Secret)

## UI-Branding

- Die App nutzt `images/AdobeStock_506577005.jpeg` als vollflächiges Hintergrundbild.
- Das Logo `images/color1_logo_transparent_background.png` wird mit transparentem Hintergrund im Sidebar-Header dargestellt.
- Für Lesbarkeit auf hellen und dunklen Bildbereichen nutzt die Oberfläche einen dunklen Overlay-Layer, kontrastreiche Textfarben sowie angepasste Button-/Formularfarben.
- Rechtstexte werden als eigene Seiten über Query-Parameter gerendert (`?legal=terms`, `?legal=privacy`) und enthalten DE/EN-Hinweise zu Content Sharing, Notice/Consent und ausgeschlossenen Datenkategorien (u. a. PHI, Daten von Kindern <13).
- Debug-Hinweise werden in den jeweiligen Fachbereichen angezeigt (z. B. API-Usage-Expander in Intake/Summary), ohne Secrets preiszugeben.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt -c constraints.txt
```

Falls du ohne Constraints arbeiten willst, bleibt auch `pip install -r requirements.txt` möglich.

## ESCO API Konfiguration

Die ESCO-Basis-URL kann optional über `ESCO_API_BASE_URL` gesetzt werden (z. B. für lokale Mirror/Proxy-Setups).

### Auflösungsreihenfolge

1. explizite Session-Konfiguration (`st.session_state[SSKey.ESCO_CONFIG]["base_url"]`)
2. Umgebungsvariable `ESCO_API_BASE_URL`
3. Default: `https://ec.europa.eu/esco/api/`

### Beispiel (Local Deployment)

```bash
export ESCO_API_BASE_URL="http://localhost:9000/esco/api/"
streamlit run app.py
```

### Verifikation

```bash
pip check
python -c "import openai; print(openai.__version__)"
```

## OpenAI Modell-Kompatibilität
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
- Optionales task-basiertes Modell-Routing ist schlank integriert (ohne UX-Umbau): `extract_job_ad -> LIGHTWEIGHT_MODEL`, `generate_question_plan -> MEDIUM_REASONING_MODEL`, `generate_vacancy_brief -> MEDIUM_REASONING_MODEL`, `generate_job_ad -> HIGH_REASONING_MODEL`, `generate_interview_sheet_hr -> HIGH_REASONING_MODEL`, `generate_interview_sheet_hm -> HIGH_REASONING_MODEL`, `generate_boolean_search -> MEDIUM_REASONING_MODEL`, `generate_employment_contract -> HIGH_REASONING_MODEL`.
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

## Exporte

- Recruiting Brief: JSON, Markdown, DOCX
- Job-Ad-Ergebnis: DOCX, PDF
- Interview-Sheet (HR): JSON, DOCX
- Interview-Sheet (Fachbereich): JSON, DOCX
- Boolean Search Pack: JSON, Markdown
- Arbeitsvertrag (Template Draft): JSON, DOCX
- ESCO Mapping Report: CSV (UTF-8), JSON
