from __future__ import annotations

import os
import re

import pytest

from app.database.schema import MARIADB_SCHEMA_STATEMENTS

_EXPECTED_TABLES = ("import_history", "records", "sleep_sessions", "daily_summaries")


def _table_created_by(statement: str) -> str | None:
    match = re.search(r"CREATE TABLE IF NOT EXISTS (\w+)", statement)
    return match.group(1) if match else None


def _tables_referenced_by_foreign_key(statement: str) -> list[str]:
    return re.findall(r"REFERENCES (\w+)\(", statement)


class TestSchemaStructure:
    def test_creates_all_expected_tables_exactly_once(self):
        created_tables = [
            table
            for statement in MARIADB_SCHEMA_STATEMENTS
            if (table := _table_created_by(statement)) is not None
        ]
        assert sorted(created_tables) == sorted(_EXPECTED_TABLES)

    def test_referenced_tables_are_created_before_their_dependents(self):
        created_so_far: set[str] = set()
        for statement in MARIADB_SCHEMA_STATEMENTS:
            for referenced_table in _tables_referenced_by_foreign_key(statement):
                assert referenced_table in created_so_far, (
                    f"{referenced_table} must be created before a statement "
                    "references it via FOREIGN KEY"
                )
            created_table = _table_created_by(statement)
            if created_table is not None:
                created_so_far.add(created_table)

    def test_every_statement_is_idempotent(self):
        for statement in MARIADB_SCHEMA_STATEMENTS:
            assert "IF NOT EXISTS" in statement, (
                f"statement should be safe to re-run: {statement.strip()[:80]}"
            )

    def test_daily_summaries_keeps_unique_metric_and_date_constraint(self):
        daily_summaries_ddl = next(
            statement
            for statement in MARIADB_SCHEMA_STATEMENTS
            if _table_created_by(statement) == "daily_summaries"
        )
        assert "UNIQUE KEY" in daily_summaries_ddl
        assert "(metric_name, summary_date)" in daily_summaries_ddl

    def test_import_history_notes_column_is_plain_text_not_json(self):
        import_history_ddl = next(
            statement
            for statement in MARIADB_SCHEMA_STATEMENTS
            if _table_created_by(statement) == "import_history"
        )
        assert "notes TEXT" in import_history_ddl


@pytest.fixture()
def _live_mariadb_connection():
    pymysql = pytest.importorskip("pymysql")

    host = os.environ.get("APPLE_DV_TEST_DB_HOST", "127.0.0.1")
    port = int(os.environ.get("APPLE_DV_TEST_DB_PORT", "3306"))
    user = os.environ.get("APPLE_DV_TEST_DB_USER", "root")
    password = os.environ.get("APPLE_DV_TEST_DB_PASSWORD", "")
    database_name = "apple_dv_schema_test"

    try:
        admin_connection = pymysql.connect(
            host=host, port=port, user=user, password=password
        )
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"no local MariaDB/MySQL server available for a live schema check: {exc}")

    # Note: pymysql.Connection.__exit__ closes the connection (it is not a
    # plain commit/rollback context manager), so this connection is used
    # directly rather than via `with` and closed exactly once at the end.
    with admin_connection.cursor() as cursor:
        cursor.execute(f"DROP DATABASE IF EXISTS {database_name}")
        cursor.execute(
            f"CREATE DATABASE {database_name} "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
    admin_connection.commit()

    connection = pymysql.connect(
        host=host, port=port, user=user, password=password, database=database_name
    )
    try:
        yield connection
    finally:
        connection.close()
        with admin_connection.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS {database_name}")
        admin_connection.commit()
        admin_connection.close()


class TestSchemaAgainstLiveMariaDB:
    def test_schema_applies_cleanly_and_is_rerunnable(self, _live_mariadb_connection):
        connection = _live_mariadb_connection
        with connection.cursor() as cursor:
            for statement in MARIADB_SCHEMA_STATEMENTS:
                cursor.execute(statement)
        connection.commit()

        with connection.cursor() as cursor:
            for statement in MARIADB_SCHEMA_STATEMENTS:
                cursor.execute(statement)
        connection.commit()

        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = {row[0] for row in cursor.fetchall()}

        assert set(_EXPECTED_TABLES) <= tables
