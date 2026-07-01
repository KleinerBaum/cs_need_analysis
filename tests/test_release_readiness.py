from __future__ import annotations

from pathlib import Path

from scripts import validate_changelog


ROOT = Path(__file__).resolve().parents[1]


def test_current_changelog_passes_release_readiness_validation() -> None:
    errors = validate_changelog.validate_changelog(ROOT / "CHANGELOG.md")

    assert errors == []


def test_changelog_validator_requires_expected_version_and_date() -> None:
    changelog = """# Changelog

## 2026.07.01 - 2026-07-01

- Added release readiness validation.
- **Breaking Change:** none.

## 2026-05-05

- Legacy date-only section.
"""

    errors = validate_changelog.validate_changelog_text(
        changelog,
        expected_version="2026.07.01",
        expected_date="2026-07-01",
    )
    missing_errors = validate_changelog.validate_changelog_text(
        changelog,
        expected_version="2026.08.01",
        expected_date="2026-08-01",
    )

    assert errors == []
    assert "Missing expected changelog section: ## 2026.08.01 - 2026-08-01" in (
        missing_errors
    )


def test_release_readiness_workflow_is_manual_only_and_runs_core_gates() -> None:
    workflow = (ROOT / ".github/workflows/release-readiness.yml").read_text(
        encoding="utf-8"
    )

    assert "workflow_dispatch:" in workflow
    assert "pull_request:" not in workflow
    assert "push:" not in workflow
    assert "python scripts/validate_changelog.py \\" in workflow
    assert "python scripts/check_repo_hygiene.py" in workflow
    assert "python -m compileall" in workflow
    assert "tests/test_repo_contract_drift.py" in workflow
    assert "python -m pytest -q tests \\" in workflow
    assert "--ignore=tests/e2e" in workflow
    assert "--ignore=tests/apptest" in workflow
    assert "python scripts/openai_smoke_test.py \\" in workflow
    assert "python scripts/run_quality_evals.py \\" in workflow
