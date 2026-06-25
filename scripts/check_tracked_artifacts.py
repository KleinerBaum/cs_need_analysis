"""Fail on unexpected tracked generated files or binary artifacts."""

from __future__ import annotations

import fnmatch
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

ALLOWED_BINARY_PATTERNS = (
    "images/*.gif",
    "images/*.jpeg",
    "images/*.jpg",
    "images/*.png",
)

KNOWN_TRACKED_REPORTS = {
    "reports/Aktualisierter Implementierungsreport f\u00fcr den dynamischen Intake-Wizard.md",
    "reports/Key-Analyse-report.md",
    "reports/README.md",
    "reports/deep-research-report_21_06_2026.md",
    "reports/deep-research-report_22_06_2026.md:Zone.md",
}

GENERATED_PATH_PARTS = (
    "/.mypy_cache/",
    "/.pytest_cache/",
    "/.ruff_cache/",
    "/.tox/",
    "/.nox/",
    "/__pycache__/",
    "/build/",
    "/cover/",
    "/dist/",
    "/htmlcov/",
    "/target/",
)

GENERATED_NAME_PATTERNS = (
    "*.bak",
    "*.cache",
    "*.cover",
    "*.db",
    "*.db-journal",
    "*.log",
    "*.py.cover",
    "*.pyc",
    "*.pyd",
    "*.pyo",
    "*.sqlite",
    "*.tmp",
    "*:Zone.*",
    ".coverage",
    ".coverage.*",
    "coverage.xml",
    "nosetests.xml",
)


@dataclass(frozen=True)
class Finding:
    path: str
    reason: str


def _tracked_paths() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
    )
    return [path.decode("utf-8") for path in result.stdout.split(b"\0") if path]


def _matches_any(path: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def _looks_binary(path: str) -> bool:
    sample = (ROOT / path).read_bytes()[:8192]
    if b"\0" in sample:
        return True
    if not sample:
        return False
    text_chars = bytes(range(32, 127)) + b"\b\f\n\r\t"
    non_text = sample.translate(None, text_chars)
    return len(non_text) / len(sample) > 0.30


def _finding_for(path: str) -> Finding | None:
    if path in KNOWN_TRACKED_REPORTS:
        return None

    normalized = f"/{path}"
    if any(part in normalized for part in GENERATED_PATH_PARTS):
        return Finding(path, "generated/cache path is tracked")

    if path.startswith("reports/"):
        return Finding(path, "generated report path is tracked")

    name = Path(path).name
    if _matches_any(name, GENERATED_NAME_PATTERNS):
        return Finding(path, "generated/cache file is tracked")

    if _looks_binary(path) and not _matches_any(path, ALLOWED_BINARY_PATTERNS):
        return Finding(path, "unexpected binary file is tracked")

    return None


def main() -> int:
    findings = [
        finding
        for path in _tracked_paths()
        if (finding := _finding_for(path)) is not None
    ]
    if not findings:
        print("Tracked artifact scan passed: no unexpected generated or binary files.")
        return 0

    print("Tracked artifact scan found unexpected tracked files:")
    for finding in findings:
        print(f"- {finding.path}: {finding.reason}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
