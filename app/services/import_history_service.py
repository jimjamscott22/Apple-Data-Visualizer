from __future__ import annotations

import json
from typing import Any

from app.models.imports import (
    DatabaseStatusData,
    ImportHistoryRecord,
    ImportsSummaryData,
    ImportStatistics,
    MetricInventoryRecord,
)


class ImportHistoryService:
    """Builds safe, typed Imports/Data Manager read models from database rows."""

    METRIC_DISPLAY_NAMES = {
        "sleep_analysis": "Sleep Analysis",
        "step_count": "Step Count",
        "heart_rate": "Heart Rate",
        "resting_heart_rate": "Resting Heart Rate",
        "heart_rate_variability": "Heart Rate Variability",
        "respiratory_rate": "Respiratory Rate",
        "walking_running_distance": "Walking + Running Distance",
    }

    STATUS_LABELS = {
        "completed": "Completed",
        "duplicate": "Duplicate",
        "failed": "Failed",
        "in_progress": "In progress",
    }

    def build_summary(
        self,
        database_status: DatabaseStatusData,
        statistics_row: dict[str, Any],
        inventory_rows: list[dict[str, Any]],
        history_rows: list[dict[str, Any]],
    ) -> ImportsSummaryData:
        """Transform raw read-query rows without exposing private database fields."""
        statistics = ImportStatistics(
            completed_imports=int(statistics_row.get("completed_imports") or 0),
            stored_records=int(statistics_row.get("stored_records") or 0),
            warning_count=int(statistics_row.get("warning_count") or 0),
            duplicate_attempts=int(statistics_row.get("duplicate_attempts") or 0),
        )
        inventory = tuple(self._build_inventory_record(row) for row in inventory_rows)
        history = tuple(self._build_history_record(row) for row in history_rows)
        return ImportsSummaryData(database_status, statistics, inventory, history)

    def _build_inventory_record(self, row: dict[str, Any]) -> MetricInventoryRecord:
        metric_name = str(row["metric_name"])
        return MetricInventoryRecord(
            metric_name=metric_name,
            display_name=self.METRIC_DISPLAY_NAMES.get(
                metric_name, metric_name.replace("_", " ").title()
            ),
            record_count=int(row.get("record_count") or 0),
            first_recorded_at=row.get("first_recorded_at"),
            last_recorded_at=row.get("last_recorded_at"),
            unit=row.get("unit"),
        )

    def _build_history_record(self, row: dict[str, Any]) -> ImportHistoryRecord:
        source_type, warnings, detail_message, duplicate_of_import_id = self._parse_notes(
            row.get("notes")
        )
        status = str(row["import_status"])
        return ImportHistoryRecord(
            id=int(row["id"]),
            file_name=str(row["file_name"]),
            file_path=str(row["file_path"]),
            file_size=row.get("file_size"),
            status=status,
            status_label=self.STATUS_LABELS.get(
                status, status.replace("_", " ").title()
            ),
            record_count=int(row.get("record_count") or 0),
            warning_count=int(row.get("warning_count") or 0),
            imported_at=str(row["imported_at"]),
            source_type=source_type,
            warnings=warnings,
            detail_message=detail_message,
            duplicate_of_import_id=duplicate_of_import_id,
        )

    @staticmethod
    def _parse_notes(
        notes: object,
    ) -> tuple[str | None, tuple[str, ...], str | None, int | None]:
        if notes is None:
            return None, (), None, None

        try:
            parsed_notes = json.loads(notes)
        except (TypeError, json.JSONDecodeError):
            return None, (), notes if isinstance(notes, str) else None, None

        if not isinstance(parsed_notes, dict):
            return None, (), None, None

        source_type = parsed_notes.get("source_type")
        warnings_value = parsed_notes.get("warnings")
        duplicate_of_import_id = parsed_notes.get("duplicate_of_import_id")
        warnings = (
            tuple(str(warning) for warning in warnings_value)
            if isinstance(warnings_value, list)
            else ()
        )
        return (
            source_type if isinstance(source_type, str) else None,
            warnings,
            None,
            duplicate_of_import_id
            if isinstance(duplicate_of_import_id, int) and not isinstance(duplicate_of_import_id, bool)
            else None,
        )
