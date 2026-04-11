from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ROLE_TASKS_PATH = (
    Path(__file__).resolve().parents[1] / "wizard_pages" / "04_role_tasks.py"
)
SPEC = spec_from_file_location("wizard_pages.page_04_role_tasks", ROLE_TASKS_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load role tasks module")
ROLE_TASKS_MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(ROLE_TASKS_MODULE)  # type: ignore[attr-defined]


def test_normalize_and_dedupe_task_terms() -> None:
    deduped = ROLE_TASKS_MODULE._dedupe_task_terms(
        [
            " Ownership ",
            "ownership",
            "  ",
            "Stakeholder Alignment",
            "stakeholder alignment",
        ]
    )

    assert ROLE_TASKS_MODULE._normalize_task_term("  OWNERSHIP  ") == "ownership"
    assert deduped == ["Ownership", "Stakeholder Alignment"]


def test_load_esco_task_suggestions_returns_empty_for_sparse_payload(
    monkeypatch,
) -> None:
    class _SparseEscoClient:
        def resource_occupation(self, *, uri: str) -> dict[str, object]:
            return {"uri": uri, "preferredLabel": "Data Engineer"}

    monkeypatch.setattr(ROLE_TASKS_MODULE, "EscoClient", _SparseEscoClient)

    suggestions, error = (
        ROLE_TASKS_MODULE._load_esco_task_suggestions_from_selected_occupation(
            "uri:occupation:1"
        )
    )

    assert error is None
    assert suggestions == []


def test_merge_llm_task_suggestions_dedupes_against_blocked_labels() -> None:
    merged = ROLE_TASKS_MODULE._merge_llm_task_suggestions(
        llm_tasks=[
            {
                "label": "Roadmap steuern",
                "importance": "high",
                "rationale": "Neu",
                "evidence": "A",
            },
            {
                "label": " ownership ",
                "importance": "medium",
                "rationale": "Duplikat",
                "evidence": "B",
            },
        ],
        blocked_labels=["Ownership", "Stakeholder-Management"],
    )

    assert merged == [
        {
            "label": "Roadmap steuern",
            "source": "AI",
            "importance": "high",
            "rationale": "Neu",
            "evidence": "A",
        }
    ]


def test_save_selected_task_suggestions_merges_without_duplicates() -> None:
    setattr(
        ROLE_TASKS_MODULE,
        "st",
        SimpleNamespace(session_state={"cs.role_tasks.selected": ["Ownership"]}),
    )

    added = ROLE_TASKS_MODULE._save_selected_task_suggestions(
        [" ownership ", "Incident Management"]
    )

    assert added == 1
    assert ROLE_TASKS_MODULE.st.session_state["cs.role_tasks.selected"] == [
        "Ownership",
        "Incident Management",
    ]
