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

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
