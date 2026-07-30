from __future__ import annotations

from app.models.activity import ActivityDayRecord, ActivitySummaryData


class ActivityAnalysisService:
    """Computes activity (steps + distance) summary statistics from daily-summary rows."""

    STEP_GOAL = 10000

    def compute_summary(
        self,
        step_rows: list,
        distance_rows: list,
        days: int,
    ) -> ActivitySummaryData:
        """Build an activity summary from ``daily_summaries`` rows.

        Args:
            step_rows: dict list from daily_summaries for ``step_count``.
            distance_rows: dict list from daily_summaries for ``walking_running_distance``.
            days: the requested range in days, echoed back for the UI header.

        Both row lists expose ``summary_date`` (ISO date string) and ``total_value``
        (the day's summed steps / kilometres). Days present in either metric appear in
        the merged, chronologically-ordered ``daily_records``.
        """
        steps_by_date = {
            row["summary_date"]: row["total_value"]
            for row in step_rows
            if row.get("total_value") is not None
        }
        distance_by_date = {
            row["summary_date"]: row["total_value"]
            for row in distance_rows
            if row.get("total_value") is not None
        }

        all_dates = sorted(set(steps_by_date) | set(distance_by_date))
        daily_records = [
            ActivityDayRecord(
                date=day,
                steps=steps_by_date.get(day),
                distance_km=distance_by_date.get(day),
                goal_met=(steps_by_date.get(day) or 0) >= self.STEP_GOAL,
            )
            for day in all_dates
        ]

        if not daily_records:
            return ActivitySummaryData(
                range_days=days,
                step_goal=self.STEP_GOAL,
                day_count=0,
                active_days=0,
                total_steps=None,
                avg_daily_steps=None,
                best_day_steps=None,
                best_day_date=None,
                total_distance_km=None,
                avg_daily_distance_km=None,
                daily_records=[],
            )

        step_days = [r for r in daily_records if r.steps is not None]
        distance_values = [r.distance_km for r in daily_records if r.distance_km is not None]

        total_steps = sum(r.steps for r in step_days) if step_days else None
        avg_daily_steps = (total_steps / len(step_days)) if step_days else None

        best_day = max(step_days, key=lambda r: r.steps, default=None) if step_days else None
        best_day_steps = best_day.steps if best_day is not None else None
        best_day_date = best_day.date if best_day is not None else None

        total_distance_km = sum(distance_values) if distance_values else None
        avg_daily_distance_km = (
            total_distance_km / len(distance_values) if distance_values else None
        )

        active_days = sum(1 for r in daily_records if r.goal_met)

        return ActivitySummaryData(
            range_days=days,
            step_goal=self.STEP_GOAL,
            day_count=len(daily_records),
            active_days=active_days,
            total_steps=total_steps,
            avg_daily_steps=avg_daily_steps,
            best_day_steps=best_day_steps,
            best_day_date=best_day_date,
            total_distance_km=total_distance_km,
            avg_daily_distance_km=avg_daily_distance_km,
            daily_records=daily_records,
        )
