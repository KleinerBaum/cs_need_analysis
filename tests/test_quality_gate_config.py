from __future__ import annotations

import re
import subprocess
import tomllib
from pathlib import Path

import pytest

from scripts import check_repo_hygiene, check_tracked_artifacts

ROOT = Path(__file__).resolve().parents[1]


def _load_pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _requirement_names(path: str) -> set[str]:
    names: set[str] = set()
    for line in _read(path).splitlines():
        stripped = line.strip().lower()
        if not stripped or stripped.startswith("#") or stripped.startswith("-"):
            continue
        match = re.match(r"[a-z0-9_.-]+", stripped)
        if match is not None:
            names.add(match.group(0))
    return names


def _normalized_names(names: set[str]) -> set[str]:
    return {name.replace("_", "-") for name in names}


def test_ruff_starts_with_staged_critical_rules() -> None:
    config = _load_pyproject()

    assert config["tool"]["ruff"]["lint"]["select"] == [
        "E9",
        "F63",
        "F7",
        "F82",
        "F541",
    ]
    assert "reports" in config["tool"]["ruff"]["extend-exclude"]
    assert config["tool"]["ruff"]["lint"]["per-file-ignores"] == {
        "wizard_pages/08_summary.py": ["F821"]
    }


def test_black_uses_staged_module_allowlist() -> None:
    config = _load_pyproject()
    include = config["tool"]["black"]["include"]

    assert "app" in include
    assert "state" in include
    assert "state_store" in include
    assert "llm_error_mapping" in include
    assert "model_capabilities" in include
    assert "eures_mapping" in include
    assert "scripts/check_repo_hygiene" in include
    assert "wizard_pages" not in include
    assert "ui_widget_state" not in include
    assert "ux_copy_contract" not in include


def test_mypy_uses_permissive_selected_module_baseline() -> None:
    config = _load_pyproject()
    mypy = config["tool"]["mypy"]

    assert mypy["files"] == [
        "app.py",
        "state.py",
        "state_store.py",
        "llm_error_mapping.py",
        "model_capabilities.py",
        "usage_utils.py",
        "summary_artifacts.py",
        "eures_mapping.py",
        "esco_matrix.py",
        "esco_offline_index.py",
        "esco_rag.py",
        "salary/benchmarks.py",
        "salary/engine.py",
        "salary/features_esco.py",
        "salary/mapping.py",
        "salary/scenario_lab_builders.py",
        "salary/scenarios.py",
        "salary/types.py",
        "ui_widget_state.py",
        "ux_copy_contract.py",
        "scripts/check_repo_hygiene.py",
    ]
    assert "llm_client.py" not in mypy["files"]
    assert mypy["ignore_missing_imports"] is True
    assert mypy["follow_imports"] == "silent"
    assert mypy["disallow_untyped_defs"] is False


def test_pyright_uses_staged_selected_module_baseline() -> None:
    config = _load_pyproject()
    pyright = config["tool"]["pyright"]

    assert pyright["include"] == [
        "app.py",
        "state.py",
        "state_store.py",
        "llm_error_mapping.py",
        "model_capabilities.py",
        "usage_utils.py",
        "summary_artifacts.py",
        "eures_mapping.py",
        "esco_matrix.py",
        "esco_offline_index.py",
        "esco_rag.py",
        "salary/benchmarks.py",
        "salary/engine.py",
        "salary/features_esco.py",
        "salary/mapping.py",
        "salary/scenario_lab_builders.py",
        "salary/scenarios.py",
        "salary/types.py",
        "ui_widget_state.py",
        "ux_copy_contract.py",
        "scripts/check_repo_hygiene.py",
    ]
    assert "llm_client.py" not in pyright["include"]
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
    assert "defusedxml" in runtime_names


def test_dev_requirements_cover_configured_qa_and_test_tools() -> None:
    assert {
        "pytest",
        "ruff",
        "black",
        "mypy",
        "pyright",
        "bandit",
        "pip-audit",
        "pytest-cov",
    } <= _requirement_names("requirements-dev.txt")


def test_e2e_requirements_cover_optional_browser_smoke_tests() -> None:
    assert "playwright" in _requirement_names("requirements-e2e.txt")


def test_requirement_inputs_include_dependency_lock() -> None:
    for path in ("requirements.txt", "requirements-dev.txt", "requirements-e2e.txt"):
        active_lines = [
            line.strip()
            for line in _read(path).splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]

        assert active_lines[0] == "-c constraints.txt"


def test_constraints_fully_pin_dependency_lock() -> None:
    direct_names = set()
    for path in ("requirements.txt", "requirements-dev.txt", "requirements-e2e.txt"):
        direct_names.update(_requirement_names(path))

    constraint_names: set[str] = set()
    pin_count = 0
    for line in _read("constraints.txt").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        pin_count += 1
        assert re.fullmatch(r"[A-Za-z0-9_.-]+==[^<>=!~\s]+", stripped)
        constraint_names.add(stripped.split("==", 1)[0].lower())

    assert pin_count > 50
    assert _normalized_names(direct_names) <= _normalized_names(constraint_names)
    assert {"httpx", "pdfminer.six", "playwright", "pytest", "streamlit"} <= (
        _normalized_names(constraint_names)
    )


def test_pytest_registers_app_and_e2e_markers() -> None:
    pytest_ini = _read("pytest.ini")

    assert "apptest:" in pytest_ini
    assert "e2e:" in pytest_ini
    assert "CS_RUN_E2E=1" in pytest_ini
    assert "CS_RUN_DEPLOYED_SMOKE=1" in pytest_ini


def test_ci_contains_blocking_qa_and_security_jobs() -> None:
    workflow = _read(".github/workflows/ci.yml")
    qa_job = workflow.split("  qa:", 1)[1].split("  contract:", 1)[0]
    security_job = workflow.split("  security:", 1)[1]

    assert "permissions:\n  contents: read" in workflow
    assert 'CS_ALERT_P95_LATENCY_MS: "8000"' in workflow
    assert 'CS_ALERT_AVG_COST_USD: "0.01"' in workflow
    assert 'CS_ALERT_FAILURE_RATE: "0.03"' in workflow
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
    gitleaks_step = security_job.split("      - name: Gitleaks secret scan", 1)[
        1
    ].split("      - name: Dependency review blocking scan", 1)[0]
    dependency_review_step = security_job.split(
        "      - name: Dependency review blocking scan",
        1,
    )[1].split("      - name: Set up Python", 1)[0]
    bandit_step = security_job.split(
        "      - name: Bandit blocking high and medium scan",
        1,
    )[1].split("      - name: pip-audit dependency vulnerability scan", 1)[0]
    pip_audit_step = security_job.split(
        "      - name: pip-audit dependency vulnerability scan",
        1,
    )[1].split("      - name: Tracked artifact drift scan", 1)[0]
    artifact_drift_step = security_job.split(
        "      - name: Tracked artifact drift scan",
        1,
    )[1]
    assert "continue-on-error: true" not in gitleaks_step
    assert "continue-on-error: true" not in dependency_review_step
    assert "continue-on-error: true" not in bandit_step
    assert "continue-on-error: true" not in pip_audit_step
    assert "continue-on-error: true" not in artifact_drift_step
    assert "fetch-depth: 0" in workflow
    assert "gitleaks/gitleaks-action@v3" in workflow
    assert 'GITLEAKS_ENABLE_COMMENTS: "false"' in workflow
    assert 'GITLEAKS_ENABLE_UPLOAD_ARTIFACT: "false"' in workflow
    assert 'GITLEAKS_ENABLE_SUMMARY: "false"' in workflow
    assert "actions/dependency-review-action@v4" in workflow
    assert "fail-on-severity: high" in dependency_review_step
    assert (
        "python -m bandit -c pyproject.toml -r . --severity-level medium "
        "--confidence-level medium"
    ) in workflow
    assert "pip install -r requirements-e2e.txt -c constraints.txt" in security_job
    assert "python -m pip_audit --local --strict --progress-spinner off" in workflow
    assert "python scripts/check_tracked_artifacts.py" in workflow


def test_ci_wires_contract_unit_and_apptest_layers() -> None:
    workflow = _read(".github/workflows/ci.yml")
    apptest_smoke = _read("tests/apptest/test_streamlit_app_smoke.py")
    readme = _read("README.md")
    contract_job = workflow.split("  contract:", 1)[1].split("  unit:", 1)[0]
    unit_job = workflow.split("  unit:", 1)[1].split("  apptest:", 1)[0]
    apptest_job = workflow.split("  apptest:", 1)[1].split(
        "  deployment_observability:",
        1,
    )[0]

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
    assert "--cov=." in unit_job
    assert "--cov-report=xml:reports/coverage/unit-coverage.xml" in unit_job
    assert "--cov-fail-under=35" in unit_job
    assert "--junitxml=reports/junit/unit.xml" in unit_job
    assert "python scripts/openai_smoke_test.py \\" in unit_job
    assert "--json-only > reports/openai-smoke.json" in unit_job
    assert "python scripts/ci_observability_report.py \\" in unit_job
    assert "reports/observability/deployment-events.jsonl" in unit_job
    assert "reports/coverage/unit-coverage.xml" in unit_job
    assert "python -m pytest -q tests/apptest" in apptest_job
    assert "--junitxml=reports/junit/apptest.xml" in apptest_job
    assert "seed_summary_artifact_smoke_state" in apptest_smoke
    assert "SYNTHETIC_JOB_TITLE" in apptest_smoke
    assert (
        "seeded Summary entry without OpenAI or external website calls" in readme
    )


def test_ci_has_oidc_ready_deployment_observability_job() -> None:
    workflow = _read(".github/workflows/ci.yml")
    deploy_job = workflow.split("  deployment_observability:", 1)[1].split(
        "  browser_smoke:",
        1,
    )[0]

    assert "id-token: write" in deploy_job
    assert "actions/download-artifact@v4" in deploy_job
    assert "ci-unit-reports" in deploy_job
    assert "deployment-events.jsonl" in deploy_job
    assert '"event_type":"deployment_event"' in deploy_job


def test_dependabot_covers_python_and_github_actions() -> None:
    dependabot = _read(".github/dependabot.yml")
    readme = _read("README.md")

    assert "version: 2" in dependabot
    assert 'package-ecosystem: "pip"' in dependabot
    assert 'package-ecosystem: "github-actions"' in dependabot
    assert 'timezone: "Europe/Berlin"' in dependabot
    assert "python-runtime:" in dependabot
    assert "github-actions:" in dependabot
    assert "pip-compile --upgrade-package PACKAGE_NAME" in readme
    assert "Dependabot monitors" in readme


def test_ci_security_gdpr_runbook_covers_manual_platform_controls() -> None:
    runbook = _read("docs/ci_security_gdpr.md")

    assert "Secret Scanning" in runbook
    assert "Push Protection" in runbook
    assert "OIDC" in runbook
    assert ".streamlit/secrets.toml" in runbook
    assert "store=false" in runbook


def test_gitignore_excludes_local_scan_and_generated_report_outputs() -> None:
    gitignore = _read(".gitignore")

    assert "reports/*" in gitignore
    assert "!reports/README.md" in gitignore
    generated_artifact_patterns = {
        "reports/coverage/",
        "reports/evals/",
        "reports/from-ci/",
        "reports/junit/",
        "reports/observability/",
        "reports/openai-smoke*.json",
        "reports/visual-regression/",
        "gitleaks-report.*",
        "artifact-scan-report.*",
        "coverage.json",
        "lcov.info",
        "openai-smoke*.json",
        "latest_deep-research-report.md",
        "iceberg_need_analysis_visual_patch.diff",
        "*.diff",
        "*.patch",
        "playwright-report/",
        "screenshots/",
        "test-results/",
        "*screenshot*.png",
        "*visual-regression*.png",
    }
    for pattern in generated_artifact_patterns:
        assert pattern in gitignore
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


def test_readme_uses_non_secret_shaped_openai_key_examples() -> None:
    readme = _read("README.md")
    openai_key_prefix = "s" + "k-"

    assert f"{openai_key_prefix}..." not in readme
    assert f'export OPENAI_API_KEY="{openai_key_prefix}' not in readme
    assert "your-local-openai-api-key" not in readme


def test_i18n_inventory_does_not_render_placeholder_markdown_links() -> None:
    i18n_key_list = _read("docs/i18n_key_list.md")

    assert "]({...})" not in i18n_key_list


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
            "reports/openai-smoke.json",
            "reports/coverage/unit-coverage.xml",
            "reports/visual-regression/landing.png",
            ".coverage",
            "cover/index.html",
            "coverage.json",
            "lcov.info",
            "openai-smoke.json",
            "visual_patch.diff",
            "review.patch",
            "homepage-screenshot.png",
            "latest_deep-research-report.md",
            "iceberg_need_analysis_visual_patch.diff",
            "service/private.pem",
        ],
        require_existing=False,
    )

    by_path = {finding.path: finding.rule for finding in findings}

    assert by_path == {
        ".env": "secret-env-file",
        ".streamlit/secrets.toml": "secret-env-file",
        "app/__pycache__/module.cpython-311.pyc": "generated-python-cache",
        "client_secret.json": "secret-credential-file",
        "exports/vacancy_brief.docx": "generated-export-artifact",
        ".coverage": "generated-local-artifact",
        "cover/index.html": "generated-local-artifact",
        "coverage.json": "generated-local-artifact",
        "homepage-screenshot.png": "generated-local-artifact",
        "iceberg_need_analysis_visual_patch.diff": "generated-local-artifact",
        "latest_deep-research-report.md": "generated-local-artifact",
        "lcov.info": "generated-local-artifact",
        "openai-smoke.json": "generated-local-artifact",
        "reports/coverage/unit-coverage.xml": "generated-local-artifact",
        "reports/new-export.md": "generated-local-artifact",
        "reports/openai-smoke.json": "generated-local-artifact",
        "reports/visual-regression/landing.png": "generated-local-artifact",
        "review.patch": "generated-local-artifact",
        "service/private.pem": "secret-key-material",
        "visual_patch.diff": "generated-local-artifact",
    }


def test_artifact_guards_ignore_paths_deleted_in_worktree() -> None:
    missing_path = "missing-generated-local-report.pyc"

    assert check_repo_hygiene.finding_for_path(missing_path) is None
    assert check_tracked_artifacts._finding_for(missing_path) is None


def test_artifact_guards_share_git_prerequisite_messages() -> None:
    assert (
        check_repo_hygiene.NO_GIT_CHECKOUT_MESSAGE
        == check_tracked_artifacts.NO_GIT_CHECKOUT_MESSAGE
    )
    assert (
        check_repo_hygiene.NO_GIT_EXECUTABLE_MESSAGE
        == check_tracked_artifacts.NO_GIT_EXECUTABLE_MESSAGE
    )


def test_tracked_artifact_scan_allows_report_archive_index() -> None:
    assert "reports/README.md" in check_tracked_artifacts.KNOWN_TRACKED_REPORTS
    assert "reports/README.md" in check_repo_hygiene.ALLOWED_TRACKED_REPORTS
    assert "reports/README.md" in _read("README.md")

    assert (
        check_repo_hygiene.finding_for_path(
            "reports/README.md",
            require_existing=False,
        )
        is None
    )
    assert check_tracked_artifacts._finding_for("reports/README.md") is None


def test_tracked_artifact_scan_allows_intentional_static_theme_images() -> None:
    assert (
        check_tracked_artifacts._finding_for("static/theme-background-light.png")
        is None
    )
    assert (
        check_tracked_artifacts._finding_for("static/theme-background-dark.png")
        is None
    )


def test_tracked_artifact_scan_reports_common_generated_local_artifacts(
    monkeypatch, tmp_path
) -> None:
    forbidden_paths = [
        "artifact-scan-report.json",
        "gitleaks-report.json",
        "coverage.xml",
        "coverage.json",
        ".coverage",
        "cover/index.html",
        "lcov.info",
        "openai-smoke.json",
        "reports/openai-smoke.json",
        "reports/coverage/unit-coverage.xml",
        "reports/junit/unit.xml",
        "reports/evals/summary.json",
        "reports/observability/deployment-events.jsonl",
        "reports/visual-regression/landing.png",
        "fix.patch",
        "visual_patch.diff",
        "homepage-screenshot.png",
        "playwright-report/index.html",
        "screenshots/landing.png",
        "test-results/browser/error-context.md",
    ]
    for path in forbidden_paths:
        artifact_path = tmp_path / path
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text("generated artifact", encoding="utf-8")

    monkeypatch.setattr(check_tracked_artifacts, "ROOT", tmp_path)

    findings = {
        path: check_tracked_artifacts._finding_for(path) for path in forbidden_paths
    }

    assert all(finding is not None for finding in findings.values())
    assert findings["reports/openai-smoke.json"] == check_tracked_artifacts.Finding(
        "reports/openai-smoke.json",
        "generated/local artifact is tracked",
    )
    assert findings["visual_patch.diff"] == check_tracked_artifacts.Finding(
        "visual_patch.diff",
        "generated/local artifact is tracked",
    )


def test_tracked_artifact_scan_reports_findings_in_git_checkout(
    capsys, monkeypatch, tmp_path
) -> None:
    tracked_artifact = "build/generated.pyc"
    artifact_path = tmp_path / tracked_artifact
    artifact_path.parent.mkdir()
    artifact_path.write_bytes(b"compiled-cache")

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args[0], 0, f"{tracked_artifact}\0", "")

    monkeypatch.setattr(check_tracked_artifacts, "ROOT", tmp_path)
    monkeypatch.setattr(check_tracked_artifacts.subprocess, "run", fake_run)

    exit_code = check_tracked_artifacts.main()
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "Tracked artifact scan found unexpected tracked files:" in output
    assert f"- {tracked_artifact}: generated/cache path is tracked" in output


def test_tracked_artifact_scan_reports_no_git_checkout_prerequisite(
    capsys, monkeypatch
) -> None:
    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args[0],
            128,
            "",
            "fatal: not a git repository (or any of the parent directories): .git",
        )

    monkeypatch.setattr(check_tracked_artifacts.subprocess, "run", fake_run)

    exit_code = check_tracked_artifacts.main()
    output = capsys.readouterr().out

    assert exit_code == 2
    assert output == (
        "Tracked artifact scan prerequisite failed: "
        f"{check_tracked_artifacts.NO_GIT_CHECKOUT_MESSAGE}\n"
    )


def test_repo_hygiene_guard_output_reports_only_paths_and_rules(
    capsys, monkeypatch
) -> None:
    monkeypatch.setattr(check_repo_hygiene, "_tracked_paths", lambda: [".env"])
    monkeypatch.setattr(check_repo_hygiene, "_tracked_path_exists", lambda _path: True)

    exit_code = check_repo_hygiene.main()
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "- .env [secret-env-file]" in output
    assert "OPENAI_API_KEY" not in output
    assert "sk-" not in output


def test_repo_hygiene_guard_reports_no_git_checkout_prerequisite(
    capsys, monkeypatch
) -> None:
    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args[0],
            128,
            "",
            "fatal: not a git repository (or any of the parent directories): .git",
        )

    monkeypatch.setattr(check_repo_hygiene.subprocess, "run", fake_run)

    exit_code = check_repo_hygiene.main()
    output = capsys.readouterr().out

    assert exit_code == 2
    assert output == (
        "Repository hygiene guard prerequisite failed: "
        f"{check_repo_hygiene.NO_GIT_CHECKOUT_MESSAGE}\n"
    )


def test_git_command_helper_preserves_unrelated_git_failures(monkeypatch) -> None:
    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args[0], 129, "", "fatal: bad revision")

    monkeypatch.setattr(check_repo_hygiene.subprocess, "run", fake_run)

    with pytest.raises(subprocess.CalledProcessError):
        check_repo_hygiene._run_git_command(["git", "diff", "missing-ref"])


def test_raw_ui_changed_line_guard_tracks_active_wizard_hotspots() -> None:
    guarded_paths = check_repo_hygiene.ACTIVE_WIZARD_RAW_UI_PATHS

    assert {
        "wizard_pages/00_landing.py",
        "wizard_pages/02_company.py",
        "wizard_pages/04_role_tasks.py",
        "wizard_pages/05_skills.py",
        "wizard_pages/06_benefits.py",
        "wizard_pages/07_interview.py",
        "wizard_pages/08_summary.py",
        "wizard_pages/jobad_intake.py",
        "wizard_pages/salary_forecast.py",
        "wizard_pages/summary_artifact_preview.py",
        "wizard_pages/summary_exporters.py",
        "wizard_pages/summary_release_gate_ui.py",
        "wizard_pages/team_section.py",
        "wizard_pages/trust_grammar.py",
    } <= guarded_paths
    assert "wizard_pages/01a_jobspec_review.py" not in guarded_paths
    assert "wizard_pages/03_team.py" not in guarded_paths


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
    local_smoke_test = _read("tests/e2e/test_streamlit_wizard_smoke.py")

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
    assert "Set CS_RUN_E2E=1" in local_smoke_test
    assert "Missing Streamlit dependency" in local_smoke_test
    assert "Missing Playwright dependency" in local_smoke_test
    assert "Chromium browser is not installed" in local_smoke_test


def test_ci_wires_visual_regression_and_deployed_smoke_jobs() -> None:
    workflow = _read(".github/workflows/ci.yml")
    visual_job = workflow.split("  visual_regression:", 1)[1].split(
        "  deployed_smoke:",
        1,
    )[0]
    deployed_job = workflow.split("  deployed_smoke:", 1)[1].split("  security:", 1)[0]
    removed_base_url_env_names = (
        "CS_REQUIRE_DEPLOYED_" + "BASE_" + "URL",
        "CS_DEPLOYED_" + "BASE_" + "URL",
    )

    assert "run_visual_regression:" in workflow
    assert "visual_regression:" in workflow
    assert "continue-on-error: true" in visual_job
    assert 'CS_E2E_CAPTURE_SCREENSHOTS: "1"' in visual_job
    assert "tests/e2e/test_streamlit_wizard_smoke.py" in visual_job
    assert "reports/visual-regression/*.png" in visual_job
    assert "ci-visual-regression-artifacts" in visual_job

    assert "deployed_smoke:" in workflow
    assert "continue-on-error: true" not in deployed_job
    assert 'CS_RUN_DEPLOYED_SMOKE: "1"' in deployed_job
    for env_name in removed_base_url_env_names:
        assert env_name not in deployed_job
    assert "tests/e2e/test_deployed_smoke.py" in deployed_job
    assert "--junitxml=reports/junit/deployed-smoke.xml" in deployed_job
    assert "ci-deployed-smoke-junit" in deployed_job

    deployed_smoke_test = _read("tests/e2e/test_deployed_smoke.py")
    assert (
        'CANONICAL_PUBLIC_URL = "https://recruitment-need-analysis.streamlit.app/"'
        in deployed_smoke_test
    )
    assert "Set CS_RUN_DEPLOYED_SMOKE=1" in deployed_smoke_test
    assert "Missing Playwright dependency" in deployed_smoke_test
    assert "Chromium browser is not installed" in deployed_smoke_test
    for env_name in removed_base_url_env_names:
        assert env_name not in deployed_smoke_test


def test_ci_uses_compact_junit_summary_script() -> None:
    workflow = _read(".github/workflows/ci.yml")

    assert "python scripts/ci_junit_summary.py reports/junit/contract.xml" in workflow
    assert "python scripts/ci_junit_summary.py reports/junit/unit.xml" in workflow
    assert "python scripts/ci_junit_summary.py reports/junit/apptest.xml" in workflow
    assert (
        "python scripts/ci_junit_summary.py reports/junit/browser-smoke.xml" in workflow
    )
    assert (
        "python scripts/ci_junit_summary.py reports/junit/visual-regression.xml"
        in workflow
    )
    assert (
        "python scripts/ci_junit_summary.py reports/junit/deployed-smoke.xml"
        in workflow
    )


def test_codeql_workflow_scans_python_with_security_quality_queries() -> None:
    workflow = _read(".github/workflows/codeql.yml")

    assert "name: CodeQL" in workflow
    assert "pull_request:" in workflow
    assert "schedule:" in workflow
    assert "security-events: write" in workflow
    assert "github/codeql-action/init@v4" in workflow
    assert "github/codeql-action/analyze@v4" in workflow
    assert "languages: python" in workflow
    assert "queries: security-and-quality" in workflow


def test_quality_gate_baseline_documents_deferred_expansions() -> None:
    baseline = _read("docs/quality_gate_baseline.md")
    readme = _read("README.md")

    assert "Ruff" in baseline
    assert "F541" in baseline
    assert "Black reports formatting changes" in baseline
    assert "llm_client.py" in baseline
    assert "state.py" in baseline
    assert "Bandit is blocking for Medium/High" in baseline
    assert "high-or-critical vulnerable dependencies" in baseline
    assert "pip-audit" in baseline
    assert "CodeQL" in baseline
    assert "flaky outside the deterministic AppTest layer" in baseline
    assert "https://recruitment-need-analysis.streamlit.app/" in baseline
    assert "CS_RUN_DEPLOYED_SMOKE" in baseline
    assert "Dependency Review high/critical" in readme
    assert "strict pip-audit" in readme
    assert "tracked-artifact drift" in readme
    assert "flaky outside the deterministic AppTest layer" in readme
