from __future__ import annotations

from occupation_context import classify_occupation_context
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
