from __future__ import annotations

import re
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _requirement_names(path: str) -> set[str]:
    names: set[str] = set()
    for line in _read(path).splitlines():
        stripped = line.strip().lower()
        if not stripped or stripped.startswith("#"):
            continue
        match = re.match(r"[a-z0-9_.-]+", stripped)
        if match is not None:
            names.add(match.group(0))
    return names


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


def test_dev_requirements_cover_configured_qa_tools() -> None:
    assert {"ruff", "black", "mypy", "bandit"} <= _requirement_names(
        "requirements-dev.txt"
    )


def test_e2e_requirements_cover_optional_browser_smoke_tests() -> None:
    assert "playwright" in _requirement_names("requirements-e2e.txt")


def test_pytest_registers_optional_e2e_marker() -> None:
    pytest_ini = _read("pytest.ini")

    assert "e2e:" in pytest_ini
    assert "CS_RUN_E2E=1" in pytest_ini


def test_ci_contains_blocking_qa_and_advisory_security_jobs() -> None:
    workflow = _read(".github/workflows/ci.yml")

    assert "qa:" in workflow
    assert "python -m ruff check ." in workflow
    assert "python -m black --check ." in workflow
    assert "python -m mypy" in workflow
    assert "security:" in workflow
    assert "continue-on-error: true" in workflow
    assert "python -m bandit -c pyproject.toml -r ." in workflow


def test_ci_wires_optional_e2e_smoke_job() -> None:
    workflow = _read(".github/workflows/ci.yml")

    assert "run_e2e:" in workflow
    assert "inputs.run_e2e == true" in workflow
    assert "e2e:" in workflow
    assert "pip install -r requirements-e2e.txt -c constraints.txt" in workflow
    assert "python -m playwright install --with-deps chromium" in workflow
    assert 'CS_RUN_E2E: "1"' in workflow
    assert "python -m pytest -q tests/e2e" in workflow
