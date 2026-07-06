"""Themed pyqtgraph helpers shared across dashboard pages."""

from __future__ import annotations

from datetime import datetime

import pyqtgraph as pg

pg.setConfigOptions(antialias=True)

CHART_BACKGROUND = "#0f1b31"
AXIS_COLOR = "#93a8c8"
SERIES_PRIMARY = "#1e6bff"
SERIES_ACCENT = "#f2600c"


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


def disable_chart_interaction(plot: pg.PlotWidget) -> None:
    """Stop wheel-zoom/drag-pan from flinging these read-only charts off-screen."""
    plot.setMouseEnabled(x=False, y=False)
    plot.setMenuEnabled(False)
    plot.hideButtons()


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


class IndexDateAxisItem(pg.AxisItem):
    """Bottom axis that labels integer plot indices with their real calendar date.

    Charts here plot one point per night/day at consecutive integer x
    positions (0, 1, 2, ...). Rather than showing that raw index, this looks
    up the ISO date string for the nearest integer and renders it as e.g.
    "Jul 05". Call `set_dates()` before each render since the underlying
    series changes with the selected range.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._dates: list[str] = []

    def set_dates(self, dates: list[str]) -> None:
        self._dates = dates

    def tickStrings(self, values, scale, spacing):
        strings = []
        for value in values:
            index = round(value)
            if abs(value - index) > 1e-6 or not (0 <= index < len(self._dates)):
                strings.append("")
                continue
            try:
                parsed = datetime.fromisoformat(self._dates[index])
            except ValueError:
                strings.append("")
                continue
            strings.append(f"{parsed.strftime('%b')} {parsed.day:02d}")
        return strings
