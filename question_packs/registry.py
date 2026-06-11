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
            step_key=STEP_KEY_ROLE_TASKS,
            question_id="ctx_success_criteria",
            label="Woran wird Erfolg in den ersten 6 Monaten gemessen?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="success_context",
            priority="core",
            target_path="success_metrics",
            fact_key=FactKey.ROLE_SUCCESS_METRICS,
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
