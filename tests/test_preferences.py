from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QLabel

from app.database.config import DatabaseSettings
from app.preferences import AppPreferences, PreferenceStore
from app.ui.pages.settings_page import SettingsPage
from app.ui.pages.sleep_page import _format_clock_hours, _format_clock_time


def _store(tmp_path) -> PreferenceStore:
    settings = QSettings(str(tmp_path / "preferences.ini"), QSettings.IniFormat)
    settings.clear()
    return PreferenceStore(settings)


def _application() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_preferences_round_trip(tmp_path):
    store = _store(tmp_path)
    expected = AppPreferences(
        sleep_range_days=90,
        trends_range_days=365,
        clock_format="12-hour",
        remember_import_directory=False,
        restore_last_page=False,
    )

    store.save(expected)

    assert store.load() == expected


def test_invalid_persisted_values_fall_back_to_defaults(tmp_path):
    settings = QSettings(str(tmp_path / "preferences.ini"), QSettings.IniFormat)
    settings.setValue("analysis/sleep_range_days", 14)
    settings.setValue("analysis/trends_range_days", "all")
    settings.setValue("display/clock_format", "local")
    settings.setValue("imports/remember_directory", "not-a-boolean")
    store = PreferenceStore(settings)

    assert store.load() == AppPreferences()


def test_reset_restores_defaults_and_clears_session_state(tmp_path):
    store = _store(tmp_path)
    store.save(
        AppPreferences(
            sleep_range_days=7,
            trends_range_days=30,
            clock_format="12-hour",
            remember_import_directory=False,
            restore_last_page=False,
        )
    )
    store.set_last_import_directory("/tmp/imports")
    store.set_last_page_index(6)

    assert store.reset() == AppPreferences()
    assert store.load() == AppPreferences()
    assert store.last_import_directory() == ""
    assert store.last_page_index() == 0


def test_settings_page_emits_preferences_without_rendering_password():
    _application()
    database_settings = DatabaseSettings(
        host="db.example.test",
        port=3307,
        database="health",
        user="health_reader",
        password="do-not-display",
    )
    page = SettingsPage(database_settings, "1.2.3", AppPreferences())
    emitted: list[AppPreferences] = []
    page.preferences_saved.connect(emitted.append)

    page.sleep_range_combo.setCurrentIndex(page.sleep_range_combo.findData(90))
    page.trends_range_combo.setCurrentIndex(page.trends_range_combo.findData(365))
    page.clock_format_combo.setCurrentIndex(page.clock_format_combo.findData("12-hour"))
    page.remember_import_directory_checkbox.setChecked(False)
    page.restore_last_page_checkbox.setChecked(False)
    page._save()

    assert emitted == [
        AppPreferences(
            sleep_range_days=90,
            trends_range_days=365,
            clock_format="12-hour",
            remember_import_directory=False,
            restore_last_page=False,
        )
    ]
    rendered_text = " ".join(label.text() for label in page.findChildren(QLabel))
    assert "db.example.test:3307" in rendered_text
    assert "health_reader" in rendered_text
    assert "do-not-display" not in rendered_text


def test_clock_formatters_support_12_and_24_hour_display():
    value = "2026-07-29 22:05:00"

    assert _format_clock_time(value, use_24_hour=True) == "22:05"
    assert _format_clock_time(value, use_24_hour=False) == "10:05 PM"
    assert (
        _format_clock_hours(10.5, offset_from_noon=True, use_24_hour=False)
        == "10:30 PM"
    )
