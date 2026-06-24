from __future__ import annotations

from wizard_pages.base import WizardContext, WizardPage
from wizard_pages.jobad_intake import render_jobad_intake


def render(ctx: WizardContext) -> None:
    render_jobad_intake(ctx)


PAGE = WizardPage(
    key="landing",
    title_de="Start",
    icon="🏁",
    render=render,
    requires_jobspec=False,
)
