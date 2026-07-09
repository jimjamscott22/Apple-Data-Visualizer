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
- Completed Phase 2: Schema Port. Added `app/database/schema.py` with `MARIADB_SCHEMA_STATEMENTS`, an ordered tuple of MariaDB DDL translating the existing SQLite schema per `docs/mariadb-migration-spec.md`'s translation table (`AUTO_INCREMENT`, `DATETIME`/`DATE` temporal columns, `JSON` for `metadata_json`/`summary_json`, `InnoDB`/`utf8mb4`). Kept `import_history.notes` as `TEXT` rather than `JSON` since `DatabaseManager.log_failed_import` writes a plain exception string into it while other call sites write `json.dumps(...)` — a native `JSON` column would reject the plain-string writes.
- Verified the DDL directly against a real local MariaDB 10.11 server (installed in this session for testing only): applied cleanly, re-ran idempotently, and `SHOW CREATE TABLE` matched the intended shape including the FK constraints and the `daily_summaries` unique key.
- Added `tests/test_database_schema.py`: static structural checks (all four tables created, FK-referenced tables created before their dependents, every statement is `IF NOT EXISTS`, the `notes`-stays-`TEXT` decision) that always run, plus a live-MariaDB round-trip test that creates/drops a throwaway database and is skipped automatically when no server is reachable (reads `APPLE_DV_TEST_DB_HOST/PORT/USER/PASSWORD`, defaulting to `127.0.0.1:3306`/`root`).
- `app/database/manager.py` still targets SQLite; wiring `DatabaseManager` to this schema and PyMySQL is Phase 3.

### 2026-05-04
- Rebased the Heart / Recovery planning updates onto the current remote app implementation.
- Preserved the newer app code already merged on `main` and kept this change focused on repository instructions plus product planning docs.

### 2026-05-03
- Added the next recommended product slice after the HRV graph: a Heart / Recovery page that explains HRV using rolling baselines, resting heart rate, and sleep context.
- Updated the spec with a Heart / Recovery page contract covering expected inputs, behavior, and required initial content.
- Updated the implementation plan so Phase 6 starts with the focused Heart / Recovery slice before broader expansion work.
