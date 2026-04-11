from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from typing import Any, Literal

from constants import SSKey


BASE_PATH = Path(__file__).resolve().parents[1] / "wizard_pages" / "base.py"
SPEC = spec_from_file_location("wizard_pages.base_for_tests", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load base module")
BASE_MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = BASE_MODULE
SPEC.loader.exec_module(BASE_MODULE)  # type: ignore[attr-defined]


class _NoopContext:
    def __enter__(self) -> "_NoopContext":
        return self

    def __exit__(self, *_: object) -> Literal[False]:
        return False


class _FakeStreamlit:
    def __init__(
        self, session_state: dict[str, Any], button_map: dict[str, bool] | None = None
    ):
        self.session_state = session_state
        self.button_map = button_map or {}
        self.info_messages: list[str] = []
        self.warning_messages: list[str] = []
        self.success_messages: list[str] = []

    def warning(self, message: str) -> None:
        self.warning_messages.append(message)

    def info(self, message: str) -> None:
        self.info_messages.append(message)

    def success(self, message: str) -> None:
        self.success_messages.append(message)

    def code(self, *_: Any, **__: Any) -> None:
        return None

    def expander(self, *_: Any, **__: Any) -> _NoopContext:
        return _NoopContext()

    def button(self, _label: str, *, key: str, **__: Any) -> bool:
        return bool(self.button_map.get(key, False))

    def selectbox(self, _label: str, options: list[str], **__: Any) -> str:
        return options[1]

    def columns(self, _spec: list[int]) -> tuple[_NoopContext, _NoopContext]:
        return (_NoopContext(), _NoopContext())


def test_find_legacy_uri_payload_prefers_occupation_over_skills(monkeypatch) -> None:
    fake_st = _FakeStreamlit(
        session_state={
            SSKey.ESCO_OCCUPATION_SELECTED.value: {"uri": "legacy:occ"},
            SSKey.ESCO_SKILLS_SELECTED_MUST.value: [{"uri": "legacy:skill"}],
        }
    )
    monkeypatch.setattr(BASE_MODULE, "st", fake_st)

    payload = BASE_MODULE._find_legacy_uri_payload()

    assert payload == {
        "target": SSKey.ESCO_OCCUPATION_SELECTED.value,
        "uri": "legacy:occ",
        "concept_type": "occupation",
    }


def test_render_esco_migration_trigger_uses_skill_conversion_endpoint(
    monkeypatch,
) -> None:
    fake_st = _FakeStreamlit(
        session_state={}, button_map={"esco.legacy_uri.migrate": True}
    )
    monkeypatch.setattr(BASE_MODULE, "st", fake_st)

    captured: dict[str, str] = {}

    class _FakeEscoClient:
        def conversion(self, endpoint: str, **query: object) -> dict[str, object]:
            captured["endpoint"] = endpoint
            captured["uri"] = str(query.get("uri") or "")
            return {
                "_embedded": {
                    "results": [
                        {
                            "uri": "http://data.europa.eu/esco/skill/new",
                            "type": "skill",
                        }
                    ]
                }
            }

    monkeypatch.setattr(BASE_MODULE, "EscoClient", _FakeEscoClient)

    session_state = {
        SSKey.ESCO_SKILLS_SELECTED_MUST.value: [
            {"uri": "legacy:skill", "title": "Old", "type": "skill"}
        ],
        SSKey.ESCO_MIGRATION_LOG.value: [],
        SSKey.ESCO_MIGRATION_PENDING.value: None,
    }
    fake_st.session_state.update(session_state)

    BASE_MODULE._render_esco_migration_trigger(
        {
            "target": SSKey.ESCO_SKILLS_SELECTED_MUST.value,
            "uri": "legacy:skill",
            "concept_type": "skill",
            "index": "0",
        }
    )

    assert captured == {"endpoint": "skill", "uri": "legacy:skill"}
    assert (
        fake_st.session_state[SSKey.ESCO_SKILLS_SELECTED_MUST.value][0]["uri"]
        == "http://data.europa.eu/esco/skill/new"
    )
    assert (
        fake_st.session_state[SSKey.ESCO_MIGRATION_LOG.value][0]["old_uri"]
        == "legacy:skill"
    )


def test_render_pending_migration_choice_requires_explicit_selection(
    monkeypatch,
) -> None:
    pending = {
        "target": SSKey.ESCO_OCCUPATION_SELECTED.value,
        "uri": "legacy:occ",
        "concept_type": "occupation",
        "candidates": [
            {"uri": "uri:occ:one", "label": "One"},
            {"uri": "uri:occ:two", "label": "Two"},
        ],
    }
    fake_st = _FakeStreamlit(
        session_state={
            SSKey.ESCO_OCCUPATION_SELECTED.value: {"uri": "legacy:occ", "title": "Old"},
            SSKey.ESCO_MIGRATION_PENDING.value: pending,
            SSKey.ESCO_MIGRATION_LOG.value: [],
        },
        button_map={"esco.legacy_uri.apply_selection": True},
    )
    monkeypatch.setattr(BASE_MODULE, "st", fake_st)

    BASE_MODULE._render_pending_esco_migration_choice()

    assert (
        fake_st.session_state[SSKey.ESCO_OCCUPATION_SELECTED.value]["uri"]
        == "uri:occ:two"
    )
    assert fake_st.session_state[SSKey.ESCO_MIGRATION_PENDING.value] is None
    log_entry = fake_st.session_state[SSKey.ESCO_MIGRATION_LOG.value][0]
    assert log_entry["decision"] == "selected_from_multiple"
    assert log_entry["new_uri"] == "uri:occ:two"
    assert "migrated_at" in log_entry
