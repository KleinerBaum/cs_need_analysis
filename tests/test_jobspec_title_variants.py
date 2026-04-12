from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

from esco_client import EscoClientError

JOBSPEC_PATH = (
    Path(__file__).resolve().parents[1] / "wizard_pages" / "01a_jobspec_review.py"
)
SPEC = spec_from_file_location("wizard_pages.page_01a_jobspec_review", JOBSPEC_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load jobspec review module")
JOBSPEC_MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(JOBSPEC_MODULE)  # type: ignore[attr-defined]


def test_load_occupation_title_variants_uses_fallback_after_retryable_primary_failure(
    monkeypatch,
) -> None:
    calls: list[str] = []

    class _FakeClient:
        def terms(self, *, uri: str, type: str, language: str):
            del uri, type
            calls.append(language)
            if language == "de":
                raise EscoClientError(
                    status_code=503,
                    endpoint="terms",
                    message="ESCO service returned an error response.",
                )
            return {"preferredLabel": "Data Engineer"}

    monkeypatch.setattr(JOBSPEC_MODULE, "EscoClient", _FakeClient)

    variants, warnings = JOBSPEC_MODULE._load_occupation_title_variants(
        occupation_uri="uri:occupation:1",
        languages=["de"],
    )

    assert calls == ["de", "en"]
    assert warnings == []
    assert variants == {"de": ["Data Engineer"]}


def test_load_occupation_title_variants_collects_warning_when_primary_and_fallback_fail_retryable(
    monkeypatch,
) -> None:
    calls: list[str] = []

    class _FakeClient:
        def terms(self, *, uri: str, type: str, language: str):
            del uri, type
            calls.append(language)
            raise EscoClientError(
                status_code=503,
                endpoint="terms",
                message="ESCO service returned an error response.",
            )

    monkeypatch.setattr(JOBSPEC_MODULE, "EscoClient", _FakeClient)

    variants, warnings = JOBSPEC_MODULE._load_occupation_title_variants(
        occupation_uri="uri:occupation:1",
        languages=["de", "en"],
    )

    assert calls == ["de", "en", "en", "de"]
    assert variants == {}
    assert warnings == ["de", "en"]


def test_load_occupation_title_variants_keeps_non_retryable_error_behavior(
    monkeypatch,
) -> None:
    class _FakeClient:
        def terms(self, *, uri: str, type: str, language: str):
            del uri, type, language
            raise EscoClientError(
                status_code=404,
                endpoint="terms",
                message="ESCO service returned an error response.",
            )

    monkeypatch.setattr(JOBSPEC_MODULE, "EscoClient", _FakeClient)

    with pytest.raises(EscoClientError):
        JOBSPEC_MODULE._load_occupation_title_variants(
            occupation_uri="uri:occupation:1",
            languages=["de"],
        )
