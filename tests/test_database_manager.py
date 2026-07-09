from __future__ import annotations

import os

import pytest

from app.database.config import DatabaseSettings
from app.database.errors import DatabaseConnectionError
from app.database.manager import DatabaseManager

pymysql = pytest.importorskip("pymysql")


def _admin_connection_or_skip():
    host = os.environ.get("APPLE_DV_TEST_DB_HOST", "127.0.0.1")
    port = int(os.environ.get("APPLE_DV_TEST_DB_PORT", "3306"))
    user = os.environ.get("APPLE_DV_TEST_DB_USER", "root")
    password = os.environ.get("APPLE_DV_TEST_DB_PASSWORD", "")

    try:
        return pymysql.connect(host=host, port=port, user=user, password=password)
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"no local MariaDB/MySQL server available for a live manager test: {exc}")


@pytest.fixture()
def db_manager():
    admin_connection = _admin_connection_or_skip()

    host = os.environ.get("APPLE_DV_TEST_DB_HOST", "127.0.0.1")
    port = int(os.environ.get("APPLE_DV_TEST_DB_PORT", "3306"))
    user = os.environ.get("APPLE_DV_TEST_DB_USER", "root")
    password = os.environ.get("APPLE_DV_TEST_DB_PASSWORD", "")
    database_name = "apple_dv_manager_test"

    with admin_connection.cursor() as cursor:
        cursor.execute(f"DROP DATABASE IF EXISTS {database_name}")
        cursor.execute(
            f"CREATE DATABASE {database_name} "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
    admin_connection.commit()

    settings = DatabaseSettings(
        host=host, port=port, database=database_name, user=user, password=password
    )
    manager = DatabaseManager(settings)
    manager.initialize()

    try:
        yield manager
    finally:
        with admin_connection.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS {database_name}")
        admin_connection.commit()
        admin_connection.close()


def _record(
    metric_name: str,
    start_at: str,
    value: float | None = 1.0,
    *,
    source_type: str = "HKQuantityTypeIdentifierStepCount",
    end_at: str | None = None,
    unit: str | None = "count",
) -> dict:
    return {
        "metric_name": metric_name,
        "source_type": source_type,
        "source_name": "Test Source",
        "start_at": start_at,
        "end_at": end_at or start_at,
        "value": value,
        "unit": unit,
        "metadata": {},
    }


class TestInitialize:
    def test_creates_expected_tables(self, db_manager):
        with db_manager.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                tables = {row["Tables_in_apple_dv_manager_test"] for row in cursor.fetchall()}
        assert tables == {"import_history", "records", "sleep_sessions", "daily_summaries"}

    def test_is_idempotent(self, db_manager):
        db_manager.initialize()
        db_manager.initialize()


class TestConnect:
    def test_raises_database_connection_error_for_bad_credentials(self, db_manager):
        bad_settings = DatabaseSettings(
            host=db_manager.settings.host,
            port=db_manager.settings.port,
            database=db_manager.settings.database,
            user="definitely-not-a-real-user",
            password="wrong-password",
        )
        bad_manager = DatabaseManager(bad_settings)

        with pytest.raises(DatabaseConnectionError):
            bad_manager.connect()


class TestPersistImportAndDuplicateDetection:
    def test_persist_import_then_finds_completed_import_by_fingerprint(self, db_manager):
        import_id = db_manager.persist_import(
            file_path="/tmp/export.xml",
            file_name="export.xml",
            file_size=1234,
            file_fingerprint="fingerprint-a",
            source_type="xml",
            records=[_record("step_count", "2026-07-01 08:00:00")],
            warnings=[],
        )

        found = db_manager.find_completed_import_by_fingerprint("fingerprint-a")
        assert found is not None
        assert found["id"] == import_id
        assert found["record_count"] == 1

    def test_duplicate_import_is_logged_without_new_records(self, db_manager):
        import_id = db_manager.persist_import(
            file_path="/tmp/export.xml",
            file_name="export.xml",
            file_size=1234,
            file_fingerprint="fingerprint-b",
            source_type="xml",
            records=[_record("step_count", "2026-07-01 08:00:00")],
            warnings=[],
        )

        duplicate_id = db_manager.log_duplicate_import_attempt(
            file_path="/tmp/export-copy.xml",
            file_name="export-copy.xml",
            file_size=1234,
            file_fingerprint="fingerprint-b",
            duplicate_of_id=import_id,
        )

        assert duplicate_id != import_id
        recent = db_manager.list_recent_imports(limit=10)
        statuses = {row["file_name"]: row["import_status"] for row in recent}
        assert statuses["export.xml"] == "completed"
        assert statuses["export-copy.xml"] == "duplicate"


class TestBeginAppendCompleteImportTransaction:
    def test_successful_import_commits_records_and_status(self, db_manager):
        with db_manager.connect() as connection:
            import_id = db_manager.begin_import(
                connection,
                file_path="/tmp/export.xml",
                file_name="export.xml",
                file_size=1,
                file_fingerprint="fingerprint-c",
                source_type="xml",
            )
            db_manager.append_import_records(
                connection,
                import_id=import_id,
                records=[_record("step_count", "2026-07-01 08:00:00", 100.0)],
            )
            db_manager.complete_import(
                connection,
                import_id=import_id,
                record_count=1,
                warnings=[],
                source_type="xml",
            )

        recent = db_manager.list_recent_imports(limit=10)
        completed = next(row for row in recent if row["file_name"] == "export.xml")
        assert completed["import_status"] == "completed"
        assert completed["record_count"] == 1

    def test_failure_before_complete_rolls_back_the_whole_import(self, db_manager):
        """Mirrors the SQLite atomic-import behavior: ImportService wraps
        begin_import/append_import_records/complete_import in a single
        `with database_manager.connect() as connection:` block. If the
        parser raises mid-import, the connection is closed without a
        commit, and the whole in-progress import (including the
        begin_import row) must disappear rather than leaving an orphan
        'in_progress' import_history row.
        """
        with pytest.raises(RuntimeError):
            with db_manager.connect() as connection:
                db_manager.begin_import(
                    connection,
                    file_path="/tmp/export.xml",
                    file_name="export-that-fails.xml",
                    file_size=1,
                    file_fingerprint="fingerprint-d",
                    source_type="xml",
                )
                db_manager.append_import_records(
                    connection,
                    import_id=1,
                    records=[_record("step_count", "2026-07-01 08:00:00")],
                )
                raise RuntimeError("simulated parser failure mid-import")

        recent = db_manager.list_recent_imports(limit=10)
        assert all(row["file_name"] != "export-that-fails.xml" for row in recent)


class TestSleepSessionsAndDashboardReads:
    def test_replace_sleep_sessions_and_overview_snapshot(self, db_manager):
        import_id = db_manager.persist_import(
            file_path="/tmp/export.xml",
            file_name="export.xml",
            file_size=1,
            file_fingerprint="fingerprint-e",
            source_type="xml",
            records=[_record("resting_heart_rate", "2026-07-01 06:00:00", 52.0, unit="bpm")],
            warnings=[],
        )

        db_manager.replace_sleep_sessions(
            import_id=import_id,
            night_dates={"2026-07-01"},
            sessions=[
                {
                    "night_date": "2026-07-01",
                    "bedtime_at": "2026-06-30 23:00:00",
                    "wake_at": "2026-07-01 06:30:00",
                    "total_sleep_hours": 7.5,
                    "time_in_bed_hours": 7.5,
                    "sleep_efficiency": 0.95,
                    "consistency_score": 0.8,
                    "summary": {"source": "test"},
                }
            ],
        )

        snapshot = db_manager.get_overview_snapshot()
        assert snapshot["sleep_session_count"] == 1
        assert snapshot["imported_record_count"] == 1
        assert snapshot["latest_import_status"] == "completed"

        average_sleep = db_manager.get_average_sleep_this_week()
        assert average_sleep == pytest.approx(7.5)

        last_session = db_manager.get_last_sleep_session()
        assert last_session["night_date"] == "2026-07-01"

        latest_rhr = db_manager.get_latest_resting_heart_rate()
        assert latest_rhr["value"] == pytest.approx(52.0)

    def test_replace_sleep_sessions_is_scoped_to_given_night_dates(self, db_manager):
        import_id = db_manager.persist_import(
            file_path="/tmp/export.xml",
            file_name="export.xml",
            file_size=1,
            file_fingerprint="fingerprint-g",
            source_type="xml",
            records=[],
            warnings=[],
        )

        db_manager.replace_sleep_sessions(
            import_id=import_id,
            night_dates=set(),
            sessions=[
                {
                    "night_date": "2026-07-01",
                    "total_sleep_hours": 6.0,
                    "summary": {},
                },
                {
                    "night_date": "2026-07-02",
                    "total_sleep_hours": 8.0,
                    "summary": {},
                },
            ],
        )
        db_manager.replace_sleep_sessions(
            import_id=import_id,
            night_dates={"2026-07-02"},
            sessions=[
                {
                    "night_date": "2026-07-02",
                    "total_sleep_hours": 9.0,
                    "summary": {},
                }
            ],
        )

        sessions = {
            row["night_date"]: row["total_sleep_hours"]
            for row in db_manager.get_recent_sleep_sessions(days=10)
        }
        assert sessions["2026-07-01"] == pytest.approx(6.0)
        assert sessions["2026-07-02"] == pytest.approx(9.0)


class TestParserTimestampFormatRoundTrip:
    """HealthDataParser emits ISO 8601 timestamps with a `T` separator and a
    UTC offset, e.g. `2026-07-01T08:00:00-07:00` (see
    app/parser/health_data_parser.py DATE_FORMAT). MariaDB's DATETIME type
    accepts neither, so DatabaseManager must normalize on write and every
    read must still hand callers back a plain string (not a driver-native
    datetime/date object), matching the contract every other layer of the
    app (models, services, UI) already relies on.
    """

    def test_offset_timestamps_are_stored_and_read_back_as_plain_strings(self, db_manager):
        db_manager.persist_import(
            file_path="/tmp/export.xml",
            file_name="export.xml",
            file_size=1,
            file_fingerprint="fingerprint-h",
            source_type="xml",
            records=[
                _record(
                    "resting_heart_rate",
                    "2026-07-01T08:00:00-07:00",
                    60.0,
                    end_at="2026-07-01T08:00:00-07:00",
                    unit="bpm",
                )
            ],
            warnings=[],
        )

        latest_rhr = db_manager.get_latest_resting_heart_rate()
        assert isinstance(latest_rhr["start_at"], str)
        assert latest_rhr["start_at"] == "2026-07-01 08:00:00"

    def test_offset_sleep_session_timestamps_round_trip(self, db_manager):
        import_id = db_manager.persist_import(
            file_path="/tmp/export.xml",
            file_name="export.xml",
            file_size=1,
            file_fingerprint="fingerprint-i",
            source_type="xml",
            records=[],
            warnings=[],
        )

        db_manager.replace_sleep_sessions(
            import_id=import_id,
            night_dates={"2026-07-01"},
            sessions=[
                {
                    "night_date": "2026-07-01",
                    "bedtime_at": "2026-06-30T23:00:00-07:00",
                    "wake_at": "2026-07-01T06:30:00-07:00",
                    "total_sleep_hours": 7.5,
                    "summary": {},
                }
            ],
        )

        last_session = db_manager.get_last_sleep_session()
        assert isinstance(last_session["bedtime_at"], str)
        assert isinstance(last_session["wake_at"], str)
        assert last_session["bedtime_at"] == "2026-06-30 23:00:00"
        assert last_session["wake_at"] == "2026-07-01 06:30:00"


class TestDailySummariesUpsert:
    def test_repeated_records_for_same_day_update_rather_than_duplicate(self, db_manager):
        with db_manager.connect() as connection:
            import_id = db_manager.begin_import(
                connection,
                file_path="/tmp/export.xml",
                file_name="export.xml",
                file_size=1,
                file_fingerprint="fingerprint-f",
                source_type="xml",
            )
            db_manager.append_import_records(
                connection,
                import_id=import_id,
                records=[_record("step_count", "2026-07-01 08:00:00", 100.0)],
            )
            db_manager.append_import_records(
                connection,
                import_id=import_id,
                records=[_record("step_count", "2026-07-01 20:00:00", 300.0)],
            )
            db_manager.complete_import(
                connection,
                import_id=import_id,
                record_count=2,
                warnings=[],
                source_type="xml",
            )

        summaries = db_manager.get_daily_metric_summaries("step_count", days=30)
        assert len(summaries) == 1
        assert summaries[0]["total_value"] == pytest.approx(400.0)
        assert summaries[0]["sample_count"] == 2

        average_steps = db_manager.get_average_daily_steps(days=7)
        assert average_steps == pytest.approx(400.0)
