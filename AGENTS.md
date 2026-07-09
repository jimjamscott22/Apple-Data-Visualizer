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
- Completed Phase 3: `DatabaseManager` Port. `app/database/manager.py` now takes a `DatabaseSettings` instead of a SQLite path, connects via PyMySQL with `DictCursor`, uses `%s` placeholders throughout, bootstraps via `MARIADB_SCHEMA_STATEMENTS`, and replaces `datetime('now', '-N days')`/`date('now', ...)` with `DATE_SUB(NOW(), INTERVAL %s DAY)`/`DATE_SUB(CURDATE(), INTERVAL %s DAY)`, `substr(start_at, 1, 10)` with `DATE(start_at)`, and the SQLite `ON CONFLICT ... DO UPDATE` upsert with `ON DUPLICATE KEY UPDATE ... VALUES(...)`. Added derived-table aliases (`AS recent_nights`, `AS recent_days`) that MariaDB requires but SQLite didn't.
- Added `app/database/errors.py` with `DatabaseConnectionError`, raised by `DatabaseManager.connect()` when the PyMySQL connection attempt itself fails (bad host/credentials), so the UI layer can catch a specific type in Phase 4 instead of a raw driver exception.
- Preserved the import transaction's atomicity intentionally: `connect()` now uses `autocommit=False` (the PyMySQL/MariaDB default). Methods that own their connection commit explicitly after writing. The `begin_import`/`append_import_records`/`complete_import` trio shares one caller-supplied connection (as `ImportService.import_file` already did) and only `complete_import` commits — so if the parser raises mid-import, the connection closes without committing and the whole in-progress import (including the `begin_import` row) rolls back, matching the original SQLite behavior where `ImportService`'s `with database_manager.connect() as connection:` block committed only on clean exit.
- Updated stale `sqlite3.Row` docstring references in `app/services/hrv_analysis_service.py` and `app/services/trends_analysis_service.py` to `dict` (their actual shape now, and always was in practice since both types support `row["column"]` access).
- Verified the ported manager against a real local MariaDB 10.11 server with a new `tests/test_database_manager.py` (10 tests, same self-skip-when-no-server pattern as the schema tests): init/idempotency, bad-credential connection errors, `persist_import` + duplicate detection, the begin/append/complete transaction on both the success path and — importantly — the mid-import-failure rollback path, sleep-session replacement scoping, and the `daily_summaries` upsert aggregating repeated same-day records instead of duplicating rows. Full suite: 38 passed against a live server, 27 passed / 11 skipped without one.
- `app/config.py` and `app/main.py` are still untouched and still construct the old SQLite-path `DatabaseManager` — the app will not run end-to-end again until Phase 4 rewires `main.py` to build `DatabaseSettings` and handle connection failures in the UI.

### 2026-05-04
- Rebased the Heart / Recovery planning updates onto the current remote app implementation.
- Preserved the newer app code already merged on `main` and kept this change focused on repository instructions plus product planning docs.

### 2026-05-03
- Added the next recommended product slice after the HRV graph: a Heart / Recovery page that explains HRV using rolling baselines, resting heart rate, and sleep context.
- Updated the spec with a Heart / Recovery page contract covering expected inputs, behavior, and required initial content.
- Updated the implementation plan so Phase 6 starts with the focused Heart / Recovery slice before broader expansion work.
