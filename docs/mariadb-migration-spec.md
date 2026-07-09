# SQLite → MariaDB Migration Spec Sheet

## Purpose
This spec defines the contract for replacing the app's local SQLite storage
with a MariaDB server running on the user's LAN. The MariaDB server itself is
already provisioned; this document scopes the database/user creation
statements, the schema and driver changes required in the app, and the
connection-configuration contract so the migration can be implemented without
reopening these decisions mid-work.

This is a companion doc to `docs/spec-sheet.md`, which remains the source of
truth for product scope. This doc only concerns the storage backend change.

## Goals
- Replace the local, file-based SQLite database with a MariaDB database
  reachable over the LAN.
- Preserve the existing logical schema (`import_history`, `records`,
  `sleep_sessions`, `daily_summaries`) with MariaDB-appropriate column types.
- Centralize database connection settings (host, port, database, user,
  password) as configuration, not source, so credentials are never committed.
- Keep `DatabaseManager` as the single SQL boundary — no MariaDB-specific SQL
  should leak into services, controllers, or UI code.
- Preserve current behavior: first-run schema bootstrap, duplicate-import
  detection by fingerprint, and all existing dashboard read queries.

## Non-Goals
- No ORM adoption. The project keeps raw SQL via `DatabaseManager`, matching
  its current style.
- No multi-user or concurrent-write design beyond what MariaDB provides by
  default — this is still a single-user desktop app pointed at a personal
  server.
- No automatic migration of an existing local SQLite database's data unless
  the user asks for it (tracked as an optional phase, not required for a
  fresh setup).
- No change to parser, sleep analytics, or UI/business logic — only the
  storage backend and the code that talks to it.

## Current State
- `app/config.py` resolves a single `database_path` under `~/.apple-health-data-analyzer/health_data.sqlite3`.
- `app/database/manager.py` (`DatabaseManager`) owns all SQL:
  - opens a new `sqlite3.connect()` per call, using `sqlite3.Row` for
    dict-like row access
  - bootstraps schema via one `executescript()` call using SQLite DDL
    (`INTEGER PRIMARY KEY AUTOINCREMENT`, `PRAGMA foreign_keys`)
  - uses `?` placeholders throughout
  - uses SQLite-only functions/syntax: `datetime('now', '-N days')`,
    `date('now', ...)`, `substr(start_at, 1, 10)`, and
    `INSERT ... ON CONFLICT(...) DO UPDATE SET ...` for the `daily_summaries`
    upsert
- Callers outside `manager.py` (`app/services/trends_analysis_service.py`,
  `app/services/hrv_analysis_service.py`) type-hint and consume
  `sqlite3.Row` values directly.
- No DB-specific automated tests currently exist (`tests/` only covers
  `TrendsAnalysisService`).

## Target Architecture

### Driver
Use **PyMySQL** (pure-Python, MariaDB wire-protocol compatible, no native
client library to bundle). This matters because the spec sheet commits to
staying PyInstaller-friendly across Windows and Linux — the official
`mariadb` connector requires the native MariaDB Connector/C library to be
installed on the target machine, which complicates packaging. PyMySQL avoids
that entirely.

### Connection Configuration
Add a `DatabaseSettings` contract (new dataclass, e.g. in `app/config.py` or
a new `app/database/config.py`) sourced from environment variables, with
sane local-network defaults where reasonable:

| Setting | Env var | Default |
|---|---|---|
| Host | `APPLE_DV_DB_HOST` | *(required, no default)* |
| Port | `APPLE_DV_DB_PORT` | `3306` |
| Database | `APPLE_DV_DB_NAME` | `apple_health_data` |
| User | `APPLE_DV_DB_USER` | *(required, no default)* |
| Password | `APPLE_DV_DB_PASSWORD` | *(required, no default)* |

Credentials must never be hardcoded or committed. Support loading these from
a local `.env` file (via `python-dotenv`) for developer convenience, with
`.env` added to `.gitignore`, in addition to real environment variables.

### Schema Translation
| SQLite | MariaDB |
|---|---|
| `INTEGER PRIMARY KEY AUTOINCREMENT` | `INT UNSIGNED AUTO_INCREMENT PRIMARY KEY` |
| `TEXT` (timestamps: `start_at`, `end_at`, `imported_at`) | `DATETIME` (real temporal type — enables native date arithmetic and indexing instead of string comparisons) |
| `TEXT` (`night_date`, `summary_date`) | `DATE` |
| `TEXT` (free-form strings) | `VARCHAR(n)` where a reasonable bound exists, `TEXT` otherwise |
| `TEXT` (`metadata_json`, `summary_json`) | `JSON` (MariaDB 10.2+) |
| `REAL` | `DOUBLE` |
| implicit `PRAGMA foreign_keys = ON` | native FK enforcement via `ENGINE=InnoDB` (default-on) |
| no explicit charset | `CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci` on the database and tables |
| `UNIQUE(metric_name, summary_date)` | same, unchanged |
| indexes (`CREATE INDEX IF NOT EXISTS ...`) | same DDL shape, MariaDB supports `IF NOT EXISTS` on `CREATE INDEX` from 10.5+; assume 10.5+ as the minimum supported server version |

Switching `start_at`/`end_at`/`night_date`/`summary_date` to native
`DATETIME`/`DATE` is the one deliberate schema improvement bundled into this
migration — it replaces string-prefix filtering (`substr(start_at, 1, 10)`,
`start_at >= datetime('now', '-N days')`) with real date functions and
indexable comparisons, and removes a class of string-format bugs.

### Query Translation
- Placeholders: `?` → `%s` (PyMySQL uses `pyformat`/`format` paramstyle).
- Row access: `sqlite3.Row` → `pymysql.cursors.DictCursor` (keeps the
  existing `row["column"]` access pattern used throughout `manager.py` and
  the two services that consume rows directly).
- Schema bootstrap: `executescript()` has no MariaDB equivalent — split the
  DDL into individual statements and execute them in a loop, or move to a
  small ordered list of DDL strings.
- Relative-date filters: `datetime('now', '-' || ? || ' days')` →
  `DATE_SUB(NOW(), INTERVAL %s DAY)`; `date('now', '-' || ? || ' days')` →
  `DATE_SUB(CURDATE(), INTERVAL %s DAY)`.
- Upsert: `INSERT ... ON CONFLICT(metric_name, summary_date) DO UPDATE SET ...`
  → `INSERT ... ON DUPLICATE KEY UPDATE ...` (requires the existing
  `UNIQUE(metric_name, summary_date)` constraint, which is preserved).
- Day-prefix grouping (`substr(start_at, 1, 10)`) → `DATE(start_at)`, made
  simpler once `start_at` is a real `DATETIME` column.

### Connection Lifecycle
SQLite's per-call `with self.connect() as connection:` pattern is cheap
because it's a local file open. Over a LAN TCP connection, opening a new
connection per method call is wasteful and adds latency to every dashboard
read. Keep the same per-call method shape for a minimal-diff first pass, but
back it with a connection pool (e.g. `DBUtils.PooledDB` wrapping PyMySQL, or
PyMySQL's own reconnect-on-use pattern) so `connect()` returns a pooled
connection instead of opening a fresh TCP session each time. Pooling can land
as a fast-follow if it's cut from the first pass — call this out explicitly
so it isn't silently dropped.

### Error Handling
A LAN-connected MariaDB server introduces a failure mode that local SQLite
never had: the server can be unreachable, authentication can fail, or the
network can drop mid-session. The app must surface these as friendly,
specific error states (distinct from "no data yet" empty states) rather than
letting the app appear to hang or crash on startup or during an import.

## Risks and Open Questions
- **Offline use is no longer possible.** The app becomes dependent on LAN
  connectivity to the MariaDB host. This is an accepted tradeoff of the
  request but should be explicit rather than discovered later.
- **Plaintext credential storage.** Env var / `.env`-based credentials are
  acceptable for a personal LAN setup but are not encrypted at rest on the
  client machine. Flagging this rather than treating it as solved.
- **Server version assumption.** This spec assumes MariaDB 10.5+ (for
  `JSON` columns and `CREATE INDEX IF NOT EXISTS`). Confirm the user's LAN
  server meets this before implementation.
- **Existing local data.** If the user has an existing SQLite database with
  real imported health data, decide whether that data should be carried
  over (Phase 5 in the implementation plan) or whether a fresh MariaDB
  database with a re-import of the original Apple Health export is
  acceptable.

## Acceptance Criteria
- The MariaDB database, application user, and privileges can be created
  from the SQL published in `README.md` alone, with no other manual server
  setup required.
- The app reads connection settings from environment configuration and
  never contains a hardcoded host, user, or password.
- On startup, the app connects to the configured MariaDB server and
  bootstraps the schema if it does not already exist, mirroring today's
  first-run SQLite bootstrap behavior.
- Every existing `DatabaseManager` public method behaves equivalently
  against MariaDB (same inputs, same shape of outputs) as it does today
  against SQLite.
- No `sqlite3` import remains on the app's primary storage path.
- Connection failures (unreachable host, bad credentials) produce a clear,
  non-crashing error state in the UI.
