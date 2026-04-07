# Changelog

## 2026-04-07

- UI-Theming ergänzt: Hintergrundbild (`AdobeStock_506577005.jpeg`) mit dunklem Overlay für stabile Lesbarkeit.
- Transparenter Marken-Header mit `color1_logo_transparent_background.png` in der Sidebar ergänzt.
- Kontrastoptimierte Farbpalette für Texte, Hinweise, Buttons und Formularfelder eingeführt.
- Neues Konfigurationsmodul `settings_openai.py` eingeführt (Secrets/Env/Defaults mit Priorität, robustes Timeout-Parsing) und in `state.py`/`llm_client.py` integriert.
- `llm_client.get_openai_client()` auf zentrale `OpenAISettings`-Nutzung refaktoriert; Timeout konsolidiert und klare Fehlerhinweise bei fehlendem/ungültigem API-Key ergänzt.
