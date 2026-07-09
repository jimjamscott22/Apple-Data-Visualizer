from __future__ import annotations

import pytest

from app.database.config import (
    DEFAULT_DATABASE_NAME,
    DEFAULT_PORT,
    MissingDatabaseSettingsError,
    get_database_settings,
)

_ALL_ENV_VARS = (
    "APPLE_DV_DB_HOST",
    "APPLE_DV_DB_PORT",
    "APPLE_DV_DB_NAME",
    "APPLE_DV_DB_USER",
    "APPLE_DV_DB_PASSWORD",
)


@pytest.fixture(autouse=True)
def _clear_db_env_vars(monkeypatch):
    for name in _ALL_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def _set_required_env_vars(monkeypatch, **overrides):
    values = {
        "APPLE_DV_DB_HOST": "192.168.1.50",
        "APPLE_DV_DB_USER": "apple_health_app",
        "APPLE_DV_DB_PASSWORD": "super-secret",
        **overrides,
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)


class TestGetDatabaseSettings:
    def test_builds_settings_from_env_vars(self, monkeypatch):
        _set_required_env_vars(
            monkeypatch,
            APPLE_DV_DB_PORT="3307",
            APPLE_DV_DB_NAME="apple_health_data_test",
        )

        settings = get_database_settings()

        assert settings.host == "192.168.1.50"
        assert settings.port == 3307
        assert settings.database == "apple_health_data_test"
        assert settings.user == "apple_health_app"
        assert settings.password == "super-secret"

    def test_applies_defaults_for_optional_settings(self, monkeypatch):
        _set_required_env_vars(monkeypatch)

        settings = get_database_settings()

        assert settings.port == DEFAULT_PORT
        assert settings.database == DEFAULT_DATABASE_NAME

    def test_raises_clear_error_when_required_vars_missing(self, monkeypatch):
        with pytest.raises(MissingDatabaseSettingsError) as excinfo:
            get_database_settings()

        message = str(excinfo.value)
        assert "APPLE_DV_DB_HOST" in message
        assert "APPLE_DV_DB_USER" in message
        assert "APPLE_DV_DB_PASSWORD" in message

    def test_raises_when_only_some_required_vars_present(self, monkeypatch):
        monkeypatch.setenv("APPLE_DV_DB_HOST", "192.168.1.50")

        with pytest.raises(MissingDatabaseSettingsError) as excinfo:
            get_database_settings()

        message = str(excinfo.value)
        assert "APPLE_DV_DB_HOST" not in message
        assert "APPLE_DV_DB_USER" in message
        assert "APPLE_DV_DB_PASSWORD" in message
