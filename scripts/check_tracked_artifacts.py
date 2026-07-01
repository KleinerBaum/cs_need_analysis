"""Fail on unexpected tracked generated files or binary artifacts."""

from __future__ import annotations

import fnmatch
# Dev-only fixed Git metadata command, shell=False.
import subprocess  # nosec B404
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


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
    "iceberg_need_analysis_visual_patch.diff",
    "latest_deep-research-report.md",
    "nosetests.xml",
)


@dataclass(frozen=True)
class Finding:
    path: str
    reason: str


class GitPrerequisiteError(RuntimeError):
    """Raised when artifact checks cannot run because Git metadata is missing."""


NO_GIT_CHECKOUT_MESSAGE = (
    "Git checkout required: run from a cloned repository with a .git directory; "
    "ZIP/source exports do not include the metadata needed for tracked-file and "
    "changed-line checks."
)
NO_GIT_EXECUTABLE_MESSAGE = (
    "Git executable not found: install Git before running repository hygiene checks."
)


def _is_no_git_checkout_error(stderr: str) -> bool:
    return "not a git repository" in stderr.lower()


def _run_git_command(
    args: Sequence[str],
    *,
    allowed_returncodes: frozenset[int] = frozenset({0}),
) -> subprocess.CompletedProcess[str]:
    try:
        # Args are repo-defined Git commands; no user input and shell=False.
        result = subprocess.run(  # nosec B603
            list(args),
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError as exc:
        raise GitPrerequisiteError(NO_GIT_EXECUTABLE_MESSAGE) from exc

    if result.returncode in allowed_returncodes:
        return result
    if result.returncode == 128 and _is_no_git_checkout_error(result.stderr):
        raise GitPrerequisiteError(NO_GIT_CHECKOUT_MESSAGE)
    raise subprocess.CalledProcessError(
        result.returncode,
        list(args),
        output=result.stdout,
        stderr=result.stderr,
    )


def _tracked_paths() -> list[str]:
    result = _run_git_command(["git", "ls-files", "-z"])
    return [path for path in result.stdout.split("\0") if path]


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
    if not (ROOT / path).exists():
        return None

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
    try:
        findings = [
            finding
            for path in _tracked_paths()
            if (finding := _finding_for(path)) is not None
        ]
    except GitPrerequisiteError as exc:
        print(f"Tracked artifact scan prerequisite failed: {exc}")
        return 2

    if not findings:
        print("Tracked artifact scan passed: no unexpected generated or binary files.")
        return 0

    print("Tracked artifact scan found unexpected tracked files:")
    for finding in findings:
        print(f"- {finding.path}: {finding.reason}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
