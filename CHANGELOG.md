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
- OpenAI-SDK-Constraint in `requirements.txt` gezielt auf `openai>=2.30.0,<3.0.0` angehoben, um Responses-`parse`, Timeout-Übergabe und aktuelle Request-Felder robust sicherzustellen, ohne unnötige Neben-Upgrades.
- Neuer Smoke-Test `scripts/openai_smoke_test.py`: führt `extract_job_ad` mit kurzem Sample-Text gegen zwei Modi (`gpt-5.4-nano` und `gpt-5-nano`) aus und reportet sicher `resolved_model`, `response_model`, `usage`, `parse_status` sowie die effektiv gebauten Request-Parameter ohne Secret-Ausgabe.
- `llm_client.py` um `build_extract_job_ad_messages(...)` ergänzt, damit Prompt-Bausteine zwischen Produktivpfad und Smoke-Test konsistent wiederverwendet werden.
- Neue Unit-Tests (`tests/test_openai_smoke_modes.py`) sichern die zentrale Parametrisierung ab: `gpt-5.4-nano` mit `reasoning_effort=none` erlaubt `temperature`, `gpt-5-nano` verwirft `temperature` weiterhin korrekt.
- OpenAI-Exception-Mapping erweitert: getrennte, knappe UI-Fehler für fehlenden API-Key, Timeout, HTTP-400/inkompatible Parameter und Structured-Output-/Validierungsfehler; Logs bleiben bewusst nicht-sensitiv.
- Wizard-Seiten `jobad` und `summary` verwenden jetzt die neuen typisierten OpenAI-Fehler samt optionalem non-sensitive Debug-Expander (`OPENAI_DEBUG_ERRORS`), ohne bestehende UX-Flows zu ändern.
- Neue Tests `tests/test_openai_error_mapping.py` decken die Error-Mappings für Timeout, 400, Auth und Structured-Output-Validation ab.
