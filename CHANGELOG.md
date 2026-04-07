# Changelog

## 2026-04-07

- Prompt-Kontrakte für Nano-Modelle gezielt geschärft: neue Helper-Funktion `build_small_model_guardrails(model)` greift nur für `gpt-5-nano`/`gpt-5.4-nano` und erzwingt strukturierte Schema-Ausgabe ohne Zusatztext/Nebenaufgaben sowie `leer/null` bei fehlenden Informationen.
- Guardrails in allen drei Kernpfaden vereinheitlicht (`build_extract_job_ad_messages`, `generate_question_plan`, `generate_vacancy_brief`) ohne Prompt-Rewrite für größere Modelle.
- Tests erweitert (`tests/test_openai_smoke_modes.py`): neue Assertions für Nano-spezifische Guardrails in Helper und Extract-Message-Building.
- Rechtliche Unterseiten ergänzt: **Terms of Service / Nutzungsbedingungen** und **Privacy Policy / Datenschutzerklärung**.
- Sidebar erweitert: Rechtslinks sind am unteren Ende der Navigation platziert und öffnen die jeweiligen Seiten per Query-Parameter.
- Bilinguale Inhalte (DE/EN) für beide Rechtsseiten ergänzt, inklusive Rücksprung-Button in den Wizard.
- Schlanke, optionale Modell-Routing-Schicht ergänzt: task-basierte Auswahl mit `LIGHTWEIGHT_MODEL` (Extraktion/Normalisierung), `MEDIUM_REASONING_MODEL` (QuestionPlan) und `HIGH_REASONING_MODEL` (VacancyBrief), ohne UX-Umbau.
- Prioritätslogik fest verdrahtet: UI-Modelloverride > `OPENAI_MODEL` > task-spezifische Modell-Keys > `DEFAULT_MODEL`.
- `settings_openai.OpenAISettings` um `openai_model_override` erweitert, damit `OPENAI_MODEL` als expliziter globaler Override zuverlässig von Fallbacks unterscheidbar ist.
- Tests erweitert (`tests/test_openai_smoke_modes.py`): Routing-Priorität (UI vs. OPENAI_MODEL vs. Task-Keys) ist jetzt automatisiert abgesichert.
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
- Nano-spezifische Prompt-Härtung ergänzt: Für `gpt-5-nano` und `gpt-5.4-nano` erhalten `extract_job_ad`, `generate_question_plan` und `generate_vacancy_brief` einen kurzen Closed-Output-Zusatz (nur Schema, kein Zusatztext, klare Reihenfolge, keine Nebenaufgaben), ohne das Verhalten für größere Modelle zu verändern.
- Tests erweitert: `tests/test_openai_smoke_modes.py` prüft jetzt zusätzlich Nano-Modellerkennung und das gezielte Aktivieren des Closed-Output-Zusatzes.
- OpenAI-Exception-Mapping erweitert: getrennte, knappe UI-Fehler für fehlenden API-Key, Timeout, HTTP-400/inkompatible Parameter und Structured-Output-/Validierungsfehler; Logs bleiben bewusst nicht-sensitiv.
- Wizard-Seiten `jobad` und `summary` verwenden jetzt die neuen typisierten OpenAI-Fehler samt optionalem non-sensitive Debug-Expander (`OPENAI_DEBUG_ERRORS`), ohne bestehende UX-Flows zu ändern.
- Neue Tests `tests/test_openai_error_mapping.py` decken die Error-Mappings für Timeout, 400, Auth und Structured-Output-Validation ab.
- Modell-Capability-Logik fachlich gehärtet und zentralisiert (`model_capabilities.py`): Snapshot-taugliche GPT-5-Erkennung (`gpt-5*` inkl. Datums-Suffix), neue Capability-Checks (`supports_reasoning`, `supports_verbosity`, `supports_temperature`) und erweiterte `reasoning_effort`-Normalisierung (`none|minimal|low|medium|high|xhigh`).
- Request-Building abgesichert: `reasoning`/`text.verbosity` werden nur noch bei kompatiblen GPT-5-Familien gesendet; Nicht-GPT-5-Fallbacks wie `gpt-4o-mini` erhalten keine GPT-5-spezifischen Felder.
- Tests erweitert (`tests/test_openai_smoke_modes.py`) für Snapshot-Erkennung, neue Effort-Werte und striktes Feld-Gating für Fallback-Modelle.
- `settings_openai.py` fachlich gehärtet: `reasoning_effort`/`verbosity` sind jetzt optional (`None` statt aggressiver Defaults), Timeout-Default zentral auf `120s` gesetzt und sichere Provenance-Infos (`resolved_from`) pro Key ergänzt, ohne Secret-Werte zu exponieren.
- OpenAI-Fehlerbehandlung weiter gehärtet: differenzierte Mappings für `AuthenticationError`, `APITimeoutError`/`TimeoutError`, `APIConnectionError`, `BadRequest` inkl. `unsupported parameter` sowie Structured-Output-Parse-/Validation-Fehler.
- `OpenAICallError` transportiert jetzt optionale interne Fehlercodes (`OPENAI_AUTH`, `OPENAI_TIMEOUT`, `OPENAI_BAD_REQUEST`, `OPENAI_PARSE`, etc.) für präzisere UI-/Debug-Ausgabe ohne sensitive Daten.
- OpenAI-Callsites nutzen jetzt automatische Retries mit exponentiellem Backoff für transiente Timeout-/Connection-Fehler.
- UI-Fehleranzeige zentralisiert (`render_openai_error` + Error-Banner): kurze DE/EN Meldungen für Endnutzer, optionaler non-sensitive Debugkontext via `OPENAI_DEBUG_ERRORS`.
- Tests erweitert: Error-Mapping deckt jetzt zusätzlich `APIConnectionError`, Fehlercodes und `unsupported parameter` ab; Smoke-Test enthält eine gezielte Invalid-Reasoning/Temperature-Simulation über Request-Builder-Gating.
