from schemas import QuestionPlan, VacancyBriefLLM


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
