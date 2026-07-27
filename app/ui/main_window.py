from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.config import APP_NAME
from app.database.config import DatabaseSettings
from app.models.dashboard import OverviewData
from app.models.imports import ImportResult
from app.services.dashboard_controller import DashboardController
from app.services.import_service import ImportService
from app.ui.import_worker import run_import_in_background
from app.ui.pages.activity_page import ActivityPage
from app.ui.pages.base import OverviewPage, PlaceholderPage
from app.ui.pages.hrv_page import HRVPage
from app.ui.pages.sleep_page import SleepPage
from app.ui.pages.trends_page import TrendsPage

HEADER_BUTTON_WIDTH = 230


class MainWindow(QMainWindow):
    def __init__(
        self,
        database_settings: DatabaseSettings,
        dashboard_controller: DashboardController,
        import_service: ImportService,
    ) -> None:
        super().__init__()
        self.database_settings = database_settings
        self.dashboard_controller = dashboard_controller
        self.import_service = import_service
        self._import_thread = None
        self._import_worker = None

        self.setWindowTitle(APP_NAME)
        self.resize(1440, 920)

        shell = QFrame()
        shell.setObjectName("AppShell")
        shell_layout = QHBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)
        self.setCentralWidget(shell)

        sidebar = self._build_sidebar()
        content = self._build_content_surface()

        shell_layout.addWidget(sidebar)
        shell_layout.addWidget(content, 1)

        self._handle_navigation_changed(0)
        self.refresh_pages()

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(250)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(20, 24, 20, 24)
        layout.setSpacing(18)

        eyebrow = QLabel("Apple Health")
        eyebrow.setObjectName("Eyebrow")
        title = QLabel("Analyzer")
        title.setObjectName("DisplayTitle")
        subtitle = QLabel("Desktop analytics for Apple Health exports")
        subtitle.setObjectName("BodyMuted")
        subtitle.setWordWrap(True)

        self.navigation = QListWidget()
        pages = ["Overview", "Sleep", "Activity", "Heart", "Trends", "Imports", "Settings"]
        for page_name in pages:
            QListWidgetItem(page_name, self.navigation)
        self.navigation.setCurrentRow(0)
        self.navigation.currentRowChanged.connect(self._handle_navigation_changed)

        layout.addWidget(eyebrow)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(8)
        layout.addWidget(self.navigation, 1)
        return sidebar

    def _build_content_surface(self) -> QWidget:
        content = QWidget()
        content.setObjectName("ContentSurface")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(18)

        header = QWidget()
        header.setObjectName("HeaderCard")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 24, 24, 24)
        header_layout.setSpacing(16)

        header_copy = QVBoxLayout()
        header_copy.setSpacing(6)

        self.page_eyebrow = QLabel("")
        self.page_eyebrow.setObjectName("Eyebrow")
        self.page_title = QLabel("")
        self.page_title.setObjectName("DisplayTitle")
        self.page_description = QLabel("")
        self.page_description.setObjectName("BodyMuted")
        self.page_description.setWordWrap(True)

        header_copy.addWidget(self.page_eyebrow)
        header_copy.addWidget(self.page_title)
        header_copy.addWidget(self.page_description)

        actions = QVBoxLayout()
        actions.setAlignment(Qt.AlignTop)

        self.import_button = QPushButton("Import Apple Health Export")
        self.import_button.setMinimumWidth(HEADER_BUTTON_WIDTH)
        self.import_button.clicked.connect(self._select_import_file)

        self.import_progress_bar = QProgressBar()
        self.import_progress_bar.setRange(0, 100)
        self.import_progress_bar.setMinimumWidth(HEADER_BUTTON_WIDTH)
        self.import_progress_bar.setVisible(False)

        self.import_status_label = QLabel("")
        self.import_status_label.setObjectName("BodyMuted")
        self.import_status_label.setMinimumWidth(HEADER_BUTTON_WIDTH)
        self.import_status_label.setWordWrap(True)
        self.import_status_label.setVisible(False)

        database_info_button = QPushButton("Database Info")
        database_info_button.setObjectName("SecondaryButton")
        database_info_button.setMinimumWidth(HEADER_BUTTON_WIDTH)
        database_info_button.clicked.connect(self._show_database_info)

        actions.addWidget(self.import_button)
        actions.addWidget(self.import_progress_bar)
        actions.addWidget(self.import_status_label)
        actions.addWidget(database_info_button)

        header_layout.addLayout(header_copy, 1)
        header_layout.addLayout(actions)

        self.page_stack = QStackedWidget()
        self.overview_page = OverviewPage()
        self.sleep_page = SleepPage(on_range_changed=self._handle_sleep_range_changed)
        self.activity_page = ActivityPage(on_range_changed=self._handle_activity_range_changed)
        self.hrv_page = HRVPage()
        self.trends_page = TrendsPage(on_range_changed=self._handle_trends_range_changed)
        self.page_stack.addWidget(self._scrollable(self.overview_page))
        self.page_stack.addWidget(self._scrollable(self.activity_page))
        self.page_stack.insertWidget(1, self._scrollable(self.sleep_page))
        self.page_stack.addWidget(self._scrollable(self.hrv_page))
        self.page_stack.addWidget(self._scrollable(self.trends_page))
        self.page_stack.addWidget(
            self._scrollable(
                PlaceholderPage(
                    "Imports page scaffold",
                    "Reserved for import history, file metadata, and data-manager controls.",
                )
            )
        )
        self.page_stack.addWidget(
            self._scrollable(
                PlaceholderPage(
                    "Settings page scaffold",
                    "Reserved for database location, date-range defaults, and theme expansion.",
                )
            )
        )

        layout.addWidget(header)
        layout.addWidget(self.page_stack, 1)
        return content

    def _scrollable(self, widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setObjectName("PageScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(widget)
        return scroll

    def refresh_pages(self) -> None:
        overview = self.dashboard_controller.load_overview()
        self.overview_page.render(overview)
        self.page_eyebrow.setText(self._format_data_freshness(overview))
        self.hrv_page.render(self.dashboard_controller.load_hrv_summary())
        self.sleep_page.render(
            self.dashboard_controller.load_sleep_summary(days=self.sleep_page.current_range())
        )
        self.activity_page.render(
            self.dashboard_controller.load_activity_summary(days=self.activity_page.current_range())
        )
        self.trends_page.render(
            self.dashboard_controller.load_trends_summary(days=self.trends_page.current_range())
        )

    def _format_data_freshness(self, overview: OverviewData) -> str:
        raw = overview.import_status.latest_data_at
        if not raw:
            return "No data imported yet"
        try:
            parsed = datetime.fromisoformat(raw)
        except ValueError:
            return "No data imported yet"
        return f"Data through {parsed.strftime('%b')} {parsed.day}"

    def _handle_sleep_range_changed(self, days: int) -> None:
        self.sleep_page.render(self.dashboard_controller.load_sleep_summary(days=days))

    def _handle_activity_range_changed(self, days: int) -> None:
        self.activity_page.render(self.dashboard_controller.load_activity_summary(days=days))

    def _handle_trends_range_changed(self, days: int) -> None:
        self.trends_page.render(self.dashboard_controller.load_trends_summary(days=days))

    def _handle_navigation_changed(self, index: int) -> None:
        self.page_stack.setCurrentIndex(index)
        page_names = ["Overview", "Sleep", "Activity", "Heart", "Trends", "Imports", "Settings"]
        descriptions = {
            "Overview": "Fast context and import status, backed by your MariaDB server.",
            "Sleep": "Nightly sleep analysis — duration, bedtime and wake trends, efficiency, consistency, and a full nightly sessions table.",
            "Activity": "Daily activity analysis — steps, walking/running distance, active-day streaks, and per-day history.",
            "Heart": "Heart Rate Variability (HRV) analysis — latest SDNN, 7- and 30-day averages, trend direction, and daily history.",
            "Trends": "Cross-metric relationships — sleep vs next-day HRV and resting HR, steps vs sleep, and weekday/weekend patterns.",
            "Imports": "Reserved for import history and duplicate-detection visibility.",
            "Settings": "Reserved for local configuration and future customization.",
        }
        page_name = page_names[index]
        self.page_title.setText(page_name)
        self.page_description.setText(descriptions[page_name])

    def _select_import_file(self) -> None:
        selected_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Apple Health Export",
            "",
            "Apple Health Exports (*.xml *.zip);;All Files (*)",
        )
        if not selected_path:
            return

        self.import_button.setEnabled(False)
        self.import_progress_bar.setValue(0)
        self.import_progress_bar.setVisible(True)
        self.import_status_label.setText("Starting import…")
        self.import_status_label.setVisible(True)

        self._import_thread, self._import_worker = run_import_in_background(
            self.import_service,
            selected_path,
            on_progress=self._handle_import_progress,
            on_finished=self._handle_import_finished,
        )

    def _handle_import_progress(self, percent: int, phase: str) -> None:
        self.import_progress_bar.setValue(percent)
        self.import_status_label.setText(phase)

    def _handle_import_finished(self, result: ImportResult) -> None:
        self.import_button.setEnabled(True)
        self.import_progress_bar.setVisible(False)
        self.import_status_label.setVisible(False)

        if result.is_success:
            self.refresh_pages()
            title = "Import Complete"
            if result.duplicate_detected:
                title = "Import Skipped"
            detail = result.message
            if result.warning_count:
                detail += f"\n\nWarnings recorded: {result.warning_count}."
            QMessageBox.information(self, title, detail)
        else:
            QMessageBox.warning(self, "Import Failed", result.message)

    def _show_database_info(self) -> None:
        settings = self.database_settings
        QMessageBox.information(
            self,
            "Database Info",
            "Connected to MariaDB:\n\n"
            f"Host: {settings.host}:{settings.port}\n"
            f"Database: {settings.database}\n"
            f"User: {settings.user}",
        )
