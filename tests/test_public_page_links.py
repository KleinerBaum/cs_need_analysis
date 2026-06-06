from __future__ import annotations

import ast
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from app import SIDEBAR_PAGE_LINKS
from components.sidebar import render_sidebar
from config.preferences import PAGE_DEFS


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
        assert (repo_root / page_path).is_file(), f"Missing app sidebar target: {page_path}"


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
        assert (repo_root / page_path).is_file(), f"Missing public sidebar target: {page_path}"


def test_sidebar_renders_preference_center_after_public_links(monkeypatch) -> None:
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
    fake_st.page_link = fake_st.sidebar.page_link

    monkeypatch.setattr("components.sidebar.st", fake_st)
    monkeypatch.setattr("components.sidebar.ensure_preference_state", lambda: None)
    monkeypatch.setattr("components.sidebar.get_preferences", lambda: {
        "ui_language": "de",
        "response_mode": "compact",
        "info_depth": "standard",
        "esco_match_strictness": 50,
        "regional_focus": "DACH",
        "privacy_mode": "minimal",
        "accessibility_mode": "standard",
        "output_format": "cards",
        "include_sources": False,
        "reuse_profile_context": False,
    })
    monkeypatch.setattr(
        "components.sidebar.get_cookie_consent",
        lambda: {"essential": True, "analytics": False, "personalization": False, "marketing": False},
    )
    monkeypatch.setattr("components.sidebar.update_preference", lambda *args, **kwargs: None)
    monkeypatch.setattr("components.sidebar.update_cookie", lambda *args, **kwargs: None)
    monkeypatch.setattr("components.sidebar.build_runtime_context", lambda: {})
    monkeypatch.setattr("components.sidebar.render_ui_mode_selector", lambda **kwargs: None)

    render_sidebar("landing")

    preference_exit_idx = events.index("exit:Präferenz-Center")
    public_links_idx = min(
        events.index("page_link:Unsere Kompetenzen"),
        events.index("page_link:Über Cognitive Staffing"),
        events.index("page_link:Impressum"),
        events.index("page_link:Cookie Policy/Settings"),
    )
    assert public_links_idx < preference_exit_idx
    hidden_labels = {
        "Kontakt",
        "Datenschutzrichtlinie",
        "Nutzungsbedingungen",
        "Erklärung zur Barrierefreiheit",
    }
    assert not any(event in {f"page_link:{label}" for label in hidden_labels} for event in events)


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
            if not isinstance(first_arg, ast.Constant) or not isinstance(first_arg.value, str):
                continue
            target = first_arg.value
            if not target.startswith("pages/"):
                continue
            assert (repo_root / target).is_file(), (
                f"Missing static st.page_link target in {page_file.name}: {target}"
            )
