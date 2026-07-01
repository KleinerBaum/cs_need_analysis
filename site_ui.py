# site_ui.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import streamlit as st

from i18n import t, tr
from safe_html import escape_html_text, render_static_html

PROFILE_VALUE_NOT_PUBLISHED = "__profile_value_not_published__"
PROFILE_VALUE_NOT_CONFIGURED = "__profile_value_not_configured__"


@dataclass(frozen=True)
class SiteProfile:
    brand_name: str = "Cognitive Staffing"
    legal_entity: str = "Cognitive Staffing"
    managing_director: str = PROFILE_VALUE_NOT_PUBLISHED
    street: str = PROFILE_VALUE_NOT_PUBLISHED
    postal_code: str = PROFILE_VALUE_NOT_PUBLISHED
    city: str = PROFILE_VALUE_NOT_PUBLISHED
    country: str = "Deutschland"
    email: str = "kontakt@cognitive-staffing.de"
    phone: str = PROFILE_VALUE_NOT_PUBLISHED
    website: str = "https://recruitment-need-analysis.streamlit.app/"
    support_email: str = "support@cognitive-staffing.de"
    privacy_email: str = "datenschutz@cognitive-staffing.de"
    accessibility_email: str = "barrierefreiheit@cognitive-staffing.de"
    last_updated: str = "14.04.2026"
    dpo_name: str = PROFILE_VALUE_NOT_CONFIGURED


PROFILE = SiteProfile()


def profile_last_updated_label() -> str:
    return tr("common.last_updated", date=PROFILE.last_updated)


def localized_profile_value(value: str) -> str:
    if value == PROFILE_VALUE_NOT_PUBLISHED:
        return tr("common.not_published")
    if value == PROFILE_VALUE_NOT_CONFIGURED:
        return tr("common.not_configured")
    if value == "Deutschland":
        return tr("common.country_germany")
    return value


def inject_site_styles() -> None:
    render_static_html(
        """
        <style>
            .cs-hero {
                padding: 1.35rem 1.4rem;
                border: 1px solid color-mix(in srgb, var(--text-color, #334155) 18%, transparent);
                border-radius: 20px;
                background:
                    linear-gradient(
                        135deg,
                        color-mix(in srgb, var(--primary-color, #2563EB) 14%, transparent),
                        color-mix(in srgb, var(--secondary-background-color, #f3f4f6) 70%, transparent)
                    ),
                    linear-gradient(180deg, color-mix(in srgb, var(--background-color, #ffffff) 93%, transparent), transparent);
                margin-bottom: 1rem;
            }
            .cs-eyebrow {
                display: inline-block;
                padding: 0.22rem 0.60rem;
                border-radius: 999px;
                background: color-mix(in srgb, var(--primary-color, #2563EB) 18%, transparent);
                color: var(--primary-color, #2563EB);
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
                color: var(--text-color, #16324F);
                margin: 0 0 0.45rem 0;
            }
            .cs-lead {
                color: color-mix(in srgb, var(--text-color, #334155) 86%, transparent);
                font-size: 1.05rem;
                line-height: 1.6;
                margin: 0;
            }
            .cs-card {
                border: 1px solid color-mix(in srgb, var(--text-color, #334155) 12%, transparent);
                border-radius: 18px;
                background: color-mix(in srgb, var(--secondary-background-color, #f3f4f6) 72%, transparent);
                padding: 1rem 1rem 0.9rem 1rem;
                height: 100%;
                min-height: 170px;
            }
            .cs-card h4 {
                margin: 0 0 0.45rem 0;
                color: var(--text-color, #16324F);
                font-size: 1.02rem;
                line-height: 1.3;
            }
            .cs-card p {
                margin: 0;
                color: color-mix(in srgb, var(--text-color, #334155) 86%, transparent);
                font-size: 0.96rem;
                line-height: 1.55;
            }
            .cs-callout {
                border-left: 5px solid var(--primary-color, #2563EB);
                background: color-mix(in srgb, var(--primary-color, #2563EB) 12%, transparent);
                border-radius: 14px;
                padding: 0.95rem 1rem;
                margin: 0.75rem 0 1rem 0;
            }
            .cs-callout-warning {
                border-left-color: #F59E0B;
                background: color-mix(in srgb, #F59E0B 16%, transparent);
            }
            .cs-callout-success {
                border-left-color: #0F766E;
                background: color-mix(in srgb, #0F766E 16%, transparent);
            }
            .cs-meta {
                color: color-mix(in srgb, var(--text-color, #334155) 70%, transparent);
                font-size: 0.9rem;
                margin-top: -0.15rem;
                margin-bottom: 1.2rem;
            }
            .cs-cta {
                border: 1px solid color-mix(in srgb, var(--text-color, #334155) 12%, transparent);
                border-radius: 18px;
                padding: 1.1rem 1.1rem 1rem 1.1rem;
                background: linear-gradient(
                    135deg,
                    color-mix(in srgb, var(--primary-color, #2563EB) 12%, transparent),
                    color-mix(in srgb, var(--secondary-background-color, #f3f4f6) 72%, transparent)
                );
                margin-top: 1rem;
            }
            .cs-small {
                color: color-mix(in srgb, var(--text-color, #334155) 70%, transparent);
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
        streamlit_module=st,
    )


def render_hero(title: str, lead: str, eyebrow: str = "Cognitive Staffing") -> None:
    render_static_html(
        f"""
        <div class="cs-hero">
            <div class="cs-eyebrow">{escape_html_text(t(eyebrow))}</div>
            <div class="cs-title">{escape_html_text(t(title))}</div>
            <p class="cs-lead">{escape_html_text(t(lead))}</p>
        </div>
        """,
        streamlit_module=st,
    )


def render_meta_line(text: str) -> None:
    render_static_html(
        f'<div class="cs-meta">{escape_html_text(t(text))}</div>',
        streamlit_module=st,
    )


def render_cards(cards: Iterable[dict[str, str]], columns: int = 3) -> None:
    cards = list(cards)
    if not cards:
        return

    for start in range(0, len(cards), columns):
        cols = st.columns(columns)
        chunk = cards[start : start + columns]
        for col, card in zip(cols, chunk):
            with col:
                render_static_html(
                    f"""
                    <div class="cs-card">
                        <h4>{escape_html_text(t(card["title"]))}</h4>
                        <p>{escape_html_text(t(card["body"]))}</p>
                    </div>
                    """,
                    streamlit_module=st,
                )


def render_callout(title: str, body: str, tone: str = "info") -> None:
    extra = ""
    if tone == "warning":
        extra = " cs-callout-warning"
    elif tone == "success":
        extra = " cs-callout-success"

    render_static_html(
        f"""
        <div class="cs-callout{extra}">
            <strong>{escape_html_text(t(title))}</strong><br>
            {escape_html_text(t(body))}
        </div>
        """,
        streamlit_module=st,
    )


def render_cta(title: str, body: str) -> None:
    render_static_html(
        f"""
        <div class="cs-cta">
            <strong>{escape_html_text(t(title))}</strong><br><br>
            {escape_html_text(t(body))}
        </div>
        """,
        streamlit_module=st,
    )
