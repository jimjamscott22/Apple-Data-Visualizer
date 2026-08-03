# Apple Health Data Analyzer Implementation Plan

## Summary

This implementation plan converts the spec sheet into a phased execution roadmap for the repository. It assumes an MVP-first delivery where the strongest early experience is a polished import workflow, reliable normalized storage, a strong overview dashboard, and an especially good sleep analytics module.

The plan is designed to minimize rework: build the application shell and data model once, then layer parsing, analytics, and UI features on top in a sequence that keeps the app runnable throughout development.

## Phase 1: Foundation

**Purpose**
Establish the application skeleton, runtime entrypoint, visual shell, and shared constants so future work lands in stable structure rather than ad hoc files.

**Deliverables**
- Create the initial package layout under `app/`
- Add `main.py` entrypoint and bootstrap flow
- Add dependency manifest and base configuration/constants modules
- Build the main window shell with:
  - sidebar navigation
  - top header/title area
  - central content stack
- Define theme tokens for the dark-mode-first UI
- Add placeholder page classes for Overview, Sleep, Activity, Heart, Trends, Imports, and Settings

**Dependencies**
- None

**Definition of Done**
- App launches locally from `main.py`
- The main window renders consistently with navigation and placeholder content
- Theme and layout choices are centralized enough to reuse

**May Remain Mocked or Scaffolded**
- Chart widgets can be placeholder cards
- Most page content can be static while the shell is wired

## Phase 2: Data Layer

**Purpose**
Create the persistent storage foundation and establish the boundary between business logic and SQL.

**Deliverables**
- Implement `DatabaseManager`
- Add first-run database initialization
- Define schema for:
  - `records`
  - `sleep_sessions`
  - `daily_summaries`
  - `import_history`
- Add indexes needed for metric/date lookups
- Add repository or query helpers for common reads and writes
- Define import fingerprint storage for duplicate detection

**Dependencies**
- Phase 1 application structure

**Definition of Done**
- Fresh launch creates the database schema automatically on the configured MariaDB server (originally SQLite; migrated per `docs/mariadb-migration-plan.md`)
- Schema can be initialized repeatably without corruption
- The app can read and write import and dashboard data through the database layer only

**May Remain Mocked or Scaffolded**
- Some dashboard queries can return empty/demo results until parsing lands
- Migration support can begin as simple versioned bootstrap logic

## Phase 3: Import and Parsing

**Purpose**
Implement the end-to-end import pipeline that turns an Apple Health export into normalized stored records.

**Deliverables**
- Implement file selection flow in the UI
- Add zip extraction helper that resolves `export.xml`
- Validate supported input shapes and surface friendly errors
- Implement `HealthDataParser`
- Add mapping of Apple Health record identifiers to internal metric names
- Normalize datetime parsing and units handling
- Persist import metadata, normalized records, and parser warnings through `ImportService`
- Log unsupported record types without failing the whole import

**Dependencies**
- Phase 1 shell
- Phase 2 database layer

**Definition of Done**
- Import accepts valid `export.xml`
- Import accepts valid Apple Health zip and auto-locates `export.xml`
- Invalid files show user-friendly failure states
- Duplicate imports are detected and not reinserted

**May Remain Mocked or Scaffolded**
- Only MVP record types need complete normalization
- Unsupported types can be logged and skipped

## Phase 4: Sleep Analytics MVP

**Purpose**
Deliver the app’s signature capability by turning sleep-related records into nightly, human-readable analysis.

**Deliverables**
- Implement `SleepAnalysisService`
- Define night-grouping rules for sessions that cross midnight
- Derive nightly fields:
  - total sleep duration
  - time in bed
  - sleep efficiency
  - bedtime
  - wake time
- Compute trend and rollup datasets:
  - weekly averages
  - monthly averages
  - bedtime and wake-time trends
  - sleep consistency indicators
- Persist derived sleep summaries into `sleep_sessions`

**Dependencies**
- Phase 2 storage
- Phase 3 normalized sleep records

**Definition of Done**
- Sleep records crossing midnight are grouped into the correct night
- Derived nightly metrics are queryable for charts and tables
- Missing optional sleep fields do not break nightly analysis

**May Remain Mocked or Scaffolded**
- Advanced sleep-stage visuals can be deferred
- Consistency scoring can begin as a clear rule-based heuristic

## Phase 5: UI MVP

**Purpose**
Replace placeholders with usable, polished dashboard experiences backed by real or fallback data.

**Deliverables**
- Implement Overview page summary cards and recent trend widgets
- Implement Sleep page charts, filters, and nightly sessions table
- Add empty states for:
  - no imports yet
  - imports exist but a metric has no usable data
- Wire UI pages to `DashboardController`
- Integrate chart components with the app theme
- Add import status feedback and last-import summary display

**Dependencies**
- Phases 1 through 4

**Definition of Done**
- Overview renders with imported data
- Overview still looks polished with no data
- Sleep page supports 7, 30, and 90 day filters plus custom range behavior
- Dashboard pages refresh after import without restarting the app

**May Remain Mocked or Scaffolded**
- Some smaller overview sparkline widgets can use fallback data during UI tuning
- Table-level search can wait until a later pass

## Phase 6: Expansion Pass

**Purpose**
Broaden the app beyond the MVP centerpieces without destabilizing the core experience.

### First Expansion Slice: Heart / Recovery

Because the HRV graph is already in place, the first Phase 6 priority should be a focused Heart / Recovery page that adds interpretation around HRV before broadening into every available metric.

**Deliverables**
- Add HRV 7-day and 30-day rolling averages.
- Add latest HRV, average HRV, min, max, and baseline delta summary values.
- Add resting heart rate trend and baseline comparison.
- Add a recovery summary card with rule-based states such as `Recovered`, `Normal`, `Strained`, and `Low data`.
- Add sleep context beside the heart metrics, including last night's sleep duration and sleep efficiency when available.
- Add a simple comparison of HRV after higher-sleep nights versus lower-sleep nights when the dataset has enough matching records.
- Add metric-specific empty states when HRV, resting heart rate, or sleep context is unavailable.

**Definition of Done**
- HRV can be interpreted against a personal baseline, not only viewed as raw points.
- Resting heart rate and sleep context render in the same workflow as HRV.
- The recovery summary is deterministic, explainable in code, and avoids medical claims.
- Missing optional metrics do not break the page or hide available HRV data.

**Deliverables**
- Activity page:
  - daily steps chart
  - weekly averages
  - most-active-day style summaries
- Heart page:
  - daily average heart rate
  - resting heart-rate trend
  - HRV trend where data exists
- Trends page:
  - simple comparison views
  - rule-based insights such as weekday versus weekend sleep or bedtime drift
- Imports / Data Manager page:
  - implemented read-only database status and aggregate import/storage cards
  - implemented metric inventory with counts, date coverage, and units
  - implemented latest-50 history with selection-driven warnings, duplicate context, and failures
  - implemented manual and post-import refresh without destructive data controls
  - authoritative design: `docs/superpowers/specs/2026-08-02-imports-data-manager-design.md`
  - detailed execution plan: `docs/superpowers/plans/2026-08-02-imports-data-manager.md`
  - handoff: `docs/implementation-summary-2026-08-02-imports-data-manager.md`
- Settings page:
  - database location setting
  - default date range
  - theme placeholder scaffolding

**Dependencies**
- Phases 1 through 5

**Definition of Done**
- Each nav section has meaningful content, even if some views are intentionally light
- Missing optional metrics are handled gracefully across all pages
- The app still feels coherent and polished as new sections are added

**May Remain Mocked or Scaffolded**
- Export workflows can stay as disabled or placeholder controls
- Correlation analysis can remain simple and rule-based

## Phase 7: Packaging and Documentation

**Purpose**
Make the project runnable, understandable, and ready for future packaging.

**Deliverables**
- Expand `README.md` with setup and run instructions
- Add short architecture summary
- Add extension notes for new Apple Health record types
- Add future enhancement section
- Verify project structure remains friendly to PyInstaller packaging

**Dependencies**
- Core app structure in place

**Definition of Done**
- A new contributor can install dependencies and run the app from the README
- The repo documents the architecture and extension path clearly
- Packaging direction is not blocked by layout choices

**May Remain Mocked or Scaffolded**
- Actual PyInstaller spec generation can be deferred

## Public Interfaces and Type Boundaries

### Normalized Record Shape

Parser output should define a stable record model carrying:
- normalized metric name
- original Apple source type
- source name
- start and end timestamps
- numeric or categorical value
- unit
- raw metadata payload when needed for traceability

This shape is the contract between parsing, persistence, analytics, and UI-read models.

### Database Responsibilities

- `records` stores normalized imported rows
- `sleep_sessions` stores derived nightly sleep summaries
- `daily_summaries` stores aggregated day-level metrics
- `import_history` stores file identity, import timestamps, status, counts, and duplicate detection results

### Service Boundaries

- Parser transforms XML into normalized records
- Import service owns file handling, orchestration, duplicate detection, and persistence coordination
- Database manager owns schema and SQL access
- Sleep analysis service owns nightly grouping and derived sleep metrics
- Dashboard controller assembles page-ready view data without embedding domain logic in widgets

### Dashboard Contracts

Overview page inputs:

- summary metrics
- recent trend datasets
- latest import status

Sleep page inputs:

- nightly sleep dataset
- bedtime and wake-time series
- weekly rollups
- active filter range

Both pages must support a polished empty-state path and a data-backed path without changing their high-level layout.

## Acceptance Test Scenarios

- App launches from `main.py` and initializes the database if it does not exist
- Import accepts a valid `export.xml`
- Import accepts a valid zip and auto-finds `export.xml`
- Invalid input produces a friendly error state
- Duplicate import detection prevents duplicate storage
- Sleep sessions crossing midnight are assigned to the correct night
- Missing optional metrics do not break import, analytics, or page rendering
- Overview works with real imported data
- Overview also works as an attractive no-data experience
- Sleep page filters behave correctly for 7, 30, and 90 day windows plus custom range handling

## Defaults and Assumptions

- Repo-native docs are the implementation source of truth.
- The external design brief remains the inspiration document rather than the working contract.
- MVP priority is import, storage, overview, and sleep.
- PySide6 is the default GUI framework.
- PyQtGraph is the default charting direction unless a specific chart need proves it insufficient.
- Non-core pages may ship scaffolded as long as the app shell and MVP pages feel complete.
