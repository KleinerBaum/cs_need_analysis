"""Standard page layout helpers for static information and legal templates."""

from __future__ import annotations

from typing import Iterable, Mapping
from collections.abc import Sequence
from dataclasses import dataclass

import streamlit as st

from constants import APP_NAME, APP_TAGLINE
from i18n import (
    LANGUAGE_WIDGET_KEY_SIDEBAR,
    bootstrap_public_page,
    render_language_toggle,
    t,
    tr,
)
from safe_html import escape_html_text, render_static_html


@dataclass(frozen=True)
class SectionBlock:
    heading: str
    body: Sequence[str]


def load_css(path: str = "styles/theme.css") -> None:
    with open(path, "r", encoding="utf-8") as css_file:
        render_static_html(f"<style>{css_file.read()}</style>", streamlit_module=st)


def render_page_header(title: str, intro: str, eyebrow: str | None = None) -> None:
    eyebrow_html = (
        f'<div class="cs-eyebrow">{escape_html_text(t(eyebrow))}</div>'
        if eyebrow
        else ""
    )
    render_static_html(
        f"""
        <section class="cs-hero">
            {eyebrow_html}
            <h1>{escape_html_text(t(title))}</h1>
            <p>{escape_html_text(t(intro))}</p>
        </section>
        """,
        streamlit_module=st,
    )


def render_sections(sections: Iterable[Mapping[str, str]]) -> None:
    for section in sections:
        render_static_html(
            f"""
            <section class="cs-section">
                <h2>{escape_html_text(t(section['title']))}</h2>
                <p>{escape_html_text(t(section['body']))}</p>
            </section>
            """,
            streamlit_module=st,
        )


def render_legal_note(note: str) -> None:
    st.info(str(t(note)))


def render_page_footer() -> None:
    st.caption(f"{APP_NAME} · {t(APP_TAGLINE)}")


def render_hero(*, eyebrow: str, title: str, intro: Sequence[str]) -> None:
    st.caption(str(t(eyebrow)))
    st.title(str(t(title)))
    for paragraph in intro:
        text = paragraph.strip()
        if text:
            st.markdown(str(t(text)))


def render_section_block(*, heading: str, paragraphs: Sequence[str]) -> None:
    st.markdown(f"### {t(heading)}")
    for paragraph in paragraphs:
        text = paragraph.strip()
        if text:
            st.markdown(str(t(text)))


def render_placeholder_block(*, heading: str, missing_inputs: Sequence[str]) -> None:
    visible_items = [item.strip() for item in missing_inputs if item.strip()]
    if not visible_items:
        return
    st.warning(
        tr("public_pages.legal_placeholder_title")
        + "\n\n"
        + f"**{t(heading)}**\n"
        + "\n".join(f"- {t(item)}" for item in visible_items)
    )


def render_trust_info_block(
    *, heading: str, details: Sequence[str], legal_template: bool
) -> None:
    lines = [item.strip() for item in details if item.strip()]
    if legal_template:
        lines.insert(0, tr("public_pages.legal_template_notice"))
    if not lines:
        return
    st.info(f"**{t(heading)}**\n\n" + "\n".join(f"- {t(line)}" for line in lines))


def render_footer(*, product_name: str, classification: str) -> None:
    st.divider()
    st.caption(f"{product_name} · {t(classification)}")


def render_standard_page(
    *,
    eyebrow: str,
    title: str,
    intro: Sequence[str],
    sections: Sequence[SectionBlock],
    footer_classification: str,
    product_name: str = "Cognitive Staffing – Vacancy Intake Wizard",
    trust_heading: str | None = None,
    trust_details: Sequence[str] = (),
    legal_template: bool = False,
    placeholders: Sequence[tuple[str, Sequence[str]]] = (),
) -> None:
    bootstrap_public_page(page_title=title, page_icon="📄")
    load_css()
    render_language_toggle(location="sidebar", key=LANGUAGE_WIDGET_KEY_SIDEBAR)
    render_hero(eyebrow=eyebrow, title=title, intro=intro)
    for section in sections:
        render_section_block(heading=section.heading, paragraphs=section.body)
    for heading, missing_inputs in placeholders:
        render_placeholder_block(heading=heading, missing_inputs=missing_inputs)
    if trust_heading:
        render_trust_info_block(
            heading=trust_heading,
            details=trust_details,
            legal_template=legal_template,
        )
    render_footer(product_name=product_name, classification=footer_classification)
