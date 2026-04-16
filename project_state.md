# Project State

## Project
- Name: `Apple Health Data Analyzer`
- Repo root: `/home/jimjamscozz/Desktop/Coding Files/Python/Projects/Apple-Data-Visualizer`
- Stack: Python 3, PySide6, SQLite
- Current date of handoff: `2026-04-16`

## Current Status
- Phase 1 completed: application shell, entrypoint, package layout, theme, placeholder pages.
- Phase 2 completed: SQLite bootstrap, schema creation, indexes, database manager foundation.
- Phase 3 completed: import pipeline, zip/XML resolution, Apple Health XML parsing, normalization, duplicate detection, persistence, and UI import wiring.
- Phase 4 has not started yet.

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
- SQLite file location is derived from `app/config.py`.
- Current logical tables:
  - `records`
  - `sleep_sessions`
  - `daily_summaries`
  - `import_history`
- `sleep_sessions` exists in schema but is not populated yet.
- `daily_summaries` currently refreshes only for newly imported non-sleep records and uses the record `start_at` calendar date.

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
- No Phase 4 sleep session derivation yet.
- `sleep_sessions` remains empty until `SleepAnalysisService` is implemented.
- Overview still uses placeholder values for:
  - average sleep this week
  - last night sleep
  - average daily steps
  - latest resting heart rate
- Sleep page is still scaffolded rather than analytics-driven.
- Import UI shows summary dialogs only; there is no detailed import history page yet.
- Parser warnings are stored in `import_history.notes`, but there is no UI to inspect them yet.
- No automated tests added yet.
- No sample fixture import file has been added to the repo.

## Next Recommended Phase
- Phase 4: Sleep Analytics MVP
- Main objective:
  - turn normalized sleep records into nightly sessions and persisted summaries
- Expected work:
  - implement `SleepAnalysisService`
  - define night grouping logic for sessions crossing midnight
  - derive:
    - total sleep duration
    - time in bed
    - sleep efficiency
    - bedtime
    - wake time
  - persist nightly summaries into `sleep_sessions`
  - update dashboard reads to consume real sleep data

## Suggested Resume Checklist
1. Read `docs/spec-sheet.md` and `docs/implementation-plan.md`.
2. Review:
   - `app/services/import_service.py`
   - `app/parser/health_data_parser.py`
   - `app/database/manager.py`
3. Start Phase 4 in `app/services/sleep_analysis_service.py`.
4. Add DB methods for inserting and querying `sleep_sessions`.
5. Wire post-import sleep summary generation into the import flow.
6. Refresh overview and sleep-page reads from derived data.

## Verification Performed
- Command run:
```bash
python3 -m compileall app main.py
```
- Result:
  - passed after Phase 3 changes

## Run Instructions
```bash
python3 -m pip install -r requirements.txt
python3 main.py
```

## Notes For Another Device
- The handoff assumes the repo contents are synced, including this file.
- If the new device has no existing local app data yet, the SQLite DB will be created on first run.
- If the new device already has an old local DB in the configured app data directory, be aware that code and local data may be out of sync.
