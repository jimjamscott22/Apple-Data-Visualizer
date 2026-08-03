from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox, QPushButton

from app.database.config import DatabaseSettings
from app.models.activity import ActivitySummaryData
from app.models.dashboard import OverviewData
from app.models.hrv import HRVSummaryData
from app.models.imports import (
    DatabaseStatusData,
    ImportHistoryRecord,
    ImportResult,
    ImportStatistics,
    ImportsSummaryData,
    MetricInventoryRecord,
)
from app.models.sleep import SleepSummaryData
from app.models.trends import TrendsSummaryData
from app.preferences import AppPreferences
from app.ui.main_window import MainWindow
from app.ui.pages.imports_page import ImportsPage


def _application() -> QApplication:
    return QApplication.instance() or QApplication([])


def _summary() -> ImportsSummaryData:
    return ImportsSummaryData(
        database_status=DatabaseStatusData(
            "Connected", "db.example.test", 3307, "health", "health_reader"
        ),
        statistics=ImportStatistics(1, 12_345, 2, 1),
        inventory=(
            MetricInventoryRecord(
                "step_count",
                "Step Count",
                12_000,
                "2026-07-01 08:00:00",
                "2026-07-31 18:00:00",
                "count",
            ),
        ),
        history=(
            ImportHistoryRecord(
                30,
                "completed.zip",
                "C:/Health/completed.zip",
                2048,
                "completed",
                "Completed",
                12_000,
                2,
                "2026-08-02 08:00:00",
                "zip",
                ("Skipped unsupported record type.", "A second warning."),
            ),
            ImportHistoryRecord(
                29,
                "duplicate.xml",
                "C:/Health/duplicate.xml",
                1024,
                "duplicate",
                "Duplicate",
                0,
                0,
                "2026-08-01 08:00:00",
                duplicate_of_import_id=30,
            ),
            ImportHistoryRecord(
                28,
                "failed.xml",
                "C:/Health/failed.xml",
                10,
                "failed",
                "Failed",
                0,
                0,
                "2026-07-31 08:00:00",
                detail_message="Could not parse export.xml",
            ),
            ImportHistoryRecord(
                27,
                "active.xml",
                "C:/Health/active.xml",
                None,
                "in_progress",
                "In progress",
                5,
                0,
                "2026-07-30 08:00:00",
            ),
        ),
    )


def test_empty_inventory_and_history_render_independently():
    _application()
    page = ImportsPage()
    page.show()
    empty_history = ImportsSummaryData(
        DatabaseStatusData("Connected", "db", 3306, "health", "reader"),
        ImportStatistics(),
        inventory=(MetricInventoryRecord("step_count", "Step Count", 1, None, None, None),),
    )

    page.render(empty_history)

    assert page.inventory_table.isVisible() is True
    assert page.inventory_empty.isVisible() is False
    assert page.history_table.isVisible() is False
    assert page.history_empty.isVisible() is True
    assert page.detail_card.isVisible() is False


def test_populated_page_renders_statistics_tables_selection_and_safe_details():
    _application()
    page = ImportsPage()
    page.show()
    page.render(_summary())

    rendered_text = " ".join(label.text() for label in page.findChildren(QLabel))
    assert "1" in rendered_text
    assert "12,345" in rendered_text
    assert "2" in rendered_text
    assert page.inventory_table.rowCount() == 1
    assert page.inventory_table.focusPolicy() == Qt.StrongFocus
    assert page.history_table.rowCount() == 4
    assert page.history_table.item(0, 0).data(Qt.UserRole) == 30
    assert page._selected_import_id() == 30
    assert "• Skipped unsupported record type." in page.detail_context_label.text()
    assert "do-not-display" not in rendered_text
    assert "fingerprint" not in rendered_text.lower()

    page.history_table.selectRow(1)
    assert page._selected_import_id() == 29
    assert "Duplicate of import #30" in page.detail_context_label.text()
    assert "No records were inserted." in page.detail_context_label.text()

    page.history_table.selectRow(2)
    assert page._selected_import_id() == 28
    assert page.detail_context_label.text() == "Could not parse export.xml"

    page.history_table.selectRow(3)
    assert page._selected_import_id() == 27
    assert "has not reached a terminal state" in page.detail_context_label.text()


def test_empty_inventory_does_not_hide_populated_history():
    _application()
    page = ImportsPage()
    page.show()
    summary = _summary()
    page.render(
        ImportsSummaryData(
            summary.database_status,
            summary.statistics,
            inventory=(),
            history=summary.history,
        )
    )

    assert page.inventory_table.isVisible() is False
    assert page.inventory_empty.isVisible() is True
    assert page.history_table.isVisible() is True
    assert page._selected_import_id() == 30


def test_render_preserves_selected_import_and_refresh_signal_emits():
    _application()
    page = ImportsPage()
    page.render(_summary())
    page.history_table.selectRow(1)

    page.render(_summary())
    assert page._selected_import_id() == 29

    summary = _summary()
    page.render(
        ImportsSummaryData(
            summary.database_status,
            summary.statistics,
            summary.inventory,
            history=(summary.history[0], summary.history[2]),
        )
    )
    assert page._selected_import_id() == 30

    emitted: list[bool] = []
    page.refresh_requested.connect(lambda: emitted.append(True))
    refresh_button = next(
        widget
        for widget in page.findChildren(QPushButton)
        if widget.text() == "Refresh"
    )
    refresh_button.click()
    assert emitted == [True]


class _DashboardControllerFake:
    def __init__(self) -> None:
        self.calls: dict[str, int] = {}

    def _record_call(self, name: str) -> None:
        self.calls[name] = self.calls.get(name, 0) + 1

    def load_overview(self) -> OverviewData:
        self._record_call("overview")
        return OverviewData()

    def load_sleep_summary(self, *, days: int) -> SleepSummaryData:
        self._record_call("sleep")
        return SleepSummaryData(days, None, None, None, None, None, None)

    def load_activity_summary(self, *, days: int) -> ActivitySummaryData:
        self._record_call("activity")
        return ActivitySummaryData(days, 10_000, 0, 0, None, None, None, None, None, None)

    def load_hrv_summary(self) -> HRVSummaryData:
        self._record_call("hrv")
        return HRVSummaryData(None, None, None, None, "insufficient_data", None, None)

    def load_trends_summary(self, *, days: int) -> TrendsSummaryData:
        self._record_call("trends")
        return TrendsSummaryData(days)

    def load_imports_summary(self, *, limit: int) -> ImportsSummaryData:
        assert limit == 50
        self._record_call("imports")
        return _summary()


class _PreferenceStoreFake:
    def last_page_index(self) -> int:
        return 0

    def set_last_page_index(self, index: int) -> None:
        pass


def _main_window(controller: _DashboardControllerFake) -> MainWindow:
    return MainWindow(
        database_settings=DatabaseSettings("db.example.test", 3307, "health", "reader", "secret"),
        dashboard_controller=controller,
        import_service=object(),
        preference_store=_PreferenceStoreFake(),
        preferences=AppPreferences(restore_last_page=False),
        app_version="test",
    )


def test_main_window_refreshes_imports_on_request_and_after_failed_import(monkeypatch):
    _application()
    controller = _DashboardControllerFake()
    window = _main_window(controller)

    initial_calls = dict(controller.calls)
    window.imports_page.refresh_requested.emit()
    assert controller.calls["imports"] == initial_calls["imports"] + 1

    monkeypatch.setattr(QMessageBox, "warning", lambda *args: None)
    before_failure = dict(controller.calls)
    window._handle_import_finished(ImportResult(False, "failed", "Unable to parse export."))

    assert controller.calls["imports"] == before_failure["imports"] + 1
    assert {
        name: controller.calls[name]
        for name in ("overview", "sleep", "activity", "hrv", "trends")
    } == {
        name: before_failure[name]
        for name in ("overview", "sleep", "activity", "hrv", "trends")
    }
