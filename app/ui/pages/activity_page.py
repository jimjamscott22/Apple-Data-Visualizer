from __future__ import annotations

from typing import Callable

import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.charts import (
    SERIES_ACCENT,
    SERIES_PRIMARY,
    IndexDateAxisItem,
    disable_chart_interaction,
    style_axes,
)
from app.models.activity import ActivitySummaryData
from app.ui.pages.base import EmptyStateCard, MetricCard, right_aligned


RANGE_OPTIONS = [7, 30, 90]


class ActivityPage(QWidget):
    """Dedicated page for daily activity analytics — steps and movement distance."""

    def __init__(
        self,
        on_range_changed: Callable[[int], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("PageRoot")
        self._on_range_changed = on_range_changed
        self._current_range = 30

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        self.range_bar = self._build_range_bar()
        layout.addWidget(self.range_bar)

        self.metrics_row = QHBoxLayout()
        self.metrics_row.setSpacing(14)
        layout.addLayout(self.metrics_row)

        self.steps_chart_frame = self._build_chart_frame(
            "Daily steps",
            legend=(
                f'<span style="color:{SERIES_PRIMARY};">■</span> Daily steps &nbsp;|&nbsp; '
                f'<span style="color:{SERIES_ACCENT};">┅</span> Average'
            ),
        )
        self.steps_plot: pg.PlotWidget = self.steps_chart_frame.findChild(pg.PlotWidget)
        disable_chart_interaction(self.steps_plot)
        layout.addWidget(self.steps_chart_frame)

        self.distance_chart_frame = self._build_chart_frame(
            "Daily walking + running distance",
            legend=f'<span style="color:{SERIES_ACCENT};">●</span> Distance (km)',
        )
        self.distance_plot: pg.PlotWidget = self.distance_chart_frame.findChild(pg.PlotWidget)
        disable_chart_interaction(self.distance_plot)
        layout.addWidget(self.distance_chart_frame)

        self.table_frame = QFrame()
        self.table_frame.setObjectName("MetricCard")
        table_layout = QVBoxLayout(self.table_frame)
        table_layout.setContentsMargins(18, 18, 18, 18)
        table_layout.setSpacing(10)

        table_title = QLabel("Daily activity")
        table_title.setObjectName("SectionTitle")
        table_layout.addWidget(table_title)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Date", "Steps", "Distance (km)", "Goal"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setMinimumHeight(240)
        table_layout.addWidget(self.table)

        layout.addWidget(self.table_frame)
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

    def _build_chart_frame(self, title: str, legend: str | None = None) -> QFrame:
        frame = QFrame()
        frame.setObjectName("MetricCard")
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(18, 18, 18, 18)
        frame_layout.setSpacing(10)

        header = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setObjectName("SectionTitle")
        header.addWidget(title_label, 1)
        if legend:
            legend_label = QLabel(legend)
            legend_label.setObjectName("BodyMuted")
            legend_label.setStyleSheet("color: #8da2c3; font-size: 12px;")
            header.addWidget(legend_label)
        frame_layout.addLayout(header)

        plot = pg.PlotWidget(axisItems={"bottom": IndexDateAxisItem(orientation="bottom")})
        plot.setBackground("#0f1b31")
        plot.setMinimumHeight(220)
        frame_layout.addWidget(plot)
        return frame

    def _handle_range_click(self, days: int) -> None:
        if days == self._current_range:
            return
        self._current_range = days
        if self._on_range_changed is not None:
            self._on_range_changed(days)

    def current_range(self) -> int:
        return self._current_range

    def render(self, summary: ActivitySummaryData | None) -> None:
        while self.metrics_row.count():
            item = self.metrics_row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        has_data = summary is not None and len(summary.daily_records) > 0
        if not has_data:
            self.metrics_row.addWidget(
                EmptyStateCard(
                    "No activity data yet",
                    "Import an Apple Health export containing step-count or "
                    "walking/running distance records to see daily steps, distance, "
                    "and active-day summaries here.",
                )
            )
            self.steps_chart_frame.setVisible(False)
            self.distance_chart_frame.setVisible(False)
            self.table_frame.setVisible(False)
            return

        self.steps_chart_frame.setVisible(True)
        self.distance_chart_frame.setVisible(True)
        self.table_frame.setVisible(True)

        avg_steps_value = _format_steps(summary.avg_daily_steps)
        step_day_count = sum(1 for r in summary.daily_records if r.steps is not None)
        avg_steps_detail = f"Across {step_day_count} day(s) with step data"

        best_value = _format_steps(summary.best_day_steps)
        best_detail = (
            f"On {summary.best_day_date}" if summary.best_day_date else "Most active day"
        )

        total_steps_value = _format_steps(summary.total_steps)
        total_steps_detail = f"Over the last {summary.range_days} days"

        avg_distance_value = _format_distance(summary.avg_daily_distance_km)
        avg_distance_detail = "Walking + running distance per day"

        active_value = f"{summary.active_days} / {summary.day_count}"
        active_detail = f"Days reaching {summary.step_goal:,} steps"

        self.metrics_row.addWidget(MetricCard("Avg daily steps", avg_steps_value, avg_steps_detail))
        self.metrics_row.addWidget(MetricCard("Best day", best_value, best_detail))
        self.metrics_row.addWidget(MetricCard("Total steps", total_steps_value, total_steps_detail))
        self.metrics_row.addWidget(
            MetricCard("Avg daily distance", avg_distance_value, avg_distance_detail)
        )
        self.metrics_row.addWidget(MetricCard("Active days", active_value, active_detail))

        self._render_steps_chart(summary)
        self._render_distance_chart(summary)
        self._render_table(summary)

    def _render_steps_chart(self, summary: ActivitySummaryData) -> None:
        self.steps_plot.clear()
        days = [r for r in summary.daily_records if r.steps is not None]
        if not days:
            self.steps_plot.getAxis("bottom").set_dates([])
            return

        x = list(range(len(days)))
        y = [r.steps for r in days]

        bar = pg.BarGraphItem(x=x, height=y, width=0.7, brush=SERIES_PRIMARY, pen=pg.mkPen(None))
        self.steps_plot.addItem(bar)

        if summary.avg_daily_steps is not None:
            avg_line = pg.InfiniteLine(
                pos=summary.avg_daily_steps,
                angle=0,
                pen=pg.mkPen(SERIES_ACCENT, width=2, style=Qt.DashLine),
            )
            self.steps_plot.addItem(avg_line)

        self.steps_plot.getAxis("bottom").set_dates([r.date for r in days])
        style_axes(self.steps_plot, left_label="Steps", bottom_label="Day")

    def _render_distance_chart(self, summary: ActivitySummaryData) -> None:
        self.distance_plot.clear()
        days = [r for r in summary.daily_records if r.distance_km is not None]
        if not days:
            self.distance_plot.getAxis("bottom").set_dates([])
            return

        x = list(range(len(days)))
        y = [r.distance_km for r in days]

        pen = pg.mkPen(color=SERIES_ACCENT, width=2)
        self.distance_plot.plot(
            x, y, pen=pen, symbol="o", symbolSize=6, symbolBrush=SERIES_ACCENT
        )

        self.distance_plot.getAxis("bottom").set_dates([r.date for r in days])
        style_axes(self.distance_plot, left_label="Distance (km)", bottom_label="Day")

    def _render_table(self, summary: ActivitySummaryData) -> None:
        records_desc = list(reversed(summary.daily_records))
        self.table.setRowCount(len(records_desc))
        for row_idx, record in enumerate(records_desc):
            steps = _format_steps(record.steps)
            distance = _format_distance(record.distance_km)
            goal = "✓" if record.goal_met else "—"

            self.table.setItem(row_idx, 0, QTableWidgetItem(record.date))
            self.table.setItem(row_idx, 1, right_aligned(steps))
            self.table.setItem(row_idx, 2, right_aligned(distance))
            self.table.setItem(row_idx, 3, right_aligned(goal))


def _format_steps(value: float | None) -> str:
    if value is None:
        return "--"
    return f"{int(round(value)):,}"


def _format_distance(value: float | None) -> str:
    if value is None:
        return "--"
    return f"{value:.2f} km"
