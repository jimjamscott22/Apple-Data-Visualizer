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
