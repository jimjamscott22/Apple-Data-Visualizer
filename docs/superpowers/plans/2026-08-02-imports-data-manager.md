# Imports / Data Manager Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Imports placeholder with a read-only dashboard for database status,
record inventory, recent import attempts, and stored warning/failure details.

**Architecture:** Add immutable imports-page models and a pure `ImportHistoryService` between
MariaDB rows and Qt. `DatabaseManager` supplies three focused read queries,
`DashboardController` assembles the page data without exposing credentials, and a dedicated
`ImportsPage` renders the master-detail workflow and emits refresh requests.

**Tech Stack:** Python 3, PySide6, MariaDB 10.5+, PyMySQL, pytest, uv

## Global Constraints

- The page is read-only; do not add delete, retry, export, database-edit, or record-edit actions.
- Show at most the 50 most recent import attempts, ordered by `imported_at DESC, id DESC`.
- Never return or render the database password or file fingerprint.
- Preserve the database layer's string-typed `DATETIME` contract.
- Treat invalid JSON in `import_history.notes` as plain text and never fail page rendering.
- Use existing Qt/card/table styling; add no dependency and no new theme system.
- Run Python commands through `uv run`.

---

## File Structure

- Modify `app/models/imports.py` — immutable read models for the page.
- Create `app/services/import_history_service.py` — pure row parsing and model construction.
- Modify `app/database/manager.py` — aggregate, inventory, and expanded-history reads.
- Modify `app/services/dashboard_controller.py` — `load_imports_summary` façade.
- Modify `app/main.py` — construct and inject `ImportHistoryService`.
- Create `app/ui/pages/imports_page.py` — read-only master-detail Qt page.
- Modify `app/ui/main_window.py` — replace the placeholder and coordinate refreshes.
- Create `tests/test_import_history_service.py` — pure transformation tests.
- Modify `tests/test_database_manager.py` — live MariaDB read-query tests.
- Create `tests/test_imports_page.py` — offscreen Qt rendering and interaction tests.
- Create `tests/test_dashboard_controller.py` — controller orchestration/privacy tests.
- Modify `project_state.md`, `AGENTS.md`, and the planning docs after implementation.

### Task 1: Typed imports read model and note parser

**Files:**
- Modify: `app/models/imports.py`
- Create: `app/services/import_history_service.py`
- Test: `tests/test_import_history_service.py`

**Interfaces:**
- Consumes: raw statistics, inventory, and import-history dictionaries returned by Task 2.
- Produces: `ImportHistoryService.build_summary(...) -> ImportsSummaryData` for Task 3.

- [ ] **Step 1: Write failing model/transformation tests**

Cover empty rows, friendly metric labels, unknown metrics, structured completed/duplicate notes,
plain failure text, malformed JSON, non-list warnings, and unknown statuses. Use assertions such
as:

```python
summary = service.build_summary(
    database_status=DatabaseStatusData("Connected", "db.local", 3306, "health", "reader"),
    statistics_row={"completed_imports": 1, "stored_records": 12, "warning_count": 2,
                    "duplicate_attempts": 1},
    inventory_rows=[{"metric_name": "step_count", "record_count": 12,
                     "first_recorded_at": "2026-07-01 08:00:00",
                     "last_recorded_at": "2026-07-02 08:00:00", "unit": "count"}],
    history_rows=[{"id": 7, "file_name": "export.zip", "file_path": "C:/Health/export.zip",
                   "file_size": 2048, "import_status": "completed",
                   "duplicate_detected": 0, "record_count": 12, "warning_count": 2,
                   "imported_at": "2026-07-02 09:00:00",
                   "notes": '{"source_type":"zip","warnings":["first","second"]}'}],
)
assert summary.inventory[0].display_name == "Step Count"
assert summary.history[0].warnings == ("first", "second")
assert summary.history[0].source_type == "zip"
```

- [ ] **Step 2: Run the focused tests and confirm they fail**

Run: `uv run pytest tests/test_import_history_service.py -q`

Expected: collection/import failure because the new models and service do not exist.

- [ ] **Step 3: Add immutable models**

Add these frozen dataclasses to `app/models/imports.py`:

```python
@dataclass(frozen=True)
class DatabaseStatusData:
    status: str
    host: str
    port: int
    database: str
    user: str

@dataclass(frozen=True)
class ImportStatistics:
    completed_imports: int = 0
    stored_records: int = 0
    warning_count: int = 0
    duplicate_attempts: int = 0

@dataclass(frozen=True)
class MetricInventoryRecord:
    metric_name: str
    display_name: str
    record_count: int
    first_recorded_at: str | None
    last_recorded_at: str | None
    unit: str | None

@dataclass(frozen=True)
class ImportHistoryRecord:
    id: int
    file_name: str
    file_path: str
    file_size: int | None
    status: str
    status_label: str
    record_count: int
    warning_count: int
    imported_at: str
    source_type: str | None = None
    warnings: tuple[str, ...] = ()
    detail_message: str | None = None
    duplicate_of_import_id: int | None = None

@dataclass(frozen=True)
class ImportsSummaryData:
    database_status: DatabaseStatusData
    statistics: ImportStatistics
    inventory: tuple[MetricInventoryRecord, ...] = ()
    history: tuple[ImportHistoryRecord, ...] = ()
```

- [ ] **Step 4: Implement the pure transformation service**

Create `ImportHistoryService.build_summary(database_status, statistics_row, inventory_rows,
history_rows)`. Parse notes with `json.loads`; accept only dictionaries, convert a warnings list
to a tuple of strings, read an integer `duplicate_of_import_id`, and use raw text as
`detail_message` when JSON parsing fails. Use an explicit friendly-name map for current metrics
and `metric_name.replace("_", " ").title()` as the fallback.

- [ ] **Step 5: Run focused tests**

Run: `uv run pytest tests/test_import_history_service.py -q`

Expected: all tests pass.

- [ ] **Step 6: Commit Task 1**

```bash
git add app/models/imports.py app/services/import_history_service.py tests/test_import_history_service.py
git commit -m "feat: add imports dashboard read models"
```

### Task 2: MariaDB dashboard reads

**Files:**
- Modify: `app/database/manager.py`
- Modify: `tests/test_database_manager.py`

**Interfaces:**
- Produces: `get_import_statistics()`, `get_record_inventory()`, and expanded
  `list_recent_imports(limit=50)` dictionaries consumed by Tasks 1 and 3.

- [ ] **Step 1: Add failing live-database tests**

Seed completed and duplicate imports plus multiple metric records. Assert aggregate counts,
inventory ordering/date coverage, newest-first history, limit enforcement, expanded fields, and
`"file_fingerprint" not in history_row`. Retain the file's existing live-server skip fixture.

- [ ] **Step 2: Run the targeted database tests and confirm they fail**

Run: `uv run pytest tests/test_database_manager.py -q`

Expected: failures for missing methods/fields when MariaDB is available; documented skips when
it is unavailable.

- [ ] **Step 3: Implement aggregate statistics**

Add `get_import_statistics()` using one row with scalar subqueries:

```sql
SELECT
  (SELECT COUNT(*) FROM import_history WHERE import_status = 'completed') AS completed_imports,
  (SELECT COUNT(*) FROM records) AS stored_records,
  COALESCE((SELECT SUM(warning_count) FROM import_history), 0) AS warning_count,
  (SELECT COUNT(*) FROM import_history
   WHERE import_status = 'duplicate' OR duplicate_detected = 1) AS duplicate_attempts
```

- [ ] **Step 4: Implement record inventory**

Add `get_record_inventory()`:

```sql
SELECT metric_name, COUNT(*) AS record_count,
       MIN(start_at) AS first_recorded_at, MAX(start_at) AS last_recorded_at,
       MAX(unit) AS unit
FROM records
GROUP BY metric_name
ORDER BY record_count DESC, metric_name ASC
```

- [ ] **Step 5: Expand recent-import history safely**

Change the default limit to 50 and select `id`, `file_path`, `file_name`, `file_size`,
`import_status`, `duplicate_detected`, `record_count`, `warning_count`, `imported_at`, and
`notes`. Keep the parameterized `LIMIT %s`; do not select `file_fingerprint`.

- [ ] **Step 6: Run database tests**

Run: `uv run pytest tests/test_database_manager.py -q`

Expected: all available tests pass; live tests may skip only for the documented unavailable
server condition.

- [ ] **Step 7: Commit Task 2**

```bash
git add app/database/manager.py tests/test_database_manager.py
git commit -m "feat: add imports dashboard database reads"
```

### Task 3: Controller orchestration and credential boundary

**Files:**
- Modify: `app/services/dashboard_controller.py`
- Modify: `app/main.py`
- Create: `tests/test_dashboard_controller.py`

**Interfaces:**
- Consumes: Task 1's service/models and Task 2's database methods.
- Produces: `DashboardController.load_imports_summary(limit=50) -> ImportsSummaryData`.

- [ ] **Step 1: Write failing controller tests**

Use a fake database manager with a `DatabaseSettings` instance and call counters. Assert all
three read methods receive the expected limit/data and that recursively rendered model text
does not contain the password or fingerprint.

- [ ] **Step 2: Run the controller tests and confirm they fail**

Run: `uv run pytest tests/test_dashboard_controller.py -q`

- [ ] **Step 3: Add the service dependency and load method**

Extend the controller constructor with `import_history_service: ImportHistoryService`. Build
`DatabaseStatusData` only from `settings.host`, `port`, `database`, and `user`, then call:

```python
return self.import_history_service.build_summary(
    database_status=database_status,
    statistics_row=self.database_manager.get_import_statistics(),
    inventory_rows=self.database_manager.get_record_inventory(),
    history_rows=self.database_manager.list_recent_imports(limit=limit),
)
```

- [ ] **Step 4: Wire construction in `app/main.py`**

Instantiate `ImportHistoryService()` and pass it to `DashboardController` beside the existing
analysis services. Update every controller construction in tests.

- [ ] **Step 5: Run focused service/controller tests**

Run: `uv run pytest tests/test_import_history_service.py tests/test_dashboard_controller.py -q`

Expected: all pass.

- [ ] **Step 6: Commit Task 3**

```bash
git add app/services/dashboard_controller.py app/main.py tests/test_dashboard_controller.py
git commit -m "feat: expose imports dashboard data"
```

### Task 4: Read-only Imports page

**Files:**
- Create: `app/ui/pages/imports_page.py`
- Create: `tests/test_imports_page.py`
- Modify: `app/theme.py`

**Interfaces:**
- Consumes: `ImportsSummaryData` from Task 3.
- Produces: `ImportsPage.render(summary, preserve_import_id=None)` and `refresh_requested`.

- [ ] **Step 1: Write failing offscreen Qt tests**

Create one populated summary containing completed, duplicate, and failed records. Assert empty
states, four formatted statistics, inventory/history rows, automatic first selection, detail
changes after `history_table.selectRow(...)`, refresh emission, and absence of secret strings.

- [ ] **Step 2: Run the page tests and confirm they fail**

Run: `uv run pytest tests/test_imports_page.py -q`

- [ ] **Step 3: Build the status and summary sections**

Create `ImportsPage(QWidget)` with `refresh_requested = Signal()`. Use existing `MetricCard`,
`EmptyStateCard`, `MetricCard`/`SettingsCard` object names, a read-only connection form, and a
Refresh button connected to `refresh_requested.emit`.

- [ ] **Step 4: Build inventory and history tables**

Use non-editable `QTableWidget`s. Inventory has five columns and no selection; history has six
columns and `SingleSelection`/`SelectRows`. Store each import ID in the history row's first item
with `Qt.UserRole`, and connect `itemSelectionChanged` to the detail renderer.

- [ ] **Step 5: Build status-specific details and selection preservation**

Render common metadata in selectable wrapping labels. Render warnings as one bullet per line,
duplicate references as `Duplicate of import #N`, failures from `detail_message`, and neutral
copy for missing data. Before clearing the table capture the selected ID; after repopulating,
reselect it if present or select row zero.

- [ ] **Step 6: Add only necessary theme selectors**

Add object-name selectors for status text and the import-detail panel. Reuse existing colors;
status must remain understandable from its text without color.

- [ ] **Step 7: Run page tests**

Run: `uv run pytest tests/test_imports_page.py -q`

Expected: all pass under the test's `QT_QPA_PLATFORM=offscreen` setup.

- [ ] **Step 8: Commit Task 4**

```bash
git add app/ui/pages/imports_page.py app/theme.py tests/test_imports_page.py
git commit -m "feat: build read-only imports dashboard"
```

### Task 5: Main-window integration and refresh behavior

**Files:**
- Modify: `app/ui/main_window.py`
- Modify: `tests/test_imports_page.py`

**Interfaces:**
- Consumes: `ImportsPage` and `DashboardController.load_imports_summary`.
- Produces: a real Imports navigation page refreshed manually and after every terminal import.

- [ ] **Step 1: Add a failing integration-focused test**

Use a controller fake whose `load_imports_summary` increments a counter. Verify page refresh
emission invokes exactly one load, and a failed `ImportResult` reloads imports history even
though it does not reload every analytics page.

- [ ] **Step 2: Replace the placeholder**

Import and construct `ImportsPage`, connect `refresh_requested` to
`_refresh_imports_page`, add it at navigation index 5, and remove `PlaceholderPage` from the
main-window import if no longer used.

- [ ] **Step 3: Add targeted refresh orchestration**

Implement:

```python
def _refresh_imports_page(self) -> None:
    self.imports_page.render(self.dashboard_controller.load_imports_summary(limit=50))
```

Call it from `refresh_pages()`. On successful/duplicate results keep `refresh_pages()`; on a
failed result call only `_refresh_imports_page()` before showing the warning dialog.

- [ ] **Step 4: Run focused integration tests**

Run: `uv run pytest tests/test_imports_page.py tests/test_dashboard_controller.py -q`

Expected: all pass.

- [ ] **Step 5: Commit Task 5**

```bash
git add app/ui/main_window.py tests/test_imports_page.py
git commit -m "feat: wire imports dashboard navigation"
```

### Task 6: Documentation, full verification, and handoff

**Files:**
- Modify: `project_state.md`
- Modify: `docs/spec-sheet.md`
- Modify: `docs/implementation-plan.md`
- Modify: `AGENTS.md`
- Create: `docs/implementation-summary-2026-08-02-imports-data-manager.md`

**Interfaces:**
- Consumes: verified results from Tasks 1-5.
- Produces: an accurate repository handoff with no stale Imports-placeholder claims.

- [ ] **Step 1: Update repository status documentation**

Mark Imports/Data Manager implemented, list its models/service/page/tests, remove its known-gap
and next-phase entries, and link this spec and plan from the general planning documents.

- [ ] **Step 2: Run focused and full verification**

Run:

```bash
uv run pytest tests/test_import_history_service.py tests/test_dashboard_controller.py tests/test_imports_page.py -q
uv run pytest -q
uv run python -m compileall app main.py
git diff --check
```

Record passes, failures, and live-MariaDB skips separately. If the documented live server is
available, also run the full live command from `AGENTS.md`.

- [ ] **Step 3: Perform manual offscreen/desktop checks**

Verify empty data, populated data, completed warnings, duplicate details, failed details,
manual Refresh, post-import refresh, keyboard row selection, and that neither database password
nor fingerprint appears.

- [ ] **Step 4: Write the required implementation summary and update `AGENTS.md`**

Document the files, behavior, read-only boundary, data definitions, tests, and any incomplete
verification. Add a dated concise entry to the `AGENTS.md` Implementation Summary.

- [ ] **Step 5: Commit the completed slice**

```bash
git add AGENTS.md project_state.md docs app tests
git commit -m "docs: record imports dashboard implementation"
```
