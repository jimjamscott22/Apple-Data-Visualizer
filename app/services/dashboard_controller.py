from __future__ import annotations

from datetime import datetime

from app.database.manager import DatabaseManager
from app.models.dashboard import ImportStatusSummary, MetricCardData, OverviewData
from app.models.hrv import HRVSummaryData
from app.services.hrv_analysis_service import HRVAnalysisService


class DashboardController:
    def __init__(self, database_manager: DatabaseManager, hrv_analysis_service: HRVAnalysisService) -> None:
        self.database_manager = database_manager
        self.hrv_analysis_service = hrv_analysis_service

    def load_overview(self) -> OverviewData:
        snapshot = self.database_manager.get_overview_snapshot()
        if not snapshot or snapshot["imported_record_count"] == 0:
            return OverviewData(
                metrics=[
                    MetricCardData("Avg sleep this week", "--", "Import sleep records to compute it"),
                    MetricCardData("Last night sleep", "--", "Nightly sessions will appear here"),
                    MetricCardData("Avg daily steps", "--", "Step imports feed this card"),
                    MetricCardData("Latest resting HR", "--", "Resting heart rate will show here"),
                    MetricCardData("Latest HRV (SDNN)", "--", "Heart rate variability will show here"),
                ],
                import_status=ImportStatusSummary(
                    title="No imports yet",
                    detail="Use the import action to select an Apple Health export.xml file or export zip.",
                ),
            )

        latest_status = snapshot["latest_import_status"] or "Unknown"
        latest_imported_at = snapshot["latest_imported_at"] or "Unknown"
        average_sleep_this_week = self.database_manager.get_average_sleep_this_week()
        last_sleep_session = self.database_manager.get_last_sleep_session()
        average_daily_steps = self.database_manager.get_average_daily_steps()
        latest_resting_heart_rate = self.database_manager.get_latest_resting_heart_rate()

        return OverviewData(
            metrics=[
                MetricCardData(
                    "Avg sleep this week",
                    self._format_hours(average_sleep_this_week),
                    (
                        f"Based on the latest {min(snapshot['sleep_session_count'], 7)} nights."
                        if average_sleep_this_week is not None
                        else "Nightly sleep sessions will appear here after sleep imports."
                    ),
                ),
                MetricCardData(
                    "Last night sleep",
                    self._format_hours(
                        None if last_sleep_session is None else last_sleep_session["total_sleep_hours"]
                    ),
                    (
                        self._format_last_sleep_detail(last_sleep_session)
                        if last_sleep_session is not None
                        else "The latest derived sleep session will appear here."
                    ),
                ),
                MetricCardData(
                    "Avg daily steps",
                    self._format_steps(average_daily_steps),
                    (
                        "Average from the latest 7 daily summaries."
                        if average_daily_steps is not None
                        else "Step imports feed this card."
                    ),
                ),
                MetricCardData(
                    "Latest resting HR",
                    self._format_resting_hr(latest_resting_heart_rate),
                    (
                        self._format_resting_hr_detail(latest_resting_heart_rate)
                        if latest_resting_heart_rate is not None
                        else "Resting heart rate will show here once imported."
                    ),
                ),
                MetricCardData(
                    "Latest HRV (SDNN)",
                    self._format_hrv(self.database_manager.get_hrv_records(days=1)),
                    "Most recent heart rate variability sample. See Heart page for full analysis.",
                ),
            ],
            import_status=ImportStatusSummary(
                title=f"Latest import: {latest_status}",
                detail=f"Most recent import recorded at {latest_imported_at}.",
            ),
        )

    def load_hrv_summary(self) -> HRVSummaryData:
        daily_rows = self.database_manager.get_hrv_daily_summaries(days=90)
        raw_rows = self.database_manager.get_hrv_records(days=90)
        return self.hrv_analysis_service.compute_summary(daily_rows, raw_rows)

    def _format_hours(self, value: float | None) -> str:
        if value is None:
            return "--"
        total_minutes = int(round(value * 60))
        hours, minutes = divmod(total_minutes, 60)
        return f"{hours}h {minutes:02d}m"

    def _format_steps(self, value: float | None) -> str:
        if value is None:
            return "--"
        return f"{int(round(value)):,}"

    def _format_resting_hr(self, row) -> str:
        if row is None or row["value"] is None:
            return "--"
        return f"{int(round(row['value']))} {row['unit'] or 'bpm'}"

    def _format_resting_hr_detail(self, row) -> str:
        if row is None:
            return "Resting heart rate will show here once imported."
        recorded_at = datetime.fromisoformat(row["start_at"]).strftime("%Y-%m-%d %H:%M")
        return f"Latest resting-heart-rate sample recorded {recorded_at}."

    def _format_hrv(self, rows: list) -> str:
        if not rows:
            return "--"
        latest = rows[-1]
        value = latest["value"]
        if value is None:
            return "--"
        unit = latest["unit"] or "ms"
        return f"{value:.0f} {unit}"

    def _format_last_sleep_detail(self, row) -> str:
        if row is None:
            return "The latest derived sleep session will appear here."
        detail = f"Night of {row['night_date']}"
        if row["sleep_efficiency"] is not None:
            detail += f" with {row['sleep_efficiency']:.0f}% efficiency."
        else:
            detail += "."
        return detail
