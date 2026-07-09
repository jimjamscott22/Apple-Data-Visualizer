"""MariaDB schema DDL for the application's storage backend.

This mirrors the table/index shape bootstrapped by the SQLite
`DatabaseManager.initialize()` today, translated per the table in
`docs/mariadb-migration-spec.md`:

- `INTEGER PRIMARY KEY AUTOINCREMENT` -> `INT UNSIGNED AUTO_INCREMENT PRIMARY KEY`
- timestamp columns (`start_at`, `end_at`, `imported_at`, `bedtime_at`,
  `wake_at`) -> `DATETIME`
- date-only columns (`night_date`, `summary_date`) -> `DATE`
- `metadata_json` / `summary_json` -> `JSON` (always written via
  `json.dumps(...)`)
- `import_history.notes` stays `TEXT`, not `JSON` — `log_failed_import`
  writes a plain exception string into it, while other call sites write
  `json.dumps(...)`; a native `JSON` column would reject the plain-string
  writes
- `REAL` -> `DOUBLE`
- explicit `ENGINE=InnoDB` (for real foreign-key enforcement, replacing
  SQLite's `PRAGMA foreign_keys = ON`) and `utf8mb4`/`utf8mb4_unicode_ci`

Statements are ordered so `import_history` exists before the tables that
reference it via foreign key. PyMySQL (and most MariaDB drivers) execute
one statement per call, unlike `sqlite3.Connection.executescript()`, so
this is an ordered tuple of individual statements rather than one script
string. Each statement is idempotent (`IF NOT EXISTS`) and safe to re-run,
matching the current SQLite bootstrap behavior.
"""

from __future__ import annotations

MARIADB_SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS import_history (
        id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        file_path VARCHAR(1024) NOT NULL,
        file_name VARCHAR(255) NOT NULL,
        file_size BIGINT UNSIGNED,
        file_fingerprint VARCHAR(128),
        import_status VARCHAR(32) NOT NULL,
        duplicate_detected TINYINT(1) NOT NULL DEFAULT 0,
        record_count INT UNSIGNED NOT NULL DEFAULT 0,
        warning_count INT UNSIGNED NOT NULL DEFAULT 0,
        imported_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        notes TEXT
    ) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS records (
        id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        import_id INT UNSIGNED,
        metric_name VARCHAR(64) NOT NULL,
        source_type VARCHAR(64) NOT NULL,
        source_name VARCHAR(255),
        start_at DATETIME NOT NULL,
        end_at DATETIME,
        value DOUBLE,
        unit VARCHAR(32),
        metadata_json JSON,
        FOREIGN KEY (import_id) REFERENCES import_history(id) ON DELETE SET NULL
    ) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS sleep_sessions (
        id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        import_id INT UNSIGNED,
        night_date DATE NOT NULL,
        bedtime_at DATETIME,
        wake_at DATETIME,
        total_sleep_hours DOUBLE,
        time_in_bed_hours DOUBLE,
        sleep_efficiency DOUBLE,
        consistency_score DOUBLE,
        summary_json JSON,
        FOREIGN KEY (import_id) REFERENCES import_history(id) ON DELETE SET NULL
    ) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS daily_summaries (
        id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        metric_name VARCHAR(64) NOT NULL,
        summary_date DATE NOT NULL,
        average_value DOUBLE,
        total_value DOUBLE,
        minimum_value DOUBLE,
        maximum_value DOUBLE,
        sample_count INT UNSIGNED NOT NULL DEFAULT 0,
        metadata_json JSON,
        UNIQUE KEY uq_daily_summaries_metric_date (metric_name, summary_date)
    ) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_records_metric_start
        ON records(metric_name, start_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_records_import_id
        ON records(import_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_sleep_sessions_night_date
        ON sleep_sessions(night_date)
    """,
    # SQLite's version of this index is DESC; MariaDB accepts DESC in index
    # definitions but only truly stores/uses descending order from 10.8+,
    # below our 10.5 minimum it's silently treated as ascending. InnoDB can
    # still scan an ascending index backward for `ORDER BY imported_at DESC`,
    # so plain ascending gives equivalent behavior across supported versions.
    """
    CREATE INDEX IF NOT EXISTS idx_import_history_imported_at
        ON import_history(imported_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_import_history_file_fingerprint
        ON import_history(file_fingerprint)
    """,
)
