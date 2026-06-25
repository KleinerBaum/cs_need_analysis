"""Recruiting-cycle visual used on the intro landing page."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from i18n import t


@dataclass(frozen=True)
class RecruitingCycleStep:
    label: str
    subtitle: str
    impact: str
    phase: str


RECRUITING_CYCLE_STEPS: tuple[RecruitingCycleStep, ...] = (
    RecruitingCycleStep(
        label="Bedarfsanalyse",
        subtitle="Vorbereitung",
        impact="Rolle, Muss-Kriterien, Kompromisse und Erfolg werden entschieden.",
        phase="Vor Recruiting",
    ),
    RecruitingCycleStep(
        label="Talent Sourcing",
        subtitle="Suche",
        impact="Suchstrings und Ansprache funktionieren nur mit klarem Zielprofil.",
        phase="Markt aktivieren",
    ),
    RecruitingCycleStep(
        label="Applicant Screening",
        subtitle="Matching",
        impact="CVs werden gegen bestätigte Anforderungen statt gegen Bauchgefühl geprüft.",
        phase="Auswahl schärfen",
    ),
    RecruitingCycleStep(
        label="Interview & Selection",
        subtitle="Prüfung",
        impact="Interviewfragen prüfen beobachtbares Verhalten und echte Erfolgskriterien.",
        phase="Entscheidung vorbereiten",
    ),
    RecruitingCycleStep(
        label="Job Offer & Negotiation",
        subtitle="Angebot",
        impact="Gehalt, Benefits und Motivation sind mit dem Bedarf verknüpft.",
        phase="Zusage sichern",
    ),
    RecruitingCycleStep(
        label="Smooth Onboarding",
        subtitle="Start",
        impact="Die ersten 30/60/90 Tage folgen aus dem Rollenauftrag.",
        phase="Wirksamkeit erzeugen",
    ),
    RecruitingCycleStep(
        label="Feedback & Evolution",
        subtitle="Lernen",
        impact="Erkenntnisse verbessern das nächste Briefing statt nur den nächsten Prozess.",
        phase="Lernen",
    ),
)


def _cycle_coordinates(count: int) -> tuple[list[float], list[float]]:
    # Start at the top and move clockwise.
    angles = [math.pi / 2 - (2 * math.pi * index / count) for index in range(count)]
    return [math.cos(angle) for angle in angles], [math.sin(angle) for angle in angles]


def build_recruiting_cycle_figure(focused_index: int | None = None) -> Any | None:
    """Return an interactive Plotly figure for the recruiting lifecycle.

    The first phase is visually emphasized because the product promise is anchored in
    preparation / recruiting need analysis. A ``None`` return lets callers degrade
    gracefully in stripped-down test environments.
    """

    try:
        import plotly.graph_objects as go
    except Exception:
        return None

    labels = [str(t(step.label)) for step in RECRUITING_CYCLE_STEPS]
    subtitles = [str(t(step.subtitle)) for step in RECRUITING_CYCLE_STEPS]
    impacts = [str(t(step.impact)) for step in RECRUITING_CYCLE_STEPS]
    phases = [str(t(step.phase)) for step in RECRUITING_CYCLE_STEPS]
    if focused_index is not None and not 0 <= focused_index < len(labels):
        focused_index = None
    x_values, y_values = _cycle_coordinates(len(RECRUITING_CYCLE_STEPS))
    closed_x = [*x_values, x_values[0]]
    closed_y = [*y_values, y_values[0]]

    marker_sizes = [
        34 if index == focused_index else 22 for index in range(len(labels))
    ]
    if focused_index is None:
        marker_sizes[0] = 34
    marker_colors = [
        "#2EECE8" if index == 0 else "#5B6B7D" for index in range(len(labels))
    ]
    text_positions = [
        "top center",
        "middle right",
        "bottom right",
        "bottom center",
        "bottom left",
        "middle left",
        "top left",
    ]

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=closed_x,
            y=closed_y,
            mode="lines",
            line={"width": 3, "color": "rgba(46,236,232,0.44)"},
            hoverinfo="skip",
            showlegend=False,
        )
    )
    figure.add_trace(
        go.Scatter(
            x=x_values,
            y=y_values,
            mode="markers+text",
            marker={
                "size": marker_sizes,
                "color": marker_colors,
                "line": {"width": 2, "color": "rgba(255,255,255,0.82)"},
            },
            selectedpoints=[focused_index] if focused_index is not None else None,
            selected={
                "marker": {
                    "opacity": 1.0,
                    "size": 34,
                }
            },
            unselected={
                "marker": {
                    "opacity": 0.34,
                }
            },
            text=[
                f"<b>{label}</b><br><span>{subtitle}</span>"
                for label, subtitle in zip(labels, subtitles, strict=False)
            ],
            textposition=text_positions,
            textfont={"size": 12, "color": "#F8FAFC"},
            customdata=list(zip(phases, impacts, subtitles, strict=False)),
            hovertemplate=(
                "<b>%{text}</b><br>"
                + str(t("Phase"))
                + ": %{customdata[0]}<br>"
                + str(t("Wirkung"))
                + ": %{customdata[1]}"
                + "<extra></extra>"
            ),
            showlegend=False,
        )
    )
    figure.add_annotation(
        x=0,
        y=0,
        text=(
            "<b>"
            + str(t("Schritt 1"))
            + "</b><br>"
            + str(t("entscheidet die Qualität der nächsten 6 Schritte"))
        ),
        showarrow=False,
        font={"size": 15, "color": "#F8FAFC"},
        align="center",
        bordercolor="rgba(46,236,232,0.42)",
        borderwidth=1,
        borderpad=10,
        bgcolor="rgba(2, 11, 22, 0.78)",
    )
    figure.update_layout(
        height=430,
        margin={"l": 16, "r": 16, "t": 28, "b": 28},
        paper_bgcolor="#07111F",
        plot_bgcolor="#07111F",
        xaxis={
            "visible": False,
            "range": [-1.42, 1.42],
            "scaleanchor": "y",
            "scaleratio": 1,
        },
        yaxis={"visible": False, "range": [-1.32, 1.32]},
        hoverlabel={"bgcolor": "#07111F", "font_size": 12, "font_color": "#F8FAFC"},
    )
    return figure
