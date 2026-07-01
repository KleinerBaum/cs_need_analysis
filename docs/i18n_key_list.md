# i18n Key List

Snapshot date: `2026-06-23`.

This document is an inventory of the current translation surface. It does not introduce new keys or change runtime behavior.

## Scope And Sources

- `tr("dotted.key")` resolves entries from `locales/de.json` and `locales/en.json`.
- `tr_safe("dotted.key")` uses the same Locale lookup with runtime-safe placeholder formatting.
- Short Wizard UX copy is resolved by the inline runtime contract in `ux_copy_contract.py`.
- `ux_copy.steps.*` Locale keys are retained as inventory/parity entries for gradual migration work.
- `t("German source copy")` resolves German-source UI copy through `_TRANSLATIONS_EN` in `i18n.py`.
- `_PHRASE_TRANSLATIONS_EN` in `i18n.py` is a fallback replacement layer for partial strings and generated captions.
- Public pages use dynamic prefixes such as `public_pages.competencies.*`; those keys are valid Locale keys even when a static `tr("...")` search cannot see the full dotted key.

## Inventory Summary

| Source | Count | Contract |
|---|---:|---|
| `locales/de.json` leaf keys | 352 | German source Locale values, including retained `ux_copy` parity keys |
| `locales/en.json` leaf keys | 352 | English Locale values; key shape must match DE |
| `_TRANSLATIONS_EN` | 383 | German-source copy translated by `t()` |
| `_PHRASE_TRANSLATIONS_EN` | 80 | fallback phrase replacements inside `t()` |
| High-confidence unkeyed UI-copy candidates | 716 | explicit migration backlog and allowlist baseline for the changed-line raw UI guard |

## Locale Leaf Keys

All Locale leaf keys below exist in both `locales/de.json` and `locales/en.json`.

| Category | Key | Params | DE | EN |
|---|---|---|---|---|
| trust_grammar | `trust_grammar.states.detected.label` | - | Erkannt | Detected |
| trust_grammar | `trust_grammar.states.detected.action` | - | prüfen | review |
| trust_grammar | `trust_grammar.states.suggested.label` | - | Vorschlag | Suggested |
| trust_grammar | `trust_grammar.states.suggested.action` | - | auswählen | select |
| trust_grammar | `trust_grammar.states.confirmed.label` | - | Bestätigt | Confirmed |
| trust_grammar | `trust_grammar.states.confirmed.action` | - | nutzen | use |
| trust_grammar | `trust_grammar.states.assumed.label` | - | Annahme | Assumed |
| trust_grammar | `trust_grammar.states.assumed.action` | - | prüfen | review |
| trust_grammar | `trust_grammar.states.conflicted.label` | - | Konflikt | Conflict |
| trust_grammar | `trust_grammar.states.conflicted.action` | - | klären | resolve |
| trust_grammar | `trust_grammar.states.missing.label` | - | Fehlt | Missing |
| trust_grammar | `trust_grammar.states.missing.action` | - | ergänzen | add |
| trust_grammar | `trust_grammar.states.fallback.label` | - | Fallback | Fallback |
| trust_grammar | `trust_grammar.states.fallback.action` | - | prüfen | review |
| trust_grammar | `trust_grammar.states.evidence.label` | - | Beleg | Evidence |
| trust_grammar | `trust_grammar.states.evidence.action` | - | ansehen | view |
| trust_grammar | `trust_grammar.hints.detected` | - | Automatisch erkannt; bitte bei Bedarf prüfen. | Detected automatically; review if needed. |
| trust_grammar | `trust_grammar.hints.suggested` | - | Vorschlag aus Kontext oder externer Quelle; erst nach Auswahl verbindlich. | Suggested from context or an external source; binding only after selection. |
| trust_grammar | `trust_grammar.hints.confirmed` | - | Bestätigt und für die nächsten Schritte nutzbar. | Confirmed and usable for next steps. |
| trust_grammar | `trust_grammar.hints.assumed` | - | Annahme; vor Export prüfen. | Assumption; review before export. |
| trust_grammar | `trust_grammar.hints.conflicted` | - | Abweichende Quellen; bitte klären. | Sources differ; resolve before relying on it. |
| trust_grammar | `trust_grammar.hints.missing` | - | Noch nicht vorhanden. | Not available yet. |
| trust_grammar | `trust_grammar.hints.fallback` | - | Live-Abfrage nicht belastbar; Offline-Index wurde genutzt. | Live lookup was not reliable; the offline index was used. |
| trust_grammar | `trust_grammar.hints.evidence` | - | Beleg ist verfügbar. | Evidence is available. |
| trust_grammar | `trust_grammar.details_title` | - | Trust-Details | Trust details |
| trust_grammar | `trust_grammar.evidence_trigger` | - | Quelle & Beleg | Source & evidence |
| trust_grammar | `trust_grammar.no_details` | - | Keine weiteren Trust-Details verfügbar. | No further trust details available. |
| trust_grammar | `trust_grammar.unknown` | - | unbekannt | unknown |
| trust_grammar | `trust_grammar.metadata.attempted_source` | - | Versuchte Quelle | Attempted source |
| trust_grammar | `trust_grammar.metadata.final_source` | - | Genutzte Quelle | Used source |
| trust_grammar | `trust_grammar.metadata.fallback_reason` | - | Fallback-Grund | Fallback reason |
| trust_grammar | `trust_grammar.metadata.endpoint` | - | ESCO-Endpunkt | ESCO endpoint |
| trust_grammar | `trust_grammar.metadata.version` | - | Version | Version |
| trust_grammar | `trust_grammar.metadata.data_source_mode` | - | Konfigurierter Modus | Configured mode |
| trust_grammar | `trust_grammar.sources.live_api` | - | Live-API | Live API |
| trust_grammar | `trust_grammar.sources.offline_index` | - | Offline-Index | Offline index |
| trust_grammar | `trust_grammar.sources.hybrid` | - | Hybrid | Hybrid |
| trust_grammar | `trust_grammar.sources.esco` | - | ESCO | ESCO |
| trust_grammar | `trust_grammar.sources.jobspec` | - | Jobspec | Jobspec |
| trust_grammar | `trust_grammar.sources.homepage` | - | Website | Website |
| trust_grammar | `trust_grammar.sources.llm` | - | AI | AI |
| trust_grammar | `trust_grammar.sources.manual` | - | Eingabe | Input |
| trust_grammar | `trust_grammar.esco_lookup_live_first_hint` | - | ESCO nutzt die Live-API zuerst; der Offline-Index dient als Fallback. | ESCO uses the live API first; the offline index is available as fallback. |
| trust_grammar | `trust_grammar.esco_lookup_fallback_hint` | - | Live-Abfrage fehlgeschlagen; Ergebnis stammt aus dem Offline-Index. | Live lookup failed; the result comes from the offline index. |
| trust_grammar | `trust_grammar.esco_lookup_offline_hint` | - | ESCO nutzt den Offline-Index gemäß Konfiguration. | ESCO uses the offline index according to configuration. |
| trust_grammar | `trust_grammar.esco_lookup_missing_hint` | - | Noch keine ESCO-Abfrage in dieser Sitzung. | No ESCO lookup has run in this session yet. |
| ux_copy | `ux_copy.steps.landing.headline` | - | Vom Rollenbedarf zum Recruiting-Briefing. | Turn role need into a recruiting brief. |
| ux_copy | `ux_copy.steps.landing.subheadline` | - | Für Recruiting, HR und Hiring Teams, die vor Search, Matching, Interview und Angebot eine gemeinsame Entscheidungsbasis brauchen. Laden Sie eine Jobspec hoch oder fügen Sie Rohtext ein; die App zeigt zuerst, was belastbar ist und welche Lücken den Prozess bremsen. | For recruiting, HR, and hiring teams that need a shared decision basis before search, matching, interviews, and offers. Upload a jobspec or paste raw text; the app first shows what is reliable and which gaps slow the process down. |
| ux_copy | `ux_copy.steps.landing.value_line` | - | Ergebnis: ein Briefing-Cockpit mit Rollenprofil, Prioritäten, offenen Fragen, ESCO-Anker und vorbereiteten Recruiting-Unterlagen. | Result: a recruiting brief cockpit with a role profile, priorities, open questions, ESCO anchor, and prepared recruiting outputs. |
| ux_copy | `ux_copy.steps.landing.primary_cta` | - | Quelle in Briefing verwandeln | Turn source into brief |
| ux_copy | `ux_copy.steps.landing.secondary_cta` | - | Beispiel ansehen | See example |
| ux_copy | `ux_copy.steps.landing.empty_state` | - | Noch keine Quelle geladen. | No source loaded yet. |
| ux_copy | `ux_copy.steps.landing.readiness` | - | Bereit fürs Recruiting-Briefing | Ready for recruiting brief |
| ux_copy | `ux_copy.steps.company.headline` | company_name, role_title | {company_name} als Arbeitgeber für {role_title} einordnen | Position {company_name} as the employer for {role_title} |
| ux_copy | `ux_copy.steps.company.subheadline` | - | Klären Sie Unternehmenskontext, Teamstruktur und Positionierung, damit Recruiting und Kandidat:innen verstehen, warum diese Rolle relevant ist. | Clarify company context, team structure, and positioning so recruiting and candidates understand why this role matters. |
| ux_copy | `ux_copy.steps.company.value_line` | - | Hilft zu erklären, warum diese Rolle existiert. | Helps explain why this role exists. |
| ux_copy | `ux_copy.steps.company.primary_cta` | - | Unternehmenskontext speichern | Save company context |
| ux_copy | `ux_copy.steps.company.secondary_cta` | - | Website-Funde prüfen | Review website findings |
| ux_copy | `ux_copy.steps.company.empty_state` | - | Noch kein Unternehmenskontext vorhanden. | No company context yet. |
| ux_copy | `ux_copy.steps.company.readiness` | - | Arbeitgeberbild geschärft | Employer story sharpened |
| ux_copy | `ux_copy.steps.role_tasks.headline` | role_title | Klären, wofür {role_title} wirklich verantwortlich ist | Clarify what {role_title} is truly responsible for |
| ux_copy | `ux_copy.steps.role_tasks.subheadline` | - | Priorisieren Sie Aufgaben, Ergebnisse und Erfolgskriterien, damit Recruiting nicht nur Tätigkeiten sucht, sondern die richtige Wirkung. | Prioritize tasks, outcomes, and success criteria so recruiting looks for the right impact, not just a list of activities. |
| ux_copy | `ux_copy.steps.role_tasks.value_line` | - | Verhindert, dass Recruiting nur nach Titeln sucht. | Prevents recruiting from searching by title alone. |
| ux_copy | `ux_copy.steps.role_tasks.primary_cta` | - | Aufgaben speichern | Save role scope |
| ux_copy | `ux_copy.steps.role_tasks.secondary_cta` | - | Erfolgskriterien prüfen | Review success criteria |
| ux_copy | `ux_copy.steps.role_tasks.empty_state` | - | Noch keine Rollenaufgaben bestätigt. | No role tasks confirmed yet. |
| ux_copy | `ux_copy.steps.role_tasks.readiness` | - | Rollenwirkung geklärt | Role impact clarified |
| ux_copy | `ux_copy.steps.skills.headline` | - | Must-haves von Nice-to-haves trennen | Separate must-haves from nice-to-haves |
| ux_copy | `ux_copy.steps.skills.subheadline` | - | Erstellen Sie eine prüfbare Skill-Liste für Matching, Interviewfragen, Gehaltsprognose und die finale Stellenanzeige. | Build a testable skill list for matching, interview questions, salary forecasting, and the final job ad. |
| ux_copy | `ux_copy.steps.skills.value_line` | - | Trennt echte Anforderungen von Wunschlisten. | Separates real requirements from wish lists. |
| ux_copy | `ux_copy.steps.skills.primary_cta` | - | Skills speichern | Save skills |
| ux_copy | `ux_copy.steps.skills.secondary_cta` | - | Offene Begriffe prüfen | Review open terms |
| ux_copy | `ux_copy.steps.skills.empty_state` | - | Noch keine Skills priorisiert. | No skills prioritized yet. |
| ux_copy | `ux_copy.steps.skills.readiness` | - | Skill-Profil prüfbar | Skill profile testable |
| ux_copy | `ux_copy.steps.benefits.headline` | role_title | Das Angebot für {role_title} klar und überzeugend formulieren | Describe the offer for {role_title} clearly and convincingly |
| ux_copy | `ux_copy.steps.benefits.subheadline` | - | Erfassen Sie Gehalt, Arbeitsmodell, Benefits und Startbedingungen, damit Kandidat:innen früh verstehen, warum sich die Rolle lohnt. | Capture salary, work model, benefits, and start conditions so candidates understand early why the role is worth considering. |
| ux_copy | `ux_copy.steps.benefits.value_line` | - | Macht das Angebot vergleichbar und verhandelbar. | Makes the offer comparable and negotiable. |
| ux_copy | `ux_copy.steps.benefits.primary_cta` | - | Angebot speichern | Save offer details |
| ux_copy | `ux_copy.steps.benefits.secondary_cta` | - | Rahmenbedingungen prüfen | Review conditions |
| ux_copy | `ux_copy.steps.benefits.empty_state` | - | Noch keine Angebotsdetails vorhanden. | No offer details yet. |
| ux_copy | `ux_copy.steps.benefits.readiness` | - | Angebot formulierbar | Offer ready to describe |
| ux_copy | `ux_copy.steps.interview.headline` | role_title | Einen fairen Interviewprozess für {role_title} planen | Plan a fair interview process for {role_title} |
| ux_copy | `ux_copy.steps.interview.subheadline` | - | Definieren Sie Interviewstufen, Verantwortlichkeiten, Scorecards und Nachweise, damit jede Entscheidung nachvollziehbar bleibt. | Define interview stages, responsibilities, scorecards, and evidence so every decision stays transparent. |
| ux_copy | `ux_copy.steps.interview.value_line` | - | Sorgt für faire, konsistente Bewertung. | Supports fair and consistent evaluation. |
| ux_copy | `ux_copy.steps.interview.primary_cta` | - | Interviewprozess speichern | Save interview plan |
| ux_copy | `ux_copy.steps.interview.secondary_cta` | - | Bewertungskriterien prüfen | Review scorecards |
| ux_copy | `ux_copy.steps.interview.empty_state` | - | Noch kein Interviewprozess definiert. | No interview process defined yet. |
| ux_copy | `ux_copy.steps.interview.readiness` | - | Bewertung strukturiert | Evaluation structured |
| ux_copy | `ux_copy.steps.summary.headline.default` | readiness_score, role_title | Das Recruiting-Briefing für {role_title} ist zu {readiness_score}% bereit | The recruiting brief for {role_title} is {readiness_score}% ready |
| ux_copy | `ux_copy.steps.summary.headline.gap` | critical_gaps_count | Noch {critical_gaps_count} kritische Punkte offen | {critical_gaps_count} critical points still open |
| ux_copy | `ux_copy.steps.summary.headline.ready` | - | Bereit für Recruiting, Interviews und Active Sourcing | Ready for recruiting, interviews, and active sourcing |
| ux_copy | `ux_copy.steps.summary.subheadline.default` | - | Prüfen Sie offene Lücken, übernehmen Sie finale Anpassungen und erstellen Sie die passenden Recruiting-Unterlagen für Recruiting, HR und Active Sourcing. | Review remaining gaps, apply final adjustments, and generate the right recruiting outputs for recruiting, HR, and active sourcing. |
| ux_copy | `ux_copy.steps.summary.subheadline.gap` | - | Klären Sie diese Angaben, bevor Sie Stellenanzeige, Interviewleitfaden oder Suchstrings exportieren. | Clarify these items before exporting a job ad, interview guide, or search strings. |
| ux_copy | `ux_copy.steps.summary.subheadline.ready` | - | Alle wichtigen Fakten sind geprüft. Erstellen Sie jetzt Stellenanzeige, HR-Sheet und Suchstrings. | All important facts are checked. Generate the job ad, HR sheet, and search strings now. |
| ux_copy | `ux_copy.steps.summary.value_line` | - | Erstellt direkt nutzbare Unterlagen für HR, Recruiting und Sourcing. | Creates directly usable material for HR, recruiting, and sourcing. |
| ux_copy | `ux_copy.steps.summary.primary_cta` | - | Recruiting-Unterlagen erstellen | Generate recruiting outputs |
| ux_copy | `ux_copy.steps.summary.secondary_cta` | - | Lücken prüfen | Review gaps |
| ux_copy | `ux_copy.steps.summary.empty_state` | - | Noch keine Analyse für die Zusammenfassung vorhanden. | No analysis available for the summary yet. |
| ux_copy | `ux_copy.steps.summary.readiness.default` | readiness_score | {readiness_score}% bereit | {readiness_score}% ready |
| ux_copy | `ux_copy.steps.summary.readiness.gap` | critical_gaps_count | {critical_gaps_count} kritische Lücken | {critical_gaps_count} critical gaps |
| ux_copy | `ux_copy.steps.summary.readiness.ready` | - | Bereit | Ready |
| common.language | `common.language` | - | Sprache | Language |
| common.german | `common.german` | - | Deutsch | German |
| common.english | `common.english` | - | Englisch | English |
| common.last_updated | `common.last_updated` | date | Stand: {date} | Last updated: {date} |
| common.back_to_wizard | `common.back_to_wizard` | - | Zurück zum Wizard | Back to wizard |
| common.open_full_view | `common.open_full_view` | - | Vollansicht öffnen | Open full view |
| common.country_germany | `common.country_germany` | - | Deutschland | Germany |
| common.not_published | `common.not_published` | - | Nicht veröffentlicht | Not published |
| common.not_configured | `common.not_configured` | - | Nicht konfiguriert | Not configured |
| iceberg.aria_label | `iceberg.aria_label` | - | Eisberg-Modell für klassisches und KI-gestütztes Recruiting-Briefing | Iceberg model for classic and AI-supported recruiting briefs |
| iceberg.surface_label | `iceberg.surface_label` | - | oberhalb: sichtbar in Jobspec, Stellenanzeige und erstem Briefing | above: visible in jobspec, job ad, and first briefing |
| iceberg.deep_label | `iceberg.deep_label` | - | unterhalb: entscheidend für Search, Matching, Interview und Zusage | below: essential for search, matching, interview, and offer acceptance |
| public_pages.legal_missing_inputs_title | `public_pages.legal_missing_inputs_title` | - | ⚠️ **Erforderliche Fachangaben fehlen** | ⚠️ **Required subject-matter details are missing** |
| public_pages.legal_review_notice | `public_pages.legal_review_notice` | - | Diese Seite ist erst nach fachlicher und rechtlicher Prüfung verbindlich. | This page is binding only after subject-matter and legal review. |
| public_pages.competencies | `public_pages.competencies.title` | - | Unsere Kompetenzen | Our competencies |
| public_pages.competencies | `public_pages.competencies.hero.eyebrow` | - | Recruiting-Briefing · ESCO · KI · Struktur | Recruiting brief · ESCO · AI · structure |
| public_pages.competencies | `public_pages.competencies.hero.lead` | - | Wir professionalisieren den ersten Schritt jedes Recruiting-Prozesses: das Recruiting-Briefing. Aus unstrukturierten Eingangsinformationen entsteht ein klarer, belastbarer und weiterverwendbarer Datensatz, der Suche, Auswahl und interne Abstimmung von Beginn an verbessert. | We professionalize the first step of every recruiting process: the recruiting brief. Unstructured input is turned into a clear, robust, reusable data set that improves search, selection, and internal alignment from the start. |
| public_pages.competencies | `public_pages.competencies.meta` | - | Fokus: strukturiertes Recruiting-Briefing, semantische Qualität, kontrollierte KI-Nutzung, Sicherheit und Weiterverarbeitung | Focus: structured recruiting briefs, semantic quality, controlled AI use, security, and downstream processing |
| public_pages.competencies | `public_pages.competencies.top_cards.structured_intake.title` | - | Strukturiertes Recruiting-Briefing | Structured recruiting brief |
| public_pages.competencies | `public_pages.competencies.top_cards.structured_intake.body` | - | Wir setzen nicht erst bei der Jobanzeige an, sondern bei der Bedarfsklärung. So werden Missverständnisse, spätere Korrekturschleifen und überladene Wunschprofile früh reduziert. | We do not start with the job ad, but with need clarification. This reduces misunderstandings, late correction loops, and overloaded wish lists early. |
| public_pages.competencies | `public_pages.competencies.top_cards.dynamic_flow.title` | - | Dynamischer Fragenfluss | Dynamic question flow |
| public_pages.competencies | `public_pages.competencies.top_cards.dynamic_flow.body` | - | Die App arbeitet nicht mit einem starren Standardformular. Sie leitet aus Jobspec, Rolle, Kontext und bisherigen Antworten genau die Fragen ab, die wirklich relevant sind. | The app does not use a rigid standard form. It derives exactly the questions that matter from the jobspec, role, context, and previous answers. |
| public_pages.competencies | `public_pages.competencies.top_cards.esco_semantics.title` | - | ESCO-gestützte Semantik | ESCO-supported semantics |
| public_pages.competencies | `public_pages.competencies.top_cards.esco_semantics.body` | - | Berufe und Skills werden nicht nur sprachlich erfasst, sondern semantisch verankert. Das verbessert Vergleichbarkeit, Klarheit und Anschlussfähigkeit in internationalen Recruiting-Kontexten. | Occupations and skills are not only captured linguistically, but anchored semantically. This improves comparability, clarity, and interoperability in international recruiting contexts. |
| public_pages.competencies | `public_pages.competencies.top_cards.controlled_ai.title` | - | Kontrollierte KI-Unterstützung | Controlled AI support |
| public_pages.competencies | `public_pages.competencies.top_cards.controlled_ai.body` | - | KI wird dort eingesetzt, wo sie Struktur schafft und Inhalte verdichtet. Nicht als Selbstzweck, sondern innerhalb eines klaren, nachvollziehbaren Workflows. | AI is used where it creates structure and condenses content. Not as an end in itself, but inside a clear, traceable workflow. |
| public_pages.competencies | `public_pages.competencies.top_cards.salary_estimation.title` | - | Salary Estimation | Salary estimation |
| public_pages.competencies | `public_pages.competencies.top_cards.salary_estimation.body` | - | Eine indikative Gehaltsprognose macht sichtbar, wie einzelne Parameter die Vergütung beeinflussen. Dadurch werden Stellen realistischer und marktnäher formuliert. | An indicative salary forecast makes visible how individual parameters influence compensation. This helps formulate roles more realistically and closer to the market. |
| public_pages.competencies | `public_pages.competencies.top_cards.exports.title` | - | Weiterverarbeitung & Exporte | Downstream processing and exports |
| public_pages.competencies | `public_pages.competencies.top_cards.exports.body` | - | Aus derselben Datengrundlage lassen sich Recruiting Brief, Stellenanzeige, HR-Sheet, Fachbereich-Sheet, Suchstrings und weitere Recruiting-Unterlagen direkt ableiten. | The same data foundation can directly produce a recruiting brief, job ad, HR sheet, hiring manager sheet, search strings, and further recruiting outputs. |
| public_pages.competencies | `public_pages.competencies.how.heading` | - | ## Wie die App arbeitet | ## How the app works |
| public_pages.competencies | `public_pages.competencies.how.body` | - | Die App beginnt mit einer Jobspec, einem Upload oder Freitext. Diese Ausgangsbasis wird zuerst analysiert und in eine belastbare Struktur überführt.<br><br>Darauf aufbauend entsteht ein rollenabhängiger Frageplan, der Nutzerinnen und Nutzer Schritt für Schritt durch die weitere Präzisierung führt.<br><br>Das Ziel ist kein längerer Prozess, sondern ein besserer: weniger unnötige Fragen, weniger Interpretationsspielraum und eine deutlich höhere Wiederverwendbarkeit der Ergebnisse. | The app starts with a jobspec, an upload, or free text. This starting point is first analyzed and converted into a robust structure.<br><br>Based on that, a role-specific question plan guides users step by step through further clarification.<br><br>The goal is not a longer process, but a better one: fewer unnecessary questions, less room for interpretation, and much higher reusability of the results. |
| public_pages.competencies | `public_pages.competencies.expanders.intake.title` | - | 1. Briefing statt Rätselraten | 1. Briefing instead of guesswork |
| public_pages.competencies | `public_pages.competencies.expanders.intake.body` | - | Zu Beginn werden vorhandene Stelleninformationen aufgenommen und strukturiert analysiert. Die App trennt dabei bewusst zwischen Quelle, Interpretation und Bestätigung.<br><br>So entsteht früh ein belastbarer Startpunkt für den weiteren Recruiting-Prozess.<br><br>**Mehrwert**<br>- weniger unklare Ausgangslagen,<br>- weniger Rückfragen zwischen Fachbereich und Recruiting,<br>- frühere Qualitätssicherung im Prozess. | At the beginning, existing role information is captured and structurally analyzed. The app deliberately separates source, interpretation, and confirmation.<br><br>This creates a robust starting point for the rest of the recruiting process.<br><br>**Value**<br>- fewer unclear starting points,<br>- fewer follow-up loops between the business team and recruiting,<br>- earlier quality assurance in the process. |
| public_pages.competencies | `public_pages.competencies.expanders.dynamic.title` | - | 2. Dynamischer Fragenfluss statt Formular-Overkill | 2. Dynamic question flow instead of form overload |
| public_pages.competencies | `public_pages.competencies.expanders.dynamic.body` | - | Auf Basis der bereits bekannten Informationen erzeugt die App einen **dynamischen Fragenfluss**.<br><br>Sichtbar werden zuerst die wichtigsten Themen; zusätzliche Tiefe wird nur dort geöffnet, wo Informationslücken bestehen oder Präzisierungen sinnvoll sind.<br><br>**Das bedeutet konkret**<br>- minimale Reibung für Fachbereiche,<br>- höhere Eingabequalität,<br>- bessere Akzeptanz im Alltag,<br>- klare Trennung zwischen Kerninformationen und Details. | Based on the information already known, the app creates a **dynamic question flow**.<br><br>The most important topics appear first; additional depth opens only where information gaps exist or clarification is useful.<br><br>**In practical terms**<br>- minimal friction for business teams,<br>- higher input quality,<br>- better acceptance in daily work,<br>- clear separation between core information and details. |
| public_pages.competencies | `public_pages.competencies.expanders.sharpening.title` | - | 3. Schärfung statt eierlegender Wollmilchsau | 3. Sharpening instead of an impossible all-in-one profile |
| public_pages.competencies | `public_pages.competencies.expanders.sharpening.body` | - | Aufgaben, Anforderungen, Skills, Benefits und Gehaltslogik werden nicht nur gesammelt, sondern gegeneinander kalibriert.<br><br>Dadurch sinkt das Risiko, unrealistische Stellenprofile zu formulieren, die am Markt kaum besetzbar sind.<br><br>**Ergebnis**<br>- realistischere Zielprofile,<br>- sauberere Trennung von Must-have und Nice-to-have,<br>- bessere Grundlage für spätere Suche und Interviews. | Tasks, requirements, skills, benefits, and salary logic are not only collected, but calibrated against each other.<br><br>This lowers the risk of formulating unrealistic role profiles that are barely fillable in the market.<br><br>**Result**<br>- more realistic target profiles,<br>- cleaner separation of must-have and nice-to-have criteria,<br>- a better foundation for later search and interviews. |
| public_pages.competencies | `public_pages.competencies.esco.heading` | - | ## ESCO als semantischer Anker | ## ESCO as a semantic anchor |
| public_pages.competencies | `public_pages.competencies.esco.body` | - | Mit ESCO integriert Cognitive Staffing eine europaweit etablierte, mehrsprachige Klassifikation für Skills, Competences, Qualifications und Occupations.<br><br>ESCO funktioniert dabei wie ein gemeinsames semantisches Vokabular, das Begriffe nicht nur beschreibt, sondern auch in ihren Beziehungen maschinenlesbar macht. | With ESCO, Cognitive Staffing integrates a Europe-wide, multilingual classification for skills, competences, qualifications, and occupations.<br><br>ESCO works like a shared semantic vocabulary that not only describes terms, but also makes their relationships machine-readable. |
| public_pages.competencies | `public_pages.competencies.esco.callout_title` | - | Warum ESCO in dieser App so wertvoll ist | Why ESCO is valuable in this app |
| public_pages.competencies | `public_pages.competencies.esco.callout_body` | - | Statt nur freie Rollen- und Skillbezeichnungen zu sammeln, kann die App Occupations und Skills semantisch verankern. Das erhöht Konsistenz, Vergleichbarkeit und die Qualität späterer Ableitungen. | Instead of collecting only free-form role and skill labels, the app can semantically anchor occupations and skills. This increases consistency, comparability, and the quality of later derivations. |
| public_pages.competencies | `public_pages.competencies.esco.column_a` | - | ### Was ESCO mitbringt<br>- standardisierte Occupations und Skills,<br>- mehrsprachige Begriffe,<br>- API-Zugriff für technische Einbindung,<br>- Beziehungen zwischen Berufen, Skills und Wissensbereichen,<br>- maschinenlesbare Konzepte statt bloßer Stichwörter. | ### What ESCO provides<br>- standardized occupations and skills,<br>- multilingual terms,<br>- API access for technical integration,<br>- relationships between occupations, skills, and knowledge areas,<br>- machine-readable concepts instead of plain keywords. |
| public_pages.competencies | `public_pages.competencies.esco.column_b` | - | ### Mehrwert für Cognitive Staffing<br>- saubereres Occupation-Mapping,<br>- normalisierte Skill-Vorschläge,<br>- nachvollziehbare Herkunft von Empfehlungen,<br>- bessere Anschlussfähigkeit für Suche, Matching und Reporting,<br>- stabilere Begriffslogik über Teams und Standorte hinweg. | ### Value for Cognitive Staffing<br>- cleaner occupation mapping,<br>- normalized skill suggestions,<br>- traceable origin of recommendations,<br>- better interoperability for search, matching, and reporting,<br>- more stable terminology across teams and locations. |
| public_pages.competencies | `public_pages.competencies.esco.after` | - | Gerade weil ESCO Occupations und Skills nicht nur als Wörter, sondern als verknüpfte Konzepte beschreibt, eignet sich die Klassifikation sehr gut für ein strukturiertes Recruiting-Briefing. | Because ESCO describes occupations and skills not merely as words, but as linked concepts, the classification is especially well suited for a structured recruiting brief. |
| public_pages.competencies | `public_pages.competencies.model.heading` | - | ## Verwendetes ChatGPT-Modell und KI-Architektur | ## ChatGPT model use and AI architecture |
| public_pages.competencies | `public_pages.competencies.model.body` | - | Die App nutzt die OpenAI API **aufgabenbezogen**. Das bedeutet: Nicht jede Funktion wird zwangsläufig mit demselben Modell ausgeführt.<br><br>Je nach Task – etwa Extraktion, Frageplanung oder Generierung von Recruiting-Unterlagen – kann unterschiedlich geroutet werden.<br><br>Wichtig ist deshalb nicht nur das Modell selbst, sondern die **kontrollierte Form der Ausgabe**:<br>- strukturierte Ergebnisse statt bloßer Fließtexte,<br>- klare Schemata statt freier Halluzinationsflächen,<br>- bessere Weiterverarbeitung innerhalb des Wizards. | The app uses the OpenAI API **by task**. This means not every function necessarily runs on the same model.<br><br>Depending on the task - such as extraction, question planning, or output generation - routing can differ.<br><br>What matters is therefore not only the model itself, but the **controlled shape of the output**:<br>- structured results instead of plain prose,<br>- clear schemas instead of open-ended hallucination space,<br>- better downstream processing inside the wizard. |
| public_pages.competencies | `public_pages.competencies.model.callout_title` | - | Wichtige Einordnung | Important context |
| public_pages.competencies | `public_pages.competencies.model.callout_body` | - | Die produktive Konfiguration ist modellabhängig und deploymentabhängig. Damit bleibt die Architektur flexibel, ohne die Qualität des Workflows an ein einziges festes Modell zu ketten. | Production configuration depends on the selected model and deployment. This keeps the architecture flexible without tying workflow quality to a single fixed model. |
| public_pages.competencies | `public_pages.competencies.dynamic_flow.heading` | - | ## Dynamischer Fragenfluss | ## Dynamic question flow |
| public_pages.competencies | `public_pages.competencies.dynamic_flow.body` | - | Der Fragenfluss passt sich an:<br>- die eingebrachte Jobspec,<br>- bereits identifizierte Informationen,<br>- den gewählten Detailgrad,<br>- frühere Antworten im Verlauf,<br>- und die bestätigte semantische Einordnung der Stelle.<br><br>So entsteht ein Prozess, der **adaptiv** statt starr arbeitet.<br><br>Nutzerinnen und Nutzer sehen zuerst das Wesentliche – und nur dort mehr Tiefe, wo sie für die konkrete Vakanz tatsächlich Mehrwert schafft. | The question flow adapts to:<br>- the submitted jobspec,<br>- information already identified,<br>- the selected level of detail,<br>- earlier answers in the workflow,<br>- and the confirmed semantic classification of the role.<br><br>This creates a process that works **adaptively** rather than rigidly.<br><br>Users see the essentials first - and more depth only where it actually adds value for the specific vacancy. |
| public_pages.competencies | `public_pages.competencies.downstream.heading` | - | ## Weiterverarbeitungsoptionen | ## Downstream options |
| public_pages.competencies | `public_pages.competencies.downstream.cards.brief.title` | - | Recruiting Brief | Recruiting brief |
| public_pages.competencies | `public_pages.competencies.downstream.cards.brief.body` | - | Die konsolidierte Entscheidungsgrundlage für Recruiting, Fachbereich und Management. | The consolidated decision foundation for recruiting, the business team, and management. |
| public_pages.competencies | `public_pages.competencies.downstream.cards.job_ad.title` | - | Stellenanzeige | Job ad generation |
| public_pages.competencies | `public_pages.competencies.downstream.cards.job_ad.body` | - | Aus der strukturierten Datensammlung entsteht eine konsistente, zielgruppengerechte Stellenanzeige. | The structured data collection becomes a consistent, audience-specific job ad. |
| public_pages.competencies | `public_pages.competencies.downstream.cards.interview.title` | - | HR-Sheet und Fachbereich-Sheet | HR sheet and hiring manager sheet |
| public_pages.competencies | `public_pages.competencies.downstream.cards.interview.body` | - | Vorbereitungen für HR und Fachbereich mit klaren Themen, Prüfpunkten und Leitfragen. | Preparation for HR and the business team with clear topics, checkpoints, and guiding questions. |
| public_pages.competencies | `public_pages.competencies.downstream.cards.boolean.title` | - | Suchstrings | Search strings |
| public_pages.competencies | `public_pages.competencies.downstream.cards.boolean.body` | - | Ableitungen für LinkedIn, Xing oder Google, damit Suchstrategien präziser und reproduzierbarer werden. | Derivations for LinkedIn, Xing, or Google so search strategies become more precise and reproducible. |
| public_pages.competencies | `public_pages.competencies.downstream.cards.exports.title` | - | Exports | Exports |
| public_pages.competencies | `public_pages.competencies.downstream.cards.exports.body` | - | Je nach Unterlage als JSON, Markdown, DOCX, PDF oder Mapping-Report weiterverwendbar. | Depending on the output, results can be reused as JSON, Markdown, DOCX, PDF, or mapping report. |
| public_pages.competencies | `public_pages.competencies.security.heading` | - | ## Sicherheit | ## Security |
| public_pages.competencies | `public_pages.competencies.security.body` | - | Im HR-Kontext ist Datensensibilität kein Randthema. Deshalb ist Sicherheit für uns Teil der Produktlogik – nicht bloß ein Nachgedanke.<br><br>Schon in einem cloudbasierten Setup helfen strukturierte Verarbeitung, klare Exportpfade, kontrollierte Modellaufrufe und Datenminimierung dabei, sensible Inhalte bewusster zu behandeln. | In an HR context, data sensitivity is not a side issue. That is why security is part of the product logic, not an afterthought.<br><br>Even in a cloud-based setup, structured processing, clear export paths, controlled model calls, and data minimization help handle sensitive content more deliberately. |
| public_pages.competencies | `public_pages.competencies.security.local_llm.title` | - | Lokales LLM als Sicherheitsoption | Local LLM as a security option |
| public_pages.competencies | `public_pages.competencies.security.local_llm.body` | - | Für besonders sensible HR-Themen kann ein **lokal laufendes LLM** oder ein streng isoliertes On-Prem-/VPC-Setup erhebliche Vorteile bringen:<br><br>- Daten verbleiben in der eigenen Infrastruktur,<br>- Zugriffe und Speicherorte sind enger kontrollierbar,<br>- Drittlandtransfers und externe Abhängigkeiten können reduziert werden,<br>- Sicherheitsregeln lassen sich unternehmensspezifisch erzwingen,<br>- Akzeptanz für sensible HR-Prozesse steigt oft deutlich.<br><br>**Wichtige Einordnung**<br>Ein lokales LLM ist nicht automatisch sicher. Es verschiebt Verantwortung vom externen Anbieter in die eigene Umgebung.<br><br>Richtig umgesetzt bietet es jedoch bei sensiblen Recruiting- und HR-Themen oft mehr Kontrolle, mehr Transparenz und mehr Governance. | For especially sensitive HR topics, a **locally running LLM** or a strictly isolated on-prem/VPC setup can provide significant advantages:<br><br>- data remains in the organization's own infrastructure,<br>- access and storage locations can be controlled more tightly,<br>- third-country transfers and external dependencies can be reduced,<br>- security rules can be enforced company-specifically,<br>- acceptance for sensitive HR processes often increases significantly.<br><br>**Important context**<br>A local LLM is not automatically secure. It shifts responsibility from an external provider into the organization's own environment.<br><br>Implemented properly, however, it often offers more control, more transparency, and more governance for sensitive recruiting and HR topics. |
| public_pages.competencies | `public_pages.competencies.cta.title` | - | Sie möchten sehen, wie aus einem unklaren Stellenbedarf ein belastbarer Recruiting-Startpunkt wird? | Would you like to see how an unclear hiring need becomes a reliable recruiting starting point? |
| public_pages.competencies | `public_pages.competencies.cta.body` | brand | Testen Sie {brand} und erleben Sie, wie strukturiertes Recruiting-Briefing Recruiting von Anfang an besser macht. | Try {brand} and experience how a structured recruiting brief improves recruiting from the start. |
| public_pages.about | `public_pages.about.title` | - | Über Cognitive Staffing | About Cognitive Staffing |
| public_pages.about | `public_pages.about.hero.eyebrow` | - | Über uns | About us |
| public_pages.about | `public_pages.about.hero.lead` | - | Der Firmengründer, Gerrit Fabisch, entwickelt digitale Werkzeuge, die Arbeitgebern helfen, Prozesse klarer zu definieren und durch den Einsatz von KI zu optimieren. | The company founder, Gerrit Fabisch, develops digital tools that help employers define processes more clearly and optimize them through the use of AI. |
| public_pages.about | `public_pages.about.meta` | - | Präzision · Steuerbarkeit · Wiederverwendbarkeit | Precision · controllability · reusability |
| public_pages.about | `public_pages.about.cards.career.title` | - | Mein Werdegang | My background |
| public_pages.about | `public_pages.about.cards.career.body` | - | Ich bringe dafür ein Profil mit, das Business-Verständnis, Schnittstellenkompetenz und aktuelle KI-Praxis zusammenführt. Nach meinem BWL-Studium habe ich über viele Jahre in vertriebs- und recruitingnahen Rollen gearbeitet – mit Verantwortung für Kundenentwicklung, Verhandlungen, Projektstabilität, KPI-Steuerung und die Zusammenarbeit mit unterschiedlichen internen und externen Stakeholdern. | I bring a profile that combines business understanding, interface competence, and current AI practice. After studying business administration, I worked for many years in sales- and recruiting-related roles - with responsibility for customer development, negotiations, project stability, KPI steering, and collaboration with different internal and external stakeholders. |
| public_pages.about | `public_pages.about.cards.offer.title` | - | Was ich biete | What I offer |
| public_pages.about | `public_pages.about.cards.offer.body` | - | In meiner aktuellen Tätigkeit als Gründer und KI-Recruitment-Berater entwickle ich einen KI-gestützten Prototypen zur Optimierung von Recruiting-Aktivitäten auf Basis der OpenAI-API, ESCO-API und eines eigenen Vector Stores. Ergänzt wird dies durch meine Data-Science-Weiterbildung sowie LLM-spezifische Kurse zu strukturierten Ergebnissen und Reasoning. | In my current work as a founder and AI recruitment consultant, I develop an AI-supported prototype for optimizing recruiting activities based on the OpenAI API, ESCO API, and a dedicated vector store. This is complemented by my data science training and LLM-specific courses on structured outputs and reasoning. |
| public_pages.about | `public_pages.about.cards.goal.title` | - | Was ich mir wünsche | What I am looking for |
| public_pages.about | `public_pages.about.cards.goal.body` | - | Ich sehe KI nicht als Selbstzweck, sondern als Hebel für bessere Entscheidungen, effizientere Prozesse und einen konkreten Mehrwert für Fachbereiche und Kunden. Diese Haltung möchte ich in ein Umfeld einbringen, das KI bereits strategisch und international verankert. | I do not see AI as an end in itself, but as a lever for better decisions, more efficient processes, and concrete value for business teams and customers. I want to bring this mindset into an environment where AI is already anchored strategically and internationally. |
| public_pages.about | `public_pages.about.why.heading` | - | ## Warum Cognitive Staffing | ## Why Cognitive Staffing |
| public_pages.about | `public_pages.about.why.body` | - | Unsere Stärke liegt in der Verbindung aus Recruiting-Fachlogik, semantischer Strukturierung und moderner KI-Unterstützung.<br><br>So entstehen Lösungen, die nicht nur innovativ wirken, sondern im Alltag spürbar entlasten.<br><br>Wir denken vom Prozess her:<br>nicht von einem einzelnen Text, nicht von einem einzelnen Formular, sondern von einem besseren Startpunkt für den gesamten Recruiting-Verlauf. | Our strength lies in combining recruiting domain logic, semantic structuring, and modern AI support.<br><br>This creates solutions that do not merely look innovative, but noticeably reduce effort in daily work.<br><br>We think from the process perspective:<br>not from a single text, not from a single form, but from a better starting point for the entire recruiting journey. |
| public_pages.about | `public_pages.about.cta.title` | - | Unser Ziel | Our goal |
| public_pages.about | `public_pages.about.cta.body` | - | Nicht nur schnellere Besetzungen. Unser Ziel ist, Arbeitgeber und Arbeitnehmer langfristig passender, erfolgreicher und nachhaltiger zusammenzubringen. | Not just faster hiring. Our goal is to bring employers and employees together in a way that is more fitting, more successful, and more sustainable over the long term. |
| public_pages.imprint | `public_pages.imprint.eyebrow` | - | Rechtliche Information | Legal information |
| public_pages.imprint | `public_pages.imprint.title` | - | Impressum | Imprint |
| public_pages.imprint | `public_pages.imprint.intro.0` | - | Diese Seite bündelt die Anbieterkennzeichnung für Cognitive Staffing. | This page bundles the provider identification for Cognitive Staffing. |
| public_pages.imprint | `public_pages.imprint.intro.1` | - | Für eine verbindliche Veröffentlichung fehlen noch final geprüfte Unternehmens- und Registerdaten. | Final reviewed company and register data is still missing for binding publication. |
| public_pages.imprint | `public_pages.imprint.sections.scope.heading` | - | Anwendungsbereich | Scope |
| public_pages.imprint | `public_pages.imprint.sections.scope.body` | - | Das Impressum gilt für diese Website, die App-Oberfläche und alle hier verlinkten öffentlichen Informationsseiten. | This imprint applies to this website, the app interface, and all public information pages linked here. |
| public_pages.imprint | `public_pages.imprint.sections.required_info.heading` | - | Pflichtangaben | Mandatory information |
| public_pages.imprint | `public_pages.imprint.sections.required_info.body` | - | Die Anbieterkennzeichnung muss die rechtlich erforderlichen Angaben zur verantwortlichen Stelle enthalten, insbesondere Name/Firma, Anschrift, Kontaktwege, Vertretungsberechtigte und gegebenenfalls Register- oder Aufsichtsangaben. | The provider identification must contain the legally required information about the responsible entity, in particular name/company, address, contact channels, authorized representatives, and, where applicable, register or supervisory information. |
| public_pages.imprint | `public_pages.imprint.sections.responsibilities.heading` | - | Verantwortlichkeit für Inhalte | Responsibility for content |
| public_pages.imprint | `public_pages.imprint.sections.responsibilities.body` | - | Die Inhalte dieser Website werden mit Sorgfalt gepflegt. Aktualität und Richtigkeit werden bei Änderungen an Unternehmensdaten, Kontaktwegen oder App-Konfiguration überprüft. | The content of this website is maintained with care. Timeliness and accuracy are reviewed when company data, contact channels, or app configuration change. |
| public_pages.imprint | `public_pages.imprint.sections.contact_paths.heading` | - | Kontaktwege | Contact channels |
| public_pages.imprint | `public_pages.imprint.sections.contact_paths.body` | - | Für allgemeine Anfragen, Datenschutzanliegen und Barrierefreiheitsfeedback sollten klar getrennte Kontaktwege angegeben werden, sofern diese organisatorisch vorgesehen sind. | Separate contact channels should be stated for general inquiries, privacy requests, and accessibility feedback where these are organizationally intended. |
| public_pages.imprint | `public_pages.imprint.sections.version_note.heading` | - | Stand und Pflege | Status and maintenance |
| public_pages.imprint | `public_pages.imprint.sections.version_note.body` | - | Das Impressum sollte bei Änderungen an Unternehmensdaten, Rechtsform, Vertretungsberechtigten, Hosting-Konstellation oder Kontaktwegen zeitnah aktualisiert werden. | The imprint should be updated promptly when company data, legal form, authorized representatives, hosting setup, or contact channels change. |
| public_pages.imprint | `public_pages.imprint.missing_inputs.legal_info.heading` | - | Noch fehlende Unternehmensdaten | Company data still missing |
| public_pages.imprint | `public_pages.imprint.missing_inputs.legal_info.items.company_address` | - | vollständige Anbieteranschrift mit Rechtsform und Vertretungsberechtigung | full provider address with legal form and authorized representation |
| public_pages.imprint | `public_pages.imprint.missing_inputs.legal_info.items.registry` | - | Registergericht, Registernummer, Umsatzsteuer-ID oder Wirtschafts-ID, falls einschlägig | register court, register number, VAT ID, or business ID where applicable |
| public_pages.imprint | `public_pages.imprint.trust.heading` | - | Hinweis | Note |
| public_pages.imprint | `public_pages.imprint.trust.details.0` | - | Diese Seite ersetzt keine Rechtsberatung. Nicht veröffentlichte Unternehmensdaten sind ausdrücklich gekennzeichnet und dürfen nicht durch angenommene Werte ersetzt werden. | This page does not replace legal advice. Company data that has not been published is marked explicitly and must not be replaced with assumed values. |
| public_pages.imprint | `public_pages.imprint.footer_classification` | - | Rechtliche Seite · Prüfung erforderlich | Legal page · review required |
| public_pages.privacy | `public_pages.privacy.title` | - | Datenschutzrichtlinie | Privacy policy |
| public_pages.privacy | `public_pages.privacy.hero.eyebrow` | - | Datenschutz | Privacy |
| public_pages.privacy | `public_pages.privacy.hero.lead` | - | Der Schutz personenbezogener Daten ist uns wichtig. Auf dieser Seite informieren wir darüber, welche Daten bei der Nutzung unserer Website und App verarbeitet werden, zu welchen Zwecken dies geschieht und welche Rechte betroffene Personen haben. | Protecting personal data matters to us. This page explains which data is processed when using our website and app, for which purposes this happens, and which rights affected persons have. |
| public_pages.privacy | `public_pages.privacy.notice.title` | - | Hinweis | Note |
| public_pages.privacy | `public_pages.privacy.notice.body` | - | Diese Datenschutzrichtlinie beschreibt die aktuell dokumentierte App-Konfiguration, Kontaktwege und Datenverarbeitung. Änderungen an Dienstleistern, Speicherfristen oder internen Prozessen müssen zeitnah nachgezogen werden. | This privacy policy describes the currently documented app configuration, contact channels, and data processing. Changes to service providers, retention periods, or internal processes must be reflected promptly. |
| public_pages.privacy | `public_pages.privacy.controller.heading` | - | ## 1. Verantwortlicher | ## 1. Controller |
| public_pages.privacy | `public_pages.privacy.controller.body` | city, country, email, legal_entity, phone, postal_code, street, website | **{legal_entity}**  <br>{street}  <br>{postal_code} {city}  <br>{country}<br><br>**E-Mail:** {email}  <br>**Telefon:** {phone}  <br>**Website:** {website} | **{legal_entity}**  <br>{street}  <br>{postal_code} {city}  <br>{country}<br><br>**Email:** {email}  <br>**Phone:** {phone}  <br>**Website:** {website} |
| public_pages.privacy | `public_pages.privacy.privacy_contact.heading` | - | ## 2. Datenschutzkontakt | ## 2. Privacy contact |
| public_pages.privacy | `public_pages.privacy.privacy_contact.body` | dpo_name, privacy_email | Fragen zum Datenschutz können an folgende Stelle gerichtet werden:<br><br>**E-Mail:** {privacy_email}  <br>**Datenschutzbeauftragte Person / Stelle:** {dpo_name} | Privacy questions can be directed to the following contact:<br><br>**Email:** {privacy_email}  <br>**Data protection officer / contact point:** {dpo_name} |
| public_pages.privacy | `public_pages.privacy.processed_data.heading` | - | ## 3. Welche Daten wir verarbeiten | ## 3. Which data we process |
| public_pages.privacy | `public_pages.privacy.processed_data.body` | - | Je nach Nutzung der Website und App können insbesondere folgende Daten verarbeitet werden:<br><br>- technische Zugriffsdaten und Protokolldaten,<br>- Kontakt- und Kommunikationsdaten,<br>- Inhalte, die Nutzerinnen und Nutzer aktiv eingeben oder hochladen,<br>- Nutzungs- und Einstellungsdaten,<br>- Einwilligungs- und Präferenzdaten, soweit einschlägig,<br>- organisationsbezogene Informationen im Rahmen der App-Nutzung. | Depending on website and app use, the following data in particular may be processed:<br><br>- technical access data and log data,<br>- contact and communication data,<br>- content that users actively enter or upload,<br>- usage and settings data,<br>- consent and preference data where applicable,<br>- organization-related information in the context of app use. |
| public_pages.privacy | `public_pages.privacy.purposes.heading` | - | ## 4. Zwecke der Verarbeitung | ## 4. Purposes of processing |
| public_pages.privacy | `public_pages.privacy.purposes.body` | - | Wir verarbeiten Daten insbesondere zu folgenden Zwecken:<br><br>- Bereitstellung und Betrieb der Website und App,<br>- Bearbeitung von Anfragen,<br>- strukturierte Aufbereitung von Recruiting- und Stelleninformationen,<br>- Generierung weiterer Recruiting-Unterlagen innerhalb der Anwendung,<br>- Gewährleistung von IT-Sicherheit, Fehleranalyse und Missbrauchsprävention,<br>- Nachweis- und Dokumentationspflichten. | We process data in particular for the following purposes:<br><br>- providing and operating the website and app,<br>- handling inquiries,<br>- structurally preparing recruiting and vacancy information,<br>- generating downstream recruiting outputs inside the application,<br>- ensuring IT security, error analysis, and abuse prevention,<br>- meeting documentation and evidence obligations. |
| public_pages.privacy | `public_pages.privacy.hr_content.heading` | - | ## 5. Besondere Hinweise zu HR-Inhalten | ## 5. Special notes on HR content |
| public_pages.privacy | `public_pages.privacy.hr_content.body` | - | Unsere Anwendung kann zur Verarbeitung von Stelleninformationen, Jobspecs und vergleichbaren Dokumenten genutzt werden.<br><br>Bitte laden Sie nur solche Inhalte hoch oder übermitteln Sie nur solche Informationen, deren Verarbeitung zulässig, erforderlich und intern freigegeben ist.<br><br>Besonders sensible personenbezogene Daten sollten nur dann verarbeitet werden, wenn hierfür eine tragfähige rechtliche Grundlage und ein geeigneter organisatorischer Rahmen bestehen. | Our application can be used to process vacancy information, jobspecs, and comparable documents.<br><br>Please upload or submit only content whose processing is lawful, necessary, and internally approved.<br><br>Especially sensitive personal data should be processed only where there is a sound legal basis and an appropriate organizational framework. |
| public_pages.privacy | `public_pages.privacy.legal_basis.heading` | - | ## 6. Rechtsgrundlagen | ## 6. Legal bases |
| public_pages.privacy | `public_pages.privacy.legal_basis.body` | - | Die Verarbeitung erfolgt – je nach Fallgestaltung – insbesondere auf Grundlage von:<br><br>- Art. 6 Abs. 1 lit. a DSGVO,<br>- Art. 6 Abs. 1 lit. b DSGVO,<br>- Art. 6 Abs. 1 lit. c DSGVO,<br>- Art. 6 Abs. 1 lit. f DSGVO.<br><br>Soweit besondere Kategorien personenbezogener Daten betroffen sind, gelten zusätzlich die hierfür einschlägigen spezialgesetzlichen und datenschutzrechtlichen Anforderungen. | Depending on the specific case, processing is based in particular on:<br><br>- Art. 6(1)(a) GDPR,<br>- Art. 6(1)(b) GDPR,<br>- Art. 6(1)(c) GDPR,<br>- Art. 6(1)(f) GDPR.<br><br>Where special categories of personal data are affected, the relevant sector-specific and data protection requirements also apply. |
| public_pages.privacy | `public_pages.privacy.recipients.heading` | - | ## 7. Empfänger und eingesetzte Dienstleister | ## 7. Recipients and service providers used |
| public_pages.privacy | `public_pages.privacy.recipients.providers.hosting` | - | Hosting / Deployment: Streamlit-App-Hosting | Hosting / deployment: Streamlit app hosting |
| public_pages.privacy | `public_pages.privacy.recipients.providers.ai` | - | KI-Anbieter / LLM-Infrastruktur: OpenAI API, sofern KI-Funktionen genutzt werden | AI provider / LLM infrastructure: OpenAI API where AI functions are used |
| public_pages.privacy | `public_pages.privacy.recipients.providers.email` | - | E-Mail / Support-Workflow: konfigurierte Kontakt-E-Mail-Adressen | Email / support workflow: configured contact email aliases |
| public_pages.privacy | `public_pages.privacy.recipients.providers.consent` | - | Consent- / Cookie-Management: Streamlit-Präferenzen und Session-State | Consent / cookie management: Streamlit preferences and session state |
| public_pages.privacy | `public_pages.privacy.recipients.body` | - | Sofern externe technische Dienstleister oder KI-Dienste eingebunden sind, erfolgt dies nur im Rahmen der jeweils vorgesehenen technischen, organisatorischen und vertraglichen Vorkehrungen. | Where external technical service providers or AI services are involved, this takes place only within the intended technical, organizational, and contractual safeguards. |
| public_pages.privacy | `public_pages.privacy.retention.heading` | - | ## 8. Speicherung und Löschung | ## 8. Storage and deletion |
| public_pages.privacy | `public_pages.privacy.retention.body` | - | Wir speichern personenbezogene Daten nur so lange, wie dies für die jeweiligen Zwecke erforderlich ist oder gesetzliche Aufbewahrungspflichten dies verlangen.<br><br>Soweit Inhalte innerhalb der Anwendung verarbeitet werden, sollte die Verarbeitung auf das erforderliche Maß begrenzt und organisatorisch kontrolliert werden. Exportierte Dokumente und weitere Recruiting-Unterlagen unterliegen zusätzlich den Regeln der jeweiligen Nutzerorganisation. | We store personal data only for as long as necessary for the respective purposes or as required by statutory retention obligations.<br><br>Where content is processed inside the application, processing should be limited to what is necessary and organizationally controlled. Exported documents and downstream recruiting outputs are also subject to the rules of the respective user organization. |
| public_pages.privacy | `public_pages.privacy.cookies.heading` | - | ## 9. Cookies und ähnliche Technologien | ## 9. Cookies and similar technologies |
| public_pages.privacy | `public_pages.privacy.cookies.body` | - | Wir verwenden Cookies und vergleichbare Technologien nur im jeweils erforderlichen Umfang.<br><br>Soweit nicht unbedingt erforderliche Technologien eingesetzt werden, erfolgt dies nur auf der Grundlage einer wirksamen Einwilligung oder einer sonst einschlägigen Rechtsgrundlage.<br><br>Weitere Informationen finden Sie in unserer Cookie Policy. | We use cookies and comparable technologies only to the extent required.<br><br>Where technologies that are not strictly necessary are used, this is done only on the basis of valid consent or another applicable legal basis.<br><br>Further information is available in our cookie policy. |
| public_pages.privacy | `public_pages.privacy.rights.heading` | - | ## 10. Ihre Rechte | ## 10. Your rights |
| public_pages.privacy | `public_pages.privacy.rights.body` | - | Betroffene Personen haben im Rahmen der gesetzlichen Voraussetzungen insbesondere das Recht auf:<br><br>- Auskunft,<br>- Berichtigung,<br>- Löschung,<br>- Einschränkung der Verarbeitung,<br>- Datenübertragbarkeit,<br>- Widerspruch,<br>- Widerruf erteilter Einwilligungen mit Wirkung für die Zukunft,<br>- Beschwerde bei einer zuständigen Aufsichtsbehörde. | Affected persons have, within the statutory requirements, in particular the right to:<br><br>- access,<br>- rectification,<br>- deletion,<br>- restriction of processing,<br>- data portability,<br>- objection,<br>- withdraw consent with effect for the future,<br>- lodge a complaint with a competent supervisory authority. |
| public_pages.privacy | `public_pages.privacy.security.heading` | - | ## 11. Datensicherheit | ## 11. Data security |
| public_pages.privacy | `public_pages.privacy.security.body` | - | Wir treffen angemessene technische und organisatorische Maßnahmen, um personenbezogene Daten vor Verlust, Manipulation, unberechtigtem Zugriff und sonstigen Risiken zu schützen.<br><br>Dazu gehören insbesondere Maßnahmen zur Zugriffskontrolle, zur Begrenzung unnötiger Datenverarbeitung, zur sicheren Konfiguration der eingesetzten Systeme und zur nachvollziehbaren Steuerung sensibler Prozesse. | We take appropriate technical and organizational measures to protect personal data against loss, manipulation, unauthorized access, and other risks.<br><br>These include, in particular, measures for access control, limiting unnecessary data processing, secure configuration of the systems used, and traceable control of sensitive processes. |
| public_pages.privacy | `public_pages.privacy.cta.title` | - | Fragen zum Datenschutz | Questions about privacy |
| public_pages.privacy | `public_pages.privacy.cta.body` | privacy_email | Für datenschutzbezogene Anliegen erreichen Sie uns unter **{privacy_email}**. | For privacy-related matters, you can reach us at **{privacy_email}**. |
| public_pages.terms | `public_pages.terms.title` | - | Nutzungsbedingungen | Terms of use |
| public_pages.terms | `public_pages.terms.hero.eyebrow` | - | Rechtliches | Legal |
| public_pages.terms | `public_pages.terms.hero.lead` | - | Diese Nutzungsbedingungen regeln die Nutzung unserer Website und der bereitgestellten App-Funktionen. Bitte lesen Sie die folgenden Hinweise sorgfältig. | These terms of use govern the use of our website and the app functions provided. Please read the following information carefully. |
| public_pages.terms | `public_pages.terms.offer.heading` | - | ## 1. Gegenstand des Angebots | ## 1. Subject matter of the offering |
| public_pages.terms | `public_pages.terms.offer.body` | - | Cognitive Staffing stellt digitale Funktionen zur strukturierten Erfassung, Aufbereitung und Weiterverarbeitung von Recruiting- und Stelleninformationen bereit.<br><br>Das Angebot dient der Unterstützung von Recruiting-, HR- und Abstimmungsprozessen. Es handelt sich nicht um ein autonom entscheidendes System. | Cognitive Staffing provides digital functions for the structured capture, preparation, and further processing of recruiting and vacancy information.<br><br>The offering supports recruiting, HR, and alignment processes. It is not an autonomously deciding system. |
| public_pages.terms | `public_pages.terms.no_advice.heading` | - | ## 2. Kein Ersatz für Rechts- oder Personalberatung | ## 2. No substitute for legal or HR advice |
| public_pages.terms | `public_pages.terms.no_advice.body` | - | Die innerhalb der Anwendung erzeugten Inhalte und Ergebnisse dienen der fachlichen Unterstützung.<br><br>Sie stellen weder Rechtsberatung noch eine verbindliche Personalentscheidung oder eine automatische Eignungsbewertung dar.<br><br>Alle Ergebnisse sind vor der weiteren Verwendung eigenverantwortlich zu prüfen. | The content and results generated inside the application are intended as professional support.<br><br>They do not constitute legal advice, a binding HR decision, or an automatic suitability assessment.<br><br>All results must be reviewed independently before further use. |
| public_pages.terms | `public_pages.terms.permitted_use.heading` | - | ## 3. Zulässige Nutzung | ## 3. Permitted use |
| public_pages.terms | `public_pages.terms.permitted_use.body` | - | Die Nutzung ist nur im Einklang mit geltendem Recht und nur mit solchen Inhalten zulässig, zu deren Verarbeitung Sie berechtigt sind.<br><br>Untersagt ist insbesondere die Nutzung für:<br>- rechtswidrige oder diskriminierende Inhalte,<br>- missbräuchliche oder sicherheitsgefährdende Zwecke,<br>- die Verarbeitung unzulässiger oder unbefugt übermittelter Daten,<br>- Versuche der Manipulation, Überlastung oder Umgehung technischer Schutzmechanismen. | Use is permitted only in compliance with applicable law and only with content that you are authorized to process.<br><br>In particular, use is prohibited for:<br>- unlawful or discriminatory content,<br>- abusive or security-endangering purposes,<br>- processing impermissible or unauthorizedly submitted data,<br>- attempts to manipulate, overload, or circumvent technical safeguards. |
| public_pages.terms | `public_pages.terms.user_responsibility.heading` | - | ## 4. Verantwortung der Nutzerinnen und Nutzer | ## 4. User responsibility |
| public_pages.terms | `public_pages.terms.user_responsibility.body` | - | Nutzerinnen und Nutzer sind insbesondere dafür verantwortlich,<br><br>- nur rechtmäßig verarbeitbare Daten einzugeben,<br>- erzeugte Ergebnisse fachlich zu prüfen,<br>- interne Richtlinien und rechtliche Anforderungen einzuhalten,<br>- geeignete Schutzmaßnahmen im eigenen organisatorischen Umfeld sicherzustellen. | Users are responsible in particular for:<br><br>- entering only lawfully processable data,<br>- reviewing generated results professionally,<br>- complying with internal policies and legal requirements,<br>- ensuring appropriate safeguards in their own organizational environment. |
| public_pages.terms | `public_pages.terms.availability.heading` | - | ## 5. Verfügbarkeit | ## 5. Availability |
| public_pages.terms | `public_pages.terms.availability.body` | - | Wir bemühen uns um eine möglichst stabile und unterbrechungsfreie Bereitstellung des Angebots.<br><br>Ein Anspruch auf permanente Verfügbarkeit besteht jedoch nicht. Wartungen, Weiterentwicklungen, technische Störungen oder externe Abhängigkeiten können zu Einschränkungen führen. | We strive to provide the offering as stably and continuously as possible.<br><br>However, there is no entitlement to permanent availability. Maintenance, further development, technical disruptions, or external dependencies may lead to limitations. |
| public_pages.terms | `public_pages.terms.changes.heading` | - | ## 6. Änderungen des Angebots | ## 6. Changes to the offering |
| public_pages.terms | `public_pages.terms.changes.body` | - | Wir behalten uns vor, Inhalte, Funktionen und technische Ausgestaltungen anzupassen, weiterzuentwickeln, einzuschränken oder einzustellen, soweit hierfür ein sachlicher Grund besteht. | We reserve the right to adapt, further develop, restrict, or discontinue content, functions, and technical designs where there is an objective reason to do so. |
| public_pages.terms | `public_pages.terms.ip.heading` | - | ## 7. Geistiges Eigentum | ## 7. Intellectual property |
| public_pages.terms | `public_pages.terms.ip.body` | - | Sämtliche Inhalte, Marken, Texte, Designs, Softwarebestandteile und sonstigen geschützten Elemente dieser Website und App bleiben – soweit nicht anders angegeben – unser Eigentum oder das Eigentum der jeweiligen Rechteinhaber. | All content, trademarks, texts, designs, software components, and other protected elements of this website and app remain - unless stated otherwise - our property or the property of the respective rights holders. |
| public_pages.terms | `public_pages.terms.liability.heading` | - | ## 8. Haftung | ## 8. Liability |
| public_pages.terms | `public_pages.terms.liability.body` | - | Wir haften nach Maßgabe der gesetzlichen Vorschriften.<br><br>Für automatisch oder unterstützend erzeugte Inhalte übernehmen wir keine Gewähr für Vollständigkeit, rechtliche Zulässigkeit, wirtschaftliche Eignung oder Fehlerfreiheit im Einzelfall. Nutzerinnen und Nutzer bleiben zur eigenständigen Prüfung verpflichtet. | We are liable in accordance with statutory provisions.<br><br>For automatically or supportively generated content, we do not guarantee completeness, legal permissibility, commercial suitability, or absence of errors in individual cases. Users remain obliged to conduct their own review. |
| public_pages.terms | `public_pages.terms.callout.title` | - | Wichtige Einordnung | Important context |
| public_pages.terms | `public_pages.terms.callout.body` | - | Cognitive Staffing unterstützt strukturierte Entscheidungen. Die Verantwortung für fachliche, rechtliche und organisatorische Freigaben verbleibt bei den nutzenden Personen bzw. Organisationen. | Cognitive Staffing supports structured decisions. Responsibility for professional, legal, and organizational approvals remains with the using persons or organizations. |
| public_pages.terms | `public_pages.terms.final.heading` | - | ## 9. Schlussbestimmungen | ## 9. Final provisions |
| public_pages.terms | `public_pages.terms.final.body` | - | Es gilt das Recht der Bundesrepublik Deutschland, soweit dem keine zwingenden gesetzlichen Vorschriften entgegenstehen.<br><br>Sollten einzelne Bestimmungen dieser Nutzungsbedingungen ganz oder teilweise unwirksam sein oder werden, bleibt die Wirksamkeit der übrigen Bestimmungen unberührt. | The law of the Federal Republic of Germany applies unless mandatory statutory provisions conflict with this.<br><br>If individual provisions of these terms of use are or become wholly or partly invalid, the validity of the remaining provisions remains unaffected. |
| public_pages.terms | `public_pages.terms.cta.title` | - | Kontakt bei Rückfragen | Contact for questions |
| public_pages.terms | `public_pages.terms.cta.body` | email | Bei Fragen zu diesen Nutzungsbedingungen erreichen Sie uns unter **{email}**. | For questions about these terms of use, you can reach us at **{email}**. |
| public_pages.cookies | `public_pages.cookies.page_title` | - | Cookie Policy/Settings | Cookie policy/settings |
| public_pages.cookies | `public_pages.cookies.title` | - | Cookie Policy & Einstellungen | Cookie policy and settings |
| public_pages.cookies | `public_pages.cookies.hero.eyebrow` | - | Cookies & Präferenzen | Cookies and preferences |
| public_pages.cookies | `public_pages.cookies.hero.lead` | - | Wir verwenden Cookies und vergleichbare Technologien nur im jeweils erforderlichen Umfang. Auf dieser Seite informieren wir darüber, welche Kategorien es gibt und wie Sie Ihre Einstellungen verwalten können. | We use cookies and comparable technologies only to the extent required. This page explains which categories exist and how you can manage your settings. |
| public_pages.cookies | `public_pages.cookies.notice.title` | - | Wichtiger Hinweis | Important note |
| public_pages.cookies | `public_pages.cookies.notice.body` | - | Aktueller Stand: Die App nutzt technische Laufzeit- und Spracheinstellungen. Marketing-Cookies, Werbetracker und externe Analytics-Cookies sind nicht Bestandteil dieses Setups. | Current status: The app uses technical runtime and language settings. Marketing cookies, advertising trackers, and external analytics cookies are not part of this setup. |
| public_pages.cookies | `public_pages.cookies.choices.heading` | - | ## Ihre Wahlmöglichkeiten | ## Your choices |
| public_pages.cookies | `public_pages.cookies.choices.body` | - | Sprache und UI-Präferenzen können Sie direkt in der Oberfläche anpassen. Browserseitige Speicherung können Sie zusätzlich über die Einstellungen Ihres Browsers löschen.<br><br>Technisch notwendige Speicherung wird genutzt, soweit sie für die sichere und funktionsfähige Bereitstellung der Website oder App erforderlich ist. | You can adjust language and UI preferences directly in the interface. Browser-side storage can also be cleared through your browser settings.<br><br>Technically necessary storage is used where required for secure and functional provision of the website or app. |
| public_pages.cookies | `public_pages.cookies.categories.necessary.title` | - | Technisch notwendig | Technically necessary |
| public_pages.cookies | `public_pages.cookies.categories.necessary.body` | - | Erforderlich für sicheren Betrieb, Navigation, Sitzungssteuerung, Sprachpersistenz und lokale Entwurfswiederherstellung. | Required for secure operation, navigation, session control, language persistence, and local draft recovery. |
| public_pages.cookies | `public_pages.cookies.categories.preferences.title` | - | Präferenzen | Preferences |
| public_pages.cookies | `public_pages.cookies.categories.preferences.body` | - | Speichert Sprache, Darstellungspräferenzen und Wizard-Einstellungen, damit die Oberfläche konsistent bleibt. | Stores language, display preferences, and wizard settings so the interface remains consistent. |
| public_pages.cookies | `public_pages.cookies.categories.statistics.title` | - | Statistik | Statistics |
| public_pages.cookies | `public_pages.cookies.categories.statistics.body` | - | Nicht aktiv im aktuellen Setup. Es werden keine externen Analytics-Cookies für Reichweitenmessung gesetzt. | Not active in the current setup. No external analytics cookies are set for traffic measurement. |
| public_pages.cookies | `public_pages.cookies.categories.external.title` | - | Externe Inhalte / Dienste | External content / services |
| public_pages.cookies | `public_pages.cookies.categories.external.body` | - | Nicht als Cookie- oder Tracking-Kategorie aktiv. KI-Funktionen nutzen serverseitig konfigurierte OpenAI-API-Aufrufe, sofern sie ausgelöst werden. | Not active as a cookie or tracking category. AI functions use server-side configured OpenAI API calls where triggered. |
| public_pages.cookies | `public_pages.cookies.consent.heading` | - | ## Einstellungen verwalten | ## Managing settings |
| public_pages.cookies | `public_pages.cookies.consent.body` | - | Die App setzt kein separates Consent-Banner für optionale Marketing- oder Analytics-Cookies ein, weil diese Kategorien im aktuellen Setup nicht aktiv sind.<br><br>Sprache und Wizard-Präferenzen können in der Oberfläche geändert werden. Lokale Browserdaten, etwa gespeicherte Sprache oder Entwurfswiederherstellungs-Metadaten, können über die Browser-Einstellungen gelöscht werden. | The app does not use a separate consent banner for optional marketing or analytics cookies because those categories are not active in the current setup.<br><br>Language and wizard preferences can be changed in the interface. Local browser data, such as stored language or draft-recovery metadata, can be cleared through browser settings. |
| public_pages.cookies | `public_pages.cookies.transparency.heading` | - | ## Transparenz | ## Transparency |
| public_pages.cookies | `public_pages.cookies.transparency.body` | - | Die aktuelle Website nutzt Streamlit-Laufzeitmechanismen, Session-State, Local Storage für Sprache und sichere Entwurfswiederherstellung sowie ein SameSite-Lax-Sprachcookie als Fallback.<br><br>Gespeicherte Entwurfs-Metadaten enthalten keinen vollständigen Entwurf; der dauerhafte Produktvertrag bleibt der manuelle JSON-Entwurf. | The current website uses Streamlit runtime mechanisms, session state, local storage for language and safe draft recovery, and a SameSite=Lax language cookie as fallback.<br><br>Stored draft metadata does not contain the full draft; the durable product contract remains the manual JSON draft. |
| public_pages.cookies | `public_pages.cookies.current_setup.heading` | - | ## Aktueller Technologieeinsatz | ## Current technology use |
| public_pages.cookies | `public_pages.cookies.current_setup.body` | - | - Spracheinstellung: Local Storage und SameSite-Lax-Cookie als Fallback,<br>- Wizard- und UI-Präferenzen: Streamlit Session-State,<br>- sichere Entwurfswiederherstellung: Local-Storage-Metadaten bei ungesichertem Fortschritt,<br>- Marketing-Cookies: nicht aktiv,<br>- externe Analytics-Cookies: nicht aktiv. | - Language setting: local storage and SameSite=Lax cookie fallback,<br>- wizard and UI preferences: Streamlit session state,<br>- safe draft recovery: local-storage metadata while unsaved progress exists,<br>- marketing cookies: not active,<br>- external analytics cookies: not active. |
| public_pages.cookies | `public_pages.cookies.cta.title` | - | Fragen zu Cookie-Einstellungen | Questions about cookie settings |
| public_pages.cookies | `public_pages.cookies.cta.body` | privacy_email | Bei Rückfragen zu eingesetzten Technologien oder Präferenzen erreichen Sie uns unter **{privacy_email}**. | For questions about technologies or preferences used, you can reach us at **{privacy_email}**. |
| public_pages.accessibility | `public_pages.accessibility.title` | - | Erklärung zur Barrierefreiheit | Accessibility statement |
| public_pages.accessibility | `public_pages.accessibility.hero.eyebrow` | - | Barrierefreiheit | Accessibility |
| public_pages.accessibility | `public_pages.accessibility.hero.lead` | - | Wir möchten unsere Website und digitalen Inhalte möglichst barrierearm und gut zugänglich gestalten. Dabei orientieren wir uns an anerkannten Standards der digitalen Barrierefreiheit und entwickeln die Nutzbarkeit fortlaufend weiter. | We want to make our website and digital content as accessible and usable as possible. We orient ourselves toward recognized digital accessibility standards and continuously improve usability. |
| public_pages.accessibility | `public_pages.accessibility.notice.title` | - | Rechtliche Einordnung | Legal context |
| public_pages.accessibility | `public_pages.accessibility.notice.body` | - | Diese Erklärung beschreibt den aktuellen Anspruch an Zugänglichkeit und den bekannten Verbesserungsbedarf. Ob BITV 2.0, BFSG oder weitere Vorgaben unmittelbar anwendbar sind, hängt vom konkreten Betreiber- und Angebotskontext ab. | This statement describes the current accessibility standard and known improvement areas. Whether BITV 2.0, BFSG, or further requirements apply directly depends on the specific operator and offering context. |
| public_pages.accessibility | `public_pages.accessibility.status.heading` | - | ## Stand der Vereinbarkeit | ## Compliance status |
| public_pages.accessibility | `public_pages.accessibility.status.body` | - | Diese Website ist derzeit **teilweise barrierefrei**.<br><br>Wir arbeiten fortlaufend daran, Nutzbarkeit, Verständlichkeit und technische Zugänglichkeit weiter zu verbessern. | This website is currently **partly accessible**.<br><br>We continuously work to further improve usability, clarity, and technical accessibility. |
| public_pages.accessibility | `public_pages.accessibility.standard.heading` | - | ## Unser Anspruch | ## Our standard |
| public_pages.accessibility | `public_pages.accessibility.standard.body` | - | Wir möchten, dass Inhalte möglichst verständlich, klar strukturiert und in unterschiedlichen Nutzungssituationen zugänglich sind.<br><br>Dazu orientieren wir uns insbesondere an:<br>- klarer Informationsarchitektur,<br>- guter Lesbarkeit,<br>- kontrastbewusster Gestaltung,<br>- konsistenter Navigation,<br>- schrittweiser Verbesserung interaktiver Komponenten. | We want content to be as understandable, clearly structured, and accessible in different usage situations as possible.<br><br>In particular, we orient ourselves toward:<br>- clear information architecture,<br>- good readability,<br>- contrast-aware design,<br>- consistent navigation,<br>- step-by-step improvement of interactive components. |
| public_pages.accessibility | `public_pages.accessibility.implemented.heading` | - | ## Bereits umgesetzte Maßnahmen | ## Measures already implemented |
| public_pages.accessibility | `public_pages.accessibility.implemented.body` | - | - klare Überschriften- und Abschnittslogik,<br>- kompakte, möglichst verständliche Texte,<br>- konsistente Navigationsmuster,<br>- fortlaufende Überprüfung von Kontrasten und Darstellungslogik,<br>- laufende Optimierung der Bedienbarkeit in dynamischen Oberflächen. | - clear heading and section logic,<br>- compact, understandable texts wherever possible,<br>- consistent navigation patterns,<br>- ongoing review of contrast and display logic,<br>- continuous optimization of operability in dynamic interfaces. |
| public_pages.accessibility | `public_pages.accessibility.barriers.heading` | - | ## Noch bestehende Barrieren | ## Remaining barriers |
| public_pages.accessibility | `public_pages.accessibility.barriers.body` | - | Trotz unserer Bemühungen können derzeit noch Einschränkungen bestehen, insbesondere:<br>- bei einzelnen interaktiven Komponenten,<br>- bei Tastaturbedienung und Fokusführung,<br>- bei dynamisch eingeblendeten oder generierten Inhalten,<br>- bei Dokumenten oder exportierten Dateien,<br>- bei komplexeren visuellen oder datengetriebenen Darstellungen. | Despite our efforts, limitations may still exist at present, in particular:<br>- for individual interactive components,<br>- for keyboard operation and focus guidance,<br>- for dynamically displayed or generated content,<br>- for documents or exported files,<br>- for more complex visual or data-driven displays. |
| public_pages.accessibility | `public_pages.accessibility.feedback.heading` | - | ## Feedback und Kontakt | ## Feedback and contact |
| public_pages.accessibility | `public_pages.accessibility.feedback.body` | accessibility_email, email | Wenn Sie Barrieren auf unserer Website feststellen oder Inhalte in einer besser zugänglichen Form benötigen, kontaktieren Sie uns bitte:<br><br>**E-Mail:** {accessibility_email}  <br>**Allgemeiner Kontakt:** {email} | If you notice barriers on our website or need content in a more accessible form, please contact us:<br><br>**Email:** {accessibility_email}  <br>**General contact:** {email} |
| public_pages.accessibility | `public_pages.accessibility.enforcement.heading` | - | ## Durchsetzungs- oder Schlichtungshinweise | ## Enforcement or mediation information |
| public_pages.accessibility | `public_pages.accessibility.enforcement.body` | - | Soweit gesetzlich erforderlich oder im konkreten Anwendungsfall vorgesehen, können ergänzende Hinweise auf zuständige Schlichtungs- oder Beschwerdestellen aufgenommen werden. | Where legally required or provided for in the specific use case, additional references to competent mediation or complaint bodies can be added. |
| public_pages.accessibility | `public_pages.accessibility.cta.title` | - | Barrieren melden | Report barriers |
| public_pages.accessibility | `public_pages.accessibility.cta.body` | accessibility_email | Wir freuen uns über konkrete Hinweise, damit wir die Zugänglichkeit unserer Inhalte gezielt weiter verbessern können. Kontakt: **{accessibility_email}** | We welcome specific feedback so that we can keep improving the accessibility of our content in a targeted way. Contact: **{accessibility_email}** |
| public_pages.contact | `public_pages.contact.title` | - | Kontakt | Contact |
| public_pages.contact | `public_pages.contact.hero.eyebrow` | - | Kontakt & Demo | Contact and demo |
| public_pages.contact | `public_pages.contact.hero.lead` | - | Sie möchten Cognitive Staffing kennenlernen, eine Demo anfragen oder über einen konkreten Einsatzfall sprechen? Dann freuen wir uns auf Ihre Nachricht. | Would you like to get to know Cognitive Staffing, request a demo, or discuss a specific use case? We look forward to your message. |
| public_pages.contact | `public_pages.contact.meta` | - | Für Unternehmen, HR, Recruiting, IT und Produktverantwortliche | For companies, HR, recruiting, IT, and product owners |
| public_pages.contact | `public_pages.contact.cards.decision_makers.title` | - | Unternehmen & Entscheider | Companies and decision makers |
| public_pages.contact | `public_pages.contact.cards.decision_makers.body` | - | Sie möchten Ihr Recruiting-Briefing professionalisieren, Reibung im Recruiting reduzieren und bessere Entscheidungen früher im Prozess ermöglichen. | You want to professionalize the recruiting brief, reduce friction in recruiting, and enable better decisions earlier in the process. |
| public_pages.contact | `public_pages.contact.cards.hr.title` | - | HR & Recruiting | HR and recruiting |
| public_pages.contact | `public_pages.contact.cards.hr.body` | - | Sie interessieren sich für klarere Übergaben, bessere Suchprofile, stärkere Interviewvorbereitung und wiederverwendbare Recruiting-Unterlagen. | You are interested in clearer handovers, better search profiles, stronger interview preparation, and reusable recruiting outputs. |
| public_pages.contact | `public_pages.contact.cards.it.title` | - | IT & Produktverantwortliche | IT and product owners |
| public_pages.contact | `public_pages.contact.cards.it.body` | - | Sie möchten mehr über Architektur, Sicherheit, Integrationsfähigkeit, On-Prem-Optionen oder lokale LLM-Szenarien erfahren. | You want to learn more about architecture, security, integration capability, on-prem options, or local LLM scenarios. |
| public_pages.contact | `public_pages.contact.reach.heading` | - | ## So erreichen Sie uns | ## How to reach us |
| public_pages.contact | `public_pages.contact.reach.body` | city, country, email, legal_entity, phone, postal_code, street | **E-Mail**  <br>{email}<br><br>**Telefon**  <br>{phone}<br><br>**Adresse**  <br>{legal_entity}  <br>{street}  <br>{postal_code} {city}  <br>{country} | **Email**  <br>{email}<br><br>**Phone**  <br>{phone}<br><br>**Address**  <br>{legal_entity}  <br>{street}  <br>{postal_code} {city}  <br>{country} |
| public_pages.contact | `public_pages.contact.privacy_notice.title` | - | Hinweis zum Datenschutz | Privacy note |
| public_pages.contact | `public_pages.contact.privacy_notice.body` | - | Bitte senden Sie uns über das Kontaktformular oder per E-Mail keine besonders sensiblen personenbezogenen Daten, sofern dies nicht erforderlich und abgestimmt ist. | Please do not send us especially sensitive personal data through the contact form or by email unless this is necessary and agreed. |
| public_pages.contact | `public_pages.contact.form.heading` | - | ## Demo oder Rückruf anfragen | ## Request a demo or callback |
| public_pages.contact | `public_pages.contact.form.name` | - | Name | Name |
| public_pages.contact | `public_pages.contact.form.company` | - | Unternehmen | Company |
| public_pages.contact | `public_pages.contact.form.email` | - | E-Mail | Email |
| public_pages.contact | `public_pages.contact.form.topic` | - | Anliegen | Topic |
| public_pages.contact | `public_pages.contact.form.topic_options.demo` | - | Demo anfragen | Request a demo |
| public_pages.contact | `public_pages.contact.form.topic_options.product` | - | Produktinformationen | Product information |
| public_pages.contact | `public_pages.contact.form.topic_options.technical` | - | Technische Fragen | Technical questions |
| public_pages.contact | `public_pages.contact.form.topic_options.partnership` | - | Partnerschaft / Zusammenarbeit | Partnership / collaboration |
| public_pages.contact | `public_pages.contact.form.topic_options.other` | - | Sonstiges | Other |
| public_pages.contact | `public_pages.contact.form.message` | - | Nachricht | Message |
| public_pages.contact | `public_pages.contact.form.message_placeholder` | - | Beschreiben Sie kurz Ihren Anwendungsfall oder Ihr Anliegen. | Briefly describe your use case or request. |
| public_pages.contact | `public_pages.contact.form.submit` | - | Anfrage vorbereiten | Prepare request |
| public_pages.contact | `public_pages.contact.form.success` | - | Die Anfrage ist vorbereitet. Öffnen Sie Ihre E-Mail-App, prüfen Sie die Nachricht und senden Sie sie direkt ab. | The request is prepared. Open your email app, review the message, and send it directly. |
| public_pages.contact | `public_pages.contact.form.email_cta` | - | In E-Mail-App öffnen | Open in email app |
| public_pages.contact | `public_pages.contact.form.email_subject` | topic | Kontaktanfrage: {topic} | Contact request: {topic} |
| public_pages.contact | `public_pages.contact.form.summary` | company, email, message, name, topic | Name: {name}<br>Unternehmen: {company}<br>E-Mail: {email}<br>Anliegen: {topic}<br><br>Nachricht:<br>{message} | Name: {name}<br>Company: {company}<br>Email: {email}<br>Topic: {topic}<br><br>Message:<br>{message} |
| public_pages.contact | `public_pages.contact.cta.title` | - | Direkter Draht | Direct line |
| public_pages.contact | `public_pages.contact.cta.body` | email | Für schnelle Rückfragen erreichen Sie uns direkt unter **{email}**. | For quick questions, you can reach us directly at **{email}**. |
| public_pages.contact | `public_pages.contact.policy_links.heading` | - | ## Rechtliches & Richtlinien | ## Legal and policies |
| public_pages.contact | `public_pages.contact.policy_links.imprint` | - | Impressum | Imprint |
| public_pages.contact | `public_pages.contact.policy_links.privacy` | - | Datenschutzrichtlinie | Privacy policy |
| public_pages.contact | `public_pages.contact.policy_links.terms` | - | Nutzungsbedingungen | Terms of use |
| public_pages.contact | `public_pages.contact.policy_links.cookies` | - | Cookie Policy Settings | Cookie policy settings |
| public_pages.contact | `public_pages.contact.policy_links.accessibility` | - | Erklärung zur Barrierefreiheit | Accessibility statement |

## German-Source Translation Entries

These entries are consumed by `t(text)` when the active UI language is English. The German source copy itself is the lookup key.

| Category | German source copy | EN |
|---|---|---|
| wizard.step | Einleitung | Introduction |
| wizard.step | Start | Start |
| wizard.step | Unternehmen | Company |
| wizard.step | Rolle & Aufgaben | Role & tasks |
| wizard.step | Skills & Anforderungen | Skills & requirements |
| wizard.step | Benefits & Rahmenbedingungen | Benefits & conditions |
| wizard.step | Interviewprozess | Interview process |
| wizard.step | Zusammenfassung | Summary |
| ui.mode | schnell | quick |
| ui.mode | ausführlich | standard |
| ui.mode | vollumfänglich | full |
| ui.mode | Schnell | Quick |
| ui.mode | Ausführlich | Standard |
| ui.mode | Vollumfänglich | Full |
| common | niedrig | low |
| common | hoch | high |
| common | locker | loose |
| common | ausgewogen | balanced |
| common | streng | strict |
| ui.mode | standard | standard |
| common | ja | yes |
| common | nein | no |
| common | Später | Later |
| common | Nicht übernommen | Not applied |
| common | Prozess | Process |
| common | Sprache | Language |
| common | Sprache für Vorschläge | Language for suggestions |
| common | Alternative Sprache | Fallback language |
| common | Unsere Kompetenzen | Our competencies |
| common | Über Cognitive Staffing | About Cognitive Staffing |
| common | Über uns | About us |
| public.legal | Impressum | Imprint |
| public.legal | Impressum (Prüfung erforderlich) | Imprint (review required) |
| public.legal | Datenschutzrichtlinie | Privacy policy |
| public.legal | Nutzungsbedingungen | Terms of use |
| public.legal | Cookie Policy/Settings | Cookie policy/settings |
| public.legal | Cookie Policy & Einstellungen | Cookie policy & settings |
| public.legal | Erklärung zur Barrierefreiheit | Accessibility statement |
| common | Kontakt | Contact |
| common | Kontakt & Demo | Contact & demo |
| public.legal | Rechtliches | Legal |
| public.legal | Rechtliche Information | Legal information |
| public.legal | Datenschutz | Privacy |
| public.legal | Barrierefreiheit | Accessibility |
| public.legal | Cookies & Präferenzen | Cookies & preferences |
| common | Wichtiger Hinweis | Important note |
| common | Hinweis | Note |
| common | AI-gestützte Kompetenz- und Matching-Workflows | AI-supported competency and matching workflows |
| public.legal | Rechtliche Seite · Prüfung erforderlich | Legal page · review required |
| public.legal | Diese Seite ist erst nach fachlicher und rechtlicher Prüfung verbindlich. | This page is binding only after subject-matter and legal review. |
| common | ⚠️ **Erforderliche Fachangaben fehlen** | ⚠️ **Required subject-matter details are missing** |
| common | Wie weit möchten Sie ins Detail gehen? | How much detail do you want? |
| common | Detailgrad aktiv: **Schnell** (`quick`) | Active detail level: **Quick** (`quick`) |
| common | Detailgrad aktiv: **Ausführlich** (`standard`) | Active detail level: **Standard** (`standard`) |
| common | Detailgrad aktiv: **Vollumfänglich** (`expert`) | Active detail level: **Full** (`expert`) |
| wizard.intake | Der Modus steuert, wie viele Fragen im aktuellen Schritt sichtbar sind. | The mode controls how many questions are visible in the current step. |
| common | Antwortmodus | Response mode |
| common | Informationstiefe | Information depth |
| common | Confidence-Schwelle für Treffer | Confidence threshold for matches |
| common | PII-Reduktion | PII reduction |
| common | Details standardmäßig öffnen | Open details by default |
| wizard.intake | Details kompakt anzeigen | Show details compactly |
| common | Präferenz-Center | Preference center |
| common | Globale Einstellungen gelten wizard-weit. | Global settings apply across the wizard. |
| common | Advanced / Bestehende Detail-Einstellungen | Advanced / existing detail settings |
| common | ← Zurück zum Wizard | Back to wizard |
| common | Globale Steuerung für den aktuellen Wizard-Kontext. | Global controls for the current wizard context. |
| common | Seiten | Pages |
| common | Reset Vacancy | Reset vacancy |
| common | ← Zurück | Back |
| common | Weiter → | Next |
| wizard.intake | Bitte zuerst im Start-Schritt eine Analyse durchführen. | Please run an analysis in the Start step first. |
| common | Zur Startseite | Go to start page |
| common | Zum Start | Go to Start |
| summary.artifact | Stellenanzeige einlesen und Intake starten | Import job ad and start intake |
| wizard.intake | Anzeige hochladen oder einfügen | Upload or paste job ad |
| common | Vakanzanforderungen präzise erfassen | Capture vacancy requirements precisely |
| common | Bevor Recruiting beginnt, muss klar sein, welche Person wirklich gesucht wird. | Before recruiting begins, it must be clear which person is really needed. |
| common | Aus langjähriger Erfahrung in der Personalvermittlung zeigt sich immer wieder: Essentielle Informationen zu einer Vakanz ändern sich oft erst im laufenden Bewerbungsprozess, werden zu spät sichtbar oder fehlen vollständig. Das kann Abstimmungsschleifen, Fehlbesetzungen und hohe Folgekosten verursachen. | Years of recruiting experience show the same pattern again and again: essential information about a vacancy often changes during the application process, appears too late, or is missing entirely. This can create alignment loops, hiring mistakes, and high downstream costs. |
| summary.artifact | Gerade in großen Unternehmen werden regelmäßig ähnliche Qualitäten gesucht und auf Basis derselben Stellenanzeige ausgeschrieben. Die individuellen Charakteristika einer konkreten Vakanz bleiben dabei häufig zu unscharf. | Especially in large organizations, similar qualities are often needed and advertised from the same job ad. The individual characteristics of a specific vacancy often remain too vague. |
| esco | Diese App fokussiert ausschließlich den ersten Schritt jedes Recruiting-Prozesses: Der fachliche Vorgesetzte definiert, welchen Mitarbeiter er sucht. Diverse Funktionen helfen dabei, mit möglichst wenig Aufwand ein umfassendes Bild der Stelle zu erstellen. Dafür nutzt die App die europäische Berufs- und Skill-Taxonomie ESCO sowie die OpenAI-API, um den Informationsgewinnungsprozess dynamisch an die individuellen Bedürfnisse Ihrer Vakanz anzupassen. | This app focuses exclusively on the first step of every recruiting process: the hiring manager defines which employee they are looking for. A set of focused functions helps create a comprehensive picture of the role with as little effort as possible. To do that, the app uses the European occupation and skills taxonomy ESCO as well as the OpenAI API to dynamically adapt the information-gathering process to the individual needs of your vacancy. |
| common | Bereit, die Anforderungen Ihrer Vakanz richtig kennenzulernen? Probieren Sie es aus. | Ready to properly understand the requirements of your vacancy? Try it out. |
| common | Das Eisberg-Modell zeigt, welche sichtbaren und verdeckten Informationen ein gutes Recruiting-Briefing zusammenführt. | The iceberg model shows which visible and hidden information a strong recruiting brief brings together. |
| wizard.intake | Von der Jobspec zum klaren Recruiting-Bild. | From job spec to a clear recruiting picture. |
| summary.artifact | Die App liest eine Stellenanzeige ein, erkennt den fachlichen Kontext und fragt nur dort nach, wo Informationen für gute Recruiting-Entscheidungen fehlen. | The app reads a job ad, detects the professional context, and only asks where information is missing for good recruiting decisions. |
| common | Warum der Intake mehr sieht | Why the intake sees more |
| common | Was passiert danach? | What happens next? |
| common | Nach dem Start | After starting |
| wizard.intake | Nach dem Klick auf "Analyse starten" | After clicking "Start analysis" |
| common | Text verstehen | Understand text |
| common | Upload oder Freitext wird gelesen und in ein sauberes Rollenprofil überführt. | Upload or free text is read and converted into a clean role profile. |
| common | Beruf verankern | Anchor occupation |
| esco | Die App sucht den passenden ESCO-Beruf als gemeinsame Referenz. | The app searches for the matching ESCO occupation as a shared reference. |
| wizard.intake | Fragen priorisieren | Prioritize questions |
| common | Nur fehlende oder unsichere Punkte werden für den Wizard vorbereitet. | Only missing or uncertain points are prepared for the wizard. |
| common | Weiterverarbeiten | Continue processing |
| summary.artifact | Aufgaben, Skills, Benefits, Interview und Summary-Unterlagen bauen darauf auf. | Tasks, skills, benefits, interview, and summary outputs build on it. |
| common | Ergebnis: weniger manuelle Sortierarbeit und eine bessere Grundlage für alle Recruiting-Aktivitäten. | Result: less manual sorting and a better foundation for all recruiting activities. |
| common | Mehr Kontext: | More context: |
| esco | Was ist ESCO? | What is ESCO? |
| common | Was bedeutet RAG? | What does RAG mean? |
| common | Warum Recruiting-Briefing? | Why the recruiting brief? |
| common | Kurzer Kontext, warum die App nicht nur sichtbare Anforderungen, sondern auch Lücken und implizite Bedarfstreiber strukturiert. | Brief context on why the app structures not only visible requirements, but also gaps and implicit demand drivers. |
| public.legal | Datenschutz und Kontrolle | Privacy and control |
| wizard.intake | Weniger Rückfragen | Fewer follow-up questions |
| common | Der Wizard fragt gezielt nach, statt ein starres Formular abzuarbeiten. | The wizard asks targeted questions instead of running through a rigid form. |
| common | Klarer Rollenanker | Clear role anchor |
| esco | Jobtitel werden mit ESCO abgeglichen, damit alle Folgeschritte denselben Berufskontext nutzen. | Job titles are matched with ESCO so every later step uses the same occupation context. |
| common | Direkt nutzbare Recruiting-Unterlagen | Ready-to-use recruiting outputs |
| summary.artifact | Aus dem Intake entstehen strukturierte Informationen für Recruiting, Hiring-Team und Summary. | The intake produces structured information for recruiting, the hiring team, and the summary. |
| common | 1. Beruf eindeutig verankern | 1. Anchor the occupation clearly |
| esco | Die Rolle wird auf einen klaren ESCO-Beruf gemappt, damit alle Folgeschritte denselben Kontext nutzen. | The role is mapped to a clear ESCO occupation so all later steps use the same context. |
| common | 2. Anforderungen strukturieren | 2. Structure requirements |
| domain | Skills, Aufgaben und Muss-/Kann-Kriterien werden normalisiert und in einen nutzbaren Plan überführt. | Skills, tasks, and must-have/nice-to-have criteria are normalized into a usable plan. |
| summary.artifact | 3. Recruiting-Unterlagen erzeugen | 3. Generate recruiting outputs |
| common | Die App erstellt belastbare Texte, Zusammenfassungen und Recruiting-Unterlagen für Recruiting und Hiring-Team. | The app creates robust text, summaries, and recruiting outputs for recruiting and the hiring team. |
| wizard.intake | Vor der Verarbeitung können sensible personenbezogene Angaben optional reduziert werden. Ziel ist ein datensparsames, nachvollziehbares Recruiting-Briefing. | Before processing, sensitive personal information can optionally be reduced. The goal is a data-minimizing, traceable recruiting brief. |
| common | Start ist gesperrt, bis die Einwilligung bestätigt wurde. Start is blocked until consent is confirmed. | Start is blocked until consent is confirmed. |
| common | Wenn für eure Organisation Designated Content freigegeben ist, können diese Inhalte von OpenAI zu Entwicklungszwecken genutzt werden (inkl. Training, Evaluierung, Tests). Ihr müsst Endnutzende informieren und – falls erforderlich – Einwilligungen einholen. | If designated content is enabled for your organization, this content may be used by OpenAI for development purposes, including training, evaluation, and testing. You must inform end users and obtain consent where required. |
| common | Offen kommunizierbar | Can be communicated openly |
| common | Intern begrenzt | Limited internally |
| common | Vertraulich / neutralisieren | Confidential / neutralize |
| common | Noch unklar | Still unclear |
| common | Ersatz / Backfill | Replacement / backfill |
| common | Wachstum | Growth |
| common | Neue Rolle / Neuaufbau | New role / build-up |
| common | Interne Nachfolge | Internal succession |
| common | Vertrauliche Suche | Confidential search |
| common | Planbar | Plannable |
| common | Relevant | Relevant |
| common | Dringend | Urgent |
| common | Kritisch / sofort | Critical / immediate |
| common | Intern kalibriert | Internally calibrated |
| common | Teilweise kalibriert | Partly calibrated |
| common | Noch unscharf | Still vague |
| common | Auswahl übernehmen | Apply selection |
| common | Auswahl verwerfen | Discard selection |
| common | Legacy-URI migrieren | Migrate legacy URI |
| esco | ESCO-Konfiguration aktualisiert. Cache wurde invalidiert. | ESCO configuration updated. Cache was invalidated. |
| wizard.intake | Analyse starten | Start analysis |
| wizard.intake | Analyseergebnis | Analysis result |
| esco | Berufsabgleich | Occupation matching |
| esco | Berufsabgleich bestätigen | Confirm occupation match |
| wizard.intake | Quelle bearbeiten | Edit source |
| wizard.intake | Erkannte Angaben prüfen | Review detected information |
| wizard.intake | Angaben übernehmen | Apply information |
| wizard.intake | Angaben übernommen. | Information applied. |
| common | Ein paar Informationen vorab | A few details first |
| common | Unternehmenswebsite | Company website |
| wizard.intake | Hinweise aus der Website-Analyse | Insights from website analysis |
| common | Strukturierter Kontext | Structured context |
| common | Unternehmensprofil | Company profile |
| common | Team & Reporting | Team & reporting |
| common | Arbeitsmodell | Work model |
| common | Non-negotiables & Compliance | Non-negotiables & compliance |
| common | Outcome & Scope | Outcome & scope |
| common | Priorisierung | Prioritization |
| common | Erfolg und Entscheidungsspielraum | Success and decision scope |
| common | Reiseprofil | Travel profile |
| common | Auswirkung auf Prognose | Impact on forecast |
| domain | Skills präzisieren und priorisieren | Clarify and prioritize skills |
| common | Weitere AI-Vorschläge | More AI suggestions |
| common | AI-Vorschläge | AI suggestions |
| common | AI-Vorschläge ergänzen | Add AI suggestions |
| domain | Erkannte und ausgewählte Benefits | Detected and selected benefits |
| common | Einflussfaktoren | Influence factors |
| common | Details zu Einflussfaktoren | Details on influence factors |
| domain | Variable Vergütung | Variable compensation |
| common | Arbeitszeit, Schicht und Ausgleich | Working time, shifts, and compensation |
| common | Vertrags- und Offer-Komponenten | Contract and offer components |
| common | Interne Rollen und Ansprechpartner | Internal roles and contacts |
| summary.artifact | Interviewstufen | Interview stages |
| common | Stage Owner | Stage owner |
| common | Candidate Update SLA | Candidate update SLA |
| common | Assessment Evidence | Assessment evidence |
| common | Scorecard | Scorecard |
| common | Stage & Evaluation | Stage & evaluation |
| summary.artifact | Interviewprozess definieren | Define interview process |
| common | Candidate Communication | Candidate communication |
| common | Readiness-Übersicht | Readiness overview |
| summary.artifact | Unterlagenübersicht | Recruiting outputs overview |
| wizard.intake | Quellen & Details prüfen | Review sources and details |
| summary.artifact | Recruiting Brief | Recruiting brief |
| wizard.intake | Frageblöcke | Question blocks |
| common | Bewertungsrubrik | Evaluation rubric |
| common | Empfehlungsoptionen | Recommendation options |
| common | Kompetenzen validieren | Validate competencies |
| summary.artifact | Debrief-Fragen | Debrief questions |
| common | Klauseln | Clauses |
| common | Keine Vorschläge. | No suggestions. |
| common | Keine Einträge. | No entries. |
| common | Keine Treffer für die aktuellen Filter. | No matches for the current filters. |
| wizard.intake | Keine sichtbaren Fragen in diesem Schritt. | No visible questions in this step. |
| common | Antworten übernehmen | Apply answers |
| common | Antworten übernommen. | Answers applied. |
| common | Übernehmen | Apply |
| common | Weitere Sprache hinzufügen | Add another language |
| esco | Taxonomie laden | Load taxonomy |
| common | Top-Treffer wurde per Enter übernommen. | Top match was applied via Enter. |
| esco | Referenzberuf auswählen | Select reference occupation |
| common | Kontextrolle auswählen | Select context role |
| esco | Suchbegriff für Berufsabgleich | Search term for occupation matching |
| common | Suchbegriff für Kontextrolle | Search term for context role |
| esco | Bestätigter Referenzberuf | Confirmed reference occupation |
| esco | Bestätigte ESCO-Auswahl | Confirmed ESCO selection |
| common | Ausgewählte Kontextrolle | Selected context role |
| esco | Als Kontextanker hinzufügen | Add as context anchor |
| esco | Kontextanker hinzugefügt. | Context anchor added. |
| esco | Ohne bestätigten Referenzberuf fortfahren | Continue without a confirmed reference occupation |
| common | Später erneut versuchen | Try again later |
| common | URI kopieren | Copy URI |
| common | URI zum Kopieren eingeblendet. | URI shown for copying. |
| common | Mehr Details | More details |
| esco | Warum Berufsabgleich? | Why occupation matching? |
| common | Warum dieser Vorschlag? | Why this suggestion? |
| common | Geladene Occupation-Titelvarianten | Loaded occupation title variants |
| wizard.intake | Nur verfügbare Felder anzeigen | Show available fields only |
| common | Portal öffnen | Open portal |

## Phrase Replacement Entries

These replacements are applied after exact `t(text)` lookup misses. They are useful for generated labels, but new UI copy should prefer explicit Locale keys or exact source-copy mappings.

| German phrase | EN phrase |
|---|---|
| Globale Voreinstellung für Detailgruppen in allen Wizard-Schritten. | Global default for detail groups in all wizard steps. |
| Schritt-spezifische Anzeige: Aktiv hält Detailgruppen standardmäßig geschlossen. | Step-specific display: enabled keeps detail groups closed by default. |
| Deaktiviert öffnet Detailgruppen standardmäßig. | Disabled opens detail groups by default. |
| Bitte explizit auswählen. | Please choose explicitly. |
| Legacy-URI erkannt. | Legacy URI detected. |
| Bitte migrieren, damit aktuelle ESCO-Daten konsistent geladen werden. | Please migrate so current ESCO data can be loaded consistently. |
| Nicht angegeben | Not specified |
| Offen | Open |
| Teilweise | Partial |
| Vollständig | Complete |
| beantwortet | answered |
| Fehlt (essentiell) | Missing (essential) |
| Sicherheit | Confidence |
| Technische Details | Technical details |
| Vorschläge | Suggestions |
| Ausgewählt | Selected |
| Ausgewählte | Selected |
| Ausgewählter | Selected |
| Noch keine | No |
| Keine | No |
| Berufsabgleich | Occupation matching |
| Analyse läuft | Analysis running |
| Analyse abgeschlossen | Analysis complete |
| Informationen extrahiert und Fragebogen erzeugt | information extracted and questionnaire generated |
| Mindestens ein Ergebnis wurde aus dem Cache geladen | At least one result was loaded from cache |
| Die Quelle ist sehr kurz | The source is very short |
| Die Extraktion kann unvollstaendig sein | Extraction may be incomplete |
| Datei bereit | File ready |
| Unbekannt | Unknown |
| Extraktion fehlgeschlagen | Extraction failed |
| Zeichen | Characters |
| Quelle | Source |
| Upload | Upload |
| Text | Text |
| Manuell erfasste URL | Manually entered URL |
| Website-Analyse | website analysis |
| Arbeitsmodell | Work model |
| Aufgaben | tasks |
| Skills | skills |
| Benefits | benefits |
| Fragen | questions |
| Antworten | answers |
| Essentials offen | Open essentials |
| Gruppenstatus | Group status |
| vollständig beantwortet | fully answered |
| vollständig | complete |
| offen | open |
| weitere | more |
| Rolle | Role |
| Zielregionen | Target regions |
| Primäre Query | Primary query |
| Beobachtbare Evidenz | Observable evidence |
| Skala | Scale |
| Keine kritischen Lücken erkannt | No critical gaps detected |
| Kritische Lücken | Critical gaps |
| Bereit | Ready |
| Erfüllt | Met |
| Ungültig | Invalid |
| ungültig | invalid |
| Offene Lücken | Open gaps |
| Nächster verfügbarer Schritt | Next available step |

## Gap Backlog: High-Confidence Visible UI Copy

This table is a migration backlog and the explicit allowlist baseline used by `scripts/check_repo_hygiene.py` for already-known raw Wizard UI copy. It is generated from direct Streamlit/helper string literals that are not already Locale keys, exact German-source mappings, or phrase replacements. It intentionally excludes prompts, schemas, logs, tests, CSS, and dynamic JSON content.

Priority guide: `P1` visible wizard workflow copy, `P2` shared/public/helper copy, `P3` legacy/debug/preview copy.

| Priority | Recommended future key prefix | File:line | Current copy |
|---|---|---|---|
| P1 | `common` | `wizard_pages/base.py:1002` | Abschnitte: {...}/{...} geklärt |
| P1 | `common` | `wizard_pages/base.py:1006` | Missing: {...} |
| P1 | `common` | `wizard_pages/base.py:1311` | Mehrere mögliche Zielkonzepte gefunden. Bitte explizit auswählen. |
| P1 | `common` | `wizard_pages/base.py:1328` | Migrationsziel auswählen |
| P1 | `common` | `wizard_pages/base.py:1343` | Legacy-URI wurde auf eine kanonische ESCO-URI migriert. |
| P1 | `common` | `wizard_pages/base.py:1345` | Die Auswahl konnte nicht übernommen werden. |
| P1 | `common` | `wizard_pages/base.py:1349` | Migrationsauswahl wurde verworfen. |
| P1 | `common` | `wizard_pages/base.py:1366` | Migration aktuell nicht möglich: {...} |
| P1 | `common` | `wizard_pages/base.py:1374` | Keine kanonische URI im Conversion-Resultat gefunden. |
| P1 | `common` | `wizard_pages/base.py:1383` | Legacy-URI wurde auf eine kanonische ESCO-URI migriert. |
| P1 | `common` | `wizard_pages/base.py:1385` | Keine aktualisierbare ESCO-Auswahl gefunden. |
| P1 | `common` | `wizard_pages/base.py:1391` | Bitte wählen Sie ein Zielkonzept für die Migration aus. |
| P1 | `common` | `wizard_pages/base.py:1407` | ESCO Release Lane |
| P1 | `common` | `wizard_pages/base.py:1419` | Obsolete anzeigen (Debug only) |
| P1 | `common` | `wizard_pages/base.py:1474` | ESCO Obsolete-Modus ist aktiv. Ergebnisse können veraltete Konzepte enthalten. |
| P1 | `common` | `wizard_pages/base.py:1482` | Legacy-URI erkannt. Bitte migrieren, damit aktuelle ESCO-Daten konsistent geladen werden. |
| P1 | `common` | `wizard_pages/base.py:1486` | Legacy-URI Details |
| P1 | `common` | `wizard_pages/base.py:2105` | Mehr erfahren |
| P1 | `common` | `wizard_pages/base.py:2132` | ### Wertbeitrag auf einen Blick |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:210` | ESCO-Anfrage kurzzeitig gedrosselt (wiederholter 4xx-Fehler). Unterdrückte Wiederholungen: {...}. |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:837` | ESCO Capability Status |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1065` | Die wichtigsten Inhalte zuerst, technische Daten darunter. |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1066` | #### Concept overview |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1067` | **Description** |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1073` | **Scope note** |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1076` | **ESCO Code** |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1078` | **NACE Code** |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1083` | Nicht von ESCO geliefert |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1085` | **Alternative Labels** |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1092` | #### Skills & Competences |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1102` | Knowledge: ✅ verfügbar |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1104` | Knowledge: 🚫 nicht unterstützt |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1106` | **Essential Skills and Competences** |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1110` | {...} Treffer |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1112` | **Optional Skills and Competences** |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1116` | {...} Treffer |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1118` | **Essential Knowledge** |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1122` | {...} Treffer |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1124` | **Optional Knowledge** |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1128` | {...} Treffer |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1131` | {...}/{...} Felder verfügbar |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1145` | ##### Beschreibung |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1150` | ##### Basisdaten |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1159` | ##### Klassifikation |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1162` | ##### Relationen |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1185` | \[ESCO URI: …{...}\]\({...}\) |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1195` | ##### Skills Group Share |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1434` | Optionale Kontextanker |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1435` | Für Grenzrollen oder Mischprofile: Kontextanker ergänzen die Einordnung, ersetzen aber nicht Primäranker und Kernexport. |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1449` | - **{...}. {...}** / Grund: {...} |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1451` | Noch keine Kontextanker hinterlegt. |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1453` | Maximal zwei sekundäre Kontextanker sind hinterlegt. |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1471` | arbeitsmarktüblicher Alternativtitel |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1471` | benachbarte Rolle |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1471` | spezialisierende Variante |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1486` | Primäranker kann nicht zusätzlich als Kontextanker genutzt werden. |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1497` | Kontextanker konnte nicht validiert werden. |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1527` | Kein Jobtitel vorhanden. Gib einen Rollenbegriff ein, um die Berufsabgleich manuell zu starten. |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1533` | ### Berufsabgleich bestätigen |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1534` | Suche mit: `{...}` |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1536` | Kontext: {...} |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1575` | Verbindung neu initialisiert. Du kannst die Suche erneut starten. |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1639` | ESCO ist gerade nicht stabil erreichbar. Du kannst manuell fortfahren und später erneut laden. |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1645` | Manuell fortfahren |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1650` | Fortsetzung ohne ESCO-Details aktiviert. Die Auswahl kann später ergänzt werden. |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1657` | Bitte den Ladevorgang später erneut ausführen. |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1659` | ESCO-Berufsdetails konnten nicht geladen werden: {...} |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1677` | ESCO-Relationsdaten sind gerade nicht stabil erreichbar. Du kannst manuell fortfahren und später erneut laden. |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1682` | ESCO-Relationsdaten konnten nicht vollständig geladen werden: {...} |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1704` | ESCO-Skillgruppen-Daten sind gerade nicht stabil erreichbar. Du kannst manuell fortfahren und später erneut laden. |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1709` | ESCO-Skillgruppen-Daten konnten nicht vollständig geladen werden: {...} |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1716` | Das ESCO-Portal zeigt diesen Anteil, der aktuell über den genutzten ESCO-Webservice nicht abrufbar ist. |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1719` | \[Portal öffnen\]\({...}\) |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1728` | ### Berufsabgleich bestätigen |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1729` | Suche mit: `{...}` |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1730` | Der Referenzberuf ist der gemeinsame Bezugspunkt für Aufgaben, Skills und Zusammenfassung. |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1734` | \[Portal öffnen\]\({...}\) |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1736` | Taxonomie, technische Daten und Berufsdetails sind hier gebündelt. |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1751` | \[ESCO URI: …{...}\]\({...}\) |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1768` | Weitere Details sind in den aufklappbaren ESCO-Bereichen verfügbar. |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1780` | Die App nutzt diese Einordnung für passendere Vorschläge zu Aufgaben, Skills und Summary. |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1792` | Diese Hinweise erklären, warum der Referenzberuf zur Jobspec passt. |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1818` | \[ESCO URI: …{...}\]\({...}\) |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1823` | ESCO Debug |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1824` | Session key: {...} · URI: {...} |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1828` | Beruf im Detail |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1861` | Sprachen für Berufstitel |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1870` | Titel-Varianten laden |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1880` | ESCO-Titelvarianten konnten nicht geladen werden: {...} |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1905` | Titelvarianten konnten nicht in allen Sprachen geladen werden ({...}). Bitte später erneut versuchen. |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1914` | {...}: keine Titel gefunden. |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1927` | ### Not normalized yet |
| P1 | `esco` | `wizard_pages/esco_occupation_ui.py:1928` | Diese Rollenbegriffe konnten noch nicht robust auf ESCO abgebildet werden. |
| P1 | `salary` | `wizard_pages/salary_forecast.py:273` | **Genutzte Werte** |
| P1 | `salary` | `wizard_pages/salary_forecast.py:274` | Aktive Werte fließen in die nächste Berechnung ein. |
| P1 | `salary` | `wizard_pages/salary_forecast.py:287` | {...} ({...}/{...} aktiv) |
| P1 | `salary` | `wizard_pages/salary_forecast.py:314` | ### Gehaltsprognose |
| P1 | `salary` | `wizard_pages/salary_forecast.py:335` | Berechnet die Prognose mit den aktuell aktivierten Werten neu. |
| P1 | `salary` | `wizard_pages/salary_forecast.py:335` | Update berechnen |
| P1 | `salary` | `wizard_pages/salary_forecast.py:343` | Noch kein Orientierungswert vorhanden. Wähle die relevanten Werte aus und starte die Berechnung. |
| P1 | `salary` | `wizard_pages/salary_forecast.py:348` | Orientierungswert ({...}) |
| P1 | `salary` | `wizard_pages/salary_forecast.py:352` | Realistische Spanne |
| P1 | `salary` | `wizard_pages/salary_forecast.py:352` | {...} bis {...} |
| P1 | `salary` | `wizard_pages/salary_forecast.py:364` | Berechnet für {...}; Standort: {...}; {...} Must-have-Skills; {...} aktive Eingaben. |
| P1 | `salary` | `wizard_pages/salary_forecast.py:370` | **Einfluss auf die Schätzung** |
| P1 | `salary` | `wizard_pages/salary_forecast.py:412` | {...}/{...} gespeicherte Werte aktiv. |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:115` | Quellenmix erscheint, sobald Elemente ausgewählt sind. |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:132` | Das Diagramm zeigt den Quellenmix der aktuell ausgewählten Elemente. |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:478` | Skills hinzufügen |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:484` | Skills entfernen |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:498` | Suchradius (km) |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:505` | Remote Share (%) |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:512` | Seniority Override |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:537` | Gehaltsprognose (indikativ) |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:603` | Bandbreite und p50 sind indikative Richtwerte (kein Garantiewert). |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:604` | Datenqualität: {...}% – signalisiert Datenabdeckung und Mapping-Treffer, nicht Prognosegenauigkeit. |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:611` | Technische Prognose-Diagnose |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:612` | quality_kind={...} |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:766` | **Szenario-Tabelle** |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:833` | Suchradius (km) |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:840` | Remote Share (%) |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:934` | p50 (Median) |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:936` | p10 (niedrig) |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:938` | p90 (hoch) |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:940` | Datenqualität: {...}. Sie beschreibt Datenabdeckung und Mapping-Treffer, nicht Prognosegenauigkeit. |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:944` | Berücksichtigte Antworten: {...}. |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:949` | Technische Prognose-Diagnose |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:966` | #### Einflussfaktoren |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:971` | #### Quellenmix |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:977` | #### Szenario-Steuerung |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:983` | Prognose aktualisieren |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:989` | #### Prognose-Ergebnis |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:1010` | Ausgewählte Rollen/Aufgaben: {...} |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:1040` | Prognose automatisch aktualisiert. |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:1042` | Prognose ist für die aktuellen Eingaben aktuell. |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:1095` | Diese Faktoren werden in der Prognose berücksichtigt. |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:1096` | Gewählte Benefits: {...} |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:1098` | Keine Benefits ausgewählt – Prognose wird ohne Benefit-Einflussfaktoren berechnet. |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:1128` | Prognose automatisch aktualisiert. |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:1134` | Die Gehaltsprognose ist vorübergehend nicht verfügbar. Bitte versuche es in Kürze erneut. |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:1138` | Prognose ist für die aktuellen Eingaben aktuell. |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:1232` | Must-have: {...} · Nice-to-have: {...} |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:1280` | Prognose automatisch aktualisiert. |
| P1 | `salary` | `wizard_pages/salary_forecast_panel.py:1282` | Prognose ist für die aktuellen Eingaben aktuell. |
| P1 | `wizard.benefits` | `wizard_pages/06_benefits.py:323` | + {...} weitere |
| P1 | `wizard.benefits` | `wizard_pages/06_benefits.py:362` | Vorschläge konnten nicht erzeugt werden. |
| P1 | `wizard.benefits` | `wizard_pages/06_benefits.py:391` | Variable Vergütung? |
| P1 | `wizard.benefits` | `wizard_pages/06_benefits.py:399` | OTE von |
| P1 | `wizard.benefits` | `wizard_pages/06_benefits.py:407` | OTE bis |
| P1 | `wizard.benefits` | `wizard_pages/06_benefits.py:416` | Währung |
| P1 | `wizard.benefits` | `wizard_pages/06_benefits.py:457` | z. B. alle 6 Wochen, keine |
| P1 | `wizard.benefits` | `wizard_pages/06_benefits.py:464` | Ausgleich / Zuschläge |
| P1 | `wizard.benefits` | `wizard_pages/06_benefits.py:469` | Besondere Zeiten |
| P1 | `wizard.benefits` | `wizard_pages/06_benefits.py:490` | YYYY-MM-DD oder freier Zeitraum |
| P1 | `wizard.benefits` | `wizard_pages/06_benefits.py:497` | Flexibilität |
| P1 | `wizard.benefits` | `wizard_pages/06_benefits.py:508` | Kündigungsfristen / Einschränkungen |
| P1 | `wizard.benefits` | `wizard_pages/06_benefits.py:525` | Nur ausfüllen, wenn diese Punkte für das Angebot relevant sind. |
| P1 | `wizard.benefits` | `wizard_pages/06_benefits.py:526` | #### Variable Vergütung |
| P1 | `wizard.benefits` | `wizard_pages/06_benefits.py:528` | #### Arbeitszeit und Ausgleich |
| P1 | `wizard.benefits` | `wizard_pages/06_benefits.py:530` | #### Vertrag und Start |
| P1 | `wizard.benefits` | `wizard_pages/06_benefits.py:572` | #### Weitere Rahmenbedingungen |
| P1 | `wizard.benefits` | `wizard_pages/06_benefits.py:623` | **Benefits ({...})** |
| P1 | `wizard.benefits` | `wizard_pages/06_benefits.py:662` | ### Angebot bearbeiten |
| P1 | `wizard.benefits` | `wizard_pages/06_benefits.py:663` | Wähle Benefits und Rahmenbedingungen, die später in Anzeige, Briefing und Prognose verwendet werden. |
| P1 | `wizard.benefits` | `wizard_pages/06_benefits.py:675` | Rollenbezug: {...} |
| P1 | `wizard.benefits` | `wizard_pages/06_benefits.py:717` | Vorschläge anpassen |
| P1 | `wizard.benefits` | `wizard_pages/06_benefits.py:718` | z. B. Berlin, NRW, DACH |
| P1 | `wizard.benefits` | `wizard_pages/06_benefits.py:734` | Weitere Vorschläge |
| P1 | `wizard.benefits` | `wizard_pages/06_benefits.py:757` | Neue Vorschläge hinzugefügt: {...} |
| P1 | `wizard.benefits` | `wizard_pages/06_benefits.py:759` | Keine neuen Vorschläge gefunden. |
| P1 | `wizard.benefits` | `wizard_pages/06_benefits.py:795` | #### Ausgewählt |
| P1 | `wizard.benefits` | `wizard_pages/06_benefits.py:813` | Noch keine Benefits ausgewählt. Die Prognose läuft ohne Benefit-Einfluss. |
| P1 | `wizard.benefits` | `wizard_pages/06_benefits.py:838` | Die Gehaltsprognose ist vorübergehend nicht verfügbar. Bitte versuche es in Kürze erneut. |
| P1 | `wizard.benefits` | `wizard_pages/06_benefits.py:843` | #### Offene Klärungen |
| P1 | `wizard.benefits` | `wizard_pages/06_benefits.py:844` | Klärt, was für Angebot und Kommunikation noch fehlt. |
| P1 | `wizard.benefits` | `wizard_pages/06_benefits.py:848` | Für diesen Abschnitt wurden keine spezifischen Fragen erzeugt. Du kannst trotzdem weitergehen. |
| P1 | `wizard.benefits` | `wizard_pages/06_benefits.py:855` | #### Prüfung |
| P1 | `wizard.benefits` | `wizard_pages/06_benefits.py:856` | Prüft, ob Angebot, Auswahl und offene Punkte zusammenpassen. |
| P1 | `wizard.benefits` | `wizard_pages/06_benefits.py:876` | Angebot kompakt machen |
| P1 | `wizard.company` | `wizard_pages/02_company.py:152` | Abschnitt gespeichert. |
| P1 | `wizard.company` | `wizard_pages/02_company.py:317` | #### Website analysieren |
| P1 | `wizard.company` | `wizard_pages/02_company.py:333` | Website aus der Anzeige: {...} |
| P1 | `wizard.company` | `wizard_pages/02_company.py:335` | Öffentliche Website, die für die Analyse verwendet werden soll. |
| P1 | `wizard.company` | `wizard_pages/02_company.py:342` | Manuell erfasste URL wird für die Analyse verwendet. |
| P1 | `wizard.company` | `wizard_pages/02_company.py:370` | Noch keine Website-Analyse durchgeführt. |
| P1 | `wizard.company` | `wizard_pages/02_company.py:399` | Noch nicht analysiert. |
| P1 | `wizard.company` | `wizard_pages/02_company.py:434` | Merkt passende Website-Hinweise vor. Antworten werden erst nach Bestätigung im passenden Fragefeld gespeichert. |
| P1 | `wizard.company` | `wizard_pages/02_company.py:434` | Website-Hinweise für offene Fragen |
| P1 | `wizard.company` | `wizard_pages/02_company.py:452` | #### Website-Funde übernehmen |
| P1 | `wizard.company` | `wizard_pages/02_company.py:453` | Prüfe die vorgeschlagenen Werte und übernimm nur belastbare Angaben. |
| P1 | `wizard.company` | `wizard_pages/02_company.py:487` | Ziel-Feld {...} |
| P1 | `wizard.company` | `wizard_pages/02_company.py:521` | Quelle: {...} |
| P1 | `wizard.company` | `wizard_pages/02_company.py:528` | Beleg anzeigen |
| P1 | `wizard.company` | `wizard_pages/02_company.py:532` | Bestätigten Wert überschreiben |
| P1 | `wizard.company` | `wizard_pages/02_company.py:542` | Diesen Fund übernehmen |
| P1 | `wizard.company` | `wizard_pages/02_company.py:565` | Website-Funde übernehmen |
| P1 | `wizard.company` | `wizard_pages/02_company.py:602` | {...} Website-Kontextwerte gespeichert. |
| P1 | `wizard.company` | `wizard_pages/02_company.py:604` | {...} Website-Kontextwerte bestätigt. |
| P1 | `wizard.company` | `wizard_pages/02_company.py:606` | {...} Website-Konflikte wurden als zusätzlicher Beleg gespeichert. |
| P1 | `wizard.company` | `wizard_pages/02_company.py:610` | {...} ausgewählte Kontextwerte wurden nicht gespeichert. |
| P1 | `wizard.company` | `wizard_pages/02_company.py:840` | #### Arbeitgeberprofil |
| P1 | `wizard.company` | `wizard_pages/02_company.py:869` | #### Unternehmenskontext |
| P1 | `wizard.company` | `wizard_pages/02_company.py:914` | #### Team & Berichtslinie |
| P1 | `wizard.company` | `wizard_pages/02_company.py:1044` | Keine zusätzlichen offenen Fragen. |
| P1 | `wizard.company` | `wizard_pages/02_company.py:1083` | Keine verlässlichen Werte erkannt. Details siehe Gaps/Assumptions. |
| P1 | `wizard.company` | `wizard_pages/02_company.py:1104` | #### Kontext bearbeiten |
| P1 | `wizard.company` | `wizard_pages/02_company.py:1105` | Unternehmen, Team und offene Klärungen werden hier zusammen gepflegt. |
| P1 | `wizard.company` | `wizard_pages/02_company.py:1108` | ##### Unternehmen |
| P1 | `wizard.company` | `wizard_pages/02_company.py:1116` | ##### Team |
| P1 | `wizard.company` | `wizard_pages/02_company.py:1125` | #### Prüfung |
| P1 | `wizard.company` | `wizard_pages/team_section.py:161` | Kein ESCO-Occupation-Anker bestätigt. Gehe zu „Start → Phase C: Semantischen Anker bestätigen“. |
| P1 | `wizard.company` | `wizard_pages/team_section.py:164` | Zu Start → Phase C |
| P1 | `wizard.company` | `wizard_pages/team_section.py:175` | ESCO-Kontext aktuell nicht verfügbar: {...} |
| P1 | `wizard.company` | `wizard_pages/team_section.py:251` | {...} Kontextwert(e) übernommen. |
| P1 | `wizard.company` | `wizard_pages/team_section.py:253` | Keine geeignete Team-Notizfrage zum Übernehmen gefunden. |
| P1 | `wizard.company` | `wizard_pages/team_section.py:261` | Übernommener Kontext ist in der Team-Notiz gespeichert. |
| P1 | `wizard.company` | `wizard_pages/team_section.py:275` | Für diesen Abschnitt wurden keine spezifischen Fragen erzeugt. Du kannst trotzdem weitergehen. |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:248` | +{...} weitere Angabe(n) |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:267` | In Summary und Export übernehmen |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:342` | ### Bereits bekannt |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:343` | Diese Angaben wurden aus Jobspec, bisherigen Antworten und diesem Schritt gesammelt. |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:374` | Summary- und Exportauswahl |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:448` | Lege fest, wer entscheidet, wer informiert und wer am Interview teilnimmt. |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:463` | Eine Person kann mehrere Rollen übernehmen. |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:485` | Daten aus Budget übernehmen |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:508` | Bei Interviews dabei |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:549` | **Updates an Kandidat:innen** |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:590` | Nächstes Update |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:598` | Update hinzufügen |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:602` | Auswahl zurücksetzen |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:607` | Geplante Updates |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:649` | Keine verlässlichen Werte erkannt. Details siehe Gaps/Assumptions. |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:703` | Für Summary/Export verwenden |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:847` | #### Ablauf |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:858` | Ziel der Stufe |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:887` | #### Verantwortung |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:900` | Rolle im Entscheidungsprozess |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:900` | z. B. Entscheider, Interviewer, Feedback |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:921` | #### Rückmeldefristen |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:938` | Update binnen Tagen |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:962` | #### Arbeitsproben und Nachweise |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:967` | Was wird bewertet? |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:980` | Woran erkennt man gute Ergebnisse? |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:1001` | #### Bewertung |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:1002` | Interviewstufe für die Bewertung |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:1014` | **Bewertungspunkt {...}** |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:1017` | Was wird bewertet? |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:1023` | Gewichtung % |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:1037` | Woran erkennt man gute Antworten? |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:1058` | Notizen zur Bewertung |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:1078` | Welche Fragen sind für alle Kandidat:innen identisch? |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:1094` | ### Interviewprozess planen |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:1095` | Ablauf, Kommunikation, Zuständigkeiten und Bewertung werden hier zusammen gepflegt. |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:1161` | #### Offene Fragen |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:1163` | Für diesen Abschnitt wurden keine spezifischen Fragen erzeugt. Du kannst trotzdem weitergehen. |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:1170` | #### Prüfung |
| P1 | `wizard.interview` | `wizard_pages/07_interview.py:1187` | Interviewprozess klar und fair gestalten |
| P1 | `wizard.role_tasks` | `wizard_pages/04_role_tasks.py:344` | Keine Angabe erkannt. |
| P1 | `wizard.role_tasks` | `wizard_pages/04_role_tasks.py:350` | {...} weitere anzeigen |
| P1 | `wizard.role_tasks` | `wizard_pages/04_role_tasks.py:377` | Deutsch, Englisch, ... |
| P1 | `wizard.role_tasks` | `wizard_pages/04_role_tasks.py:377` | {...}: Sprache |
| P1 | `wizard.role_tasks` | `wizard_pages/04_role_tasks.py:386` | {...}: Mindestniveau |
| P1 | `wizard.role_tasks` | `wizard_pages/04_role_tasks.py:392` | {...}: Kontext |
| P1 | `wizard.role_tasks` | `wizard_pages/04_role_tasks.py:409` | #### Arbeitsmodell & Standort |
| P1 | `wizard.role_tasks` | `wizard_pages/04_role_tasks.py:453` | Erlaubte Regionen oder Zeitzonen |
| P1 | `wizard.role_tasks` | `wizard_pages/04_role_tasks.py:453` | z. B. Deutschland / DACH / CET +/- 2h |
| P1 | `wizard.role_tasks` | `wizard_pages/04_role_tasks.py:483` | #### Fixe Rahmenbedingungen |
| P1 | `wizard.role_tasks` | `wizard_pages/04_role_tasks.py:556` | Reisen erforderlich? |
| P1 | `wizard.role_tasks` | `wizard_pages/04_role_tasks.py:568` | Reiseanteil (%) |
| P1 | `wizard.role_tasks` | `wizard_pages/04_role_tasks.py:577` | z. B. monatlich, wöchentlich |
| P1 | `wizard.role_tasks` | `wizard_pages/04_role_tasks.py:591` | Übernachtungen möglich |
| P1 | `wizard.role_tasks` | `wizard_pages/04_role_tasks.py:602` | Führerschein / Mobilitätsnachweis |
| P1 | `wizard.role_tasks` | `wizard_pages/04_role_tasks.py:623` | ### Aufgaben schärfen |
| P1 | `wizard.role_tasks` | `wizard_pages/04_role_tasks.py:649` | Prioritäten prüfen |
| P1 | `wizard.role_tasks` | `wizard_pages/04_role_tasks.py:655` | Priorität |
| P1 | `wizard.role_tasks` | `wizard_pages/04_role_tasks.py:669` | ### Erfolg & Verantwortung |
| P1 | `wizard.role_tasks` | `wizard_pages/04_role_tasks.py:687` | Meilensteine 30 bis 180 Tage |
| P1 | `wizard.role_tasks` | `wizard_pages/04_role_tasks.py:691` | Reiseprofil und Bereitschaft |
| P1 | `wizard.role_tasks` | `wizard_pages/04_role_tasks.py:737` | Keine belastbaren Aufgaben erkannt. Kläre die Rolle über die offenen Fragen. |
| P1 | `wizard.role_tasks` | `wizard_pages/04_role_tasks.py:777` | ESCO-Hinweis: Occupation-Details konnten nicht geladen werden ({...}). |
| P1 | `wizard.role_tasks` | `wizard_pages/04_role_tasks.py:787` | Vorschläge basieren auf dem bestätigten Referenzberuf: {...}. |
| P1 | `wizard.role_tasks` | `wizard_pages/04_role_tasks.py:828` | Weitere Vorschläge |
| P1 | `wizard.role_tasks` | `wizard_pages/04_role_tasks.py:835` | Vorschläge ergänzen |
| P1 | `wizard.role_tasks` | `wizard_pages/04_role_tasks.py:914` | {...} Aufgaben ausgewählt |
| P1 | `wizard.role_tasks` | `wizard_pages/04_role_tasks.py:936` | #### Wirkung auf die Gehaltsprognose |
| P1 | `wizard.role_tasks` | `wizard_pages/04_role_tasks.py:937` | {...} ausgewählte Aufgaben fließen in die Prognose ein. |
| P1 | `wizard.role_tasks` | `wizard_pages/04_role_tasks.py:939` | Noch keine Aufgaben ausgewählt. |
| P1 | `wizard.role_tasks` | `wizard_pages/04_role_tasks.py:947` | #### Offene Punkte |
| P1 | `wizard.role_tasks` | `wizard_pages/04_role_tasks.py:948` | Nur die Fragen beantworten, die für ein klares Rollenbild noch fehlen. |
| P1 | `wizard.role_tasks` | `wizard_pages/04_role_tasks.py:952` | Für diesen Abschnitt wurden keine spezifischen Fragen erzeugt. Du kannst trotzdem weitergehen. |
| P1 | `wizard.role_tasks` | `wizard_pages/04_role_tasks.py:960` | #### Prüfung |
| P1 | `wizard.role_tasks` | `wizard_pages/04_role_tasks.py:961` | Kurz prüfen, ob Aufgaben, Verantwortung und offene Punkte reichen. |
| P1 | `wizard.role_tasks` | `wizard_pages/04_role_tasks.py:982` | Rolle und Aufgaben klären |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:497` | Neue Vorschläge erscheinen im Board und werden erst nach Auswahl übernommen. |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:510` | AI-Vorschläge generieren |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:521` | Keine Begriffe erkannt. |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:527` | Mehr anzeigen ({...}) |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:627` | Als optional markieren |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:829` | Aus Anzeige erkannt |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:834` | ESCO ergänzt |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:836` | ESCO + AI als gemeinsame Empfehlungsliste. |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:838` | ESCO-Vorschläge erscheinen nach bestätigtem ESCO-Anker. |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:861` | Übernommen |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:862` | Finale Auswahl für Brief, Matching und Interview. |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1114` | Noch keine Skills ausgewählt. |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1128` | Skill-Details werden nur bei Bedarf geladen. |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1130` | Details laden |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1138` | Details geladen. |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1148` | **Bezeichnung:** {...} |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1149` | **Beschreibung:** {...} |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1150` | **Hinweis:** {...} |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1152` | Für diesen Skill sind aktuell keine sicheren Details verfügbar. |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1156` | Noch keine Details geladen. |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1159` | URI (optional kopieren): |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1498` | #### ESCO Matrix Coverage |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1511` | reason={...} |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1512` | covered=0 · partial=0 · missing=0 · overrepresented=0 |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1522` | Matrix-Coverage hat Lücken: bitte fehlende oder teilweise abgedeckte Skill-Gruppen prüfen. |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1524` | Matrix-Coverage ist vollständig oder überrepräsentiert. |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1528` | reason={...} |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1596` | AI-Vorschläge konnten nicht erzeugt werden. |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1638` | {...} AI-Skill(s) übernommen. |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1640` | Keine zusätzlichen AI-Skills gefunden. |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1670` | #### Offene Begriffe |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1671` | Für jeden Begriff: ESCO mappen, Freitext behalten, ignorieren oder erneut suchen. |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1744` | Retry Sprache |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1781` | Die Jobspec liefert die erste Vorauswahl. Im Board entscheidest du, was in die finale Skill-Liste kommt. |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1791` | Tech Stack |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1792` | Erkannte Begriffe anzeigen |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1795` | **Must-have ({...}):** |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1799` | Noch nicht erkannt. |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1801` | **Nice-to-have ({...}):** |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1805` | Noch nicht erkannt. |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1807` | **Tech Stack ({...}):** |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1811` | Noch nicht erkannt. |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1813` | Keine verlässlichen Werte erkannt. Details siehe Gaps/Assumptions. |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1815` | {...} eindeutige Skill-Signale erkannt. |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1827` | #### Auswahl |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1828` | Finale Auswahl für Brief, Matching und Interview. |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1899` | ##### Kategorien |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1917` | Details anzeigen |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1952` | Vertiefung (optional) |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1970` | #### AI · Vorschläge |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:1977` | Noch keine AI-Skills vorhanden. |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:2007` | ESCO-Sektion wird nach bestätigtem ESCO-Anker eingeblendet. |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:2030` | Matrix-Prior nicht geladen: {...} |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:2034` | ESCO-Anfragen kurzzeitig gedrosselt (wiederholter 4xx-Fehler). Unterdrückte Wiederholungen: {...}. |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:2079` | ESCO empfiehlt {...} Skills für {...}. |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:2297` | Ausgewählt: {...} Skills |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:2323` | {...} Skills übernommen · {...} offene Begriffe · {...} |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:2327` | Technische Prüfung |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:2328` | Technische ESCO- und Mapping-Prüfung für Expert:innen. |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:2340` | {...} Skills übernommen · Bereit für Recruiting Brief, Matching und Interviewfragen. |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:2425` | Freitext-Begriffe begründen |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:2426` | Nur ausfüllen, wenn ein Begriff bewusst ohne ESCO-Mapping übernommen bleibt. |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:2451` | Begründungen übernehmen |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:2481` | Wähle zuerst Skills aus den Quellen aus, um Status, Niveau und Timing zu präzisieren. |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:2496` | ### Skill-Anforderungen strukturieren |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:2497` | Status, Mindestniveau, Timing und Nachweis werden als kompakte Tabelle gespeichert. |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:2569` | Zertifikate / Nachweise mit Pflichtgrad, Frist oder Gültigkeit |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:2575` | Skill-Anforderungen übernehmen |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:2581` | Tabellenänderungen werden erst nach dem Übernehmen gespeichert. |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:2673` | #### Offene Klärungen |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:2674` | Diese Fragen klären Pflichtgrad, Mindestniveau, Timing und Nachweise, die aus der Jobspec noch nicht sicher hervorgehen. |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:2681` | Für diesen Abschnitt wurden keine spezifischen Fragen erzeugt. Du kannst trotzdem weitergehen. |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:2716` | ### Skill-Liste bauen |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:2717` | Vergleiche Quellen, übernimm relevante Skills und strukturiere sie direkt für Matching, Interview und Export. |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:2731` | #### Prüfung |
| P1 | `wizard.skills` | `wizard_pages/05_skills.py:2732` | Prüfe, ob Skill-Auswahl, Pflichtgrad und offene Pflichtangaben für Brief, Matching und Interview verwertbar sind. |
| P1 | `wizard.start` | `wizard_pages/jobad_intake.py:466` | Extrahierter Text ist bereit ({...} Zeichen). Die vollständige Quelle bleibt einklappbar. |
| P1 | `wizard.start` | `wizard_pages/jobad_intake.py:471` | Extrahierter Text ist bereit ({...} Zeichen). Kompakte Vorschau: |
| P1 | `wizard.start` | `wizard_pages/jobad_intake.py:736` | Kleine Info-Icons zeigen die jeweilige Fundstelle bei Bedarf. |
| P1 | `wizard.start` | `wizard_pages/jobad_intake.py:967` | #### Prüffokus |
| P1 | `wizard.start` | `wizard_pages/jobad_intake.py:980` | Arbeitsort: {...} |
| P1 | `wizard.start` | `wizard_pages/jobad_intake.py:1005` | #### Herkunft der Informationen |
| P1 | `wizard.start` | `wizard_pages/jobad_intake.py:1016` | Belegte Fundstellen und Annahmen anzeigen |
| P1 | `wizard.start` | `wizard_pages/jobad_intake.py:1050` | #### Erkannte Angaben prüfen |
| P1 | `wizard.start` | `wizard_pages/jobad_intake.py:1130` | Optional: Im nächsten Abschnitt können Sie einen Referenzberuf für den Berufsabgleich bestätigen. |
| P1 | `wizard.start` | `wizard_pages/jobad_intake.py:1196` | Ein paar Informationen vorab: Standardwerte werden verwendet. |
| P1 | `wizard.start` | `wizard_pages/jobad_intake.py:1232` | Anzahl Positionen |
| P1 | `wizard.start` | `wizard_pages/jobad_intake.py:1356` | Maximale Dateigröße: {...} MB. |
| P1 | `wizard.start` | `wizard_pages/jobad_intake.py:1356` | PDF, DOCX oder TXT hochladen |
| P1 | `wizard.start` | `wizard_pages/jobad_intake.py:1390` | Datei bereit: {...} |
| P1 | `wizard.start` | `wizard_pages/jobad_intake.py:1393` | Extraktion fehlgeschlagen: {...} |
| P1 | `wizard.start` | `wizard_pages/jobad_intake.py:1397` | #### Einstellungen |
| P1 | `wizard.start` | `wizard_pages/jobad_intake.py:1400` | Erweiterte Intake-Einstellungen |
| P1 | `wizard.start` | `wizard_pages/jobad_intake.py:1414` | Die Quelle ist sehr kurz. Die Extraktion kann unvollstaendig sein. |
| P1 | `wizard.start` | `wizard_pages/jobad_intake.py:1418` | Es wird immer nur die aktuell aktive Quelle analysiert. |
| P1 | `wizard.start` | `wizard_pages/jobad_intake.py:1436` | Dokumentvorschau anzeigen |
| P1 | `wizard.start` | `wizard_pages/jobad_intake.py:1443` | Extrahierter Text für die Analyse |
| P1 | `wizard.start` | `wizard_pages/jobad_intake.py:1451` | Extrahierter Text für die Analyse |
| P1 | `wizard.start` | `wizard_pages/jobad_intake.py:1451` | Füge hier den vollständigen Ausschreibungstext ein … |
| P1 | `wizard.start` | `wizard_pages/jobad_intake.py:1460` | Füge hier den vollständigen Ausschreibungstext ein … |
| P1 | `wizard.start` | `wizard_pages/jobad_intake.py:1460` | Jobspec oder Rohtext für das Briefing einfügen |
| P1 | `wizard.start` | `wizard_pages/jobad_intake.py:1488` | Berufsabgleich: Standardsprache DE, Alternative EN |
| P1 | `wizard.start` | `wizard_pages/jobad_intake.py:1504` | #### Berufsabgleich |
| P1 | `wizard.start` | `wizard_pages/jobad_intake.py:1506` | Debug: technische ESCO-Einstellungen für Version, API und Datenquelle. |
| P1 | `wizard.start` | `wizard_pages/jobad_intake.py:1519` | **European Skills/Competences, Qualifications and Occupations (ESCO)** |
| P1 | `wizard.start` | `wizard_pages/jobad_intake.py:1532` | ESCO beschreibt 3.039 Berufe und 13.939 damit verknüpfte Skills in 28 Sprachen. |
| P1 | `wizard.start` | `wizard_pages/jobad_intake.py:1578` | Obsolete anzeigen |
| P1 | `wizard.start` | `wizard_pages/jobad_intake.py:1594` | Diagnose: lane={...} · version={...} · api={...} · runtime={...} · language={...}/{...} |
| P1 | `wizard.start` | `wizard_pages/jobad_intake.py:1627` | ### Analyseergebnis |
| P1 | `wizard.start` | `wizard_pages/jobad_intake.py:1639` | ### Berufsabgleich bestätigen |
| P1 | `wizard.start` | `wizard_pages/jobad_intake.py:1705` | Quelle oder Einstellungen ändern |
| P1 | `wizard.start` | `wizard_pages/jobad_intake.py:1863` | Mindestens ein Ergebnis wurde aus dem Cache geladen. |
| P1 | `wizard.summary` | `wizard_pages/08_summary.py:696` | Die Firmen-Website-Research-Daten sind ungültig. Bitte prüfe die Angaben im Unternehmensschritt und versuche es erneut. |
| P1 | `wizard.summary` | `wizard_pages/08_summary.py:731` | Recruiting Brief aus dem Cache geladen. |
| P1 | `wizard.summary` | `wizard_pages/08_summary.py:1004` | #### 1. Ziel der Anzeige |
| P1 | `wizard.summary` | `wizard_pages/08_summary.py:1005` | Wähle den Schwerpunkt für die erste Variante. |
| P1 | `wizard.summary` | `wizard_pages/08_summary.py:1015` | #### 2. Inhalte auswählen |
| P1 | `wizard.summary` | `wizard_pages/08_summary.py:1016` | Die wichtigsten Inhalte werden vorausgewählt. Passe nur an, was in der Anzeige wirklich sichtbar sein soll. |
| P1 | `wizard.summary` | `wizard_pages/08_summary.py:1068` | #### 3. Sprache & Marke |
| P1 | `wizard.summary` | `wizard_pages/08_summary.py:1077` | Tonalität |
| P1 | `wizard.summary` | `wizard_pages/08_summary.py:1084` | Länge |
| P1 | `wizard.summary` | `wizard_pages/08_summary.py:1090` | CTA-Stärke |
| P1 | `wizard.summary` | `wizard_pages/08_summary.py:1096` | AGG-konforme, inklusive Sprache ist immer aktiv und kann nicht deaktiviert werden. |
| P1 | `wizard.summary` | `wizard_pages/08_summary.py:1100` | Das Logo wird als Metadatum gespeichert und kann im Exportprozess weiterverwendet werden. |
| P1 | `wizard.summary` | `wizard_pages/08_summary.py:1100` | Logo-Upload (optional) |
| P1 | `wizard.summary` | `wizard_pages/08_summary.py:1112` | Logo kann nicht verwendet werden. Bitte PNG oder JPG/JPEG mit unterstützter Größe und gültigen Bilddaten verwenden. |
| P1 | `wizard.summary` | `wizard_pages/08_summary.py:1130` | Zusätzlicher Styleguide des Arbeitgebers (optional) |
| P1 | `wizard.summary` | `wizard_pages/08_summary.py:1130` | z. B. Tonalität, Wording, No-Gos, Corporate Language, Du/Sie, Diversity-Hinweise … |
| P1 | `wizard.summary` | `wizard_pages/08_summary.py:1157` | #### 4. Optimierung |
| P1 | `wizard.summary` | `wizard_pages/08_summary.py:1158` | Was soll bei der nächsten Variante besonders verbessert werden? |
| P1 | `wizard.summary` | `wizard_pages/08_summary.py:1175` | Weitere Anpassungswünsche (optional) |
| P1 | `wizard.summary` | `wizard_pages/08_summary.py:1175` | z. B. stärker auf Senior-Profile fokussieren, CTA kürzen, Benefits konkretisieren … |
| P1 | `wizard.summary` | `wizard_pages/08_summary.py:1196` | Hinweis: Kritische Lücken werden in der AGG-Checkliste markiert und nicht halluziniert. |
| P1 | `wizard.summary` | `wizard_pages/08_summary.py:1201` | Job-Ad-Modell: `{...}` |
| P1 | `wizard.summary` | `wizard_pages/08_summary.py:1250` | Fakten je Schritt bearbeiten |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:617` | {...}: Keine passenden Daten vorhanden. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:621` | {...}: Keine passenden Daten vorhanden. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:683` | **Einstellungs-Zusammenfassung** |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:684` | - Zielgruppe: {...} |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:685` | - Länge: {...} |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:686` | - Ansprache: {...} |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:687` | - Fokus: {...} |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:688` | - Offene Lücken: {...} |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:704` | Datenmatrix für Stellenanzeigen-Generierung |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:722` | **Auswahl (Multi-Select Pills pro Angabe)** |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:735` | Kritische/fehlende Informationen |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:740` | Keine kritischen Lücken erkannt. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:820` | Keine ESCO-RAG-Anforderungsdaten verfügbar. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:822` | ESCO-RAG-Abdeckung: kompakte KPI-Übersicht zur Anforderungsabdeckung |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:833` | ### Fakten |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:840` | Keine Fakten verfügbar. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:860` | ### Fakten |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:886` | Bereich, Feld, Wert oder Quelle filtern … |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:886` | Suche in Fakten |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:894` | Automatisch erkannt |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:964` | ### Fakten je Schritt |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:965` | Nur vorhandene Werte werden angezeigt. Änderungen werden in die kanonischen Intake-Daten zurückgeschrieben. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:967` | Keine auswertbaren Fakten vorhanden. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:977` | Keine Werte vorhanden. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1070` | Änderungen speichern |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1080` | Änderungen gespeichert. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1083` | Keine Änderungen erkannt. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1123` | Zum Feld |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1141` | ### Kritische Lücken |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1144` | Keine kritischen Lücken erkannt. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1268` | Länge |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1275` | Tonalität |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1287` | Logo (PNG/JPG) |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1298` | Logo kann nicht verwendet werden. Bitte PNG oder JPG/JPEG mit unterstützter Größe und gültigen Bilddaten verwenden. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1302` | Styleguide (TXT/MD) |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1307` | Styleguide / No-Gos |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1307` | z. B. Corporate Language, Wording, No-Gos |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1350` | Erstgespräch |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1350` | Finale Runde |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1363` | Fachliche Vertiefung |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1363` | Kultur & Motivation |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1394` | Bis zu 10 fachbereichsbezogene Vorschläge aus Brief, Skills und ESCO-Kontext. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1406` | Fragen je Frageblock |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1439` | Kanäle |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1466` | z. B. Berlin, remote DACH |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1472` | Ausschlüsse |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1472` | z. B. Praktikum, Werkstudent |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1506` | 3 Monate |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1506` | 6 Monate |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1518` | Arbeitszeit / Gehaltshinweis |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1518` | z. B. 40h/Woche, Gehaltsband aus Intake übernehmen |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1524` | Rechtliche Prüfung bleibt erforderlich; das Ergebnis ist nur ein Vorlagenentwurf. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1542` | ### Recruiting-Unterlagen |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1543` | Wähle eine Unterlage, schärfe die wichtigsten Einflussfaktoren und generiere direkt aus den aktuellen Daten. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1592` | Reservierter Slot |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1593` | Noch nicht aktiv |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1607` | Status: {...} |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1642` | Status: {...} |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1648` | Voraussetzung: ✅ {...} |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1650` | Voraussetzung: ⚠️ {...} |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1654` | Vorbereitung im separaten Panel unterhalb der Aktionskarten. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1655` | Stellenanzeige vorbereiten |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1666` | **Eingaben** |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1671` | Nicht verfügbar: {...} |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1713` | ### Stellenanzeige vorbereiten |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1714` | Welche Informationen sollen in die Stellenanzeige einfließen? |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1715` | Blendet Auswahl, Spracheinstellungen und Optimierung für die Stellenanzeige ein oder aus. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1715` | Konfigurationspanel anzeigen |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1721` | Panel ausgeblendet. Nutze „Stellenanzeige vorbereiten“ in der Job-Ad-Karte. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1738` | ### Recruiting Brief |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1747` | Status: {...} · {...} |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1766` | ### Weitere Recruiting-Unterlagen |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1767` | Nachgelagerte Unterlagen bauen auf einem aktuellen Recruiting Brief auf. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1780` | ### Export |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1782` | Export wird im Bereich **Brief & Export** bereitgestellt (JSON, Markdown, DOCX, ESCO-Mapping). |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1786` | Bereit: Recruiting Brief vorhanden – Exporte können erstellt werden. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1790` | Noch nicht bereit: Erst den Recruiting Brief erstellen, dann Exporte nutzen. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1876` | #### Unterlagen-Pipeline |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1877` | Status der wichtigsten Recruiting-Unterlagen auf einen Blick. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1903` | Status: {...} |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1907` | Voraussetzungen: {...} |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:1980` | Aktuell ist kein nächster Schritt verfügbar. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2000` | Voraussetzung: {...} {...} |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2003` | Aktion: {...} |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2021` | Keine kritischen Lücken erkannt. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2029` | #### Recruiting-Unterlagen starten |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2043` | Status: {...} · Voraussetzungen: {...} |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2047` | Voraussetzungen: {...} |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2102` | ### Arbeitsbereiche |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2113` | Noch kein gültiger Recruiting Brief verfügbar. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2131` | Export ist verfügbar, sobald ein gültiger Recruiting Brief vorhanden ist. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2137` | Technische Vorschauen und Statusdaten bleiben hier gebündelt. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2139` | Strukturierte Exportvorschau |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2170` | Noch keine Timing-Daten für Enrichment-Pfade verfügbar. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2212` | #### Unterlagenübersicht |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2256` | Details: {...}{...} |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2261` | **Voraussetzungen:** {...} {...} |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2265` | Stellenanzeige vorbereiten |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2275` | **Eingaben** |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2296` | Keine AGG-Checkliste hinterlegt. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2337` | ### Ergebnis |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2350` | ### Prüfung |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2351` | **Zielgruppe** |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2356` | Keine Zielgruppe hinterlegt. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2357` | **AGG-Checkliste** |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2372` | ### Export |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2378` | Stellenanzeige herunterladen (DOCX) |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2386` | PDF-Export benötigt reportlab (nicht verfügbar). |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2388` | Stellenanzeige herunterladen (PDF) |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2395` | Stellenanzeige herunterladen (Markdown) |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2417` | Für diese Unterlage liegt noch kein Ergebnis vor. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2433` | HR-Sheet herunterladen (JSON) |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2440` | HR-Sheet herunterladen (DOCX) |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2447` | Für diese Unterlage liegt noch kein Ergebnis vor. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2472` | Fachbereich-Sheet herunterladen (JSON) |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2479` | Fachbereich-Sheet herunterladen (DOCX) |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2487` | PDF-Export benötigt reportlab (nicht verfügbar). |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2489` | Fachbereich-Sheet herunterladen (PDF) |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2496` | Für diese Unterlage liegt noch kein Ergebnis vor. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2505` | Für diese Unterlage liegt noch kein Ergebnis vor. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2568` | Vorhandene Ergebnisse |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2602` | Was soll am Ergebnis angepasst werden? |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2602` | z. B. kürzer, stärker auf Senior-Profile, mehr Interviewfragen zu Stakeholder-Management … |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2612` | Anpassungen übernehmen |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2670` | ### Ergebnis |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2687` | Dieses Ergebnis basiert auf älteren Fakten oder Optionen. Bitte neu generieren. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2691` | Für diese Unterlage liegt noch kein Ergebnis vor. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2734` | Weitere Ergebnisse |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2736` | Als Fokus öffnen: {...} |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2760` | Noch keine weiteren Recruiting-Unterlagen vorhanden. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2784` | Lade die Exportformate direkt herunter. JSON-Vorschau und Debug-Details sind standardmäßig eingeklappt. |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2789` | JSON herunterladen |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2796` | Markdown herunterladen |
| P1 | `wizard.summary` | `wizard_pages/summary_view.py:2803` | DOCX herunterladen |
| P2 | `common` | `app.py:557` | Detailgrad, Antwortmodus und Informationstiefe werden im Start-Schritt über eine gemeinsame Auswahl gesteuert. |
| P2 | `common` | `app.py:567` | Globale Schwelle für erkannte Fakten, Match-Hinweise, Readiness und Trefferdarstellung. |
| P2 | `common` | `app.py:588` | Reduziert sensible personenbezogene Angaben in der Verarbeitung, wo möglich. |
| P2 | `components` | `components/sidebar.py:34` | #### Seiten |
| P2 | `esco` | `ui_esco_picker.py:268` | Taxonomie konnte nicht geladen werden: {...} |
| P2 | `esco` | `ui_esco_picker.py:273` | Keine übergeordnete Relation (`hasBroaderTransitive`) für dieses ESCO-Konzept gefunden. |
| P2 | `esco` | `ui_esco_picker.py:277` | Taxonomie ist noch nicht geladen. |
| P2 | `esco` | `ui_esco_picker.py:294` | Keine übergeordnete Taxonomie für dieses ESCO-Konzept verfügbar. |
| P2 | `esco` | `ui_esco_picker.py:341` | ESCO-Picker-Konfiguration ist ungültig (fehlender target_state_key). |
| P2 | `esco` | `ui_esco_picker.py:385` | Der Begriff steuert nur den Berufsabgleich; deine Rollenbeschreibung und spätere Antworten bleiben unverändert. |
| P2 | `esco` | `ui_esco_picker.py:427` | ESCO-Suche aktuell nicht verfügbar: {...} |
| P2 | `esco` | `ui_esco_picker.py:433` | Der Begriff wurde gesucht, aber es wurde kein passender Beruf gefunden. Bitte Sprache umschalten (DE/EN), einen kürzeren Suchbegriff ohne Klammer-Kontext testen oder die Einstellungen prüfen. |
| P2 | `esco` | `ui_esco_picker.py:443` | Diagnose: language={...} · selected_version={...} · fallback_used={...} · cleaned_query_fallback_used={...} |
| P2 | `esco` | `ui_esco_picker.py:492` | Keine Vorschläge verfügbar |
| P2 | `esco` | `ui_esco_picker.py:537` | Noch keine Vorschläge ausgewählt. |
| P2 | `esco` | `ui_esco_picker.py:539` | **Vorschau der Auswahl (noch nicht bestätigt):** |
| P2 | `esco` | `ui_esco_picker.py:544` | {...} · URI: {...} · Quelle: {...} |
| P2 | `esco` | `ui_esco_picker.py:593` | Auswahl konnte nicht validiert werden. Bitte erneut auswählen. |
| P2 | `esco` | `ui_esco_picker.py:668` | **Bestätigter Referenzberuf** |
| P2 | `esco` | `ui_esco_picker.py:671` | URI: {...} · Version: {...} · Quelle: {...} |
| P2 | `esco` | `ui_esco_picker.py:674` | **Position im Berufsverzeichnis** |
| P2 | `esco` | `ui_esco_picker.py:690` | {...} · URI: {...} · Version: {...} · Quelle: {...} |
| P2 | `esco` | `wizard_pages/esco_occupation_ui.py:1537` | Ein eindeutiger Referenzberuf reduziert Mehrdeutigkeit und wird in den nächsten Schritten für Aufgaben, Skills und Summary weiterverwendet. |
| P2 | `esco` | `wizard_pages/esco_occupation_ui.py:1586` | Berufsabgleich übersprungen: Jobspec- und AI-Schritte bleiben nutzbar; berufsbezogene Normalisierung und technische ESCO-Exporte bleiben deaktiviert. |
| P2 | `esco` | `wizard_pages/esco_occupation_ui.py:1775` | Der Berufsabgleich ordnet die Rolle einem standardisierten Referenzberuf zu. So bleiben ähnliche Jobtitel und Anforderungen in den nächsten Schritten vergleichbar. |
| P2 | `esco` | `wizard_pages/esco_occupation_ui.py:1785` | **Quellen**: ESCO Web-Service API, Offline ESCO Index, Occupations pillar, Skills & Competences pillar, Skills–Occupations Matrix Tables |
| P2 | `salary` | `wizard_pages/salary_forecast_panel.py:939` | Kontext: indikative Prognose basierend auf den gewählten Angaben. / Fehlende Inputs können die Prognosequalität reduzieren. |
| P2 | `ui` | `ui_badges.py:219` | Sicherheit: {...} |
| P2 | `ui` | `ui_fact_review.py:261` | Hinweis: Abhängigkeiten oder aktueller Umfang können Detailfragen ausblenden. |
| P2 | `ui` | `ui_fact_review.py:398` | {...} Beantwortet {...}/{...} |
| P2 | `ui` | `ui_fact_review.py:403` | {...} Pflichtangaben {...}/{...} |
| P2 | `ui` | `ui_fact_review.py:410` | {...} Gruppen {...} vollständig · {...} offen |
| P2 | `ui` | `ui_fact_review.py:415` | • Keine Gruppen |
| P2 | `ui` | `ui_fact_review.py:419` | • Beantwortet {...}/{...} |
| P2 | `ui` | `ui_fact_review.py:423` | ##### ⚠️ Pflichtangaben offen |
| P2 | `ui` | `ui_fact_review.py:433` | +{...} weitere |
| P2 | `ui` | `ui_fact_review.py:435` | Betroffene Gruppen: {...} |
| P2 | `ui` | `ui_fact_review.py:440` | Noch keine sichtbaren Antworten vorhanden. |
| P2 | `ui` | `ui_fact_review.py:457` | {...} offene Frage(n) – Details und direkte Eingabe im Bereich „Details je Bereich“. |
| P2 | `ui` | `ui_fact_review.py:464` | Details je Bereich |
| P2 | `ui` | `ui_fact_review.py:490` | Noch keine bestätigten Antworten in dieser Gruppe. |
| P2 | `ui` | `ui_fact_review.py:516` | Zu prüfen: {...}{...} |
| P2 | `ui` | `ui_fact_review.py:518` | **Offene Fragen direkt beantworten** |
| P2 | `ui` | `ui_fact_review.py:526` | {...} offene Frage(n) in dieser Gruppe. |
| P2 | `ui` | `ui_feedback.py:22` | Debug (non-sensitive) |
| P2 | `ui` | `ui_feedback.py:23` | Nur technische Metadaten, keine Inhalte (kein Prompt/PII). |
| P2 | `ui` | `ui_inputs.py:840` | Aktuell sind keine Fragen sichtbar. Prüfe vorherige Antworten oder fahre mit dem nächsten Schritt fort. |
| P2 | `ui` | `ui_inputs.py:931` | {...} offen |
| P2 | `ui` | `ui_inputs.py:1239` | Bitte präzisieren … |
| P2 | `ui` | `ui_inputs.py:1239` | Bitte spezifizieren |
| P2 | `ui` | `ui_inputs.py:1289` | Bitte präzisieren … |
| P2 | `ui` | `ui_inputs.py:1289` | Bitte spezifizieren |
| P2 | `ui` | `ui_inputs.py:1339` | Rationale: {...} |
| P2 | `ui` | `ui_job_extract.py:78` | ### Identifizierte Informationen |
| P2 | `ui` | `ui_job_extract.py:154` | Alle {...} Einträge anzeigen |
| P2 | `ui` | `ui_job_extract.py:171` | ### Analyseergebnis |
| P2 | `ui` | `ui_job_extract.py:172` | Die wichtigsten Angaben sind nach Themen gruppiert. Die Prüfung fokussiert auf Sicherheit, offene Punkte und direkte Korrektur. |
| P2 | `ui` | `ui_job_extract.py:256` | Keine verlässlichen Werte erkannt. Details siehe Gaps/Assumptions. |
| P2 | `ui` | `ui_job_extract.py:260` | Kompaktansicht für lange Listen. Gezeigt werden zunächst die Top 5 Einträge. |
| P2 | `ui` | `ui_job_extract.py:294` | Alle {...} Einträge anzeigen |
| P2 | `ui` | `ui_job_extract.py:304` | Extrahierte Werte können hier direkt angepasst werden. Änderungen werden sofort gespeichert. |
| P2 | `ui` | `ui_job_extract.py:310` | Skills & Benefits |
| P2 | `ui` | `ui_job_extract.py:358` | Keine extrahierten Basiswerte mit Inhalt vorhanden. |
| P2 | `ui` | `ui_job_extract.py:406` | Keine extrahierten Standort-/Org-Werte mit Inhalt vorhanden. |
| P2 | `ui` | `ui_job_extract.py:494` | Einige Eingaben sind ungültig und wurden nicht übernommen. Bitte Felder prüfen. |
| P2 | `ui` | `ui_job_extract.py:514` | Wird automatisch aus dem Detailgrad berechnet ({...}) |
| P2 | `ui` | `ui_job_extract.py:536` | Maximal {...} verfügbare Fragen in diesem Step. |
| P2 | `ui` | `ui_layout.py:258` | ⬜ Offen |
| P2 | `ui` | `ui_layout.py:259` | 0/0 beantwortet |
| P2 | `ui` | `ui_layout.py:264` | {...}/{...} beantwortet |
| P2 | `ui` | `ui_layout.py:267` | Fehlt (essentiell): {...} |
| P2 | `ui` | `ui_layout.py:613` | Annahme prüfen |
| P2 | `ui` | `ui_layout.py:620` | Annahme prüfen |
| P2 | `ui` | `ui_layout.py:634` | Korrekte Annahme oder Klarstellung eintragen |
| P2 | `ui` | `ui_requirement_board.py:121` | Begriff eingeben… |
| P2 | `ui` | `ui_requirement_board.py:121` | Filtert Vorschläge direkt nach Bezeichnung und Hinweisen. |
| P2 | `ui` | `ui_requirement_board.py:128` | Nur neue Vorschläge |
| P2 | `wizard.skills` | `wizard_pages/05_skills.py:2002` | ESCO-Anker ist bestätigt, aber die Occupation-Payload ist unvollständig oder veraltet. Bitte ESCO-Auswahl erneut synchronisieren (Start → Phase C). |
| P2 | `wizard.skills` | `wizard_pages/05_skills.py:2041` | ESCO-Vorschläge sind aktuell nicht verfügbar. Du kannst mit manueller Auswahl weiterarbeiten oder später erneut versuchen. |
| P2 | `wizard.skills` | `wizard_pages/05_skills.py:2707` | Automatische Skill-Vorschläge basieren auf dem im Start bestätigten Referenzberuf: {...}. Übernommene Skills fließen in Zusammenfassung, Matching, Interviewfragen und Gehaltsprognose ein. |
| P2 | `wizard.start` | `wizard_pages/jobad_intake.py:890` | Der Upload wirkt wie gemischte Research- oder Interviewnotizen statt wie eine reine Stellenanzeige. Bitte prüfen Sie die erkannten Werte besonders sorgfältig, bevor Sie sie in den Wizard übernehmen. |
| P2 | `wizard.start` | `wizard_pages/jobad_intake.py:1021` | Die Buckets trennen belegte Upload-Fundstellen, unsichere Ableitungen, offene Lücken und explizite Annahmen. ESCO-/Kontextvorschläge erscheinen separat als bestätigungspflichtige Vorschläge. |
| P2 | `wizard.start` | `wizard_pages/jobad_intake.py:1051` | Prüfen Sie unsichere und offene Angaben vor dem Weiterarbeiten. Die Spalten entsprechen den nächsten Wizard-Schritten; korrigieren Sie Werte direkt in der passenden Spalte oder löschen Sie eine Zeile, wenn die Angabe nicht übernommen werden soll. Änderungen werden automatisch gespeichert. |
| P2 | `wizard.start` | `wizard_pages/jobad_intake.py:1108` | Die wichtigsten Angaben sind vorbereitet. Prüfen Sie unsichere und offene Punkte direkt in der Tabelle und bestätigen Sie anschließend den passenden Beruf für den Abgleich. |
| P2 | `wizard.start` | `wizard_pages/jobad_intake.py:1510` | Mithilfe der ESCO-Taxonomie nutzt diese App einen standardisierten Berufs- und Skill-Bezug. Sie bestätigen nur den passenden Referenzberuf; Aufgaben- und Skill-Vorschläge werden danach automatisch daraus abgeleitet. |
| P2 | `wizard.start` | `wizard_pages/jobad_intake.py:1522` | Die europäische mehrsprachige Klassifikation von Skills, Kompetenzen, Qualifikationen und Berufen der Europäischen Kommission. |
| P2 | `wizard.start` | `wizard_pages/jobad_intake.py:1526` | ESCO funktioniert wie ein Wörterbuch: Es beschreibt, identifiziert und klassifiziert 3.039 berufliche Tätigkeiten und 13.939 damit verknüpfte Skills, übersetzt in 28 Sprachen. |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:29` | **Kurzprofil:** {...} |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:30` | **Einstellungskontext** |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:32` | **Rollenzusammenfassung** |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:35` | **Wichtigste Aufgaben** |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:39` | **Must-have** |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:43` | **Nice-to-have** |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:47` | **Ausschlusskriterien** |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:51` | **Interviewplan** |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:55` | **Bewertungsraster** |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:59` | **Risiken / offene Fragen** |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:63` | **Stellenanzeigenentwurf (DE)** |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:78` | **Strukturierte Daten** |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:79` | Kompakte Vorschau. Der vollständige Export-JSON steht im Bereich „Export“ bereit. |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:84` | **JSON anzeigen** |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:87` | JSON herunterladen |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:96` | **Rolle:** {...} · **Phase:** {...} · **Dauer:** {...} Min. |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:100` | **Einstiegsskript** |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:103` | **Frageblöcke** |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:105` | Keine Frageblöcke vorhanden. |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:108` | Ziel: {...} |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:118` | **Knockout-Kriterien** |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:123` | Keine Knockout-Kriterien hinterlegt. |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:125` | **Bewertungsrubrik** |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:127` | Keine Bewertungsrubrik vorhanden. |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:134` | Skala: {...} |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:136` | Beobachtbare Evidenz: |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:140` | **Empfehlungsoptionen** |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:145` | Keine finalen Empfehlungsoptionen hinterlegt. |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:149` | **Rolle:** {...} · **Phase:** {...} · **Dauer:** {...} Min. |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:154` | **Kompetenzen validieren** |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:159` | Keine zu validierenden Kompetenzen hinterlegt. |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:161` | **Frageblöcke** |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:163` | Keine Frageblöcke vorhanden. |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:166` | Ziel: {...} |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:176` | **Fachliche Vertiefungsthemen** |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:181` | Keine Deep-Dive-Themen hinterlegt. |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:183` | **Case-/Aufgabenbriefing** |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:187` | Kein Case-/Aufgabenbriefing hinterlegt. |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:189` | **Bewertungsrubrik** |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:191` | Keine Bewertungsrubrik vorhanden. |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:198` | Skala: {...} |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:200` | Beobachtbare Evidenz: |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:204` | **Debrief-Fragen** |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:209` | Keine Debrief-Fragen hinterlegt. |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:241` | Keine Suchstrings vorhanden. |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:246` | Suchstring {...} |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:251` | ### Suchbegriffe |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:268` | ### Nutzungshinweise |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:273` | Keine Nutzungshinweise hinterlegt. |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:277` | ### Risiken |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:282` | Keine kanalbezogenen Einschränkungen hinterlegt. |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:303` | ## Suchstrings |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:305` | Rolle: {...} · Zielregionen: {...} |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:308` | Keine Suchstrings vorhanden. |
| P2 | `wizard.summary` | `ui_summary_artifacts.py:311` | ### Kanalvarianten |
| P2 | `wizard.summary` | `wizard_pages/summary_view.py:2204` | **Pipeline:** `Recruiting Brief` → `HR-Sheet/Fachbereich-Sheet` → `Suchstrings` → `Export` / Status Recruiting Brief: {...} · {...} |
| P3 | `common` | `wizard_pages/01a_jobspec_review.py:91` | Extraktionsqualität: {...} ({...}/{...} Kernfelder gefüllt). |
| P3 | `common` | `wizard_pages/01a_jobspec_review.py:110` | Identifizierte Informationen |
| P3 | `common` | `wizard_pages/01a_jobspec_review.py:111` | Hier prüfst und ergänzt du die extrahierten Inhalte, Gaps und Assumptions, bevor du in den Schritt 'Unternehmen' wechselst. |
| P3 | `common` | `wizard_pages/01a_jobspec_review.py:117` | **Jobtitel:** {...} |
| P3 | `common` | `wizard_pages/01a_jobspec_review.py:127` | Falls ESCO gerade nicht verfügbar ist, kannst du mit den vorhandenen Jobspec-Informationen manuell fortfahren und später erneut versuchen. |
| P3 | `common` | `wizard_pages/01a_jobspec_review.py:135` | Fragen pro Step |
| P3 | `common` | `wizard_pages/01a_jobspec_review.py:138` | Fragen pro Step |
| P3 | `common` | `wizard_pages/01a_jobspec_review.py:143` | QuestionPlan geladen: {...} Fragen in {...} Steps. |
| P3 | `common` | `wizard_pages/03_team.py:36` | Keine verlässlichen Werte erkannt. Details siehe Gaps/Assumptions. |

## Maintenance Notes

- Keep `locales/de.json` and `locales/en.json` leaf-key shapes identical.
- Keep placeholder names aligned between DE and EN values.
- Keep required `ux_copy.steps.*` and inline `ux_copy_contract.py` entries aligned for DE and EN.
- Prefer `tr("dotted.key")` for new public-page and reusable UI copy.
- Existing German-source wizard copy may stay on `t(text)` until migrated deliberately.
- Changed `wizard_pages/*.py` lines fail the raw UI guard when direct Streamlit UI literals are introduced without translation. Use `tr(...)`, `tr_safe(...)`, `t(...)`, or `ux_copy_contract.py`; intentional exceptions require `# i18n: allow-raw-ui <reason>` on the same or previous line, or a reviewed backlog entry in this document.
- When migrating a gap item, update UI, state-dependent labels, exports, prompt construction, and tests together when they share copy semantics.
