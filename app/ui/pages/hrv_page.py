from __future__ import annotations

import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.charts import SERIES_ACCENT, SERIES_PRIMARY
from app.models.hrv import HRVSummaryData
from app.ui.pages.base import EmptyStateCard, MetricCard


class HRVPage(QWidget):
    """Dedicated page for Heart Rate Variability analysis."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PageRoot")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        self.metrics_row = QHBoxLayout()
        self.metrics_row.setSpacing(14)
        layout.addLayout(self.metrics_row)

        self.chart_frame = QFrame()
        self.chart_frame.setObjectName("MetricCard")
        chart_layout = QVBoxLayout(self.chart_frame)
        chart_layout.setContentsMargins(18, 18, 18, 18)
        chart_layout.setSpacing(10)

        chart_header = QHBoxLayout()
        chart_title = QLabel("HRV Trend — last 30 days")
        chart_title.setObjectName("SectionTitle")
        chart_legend = QLabel(
            f'<span style="color:{SERIES_PRIMARY};">●</span> Daily avg &nbsp;|&nbsp; '
            f'<span style="color:{SERIES_ACCENT};">●</span> 7-day rolling avg'
        )
        chart_legend.setObjectName("BodyMuted")
        chart_legend.setStyleSheet("color: #8da2c3; font-size: 12px;")
        chart_header.addWidget(chart_title, 1)
        chart_header.addWidget(chart_legend)
        chart_layout.addLayout(chart_header)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("#0f1b31")
        self.plot_widget.setMinimumHeight(220)
        chart_layout.addWidget(self.plot_widget)

        layout.addWidget(self.chart_frame)

        self.table_frame = QFrame()
        self.table_frame.setObjectName("MetricCard")
        table_layout = QVBoxLayout(self.table_frame)
        table_layout.setContentsMargins(18, 18, 18, 18)
        table_layout.setSpacing(10)

        table_title = QLabel("Daily HRV History")
        table_title.setObjectName("SectionTitle")
        table_layout.addWidget(table_title)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Date", "Avg (ms)", "Min (ms)", "Max (ms)", "Samples"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setMinimumHeight(240)
        table_layout.addWidget(self.table)

        layout.addWidget(self.table_frame)
        layout.addStretch()

        self.render(None)

    def render(self, summary: HRVSummaryData | None) -> None:
        while self.metrics_row.count():
            item = self.metrics_row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        has_data = summary is not None and (
            summary.latest_hrv_ms is not None or len(summary.daily_records) > 0
        )

        if not has_data:
            self.metrics_row.addWidget(
                EmptyStateCard(
                    "No HRV data yet",
                    "Import an Apple Health export containing Heart Rate Variability (SDNN) "
                    "records to see your full HRV analysis here.",
                )
            )
            self.chart_frame.setVisible(False)
            self.table_frame.setVisible(False)
            return

        self.chart_frame.setVisible(True)
        self.table_frame.setVisible(True)

        latest_str = f"{summary.latest_hrv_ms:.0f} ms" if summary.latest_hrv_ms is not None else "--"
        latest_detail = (
            f"Recorded {summary.latest_hrv_date}"
            if summary.latest_hrv_date
            else "Most recent SDNN reading"
        )

        avg_7_str = f"{summary.avg_7_day_ms:.0f} ms" if summary.avg_7_day_ms is not None else "--"
        avg_30_str = f"{summary.avg_30_day_ms:.0f} ms" if summary.avg_30_day_ms is not None else "--"

        trend_labels = {
            "rising": "↑ Rising",
            "falling": "↓ Falling",
            "stable": "→ Stable",
            "insufficient_data": "--",
        }
        trend_str = trend_labels.get(summary.trend_direction, "--")
        if summary.trend_ms_per_week is not None:
            sign = "+" if summary.trend_ms_per_week >= 0 else ""
            trend_detail = f"{sign}{summary.trend_ms_per_week:.1f} ms/week over last 30 days"
        else:
            trend_detail = "Requires 5+ days of data"

        cv_str = (
            f"{summary.coefficient_of_variation:.1f}%"
            if summary.coefficient_of_variation is not None
            else "--"
        )
        cv_detail = (
            "Lower % = more consistent HRV day-to-day"
            if summary.coefficient_of_variation is not None
            else "Coefficient of variation (30-day)"
        )

        self.metrics_row.addWidget(MetricCard("Latest HRV (SDNN)", latest_str, latest_detail))
        self.metrics_row.addWidget(MetricCard("7-Day Average", avg_7_str, "Rolling 7-day mean"))
        self.metrics_row.addWidget(MetricCard("30-Day Average", avg_30_str, "Rolling 30-day mean"))
        self.metrics_row.addWidget(MetricCard("30-Day Trend", trend_str, trend_detail))
        self.metrics_row.addWidget(MetricCard("Variability (CV)", cv_str, cv_detail))

        self._render_chart(summary)
        self._render_table(summary)

    def _render_chart(self, summary: HRVSummaryData) -> None:
        self.plot_widget.clear()
        records = summary.daily_records
        if not records:
            return

        x = list(range(len(records)))
        y = [r.average_ms for r in records]

        pen_daily = pg.mkPen(color="#1e6bff", width=1.5)
        self.plot_widget.plot(x, y, pen=pen_daily, connect="all")

        scatter = pg.ScatterPlotItem(
            x=x,
            y=y,
            pen=pg.mkPen(None),
            brush=pg.mkBrush("#1e6bff"),
            size=7,
        )
        self.plot_widget.addItem(scatter)

        rolling = self._rolling_average(y, window=7)
        x_rolling = [i for i, v in enumerate(rolling) if v is not None]
        y_rolling = [v for v in rolling if v is not None]
        if len(x_rolling) >= 2:
            pen_rolling = pg.mkPen(color="#ff6b35", width=2.5)
            self.plot_widget.plot(x_rolling, y_rolling, pen=pen_rolling)

        axis_pen = pg.mkPen(color="#93a8c8")
        text_pen = pg.mkPen(color="#93a8c8")
        left_axis = self.plot_widget.getAxis("left")
        bottom_axis = self.plot_widget.getAxis("bottom")
        left_axis.setLabel("HRV SDNN (ms)", color="#93a8c8")
        bottom_axis.setLabel("Day (oldest → newest)", color="#93a8c8")
        left_axis.setPen(axis_pen)
        bottom_axis.setPen(axis_pen)
        left_axis.setTextPen(text_pen)
        bottom_axis.setTextPen(text_pen)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.15)

    def _render_table(self, summary: HRVSummaryData) -> None:
        records_desc = list(reversed(summary.daily_records))
        self.table.setRowCount(len(records_desc))
        for row_idx, record in enumerate(records_desc):
            self.table.setItem(row_idx, 0, QTableWidgetItem(record.date))
            self.table.setItem(row_idx, 1, QTableWidgetItem(f"{record.average_ms:.1f}"))
            self.table.setItem(row_idx, 2, QTableWidgetItem(f"{record.min_ms:.1f}"))
            self.table.setItem(row_idx, 3, QTableWidgetItem(f"{record.max_ms:.1f}"))
            self.table.setItem(row_idx, 4, QTableWidgetItem(str(record.sample_count)))

    def _rolling_average(self, values: list[float], window: int) -> list[float | None]:
        result: list[float | None] = []
        for i in range(len(values)):
            start = max(0, i - window + 1)
            window_vals = values[start : i + 1]
            result.append(sum(window_vals) / len(window_vals) if window_vals else None)
        return result
