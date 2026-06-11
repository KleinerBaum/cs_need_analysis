from __future__ import annotations

from occupation_context import (
    build_occupation_question_context,
    classify_occupation_context,
    resolve_question_module_keys,
)
from schemas import JobAdExtract, OccupationFamily, RelevanceLevel, WorkArrangement


def test_classifies_digital_product_with_remote_and_irrelevant_driving() -> None:
    profile = classify_occupation_context(
        job=JobAdExtract(
            job_title="Senior Software Developer",
            remote_policy="Remote-first in EU time zones",
            tech_stack=["Python", "Cloud"],
        )
    )

    assert profile.occupation_family == OccupationFamily.DIGITAL_PRODUCT
    assert profile.work_arrangement == WorkArrangement.REMOTE_POSSIBLE
    assert profile.driving_relevance == RelevanceLevel.IRRELEVANT
    assert "family.digital_product" in profile.pack_keys
    assert "facet.remote_global_possible" in profile.pack_keys


def test_confirmed_esco_anchor_sets_authority_source() -> None:
    profile = classify_occupation_context(
        job=JobAdExtract(job_title="Arzt Innere Medizin"),
        esco_selected={
            "uri": "http://data.europa.eu/esco/occupation/doctor",
            "title": "Medical doctor",
            "type": "occupation",
        },
    )

    assert profile.authority_source == "user_confirmed_esco"
    assert profile.occupation_family == OccupationFamily.CLINICAL_PHYSICIAN
    assert profile.regulated_profession is True
    assert profile.work_arrangement == WorkArrangement.ONSITE_REQUIRED
    assert "facet.regulated_profession" in profile.pack_keys


def test_field_sales_promotes_driving_and_travel() -> None:
    profile = classify_occupation_context(
        job=JobAdExtract(
            job_title="Sales Representative Aussendienst",
            responsibilities=["Kundenbesuche im Vertriebsgebiet"],
        )
    )

    assert profile.occupation_family == OccupationFamily.FIELD_SALES
    assert profile.driving_relevance == RelevanceLevel.HIGH
    assert profile.travel_relevance == RelevanceLevel.REQUIRED
    assert "facet.driving_required" in profile.pack_keys
    assert "facet.travel_high" in profile.pack_keys


def test_unknown_profile_uses_generic_fallback() -> None:
    profile = classify_occupation_context(job=JobAdExtract(job_title=""))

    assert profile.occupation_family == OccupationFamily.UNKNOWN
    assert profile.authority_source == "generic_fallback"
    assert profile.pack_keys == ["base.core", "base.interview"]


def test_build_occupation_question_context_normalizes_esco_fields() -> None:
    context = build_occupation_question_context(
        esco_selected={
            "uri": "uri:occupation:analytics-manager",
            "title": "Analytics manager",
            "iscoGroup": "2512.1",
        },
        esco_payload={
            "alternativeLabel": ["AI Strategy Manager", "Analytics Lead"],
            "naceCodes": ["J62", "M70"],
            "regulatedProfession": False,
        },
        essential_skills=[
            {
                "uri": "uri:skill:data-governance",
                "title": "Data governance",
                "type": "skill",
                "group_hint": "data analytics",
                "skillReusabilityLevel": "sector-specific",
            }
        ],
        optional_skills=[
            {
                "uri": "uri:skill:stakeholder",
                "title": "Stakeholder management",
                "type": "skill",
                "group_hint": "customer stakeholder communication",
            }
        ],
        matrix_coverage_rows=[
            {
                "skill_group_label": "Documentation and reporting",
                "skill_group_id": "sg-documentation",
            }
        ],
        esco_version="v1.2.1",
        source_mode="hybrid",
    )

    assert context.occupation_uri == "uri:occupation:analytics-manager"
    assert context.preferred_label == "Analytics manager"
    assert context.isco_code == "2512"
    assert context.isco_path == ["2", "25", "251", "2512"]
    assert context.nace_codes == ["J62", "M70"]
    assert context.regulated_profession is False
    assert context.essential_skill_uris == ["uri:skill:data-governance"]
    assert "digital_data_ai" in context.skill_groups
    assert "customer_client_interaction" in context.skill_groups
    assert "documentation_reporting" in context.skill_groups
    assert context.reuse_levels == ["sector-specific"]
    assert context.esco_version == "v1.2.1"
    assert context.source_mode == "hybrid"


def test_resolve_question_module_keys_is_ordered_and_degrades() -> None:
    context = build_occupation_question_context(
        esco_selected={
            "uri": "uri:occupation:1",
            "title": "Data Engineer",
            "isco08Code": "2511",
        },
        esco_payload={"naceCodes": ["J62"], "regulatedProfession": True},
        essential_skills=[
            {
                "uri": "uri:skill:python",
                "title": "Python",
                "group_hint": "digital data",
            }
        ],
    )

    keys, skipped = resolve_question_module_keys(context)

    assert keys == [
        "BASE_RECRUITING",
        "ISCO1:2",
        "ISCO3:251",
        "ISCO4:2511",
        "ESCO_OCCUPATION:uri:occupation:1",
        "SKILL_GROUP:digital_data_ai",
        "NACE:J62",
        "REGULATED_PROFESSION",
    ]
    assert skipped == {}

    empty_keys, empty_skipped = resolve_question_module_keys(None)

    assert empty_keys == ["BASE_RECRUITING"]
    assert empty_skipped == {"context": "missing"}
