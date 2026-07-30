from __future__ import annotations

from datetime import datetime
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
    ClockAxisItem,
    IndexDateAxisItem,
    disable_chart_interaction,
    style_axes,
)
from app.models.sleep import SleepSummaryData
from app.preferences import SLEEP_RANGE_OPTIONS
from app.ui.pages.base import EmptyStateCard, MetricCard, right_aligned


RANGE_OPTIONS = SLEEP_RANGE_OPTIONS


class SleepPage(QWidget):
    """Dedicated page for nightly sleep analytics."""

    def __init__(
        self,
        on_range_changed: Callable[[int], None] | None = None,
        initial_range: int = 30,
        clock_format: str = "24-hour",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("PageRoot")
        self._on_range_changed = on_range_changed
        self._current_range = initial_range if initial_range in RANGE_OPTIONS else 30
        self._use_24_hour = clock_format == "24-hour"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        self.range_bar = self._build_range_bar()
        layout.addWidget(self.range_bar)

        self.metrics_row = QHBoxLayout()
        self.metrics_row.setSpacing(14)
        layout.addLayout(self.metrics_row)

        self.duration_chart_frame = self._build_chart_frame(
            "Nightly sleep duration",
            legend=(
                f'<span style="color:{SERIES_PRIMARY};">■</span> Nightly duration &nbsp;|&nbsp; '
                f'<span style="color:{SERIES_ACCENT};">┅</span> Average'
            ),
            bottom_axis_item=IndexDateAxisItem(orientation="bottom"),
        )
        self.duration_plot: pg.PlotWidget = self.duration_chart_frame.findChild(pg.PlotWidget)
        disable_chart_interaction(self.duration_plot)
        layout.addWidget(self.duration_chart_frame)

        self.clock_axis = ClockAxisItem(
            orientation="left",
            use_24_hour=self._use_24_hour,
        )
        self.timing_chart_frame = self._build_chart_frame(
            "Bedtime & wake-time trend",
            legend=(
                f'<span style="color:{SERIES_PRIMARY};">●</span> Bedtime &nbsp;|&nbsp; '
                f'<span style="color:{SERIES_ACCENT};">●</span> Wake time'
            ),
            left_axis_item=self.clock_axis,
            bottom_axis_item=IndexDateAxisItem(orientation="bottom"),
        )
        self.timing_plot: pg.PlotWidget = self.timing_chart_frame.findChild(pg.PlotWidget)
        disable_chart_interaction(self.timing_plot)
        layout.addWidget(self.timing_chart_frame)

        self.table_frame = QFrame()
        self.table_frame.setObjectName("MetricCard")
        table_layout = QVBoxLayout(self.table_frame)
        table_layout.setContentsMargins(18, 18, 18, 18)
        table_layout.setSpacing(10)

        table_title = QLabel("Nightly sessions")
        table_title.setObjectName("SectionTitle")
        table_layout.addWidget(table_title)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Night", "Bedtime", "Wake", "Asleep", "In Bed", "Efficiency", "Consistency"]
        )
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

    def _build_chart_frame(
        self,
        title: str,
        legend: str | None = None,
        left_axis_item: pg.AxisItem | None = None,
        bottom_axis_item: pg.AxisItem | None = None,
    ) -> QFrame:
        frame = QFrame()
        frame.setObjectName("MetricCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setObjectName("SectionTitle")
        header.addWidget(title_label, 1)
        if legend:
            legend_label = QLabel(legend)
            legend_label.setObjectName("BodyMuted")
            legend_label.setStyleSheet("color: #8da2c3; font-size: 12px;")
            header.addWidget(legend_label)
        layout.addLayout(header)

        axis_items = {}
        if left_axis_item is not None:
            axis_items["left"] = left_axis_item
        if bottom_axis_item is not None:
            axis_items["bottom"] = bottom_axis_item
        plot = pg.PlotWidget(axisItems=axis_items) if axis_items else pg.PlotWidget()
        plot.setBackground("#0f1b31")
        plot.setMinimumHeight(220)
        layout.addWidget(plot)
        return frame

    def _handle_range_click(self, days: int) -> None:
        if days == self._current_range:
            return
        self._current_range = days
        if self._on_range_changed is not None:
            self._on_range_changed(days)

    def set_range(self, days: int) -> None:
        if days not in RANGE_OPTIONS:
            raise ValueError(f"Unsupported sleep range: {days}")
        self._current_range = days
        button = self._range_group.button(days)
        if button is not None:
            button.setChecked(True)

    def set_clock_format(self, clock_format: str) -> None:
        self._use_24_hour = clock_format == "24-hour"
        self.clock_axis.set_clock_format(use_24_hour=self._use_24_hour)

    def current_range(self) -> int:
        return self._current_range

    def render(self, summary: SleepSummaryData | None) -> None:
        while self.metrics_row.count():
            item = self.metrics_row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        has_data = summary is not None and len(summary.nights) > 0
        if not has_data:
            self.metrics_row.addWidget(
                EmptyStateCard(
                    "No sleep data yet",
                    "Import an Apple Health export containing sleep records to see nightly "
                    "duration, bedtime and wake trends, efficiency, and consistency here.",
                )
            )
            self.duration_chart_frame.setVisible(False)
            self.timing_chart_frame.setVisible(False)
            self.table_frame.setVisible(False)
            return

        self.duration_chart_frame.setVisible(True)
        self.timing_chart_frame.setVisible(True)
        self.table_frame.setVisible(True)

        last = summary.last_night
        last_value = _format_hours(last.total_sleep_hours) if last else "--"
        last_detail = f"Night of {last.night_date}" if last else "Most recent night"

        avg_value = _format_hours(summary.avg_sleep_hours)
        avg_detail = f"Across last {len(summary.nights)} night(s)"

        eff_value = (
            f"{summary.avg_efficiency:.0f}%" if summary.avg_efficiency is not None else "--"
        )
        eff_detail = "Asleep time ÷ time in bed"

        cons_value = (
            f"{summary.avg_consistency:.0f} / 100" if summary.avg_consistency is not None else "--"
        )
        cons_detail = "Higher = more regular schedule"

        bedtime_str = _format_clock_hours(
            summary.avg_bedtime_hours,
            offset_from_noon=True,
            use_24_hour=self._use_24_hour,
        )
        wake_str = _format_clock_hours(
            summary.avg_wake_hours,
            offset_from_noon=False,
            use_24_hour=self._use_24_hour,
        )
        schedule_value = f"{bedtime_str} → {wake_str}"
        schedule_detail = "Average bedtime → wake time"

        self.metrics_row.addWidget(MetricCard("Last night", last_value, last_detail))
        self.metrics_row.addWidget(MetricCard(f"{summary.range_days}-day avg", avg_value, avg_detail))
        self.metrics_row.addWidget(MetricCard("Avg efficiency", eff_value, eff_detail))
        self.metrics_row.addWidget(MetricCard("Avg consistency", cons_value, cons_detail))
        self.metrics_row.addWidget(MetricCard("Schedule", schedule_value, schedule_detail))

        self._render_duration_chart(summary)
        self._render_timing_chart(summary)
        self._render_table(summary)

    def _render_duration_chart(self, summary: SleepSummaryData) -> None:
        self.duration_plot.clear()
        nights = list(reversed(summary.nights))
        if not nights:
            return

        x = list(range(len(nights)))
        y = [n.total_sleep_hours for n in nights]

        bar = pg.BarGraphItem(x=x, height=y, width=0.7, brush=SERIES_PRIMARY, pen=pg.mkPen(None))
        self.duration_plot.addItem(bar)

        if summary.avg_sleep_hours is not None:
            avg_line = pg.InfiniteLine(
                pos=summary.avg_sleep_hours,
                angle=0,
                pen=pg.mkPen(SERIES_ACCENT, width=2, style=Qt.DashLine),
            )
            self.duration_plot.addItem(avg_line)

        self.duration_plot.getAxis("bottom").set_dates([n.night_date for n in nights])
        style_axes(self.duration_plot, left_label="Hours asleep", bottom_label="Night")

    def _render_timing_chart(self, summary: SleepSummaryData) -> None:
        self.timing_plot.clear()
        nights = list(reversed(summary.nights))
        if not nights:
            return

        x = list(range(len(nights)))
        bedtime_y: list[float] = []
        wake_y: list[float] = []
        for night in nights:
            b = _hours_since_prior_noon(night.bedtime_at)
            w = _hours_since_prior_noon(night.wake_at)
            bedtime_y.append(b if b is not None else float("nan"))
            wake_y.append(w if w is not None else float("nan"))

        bedtime_pen = pg.mkPen(color=SERIES_PRIMARY, width=2)
        wake_pen = pg.mkPen(color=SERIES_ACCENT, width=2)
        self.timing_plot.plot(x, bedtime_y, pen=bedtime_pen, symbol="o", symbolSize=6, symbolBrush=SERIES_PRIMARY)
        self.timing_plot.plot(x, wake_y, pen=wake_pen, symbol="o", symbolSize=6, symbolBrush=SERIES_ACCENT)

        self.timing_plot.getAxis("bottom").set_dates([n.night_date for n in nights])
        style_axes(self.timing_plot, left_label="Time of day", bottom_label="Night")

    def _render_table(self, summary: SleepSummaryData) -> None:
        self.table.setRowCount(len(summary.nights))
        for row_idx, night in enumerate(summary.nights):
            bedtime = _format_clock_time(night.bedtime_at, use_24_hour=self._use_24_hour)
            wake = _format_clock_time(night.wake_at, use_24_hour=self._use_24_hour)
            efficiency = (
                f"{night.sleep_efficiency:.0f}%"
                if night.sleep_efficiency is not None
                else "--"
            )
            consistency = (
                f"{night.consistency_score:.0f}"
                if night.consistency_score is not None
                else "--"
            )
            in_bed = (
                _format_hours(night.time_in_bed_hours)
                if night.time_in_bed_hours is not None
                else "--"
            )

            self.table.setItem(row_idx, 0, QTableWidgetItem(night.night_date))
            self.table.setItem(row_idx, 1, QTableWidgetItem(bedtime))
            self.table.setItem(row_idx, 2, QTableWidgetItem(wake))
            self.table.setItem(row_idx, 3, right_aligned(_format_hours(night.total_sleep_hours)))
            self.table.setItem(row_idx, 4, right_aligned(in_bed))
            self.table.setItem(row_idx, 5, right_aligned(efficiency))
            self.table.setItem(row_idx, 6, right_aligned(consistency))


def _format_hours(value: float | None) -> str:
    if value is None:
        return "--"
    total_minutes = int(round(value * 60))
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours}h {minutes:02d}m"


def _clock_hours(iso_value: str | None) -> float | None:
    if not iso_value:
        return None
    dt = datetime.fromisoformat(iso_value)
    return dt.hour + dt.minute / 60 + dt.second / 3600


def _hours_since_prior_noon(iso_value: str | None) -> float | None:
    """Map a clock time to a continuous timeline anchored at the prior noon.

    Evening hours count up from noon (22:00 -> 10) and hours past midnight
    continue past 24 (06:21 -> 18.35), so bedtime and wake time land on one
    monotonic axis instead of wrapping at midnight.
    """
    raw = _clock_hours(iso_value)
    if raw is None:
        return None
    return raw - 12 if raw >= 12 else raw + 12


def _format_clock_hours(
    value: float | None,
    *,
    offset_from_noon: bool,
    use_24_hour: bool,
) -> str:
    if value is None:
        return "--"
    if offset_from_noon:
        clock = (value + 12) % 24
    else:
        clock = value % 24
    hours = int(clock)
    minutes = int(round((clock - hours) * 60))
    if minutes == 60:
        hours = (hours + 1) % 24
        minutes = 0
    if use_24_hour:
        return f"{hours:02d}:{minutes:02d}"
    suffix = "AM" if hours < 12 else "PM"
    return f"{hours % 12 or 12}:{minutes:02d} {suffix}"


def _format_clock_time(iso_value: str | None, *, use_24_hour: bool) -> str:
    if not iso_value:
        return "--"
    parsed = datetime.fromisoformat(iso_value)
    if use_24_hour:
        return parsed.strftime("%H:%M")
    suffix = "AM" if parsed.hour < 12 else "PM"
    return f"{parsed.hour % 12 or 12}:{parsed.minute:02d} {suffix}"
