from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace

SKILLS_PATH = Path(__file__).resolve().parents[1] / "wizard_pages" / "05_skills.py"
SPEC = spec_from_file_location("wizard_pages.page_05_skills", SKILLS_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load skills page module")
SKILLS_MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(SKILLS_MODULE)  # type: ignore[attr-defined]


def test_merge_llm_skill_suggestions_dedupes_against_existing_esco_titles() -> None:
    merged = SKILLS_MODULE._merge_llm_skill_suggestions(
        llm_skills=[
            {
                "label": "Python",
                "importance": "high",
                "rationale": "relevant",
                "evidence": "jobspec",
            },
            {
                "label": "Data Governance",
                "source_hint": "esco_rag",
                "source_file": "rag/skills.json",
                "concept_uri": "uri:skill:data-governance",
                "importance": "medium",
                "rationale": "relevant",
                "evidence": "answers",
            },
            {
                "label": "data governance",
                "importance": "low",
                "rationale": "duplicate",
                "evidence": "llm",
            },
        ],
        blocked_labels=["Python", "Stakeholder Management"],
    )

    assert merged == [
        {
            "label": "Data Governance",
            "uri": "",
            "source": "AI suggestion",
            "source_hint": "esco_rag",
            "source_file": "rag/skills.json",
            "concept_uri": "uri:skill:data-governance",
            "importance": "medium",
            "rationale": "relevant",
            "evidence": "answers",
        }
    ]


def test_save_selected_skill_suggestions_merges_without_duplicates() -> None:
    setattr(
        SKILLS_MODULE,
        "st",
        SimpleNamespace(session_state={"cs.skills.selected": ["Python"]}),
    )

    added = SKILLS_MODULE._save_selected_skill_suggestions(["python", "SQL"])

    assert added == 1
    assert SKILLS_MODULE.st.session_state["cs.skills.selected"] == ["Python", "SQL"]


def test_merge_llm_skill_suggestions_handles_empty_result() -> None:
    merged = SKILLS_MODULE._merge_llm_skill_suggestions(
        llm_skills=[],
        blocked_labels=["Python"],
    )

    assert merged == []


def test_merge_llm_skill_suggestions_dedupes_by_uri() -> None:
    merged = SKILLS_MODULE._merge_llm_skill_suggestions(
        llm_skills=[
            {"label": "Skill A", "uri": "uri:1", "source": "AI suggestion"},
            {"label": "Skill B", "uri": "uri:1", "source": "ESCO RAG"},
        ],
        blocked_labels=[],
    )
    assert len(merged) == 1
    assert merged[0]["label"] == "Skill A"


class _NoopSpinner:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeStreamlit:
    def __init__(self, session_state: dict[str, object]):
        self.session_state = session_state
        self.warnings: list[str] = []

    def spinner(self, _message: str) -> _NoopSpinner:
        return _NoopSpinner()

    def warning(self, message: str) -> None:
        self.warnings.append(message)


def test_default_ai_skill_generation_runs_once_and_uses_fixed_count(monkeypatch) -> None:
    session_state = {
        SKILLS_MODULE.SSKey.SKILLS_AI_DEFAULT_GENERATED.value: False,
        SKILLS_MODULE.SSKey.SKILLS_LLM_SUGGESTED.value: [],
    }
    fake_st = _FakeStreamlit(session_state)
    calls: list[int] = []

    def fake_generate(**kwargs):
        calls.append(kwargs["target_skill_count"])
        return [{"label": "Kubernetes", "source": "AI suggestion"}]

    monkeypatch.setattr(SKILLS_MODULE, "st", fake_st)
    monkeypatch.setattr(SKILLS_MODULE, "_generate_ai_skill_suggestions", fake_generate)

    job = SKILLS_MODULE.JobAdExtract(job_title="Platform Engineer")

    first = SKILLS_MODULE._maybe_generate_default_ai_skill_suggestions(
        job=job,
        deduped_must=[],
        deduped_nice=[],
    )
    second = SKILLS_MODULE._maybe_generate_default_ai_skill_suggestions(
        job=job,
        deduped_must=[],
        deduped_nice=[],
    )

    assert first == [{"label": "Kubernetes", "source": "AI suggestion"}]
    assert second is None
    assert calls == [5]
    assert session_state[SKILLS_MODULE.SSKey.SKILLS_LLM_SUGGESTED.value] == first
    assert session_state[SKILLS_MODULE.SSKey.SKILLS_AI_DEFAULT_GENERATED.value] is True


def test_default_ai_skill_generation_skips_existing_llm_suggestions(monkeypatch) -> None:
    session_state = {
        SKILLS_MODULE.SSKey.SKILLS_AI_DEFAULT_GENERATED.value: False,
        SKILLS_MODULE.SSKey.SKILLS_LLM_SUGGESTED.value: [{"label": "Python"}],
    }
    fake_st = _FakeStreamlit(session_state)
    calls: list[int] = []

    def fake_generate(**kwargs):
        calls.append(kwargs["target_skill_count"])
        return []

    monkeypatch.setattr(SKILLS_MODULE, "st", fake_st)
    monkeypatch.setattr(SKILLS_MODULE, "_generate_ai_skill_suggestions", fake_generate)

    result = SKILLS_MODULE._maybe_generate_default_ai_skill_suggestions(
        job=SKILLS_MODULE.JobAdExtract(job_title="Data Engineer"),
        deduped_must=[],
        deduped_nice=[],
    )

    assert result is None
    assert calls == []
    assert session_state[SKILLS_MODULE.SSKey.SKILLS_LLM_SUGGESTED.value] == [
        {"label": "Python"}
    ]
    assert session_state[SKILLS_MODULE.SSKey.SKILLS_AI_DEFAULT_GENERATED.value] is False
