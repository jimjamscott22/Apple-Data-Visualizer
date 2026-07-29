from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QSettings

SLEEP_RANGE_OPTIONS = (7, 30, 90)
TRENDS_RANGE_OPTIONS = (30, 90, 365)
CLOCK_FORMAT_OPTIONS = ("12-hour", "24-hour")


@dataclass(frozen=True)
class AppPreferences:
    sleep_range_days: int = 30
    trends_range_days: int = 90
    clock_format: str = "24-hour"
    remember_import_directory: bool = True
    restore_last_page: bool = True


class PreferenceStore:
    """Persist local UI preferences separately from health data."""

    def __init__(self, settings: QSettings | None = None) -> None:
        self._settings = settings or QSettings()

    def load(self) -> AppPreferences:
        defaults = AppPreferences()
        return AppPreferences(
            sleep_range_days=self._choice(
                "analysis/sleep_range_days",
                defaults.sleep_range_days,
                SLEEP_RANGE_OPTIONS,
            ),
            trends_range_days=self._choice(
                "analysis/trends_range_days",
                defaults.trends_range_days,
                TRENDS_RANGE_OPTIONS,
            ),
            clock_format=self._choice(
                "display/clock_format",
                defaults.clock_format,
                CLOCK_FORMAT_OPTIONS,
            ),
            remember_import_directory=self._boolean(
                "imports/remember_directory",
                defaults.remember_import_directory,
            ),
            restore_last_page=self._boolean(
                "navigation/restore_last_page",
                defaults.restore_last_page,
            ),
        )

    def save(self, preferences: AppPreferences) -> None:
        self._settings.setValue("analysis/sleep_range_days", preferences.sleep_range_days)
        self._settings.setValue("analysis/trends_range_days", preferences.trends_range_days)
        self._settings.setValue("display/clock_format", preferences.clock_format)
        self._settings.setValue(
            "imports/remember_directory",
            preferences.remember_import_directory,
        )
        self._settings.setValue(
            "navigation/restore_last_page",
            preferences.restore_last_page,
        )
        self._settings.sync()

    def reset(self) -> AppPreferences:
        defaults = AppPreferences()
        self.save(defaults)
        self.clear_last_import_directory()
        self.set_last_page_index(0)
        return defaults

    def last_import_directory(self) -> str:
        return str(self._settings.value("session/last_import_directory", ""))

    def set_last_import_directory(self, directory: str) -> None:
        self._settings.setValue("session/last_import_directory", directory)
        self._settings.sync()

    def clear_last_import_directory(self) -> None:
        self._settings.remove("session/last_import_directory")
        self._settings.sync()

    def last_page_index(self) -> int:
        try:
            return int(self._settings.value("session/last_page_index", 0))
        except (TypeError, ValueError):
            return 0

    def set_last_page_index(self, index: int) -> None:
        self._settings.setValue("session/last_page_index", index)
        self._settings.sync()

    def _choice(self, key: str, default, valid_options):
        value = self._settings.value(key, default)
        try:
            candidate = type(default)(value)
        except (TypeError, ValueError):
            return default
        return candidate if candidate in valid_options else default

    def _boolean(self, key: str, default: bool) -> bool:
        value = self._settings.value(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "on"}:
                return True
            if normalized in {"false", "0", "no", "off"}:
                return False
        return default
