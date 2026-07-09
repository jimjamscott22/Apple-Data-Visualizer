from __future__ import annotations

import math
from datetime import date, timedelta

from app.models.hrv import HRVDailyRecord, HRVSummaryData


class HRVAnalysisService:
    """Computes HRV summary statistics from raw database rows."""

    TREND_STABLE_THRESHOLD_MS_PER_WEEK = 1.5
    MIN_RECORDS_FOR_TREND = 5

    def compute_summary(
        self,
        daily_rows: list,
        raw_rows: list,
    ) -> HRVSummaryData:
        """Compute an HRV summary from daily_summaries rows and raw records rows.

        Args:
            daily_rows: dict list from daily_summaries for heart_rate_variability.
            raw_rows: dict list from records for heart_rate_variability.
        """
        daily_records = [
            HRVDailyRecord(
                date=row["summary_date"],
                average_ms=row["average_value"],
                # minimum_value / maximum_value may be NULL when a day has only one sample;
                # fall back to average_value so callers always receive a usable range.
                min_ms=row["minimum_value"] if row["minimum_value"] is not None else row["average_value"],
                max_ms=row["maximum_value"] if row["maximum_value"] is not None else row["average_value"],
                sample_count=row["sample_count"],
            )
            for row in daily_rows
            if row["average_value"] is not None
        ]

        if not daily_records and not raw_rows:
            return HRVSummaryData(
                latest_hrv_ms=None,
                latest_hrv_date=None,
                avg_7_day_ms=None,
                avg_30_day_ms=None,
                trend_direction="insufficient_data",
                trend_ms_per_week=None,
                coefficient_of_variation=None,
                daily_records=[],
            )

        latest_hrv_ms: float | None = None
        latest_hrv_date: str | None = None
        if raw_rows:
            latest = raw_rows[-1]
            latest_hrv_ms = latest["value"]
            latest_hrv_date = latest["start_at"][:10]

        today = date.today()
        cutoff_7 = (today - timedelta(days=7)).isoformat()
        cutoff_30 = (today - timedelta(days=30)).isoformat()

        values_7 = [r.average_ms for r in daily_records if r.date >= cutoff_7]
        values_30 = [r.average_ms for r in daily_records if r.date >= cutoff_30]

        avg_7_day_ms = (sum(values_7) / len(values_7)) if values_7 else None
        avg_30_day_ms = (sum(values_30) / len(values_30)) if values_30 else None

        trend_direction = "insufficient_data"
        trend_ms_per_week: float | None = None
        records_30 = [r for r in daily_records if r.date >= cutoff_30]
        if len(records_30) >= self.MIN_RECORDS_FOR_TREND:
            x_vals = list(range(len(records_30)))
            y_vals = [r.average_ms for r in records_30]
            slope_per_day = self._linear_slope(x_vals, y_vals)
            slope_per_week = slope_per_day * 7
            trend_ms_per_week = round(slope_per_week, 2)
            if slope_per_week > self.TREND_STABLE_THRESHOLD_MS_PER_WEEK:
                trend_direction = "rising"
            elif slope_per_week < -self.TREND_STABLE_THRESHOLD_MS_PER_WEEK:
                trend_direction = "falling"
            else:
                trend_direction = "stable"

        coefficient_of_variation: float | None = None
        if len(values_30) >= 3:
            mean = sum(values_30) / len(values_30)
            if mean > 0:
                variance = sum((v - mean) ** 2 for v in values_30) / len(values_30)
                std_dev = math.sqrt(variance)
                coefficient_of_variation = round((std_dev / mean) * 100, 1)

        recent_records = sorted(daily_records, key=lambda r: r.date)[-30:]
        return HRVSummaryData(
            latest_hrv_ms=latest_hrv_ms,
            latest_hrv_date=latest_hrv_date,
            avg_7_day_ms=avg_7_day_ms,
            avg_30_day_ms=avg_30_day_ms,
            trend_direction=trend_direction,
            trend_ms_per_week=trend_ms_per_week,
            coefficient_of_variation=coefficient_of_variation,
            daily_records=recent_records,
        )

    def _linear_slope(self, x_vals: list[float], y_vals: list[float]) -> float:
        """Return the slope of the ordinary least-squares regression line in y-units per x-unit.

        When x_vals represents days (0, 1, 2, …) and y_vals represents HRV in ms, the returned
        value is the estimated change in ms per day.
        """
        n = len(x_vals)
        if n < 2:
            return 0.0
        mean_x = sum(x_vals) / n
        mean_y = sum(y_vals) / n
        numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_vals, y_vals))
        denominator = sum((x - mean_x) ** 2 for x in x_vals)
        if denominator == 0:
            return 0.0
        return numerator / denominator
