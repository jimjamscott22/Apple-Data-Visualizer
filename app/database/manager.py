from __future__ import annotations

import json
from datetime import date, datetime, timedelta

import pymysql
import pymysql.cursors
from pymysql.connections import Connection
from pymysql.constants import FIELD_TYPE
from pymysql.converters import conversions as _DEFAULT_CONVERSIONS
from pymysql.converters import through as _passthrough

from app.database.config import DatabaseSettings
from app.database.errors import DatabaseConnectionError
from app.database.schema import MARIADB_SCHEMA_STATEMENTS

# The rest of the app (parser output, services, UI) treats start_at/end_at/
# bedtime_at/wake_at/night_date/summary_date as plain strings, matching the
# original SQLite TEXT columns. PyMySQL's default converters would turn
# DATETIME/DATE columns into Python datetime/date objects on read, which
# would break every one of those callers. Passing the raw MariaDB string
# straight through on read keeps that contract unchanged while still
# getting native DATETIME/DATE columns for storage and indexing.
_STRING_TEMPORAL_CONVERSIONS = {
    **_DEFAULT_CONVERSIONS,
    FIELD_TYPE.DATETIME: _passthrough,
    FIELD_TYPE.DATE: _passthrough,
    FIELD_TYPE.TIMESTAMP: _passthrough,
    FIELD_TYPE.NEWDATE: _passthrough,
}


def _to_mariadb_datetime(value: str | None) -> str | None:
    """Normalize a parser-produced ISO 8601 timestamp for a DATETIME column.

    The parser emits timestamps like `2026-07-01T08:00:00-07:00`. MariaDB's
    DATETIME type accepts neither the `T` separator nor a UTC offset, and
    has no timezone-aware storage, so this parses the string and re-formats
    it as a naive `YYYY-MM-DD HH:MM:SS` value, preserving the same
    wall-clock numbers the string already carried.
    """
    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is not None:
        parsed = parsed.replace(tzinfo=None)
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


class DatabaseManager:
    def __init__(self, settings: DatabaseSettings) -> None:
        self.settings = settings

    def initialize(self) -> None:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                for statement in MARIADB_SCHEMA_STATEMENTS:
                    cursor.execute(statement)
            connection.commit()

    def connect(self) -> Connection:
        try:
            return pymysql.connect(
                host=self.settings.host,
                port=self.settings.port,
                user=self.settings.user,
                password=self.settings.password,
                database=self.settings.database,
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False,
                conv=_STRING_TEMPORAL_CONVERSIONS,
            )
        except pymysql.err.Error as exc:
            raise DatabaseConnectionError(
                "Could not connect to the MariaDB server at "
                f"{self.settings.host}:{self.settings.port} as "
                f"'{self.settings.user}': {exc}"
            ) from exc

    def find_completed_import_by_fingerprint(self, fingerprint: str) -> dict | None:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, file_name, imported_at, record_count
                    FROM import_history
                    WHERE file_fingerprint = %s
                      AND import_status = 'completed'
                      AND duplicate_detected = 0
                    ORDER BY imported_at DESC, id DESC
                    LIMIT 1
                    """,
                    (fingerprint,),
                )
                return cursor.fetchone()

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
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO import_history (
                        file_path,
                        file_name,
                        file_size,
                        file_fingerprint,
                        import_status,
                        duplicate_detected,
                        notes
                    ) VALUES (%s, %s, %s, %s, 'duplicate', 1, %s)
                    """,
                    (
                        file_path,
                        file_name,
                        file_size,
                        file_fingerprint,
                        json.dumps({"duplicate_of_import_id": duplicate_of_id}),
                    ),
                )
                import_id = int(cursor.lastrowid)
            connection.commit()
            return import_id

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
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO import_history (
                        file_path,
                        file_name,
                        file_size,
                        file_fingerprint,
                        import_status,
                        notes
                    ) VALUES (%s, %s, %s, %s, 'failed', %s)
                    """,
                    (file_path, file_name, file_size, file_fingerprint, notes),
                )
                import_id = int(cursor.lastrowid)
            connection.commit()
            return import_id

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
            with connection.cursor() as cursor:
                cursor.execute(
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
                    ) VALUES (%s, %s, %s, %s, 'completed', %s, %s, %s)
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
                    cursor.executemany(
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
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        [
                            (
                                import_id,
                                record["metric_name"],
                                record["source_type"],
                                record.get("source_name"),
                                _to_mariadb_datetime(record["start_at"]),
                                _to_mariadb_datetime(record["end_at"]),
                                record.get("value"),
                                record.get("unit"),
                                json.dumps(record.get("metadata", {})),
                            )
                            for record in records
                        ],
                    )
                    self._refresh_daily_summaries(connection, records)

            connection.commit()
            return import_id

    def begin_import(
        self,
        connection: Connection,
        *,
        file_path: str,
        file_name: str,
        file_size: int,
        file_fingerprint: str,
        source_type: str,
    ) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO import_history (
                    file_path,
                    file_name,
                    file_size,
                    file_fingerprint,
                    import_status,
                    notes
                ) VALUES (%s, %s, %s, %s, 'in_progress', %s)
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
        connection: Connection,
        *,
        import_id: int,
        records: list[dict],
    ) -> None:
        if not records:
            return

        with connection.cursor() as cursor:
            cursor.executemany(
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
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    (
                        import_id,
                        record["metric_name"],
                        record["source_type"],
                        record.get("source_name"),
                        _to_mariadb_datetime(record["start_at"]),
                        _to_mariadb_datetime(record["end_at"]),
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
        connection: Connection,
        *,
        import_id: int,
        record_count: int,
        warnings: list[str],
        source_type: str,
    ) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE import_history
                SET import_status = 'completed',
                    record_count = %s,
                    warning_count = %s,
                    notes = %s
                WHERE id = %s
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
        connection.commit()

    def list_sleep_records(self) -> list[dict]:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT start_at, end_at, value, unit, metadata_json
                    FROM records
                    WHERE metric_name = 'sleep_analysis'
                    ORDER BY start_at ASC
                    """
                )
                rows = cursor.fetchall()

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
            with connection.cursor() as cursor:
                if night_dates:
                    placeholders = ", ".join("%s" for _ in night_dates)
                    cursor.execute(
                        f"DELETE FROM sleep_sessions WHERE night_date IN ({placeholders})",
                        tuple(sorted(night_dates)),
                    )

                if sessions:
                    cursor.executemany(
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
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        [
                            (
                                import_id,
                                session["night_date"],
                                _to_mariadb_datetime(session.get("bedtime_at")),
                                _to_mariadb_datetime(session.get("wake_at")),
                                session.get("total_sleep_hours"),
                                session.get("time_in_bed_hours"),
                                session.get("sleep_efficiency"),
                                session.get("consistency_score"),
                                json.dumps(session.get("summary", {})),
                            )
                            for session in sessions
                        ],
                    )
            connection.commit()

    def get_overview_snapshot(self) -> dict | None:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
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
                )
                return cursor.fetchone()

    def get_average_sleep_this_week(self) -> float | None:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT AVG(total_sleep_hours) AS average_sleep_hours
                    FROM (
                        SELECT total_sleep_hours
                        FROM sleep_sessions
                        ORDER BY night_date DESC
                        LIMIT 7
                    ) AS recent_nights
                    """
                )
                row = cursor.fetchone()
        return None if row is None else row["average_sleep_hours"]

    def get_last_sleep_session(self) -> dict | None:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT night_date, total_sleep_hours, bedtime_at, wake_at, sleep_efficiency
                    FROM sleep_sessions
                    ORDER BY night_date DESC
                    LIMIT 1
                    """
                )
                return cursor.fetchone()

    def get_recent_sleep_sessions(self, days: int) -> list[dict]:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT night_date,
                           bedtime_at,
                           wake_at,
                           total_sleep_hours,
                           time_in_bed_hours,
                           sleep_efficiency,
                           consistency_score
                    FROM sleep_sessions
                    ORDER BY night_date DESC
                    LIMIT %s
                    """,
                    (days,),
                )
                return cursor.fetchall()

    def get_average_daily_steps(self, days: int = 7) -> float | None:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT AVG(total_value) AS average_steps
                    FROM (
                        SELECT total_value
                        FROM daily_summaries
                        WHERE metric_name = 'step_count'
                        ORDER BY summary_date DESC
                        LIMIT %s
                    ) AS recent_days
                    """,
                    (days,),
                )
                row = cursor.fetchone()
        return None if row is None else row["average_steps"]

    def get_latest_resting_heart_rate(self) -> dict | None:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT start_at, value, unit
                    FROM records
                    WHERE metric_name = 'resting_heart_rate'
                      AND value IS NOT NULL
                    ORDER BY start_at DESC
                    LIMIT 1
                    """
                )
                return cursor.fetchone()

    def get_hrv_records(self, days: int = 90) -> list[dict]:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT start_at, value, unit
                    FROM records
                    WHERE metric_name = 'heart_rate_variability'
                      AND value IS NOT NULL
                      AND start_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                    ORDER BY start_at ASC
                    """,
                    (days,),
                )
                return cursor.fetchall()

    def get_daily_metric_summaries(self, metric_name: str, days: int) -> list[dict]:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT summary_date, average_value, total_value, minimum_value,
                           maximum_value, sample_count
                    FROM daily_summaries
                    WHERE metric_name = %s
                      AND summary_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                    ORDER BY summary_date ASC
                    """,
                    (metric_name, days),
                )
                return cursor.fetchall()

    def get_hrv_daily_summaries(self, days: int = 90) -> list[dict]:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT summary_date, average_value, minimum_value, maximum_value, sample_count
                    FROM daily_summaries
                    WHERE metric_name = 'heart_rate_variability'
                      AND summary_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                    ORDER BY summary_date ASC
                    """,
                    (days,),
                )
                return cursor.fetchall()

    def list_recent_imports(self, limit: int = 10) -> list[dict]:
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT file_name, import_status, record_count, warning_count, imported_at
                    FROM import_history
                    ORDER BY imported_at DESC, id DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                return cursor.fetchall()

    def _refresh_daily_summaries(
        self,
        connection: Connection,
        records: list[dict],
    ) -> None:
        impacted_keys = {
            (record["metric_name"], record["start_at"][:10])
            for record in records
            if record["metric_name"] != "sleep_analysis" and record.get("value") is not None
        }
        if not impacted_keys:
            return

        with connection.cursor() as cursor:
            for metric_name, summary_date in impacted_keys:
                range_start = f"{summary_date} 00:00:00"
                range_end_date = date.fromisoformat(summary_date) + timedelta(days=1)
                range_end = f"{range_end_date.isoformat()} 00:00:00"
                cursor.execute(
                    """
                    SELECT
                        AVG(value) AS average_value,
                        SUM(value) AS total_value,
                        MIN(value) AS minimum_value,
                        MAX(value) AS maximum_value,
                        COUNT(*) AS sample_count
                    FROM records
                    WHERE metric_name = %s
                      AND start_at >= %s
                      AND start_at < %s
                      AND value IS NOT NULL
                    """,
                    (metric_name, range_start, range_end),
                )
                aggregate_row = cursor.fetchone()

                cursor.execute(
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
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        average_value = VALUES(average_value),
                        total_value = VALUES(total_value),
                        minimum_value = VALUES(minimum_value),
                        maximum_value = VALUES(maximum_value),
                        sample_count = VALUES(sample_count),
                        metadata_json = VALUES(metadata_json)
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
