from __future__ import annotations

import app
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def test_public_sidebar_links_exclude_legal_pages() -> None:
    links = app._public_sidebar_links()
    labels = [label for _, label in links]

    assert labels == [
        "Recruitment Need Analysis",
        "Unsere Kompetenzen",
        "Ueber Cognitive Staffing",
        "Kontakt",
    ]


def test_public_sidebar_link_targets_exist_and_are_allowed() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    for page_path, _ in app._public_sidebar_links():
        assert page_path == "app.py" or page_path.startswith("pages/")
        assert page_path.endswith(".py")
        assert (repo_root / page_path).is_file(), f"Missing public sidebar target: {page_path}"


def test_kontakt_legal_links_cover_all_policy_pages() -> None:
    kontakt_path = Path(__file__).resolve().parents[1] / "pages" / "15_Kontakt.py"
    spec = spec_from_file_location("pages.page_15_kontakt_for_tests", kontakt_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load Kontakt page module")
    kontakt_module = module_from_spec(spec)
    spec.loader.exec_module(kontakt_module)  # type: ignore[attr-defined]

    links = kontakt_module._legal_policy_links()
    labels = [label for _, label in links]

    assert labels == [
        "Impressum",
        "Datenschutzrichtlinie",
        "Nutzungsbedingungen",
        "Cookie Policy Settings",
        "Erklärung zur Barrierefreiheit",
    ]
