from __future__ import annotations

import ast
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

from app import SIDEBAR_PAGE_LINKS
from components.sidebar import render_sidebar
from config.preferences import (
    PAGE_DEFS,
    PAGE_ROUTE_TYPE_FILE,
    PAGE_ROUTE_TYPE_QUERY_PARAM,
    PREFERENCE_CENTER_QUERY_PARAM,
    PREFERENCE_CENTER_QUERY_VALUE,
)
from site_ui import (
    PROFILE_ENV_VARS,
    PUBLIC_SITE_MODE_ENV_VAR,
    PUBLIC_SITE_MODE_PRODUCTION,
    PublicSiteProfileConfigurationError,
    SiteProfile,
    build_site_profile_from_environment,
    validate_public_site_profile,
)


def _configured_public_profile(**overrides: str) -> SiteProfile:
    defaults = {
        "brand_name": "Example Recruiting",
        "legal_entity": "Example Recruiting GmbH",
        "managing_director": "Example Managing Director",
        "street": "Example Street 1",
        "postal_code": "10115",
        "city": "Berlin",
        "country": "Deutschland",
        "email": "contact@example.test",
        "phone": "+49 30 000000",
        "website": "https://example.test",
        "support_email": "support@example.test",
        "privacy_email": "privacy@example.test",
        "accessibility_email": "accessibility@example.test",
        "last_updated": "01.07.2026",
        "dpo_name": "Example privacy contact",
        "register_court": "Example register court",
        "register_number": "HRB 000000",
    }
    defaults.update(overrides)
    return SiteProfile(**defaults)


def test_public_site_profile_validation_allows_development_placeholders(
    monkeypatch,
) -> None:
    monkeypatch.delenv(PUBLIC_SITE_MODE_ENV_VAR, raising=False)

    validate_public_site_profile(SiteProfile())


def test_public_site_profile_validation_rejects_missing_required_fields_in_production(
    monkeypatch,
) -> None:
    monkeypatch.setenv(PUBLIC_SITE_MODE_ENV_VAR, PUBLIC_SITE_MODE_PRODUCTION)
    profile = _configured_public_profile(
        legal_entity="",
        street=" ",
        register_court="",
        email="",
        phone="",
    )

    with pytest.raises(PublicSiteProfileConfigurationError) as exc_info:
        validate_public_site_profile(profile)

    message = str(exc_info.value)
    for field_name in ("legal_entity", "street", "register_court", "email", "phone"):
        assert field_name in message
        assert PROFILE_ENV_VARS[field_name] in message
    assert "Example Recruiting GmbH" not in message
    assert "contact@example.test" not in message


def test_public_site_profile_validation_requires_deployment_environment_in_production(
    monkeypatch,
) -> None:
    monkeypatch.setenv(PUBLIC_SITE_MODE_ENV_VAR, PUBLIC_SITE_MODE_PRODUCTION)
    for env_var in PROFILE_ENV_VARS.values():
        monkeypatch.delenv(env_var, raising=False)

    with pytest.raises(PublicSiteProfileConfigurationError) as exc_info:
        validate_public_site_profile()

    message = str(exc_info.value)
    assert "CS_PUBLIC_LEGAL_ENTITY" in message
    assert "CS_PUBLIC_EMAIL" in message
    assert "CS_PUBLIC_REGISTER_NUMBER" in message
    assert "Cognitive Staffing" not in message
    assert "kontakt@" not in message


def test_public_site_profile_validation_accepts_complete_production_profile(
    monkeypatch,
) -> None:
    monkeypatch.setenv(PUBLIC_SITE_MODE_ENV_VAR, PUBLIC_SITE_MODE_PRODUCTION)

    validate_public_site_profile(_configured_public_profile())


def test_public_site_profile_uses_deployment_environment_values(monkeypatch) -> None:
    monkeypatch.setenv("CS_PUBLIC_LEGAL_ENTITY", "Runtime Example GmbH")
    monkeypatch.setenv("CS_PUBLIC_REGISTER_NUMBER", "HRB 123456")

    profile = build_site_profile_from_environment()

    assert profile.legal_entity == "Runtime Example GmbH"
    assert profile.register_number == "HRB 123456"


def test_app_sidebar_links_hide_requested_public_and_legal_pages() -> None:
    labels = [label for _, label in SIDEBAR_PAGE_LINKS]

    assert labels == [
        "Unsere Kompetenzen",
        "Über Cognitive Staffing",
        "Impressum",
        "Cookie Policy/Settings",
    ]


def test_app_sidebar_link_targets_exist() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    for page_path, _ in SIDEBAR_PAGE_LINKS:
        assert page_path.startswith("pages/")
        assert page_path.endswith(".py")
        assert (
            repo_root / page_path
        ).is_file(), f"Missing app sidebar target: {page_path}"


def test_public_sidebar_links_exclude_legal_pages() -> None:
    labels = [
        page.title
        for page in PAGE_DEFS
        if page.key in {"competencies", "about", "imprint", "cookies"}
    ]

    assert labels == [
        "Unsere Kompetenzen",
        "Über Cognitive Staffing",
        "Impressum",
        "Cookie Policy/Settings",
    ]


def test_public_sidebar_link_targets_exist_and_are_allowed() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    for page in PAGE_DEFS:
        if page.key not in {"competencies", "about", "imprint", "cookies"}:
            continue
        page_path = page.path
        assert page_path == "app.py" or page_path.startswith("pages/")
        assert page_path.endswith(".py")
        assert (
            repo_root / page_path
        ).is_file(), f"Missing public sidebar target: {page_path}"


def test_page_defs_are_existing_files_or_explicit_non_file_routes() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    for page in PAGE_DEFS:
        if page.route_type == PAGE_ROUTE_TYPE_FILE:
            assert page.query_params is None
            assert page.path.endswith(".py")
            assert (
                repo_root / page.path
            ).is_file(), f"Missing file-backed PAGE_DEF target: {page.path}"
            continue

        assert page.route_type == PAGE_ROUTE_TYPE_QUERY_PARAM
        assert page.path == "app.py"
        assert page.query_params == {
            PREFERENCE_CENTER_QUERY_PARAM: PREFERENCE_CENTER_QUERY_VALUE
        }
        assert (repo_root / page.path).is_file()


def test_sidebar_does_not_render_preference_center(monkeypatch) -> None:
    events: list[str] = []

    class _FakeExpander:
        def __init__(self, label: str) -> None:
            self.label = label

        def __enter__(self) -> "_FakeExpander":
            events.append(f"enter:{self.label}")
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            del exc_type, exc, tb
            events.append(f"exit:{self.label}")
            return False

    class _FakeSidebar:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def markdown(self, text: str, **_kwargs) -> None:
            events.append(f"markdown:{text}")

        def expander(self, label: str, expanded: bool = False) -> _FakeExpander:
            del expanded
            events.append(f"expander:{label}")
            return _FakeExpander(label)

        def page_link(self, page_path: str, label: str) -> None:
            events.append(f"page_link:{label}")

        def selectbox(self, *_args, **_kwargs):
            return "de"

        def select_slider(self, *_args, **_kwargs):
            return "standard"

        def slider(self, *_args, **_kwargs):
            return 0

        def toggle(self, *_args, **_kwargs):
            return False

        def json(self, *_args, **_kwargs):
            return None

    fake_st = type("FakeStreamlit", (), {})()
    fake_st.sidebar = _FakeSidebar()
    fake_st.markdown = fake_st.sidebar.markdown
    fake_st.expander = fake_st.sidebar.expander
    fake_st.page_link = fake_st.sidebar.page_link
    fake_st.selectbox = fake_st.sidebar.selectbox
    fake_st.select_slider = fake_st.sidebar.select_slider
    fake_st.slider = fake_st.sidebar.slider
    fake_st.toggle = fake_st.sidebar.toggle
    fake_st.json = fake_st.sidebar.json

    monkeypatch.setattr("components.sidebar.st", fake_st)
    monkeypatch.setattr("components.sidebar.ensure_preference_state", lambda: None)

    render_sidebar("landing")

    assert "expander:Präferenz-Center" not in events
    assert "expander:Aktiver Runtime-Kontext" not in events
    assert "page_link:Vollansicht öffnen" not in events
    assert "page_link:Unsere Kompetenzen" in events
    assert "page_link:Über Cognitive Staffing" in events
    assert "page_link:Impressum" in events
    assert "page_link:Cookie Policy/Settings" in events
    hidden_labels = {
        "Kontakt",
        "Datenschutzrichtlinie",
        "Nutzungsbedingungen",
        "Erklärung zur Barrierefreiheit",
    }
    assert not any(
        event in {f"page_link:{label}" for label in hidden_labels} for event in events
    )


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


def test_kontakt_mailto_url_encodes_subject_and_body() -> None:
    kontakt_path = Path(__file__).resolve().parents[1] / "pages" / "15_Kontakt.py"
    spec = spec_from_file_location(
        "pages.page_15_kontakt_mailto_for_tests", kontakt_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load Kontakt page module")
    kontakt_module = module_from_spec(spec)
    spec.loader.exec_module(kontakt_module)  # type: ignore[attr-defined]

    url = kontakt_module._contact_mailto_url(
        recipient="kontakt@example.test",
        subject="Kontaktanfrage: Demo & Rückruf",
        body="Name: Max\nNachricht: Hallo & danke",
    )

    assert url.startswith("mailto:kontakt@example.test?subject=")
    assert "Demo%20%26%20R%C3%BCckruf" in url
    assert "Name%3A%20Max%0ANachricht%3A%20Hallo%20%26%20danke" in url
    assert "\n" not in url


def test_static_page_link_targets_under_pages_exist() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pages_dir = repo_root / "pages"

    for page_file in pages_dir.glob("*.py"):
        tree = ast.parse(page_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not isinstance(func, ast.Attribute) or func.attr != "page_link":
                continue
            if not node.args:
                continue
            first_arg = node.args[0]
            if not isinstance(first_arg, ast.Constant) or not isinstance(
                first_arg.value, str
            ):
                continue
            target = first_arg.value
            if not target.startswith("pages/"):
                continue
            assert (
                repo_root / target
            ).is_file(), (
                f"Missing static st.page_link target in {page_file.name}: {target}"
            )
