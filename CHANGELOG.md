# Changelog

## 2026-04-07

- Streamlit-Debugansicht angepasst: Session-State-Vollanzeige entfernt und durch einen kleinen Sidebar-Expander mit sicheren, aufgelösten OpenAI-Werten ersetzt (`model`, `default_model`, `reasoning_effort`, `verbosity`, `timeout`), ohne Secret-Ausgabe.
- UI-Theming ergänzt: Hintergrundbild (`AdobeStock_506577005.jpeg`) mit dunklem Overlay für stabile Lesbarkeit.
- Transparenter Marken-Header mit `color1_logo_transparent_background.png` in der Sidebar ergänzt.
- Kontrastoptimierte Farbpalette für Texte, Hinweise, Buttons und Formularfelder eingeführt.
- Neues Konfigurationsmodul `settings_openai.py` eingeführt (Secrets/Env/Defaults mit Priorität, robustes Timeout-Parsing) und in `state.py`/`llm_client.py` integriert.
- `llm_client.get_openai_client()` auf zentrale `OpenAISettings`-Nutzung refaktoriert; Timeout konsolidiert und klare Fehlerhinweise bei fehlendem/ungültigem API-Key ergänzt.
- Zentrale Modell-Kompatibilitätslogik in `llm_client.py` ergänzt (`is_gpt5_legacy_model`, `is_gpt54_family`, `supports_temperature`, `normalize_reasoning_effort`) und an allen Structured-Output-Callsites verdrahtet.
- Temperatur-Handling in `llm_client.py` entkoppelt: `extract_job_ad`, `generate_question_plan` und `generate_vacancy_brief` nutzen jetzt `temperature: float | None = None` und reichen Temperatur nur noch optional über die zentrale Request-Builder-Logik weiter.
