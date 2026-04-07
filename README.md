# Cognitive Staffing – Vacancy Intake Wizard (Streamlit + OpenAI API)

Dieses Repo enthält eine Streamlit-Webapp, die Line Manager strukturiert durch ein Vacancy Intake führt.

## Features

- Upload von Jobspec/Job Ad als **PDF** oder **DOCX** (alternativ: Text einfügen)
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

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## OpenAI Modell-Kompatibilität

- Modell-spezifische Request-Optionen werden zentral in `llm_client.py` normalisiert.
- Optionales task-basiertes Modell-Routing ist schlank integriert (ohne UX-Umbau): `LIGHTWEIGHT_MODEL` für Extraktion/Normalisierung, `MEDIUM_REASONING_MODEL` für Plan-Generierung, `HIGH_REASONING_MODEL` für qualitätskritische Ausgaben (Recruiting Brief).
- Priorität beim Modellrouting: **UI-Override** > **`OPENAI_MODEL` (globaler Override)** > **task-spezifische Modell-Keys** > **`DEFAULT_MODEL`**.
- Für `gpt-5`, `gpt-5-mini` und `gpt-5-nano` wird `temperature` nicht automatisch mitgesendet.
- Für `gpt-5.4*` wird `temperature` nur mitgesendet, wenn `reasoning_effort="none"` aktiv ist.
- `reasoning_effort="none"` wird bei inkompatiblen Modellen verworfen (nicht an die API gesendet).
- Für `gpt-5-nano` und `gpt-5.4-nano` werden die drei Kern-Prompts (`extract_job_ad`, `generate_question_plan`, `generate_vacancy_brief`) minimal mit strikteren Closed-Output-Hinweisen ergänzt (nur Schema-Ausgabe, keine Zusatztexte, klare Reihenfolge, keine Nebenaufgaben).
- Mindestabhängigkeit: `openai>=2.30.0,<3.0.0`, damit `responses.parse(...)`, strukturierte `text_format`-Ausgaben, Client-`timeout` und aktuelle Request-Felder (z. B. `reasoning`, `text.verbosity`) konsistent verfügbar sind.

## OpenAI Fehlerbehandlung (UI + Logging)

- OpenAI-Fehler werden in klaren Kategorien behandelt: fehlender API-Key, Timeout, HTTP-400/inkompatible Parameter und Structured-Output-Validierungsfehler.
- UI-Texte sind knapp und zweisprachig (DE/EN), damit die bestehende UX stabil bleibt und trotzdem genaueres Feedback gibt.
- Logs enthalten nur nicht-sensitive Debug-Informationen (Fehlerklasse/kurzer Kontext), aber keine API-Keys und keine kompletten Request-Payloads.
- Optionale Fehler-Debugausgabe kann per Session-State-Flag `OPENAI_DEBUG_ERRORS` aktiviert werden und zeigt nur nicht-sensitive Hinweise.

## OpenAI Smoke-Test (extract_job_ad)

Das Repo enthält einen kleinen Smoke-Test unter `scripts/openai_smoke_test.py`.

### Ziel

- Führt `extract_job_ad` mit einem kurzen Sample-Text aus.
- Zeigt das aufgelöste Modell, die sanitisierten Request-Parameter, das Response-Modell, Usage und den Parse-Status.
- Gibt keine Secrets (`OPENAI_API_KEY`) aus.

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
