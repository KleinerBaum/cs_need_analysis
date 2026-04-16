# wizard_pages/__init__.py
"""Dynamic loader for wizard pages.

Rationale:
Your screenshot uses filenames like `00_landing.py`, which are not importable via normal
Python syntax. We therefore load them by file path and assign a safe module name.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from typing import List

from constants import STEPS
from wizard_pages.base import WizardPage


def _load_module_from_path(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module spec for {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


def load_pages() -> List[WizardPage]:
    pages_dir = Path(__file__).parent
    # Keep this list explicit so detached/legacy modules never become routable by
    # filename pattern alone.
    ignore = {
        "__init__.py",
        "base.py",
        "jobad_intake.py",
        # Legacy hidden-step module: Start phases B/C now contain this flow.
        # Intentionally non-routable in the canonical wizard.
        "01a_jobspec_review.py",
        # Legacy hidden-step module: Team was removed from the visible canonical
        # intake wizard navigation and must not be routed.
        "03_team.py",
    }
    page_pattern = re.compile(r"^\d+[a-z]?_")
    py_files = sorted(
        [
            p
            for p in pages_dir.glob("*.py")
            if p.name not in ignore and page_pattern.match(p.stem)
        ]
    )

    pages: List[WizardPage] = []
    for p in py_files:
        safe_name = f"wizard_pages.page_{p.stem.replace('-', '_')}"
        mod = _load_module_from_path(p, safe_name)
        if hasattr(mod, "PAGE"):
            page = getattr(mod, "PAGE")
        elif hasattr(mod, "get_page"):
            page = mod.get_page()
        else:
            raise RuntimeError(
                f"Wizard page {p.name} must define `PAGE` or `get_page()`."
            )
        if not isinstance(page, WizardPage):
            raise TypeError(f"{p.name}: PAGE must be a WizardPage, got {type(page)}")
        pages.append(page)

    # Ensure stable ordering: by filename (00_, 01_, ...)
    expected_step_keys = [step.key for step in STEPS]
    loaded_step_keys = [page.key for page in pages]
    if loaded_step_keys != expected_step_keys:
        raise RuntimeError(
            "Wizard page contract mismatch: loaded page keys must match constants.STEPS "
            f"in order. loaded={loaded_step_keys}, expected={expected_step_keys}"
        )
    return pages
