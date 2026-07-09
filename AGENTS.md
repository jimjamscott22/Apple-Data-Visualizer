# Repository Instructions

1. After making changes to this repository, create an implementation summary and update this file.

## Implementation Summary

### 2026-07-09
- Started implementing the SQLite → MariaDB migration plan (`docs/mariadb-migration-plan.md`), Phase 1: Connection Configuration.
- Added `pymysql` and `python-dotenv` dependencies to `pyproject.toml`.
- Added `app/database/config.py` with `DatabaseSettings` and `get_database_settings()`, sourcing MariaDB connection settings from environment variables (`APPLE_DV_DB_HOST`, `APPLE_DV_DB_PORT`, `APPLE_DV_DB_NAME`, `APPLE_DV_DB_USER`, `APPLE_DV_DB_PASSWORD`), with a `.env` file loaded via `python-dotenv` and a clear `MissingDatabaseSettingsError` when required values are absent.
- Added `.env.example` documenting the required variables (`.env` itself is already gitignored).
- Added `tests/test_database_config.py` covering defaults, full env-var construction, and the missing-required-vars error.
- Deliberately left `app/config.py` and `app/main.py` on the existing SQLite path — Phase 1 only introduces the new settings contract, it does not wire the app to it yet. That lands in Phase 3/4 of the plan.

### 2026-05-04
- Rebased the Heart / Recovery planning updates onto the current remote app implementation.
- Preserved the newer app code already merged on `main` and kept this change focused on repository instructions plus product planning docs.

### 2026-05-03
- Added the next recommended product slice after the HRV graph: a Heart / Recovery page that explains HRV using rolling baselines, resting heart rate, and sleep context.
- Updated the spec with a Heart / Recovery page contract covering expected inputs, behavior, and required initial content.
- Updated the implementation plan so Phase 6 starts with the focused Heart / Recovery slice before broader expansion work.
