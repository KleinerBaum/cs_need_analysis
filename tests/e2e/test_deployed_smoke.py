from __future__ import annotations

import os
import re
from collections.abc import Iterator
from typing import TYPE_CHECKING
from urllib.parse import urlsplit, urlunsplit

import pytest

if TYPE_CHECKING:
    from playwright.sync_api import Page

CANONICAL_DEPLOYED_BASE_URL = "https://recruitment-need-analysis.streamlit.app/"
RUN_DEPLOYED_SMOKE = os.getenv("CS_RUN_DEPLOYED_SMOKE", "").strip() == "1"
REQUIRE_DEPLOYED_BASE_URL = (
    os.getenv("CS_REQUIRE_DEPLOYED_BASE_URL", "").strip() == "1"
)
CONFIGURED_DEPLOYED_BASE_URL = os.getenv("CS_DEPLOYED_BASE_URL", "").strip()
DEPRECATED_DEPLOYED_URLS = tuple(
    url.strip()
    for url in os.getenv("CS_DEPLOYED_DEPRECATED_URLS", "").split(",")
    if url.strip()
)
LANDING_SMOKE_TEXT = re.compile(
    r"Recruitment Need Analysis|Erst klären\. Dann suchen\.|Cognitive Staffing"
)
STREAMLIT_INTERNAL_ERROR_TEXT = re.compile(
    r"Internal Error|This app has encountered an error", re.IGNORECASE
)

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        not RUN_DEPLOYED_SMOKE,
        reason="Set CS_RUN_DEPLOYED_SMOKE=1 to run deployed smoke tests.",
    ),
]


@pytest.fixture()
def deployed_base_url() -> str:
    if CONFIGURED_DEPLOYED_BASE_URL:
        return CONFIGURED_DEPLOYED_BASE_URL

    if REQUIRE_DEPLOYED_BASE_URL:
        pytest.fail(
            "CS_DEPLOYED_BASE_URL is required when "
            "CS_REQUIRE_DEPLOYED_BASE_URL=1. Configure the deployed_smoke job "
            "with the public deployment URL.",
            pytrace=False,
        )

    return CANONICAL_DEPLOYED_BASE_URL


@pytest.fixture()
def page(deployed_base_url: str) -> Iterator["Page"]:
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


def _public_url(url: str) -> str:
    candidate = url.strip()
    if not candidate.startswith(("http://", "https://")):
        candidate = f"https://{candidate}"
    return candidate


def _normalized_public_url(url: str) -> str:
    parsed = urlsplit(_public_url(url))
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, "", ""))


def _goto_deployment(page: "Page", url: str, *, label: str) -> None:
    from playwright.sync_api import Error as PlaywrightError

    try:
        response = page.goto(_public_url(url), wait_until="domcontentloaded")
    except PlaywrightError as exc:
        message = str(exc)
        if "ERR_TOO_MANY_REDIRECTS" in message:
            pytest.fail(
                f"{label} failed with a redirect loop while loading {url}.",
                pytrace=False,
            )
        pytest.fail(f"{label} failed to load {url}: {message}", pytrace=False)

    if response is None:
        pytest.fail(f"{label} did not return a main document response.", pytrace=False)

    if response.status >= 400:
        pytest.fail(
            f"{label} returned HTTP {response.status} for {response.url}.",
            pytrace=False,
        )


def _assert_no_internal_error(page: "Page", *, label: str) -> None:
    body_text = page.locator("body").inner_text(timeout=10_000)
    if STREAMLIT_INTERNAL_ERROR_TEXT.search(body_text):
        pytest.fail(
            f"{label} rendered a Streamlit internal error at {page.url}. "
            "Check the deployment logs.",
            pytrace=False,
        )


def _assert_landing_visible(page: "Page", *, label: str) -> None:
    from playwright.sync_api import expect

    try:
        expect(page.get_by_text(LANDING_SMOKE_TEXT).first).to_be_visible(
            timeout=30_000
        )
    except AssertionError:
        _assert_no_internal_error(page, label=label)
        pytest.fail(
            f"{label} loaded {page.url}, but the landing page text was not visible.",
            pytrace=False,
        )


def test_deployed_landing_smoke(page: "Page", deployed_base_url: str) -> None:
    canonical_url = _normalized_public_url(CANONICAL_DEPLOYED_BASE_URL)
    _goto_deployment(
        page,
        deployed_base_url,
        label="Canonical deployment",
    )

    final_url = _normalized_public_url(page.url)
    assert final_url == canonical_url, (
        "Canonical deployment must stay on the documented public URL: "
        f"expected {canonical_url}, got {final_url}"
    )
    _assert_no_internal_error(page, label="Canonical deployment")
    _assert_landing_visible(page, label="Canonical deployment")

    for deprecated_url in DEPRECATED_DEPLOYED_URLS:
        _goto_deployment(page, deprecated_url, label="Deprecated deployment URL")
        final_url = _normalized_public_url(page.url)
        assert final_url == canonical_url, (
            "Deprecated deployment URLs must redirect to the canonical public URL: "
            f"expected {canonical_url}, got {final_url}"
        )
        _assert_no_internal_error(page, label="Deprecated deployment URL")
