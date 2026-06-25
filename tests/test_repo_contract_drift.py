from __future__ import annotations

import ast
import re
from pathlib import Path

import constants as app_constants
from constants import (
    OPERATIONAL_WIZARD_STEP_KEYS,
    PRE_WIZARD_STEP_KEYS,
    SUMMARY_ACTIVE_ARTIFACT_IDS,
    SUMMARY_ARTIFACT_IDS,
    STEPS,
    STEP_KEY_JOBSPEC_REVIEW,
    STEP_KEY_TEAM,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DOCS = (ROOT / "README.md", ROOT / "AGENTS.md")
REPORTS_README = ROOT / "reports" / "README.md"
QA_SUPPORT_FILES = (
    "pyproject.toml",
    "pytest.ini",
    "requirements-dev.txt",
    "requirements-e2e.txt",
)
LEGACY_MODULES = (
    "wizard_pages/01a_jobspec_review.py",
    "wizard_pages/03_team.py",
)
EXPECTED_CI_JOB_IDS = [
    "qa",
    "contract",
    "unit",
    "apptest",
    "deployment_observability",
    "browser_smoke",
    "visual_regression",
    "deployed_smoke",
    "security",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _documented_wizard_rows(path: Path) -> list[tuple[int, str, str, str]]:
    rows: list[tuple[int, str, str, str]] = []
    for line in _read(path).splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 4 or not cells[0].isdigit():
            continue
        key_match = re.fullmatch(r"`([^`]+)`", cells[1])
        module_match = re.search(r"`(wizard_pages/[^`]+\.py)`", cells[3])
        if key_match is None or module_match is None:
            continue
        rows.append(
            (
                int(cells[0]),
                key_match.group(1),
                cells[2],
                module_match.group(1),
            )
        )
    return rows


def _resolve_string_expr(expr: ast.expr, *, source_path: Path) -> str:
    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        return expr.value
    if isinstance(expr, ast.Name):
        value = getattr(app_constants, expr.id, None)
        if isinstance(value, str):
            return value
    raise AssertionError(
        f"Could not statically resolve string expression in {source_path}: "
        f"{ast.dump(expr)}"
    )


def _wizard_page_key(path: Path) -> str | None:
    tree = ast.parse(_read(path), filename=str(path))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        is_page_assignment = any(
            isinstance(target, ast.Name) and target.id == "PAGE"
            for target in node.targets
        )
        if not is_page_assignment:
            continue
        if not isinstance(node.value, ast.Call):
            continue
        for keyword in node.value.keywords:
            if keyword.arg == "key":
                return _resolve_string_expr(keyword.value, source_path=path)
    return None


def _ci_job_ids() -> list[str]:
    job_ids: list[str] = []
    in_jobs = False
    for line in _read(ROOT / ".github" / "workflows" / "ci.yml").splitlines():
        if line == "jobs:":
            in_jobs = True
            continue
        if in_jobs and line and not line.startswith(" "):
            break
        if not in_jobs:
            continue
        match = re.fullmatch(r"  ([A-Za-z0-9_-]+):", line)
        if match is not None:
            job_ids.append(match.group(1))
    return job_ids


def test_documented_wizard_tables_match_canonical_steps() -> None:
    operational_steps = [
        step for step in STEPS if step.key in set(OPERATIONAL_WIZARD_STEP_KEYS)
    ]
    expected_rows = [
        (order, step.key, step.title_de)
        for order, step in enumerate(operational_steps, start=1)
    ]

    for doc_path in CONTRACT_DOCS:
        documented_rows = _documented_wizard_rows(doc_path)
        assert [
            (order, key, title_de)
            for order, key, title_de, _module_path in documented_rows
        ] == expected_rows
        text = _read(doc_path)
        for step_key in PRE_WIZARD_STEP_KEYS:
            assert f"`{step_key}`" in text


def test_documented_active_page_modules_exist_and_match_step_keys() -> None:
    for doc_path in CONTRACT_DOCS:
        for _order, key, _title_de, module_path in _documented_wizard_rows(doc_path):
            page_path = ROOT / module_path
            assert page_path.exists(), f"{doc_path.name} documents missing {module_path}"
            assert _wizard_page_key(page_path) == key


def test_documented_legacy_modules_stay_non_routable() -> None:
    active_step_keys = {step.key for step in STEPS}

    assert STEP_KEY_JOBSPEC_REVIEW not in active_step_keys
    assert STEP_KEY_TEAM not in active_step_keys

    for module_path in LEGACY_MODULES:
        path = ROOT / module_path
        assert path.exists()
        page_key = _wizard_page_key(path)
        assert page_key is None or page_key not in active_step_keys

    for doc_path in CONTRACT_DOCS:
        text = _read(doc_path)
        documented_active_modules = {
            module_path
            for _order, _key, _title_de, module_path in _documented_wizard_rows(
                doc_path
            )
        }
        assert not set(LEGACY_MODULES) & documented_active_modules
        assert "legacy/non-routable" in text.lower()
        for module_path in LEGACY_MODULES:
            assert f"`{module_path}`" in text


def test_reports_archive_index_marks_reports_historical() -> None:
    assert REPORTS_README.exists()
    text = _read(REPORTS_README).lower()

    assert "historical archive" in text
    assert re.search(r"not\s+the\s+current\s+runtime\s+contract", text)
    assert "source-of-truth" in text
    assert "docs/legacy_wizard_modules.md" in text

    for doc_path in CONTRACT_DOCS:
        assert "`reports/README.md`" in _read(doc_path)


def test_documented_summary_artifacts_match_active_contract() -> None:
    assert "employment_contract" in SUMMARY_ARTIFACT_IDS
    assert "employment_contract" not in SUMMARY_ACTIVE_ARTIFACT_IDS

    for doc_path in CONTRACT_DOCS:
        text = _read(doc_path)
        assert "`constants.SUMMARY_ACTIVE_ARTIFACT_IDS`" in text
        assert "`constants.SUMMARY_ARTIFACT_IDS`" in text

        for artifact_id in SUMMARY_ACTIVE_ARTIFACT_IDS:
            assert f"`{artifact_id}`" in text

        assert "`employment_contract`" in text
        assert re.search(
            r"`employment_contract`[^\n]*(archived|hidden|compatibility|compatibility-only)",
            text,
            re.IGNORECASE,
        ), f"{doc_path.name} must document employment_contract as inactive legacy"


def test_docs_reference_current_quality_gate_support_files() -> None:
    for file_name in QA_SUPPORT_FILES:
        assert (ROOT / file_name).exists()

    for doc_path in CONTRACT_DOCS:
        text = _read(doc_path)
        for file_name in QA_SUPPORT_FILES:
            assert f"`{file_name}`" in text


def test_ci_job_ids_match_documented_repo_contract() -> None:
    assert _ci_job_ids() == EXPECTED_CI_JOB_IDS

    for doc_path in CONTRACT_DOCS:
        text = _read(doc_path)
        for job_id in EXPECTED_CI_JOB_IDS:
            assert f"`{job_id}`" in text
