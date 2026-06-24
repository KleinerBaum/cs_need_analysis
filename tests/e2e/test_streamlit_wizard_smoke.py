from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator
from urllib.error import URLError
from urllib.request import urlopen

import pytest

if TYPE_CHECKING:
    from playwright.sync_api import Page

E2E_ENABLED = os.getenv("CS_RUN_E2E") == "1"
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        not E2E_ENABLED,
        reason="Set CS_RUN_E2E=1 to run optional Streamlit browser smoke tests.",
    ),
]

ROOT_DIR = Path(__file__).resolve().parents[2]
STREAMLIT_APP = ROOT_DIR / "tests" / "e2e" / "streamlit_smoke_app.py"
SYNTHETIC_JOBSPEC = (
    "Synthetic Product Analyst vacancy. Build dashboards, clarify metrics, "
    "and work with stakeholders. Skills: SQL, Python, experimentation."
)


def _e2e_port() -> int:
    return int(os.getenv("CS_E2E_PORT", "8765"))


def _startup_timeout_seconds() -> float:
    return float(os.getenv("CS_E2E_STARTUP_TIMEOUT", "60"))


def _wait_for_streamlit(base_url: str, proc: subprocess.Popen[object]) -> None:
    deadline = time.monotonic() + _startup_timeout_seconds()
    health_url = f"{base_url}/_stcore/health"
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"Streamlit exited early with code {proc.returncode}.")
        try:
            with urlopen(health_url, timeout=2) as response:
                if response.status == 200:
                    return
        except (OSError, URLError) as exc:
            last_error = exc
        time.sleep(0.5)
    raise RuntimeError(f"Streamlit did not become healthy at {health_url}: {last_error}")


@pytest.fixture(scope="session")
def streamlit_base_url() -> Iterator[str]:
    port = _e2e_port()
    base_url = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["CS_E2E_TEST_MODE"] = "1"
    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(STREAMLIT_APP),
        "--server.port",
        str(port),
        "--server.address",
        "127.0.0.1",
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]
    proc: subprocess.Popen[object] = subprocess.Popen(
        command,
        cwd=ROOT_DIR,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_streamlit(base_url, proc)
        yield base_url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


@pytest.fixture()
def page() -> Iterator["Page"]:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            accept_downloads=True,
            viewport={"width": 1440, "height": 1000},
        )
        browser_page = context.new_page()
        browser_page.set_default_timeout(20_000)
        try:
            yield browser_page
        finally:
            context.close()
            browser.close()


def _expect(target: object) -> Any:
    from playwright.sync_api import expect

    return expect(target)


def test_landing_jobspec_input_and_step_navigation(
    streamlit_base_url: str, page: "Page"
) -> None:
    page.goto(streamlit_base_url, wait_until="domcontentloaded")

    _expect(
        page.get_by_role("heading", name="Recruiting-Briefing vor Workflow")
    ).to_be_visible(timeout=30_000)
    page.get_by_role("button", name="Briefing-Cockpit öffnen").click()

    _expect(page.get_by_text("Anzeige hochladen oder einfügen")).to_be_visible()
    source_input = page.get_by_label("Jobspec oder Rohtext für das Briefing einfügen")
    source_input.fill(SYNTHETIC_JOBSPEC)
    _expect(source_input).to_have_value(SYNTHETIC_JOBSPEC)

    page.get_by_role("radio", name=re.compile("Unternehmen")).check()
    _expect(
        page.get_by_text("Bitte zuerst im Start-Schritt eine Analyse durchführen.")
    ).to_be_visible()


def test_summary_artifact_download_smoke(streamlit_base_url: str, page: "Page") -> None:
    page.goto(
        f"{streamlit_base_url}/?wizard_step=summary&e2e_seed=summary_artifact",
        wait_until="domcontentloaded",
    )

    _expect(
        page.get_by_text("Alles bereit für Recruiting und Hiring-Team").first
    ).to_be_visible(timeout=30_000)
    _expect(
        page.get_by_role("button", name=re.compile("Recruiting Brief")).first
    ).to_be_visible()
    _expect(page.get_by_text("Synthetic Data Engineer").first).to_be_visible()

    with page.expect_download() as download_info:
        page.get_by_role(
            "button", name="Download Stellenanzeige (Markdown)"
        ).first.click()
    download = download_info.value

    assert download.suggested_filename == "stellenanzeige.md"
    download_path = download.path()
    assert download_path is not None
    downloaded_text = Path(download_path).read_text(encoding="utf-8")
    assert "Synthetic Data Engineer" in downloaded_text
    assert "real customer data" in downloaded_text
