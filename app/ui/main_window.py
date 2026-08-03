from __future__ import annotations

from datetime import datetime
from pathlib import Path

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
from app.preferences import AppPreferences, PreferenceStore
from app.services.dashboard_controller import DashboardController
from app.services.import_service import ImportService
from app.ui.import_worker import run_import_in_background
from app.ui.pages.activity_page import ActivityPage
from app.ui.pages.base import OverviewPage
from app.ui.pages.hrv_page import HRVPage
from app.ui.pages.imports_page import ImportsPage
from app.ui.pages.sleep_page import SleepPage
from app.ui.pages.settings_page import SettingsPage
from app.ui.pages.trends_page import TrendsPage

HEADER_BUTTON_WIDTH = 230


class MainWindow(QMainWindow):
    def __init__(
        self,
        database_settings: DatabaseSettings,
        dashboard_controller: DashboardController,
        import_service: ImportService,
        preference_store: PreferenceStore,
        preferences: AppPreferences,
        app_version: str,
    ) -> None:
        super().__init__()
        self.database_settings = database_settings
        self.dashboard_controller = dashboard_controller
        self.import_service = import_service
        self.preference_store = preference_store
        self.preferences = preferences
        self.app_version = app_version
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

        initial_page = self.preference_store.last_page_index() if preferences.restore_last_page else 0
        if not 0 <= initial_page < self.page_stack.count():
            initial_page = 0
        self.navigation.blockSignals(True)
        self.navigation.setCurrentRow(initial_page)
        self.navigation.blockSignals(False)
        self._handle_navigation_changed(initial_page)
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

        settings_button = QPushButton("Settings")
        settings_button.setObjectName("SecondaryButton")
        settings_button.setMinimumWidth(HEADER_BUTTON_WIDTH)
        settings_button.clicked.connect(self._navigate_to_settings)

        actions.addWidget(self.import_button)
        actions.addWidget(self.import_progress_bar)
        actions.addWidget(self.import_status_label)
        actions.addWidget(settings_button)

        header_layout.addLayout(header_copy, 1)
        header_layout.addLayout(actions)

        self.page_stack = QStackedWidget()
        self.overview_page = OverviewPage()
        self.sleep_page = SleepPage(on_range_changed=self._handle_sleep_range_changed)
        self.activity_page = ActivityPage(on_range_changed=self._handle_activity_range_changed)
        self.sleep_page = SleepPage(
            on_range_changed=self._handle_sleep_range_changed,
            initial_range=self.preferences.sleep_range_days,
            clock_format=self.preferences.clock_format,
        )
        self.hrv_page = HRVPage()
        self.trends_page = TrendsPage(
            on_range_changed=self._handle_trends_range_changed,
            initial_range=self.preferences.trends_range_days,
        )
        self.imports_page = ImportsPage()
        self.imports_page.refresh_requested.connect(self._refresh_imports_page)
        self.settings_page = SettingsPage(
            database_settings=self.database_settings,
            app_version=self.app_version,
            preferences=self.preferences,
        )
        self.settings_page.preferences_saved.connect(self._apply_preferences)
        self.settings_page.defaults_requested.connect(self._restore_default_preferences)
        self.page_stack.addWidget(self._scrollable(self.overview_page))
        self.page_stack.addWidget(self._scrollable(self.activity_page))
        self.page_stack.insertWidget(1, self._scrollable(self.sleep_page))
        self.page_stack.addWidget(self._scrollable(self.hrv_page))
        self.page_stack.addWidget(self._scrollable(self.trends_page))
        self.page_stack.addWidget(self._scrollable(self.imports_page))
        self.page_stack.addWidget(self._scrollable(self.settings_page))

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
        self._refresh_imports_page()

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

    def _refresh_imports_page(self) -> None:
        self.imports_page.render(self.dashboard_controller.load_imports_summary(limit=50))

    def _handle_navigation_changed(self, index: int) -> None:
        if not 0 <= index < self.page_stack.count():
            return
        self.page_stack.setCurrentIndex(index)
        self.preference_store.set_last_page_index(index)
        page_names = ["Overview", "Sleep", "Activity", "Heart", "Trends", "Imports", "Settings"]
        descriptions = {
            "Overview": "Fast context and import status, backed by your MariaDB server.",
            "Sleep": "Nightly sleep analysis — duration, bedtime and wake trends, efficiency, consistency, and a full nightly sessions table.",
            "Activity": "Daily activity analysis — steps, walking/running distance, active-day streaks, and per-day history.",
            "Heart": "Heart Rate Variability (HRV) analysis — latest SDNN, 7- and 30-day averages, trend direction, and daily history.",
            "Trends": "Cross-metric relationships — sleep vs next-day HRV and resting HR, steps vs sleep, and weekday/weekend patterns.",
            "Imports": "Database status, record inventory, and the 50 most recent import attempts.",
            "Settings": "Analysis defaults, display preferences, and application information.",
        }
        page_name = page_names[index]
        self.page_title.setText(page_name)
        self.page_description.setText(descriptions[page_name])

    def _select_import_file(self) -> None:
        initial_directory = ""
        if self.preferences.remember_import_directory:
            remembered = Path(self.preference_store.last_import_directory())
            if remembered.is_dir():
                initial_directory = str(remembered)
        selected_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Apple Health Export",
            initial_directory,
            "Apple Health Exports (*.xml *.zip);;All Files (*)",
        )
        if not selected_path:
            return
        if self.preferences.remember_import_directory:
            self.preference_store.set_last_import_directory(str(Path(selected_path).parent))

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
            self._refresh_imports_page()
            QMessageBox.warning(self, "Import Failed", result.message)

    def _navigate_to_settings(self) -> None:
        self.navigation.setCurrentRow(6)

    def _apply_preferences(self, preferences: AppPreferences) -> None:
        self.preference_store.save(preferences)
        if not preferences.remember_import_directory:
            self.preference_store.clear_last_import_directory()
        self.preferences = preferences
        self.settings_page.set_preferences(preferences)
        self.sleep_page.set_range(preferences.sleep_range_days)
        self.sleep_page.set_clock_format(preferences.clock_format)
        self.trends_page.set_range(preferences.trends_range_days)
        self.refresh_pages()
        self.settings_page.show_saved()

    def _restore_default_preferences(self) -> None:
        defaults = self.preference_store.reset()
        self._apply_preferences(defaults)
        self.settings_page.show_saved("Default settings restored.")
