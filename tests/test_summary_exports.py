from __future__ import annotations

import base64

from document_preview import (
    article_preview_html,
    document_preview_shell,
    markdown_article_preview_html,
    pdf_preview_html,
)
from schemas import (
    BooleanSearchChannelQueries,
    BooleanSearchPack,
    JobAdExtract,
    VacancyBrief,
    VacancyStructuredData,
)
from summary_exports import (
    boolean_search_pack_to_markdown,
    brief_to_markdown,
    build_summary_input_fingerprint,
)


def _fingerprint(*, answers: dict[str, object]) -> str:
    return build_summary_input_fingerprint(
        job=JobAdExtract(
            job_title="Data Engineer",
            company_name="ACME GmbH",
            location_country="DE",
        ),
        answers=answers,
        selected_role_tasks=["Build data products"],
        selected_skills=["Python", "SQL"],
        selected_benefits=["Mentoring"],
        esco_occupation_selected={"uri": "uri:occ:1", "title": "Data Engineer"},
        esco_match_explainability={
            "reason": "Anker bestätigt",
            "confidence": "high",
            "provenance": ["exact label match"],
        },
        esco_selected_skills_must=[{"uri": "uri:skill:python", "title": "Python"}],
        esco_selected_skills_nice=[],
    )


def test_build_summary_input_fingerprint_is_stable_and_sensitive_to_inputs() -> None:
    baseline = _fingerprint(answers={"team_size": 5})

    assert baseline == _fingerprint(answers={"team_size": 5})
    assert baseline != _fingerprint(answers={"team_size": 10})
    assert len(baseline) == 64


def test_brief_to_markdown_exports_primary_sections() -> None:
    brief = VacancyBrief(
        one_liner="One line",
        hiring_context="Context",
        role_summary="Summary",
        top_responsibilities=["Build pipelines"],
        must_have=["Python"],
        nice_to_have=["SQL"],
        dealbreakers=["No cloud experience"],
        interview_plan=["HR screen"],
        evaluation_rubric=["Technical depth"],
        risks_open_questions=["Budget open"],
        job_ad_draft="Draft text",
        structured_data=VacancyStructuredData(
            job_extract={"job_title": "Data Engineer"},
            answers={},
        ),
    )

    markdown = brief_to_markdown(brief)

    assert markdown.startswith("# Recruiting Brief – Data Engineer")
    assert "## Top Responsibilities\n- Build pipelines" in markdown
    assert "## Stellenanzeigenentwurf (DE)\nDraft text" in markdown


def test_boolean_search_pack_to_markdown_formats_channel_queries() -> None:
    channel = BooleanSearchChannelQueries(
        broad=["site:linkedin.com/in Python"],
        focused=[],
        fallback=["Data Engineer Berlin"],
    )
    pack = BooleanSearchPack(
        role_title="Data Engineer",
        target_locations=["Berlin"],
        seniority_terms=["Senior"],
        must_have_terms=["Python"],
        exclusion_terms=[],
        google=channel,
        linkedin=channel,
        xing=channel,
        channel_limitations=["LinkedIn search syntax varies"],
        usage_notes=["Start broad, then tighten"],
    )

    markdown = boolean_search_pack_to_markdown(pack)

    assert markdown.startswith("# Suchstrings")
    assert "**Role Title:** Data Engineer" in markdown
    assert "- `site:linkedin.com/in Python`" in markdown
    assert "### Focused\n- —" in markdown
    assert "## Usage Notes\n- Start broad, then tighten" in markdown


def test_markdown_article_preview_html_escapes_hostile_markdown() -> None:
    html = markdown_article_preview_html(
        "# <script>alert(1)</script>\n\n"
        'Intro <img src=x onerror="alert(1)">\n\n'
        '## <svg onload="alert(1)"></svg>\n\n'
        '- <a href="javascript:alert(1)">bad</a>'
    )

    assert "<script>" not in html
    assert "<img" not in html
    assert "<svg" not in html
    assert "<a href=" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;" in html
    assert "&lt;svg onload=&quot;alert(1)&quot;&gt;&lt;/svg&gt;" in html
    assert "&lt;a href=&quot;javascript:alert(1)&quot;&gt;bad&lt;/a&gt;" in html


def test_article_preview_html_escapes_hostile_structured_fields() -> None:
    html = article_preview_html(
        headline='<script>alert("headline")</script>',
        intro='<img src=x onerror="alert(1)">',
        sections=[
            (
                '<svg onload="alert(1)"></svg>',
                ['<a href="javascript:alert(1)">bad</a>'],
            )
        ],
        closing=['<iframe src="javascript:alert(1)"></iframe>'],
    )

    assert "<script>" not in html
    assert "<img" not in html
    assert "<svg" not in html
    assert "<a href=" not in html
    assert "<iframe" not in html
    assert "&lt;script&gt;alert(&quot;headline&quot;)&lt;/script&gt;" in html
    assert "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;" in html
    assert "&lt;svg onload=&quot;alert(1)&quot;&gt;&lt;/svg&gt;" in html
    assert "&lt;a href=&quot;javascript:alert(1)&quot;&gt;bad&lt;/a&gt;" in html
    assert "&lt;iframe src=&quot;javascript:alert(1)&quot;&gt;&lt;/iframe&gt;" in html


def test_document_preview_shell_escapes_title_and_rejects_css_injection() -> None:
    html = document_preview_shell(
        "<article>trusted</article>",
        title="<script>alert(1)</script>",
        accent_color='red; background-image: url("javascript:alert(1)")',
    )

    assert "<script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "javascript:alert" not in html
    assert 'background-image: url("javascript:alert(1)")' not in html
    assert "border-top: 5px solid #2563eb;" in html


def test_pdf_preview_html_uses_base64_data_uri_without_raw_payload() -> None:
    html = pdf_preview_html(b"%PDF-1.4\n<script>alert(1)</script>\n%%EOF\n")

    assert html.startswith(
        '<iframe class="cs-document-pdf-frame" title="Dokumentvorschau" '
        'src="data:application/pdf;base64,'
    )
    assert "<script>" not in html
    assert "%%EOF" not in html


def test_markdown_article_preview_html_accepts_normalized_logo_payload() -> None:
    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO5vS3wAAAAASUVORK5CYII="
    )
    html = markdown_article_preview_html(
        "# Data Engineer",
        logo_payload={
            "name": "brand.png",
            "mime_type": "image/png",
            "extension": ".png",
            "byte_size": len(png_bytes),
            "width_px": 1,
            "height_px": 1,
            "bytes": png_bytes,
        },
    )

    assert "data:image/png;base64," in html
    assert base64.b64encode(png_bytes).decode("ascii") in html
