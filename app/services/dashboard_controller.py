from __future__ import annotations

from datetime import datetime

from app.database.manager import DatabaseManager
from app.models.dashboard import ImportStatusSummary, MetricCardData, OverviewData
from app.models.hrv import HRVSummaryData
from app.models.sleep import SleepNightRecord, SleepSummaryData
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

    def load_sleep_summary(self, days: int = 30) -> SleepSummaryData:
        rows = self.database_manager.get_recent_sleep_sessions(days=days)
        nights = [
            SleepNightRecord(
                night_date=row["night_date"],
                bedtime_at=row["bedtime_at"],
                wake_at=row["wake_at"],
                total_sleep_hours=row["total_sleep_hours"],
                time_in_bed_hours=row["time_in_bed_hours"],
                sleep_efficiency=row["sleep_efficiency"],
                consistency_score=row["consistency_score"],
            )
            for row in rows
            if row["total_sleep_hours"] is not None
        ]
        if not nights:
            return SleepSummaryData(
                range_days=days,
                last_night=None,
                avg_sleep_hours=None,
                avg_efficiency=None,
                avg_consistency=None,
                avg_bedtime_hours=None,
                avg_wake_hours=None,
                nights=[],
            )

        last_night = nights[0]
        avg_sleep = sum(n.total_sleep_hours for n in nights) / len(nights)

        efficiencies = [n.sleep_efficiency for n in nights if n.sleep_efficiency is not None]
        avg_efficiency = sum(efficiencies) / len(efficiencies) if efficiencies else None

        consistencies = [n.consistency_score for n in nights if n.consistency_score is not None]
        avg_consistency = sum(consistencies) / len(consistencies) if consistencies else None

        bedtime_hours = [self._bedtime_clock_hours(n.bedtime_at) for n in nights]
        bedtime_hours = [h for h in bedtime_hours if h is not None]
        avg_bedtime = sum(bedtime_hours) / len(bedtime_hours) if bedtime_hours else None

        wake_hours = [self._clock_hours(n.wake_at) for n in nights]
        wake_hours = [h for h in wake_hours if h is not None]
        avg_wake = sum(wake_hours) / len(wake_hours) if wake_hours else None

        return SleepSummaryData(
            range_days=days,
            last_night=last_night,
            avg_sleep_hours=avg_sleep,
            avg_efficiency=avg_efficiency,
            avg_consistency=avg_consistency,
            avg_bedtime_hours=avg_bedtime,
            avg_wake_hours=avg_wake,
            nights=nights,
        )

    def _clock_hours(self, iso_value: str | None) -> float | None:
        if not iso_value:
            return None
        dt = datetime.fromisoformat(iso_value)
        return dt.hour + dt.minute / 60 + dt.second / 3600

    def _bedtime_clock_hours(self, iso_value: str | None) -> float | None:
        """Return bedtime in 'hours past noon' so 22:30 = 10.5 and 01:30 = 13.5."""
        raw = self._clock_hours(iso_value)
        if raw is None:
            return None
        return raw - 12 if raw >= 12 else raw + 12

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
