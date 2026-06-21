# Aktualisierter Deep-Research-Report für cs_need_analysis

## Gesamturteil

Das Repository ist fachlich kein Prototyp mehr, sondern ein bereits weitgehend ausgebauter, zustandsbehafteter Streamlit-Wizard für Vacancy Intake und Recruitment-Need-Analysis mit Jobspec-Extraktion, ESCO/EURES-Anreicherung, Gehaltsprognose, Interviewprozess und Summary-/Artefakt-Workspaces. Die aktuell dokumentierte Kernfunktionalität umfasst genau diese Kette: Quellenaufnahme aus Datei oder Freitext, Privacy-first Intake, strukturierte Extraktion, prüfbare Identified-Information, frageplanbasierte Downstream-Erhebung, ESCO-Anchoring mit Fallback, Company-/Team-Kontext, Rollen-/Skill-/Benefit-Kuration, Salary Forecast, Interviewprozess sowie Summary, Artefakte und Exporte. citeturn4view0turn10view1turn10view2

Mein strategisches Urteil ist deshalb zweigeteilt. **Produktisch** ist der Wizard bereits stark und funktionsreich. **Technisch** ist die Richtung richtig, aber die Codebasis befindet sich jetzt in einer typischen Übergangsphase: Die ersten großen Härtungs- und Modularisierungsschritte sind erkennbar, doch mehrere dieser Schritte sind noch nicht bis zur eigentlichen Endform durchgezogen. Besonders deutlich ist das bei State-Handling, Summary-Slicing, UI-Modularisierung, Dokumentationskonsistenz und operativer CI-/Security-Reife. citeturn4view0turn10view1turn10view4

Für die Bewertung der ersten Codex-Welle ist die wichtigste Aussage: **Die ersten neun großen Maßnahmen sind in der angehängten Snapshot-Arbeitsbasis überwiegend sichtbar oder klar vorbereitet; die verbleibenden Risiken liegen jetzt weniger in “ob vorhanden?” als in “wie sauber zu Ende integriert?”** Das verschiebt die Priorität weg von Einzel-Fixes hin zu Konsolidierung, zweiter Modularisierungswelle, systematischen Sicherheits- und Contract-Gates sowie besserer Push-/Dokumentationsdisziplin.

## Repository-Lage und Evidenzgrenzen

Es gibt derzeit ein relevantes **Baseline-Problem zwischen öffentlichem GitHub-Stand und angehängtem Snapshot**. Die öffentlich erreichbare `README.md` behauptet noch, es gebe keine repo-lokale Ruff-/Black-/Mypy-/Pyright-Konfiguration, und die öffentlich sichtbare CI-Datei zeigt in der Web-Ansicht weiterhin nur einen einzigen `test`-Job mit Install, `pip check`, `compileall`, `pytest -q` und OpenAI-Smoke-Dry-Run. citeturn4view0turn5view0turn10view3

Gleichzeitig enthält der von dir angehängte ZIP-Snapshot eindeutig zusätzliche lokale Dateien und Strukturen, die über diesen öffentlichen Stand hinausgehen, darunter `pyproject.toml`, `requirements-dev.txt`, `requirements-e2e.txt`, `pytest.ini`, `state_store.py`, `tests/e2e/…` sowie die neuen Summary- und UI-Split-Module. Das heißt praktisch: **Der lokale Arbeitsstand ist sehr wahrscheinlich weiter als die öffentlich sichtbare `main`-Ansicht**, während Doku und Push-Stand nicht überall synchron sind. Diese Divergenz ist selbst schon ein Reifeproblem, weil sie externe Reviewbarkeit, Codex-Prompting und Regressionseinschätzungen erschwert. citeturn4view0turn5view0turn10view1

Für die folgende Analyse habe ich deshalb den **angehängten Snapshot als wahrscheinliche Real-Baseline** behandelt und den öffentlichen GitHub-Stand nur als Sekundärsignal verwendet. Wo sich beide widersprechen, ist der Snapshot aus meiner Sicht für die operative Priorisierung wichtiger; für öffentlich belegbare Aussagen verweise ich aber auf die GitHub-/README-/AGENTS-/Dokumentationsquellen und kennzeichne Unsicherheit dort, wo der öffentliche Stand sichtbar hinterherhinkt. citeturn4view0turn5view0turn10view2

## Status des Recruitment-Need-Analysis-Wizards

Funktional ist der Wizard im Kern **vollständig durchgängig**. Die dokumentierte aktive Route verläuft über `intro`, `landing`, `company`, `role_tasks`, `skills`, `benefits`, `interview` und `summary`; die früheren separaten Schritte `jobspec_review` und `team` sind ausdrücklich als legacy bzw. nicht routbar beschrieben. Ebenso dokumentiert das Repo, dass der frühere Review-Flow heute direkt in den Start-Step integriert ist: Phase A für Quelle/Datenschutz, Phase B für Extraktionsprüfung und Phase C für die ESCO-Suche. citeturn4view0

Das bedeutet fachlich: Dein „Recruitment Need Analysis Wizard“ ist heute in der Praxis **ein produktisierter Vacancy-Intake-Wizard mit eingebetteter Need-Analysis-Logik**. Er sammelt nicht nur Rohdaten, sondern kombiniert mehrere Evidenzströme — Jobspec-Extraktion, manuelle Korrektur, ESCO-/EURES-Kontext, Homepage-Recherche, KI-Vorschläge und Salary Engine — und hält manuelle Korrekturen ausdrücklich als autoritativ über extrahierten Werten. Genau das ist der richtige Produktzuschnitt für Recruiting-Intake. citeturn4view0

Auch die Wahl von Structured Outputs passt technisch gut zu dieser Architektur. OpenAI empfiehlt für schemaorientierte Modellantworten ausdrücklich Structured Outputs statt reinem JSON Mode, weil nur Structured Outputs die Schema-Adhärenz absichern; genau dieses Muster ist für Jobspec-Extraktion, Fragepläne, Briefs und Artefakte besonders sinnvoll. citeturn6view6turn4view0

Der State-lastige Charakter der App ist für Streamlit ebenfalls plausibel. Streamlit beschreibt `st.session_state` als zentrales Sitzungsrückgrat, erlaubt Callbacks zur kontrollierten Zustandsaktualisierung und weist zugleich auf Grenzen hin — insbesondere darauf, dass button-/download-/file-uploader-Widgetzustände nicht per Session-State-API gesetzt werden dürfen. Diese offizielle Semantik erklärt, warum eure typed-state-Fassade und die testseitige E2E-Harness-Seeding-Strategie die richtige Richtung sind. citeturn6view5

Mein Funktionsurteil zum Wizard lautet deshalb: **Produktisch einsatznah, technisch im Übergang von “groß gewachsen” zu “professionell konsolidiert”.**

## Audit der bisherigen neun Codex-Aufgaben

Die erste Welle hat aus meiner Sicht einen klaren Nutzen erzeugt. Ich bewerte die neun bereits vorliegenden Aufgaben so:

| Aufgabe | Statusbild | Einschätzung |
|---|---|---|
| Harden Homepage Fetch Security | **weitgehend umgesetzt** | Im Snapshot sind Redirect-Limits, Redirect-Revalidierung, DNS-Auflösung via `getaddrinfo`, IP-Klassifikation und Fehlercodes wie `invalid_or_disallowed_redirect` und `too_many_redirects` sichtbar. Das ist genau die richtige Härtungsrichtung für externes Homepage-Enrichment. |
| Add Security Test Suite | **weitgehend umgesetzt** | Es gibt klar sichtbare Tests für hostile HTML, Preview-Escaping, Corrupt DOCX/PDF, Oversize-Uploads und Homepage-Fetching-Kanten. Dadurch wurde aus einem impliziten Sicherheitsansatz ein prüfbarer Contract. |
| Add Bounded LLM Cache Eviction | **umgesetzt** | In `llm_client.py` ist eine kanonische Begrenzung mit Eviction-Helper erkennbar. Das entschärft Langsession-Wachstum und passt zur Forderung, zentrale OpenAI-Request- und Cachelogik in `llm_client.py` zu halten. citeturn10view1 |
| Harden Source Switch State | **umgesetzt** | Fingerprint-basierte Source-Wechsel und abhängige State-Invalidierung sind im Snapshot sichtbar. Das ist besonders wichtig, weil Streamlit bei Interaktion neu rendert und stale Ableitungszustände sonst leicht weiterleben. citeturn6view5 |
| Add Typed State Facade | **umgesetzt, aber erst teiladoptiert** | `state_store.py` ist ein klarer Fortschritt. Strategisch ist das richtig, weil neue Session-State-Zugriffe typisiert und weniger fehleranfällig werden. Noch nicht alle Bereiche scheinen aber bereits umgestellt. |
| Split Summary Into Slices | **strukturell umgesetzt, operativ noch nicht “fertig”** | Die neue Summary-Zerlegung ist real: `summary_readiness`, `summary_artifact_actions`, `summary_exporters`, `summary_view`. Gleichzeitig ist die neue Gesamtfläche noch sehr groß, und viel Boilerplate wurde eher verteilt als eliminiert. AGENTS verlangt hier zurecht, dass Summary-Arbeit nur als vollständig gilt, wenn State, UI, Export und Doku synchron bleiben. citeturn10view2turn10view4 |
| Modularize ui_components | **erste Welle umgesetzt, zweite Welle offen** | Die neue Modulstruktur ist vorhanden, und Tests scheinen bereits auf Owning Modules umzuschwenken. Gleichzeitig bleibt mit `ui_inputs.py` ein neuer Großmonolith zurück; der Architekturschmerz wurde verlagert, nicht vollständig entfernt. |
| Add Playwright Smoke Tests | **umgesetzt** | Es gibt nun eine optionale E2E-Schicht mit Marker, separaten Requirements, festem Port, Streamlit-Harness und deterministischem Seeding. Das ist exakt die richtige Ergänzung zu einer sonst eher unterhalb des Browsers testenden Suite. |
| Add Incremental QA Gates | **im Snapshot umgesetzt, aber öffentlich/dokumentarisch unsauber** | `pyproject.toml`, `requirements-dev.txt`, Bandit, Ruff, Black, mypy und optionales E2E-Setup sind im Snapshot da. Öffentlich sichtbare README-/AGENTS-/CI-Signale sind aber noch widersprüchlich oder offenbar nicht überall gepusht. Das ist aktuell der größte Meta-Mangel dieser Welle. citeturn4view0turn5view0turn10view3 |

Das wichtigste Muster dabei ist: **Die Richtung stimmt fast durchgängig, aber mehrere Maßnahmen sind in “Phase eins abgeschlossen, Phase zwei offen”.** Die nächsten PR-Slices sollten deshalb weniger neue Fronten eröffnen und mehr Konsolidierung erzeugen.

## Priorisierte verbleibende Verbesserungen

Die folgende Liste ist meine sortierte „First-Wave“-Priorisierung für die ausstehenden Aufgaben. Ich gruppiere sie nicht nach schöner Architektur, sondern nach **Risikoreduktion pro investierter PR-Größe**.

| Priorität | Verbesserung | Warum jetzt | Erwarteter Effekt |
|---|---|---|---|
| **Kritisch** | **README-/AGENTS-/CI-Drift automatisch erkennen und schließen** | Öffentliche Doku und sichtbare CI widersprechen dem Snapshot. Das erzeugt Fehlsteuerung für Menschen und Codex zugleich. AGENTS verlangt ausdrücklich, dass State, UI, Exporte, Tests und README synchron bleiben. citeturn10view1turn10view4turn4view0turn5view0 | Niedriger Aufwand, hoher Governance-Gewinn. |
| **Kritisch** | **Unsafe-HTML-Audit und Wrapper-Pflicht durchsetzen** | Der Snapshot zeigt weiterhin eine größere Zahl direkter `unsafe_allow_html=True`-Aufrufe außerhalb des kontrollierten `safe_html`-Pfads. Für eine Streamlit-App mit vielen dynamischen Blöcken ist das unnötiger Angriffs- und Review-Overhead. | Klare HTML-Policy, weniger XSS-/Injection-Fläche, einfachere Audits. |
| **Kritisch** | **Secrets- und Binary-Artifact-Scan in CI ergänzen** | Bandit hilft, aber deckt weder Secret-Leaks noch unerwünschte Binärartefakte vollständig ab. Das ist gerade bei Uploads, Exports und `.streamlit`-/Env-Workflows wichtig. | Weniger Leckrisiko, frühere Erkennung im PR-Flow. |
| **Kritisch** | **Logo-/Style-Uploads für Summary-Artefakte härten** | Aktuell ist die Logo-Normalisierung im Snapshot im Kern MIME- und Non-Empty-basiert; harte Größen-, Decode- und Dimensionsgrenzen fehlen noch. Das ist ein klassischer „small surface, high leverage“-Fix. | Reduziert Artefakt-/DOCX-/PDF-Risiken spürbar. |
| **Hoch** | **`constants.py` segmentieren, aber Import-Vertrag beibehalten** | AGENTS macht `constants.py` zur Single Source of Truth. Genau deshalb ist die Datei heute zu groß und zu review-intensiv geworden. citeturn10view1 | Weniger Konflikte, bessere Reviewbarkeit ohne Contract-Bruch. |
| **Hoch** | **`question_packs/registry.py` datengetrieben machen** | Der Fragepack-Stack ist geschäftskritisch und aktuell stark codiert. Ein datengetriebener Registry-Ansatz senkt Coupling und erleichtert Overlay-Tests. | Bessere Erweiterbarkeit, weniger Merge-Konflikte. |
| **Hoch** | **Enrichment-Services von UI-Modulen trennen** | Homepage-, ESCO- und Salary-nahe Logik sitzt teils noch UI-nah. Streamlit empfiehlt für saubere Wiederverwendung und Caching eine klare Trennung zwischen Datenfunktionen und globalen Ressourcen. citeturn11view0turn11view1 | Bessere Testbarkeit, klarere Caches, leichtere Parallelisierung. |
| **Hoch** | **Summary zweite Refaktor-Welle** | Das Summary-Slicing war sinnvoll, aber die Slice-Files sind zusammen noch sehr groß. Jetzt lohnt sich ein zweiter Pass auf gemeinsame Helper, Import-Deduplikation und Artifact-spezifische Exportmodule. AGENTS betont, dass Summary-Änderungen nur vollständig sind, wenn State, Export und UI konsistent bleiben. citeturn10view2turn10view4 | Größter langfristiger Wartbarkeitshebel. |
| **Hoch** | **`ui_inputs.py` weiter zerlegen und direkte HTML-Renderpfade reduzieren** | Die erste UI-Modularisierung war richtig, aber ein großer Schwerpunkt blieb als neuer Monolith zurück. | Kleinere PRs, weniger Seiteneffekte, bessere UX-Iteration. |
| **Hoch** | **Optionale Homepage-Domain-Allowlist plus negativer Host-Cache** | Die DNS-/Redirect-Härtung ist da; die nächste Sicherheitsstufe ist operative Policy: optionale Allowlist sowie kurzer negativer Host-/Failure-Cache, damit schlechte Ziele nicht ständig erneut geprüft werden. | Mehr Produktionssicherheit und bessere Latenz unter Fehlerlast. |
| **Mittel** | **Integration-CI mit “voller Laufzeit” ergänzen** | Die E2E-Smokes sind opt-in; sinnvoll ist zusätzlich ein klar abgegrenzter Full-Runtime-Job, der reale Streamlit-/pytest-/OpenAI-Dry-Run-Pfade in einer konsistenten Umgebung abprüft. | Höhere Aussagekraft vor Merge und Release. |
| **Mittel** | **Reproduzierbare Installationen und Dependency-Split** | `requirements.txt`, `requirements-dev.txt`, `requirements-e2e.txt` sind ein guter Anfang, aber noch kein wirklich reproduzierbarer Install-Contract. | Weniger “works on my machine”, stabilere CI. |
| **Mittel** | **Snapshot-/Golden-Tests für Exporte und Prompts** | Für ein artefaktorientiertes Produkt sind Approval-/Golden-Tests oft wertvoller als viele kleine Kleintests. OpenAI Structured Outputs geben dafür eine gute Schema-Basis. citeturn6view6 | Stabilere Artefakte, schnelleres Regression-Review. |
| **Mittel** | **Property-Tests für Frageplan- und Fact-Resolution-Invarianten** | Gerade im Frageplan-/Fact-Stack steckt viel kombinatorische Logik. | Fängt seltene Kanteneffekte besser als rein beispielbasierte Tests. |
| **Mittel** | **Streamlit-Fragments gezielt bei schweren Panels pilotieren** | Streamlit-Fragments können unabhängig vom Rest der App rerunnt werden; das ist für schwere Summary-/Skills-/Salary-Bereiche ein realistischer Performance-Hebel, sofern Seiteneffekte sauber gehandhabt werden. citeturn9view0 | Bessere Interaktivität ohne kompletten Architekturumbau. |
| **Mittel** | **Accessibility-Pass für den operativen Wizard** | Spätestens bei einem HR-/Operations-Produkt mit viel Formularlogik ist Accessibility kein Nice-to-have. | Klare UX-Qualitätssteigerung, weniger Barrieren. |

Wenn ich nur die **drei** nächsten PR-Slices wählen dürfte, wären es diese: **Drift Detection**, **Unsafe-HTML-Audit**, **Logo-/Style-Upload-Härtung**. Sie sind kleiner als die großen Architekturschnitte, aber liefern sofort Governance-, Sicherheits- und Review-Gewinn.

## Priorisierte Codex-Prompts

Für Codex selbst würde ich mich jetzt sehr eng an die offizielle Empfehlung halten: Codex liefert bessere Ergebnisse, wenn der Auftrag eine **klare Verifikation** enthält, und komplexe Arbeit sollte in **kleine, fokussierte Schritte** zerlegt werden. Für die Modellauswahl empfiehlt OpenAI, **für die meisten Aufgaben mit `gpt-5.5` zu starten** und **`gpt-5.4-mini` für schnellere, leichtere Subtasks** oder Dokumentations-/Hilfsarbeiten zu nutzen. citeturn6view1turn6view3turn6view4

### Prompt für Drift Detection und Contract Sync

**Modell:** `gpt-5.5`  
**Plan/Ziel:** Contract-Grenze zwischen README, AGENTS, CI und realem Repo automatisch absichern.  
**Reasoning-Level:** high  
**Conclusion-Level:** concise

```text
You are modifying the repository cs_need_analysis.

Task:
Add automated README / AGENTS / CI drift detection for the current repo contract

Repro / current problem:
Public-facing repo documentation and automation signals can drift from the actual implementation state. In the current working snapshot, tooling and test surfaces have evolved, but repo contracts and docs are at risk of lagging behind, which misleads reviewers and future Codex threads.

Expected target state:
The repo should fail fast when core contract claims drift across:
- README.md
- AGENTS.md
- .github/workflows/ci.yml
- pytest.ini
- requirements-dev.txt / requirements-e2e.txt / pyproject.toml where relevant

Likely files:
- README.md
- AGENTS.md
- .github/workflows/ci.yml
- tests/test_repo_contract_drift.py
- tests/test_quality_gate_config.py
- tests/test_wizard_contract.py

Constraints:
- Read AGENTS.md first and follow the repository contract.
- Use minimal diffs. No broad docs rewrite unless needed to remove objective contradictions.
- Preserve current public helper names and wizard behavior.
- Keep constants/schema/state/UI/tests/docs synchronized if a contract statement changes.
- Do not add new third-party dependencies.
- Do not log secrets, tokens, credentials, or PII.

Required outcomes:
1. Identify current contract claims that are objectively testable:
   - active wizard step order
   - legacy/non-routable steps
   - existence of repo-local QA files
   - presence of optional e2e marker config
   - CI job names / major gates
2. Add a focused contract test that asserts those claims from the live repo files.
3. Remove or update contradictory README / AGENTS statements so they match the actual codebase.
4. Keep the tests narrow and low-noise; avoid testing prose that is subjective.
5. Preserve German user-facing product copy unless contradiction cleanup requires a wording fix.

Verification:
- python -m pytest -q tests/test_repo_contract_drift.py tests/test_wizard_contract.py tests/test_quality_gate_config.py
- python -m compileall -q README.md AGENTS.md .github/workflows tests

Deliverables:
- Minimal code/docs/test changes.
- Updated or added focused tests.
- Short final note with: changed files, tests run, assumptions, unresolved risks.
```

### Prompt für Unsafe HTML Audit und Wrapper-Pflicht

**Modell:** `gpt-5.5`  
**Plan/Ziel:** direkte `unsafe_allow_html`-Verwendung systematisch auf repo-eigene Wrapper und klar erlaubte statische Blöcke reduzieren.  
**Reasoning-Level:** high  
**Conclusion-Level:** concise

```text
You are modifying the repository cs_need_analysis.

Task:
Audit and wrap unsafe Streamlit HTML rendering

Repro / current problem:
The repo contains a growing number of direct `st.markdown(..., unsafe_allow_html=True)` calls across wizard pages and UI helpers. This makes review difficult and weakens the current “escape dynamic values first” discipline.

Expected target state:
Dynamic HTML rendering should use canonical safe helpers, and direct `unsafe_allow_html=True` usage should be limited to clearly static, repo-owned markup with explicit justification.

Likely files:
- safe_html.py
- app.py
- site_ui.py
- ui_layout.py
- ui_components.py
- ui_*.py
- wizard_pages/*.py
- tests/test_summary_exports.py
- tests/test_landing_iceberg_component.py
- add targeted tests if needed

Constraints:
- Read AGENTS.md first and follow the repository contract.
- Use minimal diffs and preserve public helper names unless a compatibility wrapper is provided.
- Do not redesign UI or restyle widgets.
- Do not change product copy beyond necessary escaping/help-text fixes.
- Do not add dependencies.
- No secrets, PII, raw prompts, or sensitive payloads in tests or logs.

Required outcomes:
1. Inventory all direct `unsafe_allow_html=True` call sites.
2. Classify each as:
   - static repo-owned markup that can remain
   - dynamic markup that must be routed through `safe_html.render_static_html` or a new thin helper
3. Replace the dynamic cases first, keeping behavior unchanged.
4. Add a narrow regression test that would fail if hostile dynamic values are interpolated unsafely in the converted helpers.
5. Leave comments only where a direct static HTML call is intentionally retained.

Verification:
- python -m pytest -q tests/test_summary_exports.py tests/test_landing_iceberg_component.py tests/test_public_page_links.py
- python -m compileall -q safe_html.py app.py site_ui.py ui_layout.py ui_*.py wizard_pages tests

Deliverables:
- Minimal code/test changes.
- A short inventory in the final note: converted call sites, intentionally retained static call sites, tests run, assumptions, unresolved risks.
```

### Prompt für Secrets- und Binary-Artifact-Scanning

**Modell:** `gpt-5.5`  
**Plan/Ziel:** Security-Gates um Secret- und Artefakt-Scans erweitern, ohne Fast-Path-CI unnötig zu verlangsamen.  
**Reasoning-Level:** medium-high  
**Conclusion-Level:** concise

```text
You are modifying the repository cs_need_analysis.

Task:
Add secrets and binary artifact scanning to CI

Repro / current problem:
Current QA/security gates cover lint/type/bandit-style checks, but not secret leakage or unwanted binary artifact drift. This is risky for a repo with exports, screenshots, app assets, and environment-driven configuration.

Expected target state:
Add low-noise CI scanning for:
- leaked secrets / credential-like material
- unexpected binary artifacts or generated files in tracked paths
while keeping the fast local/unit path practical.

Likely files:
- .github/workflows/ci.yml
- README.md
- .gitignore
- tests/test_quality_gate_config.py
- optional lightweight config files if needed

Constraints:
- Read AGENTS.md first and follow the repository contract.
- Use minimal diffs.
- Do not add noisy tools that will immediately fail on large existing baselines unless you stage them safely.
- Do not expose secrets in fixtures, examples, or logs.
- Keep dev/CI-only tooling separate from runtime dependencies.

Required outcomes:
1. Add one secrets scanning gate and one binary/generated-artifact sanity check suitable for CI.
2. Prefer advisory/continue-on-error first if the baseline needs triage.
3. Ensure reports and caches remain excluded where appropriate.
4. Document local usage briefly in README.
5. Add or update a focused config/CI contract test if the repo already tests QA config.

Verification:
- python -m pytest -q tests/test_quality_gate_config.py tests/test_public_page_links.py
- python -m compileall -q .github/workflows tests

Deliverables:
- Minimal CI/docs/test changes.
- Short final note with changed files, commands run, assumptions, unresolved risks, and whether the new scan is blocking or advisory.
```

### Prompt für Logo- und Style-Upload-Härtung

**Modell:** `gpt-5.5`  
**Plan/Ziel:** Summary-Artefakt-Uploads auf reale Bildvalidierung, Größenlimit und harmlose Failure-Modes bringen.  
**Reasoning-Level:** high  
**Conclusion-Level:** concise

```text
You are modifying the repository cs_need_analysis.

Task:
Validate logo and style uploads for summary artifacts

Repro / current problem:
Summary artifact configuration accepts logo/style-related uploads too permissively. MIME checks alone are not enough for robust artifact generation.

Expected target state:
Logo uploads should be validated with canonical, privacy-safe rules:
- allowed MIME types and extensions
- max byte size
- successful decode / image sanity
- safe storage shape in session state
- predictable fallback when invalid

Likely files:
- wizard_pages/summary_exporters.py
- wizard_pages/08_summary.py
- constants.py
- tests/test_summary_job_ad_config_panel.py
- tests/test_summary_exports.py

Constraints:
- Read AGENTS.md first and follow the repository contract.
- Use minimal diffs and preserve public helper names unless compatibility wrappers are needed.
- Do not redesign the panel.
- Do not add new heavy dependencies unless already available transitively and clearly justified.
- Do not log raw uploaded bytes, user content, or PII.

Required outcomes:
1. Add canonical size/type validation constants.
2. Reject empty, oversized, unsupported, or decode-invalid logo payloads before storage/use.
3. Keep the stored session-state payload normalized and deterministic.
4. Add focused tests for valid PNG/JPEG, unsupported MIME, oversized payload, and corrupt image bytes.
5. Keep current export behavior unchanged for valid fixtures.

Verification:
- python -m pytest -q tests/test_summary_job_ad_config_panel.py tests/test_summary_exports.py tests/test_summary_active_artifact.py
- python -m compileall -q wizard_pages/summary_exporters.py wizard_pages/08_summary.py constants.py tests

Deliverables:
- Minimal code/docs/test changes.
- Final note with changed files, validation policy, tests run, assumptions, unresolved risks.
```

### Prompt für `constants.py`-Segmentierung

**Modell:** `gpt-5.5`  
**Plan/Ziel:** kanonische Verträge modularisieren, ohne den bestehenden Importvertrag zu zerstören.  
**Reasoning-Level:** high  
**Conclusion-Level:** concise

```text
You are modifying the repository cs_need_analysis.

Task:
Segment constants.py without losing the canonical import contract

Repro / current problem:
`constants.py` remains the single source of truth, but it has become too large and too conflict-prone. Review, merge, and targeted reasoning are harder than necessary.

Expected target state:
Split `constants.py` into focused internal modules while keeping `constants.py` as the stable compatibility import surface for the rest of the repo.

Likely files:
- constants.py
- new internal constants modules
- state.py
- state_store.py
- summary_artifacts.py
- tests/test_wizard_contract.py
- tests/test_quality_gate_config.py if needed
- any focused import-stability tests you add

Constraints:
- Read AGENTS.md first and follow the repository contract.
- `constants.py` must remain the canonical public entrypoint.
- No raw session-state string keys where `SSKey` should exist.
- Use minimal diffs and avoid broad caller churn in the first PR.
- Keep tests/docs aligned if any canonical grouping names appear in README/AGENTS.

Required outcomes:
1. Identify natural groups, e.g. wizard steps, UI modes, SSKey/state, facts, summary artifact IDs, usage event types.
2. Extract only those groups that materially reduce merge pressure.
3. Keep `from constants import ...` working for existing callers.
4. Add a focused import-contract regression test.
5. Do not change values, key strings, or IDs.

Verification:
- python -m pytest -q tests/test_wizard_contract.py tests/test_state_reset.py tests/test_summary_action_registry.py
- python -m compileall -q constants.py state.py state_store.py summary_artifacts.py tests

Deliverables:
- Minimal module split with compatibility exports.
- Final note with extracted groups, unchanged public contract, tests run, assumptions, unresolved risks.
```

### Prompt für eine datengetriebene Question-Pack-Registry

**Modell:** `gpt-5.5`  
**Plan/Ziel:** Fragepack-Definitionen von Python-Boilerplate in validierbare Datenstrukturen verschieben.  
**Reasoning-Level:** high  
**Conclusion-Level:** concise

```text
You are modifying the repository cs_need_analysis.

Task:
Make question_packs/registry.py data-driven

Repro / current problem:
The question-pack registry is too code-heavy. Adding or reviewing packs requires editing a large Python registry instead of validating focused data and a small loader.

Expected target state:
Move stable question-pack metadata/registration into data-driven files or compact structured declarations, while preserving current runtime behavior and canonical question IDs.

Likely files:
- question_packs/registry.py
- question_packs/*
- schemas.py
- question_plan_compiler.py
- tests/test_question_pack_compiler.py
- tests/test_question_plan_normalization.py
- tests/test_wizard_contract.py

Constraints:
- Read AGENTS.md first and follow the repository contract.
- Use minimal diffs; no redesign of the question model.
- Keep canonical IDs, step keys, and behavior unchanged.
- Preserve existing public loader names unless a compatibility wrapper is added.
- Do not add unnecessary dependencies.

Required outcomes:
1. Identify the lowest-risk slice to data-drive first.
2. Introduce a small loader/validator path.
3. Keep the registry contract stable for existing callers.
4. Add or update tests proving parity for the migrated packs.
5. Avoid broad migration in one PR; make the pattern reusable.

Verification:
- python -m pytest -q tests/test_question_pack_compiler.py tests/test_question_plan_normalization.py tests/test_question_progress.py
- python -m compileall -q question_packs question_plan_compiler.py schemas.py tests

Deliverables:
- Minimal first migration slice.
- Final note with migrated scope, compatibility story, tests run, assumptions, unresolved risks.
```

### Prompt für Service-Extraktion aus UI-nahen Enrichment-Modulen

**Modell:** `gpt-5.5`  
**Plan/Ziel:** Homepage-, ESCO- und Salary-nahe Orchestrierung aus UI-Seiten in thin service layer verlagern.  
**Reasoning-Level:** high  
**Conclusion-Level:** concise

```text
You are modifying the repository cs_need_analysis.

Task:
Separate enrichment services from UI modules

Repro / current problem:
Operational enrichment logic is still too close to Streamlit page modules. This increases rerun side effects, makes targeted testing harder, and weakens future caching/performance work.

Expected target state:
Introduce a thin service layer for selected enrichment paths while preserving the current UI behavior and public helper contracts.

Likely files:
- wizard_pages/02_company.py
- wizard_pages/04_role_tasks.py
- wizard_pages/05_skills.py
- homepage_research.py
- esco_client.py / esco_semantics.py / salary/*
- new service modules if justified
- targeted tests in company/skills/salary areas

Constraints:
- Read AGENTS.md first and follow the repository contract.
- Use minimal diffs.
- Preserve current wizard behavior and public helper names unless a compatibility wrapper is provided.
- Keep OpenAI request construction centralized in llm_client.py.
- Keep constants/state/schema/tests/docs synchronized when boundaries change.
- No new third-party dependencies.

Required outcomes:
1. Choose one or two enrichment flows with the best payoff, not the whole repo.
2. Extract side-effect-light service functions that return data, not Streamlit UI.
3. Keep caching/state behavior explicit and unchanged.
4. Add focused tests for the new service seam.
5. Document the seam briefly if new code should use it going forward.

Verification:
- python -m pytest -q tests/test_company_team_scope_regression.py tests/test_skills_occupation_suggestions.py tests/test_salary_forecast_plot_theme.py
- python -m compileall -q wizard_pages homepage_research.py esco_client.py salary tests

Deliverables:
- Minimal service extraction slice.
- Final note with changed files, chosen seam, tests run, assumptions, unresolved risks.
```

### Prompt für artifact-spezifische Export-Module

**Modell:** `gpt-5.5`  
**Plan/Ziel:** die zweite Summary-Welle gezielt auf Exporter richten, ohne den sichtbaren Summary-Flow umzubauen.  
**Reasoning-Level:** high  
**Conclusion-Level:** concise

```text
You are modifying the repository cs_need_analysis.

Task:
Extract artifact exporters into artifact-specific modules

Repro / current problem:
After the first Summary split, exporter logic is still broad and centrally concentrated. Artifact-specific DOCX/PDF/Markdown logic remains difficult to reason about and retest independently.

Expected target state:
Move exporter implementations into artifact-specific modules while preserving `wizard_pages/08_summary.py` behavior, artifact IDs, and test expectations.

Likely files:
- wizard_pages/summary_exporters.py
- summary_exports.py
- summary_job_ad.py
- summary_artifacts.py
- tests/test_summary_exports.py
- tests/test_summary_export_payload.py
- tests/test_summary_active_artifact.py

Constraints:
- Read AGENTS.md first and follow the repository contract.
- Use minimal diffs and keep public Summary behavior stable.
- Do not add new export formats.
- Do not redesign Summary UI.
- Keep constants/state/tests/docs synchronized if any artifact contract shifts.

Required outcomes:
1. Identify the cleanest artifact boundary to extract first.
2. Keep `wizard_pages/08_summary.py` and current callers stable through imports/wrappers.
3. Reduce cross-artifact coupling in exporter code.
4. Update focused tests only where a moved helper target requires it.
5. Keep German copy unchanged unless tests require otherwise.

Verification:
- python -m pytest -q tests/test_summary_exports.py tests/test_summary_export_payload.py tests/test_summary_active_artifact.py tests/test_summary_action_registry.py
- python -m compileall -q wizard_pages/08_summary.py wizard_pages/summary_exporters.py summary_*.py tests

Deliverables:
- Minimal first exporter extraction slice.
- Final note with changed files, extracted artifact boundary, tests run, assumptions, unresolved risks.
```

### Empfohlene Ausführungsreihenfolge

Wenn du diese Prompts jetzt nacheinander an Codex gibst, würde ich exakt diese Reihenfolge wählen:

1. **Drift Detection und Contract Sync**  
2. **Unsafe HTML Audit**  
3. **Secrets-/Binary-Scanning**  
4. **Logo-/Style-Upload-Härtung**  
5. **`constants.py` segmentieren**  
6. **Question-Pack-Registry datengetrieben**  
7. **Enrichment-Services extrahieren**  
8. **Artifact-spezifische Export-Module**

Das entspricht sowohl der Repo-Logik aus `AGENTS.md` — kanonische Konstanten, zentralisierte OpenAI-Logik, synchronisierte State/UI/Export-Verträge — als auch der offiziellen Codex-Empfehlung, komplexe Arbeit in kleine, überprüfbare Schritte mit klaren Verifikationsbefehlen zu zerlegen. citeturn10view1turn10view4turn6view1turn6view3turn6view4