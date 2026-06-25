from __future__ import annotations

import os
import re
from collections.abc import Iterator
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from playwright.sync_api import Page

DEPLOYED_BASE_URL = os.getenv("CS_DEPLOYED_BASE_URL", "").strip()
LANDING_SMOKE_TEXT = re.compile(
    r"Recruitment Need Analysis|Erst klären\. Dann suchen\.|Cognitive Staffing"
)

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        not DEPLOYED_BASE_URL,
        reason="Set CS_DEPLOYED_BASE_URL to run deployed smoke tests.",
    ),
]


@pytest.fixture()
def page() -> Iterator["Page"]:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True)
        except PlaywrightError as exc:
            message = str(exc)
            if (
                "error while loading shared libraries" in message
                or "Host system is missing dependencies" in message
            ):
                pytest.skip(
                    "Chromium system dependencies are unavailable; run "
                    "`python -m playwright install --with-deps chromium`."
                )
            raise
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        browser_page = context.new_page()
        browser_page.set_default_timeout(20_000)
        try:
            yield browser_page
        finally:
            context.close()
            browser.close()


def _deployed_base_url() -> str:
    base_url = DEPLOYED_BASE_URL.rstrip("/")
    if base_url.startswith(("http://", "https://")):
        return base_url
    return f"https://{base_url}"


def test_deployed_landing_smoke(page: "Page") -> None:
    from playwright.sync_api import expect

    page.goto(_deployed_base_url(), wait_until="domcontentloaded")

    expect(page.get_by_text(LANDING_SMOKE_TEXT).first).to_be_visible(timeout=30_000)
