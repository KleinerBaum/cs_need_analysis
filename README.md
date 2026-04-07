# Cognitive Staffing – Vacancy Intake Wizard (Streamlit + OpenAI API)

Dieses Repo enthält eine Streamlit-Webapp, die Line Manager strukturiert durch ein Vacancy Intake führt.

## Features

- Upload von Jobspec/Job Ad als **PDF** oder **DOCX** (alternativ: Text einfügen)
- Quellenhandling in Schritt „Jobspec / Job Ad“ ist entkoppelt: Upload, manuelle Eingabe und Samples überschreiben sich nicht mehr; aktive Quelle wird transparent angezeigt (DE/EN).
- LLM-gestützte **Extraktion** der Jobspec in ein strukturiertes Schema (Structured Outputs)
- Dynamischer Fragebogen je Abschnitt: Unternehmen, Team, Rolle & Aufgaben, Skills, Benefits, Interviewprozess
- Finaler **Recruiting Brief** inkl. Job-Ad Draft + Export (JSON / Markdown / DOCX)

## Voraussetzungen

- Python 3.11+
- OpenAI API Key (als Umgebungsvariable oder Streamlit Secret)

## UI-Branding

- Die App nutzt `images/AdobeStock_506577005.jpeg` als vollflächiges Hintergrundbild.
- Das Logo `images/color1_logo_transparent_background.png` wird mit transparentem Hintergrund im Sidebar-Header dargestellt.
- Für Lesbarkeit auf hellen und dunklen Bildbereichen nutzt die Oberfläche einen dunklen Overlay-Layer, kontrastreiche Textfarben sowie angepasste Button-/Formularfarben.
- Optionaler Debug-Expander in der Sidebar (nur bei aktiviertem Debug-Flag) zeigt ausschließlich aufgelöste OpenAI-Laufzeitwerte an (`model`, `default_model`, `reasoning_effort`, `verbosity`, `timeout`) und blendet Secrets aus.
- Neue rechtliche Unterseiten sind über Links am unteren Ende der Sidebar erreichbar: **Terms of Service / Nutzungsbedingungen** und **Privacy Policy / Datenschutzerklärung**.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## OpenAI Modell-Kompatibilität
## OpenAI Konfiguration (Secrets, Env, UI)

Du kannst die OpenAI-Parameter entweder als Root-Level-Secrets oder in einer `[openai]`-Sektion in `.streamlit/secrets.toml` setzen (siehe `.streamlit/secrets.toml.example`).

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
- Optionales task-basiertes Modell-Routing ist schlank integriert (ohne UX-Umbau): `extract_job_ad -> LIGHTWEIGHT_MODEL`, `generate_question_plan -> MEDIUM_REASONING_MODEL`, `generate_vacancy_brief -> HIGH_REASONING_MODEL`.
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
- Logs enthalten nur nicht-sensitive Debug-Informationen (Fehlerklasse/kurzer Kontext), aber keine API-Keys und keine kompletten Request-Payloads.
- Optionale Fehler-Debugausgabe kann per Session-State-Flag `OPENAI_DEBUG_ERRORS` aktiviert werden und zeigt nur nicht-sensitive Hinweise.
- Interne Fehlercodes sind verfügbar (z. B. `OPENAI_AUTH`, `OPENAI_TIMEOUT`, `OPENAI_BAD_REQUEST`, `OPENAI_PARSE`) und werden im Debug-Modus mit ausgegeben.
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

### Typische 400er-Fehlerbilder bei falscher Parametrisierung

- `unsupported_parameter`: z. B. `temperature` wird an ein inkompatibles GPT-5 Legacy-Modell gesendet.
- `invalid_reasoning_effort`: z. B. `reasoning.effort="none"` bei einem Modell, das diesen Wert nicht unterstützt.
- `invalid_type`/`invalid_request_error`: z. B. falscher Typ in `reasoning`, `text.verbosity` oder fehlerhafte Struktur im Request-Body.

Der Smoke-Test zeigt die tatsächlich gebauten `request_kwargs`, damit sich diese Fälle schnell eingrenzen lassen.

### Hinweis zu Konfigurationsquellen (Secrets vs. Env)

Die App-Konfiguration nutzt dieselbe Priorität wie `settings_openai.py`: `st.secrets` (inkl. `openai`-Namespace) kann Umgebungsvariablen überschreiben.  
Für verlässliche lokale Verifikation daher nicht nur auf Env-Mutation verlassen, sondern die effektiven Request-Kwargs/Metadaten im Smoke-Test prüfen.
