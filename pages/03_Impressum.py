from __future__ import annotations

from components.layout import SectionBlock, render_standard_page
from i18n import tr


PREFIX = "public_pages.imprint"


def _copy(key: str, **params: object) -> str:
    return tr(f"{PREFIX}.{key}", **params)


render_standard_page(
    eyebrow=_copy("eyebrow"),
    title=_copy("title"),
    intro=[_copy("intro.0"), _copy("intro.1")],
    sections=[
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
    placeholders=[
        (
            _copy("placeholders.legal_info.heading"),
            [
                _copy("placeholders.legal_info.items.company_address"),
                _copy("placeholders.legal_info.items.registry"),
            ],
        )
    ],
    trust_heading=_copy("trust.heading"),
    trust_details=[_copy("trust.details.0")],
    legal_template=True,
    footer_classification=_copy("footer_classification"),
)
