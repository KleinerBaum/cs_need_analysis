"""Deterministic app-shell performance budget smoke checks.

This avoids timing assertions. It checks the static asset contract that drives
the Streamlit app shell and fails when oversized background payloads return or
large PNG payloads are moved inline.
"""

from __future__ import annotations

import argparse
import ast
import base64
import binascii
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "app.py"
APP_SHELL_SCAN_PATHS = (
    APP_PATH,
    ROOT / "styles" / "app_shell.css",
    ROOT / "components" / "design_system.py",
)
THEME_BACKGROUND_CONSTANT_NAMES = (
    "WIZARD_LIGHT_BACKGROUND_PATH",
    "WIZARD_DARK_BACKGROUND_PATH",
)
INLINE_PNG_BYTE_BUDGET = 32 * 1024
# Half of the former 3,021,442-byte app-shell background payload.
THEME_BACKGROUND_TOTAL_BYTE_BUDGET = 1_510_721
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
DATA_URI_PNG_PATTERN = re.compile(
    r"data:image/png;base64,(?P<payload>[A-Za-z0-9+/=\s]+)"
)


@dataclass(frozen=True)
class AppStaticContract:
    static_dir: Path
    static_url_prefix: str
    theme_background_paths: tuple[Path, ...]


@dataclass(frozen=True)
class ThemeBackgroundAsset:
    path: Path
    url_path: str
    byte_size: int


@dataclass(frozen=True)
class InlinePngFinding:
    source_path: Path
    line_number: int
    decoded_byte_size: int


@dataclass(frozen=True)
class StaticAssetFetch:
    url: str
    content_type: str


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _evaluate_contract_expr(node: ast.AST, values: dict[str, object]) -> object:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name) and node.id in values:
        return values[node.id]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        left = _evaluate_contract_expr(node.left, values)
        right = _evaluate_contract_expr(node.right, values)
        if isinstance(left, Path) and isinstance(right, str):
            return left / right
    raise ValueError(f"Unsupported app static contract expression: {ast.dump(node)}")


def load_app_static_contract(app_path: Path = APP_PATH) -> AppStaticContract:
    """Resolve static asset constants from app.py without importing Streamlit."""

    tree = ast.parse(app_path.read_text(encoding="utf-8"), filename=str(app_path))
    values: dict[str, object] = {"ROOT_DIR": ROOT}
    target_names = {
        "STATIC_DIR",
        "STREAMLIT_STATIC_URL_PREFIX",
        *THEME_BACKGROUND_CONSTANT_NAMES,
    }

    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or target.id not in target_names:
            continue
        values[target.id] = _evaluate_contract_expr(node.value, values)

    missing = sorted(name for name in target_names if name not in values)
    if missing:
        raise RuntimeError(f"Missing app static contract constants: {', '.join(missing)}")

    static_dir = values["STATIC_DIR"]
    static_url_prefix = values["STREAMLIT_STATIC_URL_PREFIX"]
    theme_paths = tuple(values[name] for name in THEME_BACKGROUND_CONSTANT_NAMES)
    if not isinstance(static_dir, Path):
        raise RuntimeError("STATIC_DIR must resolve to a Path.")
    if not isinstance(static_url_prefix, str):
        raise RuntimeError("STREAMLIT_STATIC_URL_PREFIX must resolve to a string.")
    if not all(isinstance(path, Path) for path in theme_paths):
        raise RuntimeError("Theme background constants must resolve to Paths.")

    return AppStaticContract(
        static_dir=static_dir,
        static_url_prefix=static_url_prefix,
        theme_background_paths=tuple(
            path for path in theme_paths if isinstance(path, Path)
        ),
    )


def static_asset_url(path: Path, contract: AppStaticContract) -> str:
    try:
        asset_path = path.resolve().relative_to(contract.static_dir.resolve())
    except ValueError:
        asset_path = Path(path.name)
    return f"{contract.static_url_prefix}/{quote(asset_path.as_posix())}"


def collect_theme_background_assets(
    contract: AppStaticContract | None = None,
) -> tuple[ThemeBackgroundAsset, ...]:
    contract = contract or load_app_static_contract()
    assets: list[ThemeBackgroundAsset] = []
    for path in contract.theme_background_paths:
        if not path.exists():
            raise FileNotFoundError(f"Missing theme background asset: {_relative_path(path)}")
        if path.suffix.lower() != ".png":
            raise RuntimeError(
                f"Theme background asset must be a PNG: {_relative_path(path)}"
            )
        assets.append(
            ThemeBackgroundAsset(
                path=path,
                url_path=static_asset_url(path, contract),
                byte_size=path.stat().st_size,
            )
        )
    return tuple(assets)


def _decoded_png_size(payload: str) -> int:
    normalized = re.sub(r"\s+", "", payload)
    try:
        return len(base64.b64decode(normalized, validate=True))
    except binascii.Error:
        padding = normalized.count("=")
        return max(0, (len(normalized) * 3 // 4) - padding)


def find_large_inline_pngs(
    paths: Iterable[Path] = APP_SHELL_SCAN_PATHS,
    *,
    byte_budget: int = INLINE_PNG_BYTE_BUDGET,
) -> tuple[InlinePngFinding, ...]:
    findings: list[InlinePngFinding] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for match in DATA_URI_PNG_PATTERN.finditer(text):
            decoded_size = _decoded_png_size(match.group("payload"))
            if decoded_size <= byte_budget:
                continue
            findings.append(
                InlinePngFinding(
                    source_path=path,
                    line_number=text.count("\n", 0, match.start()) + 1,
                    decoded_byte_size=decoded_size,
                )
            )
    return tuple(findings)


def _display_url(url: str) -> str:
    parsed = urlsplit(url)
    host = parsed.hostname or parsed.netloc
    if parsed.port:
        host = f"{host}:{parsed.port}"
    return urlunsplit((parsed.scheme, host, parsed.path or "/", "", ""))


def _asset_url(base_url: str, asset_path: str) -> str:
    parsed = urlsplit(base_url.strip())
    if not parsed.scheme:
        parsed = urlsplit(f"https://{base_url.strip()}")
    if parsed.scheme.lower() not in {"http", "https"}:
        raise RuntimeError("Static asset base URL must use HTTP(S).")
    base_path = parsed.path.rstrip("/")
    asset = asset_path if asset_path.startswith("/") else f"/{asset_path}"
    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            f"{base_path}{asset}",
            "",
            "",
        )
    )


def fetch_static_asset(
    base_url: str,
    asset: ThemeBackgroundAsset,
    *,
    timeout_seconds: float = 10.0,
    max_redirects: int = 5,
) -> StaticAssetFetch:
    url = _asset_url(base_url, asset.url_path)
    current_url = url
    content_type = ""
    signature = b""
    for _redirect_count in range(max_redirects + 1):
        request = Request(
            current_url,
            headers={"User-Agent": "cs-need-analysis-perf-budget-smoke/1.0"},
        )
        try:
            # _asset_url restricts requests to HTTP(S).
            with urlopen(  # nosec B310
                request,
                timeout=timeout_seconds,
            ) as response:
                content_type = response.headers.get("Content-Type", "")
                signature = response.read(len(PNG_SIGNATURE))
                break
        except HTTPError as exc:
            location = exc.headers.get("Location", "")
            if exc.code in {301, 302, 303, 307, 308} and location:
                current_url = urljoin(current_url, location)
                continue
            raise RuntimeError(
                f"Static asset returned HTTP {exc.code}: {_display_url(current_url)}"
            ) from exc
        except URLError as exc:
            raise RuntimeError(
                f"Static asset request failed for {_display_url(current_url)}: "
                f"{exc.reason}"
            ) from exc
    else:
        raise RuntimeError(f"Static asset redirect loop: {_display_url(url)}")

    if not content_type.lower().startswith("image/png"):
        raise RuntimeError(
            "Static asset did not return image/png: "
            f"{_display_url(current_url)} ({content_type or 'no content type'})"
        )
    if signature != PNG_SIGNATURE:
        raise RuntimeError(
            f"Static asset is not a PNG payload: {_display_url(current_url)}"
        )
    return StaticAssetFetch(url=current_url, content_type=content_type)


def _theme_background_total_bytes(assets: tuple[ThemeBackgroundAsset, ...]) -> int:
    return sum(asset.byte_size for asset in assets)


def _print_asset_report(assets: tuple[ThemeBackgroundAsset, ...]) -> None:
    print("Theme background static assets:")
    for asset in assets:
        print(
            f"- {_relative_path(asset.path)}: {asset.byte_size} bytes "
            f"({asset.url_path})"
        )
    total_bytes = _theme_background_total_bytes(assets)
    print(
        "Total theme background bytes: "
        f"{total_bytes} (budget: {THEME_BACKGROUND_TOTAL_BYTE_BUDGET})"
    )


def run(base_url: str | None = None) -> int:
    errors: list[str] = []
    try:
        contract = load_app_static_contract()
        assets = collect_theme_background_assets(contract)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"Static asset contract error: {exc}", file=sys.stderr)
        return 1

    _print_asset_report(assets)
    total_background_bytes = _theme_background_total_bytes(assets)
    if total_background_bytes > THEME_BACKGROUND_TOTAL_BYTE_BUDGET:
        errors.append(
            "Theme background static assets exceed "
            f"{THEME_BACKGROUND_TOTAL_BYTE_BUDGET} bytes "
            f"({total_background_bytes} bytes)"
        )

    findings = find_large_inline_pngs()
    if findings:
        for finding in findings:
            errors.append(
                "Large inline PNG data URI exceeds "
                f"{INLINE_PNG_BYTE_BUDGET} bytes: "
                f"{_relative_path(finding.source_path)}:{finding.line_number} "
                f"({finding.decoded_byte_size} decoded bytes)"
            )
    else:
        print(
            "Large inline PNG data URIs: 0 "
            f"(budget: {INLINE_PNG_BYTE_BUDGET} decoded bytes)"
        )

    normalized_base_url = str(base_url or "").strip()
    if normalized_base_url:
        for asset in assets:
            try:
                result = fetch_static_asset(normalized_base_url, asset)
            except RuntimeError as exc:
                errors.append(str(exc))
                continue
            print(
                "Static asset fetch OK: "
                f"{_display_url(result.url)} ({result.content_type})"
            )
    else:
        print(
            "Static asset fetch: skipped "
            "(pass --base-url or CS_PERF_SMOKE_BASE_URL to check HTTP responses)"
        )

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("Performance budget smoke OK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run deterministic app-shell payload budget checks."
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("CS_PERF_SMOKE_BASE_URL", ""),
        help=(
            "Optional deployed or local Streamlit base URL. When set, the script "
            "fetches theme background static assets and fails on missing/non-PNG "
            "responses."
        ),
    )
    args = parser.parse_args()
    return run(base_url=args.base_url)


if __name__ == "__main__":
    raise SystemExit(main())
