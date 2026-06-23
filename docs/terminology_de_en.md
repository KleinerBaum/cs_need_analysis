# DE/EN Terminology Mapping

Snapshot date: `2026-06-23`.

This glossary maps product terminology between German UI copy and English technical/product terms. It is documentation only and does not change runtime translation behavior.

## Usage Rules

- Use English technical identifiers in code and schemas.
- Preserve existing German UI copy unless a task explicitly changes wording.
- Prefer canonical constants/enums and existing i18n entries over duplicating string literals.
- Short Wizard headline and CTA copy should come from `ux_copy_contract.py`; retained `locales/*.json` UX-copy entries should stay aligned during migration work.
- `canonical` means the term pair is already represented in code, Locale files, or `i18n.py`.
- `proposed` means the English code/source term exists, but the German counterpart is glossary guidance until a future localization migration makes it canonical.

## Mapping

| Category | DE term | EN term | Status | Canonical source | Usage note |
|---|---|---|---|---|---|
| product | Cognitive Staffing | Cognitive Staffing | canonical | `SiteProfile.brand_name` | Brand name is not translated. |
| product | Recruiting-Briefing | Recruiting-Briefing | canonical | `constants.APP_TITLE / components/layout.py` | Canonical visible product/process label. |
| product | Vakanz | vacancy | canonical | `i18n.py` | Use for the concrete open role to be filled. |
| product | Recruiting-Briefing | Recruiting-Briefing | canonical | `ux_copy.steps.* / locales` | Canonical user-facing process label. Avoid old product descriptors in visible copy. |
| product | Bedarfsanalyse | need clarification | proposed | repo/path legacy concept | Domain synonym; prefer `Recruiting-Briefing` in visible product copy. |
| product | Stellenanzeige | job ad | canonical | `summary_artifacts.py / i18n.py` | Use `job ad`, not `job advertisement`, for UI brevity. |
| product | Jobspec | job spec | canonical | `AGENTS.md / i18n.py` | Use for source vacancy description/specification. |
| product | Recruiting Brief | recruiting brief | canonical | `summary_artifacts.py` | Artifact label keeps the English term in German UI. |
| product | Recruiting-Unterlagen | recruiting outputs | canonical | `ux_copy.steps.* / summary_view.py` | Canonical user-facing umbrella for generated downstream materials; avoid `Artefakte` and German-side `Outputs`. |
| product | Hiring-Team | hiring team | canonical | `i18n.py` | Use for stakeholders involved in hiring. |
| product | Fachbereich | hiring manager / business team | proposed | `summary_artifacts.py` | In artifact naming, use `Hiring manager sheet` as the English label for `Fachbereich-Sheet`. |
| wizard.step | Einleitung | Introduction | canonical | `constants.PRE_WIZARD_STEP_KEYS / i18n.py` | Pre-start route label; excluded from sidebar/progress/readiness. |
| wizard.step | Start | Start | canonical | `constants.OPERATIONAL_WIZARD_STEP_KEYS / i18n.py` | Operational route label. |
| wizard.step | Unternehmen | Company | canonical | `constants.OPERATIONAL_WIZARD_STEP_KEYS / i18n.py` | Operational route label. |
| wizard.step | Rolle & Aufgaben | Role & tasks | canonical | `constants.OPERATIONAL_WIZARD_STEP_KEYS / i18n.py` | Operational route label. |
| wizard.step | Skills & Anforderungen | Skills & requirements | canonical | `constants.OPERATIONAL_WIZARD_STEP_KEYS / i18n.py` | Operational route label. |
| wizard.step | Benefits & Rahmenbedingungen | Benefits & conditions | canonical | `constants.OPERATIONAL_WIZARD_STEP_KEYS / i18n.py` | Operational route label. |
| wizard.step | Interviewprozess | Interview process | canonical | `constants.OPERATIONAL_WIZARD_STEP_KEYS / i18n.py` | Operational route label. |
| wizard.step | Zusammenfassung | Summary | canonical | `constants.OPERATIONAL_WIZARD_STEP_KEYS / i18n.py` | Operational route label. |
| ui | schnell | quick | canonical | `constants.py / i18n.py / locales` | Visible lowercase mode label. |
| ui | ausführlich | standard | canonical | `constants.py / i18n.py / locales` | Visible lowercase mode label. |
| ui | vollumfänglich | full | canonical | `constants.py / i18n.py / locales` | Visible lowercase mode label; canonical mode value remains `expert`. |
| ui | Schnell | Quick | canonical | `constants.py / i18n.py / locales` | Capitalized display label. |
| ui | Ausführlich | Standard | canonical | `constants.py / i18n.py / locales` | Capitalized display label. |
| ui | Vollumfänglich | Full | canonical | `constants.py / i18n.py / locales` | Capitalized display label; canonical mode value remains `expert`. |
| ui | Antwortmodus | Response mode | canonical | `constants.py / i18n.py / locales` | Preference label. |
| ui | Informationstiefe | Information depth | canonical | `constants.py / i18n.py / locales` | Preference label. |
| ui | Details standardmäßig öffnen | Open details by default | canonical | `constants.py / i18n.py / locales` | Global detail toggle. |
| ui | Details kompakt anzeigen | Show details compactly | canonical | `constants.py / i18n.py / locales` | Step-level compact toggle. |
| ui | Sprache | Language | canonical | `constants.py / i18n.py / locales` | UI language selector label. |
| ui | Deutsch | German | canonical | `constants.py / i18n.py / locales` | Language option. |
| ui | Englisch | English | canonical | `constants.py / i18n.py / locales` | Language option. |
| esco | ESCO | ESCO | canonical | `constants.py` | European Skills, Competences, Qualifications and Occupations; do not translate acronym. |
| esco | Berufsabgleich | occupation matching | canonical | `i18n.py` | Use for matching a role title to an ESCO occupation. |
| esco | Referenzberuf | reference occupation | canonical | `i18n.py` | Primary confirmed occupation anchor. |
| esco | Kontextrolle | context role | canonical | `i18n.py` | Secondary occupation context, not the primary anchor. |
| esco | Kontextanker | context anchor | canonical | `i18n.py` | Secondary anchor used as context only. |
| esco | Bestätigter Referenzberuf | Confirmed reference occupation | canonical | `i18n.py` | Visible label for primary anchor. |
| esco | Bestätigte ESCO-Auswahl | Confirmed ESCO selection | canonical | `i18n.py` | Visible label for confirmed ESCO selection. |
| esco | stabil | stable | proposed | `_constants/esco.py` | Release lane value is `stable`. |
| esco | Vorschau | preview | canonical | `_constants/esco.py / i18n.py` | Release lane value is `preview`; `Vorschau` is also used as UI copy. |
| esco | gehostet | hosted | proposed | `_constants/esco.py` | API mode value is `hosted`. |
| esco | lokal | local | proposed | `_constants/esco.py` | API mode value is `local`. |
| esco | Live-API | live API | proposed | `_constants/esco.py` | Data-source mode value is `live_api`. |
| esco | Offline-Index | offline index | proposed | `_constants/esco.py` | Data-source mode value is `offline_index`. |
| esco | hybrid | hybrid | proposed | `_constants/esco.py` | Data-source mode value is `hybrid`. |
| esco | nicht bestätigter degraded-Modus | degraded unconfirmed | proposed | `_constants/esco.py` | Anchor state value is `degraded_unconfirmed`. |
| esco | verankert | anchored | proposed | `_constants/esco.py` | Anchor state value is `anchored`. |
| esco | mit Kontext verankert | anchored with context | proposed | `_constants/esco.py` | Anchor state value is `anchored_with_context`. |
| esco | URI | URI | canonical | `i18n.py` | Do not translate. |
| esco | RAG | RAG | canonical | `i18n.py` | Retrieval-augmented generation; keep acronym. |
| summary.artifact | Recruiting Brief | Recruiting brief | canonical | `summary_artifacts.py:brief` | Canonical Summary artifact label. |
| summary.artifact | Stellenanzeige | Job ad | canonical | `summary_artifacts.py:job_ad` | Canonical Summary artifact label. |
| summary.artifact | HR-Sheet | HR sheet | canonical | `summary_artifacts.py:interview_hr` | Canonical Summary artifact label. |
| summary.artifact | Fachbereich-Sheet | Hiring manager sheet | canonical | `summary_artifacts.py:interview_fach` | Canonical Summary artifact label. |
| summary.artifact | Suchstrings | Boolean search | canonical | `summary_artifacts.py:boolean_search` | Canonical Summary artifact label; use `Suchstrings` in German UI, not `Boolean Search`. |
| summary.artifact | Arbeitsvertrag | Employment contract | canonical | `summary_artifacts.py:employment_contract` | Canonical Summary artifact label. |
| status | Offen | Open | canonical | `i18n.py` | Generic open status. |
| status | Teilweise | Partial | canonical | `i18n.py` | Partial completion status. |
| status | Vollständig | Complete | canonical | `i18n.py` | Complete status. |
| status | Aktuell | Current | canonical | `summary_artifacts.py` | Brief pipeline state. |
| status | Veraltet | Stale | canonical | `summary_artifacts.py` | Brief pipeline state. |
| status | Fehlt | Missing | canonical | `summary_artifacts.py` | Missing state. |
| status | Wartet | Waiting | canonical | `summary_artifacts.py` | Blocked/waiting state label. |
| status | Ungültig | Invalid | canonical | `i18n.py` | Invalid state. |
| status | Bereit | Ready | canonical | `i18n.py` | Readiness state. |
| status | Erfüllt | Met | canonical | `i18n.py` | Requirement state. |
| status | Kritische Lücken | Critical gaps | canonical | `i18n.py` | Readiness/action dashboard wording. |
| status | kritische Punkte | critical points | canonical | `ux_copy.steps.summary.headline.gap` | Short Summary headline wording; use when the count refers to blocking facts. |
| status | Keine kritischen Lücken erkannt | No critical gaps detected | canonical | `i18n.py` | Readiness/action dashboard wording. |
| status | Pflicht vor Summary | Required before Summary | canonical | `_constants/facts.py` | Requirement stage display label. |
| status | Pflicht vor Recruiting-Unterlage | Required before recruiting output | canonical | `_constants/facts.py` | Requirement stage display label. |
| status | Optional | Optional | canonical | `_constants/facts.py` | Requirement stage display label. |
| salary | Gehaltsprognose | salary forecast | canonical | `constants.STEP_SECTION_LABELS_DE / i18n.py` | Use for salary prediction block. |
| salary | Salary-Treiber | salary driver | canonical | `_constants/facts.py` | Direct p50 salary impact. |
| salary | Qualität/Unsicherheit | quality/uncertainty | canonical | `_constants/facts.py` | Indirect salary-quality impact. |
| salary | Kein Salary-Einfluss | no salary impact | canonical | `_constants/facts.py` | No salary impact. |
| salary | Variable Vergütung | variable compensation | canonical | `i18n.py` | Compensation component. |
| salary | Vergütung & Vertrag | compensation & contract | canonical | `_constants/esco.py` | Question group display label. |
| salary | Einflussfaktoren | influence factors | canonical | `i18n.py` | Salary panel wording. |
| salary | Auswirkung auf Prognose | impact on forecast | canonical | `i18n.py` | Salary forecast factor wording. |
| question.group | Skill-Priorisierung | Skill prioritization | proposed | `_constants/esco.py:QUESTION_GROUP_DISPLAY_LABELS_DE` | Question-plan group display label. |
| question.group | Datenqualität | Data quality | proposed | `_constants/esco.py:QUESTION_GROUP_DISPLAY_LABELS_DE` | Question-plan group display label. |
| question.group | Tech Stack | Tech stack | proposed | `_constants/esco.py:QUESTION_GROUP_DISPLAY_LABELS_DE` | Question-plan group display label. |
| question.group | Nachweise & Lizenzen | Certificates & licenses | proposed | `_constants/esco.py:QUESTION_GROUP_DISPLAY_LABELS_DE` | Question-plan group display label. |
| question.group | Vergütung & Vertrag | Compensation & contract | proposed | `_constants/esco.py:QUESTION_GROUP_DISPLAY_LABELS_DE` | Question-plan group display label. |
| question.group | Rechtliches | Legal | canonical | `_constants/esco.py:QUESTION_GROUP_DISPLAY_LABELS_DE` | Question-plan group display label. |
| question.group | Angebot | Offer | proposed | `_constants/esco.py:QUESTION_GROUP_DISPLAY_LABELS_DE` | Question-plan group display label. |
| question.group | Timing | Timing | proposed | `_constants/esco.py:QUESTION_GROUP_DISPLAY_LABELS_DE` | Question-plan group display label. |
| question.group | Assessment | Assessment | proposed | `_constants/esco.py:QUESTION_GROUP_DISPLAY_LABELS_DE` | Question-plan group display label. |
| question.group | Bewertung | Evaluation | proposed | `_constants/esco.py:QUESTION_GROUP_DISPLAY_LABELS_DE` | Question-plan group display label. |
| question.group | Kommunikation | Communication | proposed | `_constants/esco.py:QUESTION_GROUP_DISPLAY_LABELS_DE` | Question-plan group display label. |
| question.group | Prozess & Compliance | Process & compliance | proposed | `_constants/esco.py:QUESTION_GROUP_DISPLAY_LABELS_DE` | Question-plan group display label. |
| question.group | Fachwissen | Domain knowledge | proposed | `_constants/esco.py:QUESTION_GROUP_DISPLAY_LABELS_DE` | Question-plan group display label. |
| question.group | Tools & Methoden | Tools & methods | proposed | `_constants/esco.py:QUESTION_GROUP_DISPLAY_LABELS_DE` | Question-plan group display label. |
| question.group | Regulierung & Sicherheit | Regulation & safety | proposed | `_constants/esco.py:QUESTION_GROUP_DISPLAY_LABELS_DE` | Question-plan group display label. |
| question.group | Kundenkontakt | Customer/client interaction | proposed | `_constants/esco.py:QUESTION_GROUP_DISPLAY_LABELS_DE` | Question-plan group display label. |
| question.group | Dokumentation & Reporting | Documentation & reporting | proposed | `_constants/esco.py:QUESTION_GROUP_DISPLAY_LABELS_DE` | Question-plan group display label. |
| question.group | Führung & Koordination | Leadership & coordination | proposed | `_constants/esco.py:QUESTION_GROUP_DISPLAY_LABELS_DE` | Question-plan group display label. |
| question.group | Arbeitsumgebung | Work environment | proposed | `_constants/esco.py:QUESTION_GROUP_DISPLAY_LABELS_DE` | Question-plan group display label. |
| question.group | Digital, Data & AI | Digital, data & AI | proposed | `_constants/esco.py:QUESTION_GROUP_DISPLAY_LABELS_DE` | Question-plan group display label. |
| question.group | Sprache & Kommunikation | Language & communication | proposed | `_constants/esco.py:QUESTION_GROUP_DISPLAY_LABELS_DE` | Question-plan group display label. |
| question.group | Arbeitsweise | Working style | proposed | `_constants/esco.py:QUESTION_GROUP_DISPLAY_LABELS_DE` | Question-plan group display label. |
| fact | Einstellungsgrund | Hiring reason | proposed | `_constants/facts.py:FactKey.INTAKE_HIRING_REASON` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Besetzungsdringlichkeit | Hiring urgency | proposed | `_constants/facts.py:FactKey.INTAKE_URGENCY` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Einstellungsvolumen | Hiring volume | proposed | `_constants/facts.py:FactKey.INTAKE_HIRING_VOLUME` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Vertraulichkeit der Suche | Search confidentiality | proposed | `_constants/facts.py:FactKey.INTAKE_SEARCH_CONFIDENTIALITY` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Reifegrad der Rollendefinition | Role definition maturity | proposed | `_constants/facts.py:FactKey.INTAKE_ROLE_DEFINITION_MATURITY` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Erkannte Sprache | Detected language | proposed | `_constants/facts.py:FactKey.COMPANY_LANGUAGE_GUESS` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Unternehmensname | Company name | proposed | `_constants/facts.py:FactKey.COMPANY_COMPANY_NAME` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Markenname | Brand name | proposed | `_constants/facts.py:FactKey.COMPANY_BRAND_NAME` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Unternehmenswebsite | Company website | proposed | `_constants/facts.py:FactKey.COMPANY_COMPANY_WEBSITE` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Standortstadt | Location city | proposed | `_constants/facts.py:FactKey.COMPANY_LOCATION_CITY` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Standortland | Location country | proposed | `_constants/facts.py:FactKey.COMPANY_LOCATION_COUNTRY` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Arbeitsort | Place of work | proposed | `_constants/facts.py:FactKey.COMPANY_PLACE_OF_WORK` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Remote-Regelung | Remote policy | proposed | `_constants/facts.py:FactKey.COMPANY_REMOTE_POLICY` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Arbeitsmodell | Work arrangement | proposed | `_constants/facts.py:FactKey.COMPANY_WORK_ARRANGEMENT` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Bürotage pro Woche | Office days per week | proposed | `_constants/facts.py:FactKey.COMPANY_OFFICE_DAYS_PER_WEEK` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Erlaubte Regionen und Zeitzonen | Allowed regions and timezones | proposed | `_constants/facts.py:FactKey.COMPANY_ALLOWED_REGIONS_TIMEZONES` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Arbeitgeber-Pitch | Employer pitch | proposed | `_constants/facts.py:FactKey.COMPANY_EMPLOYER_PITCH` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Rollenrelevante Positionierung | Role-relevant positioning | proposed | `_constants/facts.py:FactKey.COMPANY_ROLE_RELEVANT_POSITIONING` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Geschäftsbereich | Business unit | proposed | `_constants/facts.py:FactKey.COMPANY_BUSINESS_UNIT` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Unternehmensbezogener Einstellungsgrund | Company hiring reason | proposed | `_constants/facts.py:FactKey.COMPANY_HIRING_REASON` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Wachstumskontext des Unternehmens | Company growth context | proposed | `_constants/facts.py:FactKey.COMPANY_GROWTH_CONTEXT` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Business Impact der Rolle | Role business impact | proposed | `_constants/facts.py:FactKey.COMPANY_ROLE_BUSINESS_IMPACT` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Interne Arbeitssprache | Internal working language | proposed | `_constants/facts.py:FactKey.COMPANY_LANGUAGE_INTERNAL` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Externe Kommunikationssprache | External communication language | proposed | `_constants/facts.py:FactKey.COMPANY_LANGUAGE_EXTERNAL` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Non-negotiables | Non-negotiables | proposed | `_constants/facts.py:FactKey.COMPANY_NON_NEGOTIABLES` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Compliance-Kontext | Compliance context | proposed | `_constants/facts.py:FactKey.COMPANY_COMPLIANCE_CONTEXT` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Tarifkontext | Tariff context | proposed | `_constants/facts.py:FactKey.COMPANY_TARIFF_CONTEXT` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Abteilungsname | Department name | proposed | `_constants/facts.py:FactKey.COMPANY_DEPARTMENT_NAME` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Berichtet an | Reports to | proposed | `_constants/facts.py:FactKey.COMPANY_REPORTS_TO` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Anzahl direkter Reports | Direct reports count | proposed | `_constants/facts.py:FactKey.COMPANY_DIRECT_REPORTS_COUNT` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Teamname | Team name | proposed | `_constants/facts.py:FactKey.TEAM_NAME` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Führungsumfang | Leadership scope | proposed | `_constants/facts.py:FactKey.TEAM_LEADERSHIP_SCOPE` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Direkte Teamgröße | Direct team size | proposed | `_constants/facts.py:FactKey.TEAM_SIZE_DIRECT` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Primäre Stakeholder | Primary stakeholders | proposed | `_constants/facts.py:FactKey.TEAM_STAKEHOLDERS_PRIMARY` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | 90-Tage-Erfolgskontext des Teams | 90-day team success context | proposed | `_constants/facts.py:FactKey.TEAM_SUCCESS_CONTEXT_90D` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Jobtitel | Job title | proposed | `_constants/facts.py:FactKey.ROLE_JOB_TITLE` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Beschäftigungsart | Employment type | proposed | `_constants/facts.py:FactKey.ROLE_EMPLOYMENT_TYPE` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Vertragsart | Contract type | proposed | `_constants/facts.py:FactKey.ROLE_CONTRACT_TYPE` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Senioritätslevel | Seniority level | proposed | `_constants/facts.py:FactKey.ROLE_SENIORITY_LEVEL` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Job-Referenznummer | Job reference number | proposed | `_constants/facts.py:FactKey.ROLE_JOB_REF_NUMBER` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Rollenüberblick | Role overview | proposed | `_constants/facts.py:FactKey.ROLE_ROLE_OVERVIEW` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Verantwortlichkeiten | Responsibilities | proposed | `_constants/facts.py:FactKey.ROLE_RESPONSIBILITIES` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Priorisierte Verantwortlichkeiten | Prioritized responsibilities | proposed | `_constants/facts.py:FactKey.ROLE_RESPONSIBILITIES_PRIORITIZED` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Lieferobjekte | Deliverables | proposed | `_constants/facts.py:FactKey.ROLE_DELIVERABLES` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Erfolgskriterien | Success metrics | proposed | `_constants/facts.py:FactKey.ROLE_SUCCESS_METRICS` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Zeitplan der Erfolgskriterien | Success metrics timeline | proposed | `_constants/facts.py:FactKey.ROLE_SUCCESS_METRICS_TIMELINE` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Primäres Business Outcome | Primary business outcome | proposed | `_constants/facts.py:FactKey.ROLE_BUSINESS_OUTCOME_PRIMARY` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Day-1-Verantwortlichkeiten | Day-1 responsibilities | proposed | `_constants/facts.py:FactKey.ROLE_DAY1_RESPONSIBILITIES` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Ausbauumfang | Expansion scope | proposed | `_constants/facts.py:FactKey.ROLE_EXPANSION_SCOPE` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Entscheidungsspielraum | Decision scope | proposed | `_constants/facts.py:FactKey.ROLE_DECISION_SCOPE` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Erfolgssignale im ersten Jahr | Year-1 success signals | proposed | `_constants/facts.py:FactKey.ROLE_YEAR1_SUCCESS_SIGNALS` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Tech Stack | Tech stack | proposed | `_constants/facts.py:FactKey.ROLE_TECH_STACK` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Fachexpertise | Domain expertise | proposed | `_constants/facts.py:FactKey.ROLE_DOMAIN_EXPERTISE` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Reiseanforderung | Travel required | proposed | `_constants/facts.py:FactKey.ROLE_TRAVEL_REQUIRED` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Reiseprofil | Travel profile | proposed | `_constants/facts.py:FactKey.ROLE_TRAVEL_PROFILE` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Rufbereitschaftsanforderung | On-call requirement | proposed | `_constants/facts.py:FactKey.ROLE_ON_CALL` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Onboarding-Hinweise | Onboarding notes | proposed | `_constants/facts.py:FactKey.ROLE_ONBOARDING_NOTES` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Extraktionslücken | Extraction gaps | proposed | `_constants/facts.py:FactKey.ROLE_GAPS` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Extraktionsannahmen | Extraction assumptions | proposed | `_constants/facts.py:FactKey.ROLE_ASSUMPTIONS` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Strukturierte Skill-Einträge | Structured skill items | proposed | `_constants/facts.py:FactKey.SKILLS_ITEMS` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Must-have-Skills | Must-have skills | proposed | `_constants/facts.py:FactKey.SKILLS_MUST_HAVE_SKILLS` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Nice-to-have-Skills | Nice-to-have skills | proposed | `_constants/facts.py:FactKey.SKILLS_NICE_TO_HAVE_SKILLS` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Soft Skills | Soft skills | proposed | `_constants/facts.py:FactKey.SKILLS_SOFT_SKILLS` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Ausbildung | Education | proposed | `_constants/facts.py:FactKey.SKILLS_EDUCATION` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Zertifizierungen | Certifications | proposed | `_constants/facts.py:FactKey.SKILLS_CERTIFICATIONS` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Sprachen | Languages | proposed | `_constants/facts.py:FactKey.SKILLS_LANGUAGES` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Skill-Verfügbarkeitszeitpunkt | Skill readiness timing | proposed | `_constants/facts.py:FactKey.SKILLS_READINESS_TIMING` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Begründung für Freitext-Skill | Free-text skill retention reason | proposed | `_constants/facts.py:FactKey.SKILLS_FREE_TEXT_REASON` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Knockout-Kriterien | Knockout criteria | proposed | `_constants/facts.py:FactKey.SKILLS_KNOCKOUT_CRITERIA` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Trainierbare Skills | Trainable skills | proposed | `_constants/facts.py:FactKey.SKILLS_TRAINABLE_SKILLS` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Gehaltsrahmen | Salary range | proposed | `_constants/facts.py:FactKey.BENEFITS_SALARY_RANGE` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Variable Vergütung | Variable pay | proposed | `_constants/facts.py:FactKey.BENEFITS_VARIABLE_PAY` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Benefits | Benefits | proposed | `_constants/facts.py:FactKey.BENEFITS_BENEFITS` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Schichtausgleich | Shift compensation | proposed | `_constants/facts.py:FactKey.BENEFITS_SHIFT_COMPENSATION` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Tarifvertragskontext | Collective agreement context | proposed | `_constants/facts.py:FactKey.BENEFITS_COLLECTIVE_AGREEMENT_CONTEXT` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Offer-Komponenten | Offer components | proposed | `_constants/facts.py:FactKey.BENEFITS_OFFER_COMPONENTS` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Unterstützung bei Arbeitserlaubnis | Work authorization support | proposed | `_constants/facts.py:FactKey.LEGAL_WORK_AUTHORIZATION_SUPPORT` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Startflexibilität | Start flexibility | proposed | `_constants/facts.py:FactKey.TIMELINE_START_FLEXIBILITY` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Startdatum | Start date | proposed | `_constants/facts.py:FactKey.INTERVIEW_START_DATE` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Bewerbungsfrist | Application deadline | proposed | `_constants/facts.py:FactKey.INTERVIEW_APPLICATION_DEADLINE` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Recruiting-Schritte | Recruitment steps | proposed | `_constants/facts.py:FactKey.INTERVIEW_RECRUITMENT_STEPS` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Ansprechpersonen | Contacts | proposed | `_constants/facts.py:FactKey.INTERVIEW_CONTACTS` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Assessment-Evidenz | Assessment evidence | proposed | `_constants/facts.py:FactKey.INTERVIEW_ASSESSMENT_EVIDENCE` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Stage Owner | Stage owners | proposed | `_constants/facts.py:FactKey.INTERVIEW_STAGE_OWNERS` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Candidate Communication SLA | Candidate communication SLA | proposed | `_constants/facts.py:FactKey.INTERVIEW_COMMUNICATION_SLA` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Scorecard-Vorlage | Scorecard template | proposed | `_constants/facts.py:FactKey.INTERVIEW_SCORECARD_TEMPLATE` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Kernfragen im Interview | Core interview questions | proposed | `_constants/facts.py:FactKey.INTERVIEW_CORE_QUESTIONS` | English Fact label is canonical; DE term is glossary guidance until localized. |
| fact | Compliance-Hinweise zum Interview | Interview compliance notes | proposed | `_constants/facts.py:FactKey.INTERVIEW_COMPLIANCE_NOTES` | English Fact label is canonical; DE term is glossary guidance until localized. |
| public.legal | Unsere Kompetenzen | Our competencies | canonical | `public_pages.competencies.title` | Public/legal page terminology. |
| public.legal | Über Cognitive Staffing | About Cognitive Staffing | canonical | `public_pages.about.title` | Public/legal page terminology. |
| public.legal | Impressum | Imprint | canonical | `public_pages.imprint.title` | Public/legal page terminology. |
| public.legal | Datenschutzrichtlinie | Privacy policy | canonical | `public_pages.privacy.title` | Public/legal page terminology. |
| public.legal | Nutzungsbedingungen | Terms of use | canonical | `public_pages.terms.title` | Public/legal page terminology. |
| public.legal | Cookie Policy & Einstellungen | Cookie policy & settings | canonical | `public_pages.cookies.title` | Public/legal page terminology. |
| public.legal | Erklärung zur Barrierefreiheit | Accessibility statement | canonical | `public_pages.accessibility.title` | Public/legal page terminology. |
| public.legal | Kontakt & Demo | Contact & demo | canonical | `public_pages.contact.title` | Public/legal page terminology. |
| public.legal | Rechtliche Information | Legal information | canonical | `i18n.py` | Public/legal page terminology. |
| public.legal | Rechtliches | Legal | canonical | `i18n.py` | Public/legal page terminology. |
| public.legal | Datenschutz | Privacy | canonical | `i18n.py` | Public/legal page terminology. |
| public.legal | Barrierefreiheit | Accessibility | canonical | `i18n.py` | Public/legal page terminology. |
| public.legal | Cookies & Präferenzen | Cookies & preferences | canonical | `i18n.py` | Public/legal page terminology. |
| public.legal | Wichtiger Hinweis | Important note | canonical | `i18n.py` | Public/legal page terminology. |
| public.legal | Platzhalter | Placeholder | canonical | `locales/common.placeholder_missing` | Public/legal page terminology. |
| ui.copy | UX-Copy-Contract | UX copy contract | canonical | `ux_copy_contract.py` | Runtime contract for short Wizard copy; code identifiers stay English. |

## Maintenance Notes

- When a proposed DE term is promoted into UI copy, add it to `locales/*.json` or `i18n.py` in the same change.
- When Summary artifact IDs, Wizard steps, UI modes, ESCO modes, or Fact labels change, update this glossary with the same PR.
- Keep acronyms such as ESCO, RAG, URI, AI, HR, SLA, OTE, and JSON unchanged unless a specific UI copy decision says otherwise.
