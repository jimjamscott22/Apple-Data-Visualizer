# SQLite → MariaDB Migration Implementation Plan

## Summary
This plan sequences the work described in `docs/mariadb-migration-spec.md`
into phases that keep the app runnable throughout. It assumes the MariaDB
server itself is already running on the user's LAN and that the database,
application user, and privileges are created up front using the SQL
published in `README.md`. Everything after that is application-side: new
connection configuration, a ported schema, a ported `DatabaseManager`, and
updated error handling for a networked database.

## Phase 0: Server-Side Provisioning
**Purpose**
Create the MariaDB database, application user, and privileges the app will
connect with. This phase has no application code changes.

**Deliverables**
- `README.md` documents the `CREATE DATABASE`, `CREATE USER`, and `GRANT`
  statements to run once against the LAN MariaDB server.

**Dependencies**
- None. The user runs this manually against their existing server.

**Definition of Done**
- The database and user exist on the MariaDB server and the user can
  authenticate with a MariaDB client using the created credentials.

## Phase 1: Connection Configuration
**Purpose**
Introduce a configuration contract for MariaDB connection settings without
touching the schema or `DatabaseManager` yet.

**Deliverables**
- Add `pymysql` (and `python-dotenv` if `.env` support is desired) to
  `pyproject.toml` dependencies.
- Add a `DatabaseSettings` dataclass (host, port, database, user, password)
  sourced from environment variables as defined in the spec's config table.
- Add `.env.example` documenting the required variables (no real secrets).
- Add `.env` to `.gitignore` if `.env` loading is implemented.
- Leave `app/config.py`'s SQLite path/`DatabaseManager` construction in
  place but unused by the new settings path, so the app still runs on the
  old backend until Phase 3 lands.

**Dependencies**
- Phase 0 (so settings can be validated against a real server).

**Definition of Done**
- `DatabaseSettings` can be constructed from environment variables and
  raises a clear error when required variables are missing.
- No credentials appear in source or version control.

## Phase 2: Schema Port
**Purpose**
Translate the existing SQLite DDL into MariaDB DDL per the spec's
translation table.

**Deliverables**
- Write MariaDB `CREATE TABLE` statements for `import_history`, `records`,
  `sleep_sessions`, and `daily_summaries` using `AUTO_INCREMENT`,
  `DATETIME`/`DATE` temporal columns, `JSON` metadata columns, `InnoDB`
  engine, and `utf8mb4` charset/collation.
- Recreate all existing indexes and the `UNIQUE(metric_name, summary_date)`
  constraint.
- Split the single SQLite `executescript()` bootstrap into individual
  statements (or an ordered list) since MariaDB drivers execute one
  statement per call.

**Dependencies**
- Phase 1 settings, so the DDL can be run against the real database during
  development.

**Definition of Done**
- Running the bootstrap against a clean MariaDB database creates all four
  tables, all indexes, and the unique constraint, and is safe to re-run
  (`IF NOT EXISTS` semantics preserved).

## Phase 3: `DatabaseManager` Port
**Purpose**
Swap `DatabaseManager`'s internals from `sqlite3` to PyMySQL while keeping
its public method signatures and return shapes unchanged, so every caller
(services, controllers) keeps working without modification.

**Deliverables**
- Replace `sqlite3.connect()` with a PyMySQL connection (or pooled
  connection) built from `DatabaseSettings`.
- Replace `sqlite3.Row` row access with `pymysql.cursors.DictCursor`.
- Replace all `?` placeholders with `%s` across every query in
  `manager.py`.
- Replace `datetime('now', '-' || ? || ' days')` /
  `date('now', '-' || ? || ' days')` with `DATE_SUB(NOW(), INTERVAL %s DAY)`
  / `DATE_SUB(CURDATE(), INTERVAL %s DAY)`.
- Replace `substr(start_at, 1, 10)` with `DATE(start_at)`.
- Replace the `daily_summaries` `ON CONFLICT ... DO UPDATE` upsert with
  `INSERT ... ON DUPLICATE KEY UPDATE`.
- Update type hints referencing `sqlite3.Row`/`sqlite3.Connection` in
  `manager.py`, `app/services/trends_analysis_service.py`, and
  `app/services/hrv_analysis_service.py`.
- Wrap connection-time failures (auth failure, unreachable host) in a
  clear, app-specific exception type the UI layer can catch.

**Dependencies**
- Phase 2 schema.

**Definition of Done**
- Every existing `DatabaseManager` public method (`initialize`,
  `persist_import`, `begin_import`/`append_import_records`/
  `complete_import`, `find_completed_import_by_fingerprint`,
  `replace_sleep_sessions`, `get_overview_snapshot`,
  `get_average_sleep_this_week`, `get_last_sleep_session`,
  `get_recent_sleep_sessions`, `get_average_daily_steps`,
  `get_latest_resting_heart_rate`, `get_hrv_records`,
  `get_daily_metric_summaries`, `get_hrv_daily_summaries`,
  `list_recent_imports`) returns equivalent data against MariaDB as it did
  against SQLite.
- No remaining `import sqlite3` on the primary storage path.

## Phase 4: App Wiring and Error Handling
**Purpose**
Point the running app at the new MariaDB-backed `DatabaseManager` and
surface connection problems as friendly UI states instead of crashes.

**Deliverables**
- Update `app/main.py` bootstrap to build `DatabaseManager` from
  `DatabaseSettings` instead of the local SQLite path.
- Remove or clearly deprecate the now-unused SQLite path plumbing in
  `app/config.py` (`DATABASE_FILENAME`, `database_path`) once MariaDB is
  the only backend.
- Add a startup connection-check with a friendly failure dialog/state for
  unreachable host or authentication failure, distinct from existing
  "no data yet" empty states.
- (Optional, from the spec's connection-lifecycle note) wire in connection
  pooling if it wasn't already covered in Phase 3.

**Dependencies**
- Phase 3.

**Definition of Done**
- Launching the app with valid settings connects to MariaDB and behaves
  identically to the current SQLite-backed app for import and dashboard
  flows.
- Launching the app with an unreachable server or bad credentials shows a
  clear error state rather than hanging or crashing.

## Phase 5: Existing Data Carry-Over (Optional)
**Purpose**
Only needed if the user has an existing local SQLite database with real
imported data they want preserved instead of re-importing their Apple
Health export from scratch.

**Deliverables**
- A one-off script that reads all rows from the local SQLite database and
  writes them into the new MariaDB schema, preserving `import_history`,
  `records`, `sleep_sessions`, and `daily_summaries` relationships
  (including `import_id` foreign keys).
- Script is a standalone, run-once tool, not part of the app's runtime
  path.

**Dependencies**
- Phase 3 schema/manager in place on the MariaDB side.

**Definition of Done**
- Running the script against a populated SQLite database and an empty
  MariaDB database results in matching row counts per table and a working
  dashboard reflecting the migrated data.

## Phase 6: Documentation
**Purpose**
Leave the repo's docs consistent with the new storage backend.

**Deliverables**
- Update `README.md`'s "Run" section with the required MariaDB environment
  variables.
- Update `README.md`'s top-level description and Import section wording
  from "local SQLite database" to reflect the MariaDB backend.
- Update `docs/spec-sheet.md`'s "Supported Platforms and Stack" storage
  line and "Database Schema Expectations" section to reference MariaDB
  instead of SQLite once the migration is implemented.
- Update `project_state.md` database notes.

**Dependencies**
- Phases 1 through 4 (and 5 if performed).

**Definition of Done**
- A new contributor can read the README and get a working MariaDB-backed
  app running end to end, with no SQLite references left describing
  current behavior.

## Acceptance Test Scenarios
- Server-side SQL from `README.md` successfully creates the database, user,
  and grants on a real MariaDB server.
- App fails to start with a clear error when required DB environment
  variables are missing.
- App connects and bootstraps schema on first run against an empty MariaDB
  database.
- Import accepts a valid `export.xml` and a valid Apple Health zip, exactly
  as it does today.
- Duplicate-import detection still works, keyed off `file_fingerprint`.
- Overview and Sleep page reads return correct data against MariaDB,
  including the relative-date queries (`get_average_daily_steps`,
  `get_hrv_records`, `get_daily_metric_summaries`, `get_hrv_daily_summaries`).
- Killing the MariaDB server (or blocking the port) produces a friendly
  connection-error state instead of a crash.

## Defaults and Assumptions
- MariaDB server is already installed, running, and reachable on the LAN;
  provisioning the server itself is out of scope.
- Minimum supported MariaDB version is 10.5 (for `JSON` columns and
  `CREATE INDEX IF NOT EXISTS`).
- PyMySQL is the driver, chosen to avoid bundling a native client library
  in a PyInstaller build.
- No ORM is introduced; `DatabaseManager` remains the sole SQL boundary.
- SQLite is fully replaced, not kept as a fallback/offline mode, unless the
  user asks for dual-backend support later.
- Phase 5 (existing data carry-over) only runs if the user has local data
  worth preserving; fresh installs can skip straight to Phase 6.
