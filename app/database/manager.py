from __future__ import annotations

import json
import sqlite3
from pathlib import Path


class DatabaseManager:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(
                """
                PRAGMA foreign_keys = ON;

                CREATE TABLE IF NOT EXISTS import_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_size INTEGER,
                    file_fingerprint TEXT,
                    import_status TEXT NOT NULL,
                    duplicate_detected INTEGER NOT NULL DEFAULT 0,
                    record_count INTEGER NOT NULL DEFAULT 0,
                    warning_count INTEGER NOT NULL DEFAULT 0,
                    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT
                );

                CREATE TABLE IF NOT EXISTS records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    import_id INTEGER,
                    metric_name TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_name TEXT,
                    start_at TEXT NOT NULL,
                    end_at TEXT,
                    value REAL,
                    unit TEXT,
                    metadata_json TEXT,
                    FOREIGN KEY (import_id) REFERENCES import_history(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS sleep_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    import_id INTEGER,
                    night_date TEXT NOT NULL,
                    bedtime_at TEXT,
                    wake_at TEXT,
                    total_sleep_hours REAL,
                    time_in_bed_hours REAL,
                    sleep_efficiency REAL,
                    consistency_score REAL,
                    summary_json TEXT,
                    FOREIGN KEY (import_id) REFERENCES import_history(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS daily_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL,
                    summary_date TEXT NOT NULL,
                    average_value REAL,
                    total_value REAL,
                    minimum_value REAL,
                    maximum_value REAL,
                    sample_count INTEGER NOT NULL DEFAULT 0,
                    metadata_json TEXT,
                    UNIQUE(metric_name, summary_date)
                );

                CREATE INDEX IF NOT EXISTS idx_records_metric_start
                    ON records(metric_name, start_at);

                CREATE INDEX IF NOT EXISTS idx_records_import_id
                    ON records(import_id);

                CREATE INDEX IF NOT EXISTS idx_sleep_sessions_night_date
                    ON sleep_sessions(night_date);

                CREATE INDEX IF NOT EXISTS idx_import_history_imported_at
                    ON import_history(imported_at DESC);

                CREATE INDEX IF NOT EXISTS idx_import_history_file_fingerprint
                    ON import_history(file_fingerprint);
                """
            )

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def find_completed_import_by_fingerprint(self, fingerprint: str) -> sqlite3.Row | None:
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT id, file_name, imported_at, record_count
                FROM import_history
                WHERE file_fingerprint = ?
                  AND import_status = 'completed'
                  AND duplicate_detected = 0
                ORDER BY imported_at DESC, id DESC
                LIMIT 1
                """,
                (fingerprint,),
            ).fetchone()

    def log_duplicate_import_attempt(
        self,
        *,
        file_path: str,
        file_name: str,
        file_size: int,
        file_fingerprint: str,
        duplicate_of_id: int,
    ) -> int:
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO import_history (
                    file_path,
                    file_name,
                    file_size,
                    file_fingerprint,
                    import_status,
                    duplicate_detected,
                    notes
                ) VALUES (?, ?, ?, ?, 'duplicate', 1, ?)
                """,
                (
                    file_path,
                    file_name,
                    file_size,
                    file_fingerprint,
                    json.dumps({"duplicate_of_import_id": duplicate_of_id}),
                ),
            )
            return int(cursor.lastrowid)

    def log_failed_import(
        self,
        *,
        file_path: str,
        file_name: str,
        file_size: int,
        file_fingerprint: str | None,
        notes: str,
    ) -> int:
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO import_history (
                    file_path,
                    file_name,
                    file_size,
                    file_fingerprint,
                    import_status,
                    notes
                ) VALUES (?, ?, ?, ?, 'failed', ?)
                """,
                (file_path, file_name, file_size, file_fingerprint, notes),
            )
            return int(cursor.lastrowid)

    def persist_import(
        self,
        *,
        file_path: str,
        file_name: str,
        file_size: int,
        file_fingerprint: str,
        source_type: str,
        records: list[dict],
        warnings: list[str],
    ) -> int:
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO import_history (
                    file_path,
                    file_name,
                    file_size,
                    file_fingerprint,
                    import_status,
                    record_count,
                    warning_count,
                    notes
                ) VALUES (?, ?, ?, ?, 'completed', ?, ?, ?)
                """,
                (
                    file_path,
                    file_name,
                    file_size,
                    file_fingerprint,
                    len(records),
                    len(warnings),
                    json.dumps(
                        {
                            "source_type": source_type,
                            "warnings": warnings,
                        }
                    ),
                ),
            )
            import_id = int(cursor.lastrowid)

            if records:
                connection.executemany(
                    """
                    INSERT INTO records (
                        import_id,
                        metric_name,
                        source_type,
                        source_name,
                        start_at,
                        end_at,
                        value,
                        unit,
                        metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            import_id,
                            record["metric_name"],
                            record["source_type"],
                            record.get("source_name"),
                            record["start_at"],
                            record["end_at"],
                            record.get("value"),
                            record.get("unit"),
                            json.dumps(record.get("metadata", {})),
                        )
                        for record in records
                    ],
                )
                self._refresh_daily_summaries(connection, records)

            return import_id

    def begin_import(
        self,
        connection: sqlite3.Connection,
        *,
        file_path: str,
        file_name: str,
        file_size: int,
        file_fingerprint: str,
        source_type: str,
    ) -> int:
        cursor = connection.execute(
            """
            INSERT INTO import_history (
                file_path,
                file_name,
                file_size,
                file_fingerprint,
                import_status,
                notes
            ) VALUES (?, ?, ?, ?, 'in_progress', ?)
            """,
            (
                file_path,
                file_name,
                file_size,
                file_fingerprint,
                json.dumps({"source_type": source_type, "warnings": []}),
            ),
        )
        return int(cursor.lastrowid)

    def append_import_records(
        self,
        connection: sqlite3.Connection,
        *,
        import_id: int,
        records: list[dict],
    ) -> None:
        if not records:
            return

        connection.executemany(
            """
            INSERT INTO records (
                import_id,
                metric_name,
                source_type,
                source_name,
                start_at,
                end_at,
                value,
                unit,
                metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    import_id,
                    record["metric_name"],
                    record["source_type"],
                    record.get("source_name"),
                    record["start_at"],
                    record["end_at"],
                    record.get("value"),
                    record.get("unit"),
                    json.dumps(record.get("metadata", {})),
                )
                for record in records
            ],
        )
        self._refresh_daily_summaries(connection, records)

    def complete_import(
        self,
        connection: sqlite3.Connection,
        *,
        import_id: int,
        record_count: int,
        warnings: list[str],
        source_type: str,
    ) -> None:
        connection.execute(
            """
            UPDATE import_history
            SET import_status = 'completed',
                record_count = ?,
                warning_count = ?,
                notes = ?
            WHERE id = ?
            """,
            (
                record_count,
                len(warnings),
                json.dumps(
                    {
                        "source_type": source_type,
                        "warnings": warnings,
                    }
                ),
                import_id,
            ),
        )

    def list_sleep_records(self) -> list[dict]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT start_at, end_at, value, unit, metadata_json
                FROM records
                WHERE metric_name = 'sleep_analysis'
                ORDER BY start_at ASC
                """
            ).fetchall()

        return [
            {
                "metric_name": "sleep_analysis",
                "start_at": row["start_at"],
                "end_at": row["end_at"],
                "value": row["value"],
                "unit": row["unit"],
                "metadata": json.loads(row["metadata_json"] or "{}"),
            }
            for row in rows
        ]

    def replace_sleep_sessions(
        self,
        *,
        import_id: int,
        night_dates: set[str],
        sessions: list[dict],
    ) -> None:
        with self.connect() as connection:
            if night_dates:
                placeholders = ", ".join("?" for _ in night_dates)
                connection.execute(
                    f"DELETE FROM sleep_sessions WHERE night_date IN ({placeholders})",
                    tuple(sorted(night_dates)),
                )

            if sessions:
                connection.executemany(
                    """
                    INSERT INTO sleep_sessions (
                        import_id,
                        night_date,
                        bedtime_at,
                        wake_at,
                        total_sleep_hours,
                        time_in_bed_hours,
                        sleep_efficiency,
                        consistency_score,
                        summary_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            import_id,
                            session["night_date"],
                            session.get("bedtime_at"),
                            session.get("wake_at"),
                            session.get("total_sleep_hours"),
                            session.get("time_in_bed_hours"),
                            session.get("sleep_efficiency"),
                            session.get("consistency_score"),
                            json.dumps(session.get("summary", {})),
                        )
                        for session in sessions
                    ],
                )

    def get_overview_snapshot(self) -> sqlite3.Row | None:
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM records) AS imported_record_count,
                    (SELECT COUNT(*) FROM sleep_sessions) AS sleep_session_count,
                    (
                        SELECT import_status
                        FROM import_history
                        ORDER BY imported_at DESC, id DESC
                        LIMIT 1
                    ) AS latest_import_status,
                    (
                        SELECT imported_at
                        FROM import_history
                        ORDER BY imported_at DESC, id DESC
                        LIMIT 1
                    ) AS latest_imported_at
                """
            ).fetchone()

    def get_average_sleep_this_week(self) -> float | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT AVG(total_sleep_hours) AS average_sleep_hours
                FROM (
                    SELECT total_sleep_hours
                    FROM sleep_sessions
                    ORDER BY night_date DESC
                    LIMIT 7
                )
                """
            ).fetchone()
        return None if row is None else row["average_sleep_hours"]

    def get_last_sleep_session(self) -> sqlite3.Row | None:
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT night_date, total_sleep_hours, bedtime_at, wake_at, sleep_efficiency
                FROM sleep_sessions
                ORDER BY night_date DESC
                LIMIT 1
                """
            ).fetchone()

    def get_average_daily_steps(self, days: int = 7) -> float | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT AVG(total_value) AS average_steps
                FROM (
                    SELECT total_value
                    FROM daily_summaries
                    WHERE metric_name = 'step_count'
                    ORDER BY summary_date DESC
                    LIMIT ?
                )
                """,
                (days,),
            ).fetchone()
        return None if row is None else row["average_steps"]

    def get_latest_resting_heart_rate(self) -> sqlite3.Row | None:
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT start_at, value, unit
                FROM records
                WHERE metric_name = 'resting_heart_rate'
                  AND value IS NOT NULL
                ORDER BY start_at DESC
                LIMIT 1
                """
            ).fetchone()

    def get_hrv_records(self, days: int = 90) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT start_at, value, unit
                FROM records
                WHERE metric_name = 'heart_rate_variability'
                  AND value IS NOT NULL
                  AND start_at >= datetime('now', '-' || ? || ' days')
                ORDER BY start_at ASC
                """,
                (days,),
            ).fetchall()

    def get_hrv_daily_summaries(self, days: int = 90) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT summary_date, average_value, minimum_value, maximum_value, sample_count
                FROM daily_summaries
                WHERE metric_name = 'heart_rate_variability'
                  AND summary_date >= date('now', '-' || ? || ' days')
                ORDER BY summary_date ASC
                """,
                (days,),
            ).fetchall()

    def list_recent_imports(self, limit: int = 10) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT file_name, import_status, record_count, warning_count, imported_at
                FROM import_history
                ORDER BY imported_at DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

    def _refresh_daily_summaries(
        self,
        connection: sqlite3.Connection,
        records: list[dict],
    ) -> None:
        impacted_keys = {
            (record["metric_name"], record["start_at"][:10])
            for record in records
            if record["metric_name"] != "sleep_analysis" and record.get("value") is not None
        }
        for metric_name, summary_date in impacted_keys:
            aggregate_row = connection.execute(
                """
                SELECT
                    AVG(value) AS average_value,
                    SUM(value) AS total_value,
                    MIN(value) AS minimum_value,
                    MAX(value) AS maximum_value,
                    COUNT(*) AS sample_count
                FROM records
                WHERE metric_name = ?
                  AND substr(start_at, 1, 10) = ?
                  AND value IS NOT NULL
                """,
                (metric_name, summary_date),
            ).fetchone()

            connection.execute(
                """
                INSERT INTO daily_summaries (
                    metric_name,
                    summary_date,
                    average_value,
                    total_value,
                    minimum_value,
                    maximum_value,
                    sample_count,
                    metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(metric_name, summary_date) DO UPDATE SET
                    average_value = excluded.average_value,
                    total_value = excluded.total_value,
                    minimum_value = excluded.minimum_value,
                    maximum_value = excluded.maximum_value,
                    sample_count = excluded.sample_count,
                    metadata_json = excluded.metadata_json
                """,
                (
                    metric_name,
                    summary_date,
                    aggregate_row["average_value"],
                    aggregate_row["total_value"],
                    aggregate_row["minimum_value"],
                    aggregate_row["maximum_value"],
                    aggregate_row["sample_count"],
                    json.dumps({"refreshed_from_records": True}),
                ),
            )
