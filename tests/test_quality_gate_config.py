from __future__ import annotations

import re
import tomllib
from pathlib import Path

from scripts import check_repo_hygiene


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
    assert "scripts/check_repo_hygiene" in include
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
        "scripts/check_repo_hygiene.py",
    ]
    assert mypy["ignore_missing_imports"] is True
    assert mypy["follow_imports"] == "silent"
    assert mypy["disallow_untyped_defs"] is False


def test_pyright_uses_staged_selected_module_baseline() -> None:
    config = _load_pyproject()
    pyright = config["tool"]["pyright"]

    assert pyright["include"] == [
        "model_capabilities.py",
        "usage_utils.py",
        "summary_artifacts.py",
        "eures_mapping.py",
        "scripts/check_repo_hygiene.py",
    ]
    assert pyright["pythonVersion"] == "3.11"
    assert pyright["typeCheckingMode"] == "basic"
    assert pyright["reportMissingImports"] == "none"
    assert "reports" in pyright["exclude"]


def test_bandit_excludes_non_source_and_test_paths() -> None:
    config = _load_pyproject()
    excluded_dirs = set(config["tool"]["bandit"]["exclude_dirs"])

    assert {"tests", ".venv", "__pycache__", "data", "images", "reports"} <= (
        excluded_dirs
    )


def test_runtime_requirements_exclude_dev_and_test_tools() -> None:
    runtime_names = _requirement_names("requirements.txt")

    assert "pytest" not in runtime_names
    assert {"ruff", "black", "mypy", "pyright", "bandit", "playwright"}.isdisjoint(
        runtime_names
    )


def test_dev_requirements_cover_configured_qa_and_test_tools() -> None:
    assert {
        "pytest",
        "ruff",
        "black",
        "mypy",
        "pyright",
        "bandit",
    } <= _requirement_names("requirements-dev.txt")


def test_e2e_requirements_cover_optional_browser_smoke_tests() -> None:
    assert "playwright" in _requirement_names("requirements-e2e.txt")


def test_pytest_registers_app_and_e2e_markers() -> None:
    pytest_ini = _read("pytest.ini")

    assert "apptest:" in pytest_ini
    assert "e2e:" in pytest_ini
    assert "CS_RUN_E2E=1" in pytest_ini


def test_ci_contains_blocking_qa_and_advisory_security_jobs() -> None:
    workflow = _read(".github/workflows/ci.yml")
    qa_job = workflow.split("  qa:", 1)[1].split("  contract:", 1)[0]

    assert "qa:" in workflow
    assert "python scripts/check_repo_hygiene.py" in qa_job
    assert "fetch-depth: 0" in qa_job
    assert "CS_I18N_RAW_UI_BASE_REF" in qa_job
    assert "github.event.pull_request.base.sha" in qa_job
    assert "github.event.before" in qa_job
    assert "python -m ruff check ." in workflow
    assert "python -m black --check ." in workflow
    assert "python -m mypy" in workflow
    assert "python -m pyright" in workflow
    assert "security:" in workflow
    assert "continue-on-error: true" in workflow
    assert "fetch-depth: 0" in workflow
    assert "gitleaks/gitleaks-action@v3" in workflow
    assert 'GITLEAKS_ENABLE_COMMENTS: "false"' in workflow
    assert 'GITLEAKS_ENABLE_UPLOAD_ARTIFACT: "false"' in workflow
    assert 'GITLEAKS_ENABLE_SUMMARY: "false"' in workflow
    assert "python -m bandit -c pyproject.toml -r ." in workflow
    assert "python scripts/check_tracked_artifacts.py" in workflow


def test_ci_wires_contract_unit_and_apptest_layers() -> None:
    workflow = _read(".github/workflows/ci.yml")
    contract_job = workflow.split("  contract:", 1)[1].split("  unit:", 1)[0]
    unit_job = workflow.split("  unit:", 1)[1].split("  apptest:", 1)[0]
    apptest_job = workflow.split("  apptest:", 1)[1].split("  browser_smoke:", 1)[0]

    for job in (contract_job, unit_job, apptest_job):
        assert "pip install -r requirements.txt -c constraints.txt" in job
        assert "pip install -r requirements-dev.txt -c constraints.txt" in job
        assert "actions/upload-artifact@v4" in job
        assert "retention-days: 14" in job

    assert "tests/test_repo_contract_drift.py" in contract_job
    assert "--junitxml=reports/junit/contract.xml" in contract_job
    assert "python -m pytest -q tests \\" in unit_job
    assert "--ignore=tests/e2e" in unit_job
    assert "--ignore=tests/apptest" in unit_job
    assert "--junitxml=reports/junit/unit.xml" in unit_job
    assert "python scripts/openai_smoke_test.py \\" in unit_job
    assert "--json-only > reports/openai-smoke.json" in unit_job
    assert "python -m pytest -q tests/apptest" in apptest_job
    assert "--junitxml=reports/junit/apptest.xml" in apptest_job


def test_gitignore_excludes_local_scan_and_generated_report_outputs() -> None:
    gitignore = _read(".gitignore")

    assert "reports/" in gitignore
    assert "gitleaks-report.*" in gitignore
    assert "artifact-scan-report.*" in gitignore
    assert "*:Zone.*" in gitignore
    assert ".env.*" in gitignore
    assert "!.env.example" in gitignore
    assert "*.pem" in gitignore
    assert "*.key" in gitignore
    assert "*credential*.json" in gitignore
    assert "*secret*.toml" in gitignore
    assert "*token*.txt" in gitignore
    assert "exports/" in gitignore
    assert "*.docx" in gitignore
    assert "*.pdf" in gitignore


def test_repo_hygiene_guard_flags_forbidden_paths_without_static_asset_noise() -> None:
    findings = check_repo_hygiene.find_hygiene_findings(
        [
            ".env",
            ".env.example",
            ".streamlit/secrets.toml",
            "app/__pycache__/module.cpython-311.pyc",
            "client_secret.json",
            "exports/vacancy_brief.docx",
            "images/base_logo_white_background.png",
            "data/salary_benchmarks/demo_de.csv",
            "reports/Key-Analyse-report.md",
            "reports/new-export.md",
            "service/private.pem",
        ]
    )

    by_path = {finding.path: finding.rule for finding in findings}

    assert by_path == {
        ".env": "secret-env-file",
        ".streamlit/secrets.toml": "secret-env-file",
        "app/__pycache__/module.cpython-311.pyc": "generated-python-cache",
        "client_secret.json": "secret-credential-file",
        "exports/vacancy_brief.docx": "generated-export-artifact",
        "reports/new-export.md": "generated-local-report",
        "service/private.pem": "secret-key-material",
    }


def test_repo_hygiene_guard_output_reports_only_paths_and_rules(
    capsys, monkeypatch
) -> None:
    monkeypatch.setattr(check_repo_hygiene, "_tracked_paths", lambda: [".env"])

    exit_code = check_repo_hygiene.main()
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "- .env [secret-env-file]" in output
    assert "OPENAI_API_KEY" not in output
    assert "sk-" not in output


def test_active_terminology_guard_flags_visible_residual_copy(monkeypatch) -> None:
    monkeypatch.setattr(
        check_repo_hygiene,
        "WIZARD_COPY_CONTRACT",
        {
            "de": {"landing": {"value_line": "Vorbereitete Recruiting-Outputs"}},
            "en": {},
        },
    )
    monkeypatch.setattr(check_repo_hygiene, "ACTIVE_TERMINOLOGY_SOURCE_PATHS", ())

    findings = check_repo_hygiene.find_active_terminology_findings()

    assert findings == [
        check_repo_hygiene.TerminologyFinding(
            location="inline_wizard_copy.de.landing.value_line",
            term="Recruiting-Outputs",
        )
    ]


def test_ci_wires_advisory_browser_smoke_job() -> None:
    workflow = _read(".github/workflows/ci.yml")
    browser_job = workflow.split("  browser_smoke:", 1)[1].split("  security:", 1)[0]

    assert "run_e2e:" in workflow
    assert "browser_smoke:" in workflow
    assert "github.event_name != 'workflow_dispatch' || inputs.run_e2e == true" in (
        browser_job
    )
    assert "continue-on-error: true" in browser_job
    assert "pip install -r requirements-e2e.txt -c constraints.txt" in browser_job
    assert "python -m playwright install --with-deps chromium" in browser_job
    assert 'CS_RUN_E2E: "1"' in browser_job
    assert (
        "python -m pytest -q tests/e2e --junitxml=reports/junit/browser-smoke.xml"
        in browser_job
    )
    assert "actions/upload-artifact@v4" in browser_job
    assert "ci-browser-smoke-junit" in browser_job


def test_ci_uses_compact_junit_summary_script() -> None:
    workflow = _read(".github/workflows/ci.yml")

    assert "python scripts/ci_junit_summary.py reports/junit/contract.xml" in workflow
    assert "python scripts/ci_junit_summary.py reports/junit/unit.xml" in workflow
    assert "python scripts/ci_junit_summary.py reports/junit/apptest.xml" in workflow
    assert (
        "python scripts/ci_junit_summary.py reports/junit/browser-smoke.xml"
        in workflow
    )
