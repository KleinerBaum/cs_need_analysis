"""Standard page layout helpers for static information and legal templates."""

from __future__ import annotations

from typing import Iterable, Mapping
from collections.abc import Sequence
from dataclasses import dataclass

import streamlit as st

from config.constants import APP_NAME, APP_TAGLINE

@dataclass(frozen=True)
class SectionBlock:
    heading: str
    body: Sequence[str]

def load_css(path: str = "styles/theme.css") -> None:
    with open(path, "r", encoding="utf-8") as css_file:
        st.markdown(f"<style>{css_file.read()}</style>", unsafe_allow_html=True)


def render_page_header(title: str, intro: str, eyebrow: str | None = None) -> None:
    eyebrow_html = f'<div class="cs-eyebrow">{eyebrow}</div>' if eyebrow else ""
    st.markdown(
        f"""
        <section class="cs-hero">
            {eyebrow_html}
            <h1>{title}</h1>
            <p>{intro}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_sections(sections: Iterable[Mapping[str, str]]) -> None:
    for section in sections:
        st.markdown(
            f"""
            <section class="cs-section">
                <h2>{section['title']}</h2>
                <p>{section['body']}</p>
            </section>
            """,
            unsafe_allow_html=True,
        )


def render_legal_note(note: str) -> None:
    st.info(note)


def render_page_footer() -> None:
    st.caption(f"{APP_NAME} · {APP_TAGLINE}")

def render_hero(*, eyebrow: str, title: str, intro: Sequence[str]) -> None:
    st.caption(eyebrow)
    st.title(title)
    for paragraph in intro:
        text = paragraph.strip()
        if text:
            st.markdown(text)


def render_section_block(*, heading: str, paragraphs: Sequence[str]) -> None:
    st.markdown(f"### {heading}")
    for paragraph in paragraphs:
        text = paragraph.strip()
        if text:
            st.markdown(text)


def render_placeholder_block(*, heading: str, missing_inputs: Sequence[str]) -> None:
    visible_items = [item.strip() for item in missing_inputs if item.strip()]
    if not visible_items:
        return
    st.warning(
        "🟧 **Platzhalter – Fachinput fehlt**\n\n"
        f"**{heading}**\n" + "\n".join(f"- {item}" for item in visible_items)
    )


def render_trust_info_block(
    *, heading: str, details: Sequence[str], legal_template: bool
) -> None:
    lines = [item.strip() for item in details if item.strip()]
    if legal_template:
        lines.insert(
            0,
            "Diese Seite ist eine Vorlage und wird erst nach rechtlicher Prüfung verbindlich.",
        )
    if not lines:
        return
    st.info(f"**{heading}**\n\n" + "\n".join(f"- {line}" for line in lines))


def render_footer(*, product_name: str, classification: str) -> None:
    st.divider()
    st.caption(f"{product_name} · {classification}")


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
