"""Themed pyqtgraph helpers shared across dashboard pages."""

from __future__ import annotations

import pyqtgraph as pg

CHART_BACKGROUND = "#0f1b31"
AXIS_COLOR = "#93a8c8"
SERIES_PRIMARY = "#1e6bff"
SERIES_ACCENT = "#ff6b35"


def style_axes(plot: pg.PlotWidget, *, left_label: str, bottom_label: str) -> None:
    axis_pen = pg.mkPen(color=AXIS_COLOR)
    text_pen = pg.mkPen(color=AXIS_COLOR)
    left_axis = plot.getAxis("left")
    bottom_axis = plot.getAxis("bottom")
    left_axis.setLabel(left_label, color=AXIS_COLOR)
    bottom_axis.setLabel(bottom_label, color=AXIS_COLOR)
    left_axis.setPen(axis_pen)
    bottom_axis.setPen(axis_pen)
    left_axis.setTextPen(text_pen)
    bottom_axis.setTextPen(text_pen)
    plot.showGrid(x=True, y=True, alpha=0.15)


class ClockAxisItem(pg.AxisItem):
    """Axis that renders 'hours since prior noon' values as real HH:MM clock times.

    Values on this axis are expected in the same encoding as
    `sleep_page._hours_since_prior_noon`: evening hours count up from noon
    (22:00 -> 10), and hours past midnight continue past 24 (06:21 -> 18.35).
    That keeps an overnight span monotonic and un-wrapped on a single axis.
    """

    def tickStrings(self, values, scale, spacing):
        strings = []
        for value in values:
            clock_hours = (value + 12) % 24
            hours = int(clock_hours)
            minutes = int(round((clock_hours - hours) * 60))
            if minutes == 60:
                hours = (hours + 1) % 24
                minutes = 0
            strings.append(f"{hours:02d}:{minutes:02d}")
        return strings
