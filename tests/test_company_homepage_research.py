from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

COMPANY_PATH = Path(__file__).resolve().parents[1] / "wizard_pages" / "02_company.py"
SPEC = spec_from_file_location("wizard_pages.page_02_company", COMPANY_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load company module")
COMPANY_MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(COMPANY_MODULE)  # type: ignore[attr-defined]


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

    assert any("Gegründet" in fact and "2001" in fact for fact in facts)
    assert any("Mitarbeitende" in fact and "745000" in fact for fact in facts)


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
