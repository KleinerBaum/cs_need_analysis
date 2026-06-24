"""Rendering helpers for Summary artifact release gates."""

from __future__ import annotations

from typing import Any, Callable, TYPE_CHECKING

import streamlit as st

from constants import SSKey
from state import build_vacancy_draft_json
from ux_copy_contract import summary_ui_copy

if TYPE_CHECKING:
    from wizard_pages.summary_readiness import SummaryArtifactGate


def summary_widget_key(base_key: SSKey, suffix: str | None = None) -> str:
    if not suffix:
        return base_key.value
    return f"{base_key.value}.{suffix}"


def render_artifact_blockers(
    gate: SummaryArtifactGate,
    *,
    language: str,
    streamlit_module: Any = st,
) -> None:
    if not gate.blockers:
        streamlit_module.caption(
            summary_ui_copy(
                "release_gate.next_step",
                language=language,
                next_step=gate.next_step,
            )
        )
        return
    for blocker in gate.blockers[:3]:
        streamlit_module.caption(
            summary_ui_copy(
                "release_gate.blocker",
                language=language,
                reason=blocker.reason,
            )
        )
        streamlit_module.caption(
            summary_ui_copy(
                "release_gate.todo",
                language=language,
                next_step=blocker.next_step,
            )
        )
    remaining = len(gate.blockers) - 3
    if remaining > 0:
        streamlit_module.caption(
            summary_ui_copy(
                "release_gate.more_blockers",
                language=language,
                count=remaining,
            )
        )


def final_export_pause_copy(key: str, *, language: str) -> str:
    return summary_ui_copy(f"final_export.{key}", language=language)


def localized_artifact_release_state(
    gate: SummaryArtifactGate,
    *,
    language: str,
) -> str:
    if gate.final_export_ready:
        return final_export_pause_copy("summary_ready", language=language)
    if gate.stale_regeneration_required:
        return final_export_pause_copy("summary_stale", language=language)
    if gate.final_export_blocked:
        return final_export_pause_copy(
            "summary_warning" if gate.override_allowed else "summary_blocked",
            language=language,
        )
    if gate.draft_available:
        return final_export_pause_copy("summary_draft", language=language)
    if gate.preview_available:
        return final_export_pause_copy("summary_preview", language=language)
    return final_export_pause_copy("summary_open", language=language)


def render_final_export_pause_panel(
    gate: SummaryArtifactGate,
    artifact_label: str,
    ui_mode: str,
    *,
    language: str,
    streamlit_module: Any = st,
    draft_json_builder: Callable[[Any], str] = build_vacancy_draft_json,
) -> None:
    def copy(key: str) -> str:
        return final_export_pause_copy(key, language=language)

    title = copy("title")
    with streamlit_module.container(border=True):
        streamlit_module.warning(f"{title}: {artifact_label}")
        streamlit_module.caption(
            localized_artifact_release_state(gate, language=language)
        )
        streamlit_module.markdown(f"**{copy('blockers')}**")
        if gate.blockers:
            for blocker in gate.blockers[:5]:
                streamlit_module.write(f"- {blocker.reason}")
        else:
            streamlit_module.write(f"- {copy('fallback_blocker')}")

        streamlit_module.caption(f"{copy('next_action')}: {gate.next_step}")
        streamlit_module.info(copy("preview"))

        if gate.preview_available:
            try:
                draft_json = draft_json_builder(streamlit_module.session_state)
            except Exception:
                draft_json = ""
            if draft_json and callable(
                getattr(streamlit_module, "download_button", None)
            ):
                streamlit_module.download_button(
                    copy("draft"),
                    data=draft_json.encode("utf-8"),
                    file_name="vacancy_draft.json",
                    mime="application/json",
                    help=copy("draft_help"),
                    width="stretch",
                    key=summary_widget_key(
                        SSKey.SUMMARY_ACTION_WIDGET_PREFIX,
                        f"final_export_pause.draft.{gate.artifact_id}",
                    ),
                )
            else:
                streamlit_module.caption(copy("draft_help"))

        if str(ui_mode or "").strip() != "expert":
            return
        streamlit_module.caption(
            copy("override_available")
            if gate.override_allowed
            else copy("override_hidden")
        )
        if not gate.blockers or not callable(
            getattr(streamlit_module, "expander", None)
        ):
            return
        with streamlit_module.expander(copy("expert_details"), expanded=False):
            for blocker in gate.blockers:
                details = [
                    f"type={blocker.blocker_type}",
                    f"severity={blocker.severity}",
                ]
                if blocker.fact_key:
                    details.append(f"fact_id={blocker.fact_key}")
                if blocker.provenance:
                    details.append(f"provenance={blocker.provenance}")
                streamlit_module.code(" | ".join(details), language="text")
