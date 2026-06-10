from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace

import pytest

import homepage_research
from constants import SSKey, WEBSITE_TOPIC_ABOUT
from schemas import CompanyWebsiteResearch, QuestionPlan
from usage_events import get_usage_events

COMPANY_PATH = Path(__file__).resolve().parents[1] / "wizard_pages" / "02_company.py"
SPEC = spec_from_file_location("wizard_pages.page_02_company", COMPANY_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load company module")
COMPANY_MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(COMPANY_MODULE)  # type: ignore[attr-defined]


class _FakeHeaders:
    def __init__(self, content_type: str = "text/html") -> None:
        self._content_type = content_type

    def get_content_charset(self) -> str:
        return "utf-8"

    def get_content_type(self) -> str:
        return self._content_type


class _FakeResponse:
    def __init__(
        self,
        payload: str,
        *,
        final_url: str = "https://example.com",
        content_type: str = "text/html",
    ) -> None:
        self._payload = payload.encode("utf-8")
        self._final_url = final_url
        self.headers = _FakeHeaders(content_type)

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def geturl(self) -> str:
        return self._final_url

    def read(self, _size: int = -1) -> bytes:
        return self._payload


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


def test_fetch_url_text_rejects_unsupported_content_type(monkeypatch) -> None:
    homepage_research.clear_fetch_cache()

    def fake_urlopen(_request: object, timeout: float) -> _FakeResponse:
        assert timeout == 8.0
        return _FakeResponse("%PDF-1.7", content_type="application/pdf")

    monkeypatch.setattr(homepage_research, "urlopen", fake_urlopen)

    with pytest.raises(homepage_research.HomepageFetchError, match="unsupported"):
        COMPANY_MODULE._fetch_url_text("https://example.com")


def test_fetch_url_text_uses_cache(monkeypatch) -> None:
    homepage_research.clear_fetch_cache()
    calls: list[str] = []

    def fake_urlopen(_request: object, timeout: float) -> _FakeResponse:
        calls.append(f"timeout={timeout}")
        return _FakeResponse("<html><body>Über uns</body></html>")

    monkeypatch.setattr(homepage_research, "urlopen", fake_urlopen)

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
        "Keine valide Homepage-URL gefunden."
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
