# Graph Report - .  (2026-08-10)

## Corpus Check
- 68 files · ~52,015 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 590 nodes · 1461 edges · 23 communities (17 shown, 6 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 203 edges (avg confidence: 0.58)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Dashboard UI Pages
- MariaDB Database Layer
- Imports Data Manager
- Trends Analysis
- Dashboard Services Models
- Import Parse Pipeline
- Documentation Specs
- Settings Preferences
- Main Window Shell
- Database Schema Tests
- Imports Page UI
- Implementation Phases
- Chart UI Design
- MariaDB Migration Plan
- Database Package Init
- App Package Init
- Models Package Init
- Parser Package Init
- UI Package Init
- PyProject Package

## God Nodes (most connected - your core abstractions)
1. `DatabaseManager` - 47 edges
2. `DashboardController` - 39 edges
3. `MainWindow` - 39 edges
4. `DatabaseSettings` - 32 edges
5. `TrendsAnalysisService` - 32 edges
6. `ImportsPage` - 32 edges
7. `_DashboardControllerFake` - 26 edges
8. `ImportHistoryService` - 24 edges
9. `ImportService` - 23 edges
10. `EmptyStateCard` - 23 edges

## Surprising Connections (you probably didn't know these)
- `Overview Recent Imports Table` --semantically_similar_to--> `ImportsPage`  [INFERRED] [semantically similar]
  docs/Apple-Health-Visualizer overview design/design_handoff_overview_1c/overview_1c.png → docs/superpowers/specs/2026-08-02-imports-data-manager-design.md
- `FakeDatabaseManager` --uses--> `DatabaseSettings`  [INFERRED]
  tests/test_dashboard_controller.py → app/database/config.py
- `_DashboardControllerFake` --uses--> `DatabaseSettings`  [INFERRED]
  tests/test_imports_page.py → app/database/config.py
- `_PreferenceStoreFake` --uses--> `DatabaseSettings`  [INFERRED]
  tests/test_imports_page.py → app/database/config.py
- `_DashboardControllerFake` --uses--> `ActivitySummaryData`  [INFERRED]
  tests/test_imports_page.py → app/models/activity.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Apple Health Import Pipeline** — claude_mainwindow, claude_importworker, claude_importservice, claude_healthdataparser, claude_databasemanager [EXTRACTED 1.00]
- **Imports Dashboard Read Path** — claude_databasemanager, docs_superpowers_specs_importshistoryservice, claude_dashboardcontroller, docs_superpowers_specs_importspage [EXTRACTED 1.00]
- **Overview 1c Layout Regions** — docs_apple_health_visualizer_overview_design_design_handoff_overview_1c_overview_1c_png_kpi_row, docs_apple_health_visualizer_overview_design_design_handoff_overview_1c_overview_1c_png_chart_mosaic, docs_apple_health_visualizer_overview_design_design_handoff_overview_1c_overview_1c_png_recent_imports_table [EXTRACTED 1.00]

## Communities (23 total, 6 thin omitted)

### Community 0 - "Dashboard UI Pages"
Cohesion: 0.06
Nodes (40): ClockAxisItem, disable_chart_interaction(), IndexDateAxisItem, PlotWidget, Themed pyqtgraph helpers shared across dashboard pages., Stop wheel-zoom/drag-pan from flinging these read-only charts off-screen., Axis that renders 'hours since prior noon' values as real HH:MM clock times.…, Bottom axis that labels integer plot indices with their real calendar date.… (+32 more)

### Community 1 - "MariaDB Database Layer"
Cohesion: 0.05
Nodes (33): DatabaseSettings, get_database_settings(), MissingDatabaseSettingsError, RuntimeError, Raised when required MariaDB connection settings are not configured., Build MariaDB connection settings from environment variables. Loads a local…, DatabaseConnectionError, RuntimeError (+25 more)

### Community 2 - "Imports Data Manager"
Cohesion: 0.07
Nodes (36): Any, DatabaseStatusData, ImportHistoryRecord, ImportsSummaryData, ImportStatistics, MetricInventoryRecord, Load the read-only Imports/Data Manager model without credential fields., ImportHistoryService (+28 more)

### Community 3 - "Trends Analysis"
Cohesion: 0.06
Nodes (24): CorrelationPoint, CorrelationResult, SplitComparison, TrendsSummaryData, Computes cross-metric correlations from sleep sessions and daily summaries.…, Compare next-day HRV after higher-sleep nights vs lower-sleep nights., Build the Trends page dataset. Args: sleep_rows: dict list from sleep_sessions…, TrendsAnalysisService (+16 more)

### Community 4 - "Dashboard Services Models"
Cohesion: 0.06
Nodes (28): main(), ActivityDayRecord, ImportStatusSummary, MetricCardData, OverviewData, HRVDailyRecord, HRVSummaryData, SleepNightRecord (+20 more)

### Community 5 - "Import Parse Pipeline"
Cohesion: 0.08
Nodes (19): FileInspectionResult, ImportResult, ResolvedImportSource, HealthDataParser, _ProgressTrackingReader, datetime, Path, Wraps a binary file object so ET.iterparse's reads can drive a progress… (+11 more)

### Community 6 - "Documentation Specs"
Cohesion: 0.06
Nodes (44): DashboardController, DatabaseManager, DatabaseSettings, HealthDataParser, ImportService, ImportWorker, MainWindow, PyQtGraph (+36 more)

### Community 7 - "Settings Preferences"
Cohesion: 0.10
Nodes (21): AppPreferences, PreferenceStore, Persist local UI preferences separately from health data., QFrame, QWidget, _select_data(), _settings_card(), SettingsPage (+13 more)

### Community 8 - "Main Window Shell"
Cohesion: 0.17
Nodes (4): MainWindow, QWidget, QMainWindow, QScrollArea

### Community 9 - "Database Schema Tests"
Cohesion: 0.18
Nodes (7): MariaDB schema DDL for the application's storage backend. This mirrors the…, _live_mariadb_connection(), fixture, _table_created_by(), _tables_referenced_by_foreign_key(), TestSchemaAgainstLiveMariaDB, TestSchemaStructure

### Community 10 - "Imports Page UI"
Cohesion: 0.31
Nodes (7): _configure_table(), QFrame, QLabel, QWidget, _section_card(), _selectable_label(), QTableWidget

### Community 11 - "Implementation Phases"
Cohesion: 0.33
Nodes (6): Phase 1 Foundation, Phase 2 Data Layer, Phase 3 Import and Parsing, Phase 4 Sleep Analytics MVP, Phase 5 UI MVP, Phase 6 Expansion Pass

### Community 12 - "Chart UI Design"
Cohesion: 0.40
Nodes (5): ClockAxisItem, IndexDateAxisItem, UI Design Review, Range Button Segmented Control, Transparent QLabel Backgrounds

### Community 13 - "MariaDB Migration Plan"
Cohesion: 0.67
Nodes (3): MariaDB Migration Phase 1 Connection Configuration, MariaDB Migration Phase 3 DatabaseManager Port, MariaDB Migration Phase 4 App Wiring

## Knowledge Gaps
- **23 isolated node(s):** `apple-data-visualizer`, `Imports Data Manager Planning Summary`, `PySide6`, `PyQtGraph`, `DatabaseSettings` (+18 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TrendsAnalysisService` connect `Trends Analysis` to `MariaDB Database Layer`, `Dashboard Services Models`?**
  _High betweenness centrality (0.112) - this node is a cross-community bridge._
- **Why does `DatabaseManager` connect `MariaDB Database Layer` to `Dashboard Services Models`, `Import Parse Pipeline`?**
  _High betweenness centrality (0.104) - this node is a cross-community bridge._
- **Why does `DashboardController` connect `Dashboard Services Models` to `Dashboard UI Pages`, `MariaDB Database Layer`, `Imports Data Manager`, `Trends Analysis`, `Import Parse Pipeline`, `Main Window Shell`?**
  _High betweenness centrality (0.095) - this node is a cross-community bridge._
- **Are the 12 inferred relationships involving `DatabaseManager` (e.g. with `DatabaseSettings` and `DatabaseConnectionError`) actually correct?**
  _`DatabaseManager` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `DashboardController` (e.g. with `DatabaseManager` and `ActivitySummaryData`) actually correct?**
  _`DashboardController` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `MainWindow` (e.g. with `DatabaseSettings` and `OverviewData`) actually correct?**
  _`MainWindow` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `DatabaseSettings` (e.g. with `DatabaseManager` and `MainWindow`) actually correct?**
  _`DatabaseSettings` has 14 INFERRED edges - model-reasoned connections that need verification._