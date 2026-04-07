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
- Für `gpt-5`, `gpt-5-mini` und `gpt-5-nano` wird `temperature` nicht automatisch mitgesendet.
- Für `gpt-5.4*` wird `temperature` nur mitgesendet, wenn `reasoning_effort="none"` aktiv ist.
- `reasoning_effort="none"` wird bei inkompatiblen Modellen verworfen (nicht an die API gesendet).
- Mindestabhängigkeit: `openai>=2.30.0,<3.0.0`, damit `responses.parse(...)`, strukturierte `text_format`-Ausgaben, Client-`timeout` und aktuelle Request-Felder (z. B. `reasoning`, `text.verbosity`) konsistent verfügbar sind.
