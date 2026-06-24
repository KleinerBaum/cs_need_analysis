"""Blocking guard for repository hygiene and i18n copy-contract drift.

The forbidden-path guard is intentionally path-only: it does not read file
contents, so CI output can report file paths and rule names without exposing
matched values.
"""

from __future__ import annotations

import ast
import fnmatch
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from constants import (  # noqa: E402
    STEP_KEY_BENEFITS,
    STEP_KEY_COMPANY,
    STEP_KEY_INTERVIEW,
    STEP_KEY_LANDING,
    STEP_KEY_ROLE_TASKS,
    STEP_KEY_SKILLS,
    STEP_KEY_SUMMARY,
    SUMMARY_ACTIVE_ARTIFACT_IDS,
)
from ux_copy_contract import (  # noqa: E402
    ARTIFACT_LABELS,
    ESCO_UI_COPY,
    SALARY_UI_COPY,
    SUMMARY_EXPORT_COPY,
    SUMMARY_PREVIEW_COPY,
    SUMMARY_UI_COPY,
    TRUST_GRAMMAR_COPY,
    _COPY as WIZARD_COPY_CONTRACT,
)

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

COPY_LANGUAGES = ("de", "en")
WIZARD_COPY_STEPS = (
    STEP_KEY_LANDING,
    STEP_KEY_COMPANY,
    STEP_KEY_ROLE_TASKS,
    STEP_KEY_SKILLS,
    STEP_KEY_BENEFITS,
    STEP_KEY_INTERVIEW,
    STEP_KEY_SUMMARY,
)
STANDARD_COPY_FIELDS = (
    "headline",
    "subheadline",
    "value_line",
    "primary_cta",
    "secondary_cta",
)
LOCALE_COPY_FIELDS = (
    *STANDARD_COPY_FIELDS,
    "empty_state",
    "readiness",
)
LANDING_EXTRA_FIELDS = (
    "headline_after_analysis",
    "subheadline_after_analysis",
    "value_line_after_analysis",
)
SUMMARY_VARIANT_FIELDS = ("headline", "subheadline", "readiness")
SUMMARY_VARIANTS = ("default", "gap", "ready")
INLINE_SUMMARY_COPY_FIELDS = (
    "headline_default",
    "headline_gap",
    "headline_ready",
    "subheadline_default",
    "subheadline_gap",
    "subheadline_ready",
    "value_line",
    "primary_cta",
    "secondary_cta",
)
ACTIVE_COPY_CONTRACTS: Mapping[str, Mapping[str, object]] = {
    "artifact_labels": ARTIFACT_LABELS,
    "summary_ui": SUMMARY_UI_COPY,
    "summary_export": SUMMARY_EXPORT_COPY,
    "summary_preview": SUMMARY_PREVIEW_COPY,
    "esco_ui": ESCO_UI_COPY,
    "trust_grammar": TRUST_GRAMMAR_COPY,
    "salary_ui": SALARY_UI_COPY,
}

ACTIVE_WIZARD_RAW_UI_PATHS = frozenset(
    {
        "wizard_pages/00_landing.py",
        "wizard_pages/02_company.py",
        "wizard_pages/04_role_tasks.py",
        "wizard_pages/05_skills.py",
        "wizard_pages/06_benefits.py",
        "wizard_pages/07_interview.py",
        "wizard_pages/08_summary.py",
        "wizard_pages/jobad_intake.py",
        "wizard_pages/salary_forecast_panel.py",
        "wizard_pages/summary_artifact_actions.py",
        "wizard_pages/summary_readiness.py",
        "wizard_pages/summary_view.py",
    }
)

RAW_UI_ALLOW_COMMENT = "i18n: allow-raw-ui"
RAW_UI_BASE_REF_ENV = "CS_I18N_RAW_UI_BASE_REF"
RAW_UI_METHODS = frozenset(
    {
        "button",
        "caption",
        "checkbox",
        "download_button",
        "error",
        "expander",
        "file_uploader",
        "header",
        "info",
        "markdown",
        "metric",
        "multiselect",
        "number_input",
        "radio",
        "selectbox",
        "slider",
        "subheader",
        "success",
        "tabs",
        "text_area",
        "text_input",
        "title",
        "toast",
        "toggle",
        "warning",
        "write",
    }
)
RAW_UI_TEXT_KEYWORDS = frozenset({"help", "label", "placeholder"})
RAW_UI_OPTION_METHODS = frozenset({"multiselect", "radio", "selectbox", "tabs"})
PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")
DOC_BACKLOG_ROW_RE = re.compile(
    r"^\|\s*P\d+\s*\|\s*`[^`]+`\s*\|\s*`(?P<location>[^`]+)`\s*\|"
    r"\s*(?P<copy>.*?)\s*\|\s*$"
)
DIFF_FILE_RE = re.compile(r"^\+\+\+ b/(?P<path>.+)$")
DIFF_HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(?P<start>\d+)(?:,(?P<count>\d+))? @@")
MACHINE_TOKEN_RE = re.compile(r"^[a-z0-9_.:/%-]+$")
USER_COPY_RE = re.compile(r"[A-Za-zÄÖÜäöüß]")


@dataclass(frozen=True)
class Finding:
    path: str
    rule: str


@dataclass(frozen=True)
class ContractFinding:
    rule: str
    detail: str


@dataclass(frozen=True)
class RawUiStringFinding:
    path: str
    line: int
    method: str
    text: str
    rule: str = "i18n-raw-ui-string"


@dataclass(frozen=True)
class TerminologyFinding:
    location: str
    term: str
    rule: str = "active-terminology-drift"


ACTIVE_TERMINOLOGY_SOURCE_PATHS = (
    "wizard_pages/02_company.py",
    "wizard_pages/04_role_tasks.py",
    "wizard_pages/05_skills.py",
    "wizard_pages/08_summary.py",
    "wizard_pages/summary_view.py",
    "ui_feedback.py",
)
ACTIVE_SOURCE_FORBIDDEN_TERMS = (
    "Boolean Search",
    "Boolean Searchstrings",
    "Artefakt",
    "Artefakte",
    "Artefaktgenerierung",
    "Vacancy Intake",
    "Need Analysis",
    "Vakanzerfassung",
    "Recruiting-Outputs",
)
GERMAN_ACTIVE_COPY_FORBIDDEN_TERMS = (
    *ACTIVE_SOURCE_FORBIDDEN_TERMS,
    "Review",
    "Outputs",
)


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
        finding for path in paths if (finding := finding_for_path(path)) is not None
    ]
    return sorted(findings, key=lambda finding: (finding.rule, finding.path))


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _locale_leaf_values(
    payload: Mapping[str, object], prefix: str = ""
) -> dict[str, object]:
    values: dict[str, object] = {}
    for key, value in payload.items():
        dotted_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, Mapping):
            values.update(_locale_leaf_values(value, dotted_key))
        else:
            values[dotted_key] = value
    return values


def _placeholder_names(value: object) -> set[str]:
    if not isinstance(value, str):
        return set()
    return set(PLACEHOLDER_RE.findall(value))


def _format_set(values: Iterable[str], *, limit: int = 12) -> str:
    sorted_values = sorted(values)
    rendered = ", ".join(sorted_values[:limit])
    if len(sorted_values) > limit:
        rendered = f"{rendered}, +{len(sorted_values) - limit} more"
    return rendered or "-"


def _require_mapping(
    payload: object,
    *,
    rule: str,
    detail: str,
    findings: list[ContractFinding],
) -> Mapping[str, object] | None:
    if isinstance(payload, Mapping):
        return payload
    findings.append(ContractFinding(rule=rule, detail=detail))
    return None


def _check_locale_ux_copy_contract(
    locale: Mapping[str, object],
    *,
    language: str,
) -> list[ContractFinding]:
    findings: list[ContractFinding] = []
    steps = _require_mapping(
        locale.get("ux_copy", {}),
        rule="i18n-locale-copy-contract",
        detail=f"{language}: missing ux_copy object",
        findings=findings,
    )
    if steps is None:
        return findings
    steps = _require_mapping(
        steps.get("steps"),
        rule="i18n-locale-copy-contract",
        detail=f"{language}: missing ux_copy.steps object",
        findings=findings,
    )
    if steps is None:
        return findings

    missing_steps = set(WIZARD_COPY_STEPS) - set(steps)
    if missing_steps:
        findings.append(
            ContractFinding(
                rule="i18n-locale-copy-contract",
                detail=f"{language}: missing ux_copy steps: {_format_set(missing_steps)}",
            )
        )

    for step_key in WIZARD_COPY_STEPS:
        step_payload = _require_mapping(
            steps.get(step_key),
            rule="i18n-locale-copy-contract",
            detail=f"{language}: ux_copy.steps.{step_key} must be an object",
            findings=findings,
        )
        if step_payload is None:
            continue

        required_fields: set[str] = set(LOCALE_COPY_FIELDS)
        if step_key == STEP_KEY_LANDING:
            required_fields.update(LANDING_EXTRA_FIELDS)

        missing_fields = required_fields - set(step_payload)
        if missing_fields:
            findings.append(
                ContractFinding(
                    rule="i18n-locale-copy-contract",
                    detail=(
                        f"{language}: ux_copy.steps.{step_key} missing fields: "
                        f"{_format_set(missing_fields)}"
                    ),
                )
            )

        if step_key == STEP_KEY_SUMMARY:
            for field in SUMMARY_VARIANT_FIELDS:
                variants = _require_mapping(
                    step_payload.get(field),
                    rule="i18n-locale-copy-contract",
                    detail=f"{language}: ux_copy.steps.summary.{field} must be an object",
                    findings=findings,
                )
                if variants is None:
                    continue
                missing_variants = set(SUMMARY_VARIANTS) - set(variants)
                if missing_variants:
                    findings.append(
                        ContractFinding(
                            rule="i18n-locale-copy-contract",
                            detail=(
                                f"{language}: ux_copy.steps.summary.{field} missing "
                                f"variants: {_format_set(missing_variants)}"
                            ),
                        )
                    )
        else:
            for field in required_fields:
                if field in step_payload and not isinstance(step_payload[field], str):
                    findings.append(
                        ContractFinding(
                            rule="i18n-locale-copy-contract",
                            detail=(
                                f"{language}: ux_copy.steps.{step_key}.{field} "
                                "must be a string"
                            ),
                        )
                    )

    return findings


def _check_inline_copy_contract() -> list[ContractFinding]:
    findings: list[ContractFinding] = []
    missing_languages = set(COPY_LANGUAGES) - set(WIZARD_COPY_CONTRACT)
    if missing_languages:
        findings.append(
            ContractFinding(
                rule="i18n-inline-copy-contract",
                detail=f"missing inline copy languages: {_format_set(missing_languages)}",
            )
        )

    for language in COPY_LANGUAGES:
        copy_steps = WIZARD_COPY_CONTRACT.get(language)
        if not isinstance(copy_steps, Mapping):
            continue
        missing_steps = set(WIZARD_COPY_STEPS) - set(copy_steps)
        if missing_steps:
            findings.append(
                ContractFinding(
                    rule="i18n-inline-copy-contract",
                    detail=f"{language}: missing inline copy steps: {_format_set(missing_steps)}",
                )
            )

        for step_key in WIZARD_COPY_STEPS:
            step_payload = copy_steps.get(step_key)
            if not isinstance(step_payload, Mapping):
                findings.append(
                    ContractFinding(
                        rule="i18n-inline-copy-contract",
                        detail=f"{language}: inline copy step {step_key} must be an object",
                    )
                )
                continue
            required = (
                INLINE_SUMMARY_COPY_FIELDS
                if step_key == STEP_KEY_SUMMARY
                else STANDARD_COPY_FIELDS
            )
            if step_key == STEP_KEY_LANDING:
                required = (*required, *LANDING_EXTRA_FIELDS)
            missing_fields = set(required) - set(step_payload)
            if missing_fields:
                findings.append(
                    ContractFinding(
                        rule="i18n-inline-copy-contract",
                        detail=(
                            f"{language}: inline copy step {step_key} missing fields: "
                            f"{_format_set(missing_fields)}"
                        ),
                    )
                )

    de_steps = WIZARD_COPY_CONTRACT.get("de", {})
    en_steps = WIZARD_COPY_CONTRACT.get("en", {})
    if isinstance(de_steps, Mapping) and isinstance(en_steps, Mapping):
        for step_key in WIZARD_COPY_STEPS:
            de_keys = set(de_steps.get(step_key, {}))
            en_keys = set(en_steps.get(step_key, {}))
            if de_keys != en_keys:
                findings.append(
                    ContractFinding(
                        rule="i18n-inline-copy-contract",
                        detail=(
                            f"{step_key}: DE/EN inline copy shape mismatch "
                            f"(de-only: {_format_set(de_keys - en_keys)}; "
                            f"en-only: {_format_set(en_keys - de_keys)})"
                        ),
                    )
                )

    return findings


def _check_active_copy_contract_shapes() -> list[ContractFinding]:
    findings: list[ContractFinding] = []
    for contract_name, payload in ACTIVE_COPY_CONTRACTS.items():
        missing_languages = set(COPY_LANGUAGES) - set(payload)
        if missing_languages:
            findings.append(
                ContractFinding(
                    rule="i18n-active-copy-contract",
                    detail=(
                        f"{contract_name}: missing languages "
                        f"{_format_set(missing_languages)}"
                    ),
                )
            )
            continue

        language_leaf_values: dict[str, dict[str, object]] = {}
        for language in COPY_LANGUAGES:
            language_payload = payload.get(language, {})
            if not isinstance(language_payload, Mapping):
                findings.append(
                    ContractFinding(
                        rule="i18n-active-copy-contract",
                        detail=f"{contract_name}.{language}: must be an object",
                    )
                )
                continue
            language_leaf_values[language] = _locale_leaf_values(language_payload)

        de_leaf_values = language_leaf_values.get("de", {})
        en_leaf_values = language_leaf_values.get("en", {})
        de_keys = set(de_leaf_values)
        en_keys = set(en_leaf_values)
        if de_keys != en_keys:
            findings.append(
                ContractFinding(
                    rule="i18n-active-copy-contract",
                    detail=(
                        f"{contract_name}: DE/EN shape mismatch "
                        f"(de-only: {_format_set(de_keys - en_keys)}; "
                        f"en-only: {_format_set(en_keys - de_keys)})"
                    ),
                )
            )

        for key in sorted(de_keys & en_keys):
            de_placeholders = _placeholder_names(de_leaf_values[key])
            en_placeholders = _placeholder_names(en_leaf_values[key])
            if de_placeholders != en_placeholders:
                findings.append(
                    ContractFinding(
                        rule="i18n-active-copy-placeholders",
                        detail=(
                            f"{contract_name}.{key}: placeholder mismatch "
                            f"(de: {_format_set(de_placeholders)}; "
                            f"en: {_format_set(en_placeholders)})"
                        ),
                    )
                )

    return findings


def _check_active_artifact_label_contract() -> list[ContractFinding]:
    findings: list[ContractFinding] = []
    active_ids = set(SUMMARY_ACTIVE_ARTIFACT_IDS)
    for language in COPY_LANGUAGES:
        labels = ARTIFACT_LABELS.get(language, {})
        if not isinstance(labels, Mapping):
            findings.append(
                ContractFinding(
                    rule="i18n-active-artifact-labels",
                    detail=f"{language}: artifact labels must be an object",
                )
            )
            continue
        label_ids = set(labels)
        if label_ids != active_ids:
            findings.append(
                ContractFinding(
                    rule="i18n-active-artifact-labels",
                    detail=(
                        f"{language}: active artifact labels mismatch "
                        f"(missing: {_format_set(active_ids - label_ids)}; "
                        f"extra: {_format_set(label_ids - active_ids)})"
                    ),
                )
            )
        if "employment_contract" in label_ids:
            findings.append(
                ContractFinding(
                    rule="i18n-active-artifact-labels",
                    detail=f"{language}: archived employment_contract label is active",
                )
            )
    return findings


def _iter_string_leaf_values(
    value: object, prefix: str = ""
) -> Iterable[tuple[str, str]]:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            nested_prefix = f"{prefix}.{key}" if prefix else str(key)
            yield from _iter_string_leaf_values(nested_value, nested_prefix)
    elif isinstance(value, str):
        yield prefix, value


def _terminology_findings_for_text(
    *,
    location: str,
    text: str,
    forbidden_terms: Iterable[str],
) -> list[TerminologyFinding]:
    matched_terms = [term for term in forbidden_terms if term in text]
    specific_terms = [
        term
        for term in matched_terms
        if not any(term != other and term in other for other in matched_terms)
    ]
    return [TerminologyFinding(location=location, term=term) for term in specific_terms]


def find_active_terminology_findings() -> list[TerminologyFinding]:
    findings: list[TerminologyFinding] = []

    active_de_copy: dict[str, object] = {
        "inline_wizard_copy.de": WIZARD_COPY_CONTRACT.get("de", {}),
        "artifact_labels.de": ARTIFACT_LABELS.get("de", {}),
        "summary_ui.de": SUMMARY_UI_COPY.get("de", {}),
        "summary_export.de": SUMMARY_EXPORT_COPY.get("de", {}),
        "summary_preview.de": SUMMARY_PREVIEW_COPY.get("de", {}),
    }
    for contract_name, payload in active_de_copy.items():
        for dotted_key, text in _iter_string_leaf_values(payload, contract_name):
            findings.extend(
                _terminology_findings_for_text(
                    location=dotted_key,
                    text=text,
                    forbidden_terms=GERMAN_ACTIVE_COPY_FORBIDDEN_TERMS,
                )
            )

    active_en_copy: dict[str, object] = {
        "artifact_labels.en": ARTIFACT_LABELS.get("en", {}),
        "summary_ui.en": SUMMARY_UI_COPY.get("en", {}),
        "summary_export.en": SUMMARY_EXPORT_COPY.get("en", {}),
        "summary_preview.en": SUMMARY_PREVIEW_COPY.get("en", {}),
    }
    for contract_name, payload in active_en_copy.items():
        for dotted_key, text in _iter_string_leaf_values(payload, contract_name):
            findings.extend(
                _terminology_findings_for_text(
                    location=dotted_key,
                    text=text,
                    forbidden_terms=("Boolean search", "Boolean Search"),
                )
            )

    for path in ACTIVE_TERMINOLOGY_SOURCE_PATHS:
        absolute_path = ROOT / path
        if not absolute_path.exists():
            continue
        source = absolute_path.read_text(encoding="utf-8")
        for line_number, line in enumerate(source.splitlines(), start=1):
            findings.extend(
                _terminology_findings_for_text(
                    location=f"{path}:{line_number}",
                    text=line,
                    forbidden_terms=ACTIVE_SOURCE_FORBIDDEN_TERMS,
                )
            )
            if "nach Review" in line or "Review-" in line:
                findings.append(
                    TerminologyFinding(location=f"{path}:{line_number}", term="Review")
                )

    return sorted(
        findings, key=lambda finding: (finding.location, finding.term, finding.rule)
    )


def find_i18n_contract_findings() -> list[ContractFinding]:
    locales_dir = ROOT / "locales"
    de_locale = _load_json(locales_dir / "de.json")
    en_locale = _load_json(locales_dir / "en.json")
    findings: list[ContractFinding] = []

    if not isinstance(de_locale, Mapping) or not isinstance(en_locale, Mapping):
        return [
            ContractFinding(
                rule="i18n-locale-key-shape",
                detail="locale files must contain JSON objects",
            )
        ]

    de_leaf_values = _locale_leaf_values(de_locale)
    en_leaf_values = _locale_leaf_values(en_locale)
    de_keys = set(de_leaf_values)
    en_keys = set(en_leaf_values)
    if de_keys != en_keys:
        findings.append(
            ContractFinding(
                rule="i18n-locale-key-shape",
                detail=(
                    f"locale key mismatch (de-only: {_format_set(de_keys - en_keys)}; "
                    f"en-only: {_format_set(en_keys - de_keys)})"
                ),
            )
        )

    for key in sorted(de_keys & en_keys):
        de_placeholders = _placeholder_names(de_leaf_values[key])
        en_placeholders = _placeholder_names(en_leaf_values[key])
        if de_placeholders != en_placeholders:
            findings.append(
                ContractFinding(
                    rule="i18n-locale-placeholders",
                    detail=(
                        f"{key}: placeholder mismatch "
                        f"(de: {_format_set(de_placeholders)}; "
                        f"en: {_format_set(en_placeholders)})"
                    ),
                )
            )

    findings.extend(_check_locale_ux_copy_contract(de_locale, language="de"))
    findings.extend(_check_locale_ux_copy_contract(en_locale, language="en"))
    findings.extend(_check_inline_copy_contract())
    findings.extend(_check_active_copy_contract_shapes())
    findings.extend(_check_active_artifact_label_contract())
    return sorted(findings, key=lambda finding: (finding.rule, finding.detail))


def _normalize_ui_text(value: str) -> str:
    return " ".join(value.split()).strip()


def _expr_ui_text(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return _normalize_ui_text(node.value)
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            else:
                parts.append("{...}")
        return _normalize_ui_text("".join(parts))
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "format"
    ):
        base_text = _expr_ui_text(node.func.value)
        if base_text:
            return re.sub(r"\{[^{}]*\}", "{...}", base_text)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _expr_ui_text(node.left)
        right = _expr_ui_text(node.right)
        if left and right:
            return _normalize_ui_text(f"{left}{right}")
        if left:
            return _normalize_ui_text(f"{left}{{...}}")
        if right:
            return _normalize_ui_text(f"{{...}}{right}")
    return None


def _is_user_copy_candidate(text: str, *, option_value: bool = False) -> bool:
    if not text or text in {"---", "----"}:
        return False
    if text.startswith(("http://", "https://", "mailto:")):
        return False
    if option_value and MACHINE_TOKEN_RE.fullmatch(text):
        return False
    if text.startswith("<") or "</" in text:
        return False

    semantic_text = text.replace("{...}", "")
    semantic_text = re.sub(r"[#*_`\[\](){}:;,.!?\-/+·|%0-9\s€$]", "", semantic_text)
    return bool(USER_COPY_RE.search(semantic_text))


def _has_allow_comment(source_lines: list[str], line_number: int) -> bool:
    for index in (line_number - 1, line_number - 2):
        if index < 0 or index >= len(source_lines):
            continue
        line = source_lines[index]
        if RAW_UI_ALLOW_COMMENT not in line:
            continue
        reason = line.split(RAW_UI_ALLOW_COMMENT, 1)[1].strip(" #:;-")
        return bool(reason)
    return False


def _iter_ui_string_nodes(
    call: ast.Call, method: str
) -> Iterable[tuple[ast.AST, bool]]:
    if call.args:
        first_arg = call.args[0]
        if method == "tabs" and isinstance(first_arg, (ast.List, ast.Tuple)):
            for element in first_arg.elts:
                yield element, True
        else:
            yield first_arg, False

    for keyword in call.keywords:
        if keyword.arg in RAW_UI_TEXT_KEYWORDS:
            yield keyword.value, False
        if (
            keyword.arg == "options"
            and method in RAW_UI_OPTION_METHODS
            and isinstance(keyword.value, (ast.List, ast.Tuple))
        ):
            for element in keyword.value.elts:
                yield element, True


class _RawUiStringVisitor(ast.NodeVisitor):
    def __init__(self, path: str, source_lines: list[str]) -> None:
        self.path = path
        self.source_lines = source_lines
        self.findings: list[RawUiStringFinding] = []

    def visit_Call(self, node: ast.Call) -> None:
        function = node.func
        if isinstance(function, ast.Attribute) and function.attr in RAW_UI_METHODS:
            method = function.attr
            for value_node, option_value in _iter_ui_string_nodes(node, method):
                text = _expr_ui_text(value_node)
                if text and _is_user_copy_candidate(text, option_value=option_value):
                    self.findings.append(
                        RawUiStringFinding(
                            path=self.path,
                            line=getattr(value_node, "lineno", node.lineno),
                            method=method,
                            text=text,
                        )
                    )
        self.generic_visit(node)


def _scan_raw_ui_strings(path: Path) -> list[RawUiStringFinding]:
    normalized_path = _normalize_path(str(path.relative_to(ROOT)))
    source = path.read_text(encoding="utf-8")
    source_lines = source.splitlines()
    tree = ast.parse(source, filename=str(path))
    visitor = _RawUiStringVisitor(normalized_path, source_lines)
    visitor.visit(tree)
    return visitor.findings


def find_raw_ui_string_findings_in_source(
    path: str,
    source: str,
    *,
    changed_lines: set[int] | None = None,
    documented_allowlist: set[tuple[str, str]] | None = None,
) -> list[RawUiStringFinding]:
    source_lines = source.splitlines()
    visitor = _RawUiStringVisitor(_normalize_path(path), source_lines)
    visitor.visit(ast.parse(source))
    allowlist = documented_allowlist or set()

    findings: list[RawUiStringFinding] = []
    for finding in visitor.findings:
        if changed_lines is not None and finding.line not in changed_lines:
            continue
        if (finding.path, finding.text) in allowlist:
            continue
        if _has_allow_comment(source_lines, finding.line):
            continue
        findings.append(finding)
    return sorted(
        findings, key=lambda finding: (finding.path, finding.line, finding.text)
    )


def load_i18n_raw_ui_allowlist() -> set[tuple[str, str]]:
    doc_path = ROOT / "docs" / "i18n_key_list.md"
    if not doc_path.exists():
        return set()

    allowlist: set[tuple[str, str]] = set()
    for line in doc_path.read_text(encoding="utf-8").splitlines():
        match = DOC_BACKLOG_ROW_RE.match(line)
        if match is None:
            continue
        location = match.group("location")
        if ":" not in location:
            continue
        path = _normalize_path(location.rsplit(":", 1)[0])
        if not path.startswith("wizard_pages/"):
            continue
        copy = _normalize_ui_text(match.group("copy"))
        if copy:
            allowlist.add((path, copy))
    return allowlist


def _parse_changed_lines(diff_text: str) -> dict[str, set[int]]:
    changed_lines: dict[str, set[int]] = {}
    current_path: str | None = None
    new_line: int | None = None

    for line in diff_text.splitlines():
        file_match = DIFF_FILE_RE.match(line)
        if file_match is not None:
            current_path = _normalize_path(file_match.group("path"))
            new_line = None
            continue

        hunk_match = DIFF_HUNK_RE.match(line)
        if hunk_match is not None:
            new_line = int(hunk_match.group("start"))
            continue

        if current_path is None or new_line is None:
            continue
        if current_path not in ACTIVE_WIZARD_RAW_UI_PATHS:
            continue

        if line.startswith("+") and not line.startswith("+++"):
            changed_lines.setdefault(current_path, set()).add(new_line)
            new_line += 1
        elif line.startswith("-") and not line.startswith("---"):
            continue
        else:
            new_line += 1

    return changed_lines


def _merge_changed_lines(
    first: dict[str, set[int]],
    second: dict[str, set[int]],
) -> dict[str, set[int]]:
    merged = {path: set(lines) for path, lines in first.items()}
    for path, lines in second.items():
        merged.setdefault(path, set()).update(lines)
    return merged


def _run_git_diff(args: list[str]) -> dict[str, set[int]]:
    result = subprocess.run(
        args,
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if result.returncode not in {0, 1}:
        return {}
    return _parse_changed_lines(result.stdout)


def _changed_wizard_python_lines() -> dict[str, set[int]]:
    base_ref = os.getenv(RAW_UI_BASE_REF_ENV, "").strip()
    if base_ref and set(base_ref) != {"0"}:
        return _run_git_diff(
            [
                "git",
                "diff",
                "--unified=0",
                "--diff-filter=ACMRTUXB",
                f"{base_ref}...HEAD",
                "--",
                "wizard_pages",
            ]
        )

    github_base_ref = os.getenv("GITHUB_BASE_REF", "").strip()
    if github_base_ref:
        return _run_git_diff(
            [
                "git",
                "diff",
                "--unified=0",
                "--diff-filter=ACMRTUXB",
                f"origin/{github_base_ref}...HEAD",
                "--",
                "wizard_pages",
            ]
        )

    unstaged = _run_git_diff(
        [
            "git",
            "diff",
            "--unified=0",
            "--diff-filter=ACMRTUXB",
            "--",
            "wizard_pages",
        ]
    )
    staged = _run_git_diff(
        [
            "git",
            "diff",
            "--cached",
            "--unified=0",
            "--diff-filter=ACMRTUXB",
            "--",
            "wizard_pages",
        ]
    )
    return _merge_changed_lines(unstaged, staged)


def find_changed_raw_ui_string_findings() -> list[RawUiStringFinding]:
    changed_lines = _changed_wizard_python_lines()
    if not changed_lines:
        return []

    allowlist = load_i18n_raw_ui_allowlist()
    findings: list[RawUiStringFinding] = []
    for path, lines in changed_lines.items():
        absolute_path = ROOT / path
        if not absolute_path.exists():
            continue
        source = absolute_path.read_text(encoding="utf-8")
        findings.extend(
            find_raw_ui_string_findings_in_source(
                path,
                source,
                changed_lines=lines,
                documented_allowlist=allowlist,
            )
        )
    return sorted(
        findings, key=lambda finding: (finding.path, finding.line, finding.text)
    )


def main() -> int:
    path_findings = find_hygiene_findings(_tracked_paths())
    contract_findings = find_i18n_contract_findings()
    raw_ui_findings = find_changed_raw_ui_string_findings()
    terminology_findings = find_active_terminology_findings()

    if (
        not path_findings
        and not contract_findings
        and not raw_ui_findings
        and not terminology_findings
    ):
        print(
            "Repository hygiene guard passed: no forbidden tracked paths or "
            "i18n contract drift."
        )
        return 0

    if path_findings:
        print("Repository hygiene guard found forbidden tracked paths:")
        for path_finding in path_findings:
            print(f"- {path_finding.path} [{path_finding.rule}]")

    if contract_findings:
        print("Repository hygiene guard found i18n contract drift:")
        for contract_finding in contract_findings:
            print(f"- {contract_finding.detail} [{contract_finding.rule}]")

    if raw_ui_findings:
        print("Repository hygiene guard found uncontrolled raw wizard UI strings:")
        for raw_ui_finding in raw_ui_findings:
            print(
                f"- {raw_ui_finding.path}:{raw_ui_finding.line} "
                f"[{raw_ui_finding.rule}] {raw_ui_finding.method}: "
                f"{raw_ui_finding.text}"
            )
        print(
            "  Use tr(...), tr_safe(...), t(...), ux_copy_contract.py, or add "
            f"`# {RAW_UI_ALLOW_COMMENT} <reason>` for an intentional exception."
        )

    if terminology_findings:
        print("Repository hygiene guard found active terminology drift:")
        for terminology_finding in terminology_findings:
            print(
                f"- {terminology_finding.location} "
                f"[{terminology_finding.rule}] {terminology_finding.term}"
            )
    return 1


if __name__ == "__main__":
    sys.exit(main())
