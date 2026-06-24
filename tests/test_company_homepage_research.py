from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import socket
from types import SimpleNamespace

import pytest

import homepage_research
import services.homepage as homepage_service
import state as state_module
from constants import (
    FactKey,
    FactResolutionStatus,
    FactSourceType,
    SSKey,
    WEBSITE_RESEARCH_HOMEPAGE_URL,
    WEBSITE_RESEARCH_OPEN_QUESTION_MATCHES,
    WEBSITE_RESEARCH_SECTIONS,
    WEBSITE_SECTION_FACTS,
    WEBSITE_SECTION_SOURCE_URL,
    WEBSITE_SECTION_SUMMARY,
    WEBSITE_TOPIC_ABOUT,
)
from schemas import CompanyWebsiteResearch, QuestionPlan
from usage_events import get_usage_events

COMPANY_PATH = Path(__file__).resolve().parents[1] / "wizard_pages" / "02_company.py"
SPEC = spec_from_file_location("wizard_pages.page_02_company", COMPANY_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load company module")
COMPANY_MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(COMPANY_MODULE)  # type: ignore[attr-defined]


class _FakeHeaders:
    def __init__(
        self,
        content_type: str = "text/html",
        extra: dict[str, str] | None = None,
    ) -> None:
        self._content_type = content_type
        self._extra = {
            str(key).casefold(): str(value) for key, value in (extra or {}).items()
        }

    def get_content_charset(self) -> str:
        return "utf-8"

    def get_content_type(self) -> str:
        return self._content_type

    def get(self, key: str, default: str = "") -> str:
        if key.casefold() == "content-type":
            return self._content_type
        return self._extra.get(key.casefold(), default)


class _FakeResponse:
    def __init__(
        self,
        payload: str,
        *,
        final_url: str = "https://example.com",
        content_type: str = "text/html",
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._payload = payload.encode("utf-8")
        self._final_url = final_url
        self.headers = _FakeHeaders(content_type, headers)
        self.status = status_code
        self.code = status_code
        self.closed = False
        self.read_calls = 0

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def geturl(self) -> str:
        return self._final_url

    def getcode(self) -> int:
        return self.status

    def read(self, _size: int = -1) -> bytes:
        self.read_calls += 1
        return self._payload

    def close(self) -> None:
        self.closed = True


def _patch_dns(
    monkeypatch: pytest.MonkeyPatch,
    records: dict[str, tuple[str, ...]] | None = None,
) -> None:
    resolved = records or {"example.com": ("93.184.216.34",)}

    def fake_getaddrinfo(
        host: str,
        _port: object,
        *_args: object,
        **_kwargs: object,
    ) -> list[tuple[int, int, int, str, tuple[str, int]]]:
        addresses = resolved.get(str(host).strip("[]").casefold())
        if addresses is None:
            raise OSError("unresolved test host")
        return [
            (
                socket.AF_INET6 if ":" in address else socket.AF_INET,
                socket.SOCK_STREAM,
                0,
                "",
                (address, 0),
            )
            for address in addresses
        ]

    monkeypatch.setattr(homepage_research.socket, "getaddrinfo", fake_getaddrinfo)


def test_homepage_service_facade_preserves_legacy_imports() -> None:
    assert homepage_service.HomepageFetchError is homepage_research.HomepageFetchError
    assert homepage_service.HomepageFetchResult is homepage_research.HomepageFetchResult
    assert homepage_service.normalize_url is homepage_research.normalize_url
    assert homepage_service.fetch_url_text is homepage_research.fetch_url_text
    assert (
        homepage_service.build_company_website_research
        is homepage_research.build_company_website_research
    )


def test_company_page_uses_homepage_service_facade() -> None:
    assert COMPANY_MODULE._fetch_url_text is homepage_service.fetch_url_text
    assert (
        COMPANY_MODULE._build_company_website_research
        is homepage_service.build_company_website_research
    )


def test_strip_html_removes_script_payload_noise() -> None:
    html = """
    <html><body>
    <script>window.adobeDataLayer = [{x: 1}]</script>
    <h1>Über uns</h1>
    <p>Wir beraten Kunden in der Energiebranche mit klarer Delivery-Verantwortung.</p>
    </body></html>
    """

    text = COMPANY_MODULE._strip_html(html)

    assert "adobedatalayer" not in text.casefold()
    assert "Wir beraten Kunden" in text


def test_normalize_url_rejects_local_or_private_targets() -> None:
    assert COMPANY_MODULE._normalize_url("localhost") == ""
    assert COMPANY_MODULE._normalize_url("http://127.0.0.1:8501") == ""
    assert COMPANY_MODULE._normalize_url("https://192.168.0.10") == ""
    assert COMPANY_MODULE._normalize_url("http://[::1]/") == ""
    assert COMPANY_MODULE._normalize_url("http://[fd00::1]/") == ""
    assert COMPANY_MODULE._normalize_url("http://[fe80::1%25eth0]/") == ""
    assert COMPANY_MODULE._normalize_url("https://example.com@127.0.0.1/") == ""


def test_fetch_url_text_allows_public_target(monkeypatch) -> None:
    homepage_research.clear_fetch_cache()
    _patch_dns(monkeypatch)
    opened_urls: list[str] = []

    def fake_open_url(request: object, timeout_sec: float) -> _FakeResponse:
        assert timeout_sec == 8.0
        request_url = str(getattr(request, "full_url"))
        opened_urls.append(request_url)
        return _FakeResponse(
            "<html><body>Über uns</body></html>",
            final_url=request_url,
        )

    monkeypatch.setattr(homepage_research, "_open_url", fake_open_url)

    result = COMPANY_MODULE._fetch_url_text("example.com")

    assert result == ("https://example.com", "<html><body>Über uns</body></html>")
    assert opened_urls == ["https://example.com"]


def test_fetch_url_text_rejects_hostname_resolving_to_private_ip(monkeypatch) -> None:
    homepage_research.clear_fetch_cache()
    _patch_dns(monkeypatch, {"example.com": ("10.0.0.5",)})

    def fake_open_url(_request: object, _timeout_sec: float) -> _FakeResponse:
        pytest.fail("Fetch should not start for private DNS targets")

    monkeypatch.setattr(homepage_research, "_open_url", fake_open_url)

    with pytest.raises(homepage_research.HomepageFetchError, match="invalid"):
        COMPANY_MODULE._fetch_url_text("https://example.com")


def test_fetch_url_text_rejects_hostname_resolving_to_private_ipv6(
    monkeypatch,
) -> None:
    homepage_research.clear_fetch_cache()
    _patch_dns(monkeypatch, {"example.com": ("fd00::5",)})

    def fake_open_url(_request: object, _timeout_sec: float) -> _FakeResponse:
        pytest.fail("Fetch should not start for private IPv6 DNS targets")

    monkeypatch.setattr(homepage_research, "_open_url", fake_open_url)

    with pytest.raises(homepage_research.HomepageFetchError, match="invalid"):
        COMPANY_MODULE._fetch_url_text("https://example.com")


def test_fetch_url_text_rejects_redirect_to_private_target(monkeypatch) -> None:
    homepage_research.clear_fetch_cache()
    _patch_dns(monkeypatch)
    redirect_response = _FakeResponse(
        "",
        final_url="https://example.com",
        status_code=302,
        headers={"Location": "http://10.0.0.1/"},
    )

    def fake_open_url(_request: object, _timeout_sec: float) -> _FakeResponse:
        return redirect_response

    monkeypatch.setattr(homepage_research, "_open_url", fake_open_url)

    with pytest.raises(homepage_research.HomepageFetchError, match="redirect"):
        COMPANY_MODULE._fetch_url_text("https://example.com")
    assert redirect_response.read_calls == 0


def test_fetch_url_text_rejects_private_final_url_before_read(monkeypatch) -> None:
    homepage_research.clear_fetch_cache()
    _patch_dns(monkeypatch)
    response = _FakeResponse(
        "<html><body>secret</body></html>",
        final_url="http://127.0.0.1/admin",
    )

    def fake_open_url(_request: object, _timeout_sec: float) -> _FakeResponse:
        return response

    monkeypatch.setattr(homepage_research, "_open_url", fake_open_url)

    with pytest.raises(homepage_research.HomepageFetchError, match="redirect"):
        COMPANY_MODULE._fetch_url_text("https://example.com")
    assert response.read_calls == 0
    assert response.closed is True


def test_fetch_url_text_rejects_unsupported_explicit_port() -> None:
    homepage_research.clear_fetch_cache()

    assert COMPANY_MODULE._normalize_url("https://example.com:8443") == ""
    with pytest.raises(homepage_research.HomepageFetchError, match="invalid"):
        COMPANY_MODULE._fetch_url_text("https://example.com:8443")


def test_fetch_url_text_enforces_redirect_limit(monkeypatch) -> None:
    homepage_research.clear_fetch_cache()
    _patch_dns(monkeypatch)
    opened_urls: list[str] = []

    def fake_open_url(request: object, _timeout_sec: float) -> _FakeResponse:
        request_url = str(getattr(request, "full_url"))
        opened_urls.append(request_url)
        return _FakeResponse(
            "",
            final_url=request_url,
            status_code=302,
            headers={"Location": f"https://example.com/r{len(opened_urls)}"},
        )

    monkeypatch.setattr(homepage_research, "_open_url", fake_open_url)

    with pytest.raises(homepage_research.HomepageFetchError, match="too_many"):
        COMPANY_MODULE._fetch_url_text("https://example.com")
    assert len(opened_urls) == homepage_research.HOMEPAGE_FETCH_MAX_REDIRECTS + 1


def test_fetch_url_text_rejects_unsupported_content_type(monkeypatch) -> None:
    homepage_research.clear_fetch_cache()
    _patch_dns(monkeypatch)

    def fake_open_url(_request: object, timeout_sec: float) -> _FakeResponse:
        assert timeout_sec == 8.0
        return _FakeResponse("%PDF-1.7", content_type="application/pdf")

    monkeypatch.setattr(homepage_research, "_open_url", fake_open_url)

    with pytest.raises(homepage_research.HomepageFetchError, match="unsupported"):
        COMPANY_MODULE._fetch_url_text("https://example.com")


def test_fetch_url_text_rejects_spoofed_content_type_prefix(
    monkeypatch,
) -> None:
    homepage_research.clear_fetch_cache()
    _patch_dns(monkeypatch)
    response = _FakeResponse(
        "<html><body>Über uns</body></html>",
        content_type="text/html-malicious",
    )

    def fake_open_url(_request: object, _timeout_sec: float) -> _FakeResponse:
        return response

    monkeypatch.setattr(homepage_research, "_open_url", fake_open_url)

    with pytest.raises(homepage_research.HomepageFetchError, match="unsupported"):
        COMPANY_MODULE._fetch_url_text("https://example.com")
    assert response.read_calls == 0


def test_fetch_url_text_allows_parameterized_content_type(monkeypatch) -> None:
    homepage_research.clear_fetch_cache()
    _patch_dns(monkeypatch)

    def fake_open_url(_request: object, _timeout_sec: float) -> _FakeResponse:
        return _FakeResponse(
            "<html><body>Über uns</body></html>",
            content_type="text/html; charset=utf-8",
        )

    monkeypatch.setattr(homepage_research, "_open_url", fake_open_url)

    result = COMPANY_MODULE._fetch_url_text("https://example.com")

    assert result == ("https://example.com", "<html><body>Über uns</body></html>")


def test_fetch_url_text_negative_caches_oversize_payload(
    monkeypatch,
) -> None:
    homepage_research.clear_fetch_cache()
    _patch_dns(monkeypatch)
    opened_urls: list[str] = []

    def fake_open_url(request: object, _timeout_sec: float) -> _FakeResponse:
        request_url = str(getattr(request, "full_url"))
        opened_urls.append(request_url)
        return _FakeResponse("123456", final_url=request_url)

    monkeypatch.setattr(homepage_research, "_open_url", fake_open_url)

    with pytest.raises(homepage_research.HomepageFetchError, match="content_too_large"):
        homepage_research.fetch_url_text_result("https://example.com/large", max_bytes=5)

    with pytest.raises(homepage_research.HomepageFetchError) as exc_info:
        homepage_research.fetch_url_text_result(
            "https://example.com/large",
            max_bytes=5,
        )

    assert exc_info.value.error_code == "content_too_large"
    assert exc_info.value.from_negative_cache is True
    assert exc_info.value.suppressed_repeat_count == 1
    assert opened_urls == ["https://example.com/large"]


def test_fetch_url_text_uses_cache(monkeypatch) -> None:
    homepage_research.clear_fetch_cache()
    _patch_dns(monkeypatch)
    calls: list[str] = []

    def fake_open_url(_request: object, timeout_sec: float) -> _FakeResponse:
        calls.append(f"timeout={timeout_sec}")
        return _FakeResponse("<html><body>Über uns</body></html>")

    monkeypatch.setattr(homepage_research, "_open_url", fake_open_url)

    first = COMPANY_MODULE._fetch_url_text("example.com")
    second = COMPANY_MODULE._fetch_url_text("https://example.com")

    assert first == ("https://example.com", "<html><body>Über uns</body></html>")
    assert second == first
    assert calls == ["timeout=8.0"]


def test_run_website_research_records_invalid_url_event(monkeypatch) -> None:
    fake_st = SimpleNamespace(session_state={})
    monkeypatch.setattr(COMPANY_MODULE, "st", fake_st)

    COMPANY_MODULE._run_website_research(
        homepage_url="http://127.0.0.1:8501",
        topic_key=WEBSITE_TOPIC_ABOUT,
        plan=QuestionPlan(steps=[]),
    )

    assert fake_st.session_state[SSKey.COMPANY_WEBSITE_LAST_ERROR.value] == (
        "Homepage-Check fehlgeschlagen: Keine valide Homepage-URL gefunden. "
        "Nächste Aktion: öffentliche HTTPS-URL prüfen oder Arbeitgeberprofil unten manuell ausfüllen."
    )
    events = get_usage_events(fake_st.session_state)
    assert events[0]["event_type"] == "enrichment_timed"
    assert events[0]["metadata"]["stage"] == "homepage_research"
    assert events[0]["metadata"]["path"] == WEBSITE_TOPIC_ABOUT
    assert events[0]["metadata"]["status"] == "invalid_url"
    assert events[1]["metadata"] == {
        "topic_key": WEBSITE_TOPIC_ABOUT,
        "error_type": "invalid_url",
    }


def test_run_website_research_failure_preserves_existing_research(monkeypatch) -> None:
    existing_research = {
        WEBSITE_RESEARCH_SECTIONS: {
            WEBSITE_TOPIC_ABOUT: {
                WEBSITE_SECTION_SOURCE_URL: "https://example.com/about",
                WEBSITE_SECTION_SUMMARY: ["Bestehender Fund bleibt erhalten."],
            }
        }
    }
    fake_st = SimpleNamespace(
        session_state={SSKey.COMPANY_WEBSITE_RESEARCH.value: existing_research}
    )
    monkeypatch.setattr(COMPANY_MODULE, "st", fake_st)

    def _raise_research_error(**_kwargs: object) -> object:
        raise RuntimeError("network detail that must not be rendered")

    monkeypatch.setattr(
        COMPANY_MODULE,
        "_build_company_website_research",
        _raise_research_error,
    )

    COMPANY_MODULE._run_website_research(
        homepage_url="https://example.com",
        topic_key=WEBSITE_TOPIC_ABOUT,
        plan=QuestionPlan(steps=[]),
    )

    assert (
        fake_st.session_state[SSKey.COMPANY_WEBSITE_RESEARCH.value]
        == existing_research
    )
    error = fake_st.session_state[SSKey.COMPANY_WEBSITE_LAST_ERROR.value]
    assert "Homepage-Check fehlgeschlagen" in error
    assert "Nächste Aktion" in error
    assert "network detail" not in error


def test_build_company_website_research_returns_normalized_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payloads = {
        "https://example.com": (
            "https://example.com",
            """
            <html><body>
              <a href="/about">Über uns</a>
              <a href="/impressum">Impressum</a>
            </body></html>
            """,
        ),
        "https://example.com/about": (
            "https://example.com/about",
            """
            <html><body>
              <h1>Über uns</h1>
              <p>Unsere Vision ist nachhaltiges Wachstum mit Cloud Projekten.</p>
              <p>Acme wurde im Jahr 2001 gegründet.</p>
              <p>Heute arbeiten 745 Mitarbeitende an Kundennutzen.</p>
            </body></html>
            """,
        ),
    }

    def fake_fetch(url: str) -> tuple[str, str]:
        normalized_url = homepage_research.normalize_url(url)
        return payloads[normalized_url]

    monkeypatch.setattr(homepage_research, "fetch_url_text", fake_fetch)

    result = homepage_research.build_company_website_research(
        homepage_url="example.com",
        topic_key=WEBSITE_TOPIC_ABOUT,
        existing_research={
            WEBSITE_RESEARCH_SECTIONS: {
                "imprint": {
                    WEBSITE_SECTION_SOURCE_URL: "https://example.com/impressum",
                    WEBSITE_SECTION_SUMMARY: ["Impressum bleibt erhalten."],
                    WEBSITE_SECTION_FACTS: {},
                }
            }
        },
        open_questions=[
            {
                "id": "company_q_vision",
                "step": "company",
                "label": "Welche Vision verfolgt das Unternehmen?",
            }
        ],
    )

    research = result.research
    section = research[WEBSITE_RESEARCH_SECTIONS][WEBSITE_TOPIC_ABOUT]
    assert result.resolved_homepage_url == "https://example.com"
    assert result.resolved_topic_url == "https://example.com/about"
    assert research[WEBSITE_RESEARCH_HOMEPAGE_URL] == "https://example.com"
    assert "imprint" in research[WEBSITE_RESEARCH_SECTIONS]
    assert section[WEBSITE_SECTION_SOURCE_URL] == "https://example.com/about"
    assert section[WEBSITE_SECTION_FACTS]["Gegründet"] == "2001"
    assert section[WEBSITE_SECTION_FACTS]["Mitarbeitende (Hinweis)"] == "745"
    assert result.result_count == len(section[WEBSITE_SECTION_SUMMARY]) + len(
        section[WEBSITE_SECTION_FACTS]
    )
    assert research[WEBSITE_RESEARCH_OPEN_QUESTION_MATCHES][0]["question_id"] == (
        "company_q_vision"
    )


def test_build_company_website_research_rejects_invalid_homepage() -> None:
    with pytest.raises(homepage_research.HomepageResearchInvalidUrlError):
        homepage_research.build_company_website_research(
            homepage_url="http://127.0.0.1:8501",
            topic_key=WEBSITE_TOPIC_ABOUT,
            existing_research={},
            open_questions=[],
        )


def test_extract_imprint_facts_picks_essential_fields() -> None:
    imprint_html = """
    <html><body>
      <a href="mailto:info@example.com">info@example.com</a>
      <p>Firma: Example Consulting GmbH</p>
      <p>Musterstraße 12, 10115 Berlin</p>
      <p>Handelsregister HRB 12345</p>
      <p>Geschäftsführer: Erika Muster</p>
    </body></html>
    """
    text = COMPANY_MODULE._strip_html(imprint_html)

    facts = COMPANY_MODULE._extract_imprint_facts(imprint_html, text)

    assert facts["E-Mail"] == "info@example.com"
    assert "HRB 12345" in facts["Handelsregister"]
    assert "Erika Muster" in facts["Geschäftsführung/Vorstand"]
    assert "Musterstraße 12, 10115 Berlin" in facts["Anschrift"]


def test_derive_topic_facts_about_extracts_headcount_and_founding() -> None:
    text = (
        "Acme wurde im Jahr 2001 gegründet. "
        "Heute arbeiten 745000 Mitarbeiter weltweit an Cloud- und AI-Projekten."
    )

    facts = COMPANY_MODULE._derive_topic_facts("about", text, "")

    assert facts["Gegründet"] == "2001"
    assert facts["Mitarbeitende (Hinweis)"] == "745000"


def test_normalize_company_website_research_payload_accepts_legacy_fact_lists() -> None:
    payload = {
        "homepage_url": "https://example.com",
        "sections": {
            "about": {
                "source_url": "https://example.com/about",
                "summary": ["Example summary"],
                "facts": ["Gegründet: 2001", "Cloud delivery focus"],
                "fetched_at": "2026-06-10T00:00:00+00:00",
            }
        },
        "open_question_matches": [],
    }

    normalized = COMPANY_MODULE._normalize_company_website_research_payload(payload)
    research = CompanyWebsiteResearch.model_validate(normalized)

    facts = research.sections["about"].facts
    assert facts["Gegründet"] == "2001"
    assert facts["fact_2"] == "Cloud delivery focus"


def test_build_website_fact_candidates_maps_homepage_imprint_and_positioning() -> None:
    payload = {
        "homepage_url": "https://www.accenture.com/de-de",
        "sections": {
            "about": {
                "source_url": "https://www.accenture.com/de-de/about",
                "summary": [
                    "Accenture ist ein weltweit führendes Beratungsunternehmen für Technologie, Cloud, Data und AI mit Kundennutzen im Fokus."
                ],
                "facts": {"Mitarbeitende (Hinweis)": "745000"},
            },
            "vision_mission": {
                "summary": [
                    "Unsere Mission ist es, Kunden mit digitalen Lösungen und nachhaltigem Wachstum zu unterstützen."
                ],
                "facts": {},
            },
            "imprint": {
                "source_url": "https://www.accenture.com/de-de/impressum",
                "summary": ["Impressum der Accenture GmbH mit Sitz in 10115 Berlin."],
                "facts": {
                    "Firma": "Accenture GmbH",
                    "Anschrift": "Musterstraße 12, 10115 Berlin",
                    "E-Mail": "info@example.com",
                    "Geschäftsführung/Vorstand": "Erika Muster",
                },
            },
        },
        "open_question_matches": [],
    }

    candidates = homepage_research.build_website_fact_candidates(payload)
    by_key = {candidate["fact_key"]: candidate for candidate in candidates}

    assert by_key[FactKey.COMPANY_COMPANY_WEBSITE.value]["value"] == (
        "https://www.accenture.com/de-de"
    )
    assert by_key[FactKey.COMPANY_COMPANY_NAME.value]["value"] == "Accenture GmbH"
    assert by_key[FactKey.COMPANY_LOCATION_CITY.value]["value"] == "Berlin"
    assert FactKey.COMPANY_EMPLOYER_PITCH.value in by_key
    assert "Technologie" in by_key[
        FactKey.COMPANY_ROLE_RELEVANT_POSITIONING.value
    ]["value"]
    assert FactKey.INTERVIEW_CONTACTS.value not in by_key


def test_build_website_fact_candidates_skips_personal_contact_auto_mapping() -> None:
    payload = {
        "homepage_url": "https://example.com",
        "sections": {
            "imprint": {
                "summary": ["Kontakt: info@example.com. Geschäftsführer: Erika Muster."],
                "facts": {
                    "E-Mail": "info@example.com",
                    "Geschäftsführung/Vorstand": "Erika Muster",
                },
            }
        },
        "open_question_matches": [],
    }

    candidates = homepage_research.build_website_fact_candidates(payload)
    candidate_keys = {candidate["fact_key"] for candidate in candidates}

    assert FactKey.INTERVIEW_CONTACTS.value not in candidate_keys


def test_persist_homepage_fact_candidate_writes_fact_evidence_and_answer(
    monkeypatch,
) -> None:
    fake_st = SimpleNamespace(
        session_state={
            SSKey.ANSWERS.value: {},
            SSKey.ANSWER_META.value: {},
            SSKey.INTAKE_FACTS.value: {},
            SSKey.INTAKE_FACT_EVIDENCE.value: {},
        }
    )
    monkeypatch.setattr(COMPANY_MODULE, "st", fake_st)
    monkeypatch.setattr(state_module, "st", fake_st)

    COMPANY_MODULE._persist_homepage_fact_candidate(
        fact_key=FactKey.COMPANY_COMPANY_NAME,
        value="Accenture GmbH",
        candidate={
            "source_label": "Impressum",
            "confidence": 0.85,
            "evidence_snippet": "Firma: Accenture GmbH",
        },
    )

    assert fake_st.session_state[SSKey.ANSWERS.value][
        FactKey.COMPANY_COMPANY_NAME.value
    ] == "Accenture GmbH"
    assert fake_st.session_state[SSKey.INTAKE_FACTS.value] == {
        FactKey.COMPANY_COMPANY_NAME.value: "Accenture GmbH"
    }
    evidence = fake_st.session_state[SSKey.INTAKE_FACT_EVIDENCE.value][
        FactKey.COMPANY_COMPANY_NAME.value
    ]
    assert evidence["source_type"] == FactSourceType.HOMEPAGE.value
    assert evidence["source_label"] == "Impressum"
    assert evidence["confirmed"] is True
    assert evidence["resolution_status"] == FactResolutionStatus.CONFIRMED.value
    assert evidence["evidence_snippet"] == "Firma: Accenture GmbH"
    assert fake_st.session_state[SSKey.ANSWER_META.value][
        FactKey.COMPANY_COMPANY_NAME.value
    ]["touched"] is True


def test_persist_homepage_fact_candidate_records_conflict_without_overwrite(
    monkeypatch,
) -> None:
    fake_st = SimpleNamespace(
        session_state={
            SSKey.ANSWERS.value: {
                FactKey.COMPANY_COMPANY_NAME.value: "Existing GmbH"
            },
            SSKey.ANSWER_META.value: {},
            SSKey.INTAKE_FACTS.value: {
                FactKey.COMPANY_COMPANY_NAME.value: "Existing GmbH"
            },
            SSKey.INTAKE_FACT_EVIDENCE.value: {
                FactKey.COMPANY_COMPANY_NAME.value: {
                    "source_type": FactSourceType.MANUAL.value,
                    "source_label": "Manual input",
                    "confirmed": True,
                    "resolution_status": FactResolutionStatus.CONFIRMED.value,
                }
            },
        }
    )
    monkeypatch.setattr(COMPANY_MODULE, "st", fake_st)
    monkeypatch.setattr(state_module, "st", fake_st)

    result = COMPANY_MODULE._persist_homepage_fact_candidate(
        fact_key=FactKey.COMPANY_COMPANY_NAME,
        value="Accenture GmbH",
        candidate={
            "source_label": "Impressum",
            "confidence": 0.85,
            "evidence_snippet": "Firma: Accenture GmbH",
        },
    )

    assert result == "conflicted"
    assert fake_st.session_state[SSKey.ANSWERS.value][
        FactKey.COMPANY_COMPANY_NAME.value
    ] == "Existing GmbH"
    assert fake_st.session_state[SSKey.INTAKE_FACTS.value][
        FactKey.COMPANY_COMPANY_NAME.value
    ] == "Existing GmbH"
    evidence = fake_st.session_state[SSKey.INTAKE_FACT_EVIDENCE.value][
        FactKey.COMPANY_COMPANY_NAME.value
    ]
    assert evidence["source_type"] == FactSourceType.MANUAL.value
    secondary = evidence["secondary_evidence"]
    assert secondary[-1]["source_type"] == FactSourceType.HOMEPAGE.value
    assert secondary[-1]["resolution_status"] == (
        FactResolutionStatus.CONFLICTED.value
    )
    assert secondary[-1]["value"] == "Accenture GmbH"


def test_persist_homepage_fact_candidate_override_replaces_confirmed_value(
    monkeypatch,
) -> None:
    fake_st = SimpleNamespace(
        session_state={
            SSKey.ANSWERS.value: {
                FactKey.COMPANY_COMPANY_NAME.value: "Existing GmbH"
            },
            SSKey.ANSWER_META.value: {},
            SSKey.INTAKE_FACTS.value: {
                FactKey.COMPANY_COMPANY_NAME.value: "Existing GmbH"
            },
            SSKey.INTAKE_FACT_EVIDENCE.value: {
                FactKey.COMPANY_COMPANY_NAME.value: {
                    "source_type": FactSourceType.MANUAL.value,
                    "source_label": "Manual input",
                    "confirmed": True,
                    "resolution_status": FactResolutionStatus.CONFIRMED.value,
                }
            },
        }
    )
    monkeypatch.setattr(COMPANY_MODULE, "st", fake_st)
    monkeypatch.setattr(state_module, "st", fake_st)

    result = COMPANY_MODULE._persist_homepage_fact_candidate(
        fact_key=FactKey.COMPANY_COMPANY_NAME,
        value="Accenture GmbH",
        candidate={
            "source_label": "Impressum",
            "confidence": 0.85,
            "evidence_snippet": "Firma: Accenture GmbH",
        },
        override_conflict=True,
    )

    assert result == "saved"
    assert fake_st.session_state[SSKey.ANSWERS.value][
        FactKey.COMPANY_COMPANY_NAME.value
    ] == "Accenture GmbH"
    assert fake_st.session_state[SSKey.INTAKE_FACTS.value][
        FactKey.COMPANY_COMPANY_NAME.value
    ] == "Accenture GmbH"
    evidence = fake_st.session_state[SSKey.INTAKE_FACT_EVIDENCE.value][
        FactKey.COMPANY_COMPANY_NAME.value
    ]
    assert evidence["source_type"] == FactSourceType.HOMEPAGE.value
    assert evidence["source_label"] == "Impressum"
    assert evidence["resolution_status"] == FactResolutionStatus.CONFIRMED.value


def test_persist_homepage_fact_candidate_records_corroborating_evidence(
    monkeypatch,
) -> None:
    fake_st = SimpleNamespace(
        session_state={
            SSKey.ANSWERS.value: {
                FactKey.COMPANY_COMPANY_NAME.value: "Existing GmbH"
            },
            SSKey.ANSWER_META.value: {},
            SSKey.INTAKE_FACTS.value: {
                FactKey.COMPANY_COMPANY_NAME.value: "Existing GmbH"
            },
            SSKey.INTAKE_FACT_EVIDENCE.value: {
                FactKey.COMPANY_COMPANY_NAME.value: {
                    "source_type": FactSourceType.MANUAL.value,
                    "source_label": "Manual input",
                    "confirmed": True,
                    "resolution_status": FactResolutionStatus.CONFIRMED.value,
                }
            },
        }
    )
    monkeypatch.setattr(COMPANY_MODULE, "st", fake_st)
    monkeypatch.setattr(state_module, "st", fake_st)

    result = COMPANY_MODULE._persist_homepage_fact_candidate(
        fact_key=FactKey.COMPANY_COMPANY_NAME,
        value="Existing GmbH",
        candidate={
            "source_label": "Impressum",
            "confidence": 0.85,
            "evidence_snippet": "Firma: Existing GmbH",
        },
    )

    assert result == "corroborated"
    evidence = fake_st.session_state[SSKey.INTAKE_FACT_EVIDENCE.value][
        FactKey.COMPANY_COMPANY_NAME.value
    ]
    assert evidence["source_type"] == FactSourceType.MANUAL.value
    assert evidence["secondary_evidence"][-1]["source_type"] == (
        FactSourceType.HOMEPAGE.value
    )
    assert evidence["secondary_evidence"][-1]["resolution_status"] == (
        FactResolutionStatus.CONFIRMED.value
    )


def test_website_candidate_default_selection_protects_existing_values(
    monkeypatch,
) -> None:
    fake_st = SimpleNamespace(
        session_state={
            SSKey.ANSWERS.value: {
                FactKey.COMPANY_COMPANY_NAME.value: "Existing GmbH"
            },
            SSKey.INTAKE_FACTS.value: {},
        }
    )
    monkeypatch.setattr(state_module, "st", fake_st)

    assert (
        COMPANY_MODULE._default_select_website_candidate(
            FactKey.COMPANY_COMPANY_NAME.value,
            "Accenture GmbH",
        )
        is False
    )
    assert (
        COMPANY_MODULE._default_select_website_candidate(
            FactKey.COMPANY_COMPANY_NAME.value,
            "Existing GmbH",
        )
        is True
    )


def test_derive_insights_from_open_questions_retains_ids_and_labels() -> None:
    open_questions = [
        {
            "id": "company_q_1",
            "step": "company",
            "label": "Welche Vision verfolgt das Unternehmen?",
        }
    ]
    sections = {
        "vision_mission": {
            "summary": [
                "Unsere Vision ist nachhaltiges Wachstum mit klarer Mission für Kundenprojekte."
            ]
        }
    }

    insights = COMPANY_MODULE._derive_insights_from_open_questions(open_questions, sections)

    assert len(insights) == 1
    assert insights[0]["question_id"] == "company_q_1"
    assert insights[0]["question_label"] == "Welche Vision verfolgt das Unternehmen?"
    assert insights[0]["source_topic"] == "vision_mission"


def test_build_open_question_match_options_uses_human_labels_without_step_keys() -> None:
    options = COMPANY_MODULE._build_open_question_match_options(
        [
            {
                "question_id": "company_q_2",
                "step": "company",
                "question_label": "Welche Rechtsform hat das Unternehmen?",
                "source_topic": "imprint",
                "match_tokens": "rechtsform, unternehmen",
            }
        ]
    )

    assert len(options) == 1
    assert options[0]["display_label"] == (
        "Welche Rechtsform hat das Unternehmen? · Quelle: Impressum"
    )
    assert "[company]" not in options[0]["display_label"]
    assert "Treffer:" not in options[0]["display_label"]


def test_build_open_question_match_options_returns_empty_for_no_matches() -> None:
    assert COMPANY_MODULE._build_open_question_match_options([]) == []
