from types import SimpleNamespace

from wizard_pages.jobad_intake import _usage_has_cache_hit


def test_usage_has_cache_hit_for_dict_usage() -> None:
    assert _usage_has_cache_hit({"cached": True}) is True
    assert _usage_has_cache_hit({"cached": 0}) is False


def test_usage_has_cache_hit_for_object_usage() -> None:
    assert _usage_has_cache_hit(SimpleNamespace(cached=True)) is True
    assert _usage_has_cache_hit(SimpleNamespace(cached="")) is False


def test_usage_has_cache_hit_for_unknown_usage_type() -> None:
    assert _usage_has_cache_hit(None) is False
    assert _usage_has_cache_hit("cached") is False
