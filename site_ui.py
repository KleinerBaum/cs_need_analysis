# site_ui.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import streamlit as st


@dataclass(frozen=True)
class SiteProfile:
    brand_name: str = "Cognitive Staffing"
    legal_entity: str = "Cognitive Staffing"
    managing_director: str = "Bitte ergänzen"
    street: str = "Bitte ergänzen"
    postal_code: str = "Bitte ergänzen"
    city: str = "Bitte ergänzen"
    country: str = "Deutschland"
    email: str = "kontakt@cognitive-staffing.de"
    phone: str = "+49 ..."
    website: str = "https://recruitment-need-analysis.streamlit.app/"
    support_email: str = "support@cognitive-staffing.de"
    privacy_email: str = "datenschutz@cognitive-staffing.de"
    accessibility_email: str = "barrierefreiheit@cognitive-staffing.de"
    last_updated: str = "14.04.2026"
    dpo_name: str = "Bitte ergänzen, falls vorhanden"
    service_providers: tuple[str, ...] = (
        "Hosting / Deployment: Bitte ergänzen",
        "KI-Anbieter / LLM-Infrastruktur: Bitte ergänzen",
        "E-Mail / Support-Workflow: Bitte ergänzen",
        "Consent- / Cookie-Management: Bitte ergänzen",
    )


PROFILE = SiteProfile()


def inject_site_styles() -> None:
    st.markdown(
        """
        <style>
            .cs-hero {
                padding: 1.35rem 1.4rem;
                border: 1px solid color-mix(in srgb, var(--text-color, #111111) 18%, transparent);
                border-radius: 20px;
                background:
                    linear-gradient(
                        135deg,
                        color-mix(in srgb, var(--primary-color, #1565c0) 14%, transparent),
                        color-mix(in srgb, var(--secondary-background-color, #f3f4f6) 70%, transparent)
                    ),
                    linear-gradient(180deg, color-mix(in srgb, var(--background-color, #ffffff) 93%, transparent), transparent);
                margin-bottom: 1rem;
            }
            .cs-eyebrow {
                display: inline-block;
                padding: 0.22rem 0.60rem;
                border-radius: 999px;
                background: color-mix(in srgb, var(--primary-color, #1565c0) 18%, transparent);
                color: var(--primary-color, #1565c0);
                font-size: 0.78rem;
                font-weight: 700;
                letter-spacing: 0.04em;
                text-transform: uppercase;
                margin-bottom: 0.65rem;
            }
            .cs-title {
                font-size: 2.0rem;
                line-height: 1.15;
                font-weight: 800;
                color: var(--text-color, inherit);
                margin: 0 0 0.45rem 0;
            }
            .cs-lead {
                color: color-mix(in srgb, var(--text-color, #111111) 86%, transparent);
                font-size: 1.05rem;
                line-height: 1.6;
                margin: 0;
            }
            .cs-card {
                border: 1px solid color-mix(in srgb, var(--text-color, #111111) 12%, transparent);
                border-radius: 18px;
                background: color-mix(in srgb, var(--secondary-background-color, #f3f4f6) 72%, transparent);
                padding: 1rem 1rem 0.9rem 1rem;
                height: 100%;
                min-height: 170px;
            }
            .cs-card h4 {
                margin: 0 0 0.45rem 0;
                color: var(--text-color, inherit);
                font-size: 1.02rem;
                line-height: 1.3;
            }
            .cs-card p {
                margin: 0;
                color: color-mix(in srgb, var(--text-color, #111111) 86%, transparent);
                font-size: 0.96rem;
                line-height: 1.55;
            }
            .cs-callout {
                border-left: 5px solid var(--primary-color, #1e88e5);
                background: color-mix(in srgb, var(--primary-color, #1e88e5) 12%, transparent);
                border-radius: 14px;
                padding: 0.95rem 1rem;
                margin: 0.75rem 0 1rem 0;
            }
            .cs-callout-warning {
                border-left-color: #f9a825;
                background: color-mix(in srgb, #f9a825 16%, transparent);
            }
            .cs-callout-success {
                border-left-color: #2e7d32;
                background: color-mix(in srgb, #2e7d32 16%, transparent);
            }
            .cs-meta {
                color: color-mix(in srgb, var(--text-color, #111111) 70%, transparent);
                font-size: 0.9rem;
                margin-top: -0.15rem;
                margin-bottom: 1.2rem;
            }
            .cs-cta {
                border: 1px solid color-mix(in srgb, var(--text-color, #111111) 12%, transparent);
                border-radius: 18px;
                padding: 1.1rem 1.1rem 1rem 1.1rem;
                background: linear-gradient(
                    135deg,
                    color-mix(in srgb, var(--primary-color, #1976d2) 12%, transparent),
                    color-mix(in srgb, var(--secondary-background-color, #f3f4f6) 72%, transparent)
                );
                margin-top: 1rem;
            }
            .cs-small {
                color: color-mix(in srgb, var(--text-color, #111111) 70%, transparent);
                font-size: 0.88rem;
                line-height: 1.5;
            }
            .block-container {
                max-width: none;
                padding-top: 1rem;
                padding-bottom: 2rem;
                padding-left: clamp(1rem, 2vw, 2rem);
                padding-right: clamp(1rem, 2vw, 2rem);
            }
            @media (max-width: 900px) {
                .block-container {
                    padding-left: 0.9rem;
                    padding-right: 0.9rem;
                }
                .cs-title {
                    line-height: 1.2;
                }
                .cs-hero {
                    padding: 1rem;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero(title: str, lead: str, eyebrow: str = "Cognitive Staffing") -> None:
    st.markdown(
        f"""
        <div class="cs-hero">
            <div class="cs-eyebrow">{eyebrow}</div>
            <div class="cs-title">{title}</div>
            <p class="cs-lead">{lead}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_meta_line(text: str) -> None:
    st.markdown(f'<div class="cs-meta">{text}</div>', unsafe_allow_html=True)


def render_cards(cards: Iterable[dict[str, str]], columns: int = 3) -> None:
    cards = list(cards)
    if not cards:
        return

    for start in range(0, len(cards), columns):
        cols = st.columns(columns)
        chunk = cards[start : start + columns]
        for col, card in zip(cols, chunk):
            with col:
                st.markdown(
                    f"""
                    <div class="cs-card">
                        <h4>{card["title"]}</h4>
                        <p>{card["body"]}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def render_callout(title: str, body: str, tone: str = "info") -> None:
    extra = ""
    if tone == "warning":
        extra = " cs-callout-warning"
    elif tone == "success":
        extra = " cs-callout-success"

    st.markdown(
        f"""
        <div class="cs-callout{extra}">
            <strong>{title}</strong><br>
            {body}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_cta(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="cs-cta">
            <strong>{title}</strong><br><br>
            {body}
        </div>
        """,
        unsafe_allow_html=True,
    )
