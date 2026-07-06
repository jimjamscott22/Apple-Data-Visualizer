from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.config import APP_NAME, AppPaths
from app.models.dashboard import OverviewData
from app.services.dashboard_controller import DashboardController
from app.services.import_service import ImportService
from app.ui.pages.base import OverviewPage, PlaceholderPage
from app.ui.pages.hrv_page import HRVPage
from app.ui.pages.sleep_page import SleepPage
from app.ui.pages.trends_page import TrendsPage

HEADER_BUTTON_WIDTH = 230


class MainWindow(QMainWindow):
    def __init__(
        self,
        app_paths: AppPaths,
        dashboard_controller: DashboardController,
        import_service: ImportService,
    ) -> None:
        super().__init__()
        self.app_paths = app_paths
        self.dashboard_controller = dashboard_controller
        self.import_service = import_service

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
        reveal_button = QPushButton("Open Data Folder")
        reveal_button.setObjectName("SecondaryButton")
        reveal_button.setMinimumWidth(HEADER_BUTTON_WIDTH)
        reveal_button.clicked.connect(self._show_data_folder)

        actions.addWidget(self.import_button)
        actions.addWidget(reveal_button)

        header_layout.addLayout(header_copy, 1)
        header_layout.addLayout(actions)

        self.page_stack = QStackedWidget()
        self.overview_page = OverviewPage()
        self.sleep_page = SleepPage(on_range_changed=self._handle_sleep_range_changed)
        self.hrv_page = HRVPage()
        self.trends_page = TrendsPage(on_range_changed=self._handle_trends_range_changed)
        self.page_stack.addWidget(self._scrollable(self.overview_page))
        self.page_stack.addWidget(
            self._scrollable(
                PlaceholderPage(
                    "Activity page scaffold",
                    "Reserved for steps, movement trends, and active-day summaries.",
                )
            )
        )
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

    def _handle_trends_range_changed(self, days: int) -> None:
        self.trends_page.render(self.dashboard_controller.load_trends_summary(days=days))

    def _handle_navigation_changed(self, index: int) -> None:
        self.page_stack.setCurrentIndex(index)
        page_names = ["Overview", "Sleep", "Activity", "Heart", "Trends", "Imports", "Settings"]
        descriptions = {
            "Overview": "Fast context and import status, backed by the local SQLite foundation.",
            "Sleep": "Nightly sleep analysis — duration, bedtime and wake trends, efficiency, consistency, and a full nightly sessions table.",
            "Activity": "Reserved for steps and movement summaries.",
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

        result = self.import_service.import_file(selected_path)
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

    def _show_data_folder(self) -> None:
        folder = self.app_paths.database_path.parent
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
