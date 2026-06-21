from __future__ import annotations

import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_ruff_starts_with_critical_check_only_rules() -> None:
    config = _load_pyproject()

    assert config["tool"]["ruff"]["lint"]["select"] == ["E9", "F63", "F7", "F82"]
    assert "reports" in config["tool"]["ruff"]["extend-exclude"]
    assert config["tool"]["ruff"]["lint"]["per-file-ignores"] == {
        "wizard_pages/08_summary.py": ["F821"]
    }


def test_black_is_scoped_to_stable_helper_modules() -> None:
    config = _load_pyproject()
    include = config["tool"]["black"]["include"]

    assert "model_capabilities" in include
    assert "eures_mapping" in include
    assert "wizard_pages" not in include
    assert "summary_artifacts" not in include


def test_mypy_uses_permissive_selected_module_baseline() -> None:
    config = _load_pyproject()
    mypy = config["tool"]["mypy"]

    assert mypy["files"] == [
        "model_capabilities.py",
        "usage_utils.py",
        "summary_artifacts.py",
        "eures_mapping.py",
    ]
    assert mypy["ignore_missing_imports"] is True
    assert mypy["follow_imports"] == "silent"
    assert mypy["disallow_untyped_defs"] is False


def test_bandit_excludes_non_source_and_test_paths() -> None:
    config = _load_pyproject()
    excluded_dirs = set(config["tool"]["bandit"]["exclude_dirs"])

    assert {"tests", ".venv", "__pycache__", "data", "images", "reports"} <= (
        excluded_dirs
    )


def test_ci_contains_blocking_qa_and_advisory_security_jobs() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    assert "qa:" in workflow
    assert "python -m ruff check ." in workflow
    assert "python -m black --check ." in workflow
    assert "python -m mypy" in workflow
    assert "security:" in workflow
    assert "continue-on-error: true" in workflow
    assert "python -m bandit -c pyproject.toml -r ." in workflow
