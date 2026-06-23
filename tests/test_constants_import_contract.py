from __future__ import annotations

import ast
from pathlib import Path

import constants
from _constants import esco, facts, questions, state_keys, summary, ui, usage, wizard


ROOT = Path(__file__).resolve().parents[1]
THIS_FILE = Path(__file__).resolve()
ALLOWED_PRIVATE_IMPORTERS = {
    ROOT / "constants.py",
    THIS_FILE,
}


def _iter_python_files() -> list[Path]:
    return [
        path
        for path in ROOT.rglob("*.py")
        if "__pycache__" not in path.parts
        and ".venv" not in path.parts
        and not any(part.startswith(".") for part in path.relative_to(ROOT).parts)
    ]


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def test_constants_exports_all_repo_imported_names() -> None:
    imported_names: set[str] = set()
    for path in _iter_python_files():
        for node in ast.walk(_parse(path)):
            if not isinstance(node, ast.ImportFrom) or node.module != "constants":
                continue
            imported_names.update(alias.name for alias in node.names)

    assert imported_names
    missing_names = sorted(
        name for name in imported_names if name != "*" and not hasattr(constants, name)
    )
    assert missing_names == []


def test_constants_reexports_private_group_objects() -> None:
    assert constants.SSKey is state_keys.SSKey
    assert constants.STEPS is wizard.STEPS
    assert constants.WizardStepDef is wizard.WizardStepDef
    assert constants.UI_MODE_VALUES is ui.UI_MODE_VALUES
    assert constants.UI_MODE_QUESTION_LIMIT_RATIOS is ui.UI_MODE_QUESTION_LIMIT_RATIOS
    assert constants.DEFAULT_ESCO_RELEASE_LANE is esco.DEFAULT_ESCO_RELEASE_LANE
    assert constants.AnswerType is questions.AnswerType
    assert constants.FactKey is facts.FactKey
    assert constants.INTAKE_FACTS is facts.INTAKE_FACTS
    assert constants.SUMMARY_ARTIFACT_IDS is summary.SUMMARY_ARTIFACT_IDS
    assert constants.SUMMARY_ACTIVE_ARTIFACT_IDS is summary.SUMMARY_ACTIVE_ARTIFACT_IDS
    assert constants.UsageEventType is usage.UsageEventType


def test_private_constants_modules_are_not_imported_by_app_code() -> None:
    offenders: list[str] = []
    for path in _iter_python_files():
        if path in ALLOWED_PRIVATE_IMPORTERS or "_constants" in path.parts:
            continue
        for node in ast.walk(_parse(path)):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module == "_constants" or node.module.startswith("_constants."):
                    offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "_constants" or alias.name.startswith(
                        "_constants."
                    ):
                        offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}")

    assert offenders == []
