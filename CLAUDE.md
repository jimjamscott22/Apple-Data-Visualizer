# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A PySide6 desktop app that imports Apple Health `export.xml`/zip data, stores normalized
records in a MariaDB database, and renders sleep/HRV/trends analytics with pyqtgraph. There
is no local/file-based storage mode — MariaDB is a hard runtime dependency.

## Commands

```bash
uv sync                              # install deps / create .venv
cp .env.example .env                 # fill in APPLE_DV_DB_* MariaDB connection vars
uv run apple-data-visualizer         # run the app (entrypoint: app.main:main)
uv run python main.py                # equivalent alternate entrypoint
uv run pytest                        # run tests (see "Tests" below)
uv run pytest tests/test_trends_analysis_service.py::TestName::test_case  # single test
uv run python -m compileall app main.py   # quick syntax/compile check
```

No lint/format/type-check tooling is configured in `pyproject.toml` (no ruff/mypy config
present despite an `.mypy_cache/` existing locally) — don't assume a linter gate exists.

### Database setup

The app needs a reachable MariaDB server (10.5+) and will refuse to launch without one
(`MissingDatabaseSettingsError` / `DatabaseConnectionError` shown as a dialog, exit code 1).
`.env` (gitignored) or real env vars supply `APPLE_DV_DB_HOST/PORT/NAME/USER/PASSWORD` —
see `README.md`'s "Database Setup (MariaDB)" section for the `CREATE DATABASE`/`CREATE USER`
SQL. On first launch the app bootstraps its own schema via `MARIADB_SCHEMA_STATEMENTS`.

### Tests

Most of `tests/test_database_manager.py` and `tests/test_database_schema.py` are live-DB
round-trip tests: they connect to a real MariaDB/MySQL server (`APPLE_DV_TEST_DB_HOST/PORT/
USER/PASSWORD`, default `127.0.0.1:3306`/`root`/empty password), create a throwaway database,
and self-skip via `pytest.skip(...)` when no server is reachable — so `uv run pytest` without
a local server still passes, just with those cases skipped. Don't treat skips there as failures.

## Architecture

### Data flow (import path)

`MainWindow` (UI) → `ImportWorker` (QThread wrapper, `app/ui/import_worker.py`) →
`ImportService.import_file()` (`app/services/import_service.py`) which:

1. Resolves the selected `.xml`/`.zip` to a real `export.xml` path (extracts zips to a temp
   dir, cleaned up after).
2. SHA-256-fingerprints the file and checks `import_history` for a prior completed import
   with the same fingerprint — duplicates are logged and skipped, not re-imported.
3. Streams the XML via `HealthDataParser.parse_stream()` (`xml.etree.ElementTree.iterparse`,
   one pass, `element.clear()` per node) and batches records (`IMPORT_BATCH_SIZE = 5000`)
   into `DatabaseManager.append_import_records()` inside one long-lived connection
   (`begin_import` → repeated `append_import_records` → `complete_import`), so a mid-import
   failure rolls back the whole import instead of partially committing.
4. After commit, re-derives affected nights' `sleep_sessions` via `SleepAnalysisService`
   and `DatabaseManager.replace_sleep_sessions()` (delete + reinsert for just the impacted
   `night_date`s, not a full recompute).

Progress callbacks (`on_progress(percent, phase)`) flow from the byte-level XML reader
through the parser and `ImportService` up to the Qt progress bar — preserve that chain if
touching the parser/import path.

Only these Apple record types are recognized (`APPLE_RECORD_TYPE_MAP` in
`app/parser/health_data_parser.py`); anything else is counted and summarized as a warning,
not an error: `SleepAnalysis`, `StepCount`, `HeartRate`, `RestingHeartRate`,
`HeartRateVariabilitySDNN`, `RespiratoryRate`, `DistanceWalkingRunning`.

### Sleep-night derivation

`SleepAnalysisService` groups raw `sleep_analysis` records into nightly sessions. A "night"
is anchored by `start_at - 12h` (`NIGHT_START_HOUR = 12`) so a record starting at 1am belongs
to the previous night. Overlapping intervals of the same sleep stage are interval-merged
before summing duration (`_merged_duration_hours`), and `consistency_score` is a first-pass
weighted-penalty heuristic (bedtime/wake/duration/efficiency deviation from targets), not a
trend-based score — see `project_state.md`'s "Known Gaps" if extending this.

### Database layer

- `app/database/config.py` — `DatabaseSettings` from env vars (`.env` via `python-dotenv`),
  raises `MissingDatabaseSettingsError` if required vars are absent.
- `app/database/schema.py` — `MARIADB_SCHEMA_STATEMENTS`, an ordered tuple of idempotent
  (`IF NOT EXISTS`) DDL statements (PyMySQL executes one statement per call, unlike SQLite's
  `executescript`). Order matters: `import_history` must exist before tables that FK to it.
- `app/database/manager.py` — `DatabaseManager` wraps PyMySQL with `DictCursor`,
  `autocommit=False`, and a custom `conv` override that passes `DATETIME`/`DATE`/`TIMESTAMP`
  columns through as raw strings instead of PyMySQL's default `datetime`/`date` objects —
  every caller above this layer (models, services, UI) expects string-typed temporal values,
  matching the original SQLite `TEXT`-column contract. **If you add a new DATETIME/DATE
  column or a new read path, keep this contract**: don't let a native Python `datetime`/`date`
  leak upward.
- Timestamps written to `DATETIME` columns go through `_to_mariadb_datetime()`, which strips
  the parser's UTC offset (MariaDB `DATETIME` has no tz storage and rejects the `T`/offset
  ISO format outright) and reformats to naive `YYYY-MM-DD HH:MM:SS`.
- Four tables: `import_history`, `records`, `sleep_sessions`, `daily_summaries`.
  `daily_summaries` is upserted (`ON DUPLICATE KEY UPDATE`, unique on
  `(metric_name, summary_date)`) only for the metrics/dates touched by the current import
  batch (`_refresh_daily_summaries`), not recomputed globally.

### Services / UI layering

- `DashboardController` (`app/services/dashboard_controller.py`) is the read-side façade the
  UI calls — it queries `DatabaseManager`, hands raw rows to `SleepAnalysisService` /
  `HRVAnalysisService` / `ActivityAnalysisService` / `TrendsAnalysisService` /
  `ImportHistoryService` for statistics, and returns typed dataclasses from `app/models/`
  (`OverviewData`, `SleepSummaryData`, `HRVSummaryData`, `ActivitySummaryData`,
  `TrendsSummaryData`, `ImportsSummaryData`) via its `load_*()` methods. UI pages
  (`app/ui/pages/`) render these dataclasses and never touch `DatabaseManager` directly.
- `app/charts/__init__.py` holds shared pyqtgraph styling/axis helpers, notably
  `ClockAxisItem` (renders "hours since prior noon" float values as HH:MM clock times for
  overnight spans) and `IndexDateAxisItem` (labels integer x-positions with real calendar
  dates) — reuse these instead of writing new axis formatting when adding a chart.
- Long-running work (currently just import) runs on a `QThread` per
  `app/ui/import_worker.py`'s pattern: the `(QThread, QObject-worker)` pair must stay
  referenced by the caller (e.g. as `self._import_thread`/`self._import_worker`) until
  `finished` fires, or Qt garbage-collects it mid-run and silently aborts the task.

### Known incomplete areas

All seven nav sections are implemented — Overview, Sleep, Activity, HRV/Heart, Trends,
Imports, Settings. None are placeholders. `ImportsPage` is the read-only import-history
dashboard (database status, aggregate cards, metric inventory, latest-50 attempts, and a
detail panel for parser warnings/duplicates/failures); preserve its read-only boundary —
no delete/retry/export/credential controls without an approved follow-on design.

Verified remaining gaps, roughly in priority order:

- **Phase 6 Heart/Recovery slice is partial** (`docs/implementation-plan.md:162-179`).
  `hrv_page.py` has latest/7-day/30-day HRV, trend, and CV. Still missing: the recovery
  summary card (`Recovered`/`Normal`/`Strained`/`Low data`), baseline-delta and min/max
  HRV cards, resting-heart-rate trend and baseline comparison, and sleep context beside
  the heart metrics. `HRVAnalysisService` already computes per-day `min_ms`/`max_ms`
  (with a null-collapse fallback) — that data is plumbed but unrendered.
- **No tests for the most logic-dense modules**: `HealthDataParser`,
  `SleepAnalysisService`, `HRVAnalysisService`, `ImportService`. All are Qt-free; only
  `ImportService` touches `DatabaseManager` and that is fakeable — see
  `tests/test_dashboard_controller.py` for the established fake pattern. No sample
  `export.xml` fixture exists in the repo (`*.zip` / `apple_health_export/` are
  gitignored), so parser tests need a hand-authored minimal fixture.
- **Phase 7 docs partial**: `README.md` covers setup/run/import, but has no architecture
  summary, no notes on adding new Apple Health record types, no future-enhancements
  section, and PyInstaller-friendliness is unverified.
- **Consistency score is a fixed-target heuristic**, not a personal baseline —
  `SleepAnalysisService._calculate_consistency_score` penalizes deviation from hardcoded
  targets (22:30 bedtime, 07:00 wake, 8h, 85% efficiency), so a consistent late schedule
  scores badly. Deferred by design in the plan, not overdue.
- **Dark is the only theme**, deliberately; Settings reports that rather than showing
  dead controls. Not a gap to close.

Treat `project_state.md` as a running implementation log (update it after making changes,
per its own instruction at the top) rather than a fully current architecture doc — verify
claims against the actual code first.
