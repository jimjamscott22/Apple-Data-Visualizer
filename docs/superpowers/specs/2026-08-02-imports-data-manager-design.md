# Imports / Data Manager Design Specification

**Status:** Approved design
**Date:** 2026-08-02

## Purpose

Replace the Imports navigation placeholder with a read-only operational dashboard that makes
the existing MariaDB import state understandable. The page must show whether the configured
database is connected, what health data is stored, which imports have run, and the warnings or
failure details associated with a selected import.

The page is an observability surface, not a database administration tool. The existing global
`Import Apple Health Export` button remains the only write action in this workflow.

## Scope

The first version includes:

- a read-only database connection panel;
- summary cards for completed imports, stored records, stored parser warnings, and duplicate
  attempts;
- a global record inventory grouped by normalized `metric_name`;
- the 50 most recent import attempts, including completed, duplicate, and failed outcomes;
- a selection-driven detail panel that explains one import attempt;
- safe rendering of structured JSON notes and legacy plain-text failure notes;
- automatic refresh after an import finishes and a manual Refresh action.

## Non-Goals

This version does not include:

- deleting imports, records, summaries, or sleep sessions;
- editing database connection settings or credentials;
- retrying an old import from its stored path;
- exporting records or reports;
- browsing individual health samples;
- displaying file fingerprints;
- pagination, search, or advanced filtering;
- database migration, backup, restore, or maintenance controls.

## User Experience

The page uses a vertically stacked master-detail layout consistent with the existing dark card
system.

### Database Status Panel

The first panel shows:

- status: `Connected`;
- host and port;
- database name;
- database user;
- a `Refresh` button.

The password is never passed to the page or rendered. The panel is informational; its fields
cannot be edited. Runtime reconnection behavior remains governed by the app's existing
MariaDB startup and query handling.

### Summary Cards

Four cards appear below the connection panel:

1. **Completed imports** — count of `import_history` rows whose status is `completed`.
2. **Stored records** — total rows in `records`.
3. **Parser warnings** — sum of `warning_count` across import-history rows.
4. **Duplicate attempts** — count of rows whose status is `duplicate` or whose
   `duplicate_detected` flag is true.

All values are database-wide snapshots. Counts use thousands separators.

### Record Inventory

The record inventory is a non-editable table with these columns:

- Metric
- Records
- First recorded
- Last recorded
- Unit

Rows are grouped by normalized `records.metric_name`, ordered by record count descending and
then metric name ascending. The query returns the count, minimum `start_at`, maximum
`start_at`, and a representative non-null unit. Known metric names use friendly labels such as
`Sleep Analysis`, `Step Count`, and `Heart Rate Variability`; unknown future metrics fall back
to title-cased words rather than disappearing.

When no records exist, the table is replaced by a focused empty state explaining that an Apple
Health export must be imported. Import-history rows may still appear, for example after a
failed or duplicate attempt.

### Import History

The history table shows the 50 most recent attempts, ordered by `imported_at DESC, id DESC`.
It is non-editable and uses single-row selection. Columns are:

- Imported
- File
- Status
- Records
- Warnings
- Size

Status is written as text as well as styled by color, so meaning never depends on color alone.
Supported display states are `Completed`, `Duplicate`, `Failed`, and `In progress`; unknown
stored values are shown as safely title-cased text.

The first row is selected automatically after data loads. If there is no import history, the
page shows `No imports yet` and the detail panel remains hidden.

### Selected Import Details

Selecting a history row updates an inline detail panel without another database query. The
panel shows:

- file name and full stored file path;
- imported timestamp and file size;
- status, record count, and warning count;
- source type (`xml` or `zip`) when present in structured notes.

Conditional content is status-specific:

- **Completed:** render each stored parser warning as a readable list. If `warning_count` is
  zero, show `No parser warnings were recorded.`
- **Duplicate:** show the original import ID from `duplicate_of_import_id` when available and
  explain that no records were inserted.
- **Failed:** show the stored plain-text failure message. It must wrap and remain selectable.
- **In progress:** explain that the attempt has not reached a terminal state. This state is
  uncommon because the current transaction rolls back interrupted imports, but the UI must
  tolerate it.

Malformed or unexpected `notes` data must not break the page. Invalid JSON is treated as plain
text; non-list `warnings` values are ignored; missing fields render neutral explanatory copy.

## Architecture and Responsibilities

### Read Models

Extend `app/models/imports.py` with immutable page models:

- `DatabaseStatusData`
- `ImportStatistics`
- `MetricInventoryRecord`
- `ImportHistoryRecord`
- `ImportsSummaryData`

`ImportsSummaryData` owns the database status, aggregate statistics, inventory rows, and recent
history rows needed for one render. UI widgets consume these models and never receive raw SQL
rows or the database password.

### Database Access

`DatabaseManager` provides focused read methods:

- `get_import_statistics() -> dict`
- `get_record_inventory() -> list[dict]`
- `list_recent_imports(limit: int = 50) -> list[dict]`

The expanded history query returns the stored ID, path, name, size, status, duplicate flag,
record count, warning count, timestamp, and notes. It does not return the fingerprint. All
methods are read-only and parameterized.

### Transformation Service

Add `ImportHistoryService` in `app/services/import_history_service.py`. It converts raw database
rows into the typed page models, formats friendly metric and status labels, and parses the
polymorphic `notes` column. Keeping this logic outside Qt and SQL makes malformed-note behavior
unit-testable.

### Controller and UI

`DashboardController.load_imports_summary(limit: int = 50)` obtains the three database
datasets and delegates transformation to `ImportHistoryService`.

Add `ImportsPage` in `app/ui/pages/imports_page.py`. It owns presentation and row-selection
behavior only. It exposes a refresh callback or signal; `MainWindow` responds by loading and
rendering a fresh `ImportsSummaryData`. `MainWindow.refresh_pages()` also refreshes this page
after a successful, failed, or duplicate import attempt completes.

The existing `PlaceholderPage` class remains available for future scaffolds but is no longer
used by any navigation entry.

## Refresh and State Behavior

- Initial application refresh loads the page once.
- Selecting Imports does not issue a redundant query if current data is already rendered.
- The page refreshes after every completed import worker result, regardless of outcome.
- The manual Refresh action reloads only Imports/Data Manager data.
- Refresh preserves the selected import by ID when that ID remains in the latest 50 rows;
  otherwise the newest row becomes selected.
- Empty inventory and empty history are independent states.

## Accessibility and Privacy

- Tables are keyboard reachable, read-only, and single-selection.
- Status text accompanies status color.
- Empty states explain the next available action.
- Warning and error text wraps and can be selected for troubleshooting.
- Database passwords and file fingerprints never enter the page model.
- Full file paths appear only in the selected detail panel, not in the history table.

## Verification Requirements

### Unit Tests

Tests for `ImportHistoryService` cover:

- empty datasets;
- aggregate and inventory conversion;
- friendly labels plus unknown-metric fallback;
- completed JSON notes with and without warnings;
- duplicate JSON notes;
- failed plain-text notes;
- malformed JSON and incorrectly typed warning values;
- unknown import statuses.

### Database Tests

Live MariaDB tests cover:

- aggregate counts across completed, duplicate, and failed attempts;
- inventory grouping, ordering, date coverage, and units;
- expanded history fields and descending ordering;
- history limit enforcement;
- confirmation that fingerprints are not returned.

These tests retain the repository's existing self-skip behavior when a live test database is
unavailable.

### UI and Integration Tests

Offscreen Qt tests cover:

- empty history and empty inventory rendering;
- summary cards and both tables rendering typed data;
- automatic first-row selection;
- selection updating completed, duplicate, and failed detail content;
- refresh signal/callback behavior;
- absence of database password and fingerprint text.

Final verification runs:

- `uv run pytest -q`
- `uv run python -m compileall app main.py`
- `git diff --check`

When a configured MariaDB test server is available, run the documented live-DB test command as
well and report skipped live tests separately from failures.

## Acceptance Criteria

The section is complete when:

- Imports no longer renders `PlaceholderPage`;
- a user can understand database connectivity and total stored data at a glance;
- every normalized metric with stored records appears in the inventory;
- the latest 50 import attempts render with accurate status and counts;
- selecting an attempt reveals useful warning, duplicate, or failure context;
- malformed historical notes cannot crash rendering;
- no UI action mutates or deletes stored data;
- the page refreshes after imports and on explicit request;
- missing data produces polished, specific empty states;
- focused tests, the full available suite, compile check, and diff check pass.
