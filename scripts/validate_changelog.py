#!/usr/bin/env python3
"""Validate CHANGELOG.md for release readiness checks."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHANGELOG = ROOT / "CHANGELOG.md"
TITLE = "# Changelog"
VERSIONED_HEADING_RE = re.compile(
    r"^## (?P<version>v?[0-9]+(?:[._-][0-9A-Za-z]+){1,}"
    r"(?:\+[0-9A-Za-z.-]+)?) - (?P<date>\d{4}-\d{2}-\d{2})$"
)
DATE_ONLY_HEADING_RE = re.compile(r"^## (?P<date>\d{4}-\d{2}-\d{2})$")
BREAKING_CHANGE_RE = re.compile(r"^- \*\*Breaking Change:\*\*", re.IGNORECASE)


@dataclass(frozen=True)
class ChangelogSection:
    heading: str
    line_number: int
    version: str | None
    release_date: str
    legacy_date_only: bool
    body_lines: tuple[str, ...]


def _parse_iso_date(value: str, *, line_number: int | None = None) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        location = f" on line {line_number}" if line_number is not None else ""
        raise ValueError(f"Invalid release date{location}: {value!r}") from None


def _parse_heading(line: str, line_number: int) -> tuple[str | None, str, bool]:
    versioned_match = VERSIONED_HEADING_RE.fullmatch(line)
    if versioned_match is not None:
        release_date = versioned_match.group("date")
        _parse_iso_date(release_date, line_number=line_number)
        return versioned_match.group("version"), release_date, False

    date_only_match = DATE_ONLY_HEADING_RE.fullmatch(line)
    if date_only_match is not None:
        release_date = date_only_match.group("date")
        _parse_iso_date(release_date, line_number=line_number)
        return None, release_date, True

    raise ValueError(
        f"Invalid changelog section heading on line {line_number}: {line!r}. "
        "Use '## <version> - YYYY-MM-DD' for new releases or "
        "'## YYYY-MM-DD' for legacy date-only sections."
    )


def _extract_sections(lines: list[str]) -> tuple[list[ChangelogSection], list[str]]:
    errors: list[str] = []
    heading_positions: list[tuple[int, str]] = []

    for index, line in enumerate(lines, start=1):
        if line.startswith("## "):
            heading_positions.append((index, line))

    sections: list[ChangelogSection] = []
    for position, (line_number, heading) in enumerate(heading_positions):
        next_line_number = (
            heading_positions[position + 1][0]
            if position + 1 < len(heading_positions)
            else len(lines) + 1
        )
        body_lines = tuple(lines[line_number: next_line_number - 1])
        try:
            version, release_date, legacy_date_only = _parse_heading(
                heading,
                line_number,
            )
        except ValueError as exc:
            errors.append(str(exc))
            continue
        sections.append(
            ChangelogSection(
                heading=heading,
                line_number=line_number,
                version=version,
                release_date=release_date,
                legacy_date_only=legacy_date_only,
                body_lines=body_lines,
            )
        )

    return sections, errors


def _has_release_bullet(section: ChangelogSection) -> bool:
    return any(line.startswith("- ") for line in section.body_lines)


def _has_breaking_change_note(section: ChangelogSection) -> bool:
    return any(BREAKING_CHANGE_RE.match(line.strip()) for line in section.body_lines)


def _validate_section_order(sections: list[ChangelogSection]) -> list[str]:
    errors: list[str] = []
    previous_date: date | None = None
    previous_line_number: int | None = None

    for section in sections:
        release_date = _parse_iso_date(
            section.release_date,
            line_number=section.line_number,
        )
        if previous_date is not None and release_date > previous_date:
            errors.append(
                "Changelog sections must be sorted newest-to-oldest: "
                f"line {section.line_number} ({section.release_date}) is newer "
                f"than line {previous_line_number}."
            )
        previous_date = release_date
        previous_line_number = section.line_number

    return errors


def validate_changelog_text(
    text: str,
    *,
    expected_version: str | None = None,
    expected_date: str | None = None,
) -> list[str]:
    """Return validation errors for changelog text."""

    errors: list[str] = []
    lines = text.splitlines()
    if not lines:
        return ["CHANGELOG.md is empty."]
    if lines[0].strip() != TITLE:
        errors.append(f"CHANGELOG.md must start with {TITLE!r}.")

    if (expected_version is None) != (expected_date is None):
        errors.append("Use --version and --date together for release checks.")

    if expected_date is not None:
        try:
            _parse_iso_date(expected_date)
        except ValueError as exc:
            errors.append(str(exc))

    sections, section_errors = _extract_sections(lines)
    errors.extend(section_errors)

    if not sections:
        errors.append("CHANGELOG.md must contain at least one '##' release section.")
        return errors

    for section in sections:
        if not _has_release_bullet(section):
            errors.append(
                f"Changelog section on line {section.line_number} must contain "
                "at least one '- ' release-note bullet."
            )

    errors.extend(_validate_section_order(sections))

    duplicate_versions = {
        section.version
        for section in sections
        if section.version is not None
        and sum(candidate.version == section.version for candidate in sections) > 1
    }
    duplicate_dates = {
        section.release_date
        for section in sections
        if sum(candidate.release_date == section.release_date for candidate in sections)
        > 1
    }
    for version in sorted(duplicate_versions):
        errors.append(f"Duplicate changelog release version: {version}.")
    for release_date in sorted(duplicate_dates):
        errors.append(f"Duplicate changelog release date: {release_date}.")

    target_section = sections[0]
    if expected_version is not None and expected_date is not None:
        matching_sections = [
            section
            for section in sections
            if section.version == expected_version
            and section.release_date == expected_date
            and not section.legacy_date_only
        ]
        if not matching_sections:
            errors.append(
                "Missing expected changelog section: "
                f"## {expected_version} - {expected_date}"
            )
            return errors
        target_section = matching_sections[0]

    if not _has_breaking_change_note(target_section):
        errors.append(
            f"Changelog section on line {target_section.line_number} must include "
            "'- **Breaking Change:** ...'."
        )

    return errors


def validate_changelog(
    path: Path,
    *,
    expected_version: str | None = None,
    expected_date: str | None = None,
) -> list[str]:
    return validate_changelog_text(
        path.read_text(encoding="utf-8"),
        expected_version=expected_version,
        expected_date=expected_date,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate changelog structure before a manual release.",
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=DEFAULT_CHANGELOG,
        help="Path to CHANGELOG.md. Defaults to the repository changelog.",
    )
    parser.add_argument(
        "--version",
        help="Expected release version label, for example 2026.07.01 or v0.5.0.",
    )
    parser.add_argument(
        "--date",
        help="Expected release date in YYYY-MM-DD format.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    errors = validate_changelog(
        args.path,
        expected_version=args.version,
        expected_date=args.date,
    )

    if errors:
        print("CHANGELOG validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"CHANGELOG validation passed: {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
