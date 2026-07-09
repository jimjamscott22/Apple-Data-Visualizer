from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

HOST_ENV_VAR = "APPLE_DV_DB_HOST"
PORT_ENV_VAR = "APPLE_DV_DB_PORT"
NAME_ENV_VAR = "APPLE_DV_DB_NAME"
USER_ENV_VAR = "APPLE_DV_DB_USER"
PASSWORD_ENV_VAR = "APPLE_DV_DB_PASSWORD"

DEFAULT_PORT = 3306
DEFAULT_DATABASE_NAME = "apple_health_data"

_REQUIRED_ENV_VARS = (HOST_ENV_VAR, USER_ENV_VAR, PASSWORD_ENV_VAR)


class MissingDatabaseSettingsError(RuntimeError):
    """Raised when required MariaDB connection settings are not configured."""


@dataclass(frozen=True)
class DatabaseSettings:
    host: str
    port: int
    database: str
    user: str
    password: str


def get_database_settings() -> DatabaseSettings:
    """Build MariaDB connection settings from environment variables.

    Loads a local `.env` file first (if present) so development setups can
    keep credentials out of the shell environment. See `.env.example` and
    the "Database Setup (MariaDB)" section of README.md for how these
    values are provisioned.
    """
    missing = [name for name in _REQUIRED_ENV_VARS if not os.environ.get(name)]
    if missing:
        raise MissingDatabaseSettingsError(
            "Missing required MariaDB connection settings: "
            f"{', '.join(missing)}. Set them as environment variables or in a "
            "local .env file (copy .env.example to .env and fill it in)."
        )

    return DatabaseSettings(
        host=os.environ[HOST_ENV_VAR],
        port=int(os.environ.get(PORT_ENV_VAR, DEFAULT_PORT)),
        database=os.environ.get(NAME_ENV_VAR, DEFAULT_DATABASE_NAME),
        user=os.environ[USER_ENV_VAR],
        password=os.environ[PASSWORD_ENV_VAR],
    )
