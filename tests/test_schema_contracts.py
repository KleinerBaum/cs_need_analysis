from schemas import (
    BooleanSearchPack,
    CompanyWebsiteResearch,
    EmploymentContractDraft,
    JobAdExtract,
    JobAdFieldEvidence,
    InterviewPrepSheetHR,
    InterviewPrepSheetHiringManager,
    InterviewScorecardTemplate,
    OccupationContextProfile,
    OccupationQuestionContext,
    QuestionPlan,
    QuestionFlowProvenance,
    RequirementSuggestionPack,
    SkillRequirementItem,
    TravelProfile,
    VariablePay,
    VacancyStructuredData,
    VacancyBriefLLM,
)


def test_question_default_schema_is_typed_for_openai_structured_outputs() -> None:
    schema = QuestionPlan.model_json_schema()
    default_schema = schema["$defs"]["Question"]["properties"]["default"]
    any_of = default_schema.get("anyOf", [])
    assert any_of, "default field schema must contain anyOf branches"
    assert all("type" in branch for branch in any_of), (
        "every anyOf branch must include a concrete type for OpenAI Structured Outputs"
    )
    assert "fact_key" in schema["$defs"]["Question"]["properties"]
    assert "follow_up_prompts" in schema["$defs"]["Question"]["properties"]


def test_job_ad_extract_field_evidence_is_optional_and_strict() -> None:
    legacy_extract = JobAdExtract.model_validate({"job_title": "Data Engineer"})
    enriched_extract = JobAdExtract.model_validate(
        {
            "job_title": "Data Engineer",
            "field_evidence": [
                {
                    "field_name": "job_title",
                    "confidence": 0.8,
                    "evidence_snippet": "Data Engineer gesucht",
                    "needs_confirmation": False,
                }
            ],
        }
    )
    evidence_schema = JobAdFieldEvidence.model_json_schema()

    assert legacy_extract.field_evidence == []
    assert enriched_extract.field_evidence[0].field_name == "job_title"
    assert evidence_schema.get("additionalProperties") is False


def test_vacancy_brief_llm_schema_is_strict_for_structured_outputs() -> None:
    schema = VacancyBriefLLM.model_json_schema()
    assert schema.get("additionalProperties") is False
    assert "structured_data" not in schema["properties"]


def test_new_interview_and_contract_schemas_are_strict() -> None:
    hr_schema = InterviewPrepSheetHR.model_json_schema()
    hm_schema = InterviewPrepSheetHiringManager.model_json_schema()
    contract_schema = EmploymentContractDraft.model_json_schema()
    scorecard_schema = InterviewScorecardTemplate.model_json_schema()

    assert hr_schema.get("additionalProperties") is False
    assert hm_schema.get("additionalProperties") is False
    assert contract_schema.get("additionalProperties") is False
    assert scorecard_schema.get("additionalProperties") is False


def test_vacancy_structured_data_accepts_new_normalized_objects() -> None:
    payload = VacancyStructuredData.model_validate(
        {
            "job_extract": {},
            "answers": {},
            "skill_items": [
                {
                    "label": "Python",
                    "status": "must",
                    "proficiency": "solid",
                    "readiness_timing": "start",
                }
            ],
            "variable_pay": {
                "eligible": True,
                "currency": "EUR",
                "bonus_logic": "10% target bonus",
            },
            "travel_profile": {
                "required": True,
                "percent": 25,
                "region": "DACH",
            },
            "interview_scorecard_template": {
                "stage": "Fachinterview",
                "criteria": [{"title": "Python", "weight_percent": 40}],
                "recommendation_options": ["hire", "no_hire"],
            },
        }
    )

    assert isinstance(payload.skill_items[0], SkillRequirementItem)
    assert isinstance(payload.variable_pay, VariablePay)
    assert isinstance(payload.travel_profile, TravelProfile)
    assert isinstance(payload.interview_scorecard_template, InterviewScorecardTemplate)


def test_interview_hr_sheet_contract_references_strict_question_blocks() -> None:
    hr_schema = InterviewPrepSheetHR.model_json_schema()
    defs = hr_schema.get("$defs", {})
    question_block_schema = defs["InterviewQuestionBlock"]
    assert question_block_schema.get("additionalProperties") is False
    assert "signal_tags" in question_block_schema["properties"]


def test_employment_contract_contract_references_strict_clauses() -> None:
    contract_schema = EmploymentContractDraft.model_json_schema()
    defs = contract_schema.get("$defs", {})
    clause_schema = defs["ContractClause"]
    assert clause_schema.get("additionalProperties") is False
    assert clause_schema["properties"]["required"]["type"] == "boolean"


def test_boolean_search_pack_has_channel_specific_fields() -> None:
    schema = BooleanSearchPack.model_json_schema()
    assert schema.get("additionalProperties") is False
    properties = schema["properties"]
    assert {"google", "linkedin", "xing"}.issubset(properties)


def test_boolean_search_pack_channel_queries_are_strict() -> None:
    schema = BooleanSearchPack.model_json_schema()
    defs = schema.get("$defs", {})
    channel_schema = defs["BooleanSearchChannelQueries"]
    assert channel_schema.get("additionalProperties") is False


def test_requirement_suggestion_pack_schema_is_strict() -> None:
    schema = RequirementSuggestionPack.model_json_schema()
    assert schema.get("additionalProperties") is False
    defs = schema.get("$defs", {})
    item_schema = defs["RequirementSuggestionItem"]
    assert item_schema.get("additionalProperties") is False


def test_company_website_research_contract_is_strict_and_typed() -> None:
    schema = CompanyWebsiteResearch.model_json_schema()
    assert schema.get("additionalProperties") is False
    properties = schema["properties"]
    assert set(properties) == {"homepage_url", "sections", "open_question_matches"}
    defs = schema.get("$defs", {})
    assert defs["WebsiteResearchSection"].get("additionalProperties") is False
    assert defs["WebsiteOpenQuestionMatch"].get("additionalProperties") is False


def test_occupation_context_contracts_are_strict() -> None:
    profile_schema = OccupationContextProfile.model_json_schema()
    question_context_schema = OccupationQuestionContext.model_json_schema()
    provenance_schema = QuestionFlowProvenance.model_json_schema()

    assert profile_schema.get("additionalProperties") is False
    assert question_context_schema.get("additionalProperties") is False
    assert provenance_schema.get("additionalProperties") is False
    assert "occupation_family" in profile_schema["properties"]
    assert "skill_groups" in question_context_schema["properties"]
    assert "selected_pack_keys" in provenance_schema["properties"]
    assert "resolved_module_keys" in provenance_schema["properties"]


def test_vacancy_structured_data_rejects_invalid_company_website_research_shape() -> None:
    payload = {
        "job_extract": {},
        "answers": {},
        "company_website_research": {
            "homepage_url": "https://example.com",
            "sections": [],
            "open_question_matches": {},
        },
    }

    try:
        VacancyStructuredData.model_validate(payload)
    except Exception as exc:  # noqa: BLE001
        message = str(exc)
        assert "company_website_research.sections" in message
        assert "company_website_research.open_question_matches" in message
    else:
        raise AssertionError("Expected validation to fail for invalid research payload")
