from schemas import (
    BooleanSearchPack,
    EmploymentContractDraft,
    InterviewPrepSheetHR,
    InterviewPrepSheetHiringManager,
    QuestionPlan,
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


def test_vacancy_brief_llm_schema_is_strict_for_structured_outputs() -> None:
    schema = VacancyBriefLLM.model_json_schema()
    assert schema.get("additionalProperties") is False
    assert "structured_data" not in schema["properties"]


def test_new_interview_and_contract_schemas_are_strict() -> None:
    hr_schema = InterviewPrepSheetHR.model_json_schema()
    hm_schema = InterviewPrepSheetHiringManager.model_json_schema()
    contract_schema = EmploymentContractDraft.model_json_schema()

    assert hr_schema.get("additionalProperties") is False
    assert hm_schema.get("additionalProperties") is False
    assert contract_schema.get("additionalProperties") is False


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
