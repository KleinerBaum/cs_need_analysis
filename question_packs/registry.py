"""Canonical deterministic question packs compiled into the QuestionPlan."""

from __future__ import annotations

from constants import (
    AnswerType,
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
        ),
        _pack_entry(
            step_key=STEP_KEY_SKILLS,
            question_id="ctx_tech_stack_must",
            label="Welche Technologien sind echte Must-haves fuer den Start?",
            answer_type=AnswerType.MULTI_SELECT,
            group_key="tech_stack",
            priority="core",
            target_path="tech_stack",
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
        ),
        _pack_entry(
            step_key=STEP_KEY_SKILLS,
            question_id="ctx_approbation_required",
            label="Welche Approbation, Facharztanerkennung oder Erlaubnis ist zwingend?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="licenses",
            priority="core",
            target_path="certifications",
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
        ),
        _pack_entry(
            step_key=STEP_KEY_SKILLS,
            question_id="ctx_care_qualification",
            label="Welche Pflegequalifikation oder Anerkennung ist erforderlich?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="licenses",
            priority="core",
            target_path="certifications",
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
        ),
        _pack_entry(
            step_key=STEP_KEY_BENEFITS,
            question_id="ctx_sales_variable_pay",
            label="Wie ist variable Verguetung oder OTE fuer die Rolle geregelt?",
            answer_type=AnswerType.SHORT_TEXT,
            group_key="compensation",
            priority="core",
            target_path="salary_range.notes",
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
        ),
        _pack_entry(
            step_key=STEP_KEY_SKILLS,
            question_id="ctx_safety_equipment",
            label="Welche Sicherheits-, Werkzeug- oder Ausruestungsanforderungen sind Pflicht?",
            answer_type=AnswerType.LONG_TEXT,
            group_key="safety",
            priority="core",
            target_path="certifications",
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
    )
}


def get_question_pack(pack_key: str) -> QuestionPack | None:
    return QUESTION_PACK_REGISTRY.get(pack_key)
