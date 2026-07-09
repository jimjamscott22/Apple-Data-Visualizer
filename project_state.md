# Project State

## Project
- Name: `Apple Health Data Analyzer`
- Repo root: `/home/jimjamscozz/Desktop/Coding Files/Python/Projects/Apple-Data-Visualizer`
- Stack: Python 3, PySide6, MariaDB (via PyMySQL)
- Current date of handoff: `2026-04-16`

## Current Status
- Phase 1 completed: application shell, entrypoint, package layout, theme, placeholder pages.
- Phase 2 completed: database bootstrap, schema creation, indexes, database manager foundation. Originally SQLite; migrated to a networked MariaDB server (see `docs/mariadb-migration-spec.md` and `docs/mariadb-migration-plan.md`).
- Phase 3 completed: import pipeline, zip/XML resolution, Apple Health XML parsing, normalization, duplicate detection, persistence, and UI import wiring.
- Phase 4 is partially implemented: nightly sleep sessions are now derived and persisted after import, and overview cards now read real sleep, steps, and resting-HR metrics when data exists.

## What Works Now
- App launches from `main.py`.
- Database is created automatically on first run.
- Import button accepts:
  - direct `export.xml`
  - Apple Health zip archives containing `export.xml`
- Imports are fingerprinted using SHA-256 of the resolved `export.xml`.
- Duplicate completed imports are detected and skipped.
- Supported Apple Health record types currently parsed:
  - `HKCategoryTypeIdentifierSleepAnalysis`
  - `HKQuantityTypeIdentifierStepCount`
  - `HKQuantityTypeIdentifierHeartRate`
  - `HKQuantityTypeIdentifierRestingHeartRate`
  - `HKQuantityTypeIdentifierHeartRateVariabilitySDNN`
  - `HKQuantityTypeIdentifierRespiratoryRate`
  - `HKQuantityTypeIdentifierDistanceWalkingRunning`
- Unsupported Apple record types are skipped and summarized as warnings.
- Successful imports write to:
  - `import_history`
  - `records`
  - `daily_summaries` for non-sleep metrics
- Overview page refreshes after import and reflects DB-backed state.

## Important Files
- Entrypoints:
  - `main.py`
  - `app/main.py`
- Config/theme:
  - `app/config.py`
  - `app/theme.py`
- Database:
  - `app/database/manager.py`
- Parser:
  - `app/parser/health_data_parser.py`
- Services:
  - `app/services/import_service.py`
  - `app/services/dashboard_controller.py`
  - `app/services/sleep_analysis_service.py`
- Models:
  - `app/models/imports.py`
  - `app/models/dashboard.py`
- UI:
  - `app/ui/main_window.py`
  - `app/ui/pages/base.py`
- Planning docs:
  - `docs/spec-sheet.md`
  - `docs/implementation-plan.md`

## Database Notes
- The app connects to MariaDB using `DatabaseSettings` from `app/database/config.py` (env vars / `.env`: `APPLE_DV_DB_HOST/PORT/NAME/USER/PASSWORD`). Schema DDL lives in `app/database/schema.py`. There is no local/file-based storage mode.
- `records.start_at`/`end_at` and `sleep_sessions.bedtime_at`/`wake_at` are native `DATETIME` columns; `DatabaseManager` normalizes the parser's offset-bearing ISO 8601 strings on write and returns plain strings (not driver-native `datetime`/`date` objects) on read, so every caller above the database layer still sees the same string-typed values it always did.
- Current logical tables:
  - `records`
  - `sleep_sessions`
  - `daily_summaries`
  - `import_history`
- `daily_summaries` currently refreshes only for newly imported non-sleep records and uses the record `start_at` calendar date.
- `sleep_sessions` is now populated by post-import derivation for impacted nights only.

## Import Pipeline Notes
- Main orchestration lives in `ImportService`.
- Zip imports are extracted to a temp directory and cleaned up after use.
- Parser uses `xml.etree.ElementTree.iterparse`.
- Datetimes are parsed with format:
  - `%Y-%m-%d %H:%M:%S %z`
- Sleep records are normalized as duration-based rows with:
  - `metric_name = sleep_analysis`
  - `value = duration_hours`
  - `unit = hours`
  - sleep stage stored in metadata
- Quantity unit normalization currently includes:
  - heart rate to `bpm` when Apple unit is `count/min`
  - respiratory rate to `breaths/min` when Apple unit is `count/min`
  - HRV to `ms`
  - walking/running distance normalized to `km` for `m`, `mi`, and `ft`

## Known Gaps
- Sleep-page UI is still scaffolded rather than analytics-driven.
- Sleep-session derivation currently uses a rule-based heuristic:
  - night grouping is anchored by `start_at - 12h`
  - bedtime/wake and efficiency are computed from merged intervals
  - consistency score is a first-pass heuristic, not a trend-based score yet
- Sleep-session refresh currently re-reads all stored sleep records, then filters to impacted nights in Python.
- Import UI shows summary dialogs only; there is no detailed import history page yet.
- Parser warnings are stored in `import_history.notes`, but there is no UI to inspect them yet.
- No automated tests added yet.
- No sample fixture import file has been added to the repo.

## Next Recommended Phase
- Phase 5: UI MVP
- Main objective:
  - replace scaffolded Sleep page content with real analytics and charts
- Expected work:
  - query `sleep_sessions` for 7/30/90-day ranges
  - render nightly duration, bedtime, wake-time, and weekly-average visuals
  - add nightly sessions table
  - refine the consistency model using trend data instead of a single-night heuristic
  - add tests around night grouping and interval merging

## Suggested Resume Checklist
1. Read `docs/spec-sheet.md` and `docs/implementation-plan.md`.
2. Review:
   - `app/services/sleep_analysis_service.py`
   - `app/services/import_service.py`
   - `app/database/manager.py`
   - `app/services/dashboard_controller.py`
3. Build read models for the Sleep page from `sleep_sessions`.
4. Add tests for impacted-night replacement and merged-interval calculations.
5. Decide whether to keep the current consistency heuristic or replace it with a trend-based score.

## Verification Performed
- Command run:
```bash
python3 -m compileall app main.py
```
- Result:
  - passed after the Phase 4 sleep-session and overview changes

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
