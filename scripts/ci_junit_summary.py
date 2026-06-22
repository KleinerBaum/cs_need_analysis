"""Append compact JUnit aggregate counts to the GitHub Actions step summary."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import xml.etree.ElementTree as ET


def _int_attr(element: ET.Element, name: str) -> int:
    value = element.attrib.get(name, "0")
    try:
        return int(float(value))
    except ValueError:
        return 0


def _aggregate_counts(root: ET.Element) -> dict[str, int]:
    if root.tag == "testsuite":
        suites = [root]
    else:
        suites = list(root.findall("testsuite"))
        if not suites:
            suites = list(root.findall(".//testsuite"))

    counts = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for suite in suites:
        for key in counts:
            counts[key] += _int_attr(suite, key)
    return counts


def _summary_markdown(label: str, counts: dict[str, int]) -> str:
    passed = max(
        counts["tests"] - counts["failures"] - counts["errors"] - counts["skipped"],
        0,
    )
    return (
        f"### {label} test report\n\n"
        "| Layer | Tests | Passed | Failed | Errors | Skipped |\n"
        "| --- | ---: | ---: | ---: | ---: | ---: |\n"
        f"| {label} | {counts['tests']} | {passed} | {counts['failures']} | "
        f"{counts['errors']} | {counts['skipped']} |\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("junit_xml", help="Path to a pytest JUnit XML report.")
    parser.add_argument("label", help="Human-readable CI layer label.")
    args = parser.parse_args()

    report_path = Path(args.junit_xml)
    if not report_path.exists():
        message = f"JUnit report not found for {args.label}: {report_path}"
        print(message)
        return 0

    root = ET.parse(report_path).getroot()
    markdown = _summary_markdown(args.label, _aggregate_counts(root))
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_path:
        with Path(summary_path).open("a", encoding="utf-8") as handle:
            handle.write(markdown)
            handle.write("\n")
    else:
        print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
