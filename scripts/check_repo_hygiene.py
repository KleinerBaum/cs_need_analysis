"""Blocking guard for committed secret-like files and local artifacts.

The guard is intentionally path-only: it does not read file contents, so CI
output can report file paths and rule names without exposing matched values.
"""

from __future__ import annotations

import fnmatch
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]

ALLOWED_TRACKED_REPORTS = {
    "reports/Aktualisierter Implementierungsreport f\u00fcr den dynamischen Intake-Wizard.md",
    "reports/Key-Analyse-report.md",
    "reports/deep-research-report_21_06_2026.md",
    "reports/deep-research-report_22_06_2026.md:Zone.md",
}

ALLOWED_EXAMPLE_SECRET_PATTERNS = (
    ".env.example",
    ".env.sample",
    "*/.env.example",
    "*/.env.sample",
)

FORBIDDEN_PATH_RULES = (
    (
        "secret-env-file",
        (
            ".env",
            ".env.*",
            "*/.env",
            "*/.env.*",
            ".streamlit/secrets.toml",
            "*/.streamlit/secrets.toml",
        ),
    ),
    (
        "secret-key-material",
        (
            "*.key",
            "*.keystore",
            "*.p12",
            "*.pfx",
            "*.pem",
            "id_ed25519",
            "id_rsa",
            "*/id_ed25519",
            "*/id_rsa",
        ),
    ),
    (
        "secret-credential-file",
        (
            "*credential*.json",
            "*credential*.toml",
            "*credential*.txt",
            "*credential*.yaml",
            "*credential*.yml",
            "*secret*.json",
            "*secret*.toml",
            "*secret*.txt",
            "*secret*.yaml",
            "*secret*.yml",
            "*token*.json",
            "*token*.toml",
            "*token*.txt",
            "*token*.yaml",
            "*token*.yml",
            "service-account*.json",
        ),
    ),
    (
        "generated-python-cache",
        (
            "*.pyc",
            "*.pyd",
            "*.pyo",
            "__pycache__/*",
            "*/__pycache__/*",
        ),
    ),
    (
        "generated-tool-cache",
        (
            ".mypy_cache/*",
            ".pytest_cache/*",
            ".ruff_cache/*",
            ".tox/*",
            "*/.mypy_cache/*",
            "*/.pytest_cache/*",
            "*/.ruff_cache/*",
            "*/.tox/*",
        ),
    ),
    (
        "generated-os-metadata",
        (
            "*:Zone.*",
            ".DS_Store",
            "*/.DS_Store",
            "Thumbs.db",
            "*/Thumbs.db",
        ),
    ),
    (
        "generated-local-report",
        (
            "artifact-scan-report.*",
            "gitleaks-report.*",
            "reports/*",
        ),
    ),
    (
        "generated-export-artifact",
        (
            "*.docx",
            "*.pdf",
            "*.pptx",
            "*.xlsx",
            "*.zip",
            "export/*",
            "exports/*",
            "generated_exports/*",
            "local_exports/*",
            "*/export/*",
            "*/exports/*",
            "*/generated_exports/*",
            "*/local_exports/*",
        ),
    ),
)


@dataclass(frozen=True)
class Finding:
    path: str
    rule: str


def _tracked_paths() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
    )
    return [path.decode("utf-8") for path in result.stdout.split(b"\0") if path]


def _normalize_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _matches_any(path: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def finding_for_path(path: str) -> Finding | None:
    normalized = _normalize_path(path)
    if normalized in ALLOWED_TRACKED_REPORTS:
        return None
    if _matches_any(normalized, ALLOWED_EXAMPLE_SECRET_PATTERNS):
        return None

    for rule, patterns in FORBIDDEN_PATH_RULES:
        if _matches_any(normalized, patterns):
            return Finding(path=normalized, rule=rule)
    return None


def find_hygiene_findings(paths: Iterable[str]) -> list[Finding]:
    findings = [
        finding
        for path in paths
        if (finding := finding_for_path(path)) is not None
    ]
    return sorted(findings, key=lambda finding: (finding.rule, finding.path))


def main() -> int:
    findings = find_hygiene_findings(_tracked_paths())
    if not findings:
        print("Repository hygiene guard passed: no forbidden tracked paths.")
        return 0

    print("Repository hygiene guard found forbidden tracked paths:")
    for finding in findings:
        print(f"- {finding.path} [{finding.rule}]")
    return 1


if __name__ == "__main__":
    sys.exit(main())
