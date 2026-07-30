# Project State

## Project
- Name: `Apple Health Data Analyzer`
- Repo root: `/home/jimjamscozz/Desktop/GitHub-Repos/Apple-Data-Visualizer`
- Stack: Python 3, PySide6, pyqtgraph, MariaDB (via PyMySQL)
- Current date of handoff: `2026-07-29`

## Current Status
- Phase 1 completed: application shell, entrypoint, package layout, theme, sidebar navigation.
- Phase 2 completed: database bootstrap and schema creation. Originally SQLite; migrated to a
  networked MariaDB server (Phases 1-4 and 6 of `docs/mariadb-migration-plan.md` are done;
  Phase 5, an optional SQLite carry-over script, was explicitly skipped as not needed). There
  is no local/file-based storage mode anymore — a reachable MariaDB 10.5+ server is a hard
  requirement to launch the app at all.
- Phase 3 completed: import pipeline, zip/XML resolution, Apple Health XML parsing,
  normalization, duplicate detection, persistence, and UI import wiring — now running on a
  background `QThread` (`app/ui/import_worker.py`) with a live progress bar and status label
  in the main window instead of blocking the UI thread.
- Phase 4 completed: nightly sleep sessions are derived and persisted after each import
  (impacted nights only), and overview cards read real sleep, steps, resting-HR, and HRV
  metrics when data exists.
- Phase 5 completed: Sleep page is fully analytics-driven (`app/ui/pages/sleep_page.py`) —
  7/30/90-day range filter, nightly duration bar chart with average line, bedtime/wake-time
  trend chart on a clock axis, and a full nightly sessions table. No longer a scaffold.
- Phase 6 (Expansion Pass) partially completed:
  - Heart / Recovery slice done as an HRV page (`app/ui/pages/hrv_page.py` +
    `HRVAnalysisService`): latest/7-day/30-day HRV averages, trend direction and slope
    (ms/week via linear regression), coefficient of variation, daily HRV chart with rolling
    average, and a daily history table.
  - Trends slice done (`app/ui/pages/trends_page.py` + `TrendsAnalysisService`): Pearson
    correlation + regression line for sleep-vs-next-day-HRV, sleep-vs-next-day-resting-HR,
    and steps-vs-same-night-sleep, plus weekday/weekend and higher-sleep/lower-sleep split
    comparisons, with a 30/90/365-day range filter.
  - Settings slice done (`app/ui/pages/settings_page.py` + `app/preferences.py`): persistent
    Sleep/Trends defaults, 12/24-hour time display, remembered import folder and last-page
    behavior, read-only connection/application details, and reset-to-default controls.
  - Activity and Imports/Data Manager remain intentional placeholder scaffolds in
    `MainWindow` (`app/ui/pages/base.py::PlaceholderPage`) — not started.
- A real bug fix landed 2026-07-18 (`9346b58`): `_refresh_daily_summaries` was filtering with
  `DATE(start_at) = %s`, which can't use the `idx_records_metric_start` index (the function
  call on the column defeats it), causing a full scan of `records` per impacted metric/day on
  every import batch — this made large imports increasingly slow as the table grew. Fixed by
  filtering with an equivalent indexed range (`start_at >= range_start AND start_at <
  range_end`). The same commit added the XML byte-read progress tracker
  (`_ProgressTrackingReader`) that now drives the import progress bar.

## What Works Now
- App launches from `main.py` or `uv run apple-data-visualizer`, both via `app.main:main`.
- Database schema is created automatically on first run against the configured MariaDB server;
  missing config or a failed connection shows a dialog and exits cleanly (exit code 1) instead
  of crashing.
- Import button accepts direct `export.xml` or Apple Health zip archives, runs on a background
  thread with a visible progress bar/status label, and re-enables itself on completion.
- Imports are fingerprinted using SHA-256 of the resolved `export.xml`; duplicate completed
  imports are detected and skipped (logged as `duplicate` in `import_history`, no re-insert).
- Supported Apple Health record types currently parsed (`APPLE_RECORD_TYPE_MAP`):
  - `HKCategoryTypeIdentifierSleepAnalysis`
  - `HKQuantityTypeIdentifierStepCount`
  - `HKQuantityTypeIdentifierHeartRate`
  - `HKQuantityTypeIdentifierRestingHeartRate`
  - `HKQuantityTypeIdentifierHeartRateVariabilitySDNN`
  - `HKQuantityTypeIdentifierRespiratoryRate`
  - `HKQuantityTypeIdentifierDistanceWalkingRunning`
- Unsupported Apple record types and malformed supported records are skipped and summarized
  as warnings (capped detail list, aggregated counts), not treated as import failures.
- Successful imports write to `import_history`, `records`, `daily_summaries` (non-sleep
  metrics only), and `sleep_sessions` (impacted nights only, delete + reinsert).
- Overview, Sleep, HRV (Heart), and Trends pages all refresh with real DB-backed data after
  import completes, without restarting the app.

## Important Files
- Entrypoints:
  - `main.py`
  - `app/main.py`
- Config/theme:
  - `app/config.py` (`APP_NAME` / installed package version)
  - `app/preferences.py` — `QSettings`-backed local UI preferences and session state
  - `app/theme.py`
- Database:
  - `app/database/config.py` — `DatabaseSettings` from env vars / `.env`
  - `app/database/schema.py` — `MARIADB_SCHEMA_STATEMENTS`
  - `app/database/manager.py` — `DatabaseManager`
  - `app/database/errors.py` — `DatabaseConnectionError`
- Parser:
  - `app/parser/health_data_parser.py`
- Services:
  - `app/services/import_service.py`
  - `app/services/dashboard_controller.py`
  - `app/services/sleep_analysis_service.py`
  - `app/services/hrv_analysis_service.py`
  - `app/services/trends_analysis_service.py`
- Models:
  - `app/models/imports.py`, `app/models/dashboard.py`, `app/models/sleep.py`,
    `app/models/hrv.py`, `app/models/trends.py`
- UI:
  - `app/ui/main_window.py`
  - `app/ui/import_worker.py` — background `QThread` import wrapper
  - `app/ui/pages/base.py` — `MetricCard`, `EmptyStateCard`, `PlaceholderPage`, `OverviewPage`
  - `app/ui/pages/sleep_page.py`, `app/ui/pages/hrv_page.py`, `app/ui/pages/trends_page.py`
  - `app/ui/pages/settings_page.py`
  - `app/charts/__init__.py` — shared pyqtgraph styling and axis helpers
    (`ClockAxisItem`, `IndexDateAxisItem`)
- Planning docs:
  - `docs/spec-sheet.md`, `docs/implementation-plan.md`
  - `docs/mariadb-migration-spec.md`, `docs/mariadb-migration-plan.md`

## Database Notes
- The app connects to MariaDB using `DatabaseSettings` from `app/database/config.py` (env vars
  / `.env`: `APPLE_DV_DB_HOST/PORT/NAME/USER/PASSWORD`). Schema DDL lives in
  `app/database/schema.py`. There is no local/file-based storage mode.
- `records.start_at`/`end_at` and `sleep_sessions.bedtime_at`/`wake_at` are native `DATETIME`
  columns; `DatabaseManager` normalizes the parser's offset-bearing ISO 8601 strings on write
  (`_to_mariadb_datetime`) and returns plain strings (not driver-native `datetime`/`date`
  objects) on read via a custom PyMySQL `conv` override, so every caller above the database
  layer still sees the same string-typed values it always did.
- Current logical tables: `records`, `sleep_sessions`, `daily_summaries`, `import_history`.
- `daily_summaries` refreshes only for newly imported non-sleep records, keyed on
  `(metric_name, summary_date)` via `ON DUPLICATE KEY UPDATE`, filtered by an indexed
  `start_at` range (see the 2026-07-18 bug fix above — do not reintroduce a `DATE(start_at) =`
  filter here).
- `sleep_sessions` is populated by post-import derivation for impacted nights only
  (delete-then-reinsert per `night_date`, not a full table recompute).

## Import Pipeline Notes
- Main orchestration lives in `ImportService.import_file()`, called from a background
  `QThread` via `app/ui/import_worker.py::run_import_in_background`.
- Zip imports are extracted to a temp directory and cleaned up after use.
- Parser uses `xml.etree.ElementTree.iterparse` over a `_ProgressTrackingReader`-wrapped file
  object, driving `on_progress(percent)` from raw bytes read so the UI progress bar reflects
  actual parse position, not batch count.
- Records are batched at `ImportService.IMPORT_BATCH_SIZE = 5000` and flushed into one
  long-lived connection (`begin_import` → repeated `append_import_records` → `complete_import`)
  so a mid-import failure rolls back the entire import, including the `begin_import` row.
- Datetimes are parsed with format: `%Y-%m-%d %H:%M:%S %z`.
- Sleep records are normalized as duration-based rows with `metric_name = sleep_analysis`,
  `value = duration_hours`, `unit = hours`, sleep stage stored in metadata.
- Quantity unit normalization currently includes:
  - heart rate to `bpm` when Apple unit is `count/min`
  - respiratory rate to `breaths/min` when Apple unit is `count/min`
  - HRV to `ms`
  - walking/running distance normalized to `km` for `m`, `mi`, and `ft`

## Known Gaps
- Activity and Imports/Data Manager are still placeholder scaffolds (`PlaceholderPage` in the
  nav) — there is no steps/movement analytics or import-history UI yet, per Phase 6 of
  `docs/implementation-plan.md`.
- Dark is still the only implemented theme. The Settings page reports that fact instead of
  offering non-functional theme controls.
- Sleep-session derivation is still a rule-based heuristic (see
  `SleepAnalysisService._calculate_consistency_score`): night grouping anchored at
  `start_at - 12h`, bedtime/wake/efficiency from merged intervals, consistency scored via
  fixed penalty weights against fixed targets (22:30 bedtime, 07:00 wake, 8h duration, 85%
  efficiency) rather than a personal trend-based baseline.
- Parser warnings are stored in `import_history.notes` (JSON), but there is still no UI to
  inspect import history or those warnings — only the post-import summary dialog.
- Automated test coverage is real but partial: `tests/test_database_config.py` is a pure unit
  test; `tests/test_database_manager.py` and `tests/test_database_schema.py` are live-MariaDB
  round-trip tests that self-skip when no server is reachable
  (`APPLE_DV_TEST_DB_HOST/PORT/USER/PASSWORD`, default `127.0.0.1:3306`/`root`); and
  `tests/test_trends_analysis_service.py` unit-tests `TrendsAnalysisService`. There are no
  tests yet for `HealthDataParser`, `SleepAnalysisService`, `HRVAnalysisService`,
  `ImportService`, or `DashboardController`.
- No sample fixture import file has been added to the repo (`*.zip` and
  `apple_health_export/` are gitignored; `data_tmp/` in the working tree is local-only and
  untracked).

## Next Recommended Phase
- Continue Phase 6 (Expansion Pass) per `docs/implementation-plan.md`:
  - Imports / Data Manager page: import history table, record counts by type, database status
    panel, and a way to surface stored parser warnings — this is the most-referenced gap above.
  - Activity page: daily steps chart, weekly averages, most-active-day summaries (data is
    already imported and summarized in `daily_summaries` for `step_count`; no new ingestion
    needed, just a page).
- Alongside UI work, close the test-coverage gap for `HealthDataParser`, `SleepAnalysisService`,
  `HRVAnalysisService`, and `ImportService` — these are pure-logic services with no Qt/DB
  dependency (aside from `ImportService`'s `DatabaseManager` calls, which can be faked) and are
  currently the least-tested layer relative to their complexity.

## Suggested Resume Checklist
1. Read `docs/spec-sheet.md` and `docs/implementation-plan.md` (Phase 6 section) for the
   Imports/Activity/Settings page contracts.
2. Review:
   - `app/services/import_service.py` and `app/database/manager.py` for what's already
     available to surface on an Imports page (`list_recent_imports`, `import_history.notes`).
   - `app/ui/pages/hrv_page.py` or `trends_page.py` as the current template for a fully
     implemented (non-placeholder) page.
3. Build a read model + `DashboardController` method for import history, following the existing
   `load_sleep_summary`/`load_hrv_summary` pattern.
4. Add unit tests for `HealthDataParser`, `SleepAnalysisService`, and `HRVAnalysisService`
   before extending them further.

## Verification Performed
- This update is a documentation-only refresh of `project_state.md` based on a source-code
  review (no code changes, so no build/test run was needed for it).
- Last known real verification, from the MariaDB migration (per `AGENTS.md`): `uv run python -m
  compileall app main.py` and `uv run pytest -q` both passed (27 passed / 13 skipped without a
  live MariaDB server). Re-run these before trusting that state still holds after further changes.

## Run Instructions
```bash
cp .env.example .env   # fill in your MariaDB connection details
uv sync
uv run apple-data-visualizer
```
See the "Database Setup (MariaDB)" section of `README.md` for the `CREATE DATABASE`/`CREATE USER`/`GRANT` SQL to run against the MariaDB server first.

## Notes For Another Device
- The handoff assumes the repo contents are synced, including this file.
- A running MariaDB server (10.5+) reachable from the new device is required — there is no local/file-based fallback. Set up `.env` per `README.md` before launching.
- The app connects to the same MariaDB database regardless of which device it's launched from, so data is already shared/synced across devices by virtue of the storage backend — there is no per-device local DB to get out of sync.
