from __future__ import annotations

from typing import Any


def usage_has_cache_hit(usage: Any) -> bool:
    """Return cache-hit status for usage payloads from dicts or objects."""
    if isinstance(usage, dict):
        return bool(usage.get("cached"))
    return bool(getattr(usage, "cached", False))
