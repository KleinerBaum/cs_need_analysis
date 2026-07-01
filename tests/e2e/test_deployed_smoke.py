from __future__ import annotations

import os
import re
from collections.abc import Iterator
from typing import TYPE_CHECKING
from urllib.parse import urlsplit, urlunsplit

import pytest

if TYPE_CHECKING:
    from playwright.sync_api import Page

CANONICAL_PUBLIC_URL = "https://recruitment-need-analysis.streamlit.app/"
RUN_DEPLOYED_SMOKE = os.getenv("CS_RUN_DEPLOYED_SMOKE", "").strip() == "1"
DEPRECATED_DEPLOYED_URLS = tuple(
    url.strip()
    for url in os.getenv("CS_DEPLOYED_DEPRECATED_URLS", "").split(",")
    if url.strip()
)
LANDING_SMOKE_TEXT = re.compile(
    r"Recruitment Need Analysis|Erst klären\. Dann suchen\.|Cognitive Staffing"
)
PRIMARY_WIZARD_CTA_TEXT = re.compile(r"Briefing-Cockpit öffnen|Open briefing cockpit")
START_INTAKE_TEXT = re.compile(
    r"Anzeige hochladen oder einfügen|Upload or paste job ad", re.IGNORECASE
)
SUMMARY_ENTRY_TEXT = re.compile(
    r"Zusammenfassung|Summary|Recruiting Brief|Stellenanzeige|Job ad|Export",
    re.IGNORECASE,
)
STREAMLIT_INTERNAL_ERROR_TEXT = re.compile(
    r"Internal Error|This app has encountered an error", re.IGNORECASE
)
IGNORED_REQUEST_FAILURE_TEXT = ("net::ERR_ABORTED",)
BROWSER_ISSUE_LIMIT = 12

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        not RUN_DEPLOYED_SMOKE,
        reason="Set CS_RUN_DEPLOYED_SMOKE=1 to run deployed smoke tests.",
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


def _public_url(url: str) -> str:
    candidate = url.strip()
    if not candidate.startswith(("http://", "https://")):
        candidate = f"https://{candidate}"
    return candidate


def _normalized_public_url(url: str) -> str:
    parsed = urlsplit(_public_url(url))
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, "", ""))


def _public_url_with_query(url: str, query: str) -> str:
    parsed = urlsplit(_public_url(url))
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit((parsed.scheme, parsed.netloc, path, query, ""))


def _streamlit_health_url(url: str) -> str:
    parsed = urlsplit(_public_url(url))
    return urlunsplit((parsed.scheme, parsed.netloc, "/_stcore/health", "", ""))


def _short_url(url: str) -> str:
    parsed = urlsplit(url)
    path = parsed.path or "/"
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{parsed.netloc}{path}{query}"


def _install_browser_issue_capture(page: "Page") -> dict[str, list[str]]:
    issues: dict[str, list[str]] = {
        "console_errors": [],
        "network_failures": [],
        "server_errors": [],
    }

    def add_issue(kind: str, message: str) -> None:
        bucket = issues[kind]
        if len(bucket) < BROWSER_ISSUE_LIMIT:
            bucket.append(message)

    def on_console(message: object) -> None:
        if getattr(message, "type", "") != "error":
            return
        location = getattr(message, "location", {}) or {}
        location_url = str(location.get("url") or "")
        line = location.get("lineNumber")
        suffix = f" at {_short_url(location_url)}:{line}" if location_url else ""
        add_issue("console_errors", f"{message.text}{suffix}")

    def on_request_failed(request: object) -> None:
        failure = str(getattr(request, "failure", None) or "unknown network failure")
        if any(ignored in failure for ignored in IGNORED_REQUEST_FAILURE_TEXT):
            return
        add_issue(
            "network_failures",
            f"{getattr(request, 'method', 'GET')} {_short_url(request.url)}: {failure}",
        )

    def on_response(response: object) -> None:
        status = int(getattr(response, "status", 0) or 0)
        if status < 500:
            return
        request = response.request
        add_issue(
            "server_errors",
            f"HTTP {status} {request.method} {_short_url(response.url)}",
        )

    page.on("console", on_console)
    page.on("requestfailed", on_request_failed)
    page.on("response", on_response)
    return issues


def _assert_no_browser_issues(issues: dict[str, list[str]], *, label: str) -> None:
    details: list[str] = []
    for title, key in (
        ("HTTP 5xx responses", "server_errors"),
        ("Network failures", "network_failures"),
        ("Console errors", "console_errors"),
    ):
        values = issues[key]
        if values:
            details.append(f"{title}:\n- " + "\n- ".join(values))
    if details:
        pytest.fail(
            f"{label} emitted browser/runtime errors:\n\n" + "\n\n".join(details),
            pytrace=False,
        )


def _assert_streamlit_health(page: "Page", url: str, *, label: str) -> None:
    from playwright.sync_api import Error as PlaywrightError

    health_url = _streamlit_health_url(url)
    try:
        response = page.context.request.get(
            health_url,
            timeout=10_000,
            max_redirects=5,
        )
    except PlaywrightError as exc:
        message = str(exc)
        if "redirect" in message.lower():
            pytest.fail(
                f"{label} health check failed with a redirect loop at {health_url}.",
                pytrace=False,
            )
        pytest.fail(
            f"{label} health check failed at {health_url}: {message}",
            pytrace=False,
        )

    if response.status >= 500:
        pytest.fail(
            f"{label} health check returned HTTP {response.status} for {response.url}.",
            pytrace=False,
        )
    if response.status != 200:
        pytest.fail(
            f"{label} health check expected HTTP 200, got HTTP {response.status} "
            f"for {response.url}.",
            pytrace=False,
        )


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


def _assert_primary_cta_visible(page: "Page", *, label: str) -> None:
    from playwright.sync_api import expect

    try:
        expect(page.get_by_role("button", name=PRIMARY_WIZARD_CTA_TEXT)).to_be_visible(
            timeout=15_000
        )
    except AssertionError:
        _assert_no_internal_error(page, label=label)
        pytest.fail(
            f"{label} loaded {page.url}, but the primary wizard CTA was not visible.",
            pytrace=False,
        )


def _assert_summary_entry_reachable(page: "Page", base_url: str) -> None:
    from playwright.sync_api import expect

    summary_url = _public_url_with_query(base_url, "wizard_step=summary")
    _goto_deployment(page, summary_url, label="Summary route")
    _assert_no_internal_error(page, label="Summary route")
    try:
        expect(page.get_by_text(SUMMARY_ENTRY_TEXT).first).to_be_visible(
            timeout=30_000
        )
    except AssertionError:
        pytest.fail(
            "Summary route loaded, but no Summary/export entry point text was visible "
            f"at {page.url}.",
            pytrace=False,
        )


def test_deployed_landing_smoke(page: "Page") -> None:
    deployed_url = CANONICAL_PUBLIC_URL
    canonical_url = _normalized_public_url(CANONICAL_PUBLIC_URL)
    browser_issues = _install_browser_issue_capture(page)

    _assert_streamlit_health(
        page,
        deployed_url,
        label="Canonical deployment",
    )
    _goto_deployment(
        page,
        deployed_url,
        label="Canonical deployment",
    )

    final_url = _normalized_public_url(page.url)
    assert final_url == canonical_url, (
        "Canonical deployment must stay on the documented public URL: "
        f"expected {canonical_url}, got {final_url}"
    )
    _assert_no_internal_error(page, label="Canonical deployment")
    _assert_landing_visible(page, label="Canonical deployment")
    _assert_primary_cta_visible(page, label="Canonical deployment")
    page.get_by_role("button", name=PRIMARY_WIZARD_CTA_TEXT).click()
    try:
        from playwright.sync_api import expect

        expect(page.get_by_text(START_INTAKE_TEXT).first).to_be_visible(timeout=30_000)
    except AssertionError:
        _assert_no_internal_error(page, label="Start step")
        pytest.fail(
            "Primary wizard CTA was visible, but the Start intake step did not render.",
            pytrace=False,
        )

    _assert_summary_entry_reachable(page, deployed_url)
    _assert_no_browser_issues(browser_issues, label="Canonical deployment")

    for deprecated_url in DEPRECATED_DEPLOYED_URLS:
        _goto_deployment(page, deprecated_url, label="Deprecated deployment URL")
        final_url = _normalized_public_url(page.url)
        assert final_url == canonical_url, (
            "Deprecated deployment URLs must redirect to the canonical public URL: "
            f"expected {canonical_url}, got {final_url}"
        )
        _assert_no_internal_error(page, label="Deprecated deployment URL")
    _assert_no_browser_issues(browser_issues, label="Deprecated deployment URL")
