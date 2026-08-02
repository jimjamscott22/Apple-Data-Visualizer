from __future__ import annotations

import pytest

from app.models.imports import DatabaseStatusData
from app.services.import_history_service import ImportHistoryService


@pytest.fixture()
def service() -> ImportHistoryService:
    return ImportHistoryService()


@pytest.fixture()
def database_status() -> DatabaseStatusData:
    return DatabaseStatusData("Connected", "db.local", 3306, "health", "reader")


class TestEmptyDatasets:
    def test_empty_rows_produce_empty_read_models(self, service, database_status):
        summary = service.build_summary(database_status, {}, [], [])

        assert summary.database_status == database_status
        assert summary.statistics.completed_imports == 0
        assert summary.statistics.stored_records == 0
        assert summary.statistics.warning_count == 0
        assert summary.statistics.duplicate_attempts == 0
        assert summary.inventory == ()
        assert summary.history == ()


class TestInventoryTransformation:
    def test_known_metrics_use_friendly_display_names(self, service, database_status):
        summary = service.build_summary(
            database_status,
            {},
            [
                {
                    "metric_name": "step_count",
                    "record_count": 12,
                    "first_recorded_at": "2026-07-01 08:00:00",
                    "last_recorded_at": "2026-07-02 08:00:00",
                    "unit": "count",
                },
                {
                    "metric_name": "heart_rate_variability",
                    "record_count": 3,
                    "first_recorded_at": None,
                    "last_recorded_at": None,
                    "unit": "ms",
                },
            ],
            [],
        )

        assert [record.display_name for record in summary.inventory] == [
            "Step Count",
            "Heart Rate Variability",
        ]
        assert summary.inventory[0].record_count == 12
        assert summary.inventory[1].unit == "ms"

    def test_unknown_metric_falls_back_to_title_cased_words(self, service, database_status):
        summary = service.build_summary(
            database_status,
            {},
            [
                {
                    "metric_name": "cycling_power_output",
                    "record_count": 1,
                    "first_recorded_at": None,
                    "last_recorded_at": None,
                    "unit": "W",
                }
            ],
            [],
        )

        assert summary.inventory[0].display_name == "Cycling Power Output"


class TestHistoryNoteParsing:
    def test_completed_json_notes_expose_source_and_warnings(self, service, database_status):
        summary = service.build_summary(
            database_status,
            {
                "completed_imports": 1,
                "stored_records": 12,
                "warning_count": 2,
                "duplicate_attempts": 1,
            },
            [],
            [
                {
                    "id": 7,
                    "file_name": "export.zip",
                    "file_path": "C:/Health/export.zip",
                    "file_size": 2048,
                    "import_status": "completed",
                    "duplicate_detected": 0,
                    "record_count": 12,
                    "warning_count": 2,
                    "imported_at": "2026-07-02 09:00:00",
                    "notes": '{"source_type":"zip","warnings":["first","second"]}',
                }
            ],
        )

        record = summary.history[0]
        assert summary.statistics.stored_records == 12
        assert record.status == "completed"
        assert record.status_label == "Completed"
        assert record.source_type == "zip"
        assert record.warnings == ("first", "second")
        assert record.detail_message is None

    def test_duplicate_json_notes_expose_original_import_id(self, service, database_status):
        summary = service.build_summary(
            database_status,
            {},
            [],
            [
                {
                    "id": 8,
                    "file_name": "duplicate.xml",
                    "file_path": "C:/Health/duplicate.xml",
                    "file_size": None,
                    "import_status": "duplicate",
                    "duplicate_detected": 1,
                    "record_count": 0,
                    "warning_count": 0,
                    "imported_at": "2026-07-03 09:00:00",
                    "notes": '{"duplicate_of_import_id":7}',
                }
            ],
        )

        record = summary.history[0]
        assert record.status_label == "Duplicate"
        assert record.duplicate_of_import_id == 7
        assert record.detail_message is None

    def test_plain_failure_notes_become_detail_message(self, service, database_status):
        summary = service.build_summary(
            database_status,
            {},
            [],
            [
                {
                    "id": 9,
                    "file_name": "broken.xml",
                    "file_path": "C:/Health/broken.xml",
                    "file_size": 10,
                    "import_status": "failed",
                    "duplicate_detected": 0,
                    "record_count": 0,
                    "warning_count": 0,
                    "imported_at": "2026-07-04 09:00:00",
                    "notes": "Could not parse export.xml",
                }
            ],
        )

        record = summary.history[0]
        assert record.status_label == "Failed"
        assert record.detail_message == "Could not parse export.xml"

    def test_malformed_json_notes_become_detail_message(self, service, database_status):
        summary = service.build_summary(
            database_status,
            {},
            [],
            [
                {
                    "id": 10,
                    "file_name": "legacy.xml",
                    "file_path": "C:/Health/legacy.xml",
                    "file_size": 10,
                    "import_status": "failed",
                    "duplicate_detected": 0,
                    "record_count": 0,
                    "warning_count": 0,
                    "imported_at": "2026-07-05 09:00:00",
                    "notes": '{"warning":',
                }
            ],
        )

        assert summary.history[0].detail_message == '{"warning":'

    def test_non_list_warnings_are_ignored(self, service, database_status):
        summary = service.build_summary(
            database_status,
            {},
            [],
            [
                {
                    "id": 11,
                    "file_name": "odd.xml",
                    "file_path": "C:/Health/odd.xml",
                    "file_size": 10,
                    "import_status": "completed",
                    "duplicate_detected": 0,
                    "record_count": 1,
                    "warning_count": 1,
                    "imported_at": "2026-07-06 09:00:00",
                    "notes": '{"warnings":"not a list"}',
                }
            ],
        )

        assert summary.history[0].warnings == ()

    def test_unknown_status_uses_safe_title_cased_label(self, service, database_status):
        summary = service.build_summary(
            database_status,
            {},
            [],
            [
                {
                    "id": 12,
                    "file_name": "future.xml",
                    "file_path": "C:/Health/future.xml",
                    "file_size": 10,
                    "import_status": "awaiting_review",
                    "duplicate_detected": 0,
                    "record_count": 1,
                    "warning_count": 0,
                    "imported_at": "2026-07-07 09:00:00",
                    "notes": None,
                }
            ],
        )

        assert summary.history[0].status_label == "Awaiting Review"
