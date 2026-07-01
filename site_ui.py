# site_ui.py
from __future__ import annotations

import os
from dataclasses import dataclass, replace
from typing import Iterable, Mapping

import streamlit as st

from i18n import t, tr
from safe_html import escape_html_text, render_static_html

PROFILE_VALUE_NOT_PUBLISHED = "__profile_value_not_published__"
PROFILE_VALUE_NOT_CONFIGURED = "__profile_value_not_configured__"
PUBLIC_SITE_MODE_ENV_VAR = "CS_PUBLIC_SITE_MODE"
PUBLIC_SITE_MODE_DEVELOPMENT = "development"
PUBLIC_SITE_MODE_PRODUCTION = "production"
PUBLIC_SITE_MODES = (PUBLIC_SITE_MODE_DEVELOPMENT, PUBLIC_SITE_MODE_PRODUCTION)


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
    register_court: str = PROFILE_VALUE_NOT_CONFIGURED
    register_number: str = PROFILE_VALUE_NOT_CONFIGURED
    vat_id: str = PROFILE_VALUE_NOT_CONFIGURED


PROFILE_ENV_VARS: Mapping[str, str] = {
    "brand_name": "CS_PUBLIC_BRAND_NAME",
    "legal_entity": "CS_PUBLIC_LEGAL_ENTITY",
    "managing_director": "CS_PUBLIC_MANAGING_DIRECTOR",
    "street": "CS_PUBLIC_STREET",
    "postal_code": "CS_PUBLIC_POSTAL_CODE",
    "city": "CS_PUBLIC_CITY",
    "country": "CS_PUBLIC_COUNTRY",
    "email": "CS_PUBLIC_EMAIL",
    "phone": "CS_PUBLIC_PHONE",
    "website": "CS_PUBLIC_WEBSITE",
    "support_email": "CS_PUBLIC_SUPPORT_EMAIL",
    "privacy_email": "CS_PUBLIC_PRIVACY_EMAIL",
    "accessibility_email": "CS_PUBLIC_ACCESSIBILITY_EMAIL",
    "last_updated": "CS_PUBLIC_LAST_UPDATED",
    "dpo_name": "CS_PUBLIC_DPO_NAME",
    "register_court": "CS_PUBLIC_REGISTER_COURT",
    "register_number": "CS_PUBLIC_REGISTER_NUMBER",
    "vat_id": "CS_PUBLIC_VAT_ID",
}

PUBLIC_SITE_REQUIRED_PROFILE_FIELDS: tuple[str, ...] = (
    "brand_name",
    "legal_entity",
    "managing_director",
    "street",
    "postal_code",
    "city",
    "country",
    "email",
    "phone",
    "website",
    "support_email",
    "privacy_email",
    "accessibility_email",
    "last_updated",
    "dpo_name",
    "register_court",
    "register_number",
)

_PROFILE_MISSING_VALUES = {
    "",
    PROFILE_VALUE_NOT_PUBLISHED,
    PROFILE_VALUE_NOT_CONFIGURED,
}


class PublicSiteProfileConfigurationError(RuntimeError):
    """Raised when production public-site profile configuration is incomplete."""


def _env_profile_value(env_var: str) -> str | None:
    value = os.getenv(env_var)
    if value is None:
        return None
    return value.strip()


def build_site_profile_from_environment(
    *, defaults: SiteProfile | None = None
) -> SiteProfile:
    profile = defaults or SiteProfile()
    overrides = {
        field_name: value
        for field_name, env_var in PROFILE_ENV_VARS.items()
        if (value := _env_profile_value(env_var)) is not None
    }
    return replace(profile, **overrides)


def normalize_public_site_mode(mode: str | None = None) -> str:
    raw_mode = mode if mode is not None else os.getenv(PUBLIC_SITE_MODE_ENV_VAR)
    normalized = str(raw_mode or PUBLIC_SITE_MODE_DEVELOPMENT).strip().lower()
    if normalized not in PUBLIC_SITE_MODES:
        allowed = ", ".join(PUBLIC_SITE_MODES)
        raise PublicSiteProfileConfigurationError(
            f"{PUBLIC_SITE_MODE_ENV_VAR} must be one of: {allowed}"
        )
    return normalized


def is_public_site_production_mode(mode: str | None = None) -> bool:
    return normalize_public_site_mode(mode) == PUBLIC_SITE_MODE_PRODUCTION


def is_configured_profile_value(value: str) -> bool:
    return str(value).strip() not in _PROFILE_MISSING_VALUES


def missing_public_site_profile_fields(
    profile: SiteProfile,
    *,
    required_fields: tuple[str, ...] = PUBLIC_SITE_REQUIRED_PROFILE_FIELDS,
) -> tuple[str, ...]:
    return tuple(
        field_name
        for field_name in required_fields
        if not is_configured_profile_value(getattr(profile, field_name))
    )


def missing_public_site_profile_environment_fields(
    *,
    required_fields: tuple[str, ...] = PUBLIC_SITE_REQUIRED_PROFILE_FIELDS,
) -> tuple[str, ...]:
    return tuple(
        field_name
        for field_name in required_fields
        if _env_profile_value(PROFILE_ENV_VARS[field_name]) is None
    )


def validate_public_site_profile(
    profile: SiteProfile | None = None,
    *,
    mode: str | None = None,
) -> None:
    effective_mode = normalize_public_site_mode(mode)
    if effective_mode != PUBLIC_SITE_MODE_PRODUCTION:
        return

    active_profile = profile or PROFILE
    missing_fields = list(missing_public_site_profile_fields(active_profile))
    if profile is None:
        missing_fields.extend(missing_public_site_profile_environment_fields())
    missing_fields = list(dict.fromkeys(missing_fields))
    if not missing_fields:
        return

    missing_labels = ", ".join(
        f"{field_name} ({PROFILE_ENV_VARS[field_name]})"
        for field_name in missing_fields
    )
    raise PublicSiteProfileConfigurationError(
        "Public site production profile is incomplete. "
        f"Missing required fields: {missing_labels}."
    )


PROFILE = build_site_profile_from_environment()


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
    validate_public_site_profile()
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
