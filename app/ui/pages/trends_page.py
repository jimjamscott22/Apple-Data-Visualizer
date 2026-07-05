from __future__ import annotations

from typing import Callable

import pyqtgraph as pg
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.charts import CHART_BACKGROUND, SERIES_ACCENT, SERIES_PRIMARY, style_axes
from app.models.trends import CorrelationResult, SplitComparison, TrendsSummaryData
from app.ui.pages.base import EmptyStateCard, MetricCard


RANGE_OPTIONS = [30, 90, 365]


class TrendsPage(QWidget):
    """Cross-metric correlation analytics across sleep, HRV, resting HR, and steps."""

    def __init__(
        self,
        on_range_changed: Callable[[int], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("PageRoot")
        self._on_range_changed = on_range_changed
        self._current_range = 90

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        self.range_bar = self._build_range_bar()
        layout.addWidget(self.range_bar)

        self.metrics_row = QHBoxLayout()
        self.metrics_row.setSpacing(14)
        layout.addLayout(self.metrics_row)

        self.chart_frames: list[QFrame] = []
        self.chart_plots: list[pg.PlotWidget] = []
        self.chart_titles: list[QLabel] = []
        self.chart_captions: list[QLabel] = []
        for _ in range(3):
            frame, plot, title_label, caption_label = self._build_chart_frame()
            self.chart_frames.append(frame)
            self.chart_plots.append(plot)
            self.chart_titles.append(title_label)
            self.chart_captions.append(caption_label)
            layout.addWidget(frame)

        self.empty_state = EmptyStateCard("", "")
        layout.addWidget(self.empty_state)
        layout.addStretch()

        self.render(None)

    def _build_range_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("MetricCard")
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(18, 12, 18, 12)
        bar_layout.setSpacing(10)

        label = QLabel("Range:")
        label.setObjectName("BodyMuted")
        bar_layout.addWidget(label)

        self._range_group = QButtonGroup(self)
        self._range_group.setExclusive(True)
        for days in RANGE_OPTIONS:
            button = QPushButton(f"{days} days")
            button.setCheckable(True)
            button.setObjectName("RangeButton")
            if days == self._current_range:
                button.setChecked(True)
            button.clicked.connect(lambda _checked=False, d=days: self._handle_range_click(d))
            self._range_group.addButton(button, days)
            bar_layout.addWidget(button)

        bar_layout.addStretch()
        return bar

    def _build_chart_frame(self) -> tuple[QFrame, pg.PlotWidget, QLabel, QLabel]:
        frame = QFrame()
        frame.setObjectName("MetricCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title_label = QLabel("")
        title_label.setObjectName("SectionTitle")
        header.addWidget(title_label, 1)
        caption_label = QLabel("")
        caption_label.setObjectName("BodyMuted")
        caption_label.setStyleSheet("color: #8da2c3; font-size: 12px;")
        header.addWidget(caption_label)
        layout.addLayout(header)

        plot = pg.PlotWidget()
        plot.setBackground(CHART_BACKGROUND)
        plot.setMinimumHeight(220)
        layout.addWidget(plot)
        return frame, plot, title_label, caption_label

    def _handle_range_click(self, days: int) -> None:
        if days == self._current_range:
            return
        self._current_range = days
        if self._on_range_changed is not None:
            self._on_range_changed(days)

    def current_range(self) -> int:
        return self._current_range

    def render(self, summary: TrendsSummaryData | None) -> None:
        while self.metrics_row.count():
            item = self.metrics_row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        has_any_pairs = summary is not None and any(
            correlation.points for correlation in summary.correlations
        )
        if not has_any_pairs:
            self.empty_state.set_content(
                "No overlapping data yet",
                "Correlations need nights where sleep and another metric were both recorded. "
                "Import an Apple Health export covering the same dates for sleep, HRV, "
                "resting heart rate, or steps to see relationships here.",
            )
            self.empty_state.setVisible(True)
            for frame in self.chart_frames:
                frame.setVisible(False)
            return

        self.empty_state.setVisible(False)
        self._render_cards(summary)
        for index, correlation in enumerate(summary.correlations[: len(self.chart_frames)]):
            self._render_correlation_chart(index, correlation)

    def _render_cards(self, summary: TrendsSummaryData) -> None:
        strongest = summary.strongest
        if strongest is not None and strongest.pearson_r is not None:
            self.metrics_row.addWidget(
                MetricCard(
                    "Strongest link",
                    f"r = {strongest.pearson_r:+.2f}",
                    f"{strongest.title}. {strongest.interpretation}.",
                )
            )
        else:
            self.metrics_row.addWidget(
                MetricCard(
                    "Strongest link",
                    "--",
                    "Correlations appear once at least 5 nights overlap with another metric.",
                )
            )

        self.metrics_row.addWidget(self._split_card("Sleep → HRV", summary.hrv_sleep_split))
        self.metrics_row.addWidget(
            self._split_card("Weekday vs weekend", summary.weekday_weekend_sleep)
        )

    def _split_card(self, label: str, split: SplitComparison | None) -> MetricCard:
        if split is None or split.group_a_value is None or split.group_b_value is None:
            return MetricCard(label, "--", "Needs more overlapping nights to compare groups.")
        value = (
            f"{_format_split_value(split.group_a_value, split.unit)} vs "
            f"{_format_split_value(split.group_b_value, split.unit)}"
        )
        detail = (
            f"{split.label}: {split.group_a_label.lower()} vs {split.group_b_label.lower()}, "
            f"{split.sample_count} nights."
        )
        return MetricCard(label, value, detail)

    def _render_correlation_chart(self, index: int, correlation: CorrelationResult) -> None:
        frame = self.chart_frames[index]
        plot = self.chart_plots[index]
        frame.setVisible(True)
        self.chart_titles[index].setText(correlation.title)

        caption = correlation.interpretation
        if correlation.pearson_r is not None:
            caption = f"r = {correlation.pearson_r:+.2f}   |   {correlation.interpretation}"
        self.chart_captions[index].setText(caption)

        plot.clear()
        if not correlation.points:
            return

        x_vals = [p.x for p in correlation.points]
        y_vals = [p.y for p in correlation.points]
        scatter = pg.ScatterPlotItem(
            x=x_vals,
            y=y_vals,
            size=9,
            brush=pg.mkBrush(SERIES_PRIMARY),
            pen=pg.mkPen(None),
        )
        plot.addItem(scatter)

        if correlation.regression_slope is not None and correlation.regression_intercept is not None:
            x_min, x_max = min(x_vals), max(x_vals)
            if x_max > x_min:
                line_y = [
                    correlation.regression_intercept + correlation.regression_slope * x
                    for x in (x_min, x_max)
                ]
                plot.plot(
                    [x_min, x_max],
                    line_y,
                    pen=pg.mkPen(SERIES_ACCENT, width=2),
                )

        style_axes(plot, left_label=correlation.y_label, bottom_label=correlation.x_label)


def _format_split_value(value: float, unit: str) -> str:
    if unit == "h":
        total_minutes = int(round(value * 60))
        hours, minutes = divmod(total_minutes, 60)
        return f"{hours}h {minutes:02d}m"
    return f"{value:.0f} {unit}"
