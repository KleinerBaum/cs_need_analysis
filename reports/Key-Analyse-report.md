# Vollständige Key-Analyse für das Repo cs_need_analysis

## Wichtigste Befunde

Ich habe die Repository-Struktur statisch entlang des kanonischen Fact-Contracts ausgewertet. Für die fachliche Informationsgewinnung ist `constants.py` die zentrale Quelle: Dort ist ausdrücklich festgehalten, dass diese Datei die *Single Source of Truth* für Session-State-Keys, Wizard-Step-IDs, Frage-/Antworttypen und Schema-Versionen ist. Im selben Contract sind die aktiven Wizard-Schritte sowie die kanonischen `FactKey`-Einträge definiert. Auf dieser Basis ergibt sich für die App ein klarer Unterschied zwischen **fachlichen Schlüsselinformationen** und **technischen State-Keys**. Fachlich relevant für deinen Prozess sind vor allem die kanonischen `FactKey`-Einträge; technische `SSKey`-Einträge steuern dagegen Navigation, Cache, Summary-Status, Salary-Scenario-State, ESCO-State und andere UI-/Runtime-Aspekte. citeturn5view0turn4view0

Für die fachliche Ebene ist das wichtigste Ergebnis: Das Repo besitzt einen **kanonischen Intake-Fact-Registry-Ansatz**. Diese Fakten werden in `INTAKE_FACTS` modelliert, in `intake_facts.py` persistiert, zum Teil bereits in Schritt 1 automatisch aus dem geprüften Jobspec gespiegelt und in der Zusammenfassung wieder zusammengesetzt. Außerdem zeigt die Salary-Engine, dass nur ein Teil der Keys die Gehaltsprognose **direkt** treibt; viele andere Keys beeinflussen die Prognose nur **indirekt** über die Zahl sinnvoll befüllter Antworten, was auf Unsicherheit, Spread und Datenqualität wirkt. citeturn5view0turn8view2turn8view3turn8view0turn7view0

Die wichtigste operative Schlussfolgerung ist deshalb: Für deinen nächsten Verbesserungsschritt solltest du die Keys nicht mehr als eine einzige homogene Liste behandeln, sondern in vier Klassen organisieren: **Auto-fill in Schritt 1**, **manuell/gezielt zu klären**, **Summary-explizit sichtbar**, **Salary-relevant**. Genau dafür ist die folgende Matrix gebaut. Die Summary baut explizite Fact-Zeilen für viele, aber nicht alle Keys; zusätzlich gibt es dynamische Frage-Antwort-Zeilen. Deshalb markiere ich die Summary-Spalte bewusst als **Ja, explizit**, **Bedingt**, oder **Nein / derzeit nicht explizit**. Die Salary-Spalte unterscheidet bewusst zwischen **direkter P50-/Treiberwirkung** und **indirekter Qualitäts-/Unsicherheitswirkung**. citeturn8view1turn9view1turn9view3turn8view0turn7view0

## Leselogik der Matrix

**Schritt** meint den fachlichen Wizard-Schritt, dem der Key im kanonischen Fact-Contract zugeordnet ist.  
**Schritt 1** meint den Start-Flow inklusive Jobspec-Extraktion/Review/Promotion. Ein `Ja` bedeutet hier: Der Key wird bereits aus dem reviewed job extract in den Intake-Fact-State gespiegelt oder im Start-Routing aktiv erfasst. `intake_facts.py` definiert dafür ein explizites `_JOB_EXTRACT_FACT_FIELDS`-Mapping und `write_job_extract_intake_facts(...)`; `jobad_intake.py` ruft diese Spiegelung im Start-Flow sowie nach der Promotion des reviewed Extracts auf. citeturn8view2turn10view0turn10view1turn8view3

**Hauptfunktionen** nennen die aus fachlicher Sicht wichtigsten Runtime-Funktionen, die den Key lesen, schreiben, rendern oder weiterverarbeiten. Ich liste hier bewusst die **wichtigsten** Nutzerfunktionen, nicht jede generische Registry-Funktion. Generisch gelten praktisch für alle Facts die Registry-/Persistenzpfade rund um `write_intake_fact(...)`, `get_intake_fact_state(...)`, `fact_value(...)` und – bei UI-Fact-Inputs – `persist_fact(...)` plus `set_answer(...)`. `persist_fact(...)` schreibt den Wert zugleich in die Antworten und in den Fact-State; genau deshalb können viele manuell befüllte Keys später indirekt die Prognosequalität beeinflussen. citeturn10view2turn7view0turn7view1turn8view0

**Summary** ist konservativ gelesen:
- **Ja, explizit** = der Key hat eine klar erkennbare Fact-Zeile in `_build_summary_fact_rows(...)`.
- **Bedingt** = kein eigener expliziter Fact-Row, aber potenziell über generische Frage-/Antwort-Darstellung oder indirekte Artifakte sichtbar.
- **Nein / derzeit nicht explizit** = im aktuellen Code kein klarer eigener Summary-Fact-Row.  
**Gehaltsprognose** ist zweigeteilt:
- **P50 direkt** = der Key beeinflusst die eigentliche Salary-Berechnung direkt.
- **Qualität indirekt** = der Key wirkt eher auf `answers_count`, Confidence oder Spread.
- **Nein** = aktuell kein klarer Einfluss in der Salary-Engine. citeturn8view1turn8view0turn7view0

## Start und Unternehmen

Die Start- und Unternehmenslogik ist der Bereich mit dem größten Hebel für Automatisierung. Hier liegen die Routing-Facts, der Großteil des Schritt-1-Autofills aus dem reviewed Jobspec sowie die Website-Anreicherung. `jobad_intake.py` promoted reviewed Extract-Werte in Antworten und Fact-State; `intake_facts.py` enthält das explizite Mirror-Mapping aus dem Jobspec; `homepage_research.py` baut zusätzlich Website-Kandidaten für mehrere Company-/Context-Keys. Gleichzeitig zeigt die Summary-Datei, dass viele dieser Werte explizit in der Faktenübersicht auftauchen, während einige Extract-only-Felder derzeit nur bedingt sichtbar sind. citeturn8view3turn8view2turn8view4turn8view1

### Start

| Key | Schritt | Schritt 1 | Hauptfunktionen | Summary | Gehaltsprognose | Hinweis |
|---|---|---:|---|---|---|---|
| `intake.hiring_reason` | Start | Ja | `_render_start_routing_controls`; `classify_occupation_context` | Ja, explizit | Qualität indirekt | Routing-/Priorisierungsfakt |
| `intake.urgency` | Start | Ja | `_render_start_routing_controls`; `classify_occupation_context` | Ja, explizit | Qualität indirekt | Routing-/Dringlichkeitsfakt |
| `intake.hiring_volume` | Start | Ja | `_render_start_routing_controls`; `classify_occupation_context` | Ja, explizit | Qualität indirekt | Kapazitäts-/Volumenfakt |
| `intake.search_confidentiality` | Start | Ja | `_render_start_routing_controls`; `classify_occupation_context` | Ja, explizit | Qualität indirekt | **Sensitivity: restricted** |
| `intake.role_definition_maturity` | Start | Ja | `_render_start_routing_controls`; `classify_occupation_context` | Ja, explizit | Qualität indirekt | Routing-/Reifegradfakt |

### Unternehmen und Team

| Key | Schritt | Schritt 1 | Hauptfunktionen | Summary | Gehaltsprognose | Hinweis |
|---|---|---:|---|---|---|---|
| `company.language_guess` | Unternehmen | Ja | `write_job_extract_intake_facts` | Bedingt | Nein | Extract-only Startwert |
| `company.company_name` | Unternehmen | Ja | `write_job_extract_intake_facts`; `build_website_fact_candidates` | Ja, explizit | Nein | Website-anreicherbar |
| `company.brand_name` | Unternehmen | Ja | `write_job_extract_intake_facts` | Bedingt | Nein | Extract-only / Summary nicht explizit |
| `company.company_website` | Unternehmen | Ja | `write_job_extract_intake_facts`; `build_website_fact_candidates` | Ja, explizit | Nein | Website-anreicherbar |
| `company.location_city` | Unternehmen | Ja | `write_job_extract_intake_facts`; `build_website_fact_candidates` | Ja, explizit | **P50 direkt** | Benchmark-/Regionseinfluss |
| `company.location_country` | Unternehmen | Ja | `write_job_extract_intake_facts`; `build_website_fact_candidates` | Ja, explizit | **P50 direkt** | Benchmark-/Regionseinfluss |
| `company.place_of_work` | Unternehmen | Ja | `write_job_extract_intake_facts` | Ja, explizit | Nein | In Summary sichtbar, nicht Salary-wirksam |
| `company.remote_policy` | Unternehmen | Ja | `write_job_extract_intake_facts` | Ja, explizit | **P50 direkt** | Remote-Multiplier |
| `company.work_arrangement` | Unternehmen | Nein | `_render_structured_company_context`; `build_website_fact_candidates` | Ja, explizit | Qualität indirekt | Stark für Matching/Policy |
| `company.office_days_per_week` | Unternehmen | Nein | `_render_structured_company_context`; `build_website_fact_candidates` | Ja, explizit | Qualität indirekt | Website-anreicherbar |
| `company.allowed_regions_timezones` | Unternehmen | Nein | `_render_structured_company_context`; `build_website_fact_candidates` | Ja, explizit | Qualität indirekt | Website-anreicherbar |
| `company.employer_pitch` | Unternehmen | Nein | `_render_structured_company_context`; `build_website_fact_candidates` | Ja, explizit | Qualität indirekt | Website-anreicherbar |
| `company.role_relevant_positioning` | Unternehmen | Nein | `_render_structured_company_context`; `build_website_fact_candidates` | Ja, explizit | Qualität indirekt | Website-anreicherbar |
| `company.business_unit` | Unternehmen | Nein | `_render_structured_company_context` | Ja, explizit | Qualität indirekt | Organisationskontext |
| `company.language_internal` | Unternehmen | Nein | `_render_language_fact`; `build_website_fact_candidates` | Ja, explizit | Qualität indirekt | Website-anreicherbar |
| `company.language_external` | Unternehmen | Nein | `_render_language_fact` | Ja, explizit | Qualität indirekt | Kommunikationskontext |
| `company.non_negotiables` | Unternehmen | Nein | `_render_structured_company_context` | Ja, explizit | Qualität indirekt | Gute KO-/Hard-Constraint-Info |
| `company.compliance_context` | Unternehmen | Nein | `_render_structured_company_context`; `build_website_fact_candidates` | Ja, explizit | Qualität indirekt | Website-anreicherbar |
| `company.tariff_context` | Unternehmen | Nein | `_render_structured_company_context` | Ja, explizit | Qualität indirekt | Tarif-/Regelwerk-Kontext |
| `company.department_name` | Unternehmen | Ja | `write_job_extract_intake_facts` | Bedingt | Nein | Extract-only / Summary nicht explizit |
| `company.reports_to` | Unternehmen | Ja | `write_job_extract_intake_facts` | Bedingt | Nein | Extract-only / Summary nicht explizit |
| `company.direct_reports_count` | Unternehmen | Ja | `write_job_extract_intake_facts` | Bedingt | Nein | Extract-only / Summary nicht explizit |
| `team.name` | Unternehmen | Nein | `_render_structured_company_context` | Ja, explizit | Qualität indirekt | Team-Kontext |
| `team.leadership_scope` | Unternehmen | Nein | `_render_structured_company_context` | Ja, explizit | Qualität indirekt | Führungsumfang |
| `team.size_direct` | Unternehmen | Nein | `_render_structured_company_context` | Ja, explizit | Qualität indirekt | Teamgröße |
| `team.stakeholders_primary` | Unternehmen | Nein | `_render_structured_company_context` | Ja, explizit | Qualität indirekt | Stakeholder-Landkarte |
| `team.success_context_90d` | Unternehmen | Nein | `_render_structured_company_context` | Ja, explizit | Qualität indirekt | 90-Tage-Kontext |

Ein zusätzlicher Befund mit hohem Prozesswert: Die Company-Seite unterstützt in `_render_website_fact_review(...)` eine **kanonische Website-Review-Schleife**, in der erkannte Website-Funde einem FactKey zugeordnet, geprüft und dann persisted werden. Das ist für deinen Informationsgewinnungsprozess besonders wichtig, weil es zeigt, welche Keys sich gezielt aus einer zweiten, unabhängigen Quelle anreichern lassen. Aktuell betrifft das vor allem Company-Context, einige Role-Context-Felder und sogar `benefits.benefits`. citeturn8view4turn7view2

## Rolle und Skills

Rollen- und Skill-Keys sind der zweite große Kernblock. Ein Teil davon wird in Schritt 1 bereits aus dem Jobspec gespiegelt; ein anderer Teil wird in dedizierten UI-Blöcken strukturiert erfasst. Für Salary besonders relevant ist hier: Jobtitel, Seniorität, Must-/Nice-to-have-Skills, Zertifikate und Sprachen wirken direkt in die Salary-Engine hinein. Andere Role-/Skill-Felder wirken vor allem indirekt über bessere Antwortabdeckung, Matching, Summary-Qualität oder spätere Artefaktgenerierung. citeturn8view2turn8view0turn7view0

### Rolle und Aufgaben

| Key | Schritt | Schritt 1 | Hauptfunktionen | Summary | Gehaltsprognose | Hinweis |
|---|---|---:|---|---|---|---|
| `role.job_title` | Rolle & Aufgaben | Ja | `write_job_extract_intake_facts` | Ja, explizit | **P50 direkt** | Benchmark-Lookup + Titelfaktor |
| `role.employment_type` | Rolle & Aufgaben | Ja | `write_job_extract_intake_facts` | Ja, explizit | Nein | Wichtig für Artefakte, nicht Salary-core |
| `role.contract_type` | Rolle & Aufgaben | Ja | `write_job_extract_intake_facts` | Ja, explizit | Nein | Wichtiger Export-/Artefaktwert |
| `role.seniority_level` | Rolle & Aufgaben | Ja | `write_job_extract_intake_facts` | Ja, explizit | **P50 direkt** | Baseline + Seniority-Multiplier |
| `role.job_ref_number` | Rolle & Aufgaben | Ja | `write_job_extract_intake_facts` | Bedingt | Nein | Referenz-/Trackingfeld |
| `role.role_overview` | Rolle & Aufgaben | Ja | `write_job_extract_intake_facts` | Bedingt | Nein | Gute Summary-Lücke |
| `role.responsibilities` | Rolle & Aufgaben | Ja | `write_job_extract_intake_facts` | Bedingt | Qualität indirekt | `responsibilities_count` wirkt auf Confidence |
| `role.responsibilities_prioritized` | Rolle & Aufgaben | Nein | `_render_structured_role_scope` | Ja, explizit | Qualität indirekt | Sehr guter Priorisierungstreiber |
| `role.deliverables` | Rolle & Aufgaben | Ja | `write_job_extract_intake_facts` | Bedingt | Nein | Gute Summary-Lücke |
| `role.success_metrics` | Rolle & Aufgaben | Ja | `write_job_extract_intake_facts` | Bedingt | Nein | Gute Summary-Lücke |
| `role.success_metrics_timeline` | Rolle & Aufgaben | Nein | `_render_structured_role_scope` | Ja, explizit | Qualität indirekt | Strukturierter Erfolgspfad |
| `role.business_outcome_primary` | Rolle & Aufgaben | Nein | `_render_structured_role_scope` | Ja, explizit | Qualität indirekt | Business-Zielschärfe |
| `role.day1_responsibilities` | Rolle & Aufgaben | Nein | `_render_structured_role_scope` | Ja, explizit | Qualität indirekt | Onboarding-/Ramp-up-Qualität |
| `role.expansion_scope` | Rolle & Aufgaben | Nein | `_render_structured_role_scope` | Ja, explizit | Qualität indirekt | Scope-Entwicklung |
| `role.decision_scope` | Rolle & Aufgaben | Nein | `_render_structured_role_scope` | Ja, explizit | Qualität indirekt | Senkt Fehlinterpretation |
| `role.year1_success_signals` | Rolle & Aufgaben | Nein | `_render_structured_role_scope` | Ja, explizit | Qualität indirekt | Outcome-/KPI-Reife |
| `role.tech_stack` | Rolle & Aufgaben | Ja | `write_job_extract_intake_facts`; `build_website_fact_candidates` | Bedingt | Nein | Website-anreicherbar; Salary nicht direkt |
| `role.domain_expertise` | Rolle & Aufgaben | Ja | `write_job_extract_intake_facts`; `build_website_fact_candidates` | Bedingt | Nein | Website-anreicherbar |
| `role.travel_required` | Rolle & Aufgaben | Ja | `write_job_extract_intake_facts` | Bedingt | Nein | Gute Summary-Lücke |
| `role.travel_profile` | Rolle & Aufgaben | Nein | `_render_travel_profile` | Ja, explizit | Nein | Strukturierter als travel_required |
| `role.on_call` | Rolle & Aufgaben | Ja | `write_job_extract_intake_facts` | Bedingt | Nein | Extract-only / Summary-Lücke |
| `role.onboarding_notes` | Rolle & Aufgaben | Ja | `write_job_extract_intake_facts` | Bedingt | Nein | Gute Summary-Lücke |
| `role.gaps` | Rolle & Aufgaben | Ja | `write_job_extract_intake_facts` | Bedingt | Nein | Für Unsicherheitsmanagement wertvoll |
| `role.assumptions` | Rolle & Aufgaben | Ja | `write_job_extract_intake_facts` | Bedingt | Nein | Explizite Annahmen, aber keine klare Summary-Zeile |

### Skills und Anforderungen

| Key | Schritt | Schritt 1 | Hauptfunktionen | Summary | Gehaltsprognose | Hinweis |
|---|---|---:|---|---|---|---|
| `skills.items` | Skills & Anforderungen | Nein | `_render_structured_skill_rows` | Ja, explizit | Qualität indirekt | Sehr wertvoller strukturierter Skill-Container |
| `skills.must_have_skills` | Skills & Anforderungen | Ja | `write_job_extract_intake_facts`; `sync_selected_skill_intake_facts` | Ja, explizit | **P50 direkt** | Requirements-Density + Skill-Premiums |
| `skills.nice_to_have_skills` | Skills & Anforderungen | Ja | `write_job_extract_intake_facts`; `sync_selected_skill_intake_facts` | Ja, explizit | **P50 direkt** | Skill-Premium-Logik berücksichtigt auch Nice-to-have |
| `skills.soft_skills` | Skills & Anforderungen | Ja | `write_job_extract_intake_facts` | Bedingt | Nein | Gute Summary-Lücke |
| `skills.education` | Skills & Anforderungen | Ja | `write_job_extract_intake_facts` | Bedingt | Nein | Gute Summary-Lücke |
| `skills.certifications` | Skills & Anforderungen | Ja | `_render_structured_skill_rows`; `write_job_extract_intake_facts` | Bedingt | **P50 direkt** | Bestandteil von `requirements_density` |
| `skills.languages` | Skills & Anforderungen | Ja | `write_job_extract_intake_facts` | Ja, explizit | **P50 direkt** | Bestandteil von `requirements_density` |
| `skills.readiness_timing` | Skills & Anforderungen | Nein | `_render_structured_skill_rows` | Ja, explizit | Qualität indirekt | Sehr nützlich für Trainability |
| `skills.free_text_reason` | Skills & Anforderungen | Nein | `_render_structured_skill_rows` | Ja, explizit | Qualität indirekt | Begründungsqualität |
| `skills.knockout_criteria` | Skills & Anforderungen | Nein | `_render_structured_skill_rows` | Ja, explizit | Qualität indirekt | Stark für Screening |
| `skills.trainable_skills` | Skills & Anforderungen | Nein | `_render_structured_skill_rows` | Ja, explizit | Qualität indirekt | Gute Hiring-Strategie-Info |

## Benefits und Interview

Benefits- und Interview-Keys sind für die spätere operative Qualität der Artefakte besonders stark, aber nur einzelne Felder treiben die Salary-Engine direkt. Die Salary-Engine berücksichtigt explizit Gehaltsband, Interviewschritte und über Scenario-Inputs außerdem Remote-Anteil, Suchradius und Seniority-Overrides. Interview- und Benefit-Daten werden in der Summary sehr sichtbar gemacht, was diesen Bereich zu einem guten Kandidaten für stärkere Validierung, Pflichtfelder und Confidence-Gating macht. citeturn8view0turn8view1

### Benefits und Rahmenbedingungen

| Key | Schritt | Schritt 1 | Hauptfunktionen | Summary | Gehaltsprognose | Hinweis |
|---|---|---:|---|---|---|---|
| `benefits.salary_range` | Benefits & Rahmenbedingungen | Ja | `write_job_extract_intake_facts`; `_render_compensation_block` | Ja, explizit | **P50 direkt** | Stärkster Salary-Baseline-Treiber |
| `benefits.benefits` | Benefits & Rahmenbedingungen | Ja | `write_job_extract_intake_facts`; `build_website_fact_candidates` | Ja, explizit | Nein | Website-anreicherbar |
| `benefits.variable_pay` | Benefits & Rahmenbedingungen | Nein | `_render_variable_pay_block`; `_salary_trigger` | Ja, explizit | Nein | Salary-triggernd für Folgefragen, aber nicht Engine-core |
| `benefits.shift_compensation` | Benefits & Rahmenbedingungen | Nein | `_render_shift_compensation_block` | Ja, explizit | Nein | Gute arbeitsorganisatorische Info |
| `benefits.collective_agreement_context` | Benefits & Rahmenbedingungen | Nein | `_render_collective_context_block` | Ja, explizit | Nein | Regulierung/Tarif |
| `benefits.offer_components` | Benefits & Rahmenbedingungen | Nein | `_render_offer_components_block` | Ja, explizit | Nein | Offer-Komponenten |
| `legal.work_authorization_support` | Benefits & Rahmenbedingungen | Nein | `_render_work_authorization_block` | Ja, explizit | Nein | Sehr wichtig für Recruiting-Prozess |
| `timeline.start_flexibility` | Benefits & Rahmenbedingungen | Nein | `_render_start_flexibility_block` | Ja, explizit | Qualität indirekt | Gute Hiring-Planungsinfo |

### Interviewprozess

| Key | Schritt | Schritt 1 | Hauptfunktionen | Summary | Gehaltsprognose | Hinweis |
|---|---|---:|---|---|---|---|
| `interview.start_date` | Interviewprozess | Ja | `write_job_extract_intake_facts`; `_render_interview_timeline` | Ja, explizit | Nein | Für Time-to-hire relevant |
| `interview.application_deadline` | Interviewprozess | Ja | `write_job_extract_intake_facts`; `_render_interview_timeline` | Ja, explizit | Nein | Fristensteuerung |
| `interview.recruitment_steps` | Interviewprozess | Ja | `write_job_extract_intake_facts`; `_render_recruitment_steps`; `build_candidate_stage_values` | Ja, explizit | **P50 direkt** | Schrittzahl beeinflusst Interview-Multiplier |
| `interview.contacts` | Interviewprozess | Ja | `write_job_extract_intake_facts`; `_session_state_fact` | Bedingt | Nein | **Sensitivity: personal** |
| `interview.assessment_evidence` | Interviewprozess | Nein | `_render_assessment_evidence` | Ja, explizit | Nein | Prozess-/Diagnostikqualität |
| `interview.stage_owners` | Interviewprozess | Nein | `_render_stage_owners` | Ja, explizit | Nein | Verantwortlichkeiten |
| `interview.communication_sla` | Interviewprozess | Nein | `_render_communication_sla` | Ja, explizit | Nein | Candidate Experience |
| `interview.scorecard_template` | Interviewprozess | Nein | `_render_scorecard`; `_fallback_rubric_from_scorecard` | Ja, explizit | Nein | Starker Artefakt-/Interview-Prep-Wert |
| `interview.core_questions` | Interviewprozess | Nein | `_render_core_questions` | Ja, explizit | Nein | Interviewleitfaden |
| `interview.compliance_notes` | Interviewprozess | Nein | `_render_compliance_notes` | Ja, explizit | Nein | Governance-/Legal-Kontext |

## Was du zusätzlich pro Key wissen solltest

Die Liste oben beantwortet bereits deine Kernfragen. Für eine **herausragende** Steuerungsübersicht fehlen aber aus meiner Sicht noch einige Spalten, die dich operativ deutlich weiterbringen würden.

Zuerst brauchst du eine **Quelle-/Erstbefüllungs-Spalte** mit mindestens diesen Werten: `Jobspec`, `Manual`, `Homepage`, `ESCO`, `LLM`, `Derived`. Das Repo hat diese Denkfigur bereits im Fact-System angelegt, inklusive Confidence/Evidence-Mechanik beim Schreiben von Facts. Gerade für Prozessoptimierung ist das Gold wert, weil du damit sofort siehst, wo du zu stark von einer Quelle abhängig bist und welche Keys gut für Cross-Validation taugen. citeturn8view2

Dann lohnt sich eine **Sensitivity-/PII-Spalte**. Im aktuellen Fact-System sind mindestens `intake.search_confidentiality`, `benefits.salary_range` und `benefits.variable_pay` als `restricted` sowie `interview.contacts` als `personal` markiert. Diese Information sollte meiner Ansicht nach nicht nur technisch im Backend liegen, sondern in deiner Übersicht als Governance-Hinweis sichtbar sein. Gerade für Exporte, LLM-Prompts und HR-Freigaben ist das wichtig. citeturn10view3turn8view2

Außerdem empfehle ich dringend diese zusätzlichen Spalten:

| Zusatzspalte | Warum sie hilfreich ist |
|---|---|
| `Datentyp` | Zeigt sofort, ob der Key sauber strukturiert ist oder freie Texte erzeugt |
| `Source of truth` | Jobspec, manuell, Website, ESCO oder Derived |
| `Confidence vorhanden?` | Ob Evidence/Confidence im aktuellen Pfad gespeichert wird |
| `Verifikationsstatus` | automatisch erkannt, bestätigt, korrigiert, abgelehnt |
| `Summary-Modus` | explizite Fact-Zeile, nur generische Antwortzeile, gar nicht sichtbar |
| `Salary-Einflussart` | P50 direkt, nur Qualität/Spread, kein Einfluss |
| `Website-enrichable` | Ja/Nein; ideal für zweite Quelle |
| `Export-relevant` | Ob der Key in Brief/Artefakt-Generierung stark genutzt wird |
| `Lückenrisiko` | hoch, mittel, niedrig; ob fehlender Wert im Prozess stark schadet |
| `Empfohlene Pflichtigkeit` | optional, empfohlen, required |
| `Canonical label de` | Verhindert Drift zwischen UI, Summary und Export |
| `Owner` | Wer im Prozess typischerweise den Wert bestätigen muss |

Wenn du diese Metadaten ergänzst, wird aus einer reinen Key-Liste eine **Steuerungstabelle für Intake-Qualität**. Genau das dürfte dir am meisten helfen, den Informationsgewinnungsprozess gezielt zu verbessern. Die Codebasis ist dafür bereits vorbereitet, weil sie Facts, Evidence, Summary und verschiedene Enrichment-Quellen nicht lose, sondern als Contract behandelt. citeturn5view0turn8view2turn8view1

## Konkrete Prioritäten zur Verbesserung des Informationsgewinnungsprozesses

Die größte Hebelwirkung sehe ich an vier Stellen.

Der erste Hebel ist die **Summary-Lücke** bei mehreren bereits in Schritt 1 extrahierten Keys. Besonders auffällig sind `company.brand_name`, `company.department_name`, `company.reports_to`, `company.direct_reports_count`, `role.role_overview`, `role.deliverables`, `role.success_metrics`, `role.tech_stack`, `role.domain_expertise`, `role.travel_required`, `role.on_call`, `role.onboarding_notes`, `role.gaps`, `role.assumptions`, `skills.soft_skills`, `skills.education`, `skills.certifications` und `interview.contacts`. Diese Werte existieren fachlich bereits, haben aber derzeit keine klar explizite Summary-Fact-Zeile. Für Governance, Review und spätere Artefakterstellung ist das eine unnötige Blindstelle. citeturn8view1turn8view2

Der zweite Hebel ist die **Trennung von Salary-direkten und Salary-indirekten Keys**. Heute sind beide Klassen in der Praxis leicht zu verwechseln. Für Produktklarheit würde ich im UI und in deiner Steuerungstabelle deutlich markieren:  
`benefits.salary_range`, `role.seniority_level`, `company.remote_policy`, `company.location_city`, `company.location_country`, `role.job_title`, `skills.must_have_skills`, `skills.nice_to_have_skills`, `skills.certifications`, `skills.languages`, `interview.recruitment_steps` sind **Salary-Treiber**. Dagegen sind viele andere Keys vor allem **Qualitäts-/Unsicherheits-Treiber**, weil sie die Antwortabdeckung erhöhen. Das sollte für Nutzer sichtbar getrennt werden. citeturn8view0turn7view0

Der dritte Hebel ist die **aktive Nutzung der Website-Review als zweite Quelle**. Mehrere hochwertige Company-/Context-Keys lassen sich zusätzlich aus der Website anreichern. Das ist ideal, um früh gefüllte, aber unsichere Jobspec-Werte gegenzuprüfen und dabei Confidence plus Review-Nachvollziehbarkeit zu erhöhen. Für dich als Produktdesigner ist das besonders relevant, weil damit aus „Autofill“ ein **verifizierter Autofill** wird. citeturn8view4turn7view2

Der vierte Hebel ist ein **Pflichtigkeitsmodell pro Key**. Nicht jeder Key muss gleich früh erhoben werden. Für den operativen Nutzen würde ich mindestens drei Klassen definieren:
- **Pflicht vor Summary**: Salary-Treiber und rechtlich/prozessual kritische Keys
- **Pflicht vor Artefaktgenerierung**: z. B. Scorecard, Core Questions, Offer Components
- **Optional / opportunistisch**: Branding-, Pitch- und Zusatzkontext-Felder  
Diese Staffelung passt sehr gut zur vorhandenen Fact-/Summary-/Artifact-Architektur. citeturn8view1turn8view2turn8view0

## Grenzen und offene Fragen

Ein Punkt bleibt bewusst als Unsicherheitsmarker stehen: Für Keys ohne explizite Summary-Fact-Zeile ist im aktuellen Stand nicht immer eindeutig, ob sie über dynamische Frage-/Antwort-Zeilen zuverlässig sichtbar werden oder nur unter bestimmten Frageplan-Konstellationen. Deshalb habe ich solche Fälle konservativ als **Bedingt** markiert und nicht pauschal als „Ja“. Diese Unsicherheit entsteht nicht durch fehlende Analyse der Kernquellen, sondern durch die dynamische Natur des Question-Plans und seiner `fact_key`-Zuordnung im Laufzeitpfad. citeturn8view1turn7view0turn8view3

Ebenfalls wichtig: Diese Übersicht fokussiert die **fachlichen FactKeys**. Die App besitzt darüber hinaus eine große Zahl technischer `SSKey`-Einträge für Navigation, Caching, ESCO-State, Summary-State und Salary-Scenario-State. Für Prozessoptimierung sind diese technisch wichtig, aber sie beantworten nicht dieselbe fachliche Frage wie deine „Schlüsselinformationen“. Ich habe sie deshalb hier konzeptionell getrennt. `constants.py` macht genau diese Trennung in seiner Rolle als kanonischer Kontrakt bereits nachvollziehbar. citeturn5view0turn4view0