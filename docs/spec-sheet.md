# Apple Health Data Analyzer Spec Sheet

## Purpose
Apple Health Data Analyzer is a desktop analytics app for Windows and Linux that imports Apple Health export data, normalizes it into a local SQLite database, and presents the data in a polished, insight-oriented dashboard. The product should feel approachable and modern rather than like an internal utility, with a particular emphasis on making sleep analysis genuinely useful.

This spec turns the high-level design brief into the implementation contract for the repository. It defines the MVP, the initial architecture, the data boundaries, and the expected user experience so implementation can proceed without reopening foundational decisions.

## Product Goals
- Let a user import either an Apple Health `export.xml` file or the export zip containing `export.xml`.
- Parse supported Apple Health records into a normalized internal format that can be extended later.
- Store both raw imported records and useful derived summaries in SQLite.
- Present a polished desktop dashboard with strong sleep analytics, clear overview metrics, and room to grow into broader health insights.
- Keep the codebase modular, readable, and educational so it remains easy to study and extend.

## Target Users
- Primary: a technically comfortable individual who exports Apple Health data and wants desktop analysis beyond the Apple Health app.
- Secondary: a student or developer using the project as a portfolio or learning codebase.

## Supported Platforms and Stack
- Language: Python 3
- Desktop UI: PySide6
- Storage: SQLite
- Charting: PyQtGraph preferred for native integration and responsive desktop charts
- Parsing: `xml.etree.ElementTree`
- Packaging direction: layout and resource handling should remain PyInstaller-friendly

## MVP Scope
The MVP is the first build that should feel meaningfully usable. It does not need full parity with the original vision doc.

### Included in MVP
- Import flow for `export.xml` and zip-based Apple Health exports
- Import validation and friendly error reporting
- XML parser foundation with extensible Apple record type mapping
- SQLite schema creation on first run
- Import history and duplicate-import prevention
- Overview dashboard page
- Strong Sleep page with nightly analysis and filters
- Activity, Heart, Trends, Imports, and Settings sections scaffolded into the application shell
- Demo or fallback data support for early UI wiring and polished empty states

### Deferred Beyond MVP
- Advanced cross-metric correlation analysis
- CSV export workflow
- Notes or tagging on nights
- AI-generated health insights
- Full light theme
- Deep settings customization

## Primary User Flow
1. Launch the application from `main.py`.
2. See either an attractive empty state or an overview dashboard if data already exists.
3. Select an Apple Health export file from the import action.
4. App validates the selected file.
5. If the file is a zip, the app extracts it to a temporary location and finds `export.xml`.
6. Parser reads supported records and maps them into normalized internal models.
7. Import service writes records, summaries, and metadata to SQLite while preventing duplicate imports.
8. Dashboard refreshes to show updated overview metrics and sleep analytics.

## Functional Requirements

### Import Flow
- Support direct import of `export.xml`.
- Support direct import of an Apple Health export zip.
- Automatically detect and locate `export.xml` inside the zip.
- Reject invalid files with clear, non-technical error messaging.
- Track import status, timestamps, source file metadata, and duplicate detection results.

### Record Types Supported for MVP
- Sleep Analysis
- Step Count
- Heart Rate
- Resting Heart Rate
- Heart Rate Variability
- Respiratory Rate
- Walking/Running Distance

Unsupported record types must be ignored without crashing and should be optionally logged for future support analysis.

### Sleep Analytics
Sleep is the signature experience of the MVP.

The app must:
- Parse Apple sleep values such as in-bed, asleep, awake, and sleep-stage variants when present.
- Group sleep records into a human-friendly “night” even when sessions cross midnight.
- Compute nightly sleep duration.
- Compute time in bed.
- Estimate sleep efficiency when both asleep and in-bed data exist.
- Track bedtime and wake-time trends.
- Aggregate weekly and monthly average sleep duration.
- Measure consistency of bedtime and wake time using repeatable rule-based logic.

### Overview Dashboard
The overview page should surface fast, useful context:
- average sleep this week
- last night sleep duration
- average daily steps
- latest resting heart rate
- imported record count
- most recent import status
- small embedded recent-trend visuals

### Sleep Page
The sleep page must include:
- nightly sleep duration chart
- bedtime trend chart
- wake-time trend chart
- weekly average sleep bar chart
- sleep consistency summary indicator
- nightly sleep sessions table
- date-range filters for 7, 30, and 90 days plus a custom range

### Scaffolded Follow-On Areas
These pages should exist in navigation even if some widgets are placeholders in the first implementation pass:
- Activity
- Heart
- Trends
- Imports / Data Manager
- Settings

Their initial role is to validate application structure and preserve expansion room without blocking MVP delivery.

## UX and Visual Contract
- Dark-mode-first visual direction inspired by modern health apps
- Rounded cards and panels
- Strong spacing and hierarchy rather than stacked default widgets
- Readable typography and distinct metric group styling
- Charts should feel integrated with the UI, not embedded as obvious afterthoughts
- Empty states should look polished and useful, especially before the first import
- The app shell should include:
  - sidebar navigation
  - top header/title area
  - central content area
  - clear import call to action

## Initial Project Structure
The codebase should be organized around clear module boundaries:

```text
app/
  main.py
  ui/
  services/
  database/
  parser/
  models/
  charts/
  utils/
docs/
  spec-sheet.md
  implementation-plan.md
```

This structure keeps UI, parsing, storage, and business logic separate while remaining beginner-readable.

## Core Responsibilities and Interfaces
These are responsibility-level contracts, not final method signatures.

### `HealthDataParser`
- Accept a resolved `export.xml` path.
- Iterate Apple Health records.
- Map Apple record types into internal metric names.
- Parse and normalize datetime values consistently.
- Return structured, validated record models plus parser warnings.

### `ImportService`
- Accept a user-selected file path.
- Detect file type and resolve `export.xml`.
- Coordinate duplicate detection.
- Invoke the parser.
- Persist import metadata, normalized records, and derived summaries.
- Return a result object suitable for UI status messages.

### `DatabaseManager`
- Create and initialize the SQLite database.
- Own connection setup and schema bootstrapping.
- Provide the data-access layer for imports, records, summaries, and dashboard reads.
- Keep SQL concerns outside of UI classes.

### `SleepAnalysisService`
- Build nightly sleep sessions from normalized sleep-related records.
- Handle midnight-crossing session grouping rules.
- Produce nightly metrics and rollups for charts and summary cards.

### `DashboardController`
- Coordinate page refreshes and dashboard data loading.
- Translate service-level results into view-ready data structures.
- Keep business logic out of the widget layer.

## Data Contract

### Parser Output Model
The parser should emit normalized records with these conceptual fields:
- `metric_name`
- `source_type`
- `source_name`
- `start_at`
- `end_at`
- `value`
- `unit`
- `metadata` or equivalent raw-attribute payload for traceability

The parser may retain raw Apple identifiers or attribute snapshots when useful, but UI code should consume normalized names rather than Apple-specific type strings.

### Record Type Mapping
A mapping layer must translate Apple Health record identifiers into internal metric names. This mapping should live in configuration or parser support code rather than being scattered through the UI or database layer.

### Database Schema Expectations
The initial schema must support the following logical tables:

#### `records`
- normalized imported health records
- one row per imported Apple Health record
- indexed by metric type and datetime range for dashboard reads

#### `sleep_sessions`
- nightly derived sleep summaries
- one row per computed night/session
- stores derived fields such as total sleep, in-bed duration, efficiency, bedtime, wake time, and consistency-related inputs

#### `daily_summaries`
- daily metric rollups for overview and trend pages
- used for quick reads of steps, distance, heart averages, and other day-level analytics

#### `import_history`
- one row per import attempt or completed import
- tracks file identity, imported timestamp, duplicate status, record counts, and outcome messages

### Duplicate Import Prevention
The import layer should detect when the same source file has already been imported. The default strategy should be based on file fingerprinting or another reproducible import identity so the app can avoid writing duplicate data while still telling the user what happened.

### Time and Time Zone Handling
- Datetime parsing must be centralized.
- Stored values should be consistent and comparable.
- The app must preserve enough information to group records into user-meaningful nights and days.
- Midnight-crossing logic must be defined in the analysis layer rather than guessed in the UI.

## Dashboard Page Contracts

### Overview Page Contract
Expected inputs:
- summary cards for key metrics
- recent trend series
- latest import metadata

Behavior:
- if data exists, show key metrics and short-term trends
- if no data exists, show a polished empty state with a clear import action

Required MVP content:
- average sleep this week
- last night sleep duration
- average daily steps
- latest resting heart rate
- record count
- last import summary

### Sleep Page Contract
Expected inputs:
- nightly sleep session dataset
- bedtime and wake-time series
- weekly rollup data
- selected date-range filter state

Behavior:
- render charts and nightly table when sleep data exists
- show a sleep-specific empty state when imports exist but sleep data is unavailable
- gracefully handle partial data such as missing in-bed or sleep-stage records

Required MVP content:
- nightly duration trend
- bedtime trend
- wake-time trend
- weekly average chart
- consistency indicator
- nightly table

## Non-Functional Requirements
- Maintainable, educational code with clean naming
- Object-oriented structure without unnecessary abstraction
- Separation of UI from business logic and storage
- Friendly error handling and logging
- Extension-friendly architecture for additional Apple Health metrics
- Fast local startup and smooth desktop interactions

## Definition of MVP Success
The MVP is successful when:
- the app launches cleanly from `main.py`
- a user can import a real Apple Health export file
- the app stores normalized records and import metadata in SQLite
- the overview page displays meaningful summary information
- the sleep page feels polished and useful, not merely functional
- missing optional metrics do not break imports or dashboard rendering

## Extension Notes
The architecture should make new metric support straightforward:
- add a record type mapping
- add normalization rules if needed
- update storage or summary logic only where necessary
- expose new analytics in a service before wiring them into the UI

Future enhancement directions include:
- rule-based or AI-assisted health insights
- local LLM-generated summaries
- CSV export and richer data sharing
- a web dashboard companion
- annotation and journaling features for sleep nights
