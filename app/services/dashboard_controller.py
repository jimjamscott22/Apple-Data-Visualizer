from __future__ import annotations

from app.database.manager import DatabaseManager
from app.models.dashboard import ImportStatusSummary, MetricCardData, OverviewData


class DashboardController:
    def __init__(self, database_manager: DatabaseManager) -> None:
        self.database_manager = database_manager

    def load_overview(self) -> OverviewData:
        snapshot = self.database_manager.get_overview_snapshot()
        if not snapshot or snapshot["imported_record_count"] == 0:
            return OverviewData(
                metrics=[
                    MetricCardData("Avg sleep this week", "--", "Import sleep records to compute it"),
                    MetricCardData("Last night sleep", "--", "Nightly sessions will appear here"),
                    MetricCardData("Avg daily steps", "--", "Step imports feed this card"),
                    MetricCardData("Latest resting HR", "--", "Resting heart rate will show here"),
                ],
                import_status=ImportStatusSummary(
                    title="No imports yet",
                    detail="Use the import action to select an Apple Health export.xml file or export zip.",
                ),
            )

        latest_status = snapshot["latest_import_status"] or "Unknown"
        latest_imported_at = snapshot["latest_imported_at"] or "Unknown"
        return OverviewData(
            metrics=[
                MetricCardData("Imported records", str(snapshot["imported_record_count"]), "Normalized rows stored in SQLite"),
                MetricCardData("Sleep sessions", str(snapshot["sleep_session_count"]), "Derived nightly summaries"),
                MetricCardData("Avg daily steps", "--", "Daily summary generation lands next"),
                MetricCardData("Latest resting HR", "--", "Heart metrics land in the next pass"),
            ],
            import_status=ImportStatusSummary(
                title=f"Latest import: {latest_status}",
                detail=f"Most recent import recorded at {latest_imported_at}.",
            ),
        )
