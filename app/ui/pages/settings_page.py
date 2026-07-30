from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.database.config import DatabaseSettings
from app.preferences import (
    CLOCK_FORMAT_OPTIONS,
    SLEEP_RANGE_OPTIONS,
    TRENDS_RANGE_OPTIONS,
    AppPreferences,
)


class SettingsPage(QWidget):
    preferences_saved = Signal(object)
    defaults_requested = Signal()

    def __init__(
        self,
        database_settings: DatabaseSettings,
        app_version: str,
        preferences: AppPreferences,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("PageRoot")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        layout.addWidget(self._build_analysis_card())
        layout.addWidget(self._build_display_card())
        layout.addWidget(self._build_behavior_card())
        layout.addWidget(self._build_connection_card(database_settings, app_version))

        actions = QHBoxLayout()
        self.status_label = QLabel("")
        self.status_label.setObjectName("SettingsStatus")
        self.status_label.setAccessibleName("Settings save status")

        reset_button = QPushButton("Restore Defaults")
        reset_button.setObjectName("SecondaryButton")
        reset_button.clicked.connect(self._confirm_reset)

        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(self._save)

        actions.addWidget(self.status_label, 1)
        actions.addWidget(reset_button)
        actions.addWidget(save_button)
        layout.addLayout(actions)
        layout.addStretch()

        self.set_preferences(preferences)

    def _build_analysis_card(self) -> QFrame:
        card, layout = _settings_card(
            "Analysis defaults",
            "Choose the range selected when analytics pages open.",
        )
        form = QFormLayout()
        form.setSpacing(12)

        self.sleep_range_combo = QComboBox()
        for days in SLEEP_RANGE_OPTIONS:
            self.sleep_range_combo.addItem(f"{days} days", days)
        self.sleep_range_combo.setAccessibleName("Default Sleep range")

        self.trends_range_combo = QComboBox()
        for days in TRENDS_RANGE_OPTIONS:
            self.trends_range_combo.addItem(f"{days} days", days)
        self.trends_range_combo.setAccessibleName("Default Trends range")

        form.addRow("Sleep range:", self.sleep_range_combo)
        form.addRow("Trends range:", self.trends_range_combo)
        layout.addLayout(form)
        return card

    def _build_display_card(self) -> QFrame:
        card, layout = _settings_card(
            "Display",
            "Control how times are presented throughout the dashboard.",
        )
        form = QFormLayout()
        form.setSpacing(12)

        self.clock_format_combo = QComboBox()
        for clock_format in CLOCK_FORMAT_OPTIONS:
            self.clock_format_combo.addItem(clock_format, clock_format)
        self.clock_format_combo.setAccessibleName("Clock format")
        form.addRow("Clock format:", self.clock_format_combo)
        layout.addLayout(form)

        theme_note = QLabel("Theme: Dark (additional themes are not yet available)")
        theme_note.setObjectName("BodyMuted")
        theme_note.setWordWrap(True)
        layout.addWidget(theme_note)
        return card

    def _build_behavior_card(self) -> QFrame:
        card, layout = _settings_card(
            "Application behavior",
            "Remember useful local context between application sessions.",
        )
        self.remember_import_directory_checkbox = QCheckBox(
            "Remember the last folder used to import an Apple Health export"
        )
        self.restore_last_page_checkbox = QCheckBox(
            "Reopen the last visited page when the application starts"
        )
        layout.addWidget(self.remember_import_directory_checkbox)
        layout.addWidget(self.restore_last_page_checkbox)
        return card

    def _build_connection_card(
        self,
        database_settings: DatabaseSettings,
        app_version: str,
    ) -> QFrame:
        card, layout = _settings_card(
            "Connection and application",
            "Connection details are read-only and credentials remain hidden.",
        )
        form = QFormLayout()
        form.setSpacing(10)
        status = QLabel("Connected")
        status.setObjectName("ConnectionStatus")
        form.addRow("Database status:", status)
        form.addRow("Host:", QLabel(f"{database_settings.host}:{database_settings.port}"))
        form.addRow("Database:", QLabel(database_settings.database))
        form.addRow("User:", QLabel(database_settings.user))
        form.addRow("Application version:", QLabel(app_version))
        layout.addLayout(form)
        return card

    def set_preferences(self, preferences: AppPreferences) -> None:
        _select_data(self.sleep_range_combo, preferences.sleep_range_days)
        _select_data(self.trends_range_combo, preferences.trends_range_days)
        _select_data(self.clock_format_combo, preferences.clock_format)
        self.remember_import_directory_checkbox.setChecked(
            preferences.remember_import_directory
        )
        self.restore_last_page_checkbox.setChecked(preferences.restore_last_page)

    def show_saved(self, message: str = "Settings saved.") -> None:
        self.status_label.setText(message)

    def _save(self) -> None:
        self.preferences_saved.emit(
            AppPreferences(
                sleep_range_days=int(self.sleep_range_combo.currentData()),
                trends_range_days=int(self.trends_range_combo.currentData()),
                clock_format=str(self.clock_format_combo.currentData()),
                remember_import_directory=self.remember_import_directory_checkbox.isChecked(),
                restore_last_page=self.restore_last_page_checkbox.isChecked(),
            )
        )

    def _confirm_reset(self) -> None:
        response = QMessageBox.question(
            self,
            "Restore Default Settings",
            "Restore all application preferences to their defaults?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if response == QMessageBox.Yes:
            self.defaults_requested.emit()


def _settings_card(title: str, description: str) -> tuple[QFrame, QVBoxLayout]:
    card = QFrame()
    card.setObjectName("SettingsCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(22, 22, 22, 22)
    layout.setSpacing(12)

    title_label = QLabel(title)
    title_label.setObjectName("SectionTitle")
    description_label = QLabel(description)
    description_label.setObjectName("BodyMuted")
    description_label.setWordWrap(True)
    layout.addWidget(title_label)
    layout.addWidget(description_label)
    return card, layout


def _select_data(combo: QComboBox, value: object) -> None:
    index = combo.findData(value)
    if index >= 0:
        combo.setCurrentIndex(index)
