"""Canonical deterministic question packs compiled into the QuestionPlan."""

from __future__ import annotations

from constants import (
    AnswerType,
    ESCO_QUESTION_SKILL_GROUP_CUSTOMER_CLIENT_INTERACTION,
    ESCO_QUESTION_SKILL_GROUP_DIGITAL_DATA_AI,
    ESCO_QUESTION_SKILL_GROUP_DOCUMENTATION_REPORTING,
    ESCO_QUESTION_SKILL_GROUP_DOMAIN_KNOWLEDGE,
    ESCO_QUESTION_SKILL_GROUP_LANGUAGE_COMMUNICATION,
    ESCO_QUESTION_SKILL_GROUP_LEADERSHIP_COORDINATION,
    ESCO_QUESTION_SKILL_GROUP_PHYSICAL_MANUAL_CONTEXT,
    ESCO_QUESTION_SKILL_GROUP_REGULATION_SAFETY,
    ESCO_QUESTION_SKILL_GROUP_TOOLS_METHODS,
    ESCO_QUESTION_SKILL_GROUP_TRANSVERSAL_FIT,
    FactKey,
    STEP_KEY_BENEFITS,
    STEP_KEY_COMPANY,
    STEP_KEY_INTERVIEW,
    STEP_KEY_ROLE_TASKS,
    STEP_KEY_SKILLS,
)
from schemas import Question

from question_packs.types import QuestionPack, QuestionPackEntry


def _pack_entry(
    *,
    step_key: str,
    question_id: str,
    label: str,
    answer_type: AnswerType,
    group_key: str,
    priority: str = "standard",
    target_path: str | None = None,
    fact_key: FactKey | None = None,
    required: bool = False,
    options: list[str] | None = None,
    help_text: str | None = None,
) -> QuestionPackEntry:
    question = Question(
        id=question_id,
        label=label,
        help=help_text,
        answer_type=answer_type,
        required=required,
        options=options,
        target_path=target_path or f"answers.{step_key}.{question_id}",
        fact_key=fact_key.value if fact_key is not None else None,
        priority=priority,  # type: ignore[arg-type]
        group_key=group_key,
    )
    return QuestionPackEntry(step_key=step_key, question=question)


BASE_CORE_PACK = QuestionPack(
    pack_key="base.core",
    description="Core vacancy context questions shared across occupation families.",
    entries=(
        _pack_entry(
            step_key=STEP_KEY_COMPANY,
            question_id="ctx_company_employer_pitch",
            label="Wie wuerden Sie das Unternehmen in 1-2 Saetzen fuer Kandidat:innen beschreiben?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="company_profile",
            priority="core",
            target_path=FactKey.COMPANY_EMPLOYER_PITCH.value,
            fact_key=FactKey.COMPANY_EMPLOYER_PITCH,
            required=True,
        ),
        _pack_entry(
            step_key=STEP_KEY_COMPANY,
            question_id="ctx_company_business_unit",
            label="In welchem Geschaefts- oder Produktbereich sitzt die Rolle?",
            answer_type=AnswerType.SHORT_TEXT,
            group_key="company_profile",
            priority="core",
            target_path=FactKey.COMPANY_BUSINESS_UNIT.value,
            fact_key=FactKey.COMPANY_BUSINESS_UNIT,
            required=True,
        ),
        _pack_entry(
            step_key=STEP_KEY_COMPANY,
            question_id="ctx_company_hiring_reason",
            label="Warum wird diese Rolle jetzt besetzt?",
            answer_type=AnswerType.SHORT_TEXT,
            group_key="business_context",
            priority="standard",
            target_path=FactKey.COMPANY_HIRING_REASON.value,
            fact_key=FactKey.COMPANY_HIRING_REASON,
        ),
        _pack_entry(
            step_key=STEP_KEY_COMPANY,
            question_id="ctx_company_growth_context",
            label="Welcher Markt-, Wachstums- oder Aufbaukontext ist relevant?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="business_context",
            priority="standard",
            target_path=FactKey.COMPANY_GROWTH_CONTEXT.value,
            fact_key=FactKey.COMPANY_GROWTH_CONTEXT,
        ),
        _pack_entry(
            step_key=STEP_KEY_COMPANY,
            question_id="ctx_company_role_business_impact",
            label="Welchen Business Impact soll die Rolle fuer das Unternehmen haben?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="business_context",
            priority="standard",
            target_path=FactKey.COMPANY_ROLE_BUSINESS_IMPACT.value,
            fact_key=FactKey.COMPANY_ROLE_BUSINESS_IMPACT,
        ),
        _pack_entry(
            step_key=STEP_KEY_COMPANY,
            question_id="ctx_company_role_positioning",
            label="Welche Aspekte der Unternehmenspositionierung sind fuer diese Rolle wirklich relevant?",
            answer_type=AnswerType.MULTI_SELECT,
            group_key="company_profile",
            priority="standard",
            target_path=FactKey.COMPANY_ROLE_RELEVANT_POSITIONING.value,
            fact_key=FactKey.COMPANY_ROLE_RELEVANT_POSITIONING,
            options=[
                "Marktposition",
                "Produkt",
                "Wachstum",
                "Stabilitaet",
                "Technologie",
                "Mission",
                "Kundennutzen",
                "Sonstiges",
            ],
        ),
        _pack_entry(
            step_key=STEP_KEY_COMPANY,
            question_id="ctx_team_name",
            label="Welches Team nimmt die Person auf?",
            answer_type=AnswerType.SHORT_TEXT,
            group_key="team_reporting",
            priority="core",
            target_path=FactKey.TEAM_NAME.value,
            fact_key=FactKey.TEAM_NAME,
            required=True,
        ),
        _pack_entry(
            step_key=STEP_KEY_COMPANY,
            question_id="ctx_team_leadership_scope",
            label="Ist die Rolle individual contributor, fachlich fuehrend oder disziplinarisch fuehrend?",
            answer_type=AnswerType.SINGLE_SELECT,
            group_key="team_reporting",
            priority="core",
            target_path=FactKey.TEAM_LEADERSHIP_SCOPE.value,
            fact_key=FactKey.TEAM_LEADERSHIP_SCOPE,
            required=True,
            options=[
                "individual_contributor",
                "fachliche_fuehrung",
                "disziplinarische_fuehrung",
                "beides",
                "unklar",
            ],
        ),
        _pack_entry(
            step_key=STEP_KEY_COMPANY,
            question_id="ctx_team_size_direct",
            label="Wie gross ist das unmittelbare Team?",
            answer_type=AnswerType.NUMBER,
            group_key="team_reporting",
            priority="standard",
            target_path=FactKey.TEAM_SIZE_DIRECT.value,
            fact_key=FactKey.TEAM_SIZE_DIRECT,
        ),
        _pack_entry(
            step_key=STEP_KEY_COMPANY,
            question_id="ctx_team_stakeholders_primary",
            label="Mit welchen wichtigsten Stakeholdern arbeitet die Person regelmaessig?",
            answer_type=AnswerType.MULTI_SELECT,
            group_key="stakeholders",
            priority="core",
            target_path=FactKey.TEAM_STAKEHOLDERS_PRIMARY.value,
            fact_key=FactKey.TEAM_STAKEHOLDERS_PRIMARY,
            required=True,
            options=[
                "Fachbereich",
                "Management",
                "HR/Recruiting",
                "Sales",
                "Customer Success",
                "Operations",
                "Kund:innen",
                "Lieferanten/Partner",
                "Sonstiges",
            ],
        ),
        _pack_entry(
            step_key=STEP_KEY_COMPANY,
            question_id="ctx_company_work_arrangement",
            label="Welches Arbeitsmodell gilt fuer diese Rolle?",
            answer_type=AnswerType.SINGLE_SELECT,
            group_key="work_arrangement",
            priority="core",
            target_path=FactKey.COMPANY_WORK_ARRANGEMENT.value,
            fact_key=FactKey.COMPANY_WORK_ARRANGEMENT,
            required=True,
            options=[
                "onsite",
                "hybrid",
                "remote_country",
                "remote_cross_border",
                "unknown",
            ],
        ),
        _pack_entry(
            step_key=STEP_KEY_COMPANY,
            question_id="ctx_company_language_internal",
            label="Welche interne Arbeitssprache und welches Mindestniveau gelten?",
            answer_type=AnswerType.SHORT_TEXT,
            group_key="work_arrangement",
            priority="standard",
            target_path=FactKey.COMPANY_LANGUAGE_INTERNAL.value,
            fact_key=FactKey.COMPANY_LANGUAGE_INTERNAL,
            help_text="Beispiel: Deutsch B2 intern, Englisch C1 im Engineering.",
        ),
        _pack_entry(
            step_key=STEP_KEY_COMPANY,
            question_id="ctx_company_language_external",
            label="Welche externe Kommunikationssprache ist bei Kund:innen oder Partnern noetig?",
            answer_type=AnswerType.SHORT_TEXT,
            group_key="work_arrangement",
            priority="standard",
            target_path=FactKey.COMPANY_LANGUAGE_EXTERNAL.value,
            fact_key=FactKey.COMPANY_LANGUAGE_EXTERNAL,
        ),
        _pack_entry(
            step_key=STEP_KEY_COMPANY,
            question_id="ctx_company_non_negotiables",
            label="Welche Rahmenbedingungen sind nicht verhandelbar?",
            answer_type=AnswerType.MULTI_SELECT,
            group_key="non_negotiables",
            priority="core",
            target_path=FactKey.COMPANY_NON_NEGOTIABLES.value,
            fact_key=FactKey.COMPANY_NON_NEGOTIABLES,
            required=True,
            options=[
                "Standort",
                "Arbeitszeit",
                "Gehalt",
                "Vertragsart",
                "Sprache",
                "Zertifikat/Nachweis",
                "Reisebereitschaft",
                "Schicht/Rufbereitschaft",
                "Sonstiges",
            ],
        ),
        _pack_entry(
            step_key=STEP_KEY_COMPANY,
            question_id="ctx_team_success_context_90d",
            label="Welche Arbeitsweise ist im Team noetig, um in den ersten 90 Tagen zu bestehen?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="team_reporting",
            priority="standard",
            target_path=FactKey.TEAM_SUCCESS_CONTEXT_90D.value,
            fact_key=FactKey.TEAM_SUCCESS_CONTEXT_90D,
        ),
        _pack_entry(
            step_key=STEP_KEY_ROLE_TASKS,
            question_id="ctx_success_criteria",
            label="Woran wird Erfolg in den ersten 6 Monaten gemessen?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="success_context",
            priority="core",
            target_path="success_metrics",
            fact_key=FactKey.ROLE_SUCCESS_METRICS,
        ),
        _pack_entry(
            step_key=STEP_KEY_ROLE_TASKS,
            question_id="ctx_role_business_outcome_primary",
            label="Welches konkrete Business-Ergebnis soll die Rolle liefern?",
            answer_type=AnswerType.SHORT_TEXT,
            group_key="outcome_scope",
            priority="core",
            target_path=FactKey.ROLE_BUSINESS_OUTCOME_PRIMARY.value,
            fact_key=FactKey.ROLE_BUSINESS_OUTCOME_PRIMARY,
            required=True,
        ),
        _pack_entry(
            step_key=STEP_KEY_ROLE_TASKS,
            question_id="ctx_role_day1_responsibilities",
            label="Welche Aufgaben sind wirklich ab Tag 1 relevant?",
            answer_type=AnswerType.MULTI_SELECT,
            group_key="outcome_scope",
            priority="core",
            target_path=FactKey.ROLE_DAY1_RESPONSIBILITIES.value,
            fact_key=FactKey.ROLE_DAY1_RESPONSIBILITIES,
            required=True,
            options=["aus Jobspec uebernehmen", "Kernbetrieb", "Kundenkontakt", "Reporting", "Projektstart", "Teamkoordination", "Sonstiges"],
        ),
        _pack_entry(
            step_key=STEP_KEY_ROLE_TASKS,
            question_id="ctx_role_expansion_scope",
            label="Welche Aufgaben sind Nice-to-have oder spaeter ausbaubar?",
            answer_type=AnswerType.MULTI_SELECT,
            group_key="outcome_scope",
            priority="standard",
            target_path=FactKey.ROLE_EXPANSION_SCOPE.value,
            fact_key=FactKey.ROLE_EXPANSION_SCOPE,
            options=["Automatisierung", "Strategie", "Mentoring", "Reporting", "Stakeholder-Ausbau", "Tooling", "Sonstiges"],
        ),
        _pack_entry(
            step_key=STEP_KEY_ROLE_TASKS,
            question_id="ctx_role_success_metrics_timeline",
            label="Welche Erfolgssignale gelten nach 30, 60, 90 und 180 Tagen?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="success_context",
            priority="core",
            target_path=FactKey.ROLE_SUCCESS_METRICS_TIMELINE.value,
            fact_key=FactKey.ROLE_SUCCESS_METRICS_TIMELINE,
            required=True,
        ),
        _pack_entry(
            step_key=STEP_KEY_ROLE_TASKS,
            question_id="ctx_role_year1_success_signals",
            label="Wofuer wuerde die Person in 12 Monaten gemessen oder gelobt werden?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="success_context",
            priority="standard",
            target_path=FactKey.ROLE_YEAR1_SUCCESS_SIGNALS.value,
            fact_key=FactKey.ROLE_YEAR1_SUCCESS_SIGNALS,
        ),
        _pack_entry(
            step_key=STEP_KEY_ROLE_TASKS,
            question_id="ctx_role_decision_scope",
            label="Welche Entscheidungsrechte hat die Rolle?",
            answer_type=AnswerType.SINGLE_SELECT,
            group_key="seniority_scope",
            priority="standard",
            target_path=FactKey.ROLE_DECISION_SCOPE.value,
            fact_key=FactKey.ROLE_DECISION_SCOPE,
            options=[
                "keine_eigenen_entscheidungen",
                "fachliche_empfehlungen",
                "eigenstaendige_fachentscheidungen",
                "budget_personal_oder_prioritaeten",
                "unklar",
            ],
        ),
        _pack_entry(
            step_key=STEP_KEY_SKILLS,
            question_id="ctx_skills_readiness_timing",
            label="Welche Top-Skills muessen zum Start vorhanden sein, welche sind in 90 Tagen lernbar?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="must_nice_trainable",
            priority="core",
            target_path=FactKey.SKILLS_READINESS_TIMING.value,
            fact_key=FactKey.SKILLS_READINESS_TIMING,
            required=True,
        ),
        _pack_entry(
            step_key=STEP_KEY_SKILLS,
            question_id="ctx_skills_knockout_criteria",
            label="Welche Anforderungen sind KO-Kriterien und warum?",
            answer_type=AnswerType.MULTI_SELECT,
            group_key="must_nice_trainable",
            priority="core",
            target_path=FactKey.SKILLS_KNOCKOUT_CRITERIA.value,
            fact_key=FactKey.SKILLS_KNOCKOUT_CRITERIA,
            options=[
                "Zertifikat/Nachweis",
                "Sprache",
                "Berufserfahrung",
                "Tool/Technologie",
                "Arbeitsmodell",
                "Reise/Standort",
                "Sonstiges",
            ],
        ),
        _pack_entry(
            step_key=STEP_KEY_SKILLS,
            question_id="ctx_skills_trainable",
            label="Welche Anforderungen sind trainierbar?",
            answer_type=AnswerType.MULTI_SELECT,
            group_key="must_nice_trainable",
            priority="core",
            target_path=FactKey.SKILLS_TRAINABLE_SKILLS.value,
            fact_key=FactKey.SKILLS_TRAINABLE_SKILLS,
            options=[
                "Tooling",
                "Branchendomaene",
                "Interne Prozesse",
                "Methodik",
                "Produktwissen",
                "Kommunikationsroutine",
                "Sonstiges",
            ],
        ),
        _pack_entry(
            step_key=STEP_KEY_SKILLS,
            question_id="ctx_skills_free_text_reason",
            label="Warum sollen nicht gemappte Freitext-Anforderungen behalten werden?",
            answer_type=AnswerType.SINGLE_SELECT,
            group_key="data_hygiene",
            priority="detail",
            target_path=FactKey.SKILLS_FREE_TEXT_REASON.value,
            fact_key=FactKey.SKILLS_FREE_TEXT_REASON,
            options=[
                "firmenspezifischer_begriff",
                "tool_oder_produktname",
                "regulatorischer_begriff",
                "kundenspezifischer_kontext",
                "noch_unklar",
            ],
        ),
        _pack_entry(
            step_key=STEP_KEY_BENEFITS,
            question_id="ctx_benefits_variable_pay",
            label="Wie ist variable Verguetung, Bonus oder OTE geregelt?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="compensation_contract",
            priority="core",
            target_path=FactKey.BENEFITS_VARIABLE_PAY.value,
            fact_key=FactKey.BENEFITS_VARIABLE_PAY,
        ),
        _pack_entry(
            step_key=STEP_KEY_BENEFITS,
            question_id="ctx_benefits_contract_type",
            label="Welche Vertragsart gilt?",
            answer_type=AnswerType.SINGLE_SELECT,
            group_key="compensation_contract",
            priority="core",
            target_path=FactKey.ROLE_CONTRACT_TYPE.value,
            fact_key=FactKey.ROLE_CONTRACT_TYPE,
            required=True,
            options=[
                "unbefristet",
                "befristet",
                "freelance",
                "interim",
                "anue",
                "werkstudentisch",
                "praktikum",
                "unklar",
            ],
        ),
        _pack_entry(
            step_key=STEP_KEY_BENEFITS,
            question_id="ctx_benefits_employment_type",
            label="Welche Beschaeftigungsart gilt?",
            answer_type=AnswerType.SINGLE_SELECT,
            group_key="compensation_contract",
            priority="core",
            target_path=FactKey.ROLE_EMPLOYMENT_TYPE.value,
            fact_key=FactKey.ROLE_EMPLOYMENT_TYPE,
            required=True,
            options=[
                "vollzeit",
                "teilzeit",
                "vollzeit_oder_teilzeit",
                "minijob",
                "freelance",
                "unklar",
            ],
        ),
        _pack_entry(
            step_key=STEP_KEY_BENEFITS,
            question_id="ctx_benefits_collective_agreement",
            label="Gibt es Tarifbindung, Betriebsrat, TVoeD/TV-L oder branchenspezifische Vorgaben?",
            answer_type=AnswerType.MULTI_SELECT,
            group_key="legal_contract",
            priority="standard",
            target_path=FactKey.BENEFITS_COLLECTIVE_AGREEMENT_CONTEXT.value,
            fact_key=FactKey.BENEFITS_COLLECTIVE_AGREEMENT_CONTEXT,
            options=[
                "Tarifbindung",
                "Betriebsrat",
                "TVoed_TVl",
                "Branchenvorgaben",
                "oeffentlicher_sektor",
                "keine",
                "unklar",
            ],
        ),
        _pack_entry(
            step_key=STEP_KEY_BENEFITS,
            question_id="ctx_legal_work_authorization_support",
            label="Ist Visa- oder Work-Permit-Sponsoring moeglich?",
            answer_type=AnswerType.SINGLE_SELECT,
            group_key="legal_contract",
            priority="standard",
            target_path=FactKey.LEGAL_WORK_AUTHORIZATION_SUPPORT.value,
            fact_key=FactKey.LEGAL_WORK_AUTHORIZATION_SUPPORT,
            options=["ja", "nein", "fallweise", "unklar"],
        ),
        _pack_entry(
            step_key=STEP_KEY_BENEFITS,
            question_id="ctx_benefits_offer_components",
            label="Welche Offer-Komponenten sind relevant?",
            answer_type=AnswerType.MULTI_SELECT,
            group_key="offer_components",
            priority="standard",
            target_path=FactKey.BENEFITS_OFFER_COMPONENTS.value,
            fact_key=FactKey.BENEFITS_OFFER_COMPONENTS,
            options=[
                "Equipment",
                "Homeoffice-Kosten",
                "Relocation",
                "Firmenwagen",
                "Weiterbildung",
                "Kinderbetreuung",
                "Gesundheit",
                "Sonstiges",
            ],
        ),
        _pack_entry(
            step_key=STEP_KEY_BENEFITS,
            question_id="ctx_timeline_start_flexibility",
            label="Wie starr ist der Starttermin oder das Notice-Period-Fenster?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="timeline",
            priority="core",
            target_path=FactKey.TIMELINE_START_FLEXIBILITY.value,
            fact_key=FactKey.TIMELINE_START_FLEXIBILITY,
            required=True,
        ),
    ),
)

BASE_INTERVIEW_PACK = QuestionPack(
    pack_key="base.interview",
    description="Baseline interview evidence collection.",
    entries=(
        _pack_entry(
            step_key=STEP_KEY_INTERVIEW,
            question_id="ctx_interview_evidence",
            label="Welche Nachweise oder Arbeitsproben sollen im Interview bewertet werden?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="assessment",
            priority="core",
            target_path="recruitment_steps",
            fact_key=FactKey.INTERVIEW_RECRUITMENT_STEPS,
        ),
        _pack_entry(
            step_key=STEP_KEY_INTERVIEW,
            question_id="ctx_interview_stages",
            label="Welche Interviewstufen gibt es und welches Ziel hat jede Stufe?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="stage_evaluation",
            priority="core",
            target_path=FactKey.INTERVIEW_RECRUITMENT_STEPS.value,
            fact_key=FactKey.INTERVIEW_RECRUITMENT_STEPS,
            required=True,
        ),
        _pack_entry(
            step_key=STEP_KEY_INTERVIEW,
            question_id="ctx_interview_stage_owners",
            label="Wer ist Owner und Entscheider pro Interviewstufe?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="stage_evaluation",
            priority="core",
            target_path=FactKey.INTERVIEW_STAGE_OWNERS.value,
            fact_key=FactKey.INTERVIEW_STAGE_OWNERS,
            required=True,
        ),
        _pack_entry(
            step_key=STEP_KEY_INTERVIEW,
            question_id="ctx_interview_scorecard_template",
            label="Welche Scorecard oder Bewertungsskala nutzen wir je Stufe?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="stage_evaluation",
            priority="core",
            target_path=FactKey.INTERVIEW_SCORECARD_TEMPLATE.value,
            fact_key=FactKey.INTERVIEW_SCORECARD_TEMPLATE,
            required=True,
        ),
        _pack_entry(
            step_key=STEP_KEY_INTERVIEW,
            question_id="ctx_interview_core_questions",
            label="Welche Fragen sind fuer alle Kandidat:innen identisch?",
            answer_type=AnswerType.MULTI_SELECT,
            group_key="stage_evaluation",
            priority="core",
            target_path=FactKey.INTERVIEW_CORE_QUESTIONS.value,
            fact_key=FactKey.INTERVIEW_CORE_QUESTIONS,
            required=True,
            options=[
                "Motivation und Wechselgrund",
                "relevante Praxiserfahrung",
                "kritische Situation",
                "Zusammenarbeit",
                "fachlicher Deep Dive",
                "Arbeitsprobe",
                "Sonstiges",
            ],
        ),
        _pack_entry(
            step_key=STEP_KEY_INTERVIEW,
            question_id="ctx_interview_communication_sla",
            label="Welches Update-SLA gilt fuer Kandidat:innen nach jeder Stufe?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="candidate_communication",
            priority="core",
            target_path=FactKey.INTERVIEW_COMMUNICATION_SLA.value,
            fact_key=FactKey.INTERVIEW_COMMUNICATION_SLA,
            required=True,
        ),
        _pack_entry(
            step_key=STEP_KEY_INTERVIEW,
            question_id="ctx_interview_compliance_notes",
            label="Welche Datenschutz- oder Dokumentationspflichten gelten im Auswahlprozess?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="process_compliance",
            priority="detail",
            target_path=FactKey.INTERVIEW_COMPLIANCE_NOTES.value,
            fact_key=FactKey.INTERVIEW_COMPLIANCE_NOTES,
        ),
    ),
)

DIGITAL_PRODUCT_PACK = QuestionPack(
    pack_key="family.digital_product",
    description="Software, data, product, and digital delivery roles.",
    entries=(
        _pack_entry(
            step_key=STEP_KEY_ROLE_TASKS,
            question_id="ctx_digital_ownership",
            label="Welche Produkt-, Service- oder Systemverantwortung uebernimmt die Rolle?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="digital_delivery",
            priority="core",
            target_path="responsibilities",
            fact_key=FactKey.ROLE_RESPONSIBILITIES,
        ),
        _pack_entry(
            step_key=STEP_KEY_SKILLS,
            question_id="ctx_tech_stack_must",
            label="Welche Technologien sind echte Must-haves fuer den Start?",
            answer_type=AnswerType.MULTI_SELECT,
            group_key="tech_stack",
            priority="core",
            target_path="tech_stack",
            fact_key=FactKey.ROLE_TECH_STACK,
            options=[
                "Python",
                "Java",
                "JavaScript",
                "SQL",
                "Cloud",
                "DevOps",
                "Sonstiges",
            ],
        ),
    ),
)

CLINICAL_PHYSICIAN_PACK = QuestionPack(
    pack_key="family.clinical_physician",
    description="Clinical physician roles with patient and license constraints.",
    entries=(
        _pack_entry(
            step_key=STEP_KEY_ROLE_TASKS,
            question_id="ctx_medical_specialty",
            label="Welche Fachrichtung und Patientengruppe stehen im Fokus?",
            answer_type=AnswerType.SHORT_TEXT,
            group_key="medical_context",
            priority="core",
            target_path="domain_expertise",
            fact_key=FactKey.ROLE_DOMAIN_EXPERTISE,
        ),
        _pack_entry(
            step_key=STEP_KEY_SKILLS,
            question_id="ctx_approbation_required",
            label="Welche Approbation, Facharztanerkennung oder Erlaubnis ist zwingend?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="licenses",
            priority="core",
            target_path="certifications",
            fact_key=FactKey.SKILLS_CERTIFICATIONS,
        ),
    ),
)

NURSING_CARE_PACK = QuestionPack(
    pack_key="family.nursing_care",
    description="Nursing and care roles with shift and patient context.",
    entries=(
        _pack_entry(
            step_key=STEP_KEY_ROLE_TASKS,
            question_id="ctx_care_setting",
            label="In welchem Pflege- oder Versorgungssetting arbeitet die Rolle?",
            answer_type=AnswerType.SHORT_TEXT,
            group_key="care_context",
            priority="core",
            target_path="domain_expertise",
            fact_key=FactKey.ROLE_DOMAIN_EXPERTISE,
        ),
        _pack_entry(
            step_key=STEP_KEY_SKILLS,
            question_id="ctx_care_qualification",
            label="Welche Pflegequalifikation oder Anerkennung ist erforderlich?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="licenses",
            priority="core",
            target_path="certifications",
            fact_key=FactKey.SKILLS_CERTIFICATIONS,
        ),
    ),
)

FIELD_SALES_PACK = QuestionPack(
    pack_key="family.field_sales",
    description="Field sales and territory-based sales roles.",
    entries=(
        _pack_entry(
            step_key=STEP_KEY_ROLE_TASKS,
            question_id="ctx_sales_territory",
            label="Welches Vertriebsgebiet und welche Account-Typen gehoeren zur Rolle?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="sales_territory",
            priority="core",
            target_path="responsibilities",
            fact_key=FactKey.ROLE_RESPONSIBILITIES,
        ),
        _pack_entry(
            step_key=STEP_KEY_BENEFITS,
            question_id="ctx_sales_variable_pay",
            label="Wie ist variable Verguetung oder OTE fuer die Rolle geregelt?",
            answer_type=AnswerType.SHORT_TEXT,
            group_key="compensation",
            priority="core",
            target_path="salary_range.notes",
            fact_key=FactKey.BENEFITS_SALARY_RANGE,
        ),
    ),
)

FIELD_SERVICE_PACK = QuestionPack(
    pack_key="family.field_service",
    description="Skilled trades and mobile field service roles.",
    entries=(
        _pack_entry(
            step_key=STEP_KEY_ROLE_TASKS,
            question_id="ctx_service_area",
            label="In welchem Einsatzgebiet und bei welchen Einsatzarten arbeitet die Rolle?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="service_area",
            priority="core",
            target_path="responsibilities",
            fact_key=FactKey.ROLE_RESPONSIBILITIES,
        ),
        _pack_entry(
            step_key=STEP_KEY_SKILLS,
            question_id="ctx_safety_equipment",
            label="Welche Sicherheits-, Werkzeug- oder Ausruestungsanforderungen sind Pflicht?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="safety",
            priority="core",
            target_path="certifications",
            fact_key=FactKey.SKILLS_CERTIFICATIONS,
        ),
    ),
)

TRANSPORT_LOGISTICS_PACK = QuestionPack(
    pack_key="family.transport_logistics",
    description="Driver, transport, and logistics roles.",
    entries=(
        _pack_entry(
            step_key=STEP_KEY_ROLE_TASKS,
            question_id="ctx_route_model",
            label="Welche Touren-, Routen- oder Schichtlogik gilt fuer die Rolle?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="route_model",
            priority="core",
            target_path="responsibilities",
            fact_key=FactKey.ROLE_RESPONSIBILITIES,
        ),
    ),
)

CUSTOMER_SUPPORT_PACK = QuestionPack(
    pack_key="family.customer_support",
    description="Customer support and service center roles.",
    entries=(
        _pack_entry(
            step_key=STEP_KEY_ROLE_TASKS,
            question_id="ctx_support_channels",
            label="Welche Kanaele, SLAs und Eskalationen gehoeren zum Support-Modell?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="support_model",
            priority="core",
            target_path="responsibilities",
            fact_key=FactKey.ROLE_RESPONSIBILITIES,
        ),
    ),
)

REMOTE_GLOBAL_PACK = QuestionPack(
    pack_key="facet.remote_global_possible",
    description="Remote and hybrid work model constraints.",
    entries=(
        _pack_entry(
            step_key=STEP_KEY_COMPANY,
            question_id="ctx_remote_geography",
            label="Aus welchen Regionen oder Zeitzonen darf remote gearbeitet werden?",
            answer_type=AnswerType.SHORT_TEXT,
            group_key="work_arrangement",
            priority="core",
            target_path="remote_policy",
            fact_key=FactKey.COMPANY_REMOTE_POLICY,
        ),
    ),
)

DRIVING_REQUIRED_PACK = QuestionPack(
    pack_key="facet.driving_required",
    description="Driving license, vehicle, and mobility requirements.",
    entries=(
        _pack_entry(
            step_key=STEP_KEY_SKILLS,
            question_id="ctx_driving_license",
            label="Welche Fuehrerscheinklasse, Fahrzeug- oder Mobilitaetsanforderung ist noetig?",
            answer_type=AnswerType.SHORT_TEXT,
            group_key="mobility",
            priority="core",
            target_path="travel_required",
            fact_key=FactKey.ROLE_TRAVEL_REQUIRED,
        ),
    ),
)

TRAVEL_HIGH_PACK = QuestionPack(
    pack_key="facet.travel_high",
    description="Travel frequency and region requirements.",
    entries=(
        _pack_entry(
            step_key=STEP_KEY_BENEFITS,
            question_id="ctx_travel_frequency",
            label="Wie hoch ist der Reiseanteil und in welcher Region findet er statt?",
            answer_type=AnswerType.SHORT_TEXT,
            group_key="travel",
            priority="core",
            target_path="travel_required",
            fact_key=FactKey.ROLE_TRAVEL_REQUIRED,
        ),
    ),
)

REGULATED_PROFESSION_PACK = QuestionPack(
    pack_key="facet.regulated_profession",
    description="License, regulation, and formal qualification requirements.",
    entries=(
        _pack_entry(
            step_key=STEP_KEY_SKILLS,
            question_id="ctx_regulated_requirements",
            label="Welche regulatorischen Nachweise muessen vor Arbeitsbeginn vorliegen?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="licenses",
            priority="core",
            target_path="certifications",
            fact_key=FactKey.SKILLS_CERTIFICATIONS,
        ),
    ),
)

SHIFT_ONCALL_PACK = QuestionPack(
    pack_key="facet.shift_oncall_high",
    description="Shift, emergency duty, and on-call requirements.",
    entries=(
        _pack_entry(
            step_key=STEP_KEY_BENEFITS,
            question_id="ctx_shift_oncall_model",
            label="Welche Schicht-, Wochenend- oder Rufbereitschaftsregel gilt?",
            answer_type=AnswerType.SHORT_TEXT,
            group_key="shift_oncall",
            priority="core",
            target_path="on_call",
            fact_key=FactKey.ROLE_ON_CALL,
        ),
    ),
)

HIRING_REPLACEMENT_PACK = QuestionPack(
    pack_key="facet.hiring_replacement",
    description="Replacement and backfill context.",
    entries=(
        _pack_entry(
            step_key=STEP_KEY_ROLE_TASKS,
            question_id="ctx_hiring_replacement_gap",
            label="Was fehlte bisher in der Rolle oder soll beim Ersatz anders laufen?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="hiring_context",
            priority="standard",
            target_path=FactKey.ROLE_GAPS.value,
            fact_key=FactKey.ROLE_GAPS,
        ),
    ),
)

HIRING_GROWTH_PACK = QuestionPack(
    pack_key="facet.hiring_growth",
    description="Growth, build-up, and new role context.",
    entries=(
        _pack_entry(
            step_key=STEP_KEY_COMPANY,
            question_id="ctx_hiring_growth_context",
            label="Welcher Markt-, Wachstums- oder Aufbaukontext macht die Rolle jetzt noetig?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="company_profile",
            priority="standard",
            target_path=FactKey.COMPANY_GROWTH_CONTEXT.value,
            fact_key=FactKey.COMPANY_GROWTH_CONTEXT,
        ),
    ),
)

URGENCY_HIGH_PACK = QuestionPack(
    pack_key="facet.urgency_high",
    description="High-urgency hiring timeline controls.",
    entries=(
        _pack_entry(
            step_key=STEP_KEY_INTERVIEW,
            question_id="ctx_interview_urgency_tradeoffs",
            label="Welche Prozessschritte duerfen bei hoher Dringlichkeit verkuerzt oder parallelisiert werden?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="candidate_communication",
            priority="core",
            target_path=FactKey.INTERVIEW_COMMUNICATION_SLA.value,
            fact_key=FactKey.INTERVIEW_COMMUNICATION_SLA,
        ),
    ),
)

SEARCH_CONFIDENTIAL_PACK = QuestionPack(
    pack_key="facet.search_confidential",
    description="Confidential search and neutral external narrative controls.",
    entries=(
        _pack_entry(
            step_key=STEP_KEY_COMPANY,
            question_id="ctx_confidential_external_narrative",
            label="Welche Unternehmens- oder Rollendetails sollen in externen Artefakten neutralisiert werden?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="non_negotiables",
            priority="core",
            target_path=FactKey.COMPANY_NON_NEGOTIABLES.value,
            fact_key=FactKey.COMPANY_NON_NEGOTIABLES,
        ),
    ),
)

HIRING_VOLUME_MULTI_PACK = QuestionPack(
    pack_key="facet.hiring_volume_multi",
    description="Multi-hire calibration and standardized selection needs.",
    entries=(
        _pack_entry(
            step_key=STEP_KEY_INTERVIEW,
            question_id="ctx_multi_hire_calibration",
            label="Welche Kernfragen und Bewertungskriterien muessen fuer alle Einstellungen identisch bleiben?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="stage_evaluation",
            priority="core",
            target_path=FactKey.INTERVIEW_SCORECARD_TEMPLATE.value,
            fact_key=FactKey.INTERVIEW_SCORECARD_TEMPLATE,
        ),
    ),
)

ROLE_MATURITY_LOW_PACK = QuestionPack(
    pack_key="facet.role_maturity_low",
    description="Additional discovery for low-calibration roles.",
    entries=(
        _pack_entry(
            step_key=STEP_KEY_COMPANY,
            question_id="ctx_low_maturity_role_assumptions",
            label="Welche Annahmen zur Rolle muessen vor Briefing oder Sourcing noch kalibriert werden?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="company_profile",
            priority="core",
            target_path=FactKey.ROLE_ASSUMPTIONS.value,
            fact_key=FactKey.ROLE_ASSUMPTIONS,
        ),
    ),
)

LEADERSHIP_SCOPE_PACK = QuestionPack(
    pack_key="facet.leadership_scope",
    description="Leadership, reporting, and team accountability context.",
    entries=(
        _pack_entry(
            step_key=STEP_KEY_COMPANY,
            question_id="ctx_leadership_reporting_detail",
            label="Wie viele Direct Reports, fachliche Leads oder Budget-/Prioritaetsrechte gehoeren zur Rolle?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="team_reporting",
            priority="core",
            target_path=FactKey.ROLE_DECISION_SCOPE.value,
            fact_key=FactKey.ROLE_DECISION_SCOPE,
        ),
    ),
)

CONTRACT_CONSTRAINTS_PACK = QuestionPack(
    pack_key="facet.contract_constraints",
    description="Contractual constraints for non-standard employment models.",
    entries=(
        _pack_entry(
            step_key=STEP_KEY_BENEFITS,
            question_id="ctx_contract_constraints",
            label="Welche rechtlichen, tariflichen oder einkaufsseitigen Constraints gelten fuer dieses Vertragsmodell?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="legal_contract",
            priority="core",
            target_path=FactKey.BENEFITS_COLLECTIVE_AGREEMENT_CONTEXT.value,
            fact_key=FactKey.BENEFITS_COLLECTIVE_AGREEMENT_CONTEXT,
        ),
    ),
)

INTERNATIONAL_CONTEXT_PACK = QuestionPack(
    pack_key="facet.international_context",
    description="Cross-border, timezone, language, and authorization constraints.",
    entries=(
        _pack_entry(
            step_key=STEP_KEY_COMPANY,
            question_id="ctx_company_allowed_regions_timezones",
            label="Welche Regionen, Laender oder Zeitzonen sind fuer diese Rolle erlaubt?",
            answer_type=AnswerType.MULTI_SELECT,
            group_key="work_arrangement",
            priority="core",
            target_path=FactKey.COMPANY_ALLOWED_REGIONS_TIMEZONES.value,
            fact_key=FactKey.COMPANY_ALLOWED_REGIONS_TIMEZONES,
            options=[
                "Deutschland",
                "DACH",
                "EU",
                "EMEA",
                "weltweit",
                "CET/CEST",
                "US-Zeitzonen",
                "Sonstiges",
            ],
        ),
        _pack_entry(
            step_key=STEP_KEY_BENEFITS,
            question_id="ctx_international_payroll_authorization",
            label="Welche Payroll-, Visa- oder Work-Authorization-Grenzen gelten bei internationalen Kandidat:innen?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="legal_contract",
            priority="core",
            target_path=FactKey.LEGAL_WORK_AUTHORIZATION_SUPPORT.value,
            fact_key=FactKey.LEGAL_WORK_AUTHORIZATION_SUPPORT,
        ),
    ),
)

SKILL_GROUP_DOMAIN_KNOWLEDGE_PACK = QuestionPack(
    pack_key=f"skill_group.{ESCO_QUESTION_SKILL_GROUP_DOMAIN_KNOWLEDGE}",
    description="ESCO domain knowledge context.",
    entries=(
        _pack_entry(
            step_key=STEP_KEY_SKILLS,
            question_id="ctx_sg_domain_knowledge",
            label="Welche fachlichen Kenntnisse sind fuer die Rolle zwingend erforderlich?",
            answer_type=AnswerType.LONG_TEXT,
            group_key=ESCO_QUESTION_SKILL_GROUP_DOMAIN_KNOWLEDGE,
            priority="standard",
            target_path="domain_expertise",
            fact_key=FactKey.ROLE_DOMAIN_EXPERTISE,
        ),
    ),
)

SKILL_GROUP_TOOLS_METHODS_PACK = QuestionPack(
    pack_key=f"skill_group.{ESCO_QUESTION_SKILL_GROUP_TOOLS_METHODS}",
    description="ESCO tools, systems, methods context.",
    entries=(
        _pack_entry(
            step_key=STEP_KEY_SKILLS,
            question_id="ctx_sg_tools_methods",
            label="Welche Tools, Systeme oder Methoden muessen Kandidat:innen sicher anwenden?",
            answer_type=AnswerType.LONG_TEXT,
            group_key=ESCO_QUESTION_SKILL_GROUP_TOOLS_METHODS,
            priority="standard",
            target_path="tech_stack",
            fact_key=FactKey.ROLE_TECH_STACK,
        ),
    ),
)

SKILL_GROUP_REGULATION_SAFETY_PACK = QuestionPack(
    pack_key=f"skill_group.{ESCO_QUESTION_SKILL_GROUP_REGULATION_SAFETY}",
    description="ESCO regulation, safety, and qualification context.",
    entries=(
        _pack_entry(
            step_key=STEP_KEY_SKILLS,
            question_id="ctx_sg_regulation_safety",
            label="Gibt es gesetzliche, sicherheitsrelevante oder qualifikatorische Anforderungen?",
            answer_type=AnswerType.LONG_TEXT,
            group_key=ESCO_QUESTION_SKILL_GROUP_REGULATION_SAFETY,
            priority="standard",
            target_path="certifications",
            fact_key=FactKey.SKILLS_CERTIFICATIONS,
        ),
    ),
)

SKILL_GROUP_CUSTOMER_CLIENT_INTERACTION_PACK = QuestionPack(
    pack_key=f"skill_group.{ESCO_QUESTION_SKILL_GROUP_CUSTOMER_CLIENT_INTERACTION}",
    description="ESCO customer, client, user, and stakeholder interaction context.",
    entries=(
        _pack_entry(
            step_key=STEP_KEY_ROLE_TASKS,
            question_id="ctx_sg_customer_client_interaction",
            label="Mit welchen Kund:innen, Nutzer:innen oder Stakeholdern arbeitet die Rolle direkt?",
            answer_type=AnswerType.LONG_TEXT,
            group_key=ESCO_QUESTION_SKILL_GROUP_CUSTOMER_CLIENT_INTERACTION,
            priority="standard",
            target_path="responsibilities",
            fact_key=FactKey.ROLE_RESPONSIBILITIES,
        ),
    ),
)

SKILL_GROUP_DOCUMENTATION_REPORTING_PACK = QuestionPack(
    pack_key=f"skill_group.{ESCO_QUESTION_SKILL_GROUP_DOCUMENTATION_REPORTING}",
    description="ESCO documentation, reporting, and quality context.",
    entries=(
        _pack_entry(
            step_key=STEP_KEY_ROLE_TASKS,
            question_id="ctx_sg_documentation_reporting",
            label="Welche Dokumentations-, Reporting- oder Qualitaetsanforderungen sind relevant?",
            answer_type=AnswerType.LONG_TEXT,
            group_key=ESCO_QUESTION_SKILL_GROUP_DOCUMENTATION_REPORTING,
            priority="standard",
            target_path="responsibilities",
            fact_key=FactKey.ROLE_RESPONSIBILITIES,
        ),
    ),
)

SKILL_GROUP_LEADERSHIP_COORDINATION_PACK = QuestionPack(
    pack_key=f"skill_group.{ESCO_QUESTION_SKILL_GROUP_LEADERSHIP_COORDINATION}",
    description="ESCO leadership, planning, and coordination context.",
    entries=(
        _pack_entry(
            step_key=STEP_KEY_ROLE_TASKS,
            question_id="ctx_sg_leadership_coordination",
            label="Ist fachliche oder disziplinarische Fuehrung Teil der Rolle?",
            answer_type=AnswerType.LONG_TEXT,
            group_key=ESCO_QUESTION_SKILL_GROUP_LEADERSHIP_COORDINATION,
            priority="standard",
            target_path="responsibilities",
            fact_key=FactKey.ROLE_RESPONSIBILITIES,
        ),
    ),
)

SKILL_GROUP_PHYSICAL_MANUAL_CONTEXT_PACK = QuestionPack(
    pack_key=f"skill_group.{ESCO_QUESTION_SKILL_GROUP_PHYSICAL_MANUAL_CONTEXT}",
    description="ESCO physical, manual, and work-environment context.",
    entries=(
        _pack_entry(
            step_key=STEP_KEY_ROLE_TASKS,
            question_id="ctx_sg_physical_manual_context",
            label="Welche koerperlichen, manuellen oder umgebungsbezogenen Anforderungen praegen die Arbeit?",
            answer_type=AnswerType.LONG_TEXT,
            group_key=ESCO_QUESTION_SKILL_GROUP_PHYSICAL_MANUAL_CONTEXT,
            priority="standard",
            target_path="responsibilities",
            fact_key=FactKey.ROLE_RESPONSIBILITIES,
        ),
    ),
)

SKILL_GROUP_DIGITAL_DATA_AI_PACK = QuestionPack(
    pack_key=f"skill_group.{ESCO_QUESTION_SKILL_GROUP_DIGITAL_DATA_AI}",
    description="ESCO digital, data, analytics, automation, and AI context.",
    entries=(
        _pack_entry(
            step_key=STEP_KEY_SKILLS,
            question_id="ctx_sg_digital_data_ai",
            label="Welche digitalen Systeme, Daten- oder Automatisierungsanteile sind erfolgskritisch?",
            answer_type=AnswerType.LONG_TEXT,
            group_key=ESCO_QUESTION_SKILL_GROUP_DIGITAL_DATA_AI,
            priority="standard",
            target_path="tech_stack",
            fact_key=FactKey.ROLE_TECH_STACK,
        ),
    ),
)

SKILL_GROUP_LANGUAGE_COMMUNICATION_PACK = QuestionPack(
    pack_key=f"skill_group.{ESCO_QUESTION_SKILL_GROUP_LANGUAGE_COMMUNICATION}",
    description="ESCO language and communication context.",
    entries=(
        _pack_entry(
            step_key=STEP_KEY_SKILLS,
            question_id="ctx_sg_language_communication",
            label="Welche Sprach- und Kommunikationsanforderungen sind zwingend?",
            answer_type=AnswerType.LONG_TEXT,
            group_key=ESCO_QUESTION_SKILL_GROUP_LANGUAGE_COMMUNICATION,
            priority="standard",
            target_path="languages",
            fact_key=FactKey.SKILLS_LANGUAGES,
        ),
    ),
)

SKILL_GROUP_TRANSVERSAL_FIT_PACK = QuestionPack(
    pack_key=f"skill_group.{ESCO_QUESTION_SKILL_GROUP_TRANSVERSAL_FIT}",
    description="ESCO transversal fit and working-style context.",
    entries=(
        _pack_entry(
            step_key=STEP_KEY_ROLE_TASKS,
            question_id="ctx_sg_transversal_fit",
            label="Welche Arbeitsweise ist fuer Erfolg in den ersten sechs Monaten entscheidend?",
            answer_type=AnswerType.LONG_TEXT,
            group_key=ESCO_QUESTION_SKILL_GROUP_TRANSVERSAL_FIT,
            priority="detail",
            target_path="success_metrics",
            fact_key=FactKey.ROLE_SUCCESS_METRICS,
        ),
    ),
)

QUESTION_PACK_REGISTRY: dict[str, QuestionPack] = {
    pack.pack_key: pack
    for pack in (
        BASE_CORE_PACK,
        BASE_INTERVIEW_PACK,
        DIGITAL_PRODUCT_PACK,
        CLINICAL_PHYSICIAN_PACK,
        NURSING_CARE_PACK,
        FIELD_SALES_PACK,
        FIELD_SERVICE_PACK,
        TRANSPORT_LOGISTICS_PACK,
        CUSTOMER_SUPPORT_PACK,
        REMOTE_GLOBAL_PACK,
        DRIVING_REQUIRED_PACK,
        TRAVEL_HIGH_PACK,
        REGULATED_PROFESSION_PACK,
        SHIFT_ONCALL_PACK,
        HIRING_REPLACEMENT_PACK,
        HIRING_GROWTH_PACK,
        URGENCY_HIGH_PACK,
        SEARCH_CONFIDENTIAL_PACK,
        HIRING_VOLUME_MULTI_PACK,
        ROLE_MATURITY_LOW_PACK,
        LEADERSHIP_SCOPE_PACK,
        CONTRACT_CONSTRAINTS_PACK,
        INTERNATIONAL_CONTEXT_PACK,
        SKILL_GROUP_DOMAIN_KNOWLEDGE_PACK,
        SKILL_GROUP_TOOLS_METHODS_PACK,
        SKILL_GROUP_REGULATION_SAFETY_PACK,
        SKILL_GROUP_CUSTOMER_CLIENT_INTERACTION_PACK,
        SKILL_GROUP_DOCUMENTATION_REPORTING_PACK,
        SKILL_GROUP_LEADERSHIP_COORDINATION_PACK,
        SKILL_GROUP_PHYSICAL_MANUAL_CONTEXT_PACK,
        SKILL_GROUP_DIGITAL_DATA_AI_PACK,
        SKILL_GROUP_LANGUAGE_COMMUNICATION_PACK,
        SKILL_GROUP_TRANSVERSAL_FIT_PACK,
    )
}


def get_question_pack(pack_key: str) -> QuestionPack | None:
    return QUESTION_PACK_REGISTRY.get(pack_key)
