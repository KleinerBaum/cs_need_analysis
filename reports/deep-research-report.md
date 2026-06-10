# Analyse und Ausbauplan für die Recruitment Need Analysis App

## Gesamturteil

Der aktuelle Stand des Repos ist bereits deutlich weiter als ein Prototyp: Die App ist als zustandsbehafteter, mehrstufiger Wizard aufgebaut und deckt heute schon Jobspec-Extraktion, ESCO-Ankerung, Website-Enrichment, Skill-/Task-/Benefit-Kuration, Salary-Forecast sowie Summary-Artefakte ab. Der Startschritt ist bereits in drei Phasen gegliedert, es gibt globale UI-Modi, PII-arme Quellverarbeitung, Vergleichs- und Übernahmeblöcke sowie eine zusammengeführte Summary-/Action-Hub-Logik. Gleichzeitig benennt das Repo selbst noch klare Grenzen: Die volle offizielle ESCO-Bulk-Ingestion ist noch nicht umgesetzt, das Offline-Indexing ist lookup-orientiert, und einige Teile sind bewusst minimal gehalten. Das ist eine gute Ausgangslage: Die Architektur ist tragfähig, aber der Informationsgewinnungsprozess kann noch spürbar präziser, intelligenter und nutzerfreundlicher werden. citeturn1view0turn2view0turn1view1

Mein Fazit in einem Satz: **Du brauchst keine Grundsanierung, sondern eine gezielte zweite Ausbaustufe** — mit stärkerem Evidenzmodell, intelligenterer Fragepriorisierung, transparenterem Retrieval/RAG und einer versionierten ESCO-Ingestion, die später sauber skaliert. Das ist besonders sinnvoll, weil ESCO offiziell frei downloadbar ist, in 28 Sprachen verfügbar ist und sowohl API- als auch Download-/Local-API-Pfade anbietet; zugleich listet die ESCO-Seite inzwischen bereits Version 1.2.1 als aktuelle Version. citeturn21view0turn21view1turn22view0

## Was der aktuelle Stand bereits richtig macht

Die wichtigste Stärke ist die **klare Prozessdramaturgie**. Die App führt nicht einfach durch ein starres Formular, sondern beginnt mit Quellenaufnahme, Datenschutz-/PII-Handling, strukturierter Extraktion und anschließender ESCO-Bestätigung. Danach folgen fachlich klar abgegrenzte Schritte für Unternehmen, Rolle & Aufgaben, Skills, Benefits, Interviewprozess und Summary. Genau diese Reihenfolge ist für einen Recruitment-Need-Analysis-Prozess sinnvoll, weil sie vom unsicheren Rohtext zu immer stärker bestätigten, downstream-relevanten Entscheidungen führt. citeturn1view0turn2view0

Ebenfalls stark ist, dass das Repo bereits **mehrere Evidenzströme** zusammenführt: Jobspec-Extraktion, manuelle Korrektur, ESCO/EURES-Kontext, Website-Recherche, AI-Vorschläge und Salary-Engine. Das ist fachlich genau richtig, denn gute Recruiting-Scopings entstehen fast nie aus nur einer Quelle. Positiv ist auch, dass manuelle Korrekturen im App-Modell priorisiert bleiben. Diese Invariante solltest du unbedingt beibehalten. citeturn1view1turn2view0

Der Skills-Bereich ist bereits in die richtige Richtung entwickelt: Es gibt extrahierte Begriffe, ESCO-Normalisierung, sichtbare Must-/Nice-Logik, AI-Vorschläge und einen dedizierten Bereich für noch nicht normalisierte Begriffe. Dass zusätzliche AI-Vorschläge nicht unendlich aggressiv generiert werden, sondern im UI begrenzt und erklärbar nachgeladen werden, ist ebenfalls vernünftig. Im Code/Repo ist sogar schon sichtbar, dass die ersten fünf AI-Vorschläge einmalig automatisch erzeugt werden und weitere Vorschläge bewusst nach Bedarf ergänzt werden. citeturn2view0turn8view3turn7view1

Auch die technische Richtung für Streamlit ist prinzipiell stimmig: Session State trägt den Wizard-Zustand über Reruns und Seiten hinweg, was genau dem Multipage-/Wizard-Muster entspricht. Das passt zur Streamlit-Architektur. Gleichzeitig bietet Streamlit mit `st.form` und `st.fragment` inzwischen bessere Mittel, um Widget-Änderungen zu bündeln bzw. nur Teilbereiche neu zu rendern; genau dort liegt jetzt das nächste Optimierungspotenzial. citeturn19view4turn18view0turn19view0

## Wo der Informationsgewinnungsprozess noch Potenzial verschenkt

Der größte inhaltliche Hebel liegt nicht in “mehr LLM”, sondern in einem **besseren Auflösungsmodell für Unsicherheit**. Der Wizard sammelt bereits Informationen aus vielen Quellen, aber der nächste Qualitätssprung entsteht erst dann, wenn jede Information konsequent als eine dieser Klassen behandelt wird: `bestätigt`, `abgeleitet`, `vermutet`, `widersprüchlich`, `fehlend`. Solange dieser Status nicht als kanonische Schicht durch Intake, Zwischenstände, Summary und Exporte läuft, bleibt die Nutzerführung zwangsläufig reaktiver als nötig. Dann sieht der Nutzer zwar viele Informationen, aber nicht immer klar genug, **welche Angabe wirklich sicher ist, welche nur plausibel klingt und welche die größte Wirkung auf Briefing, Matching und Job Ad hätte**. Das ist aus meiner Sicht der wichtigste noch offene Punkt. citeturn2view0turn1view1

Der zweite Hebel ist die **Fragen-Selektion nach Informationsgewinn statt nur nach Step-Logik**. Das Repo hat schon ein differenziertes Frageplan-/Priority-/Dependency-Modell und gekoppelte UI-Modi. Aber fachlich wäre der nächste Schritt, jede offene Frage zusätzlich nach ihrem erwarteten Nutzen zu ranken: Wie stark verändert ihre Antwort Recruiting Brief, Interviewleitfaden, Salary Forecast, Skill-Matching oder ESCO-Kohärenz? Aktuell wirkt der Prozess schon strukturiert, aber noch nicht maximal informationsökonomisch. Genau hier kannst du Benutzerfreundlichkeit und Präzision gleichzeitig steigern: **weniger Fragen, aber die richtigen zuerst**. citeturn1view1turn2view0

Der dritte Hebel ist die **Quellentransparenz pro Vorschlag**. Heute gibt es schon Vergleichs- und Übernahmeflächen; in der nächsten Stufe sollte jeder Vorschlag sichtbarer erklären, warum er erscheint: “aus Anzeige”, “aus ESCO essential”, “aus Website”, “aus RAG-Treffer”, “nur LLM-Inferenz”. Je genauer diese Herkunft und Beleglage im UI sichtbar wird, desto leichter kann ein Hiring Manager schnell valide Entscheidungen treffen, ohne sich entweder blind auf AI zu verlassen oder alles manuell gegenzuprüfen. OpenAI dokumentiert inzwischen ausdrücklich, dass Suchergebnisse, Metadatenfilter und eingeschlossene Retrieval-Resultate explizit in Responses eingebunden werden können; genau diese Transparenz solltest du auch im Produktdesign spiegeln. citeturn17view0turn17view2turn17view3turn13view0

Schließlich ist die **ESCO-Perspektive noch klar als “solide, aber minimal”** erkennbar. Das ist kein Makel, sondern eine bewusste Grenze. Offiziell bietet ESCO heute Download-Pakete in RDF, TTL, ODS, CSV, XML und JSON-LD an, plus Web-Service-API und Local API. Solange dein Repo diesen offiziellen Bulk-Pfad noch nicht versioniert ingestiert, bleibt ESCO in der App funktional, aber nicht so robust und tief integrierbar wie langfristig möglich. Das betrifft besonders Alt-Labels, Hidden Labels, Mehrsprachigkeit, Sprachfallbacks, versionssichere Diffs, Relationship-Qualität und spätere Qualitätsmetriken für Skill-Kohärenz. citeturn21view1turn22view0turn21view0

## Wie RAG und ESCO tragfähig weiterentwickelt werden sollten

Für RAG ist die Grundrichtung richtig: OpenAI positioniert Retrieval auf Basis von Vector Stores; Dateien werden dabei automatisch gechunkt, eingebettet und indexiert. Gleichzeitig bietet die aktuelle Retrieval-/File-Search-Dokumentation mehr Steuerungsmöglichkeiten, als eine minimale Suche typischerweise ausnutzt: Metadatenfilter, Ranking-Optionen, Score-Schwellen, Hybrid-Gewichte, `max_num_results` und — besonders wichtig für nachvollziehbare Ergebnisse — das Einschließen der tatsächlichen Suchresultate in die Response. Genau dort würde ich die App ausbauen. citeturn13view1turn13view0turn17view0turn17view1turn17view2turn17view3

Mein Architekturvorschlag ist **kein radikaler Austausch**, sondern ein zweigleisiges Modell. Für schnelle, UI-nahe Suggestion-Surfaces — etwa Skill-, Task- oder Occupation-Vorschläge — kann eine direkte, schlanke Retrieval-Schicht weiter sinnvoll bleiben. Für Antworten, bei denen du **sichtbare Belegstellen, Explanation und Auditierbarkeit** brauchst, solltest du zusätzlich einen path über `responses.create(... tools=[{"type": "file_search", ...}])` vorsehen, inklusive `include=["file_search_call.results"]`. Damit bekommst du nicht nur generierte Antworttexte, sondern auch die zugrunde liegenden Retrieval-Ergebnisse sauber zurück. Das ist besonders wertvoll für Summary, Explainability, “Warum empfehlen wir diesen Skill?” und später für Export-/Auditberichte. citeturn17view0turn17view2turn17view3

Inhaltlich würde ich dein ESCO-RAG künftig **stärker typisieren**. Heute solltest du nicht nur nach `purpose`, `collection`, `language` und `skill_type` denken, sondern zusätzlich Attribute wie `concept_type`, `relation_type`, `occupation_group`, `isco_code`, `version`, `source_file`, `label_variant`, `is_obsolete`, `language_fallback_used` und `lane` sauber pflegen. OpenAI empfiehlt Metadatenfilter explizit, und genau diese Typisierung macht aus einer “funktionierenden Suche” eine produktionsreife Retrieval-Schicht. Der Effekt ist simpel: weniger breit gestreute Treffer, weniger semantische Streuung, mehr gezielte Ergebnisse pro App-Kontext. citeturn12view3turn17view3

Für ESCO selbst empfehle ich eine **versionierte Offline-Build-Pipeline**. Das Repo dokumentiert aktuell v1.2.0 als Default im ESCO-Kontext, während das ESCO-Portal bereits v1.2.1 als aktuelle Version führt. Ich würde deshalb den offiziellen Bulk-Download nicht direkt in die Runtime ziehen, sondern in drei Schichten trennen: `raw/`, `normalized/`, `indexed/`. Das erlaubt reproduzierbare Builds, Checksummen, Sprach-/Versionsvergleiche, rückrollbare Indizes und später differenzierte Regressionstests. Weil ESCO die Daten offiziell in mehreren Formaten bereitstellt und kostenlos verfügbar macht, lohnt sich dieser Build-Weg klar. citeturn2view0turn21view1turn22view0

## Codex-optimierte Task-Pakete

### Evidenz- und Konfliktlayer

**Ziel:** Eine kanonische Fakt-Schicht einführen, die jede Information als `confirmed`, `inferred`, `assumed`, `conflicted` oder `missing` klassifiziert.  
**Warum jetzt:** Das erhöht Präzision und Benutzerfreundlichkeit gleichzeitig, weil offene Punkte nicht mehr nur “nicht beantwortet”, sondern fachlich eingeordnet sind.  
**Dateien:** `constants.py`, `intake_facts.py`, `question_progress.py`, `wizard_pages/jobad_intake.py`, `wizard_pages/02_company.py`, `wizard_pages/08_summary.py`, optional `schemas.py`.  
**Greppable IDs/Keys:** neue Statusfamilie unter `SSKey`, z. B. `FACT_RESOLUTION_STATE`, `FACT_CONFLICTS`, `NEXT_BEST_QUESTIONS`; Anschluss an bestehende Fact-/Evidence-Strukturen.  
**Definition of done:** Jeder im Brief relevante Fakt hat Status, Quelle, Confidence, letzten Bestätigungszeitpunkt und optional Konfliktpartner; Summary zeigt nicht nur Werte, sondern Auflösungszustand; offene High-Impact-Punkte werden als “nächste beste Klärung” surfaced.  
**Pragmatischer Nutzen:** Das ist die fachliche Grundlage für alles Weitere — ohne diese Schicht bleibt Dynamik im Frageprozess immer nur halb so gut.

**Codex-Prompt-Form:**

```text
Goal: Introduce a canonical fact resolution layer with statuses confirmed/inferred/assumed/conflicted/missing.
Context: constants.py, intake_facts.py, question_progress.py, wizard_pages/jobad_intake.py, wizard_pages/02_company.py, wizard_pages/08_summary.py.
Constraints: use canonical SSKey/constants only; preserve existing manual-overrides-win behavior; no new dependencies; keep exports backward-compatible unless explicitly versioned.
Done when: each brief-relevant fact carries resolution metadata; summary shows unresolved/conflicted facts; next-best-question recommendations use this metadata.
Verification:
python -m pytest -q tests/test_fact_contract.py tests/test_intake_facts.py tests/test_question_progress.py tests/test_summary_*.py
```

### Informationsgewinn statt bloßer Frage-Reihenfolge

**Ziel:** Den Frageplan zusätzlich nach erwartetem Informationsgewinn ranken.  
**Warum jetzt:** Der Wizard ist schon strukturiert; der nächste Sprung ist, dass nicht nur “was passt in diesen Step?” entscheidet, sondern “welche Antwort reduziert aktuell das meiste fachliche Risiko?”.  
**Dateien:** `question_plan_compiler.py`, `question_limits.py`, `question_dependencies.py`, `question_packs/registry.py`, `schemas.py`, ggf. `step_status.py`.  
**Greppable IDs/Keys:** `priority`, `group_key`, `depends_on`, `follow_up_prompts`, neue Felder wie `impact_targets`, `evidence_targets`, `acquisition_cost`, `info_gain_score`.  
**Definition of done:** Offene Fragen werden pro Step nicht nur gefiltert, sondern gewichtet; UI-Modus beeinflusst die Tiefenschwelle, nicht die fachliche Priorität; jede Top-Frage kann optional mit “Warum jetzt?” erklärt werden.  
**Pragmatischer Nutzen:** Weniger gefühlte Formularlast, höhere Relevanz der verbleibenden Fragen, schnellere Brief-Reife.

**Codex-Prompt-Form:**

```text
Goal: Add information-gain ranking to the dynamic question pipeline.
Context: question_plan_compiler.py, question_limits.py, question_dependencies.py, question_packs/registry.py, schemas.py.
Constraints: preserve current visible step contract and UI modes quick/standard/expert; no step-key changes; reuse canonical question metadata rather than ad-hoc heuristics.
Done when: missing/conflicted high-impact questions rise to the top; low-value detail questions are deferred; existing tests still pass with targeted additions.
Verification:
python -m pytest -q tests/test_question_pack_compiler.py tests/test_question_limits.py tests/test_question_progress.py tests/test_step_status_payload.py
```

### Hypothesenbasiertes Intake statt reinem Review-Block

**Ziel:** Phase B nicht mehr nur als Review-Fläche, sondern als Hypothesenbestätigung gestalten.  
**Warum jetzt:** Die Drei-Phasen-Startstruktur ist bereits stark. Der UX-Gewinn entsteht jetzt durch feinere Interaktion innerhalb dieser Phasen.  
**Dateien:** `wizard_pages/jobad_intake.py`, `job_extract_review_helpers.py`, `ui_components.py`, ggf. `parsing.py`.  
**Greppable IDs/Keys:** bestehende Start-Phasen, Source-Handling-Keys, `JOB_EXTRACT`, `QUESTION_PLAN_BASE`, `SOURCE_TEXT`, `SOURCE_FILE_META`.  
**Definition of done:** Extrahierte Werte werden in drei Gruppen angezeigt: hochsicher übernehmen, kurz bestätigen, aktiv klären. Änderungen werden gesammelt in einer Form abgegeben, nicht bei jedem Widget-Rerun einzeln.  
**Technischer Hebel:** Streamlit-Forms bündeln Widget-Werte und schicken sie erst beim Submit an den Server; genau das reduziert Rerun-Stress im Startschritt. Falls du besonders teure Teilbereiche isolieren willst, kannst du zusätzlich `st.fragment` für einzelne Panels einsetzen, weil Interaktionen dort nur das Fragment statt der ganzen App rerunnen. citeturn18view0turn19view0

**Codex-Prompt-Form:**

```text
Goal: Turn Start Phase B into a hypothesis-confirmation surface with batched submits.
Context: wizard_pages/jobad_intake.py, job_extract_review_helpers.py, ui_components.py.
Constraints: keep three-phase intake; preserve active-source behavior and PII-defaults; no routing changes.
Done when: extracted facts are grouped by certainty; user can accept/edit/skip in one batched submit; unnecessary full-page reruns are reduced.
Verification:
python -m pytest -q tests/test_jobad_intake_upload_extract.py tests/test_jobad_intake_identified_info_block.py tests/test_jobad_intake_cache_usage.py
```

### RAG mit sichtbarer Evidenz und besserem Ranking

**Ziel:** Die bestehende minimale RAG-Schicht auf produktionsreife Retrieval-Qualität heben.  
**Warum jetzt:** OpenAI bietet inzwischen deutlich mehr Retrieval-Steuerung als nur eine einfache Suche: `max_num_results`, tatsächliche Search-Results in der Response, Metadatenfilter sowie Ranking-/Hybridsteuerung. Das passt sehr gut zu einer Recruiting-App, in der Belegbarkeit wichtig ist. citeturn17view0turn17view1turn17view2turn17view3turn13view0  
**Dateien:** `esco_rag.py`, `llm_client.py`, `settings_openai.py`, `scripts/prepare_esco_for_vectorstore.py`, `tests/test_esco_rag.py`, angrenzend `wizard_pages/04_role_tasks.py` und `wizard_pages/05_skills.py`.  
**Greppable IDs/Keys:** `ESCO_VECTOR_STORE_ID`, `ESCO_RAG_ENABLED`, `ESCO_RAG_MAX_RESULTS`, `purpose`, `collection`, `language`, `skill_type`.  
**Definition of done:**  
- Retrieval nutzt strengere Dateiattribute und versionierte Metadaten.  
- Es gibt Multi-Query-Retrieval je Use Case, z. B. Titel-only, Titel+Tasks, Titel+Skills, Alt-Labels.  
- Für explainable Flows werden Suchergebnisse explizit mit eingebunden.  
- Treffer werden UI-seitig mit Herkunft, Datei/Quelle und kurzer Evidenz angezeigt.  
- Der Fallback-Pfad auf Offline-Index/ESCO-API bleibt erhalten.

**Meine klare Empfehlung:**  
Nutze **zwei Retrieval-Modi**:
- **Fast Path:** direkte Suche für UI-nahe Vorschlagsflächen.  
- **Evidence Path:** `responses.create(... tools=[{"type":"file_search", ...}])` für Summary, Audit, Why-this-suggestion und Export-nahe Logik, inklusive `include=["file_search_call.results"]`. citeturn17view0turn17view2

**Codex-Prompt-Form:**

```text
Goal: Upgrade ESCO retrieval from minimal vector-store search to a dual-mode retrieval layer with explicit evidence output.
Context: esco_rag.py, llm_client.py, settings_openai.py, scripts/prepare_esco_for_vectorstore.py, wizard_pages/04_role_tasks.py, wizard_pages/05_skills.py.
Constraints: preserve degraded behavior when RAG is disabled/unavailable; keep existing env-var contract; no secret logging; minimal diff first.
Done when: retrieval supports richer metadata filtering, multi-query retrieval, explicit result inclusion for evidence-heavy flows, and stable fallback behavior.
Verification:
python -m pytest -q tests/test_esco_rag.py tests/test_skills_occupation_suggestions.py tests/test_additional_task_generators.py
```

### Offizielle ESCO-Ingestion als versionierter Offline-Build

**Ziel:** Den noch offenen “future scope”-Teil sauber vorbauen, ohne die Runtime zu überfrachten.  
**Warum jetzt:** ESCO stellt den Datensatz offiziell in vielen Formaten bereit, inklusive CSV, JSON-LD, XML, RDF und TTL. Außerdem gibt es Web-Service-API und Local API. Diese offizielle Breite lohnt sich erst dann wirklich, wenn dein Repo einen reproduzierbaren Build- und Indexpfad bekommt. citeturn21view1turn22view0  
**Dateien:** neuer Build-Pfad unter `scripts/`, plus `esco_offline_index.py`, `esco_semantics.py`, `esco_client.py`, `data/esco_index/`, Doku in `README.md`.  
**Praktischer Zuschnitt:**  
- `raw/<version>/<language>/<format>/...`  
- `normalized/<version>/...`  
- `indexed/<version>/esco_index.sqlite + manifest.json`  
- Manifest mit Version, Quelle, Dateien, Sprachen, Hashes, Buildzeit  
- Später optional Diffs zwischen `v1.2.0` und `v1.2.1`

**Warum das wichtig ist:** Das Repo dokumentiert aktuell weiterhin einen Default-Pfad auf ältere Standardversionen, während ESCO bereits neuere Versionen ausweist. Eine saubere Ingestion entkoppelt Runtime-Stabilität von ESCO-Release-Wechseln. citeturn2view0turn22view0

**Codex-Prompt-Form:**

```text
Goal: Build a versioned offline ESCO ingestion pipeline that can consume official bulk downloads and produce normalized + indexed artifacts.
Context: scripts/build_esco_index.py, esco_offline_index.py, esco_client.py, esco_semantics.py, README.md.
Constraints: keep runtime lookup lane stable; build pipeline must stay offline/preprocessing-only; do not force full bulk ingestion into request path.
Done when: official ESCO downloads can be normalized into a reproducible local index with manifest metadata and versioned storage layout.
Verification:
python -m pytest -q tests/test_esco_offline_contract.py tests/test_esco_client.py tests/test_esco_metadata.py
python scripts/esco_smoke_test.py --mode all --ci-dry-run-if-unavailable --json-only
```

### Performance, Reruns und Beobachtbarkeit

**Ziel:** Den Wizard spürbar flüssiger machen und gleichzeitig messbar verbessern.  
**Warum jetzt:** Streamlit kann mit Session State sehr gut mehrstufige Apps tragen, aber bei vielen Widgets, Compare/Adopt-Flächen und AI-Aktionen leidet sonst schnell die Interaktionsruhe. `st.cache_data` eignet sich für datenartige Ergebnisse und gibt pro Session Kopien zurück; `st.cache_resource` ist für globale, singleton-artige Ressourcen gedacht und muss thread-sicher sein. Daraus folgt für dein Repo: OpenAI-Client und vergleichbare Ressourcen bleiben bei `cache_resource`, datenartige Transformations-, Retrieval-Postprocessing- und Parser-Pfade sollten eher gezielt auf `cache_data` mit TTL gehen. citeturn19view2turn19view3turn19view4  
**Dateien:** `homepage_research.py`, Retrieval-/Postprocessing-nahe Helfer, `wizard_pages/*`, `usage_events.py`.  
**Definition of done:**  
- Teure Sidepanels und Vorschlags-Panels laufen fragmentiert oder formulargebündelt.  
- Website-/ESCO-/RAG-Laufzeiten werden anonymisiert gemessen.  
- Cache-Invalidierung folgt fachlicher Logik statt nur Session-Lebensdauer.  
- Summary zeigt nicht nur “fertig/nicht fertig”, sondern auch “welcher Pfad war teuer/langsam/unsicher”.

**Codex-Prompt-Form:**

```text
Goal: Reduce unnecessary full-app reruns and add non-sensitive timing observability for expensive enrichment paths.
Context: homepage_research.py, wizard_pages/jobad_intake.py, wizard_pages/04_role_tasks.py, wizard_pages/05_skills.py, usage_events.py.
Constraints: no sensitive payload logging; keep current app behavior intact; use Streamlit-native execution-flow primitives only.
Done when: key enrichment panels rerun independently or in batched submits; timing metrics exist for extraction, ESCO, homepage, and RAG flows.
Verification:
python -m pytest -q tests/test_company_homepage_research.py tests/test_usage_events.py tests/test_ui_mode_flow.py
```

## Priorisierte Umsetzungsempfehlung

Wenn du den Informationsgewinnungsprozess **benutzerfreundlicher, dynamischer, präziser und genauer** bauen willst, würde ich die Reihenfolge so setzen:

Zuerst den **Evidenz-/Konfliktlayer**, dann die **Info-Gain-Rangfolge für Fragen**, danach die **Start-UX als Hypothesenbestätigung**, anschließend die **RAG-Aufwertung**, und erst danach die **vollwertige ESCO-Bulk-Ingestion**. Der Grund ist einfach: Die ersten drei Punkte verbessern direkt die User Experience und die Qualität der Entscheidungen innerhalb des bestehenden Flows. Die RAG-Verbesserung erhöht dann Erklärungstiefe und Präzision. Die offizielle ESCO-Ingestion ist strategisch wichtig, aber sie entfaltet den größten Wert erst dann, wenn die Produktlogik klar weiß, **wie sie mit bestätigten, umstrittenen und fehlenden Informationen umgehen soll**. citeturn1view0turn2view0turn13view0turn21view1

Wenn du nur **eine** Sache als nächstes umsetzt, nimm nicht zuerst “mehr ESCO” und auch nicht “mehr LLM”. Nimm den **kanonischen Unsicherheits- und Konfliktstatus pro Fakt**. Das ist der Punkt, der Start, Company, Skills, Summary, Exporte und später auch Evaluierung logisch zusammenzieht. Danach werden fast alle weiteren Verbesserungen leichter, kleiner und sauberer als PRs. citeturn1view1turn2view0

## Offene Fragen und Grenzen

Die geteilte ChatGPT-URL ließ sich in der aktuellen Umgebung nicht inhaltlich auslesen, weil die Seite nur eine Login-/Shell-Ansicht zurückgab. Ich konnte den früheren Diskussionsverlauf deshalb nicht als Primärquelle auswerten und habe mich für diese Analyse auf den aktuellen Repo-Stand, die Repo-Dokumentation, die ESCO-Originalquellen sowie die aktuellen OpenAI- und Streamlit-Dokumente gestützt. citeturn23view0

Ein zweiter Punkt: Die Repo-Dokumentation und der sichtbare Code-Stand zeigen einen bereits guten, aber bewusst pragmatischen Mittelzustand. Manche der hier empfohlenen Schritte — vor allem Bulk-ESCO-Ingestion, Retrieval-Evaluierung und feinere Frage-Rankings — sind keine “Quick Fixes”, sondern produktstrategische Ausbaustufen. Sie lohnen sich dann besonders, wenn du die App nicht nur intern nutzt, sondern reproduzierbar betreiben, erklären und später vielleicht domänenspezifisch erweitern willst. Das ist aus meiner Sicht bei deinem App-Zuschnitt aber genau die richtige Richtung. citeturn1view0turn21view1turn13view0