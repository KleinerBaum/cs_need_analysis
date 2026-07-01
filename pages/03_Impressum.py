from __future__ import annotations

from components.layout import SectionBlock, render_standard_page
from i18n import tr
from site_ui import (
    PROFILE,
    is_configured_profile_value,
    is_public_site_production_mode,
    localized_profile_value,
    validate_public_site_profile,
)


PREFIX = "public_pages.imprint"


def _copy(key: str, **params: object) -> str:
    return tr(f"{PREFIX}.{key}", **params)


def _vat_id_line() -> str:
    if not is_configured_profile_value(PROFILE.vat_id):
        return ""
    return "\n" + _copy("sections.provider_profile.vat_id_line", vat_id=PROFILE.vat_id)


def _provider_profile_body() -> str:
    return _copy(
        "sections.provider_profile.body",
        legal_entity=localized_profile_value(PROFILE.legal_entity),
        managing_director=localized_profile_value(PROFILE.managing_director),
        street=localized_profile_value(PROFILE.street),
        postal_code=localized_profile_value(PROFILE.postal_code),
        city=localized_profile_value(PROFILE.city),
        country=localized_profile_value(PROFILE.country),
        email=localized_profile_value(PROFILE.email),
        phone=localized_profile_value(PROFILE.phone),
        website=localized_profile_value(PROFILE.website),
        register_court=localized_profile_value(PROFILE.register_court),
        register_number=localized_profile_value(PROFILE.register_number),
        vat_id_line=_vat_id_line(),
    )


validate_public_site_profile()
_IS_PRODUCTION = is_public_site_production_mode()
_INTRO_PREFIX = "intro_production" if _IS_PRODUCTION else "intro"

render_standard_page(
    eyebrow=_copy("eyebrow"),
    title=_copy("title"),
    intro=[_copy(f"{_INTRO_PREFIX}.0"), _copy(f"{_INTRO_PREFIX}.1")],
    sections=[
        SectionBlock(
            _copy("sections.provider_profile.heading"),
            [_provider_profile_body()],
        ),
        *[
            SectionBlock(
                _copy(f"sections.{key}.heading"),
                [_copy(f"sections.{key}.body")],
            )
            for key in (
                "scope",
                "required_info",
                "responsibilities",
                "contact_paths",
                "version_note",
            )
        ],
    ],
    missing_legal_inputs=[] if _IS_PRODUCTION else [
        (
            _copy("missing_inputs.legal_info.heading"),
            [
                _copy("missing_inputs.legal_info.items.company_address"),
                _copy("missing_inputs.legal_info.items.registry"),
            ],
        )
    ],
    trust_heading=_copy("trust.heading"),
    trust_details=[_copy("trust.details.0")],
    legal_review_required=not _IS_PRODUCTION,
    footer_classification=_copy(
        "footer_classification_production" if _IS_PRODUCTION else "footer_classification"
    ),
)
