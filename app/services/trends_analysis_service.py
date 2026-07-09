from __future__ import annotations

import math
from datetime import date, timedelta

from app.models.trends import (
    CorrelationPoint,
    CorrelationResult,
    SplitComparison,
    TrendsSummaryData,
)


class TrendsAnalysisService:
    """Computes cross-metric correlations from sleep sessions and daily summaries.

    Night/day pairing semantics: sleep sessions are keyed by ``night_date``, the
    calendar date of the evening the night started (see
    SleepAnalysisService.night_date_for_record). "Next-day" metrics for night N
    therefore live in daily summaries at summary_date = N + 1 day, while daily
    activity on day D pairs with the night whose night_date = D.
    """

    MIN_POINTS_FOR_CORRELATION = 5
    SMALL_SAMPLE_THRESHOLD = 14

    def compute_summary(
        self,
        sleep_rows: list,
        daily_rows_by_metric: dict[str, list],
        days: int,
    ) -> TrendsSummaryData:
        """Build the Trends page dataset.

        Args:
            sleep_rows: dict list from sleep_sessions (night_date,
                total_sleep_hours, ...), any order.
            daily_rows_by_metric: metric_name -> dict list from
                daily_summaries (summary_date, average_value, total_value, ...).
            days: selected range size, echoed back for the UI.
        """
        sleep_by_night = {
            row["night_date"]: row["total_sleep_hours"]
            for row in sleep_rows
            if row["total_sleep_hours"] is not None
        }
        hrv_by_day = self._daily_values(daily_rows_by_metric.get("heart_rate_variability", []), "average_value")
        resting_hr_by_day = self._daily_values(daily_rows_by_metric.get("resting_heart_rate", []), "average_value")
        steps_by_day = self._daily_values(daily_rows_by_metric.get("step_count", []), "total_value")

        sleep_vs_hrv = self._build_correlation(
            title="Sleep duration vs next-day HRV",
            x_label="Hours asleep",
            y_label="Next-day HRV (ms)",
            points=self._pair_sleep_with_next_day(sleep_by_night, hrv_by_day),
        )
        sleep_vs_resting_hr = self._build_correlation(
            title="Sleep duration vs next-day resting HR",
            x_label="Hours asleep",
            y_label="Next-day resting HR (bpm)",
            points=self._pair_sleep_with_next_day(sleep_by_night, resting_hr_by_day),
        )
        steps_vs_sleep = self._build_correlation(
            title="Daily steps vs sleep that night",
            x_label="Steps",
            y_label="Hours asleep",
            points=self._pair_same_day(steps_by_day, sleep_by_night),
        )

        correlations = [sleep_vs_hrv, sleep_vs_resting_hr, steps_vs_sleep]
        measurable = [c for c in correlations if c.pearson_r is not None]
        strongest = max(measurable, key=lambda c: abs(c.pearson_r)) if measurable else None

        return TrendsSummaryData(
            range_days=days,
            correlations=correlations,
            hrv_sleep_split=self._hrv_after_sleep_split(sleep_by_night, hrv_by_day),
            weekday_weekend_sleep=self._weekday_weekend_sleep(sleep_by_night),
            strongest=strongest,
        )

    def _daily_values(self, rows: list, value_column: str) -> dict[str, float]:
        return {
            row["summary_date"]: row[value_column]
            for row in rows
            if row[value_column] is not None
        }

    def _pair_sleep_with_next_day(
        self,
        sleep_by_night: dict[str, float],
        metric_by_day: dict[str, float],
    ) -> list[CorrelationPoint]:
        points = []
        for night_date, sleep_hours in sleep_by_night.items():
            next_day = (date.fromisoformat(night_date) + timedelta(days=1)).isoformat()
            metric_value = metric_by_day.get(next_day)
            if metric_value is not None:
                points.append(CorrelationPoint(x=sleep_hours, y=metric_value, label_date=night_date))
        return sorted(points, key=lambda p: p.label_date)

    def _pair_same_day(
        self,
        metric_by_day: dict[str, float],
        sleep_by_night: dict[str, float],
    ) -> list[CorrelationPoint]:
        points = []
        for day, metric_value in metric_by_day.items():
            sleep_hours = sleep_by_night.get(day)
            if sleep_hours is not None:
                points.append(CorrelationPoint(x=metric_value, y=sleep_hours, label_date=day))
        return sorted(points, key=lambda p: p.label_date)

    def _build_correlation(
        self,
        *,
        title: str,
        x_label: str,
        y_label: str,
        points: list[CorrelationPoint],
    ) -> CorrelationResult:
        sample_count = len(points)
        if sample_count < self.MIN_POINTS_FOR_CORRELATION:
            return CorrelationResult(
                title=title,
                x_label=x_label,
                y_label=y_label,
                points=points,
                pearson_r=None,
                sample_count=sample_count,
                interpretation=(
                    f"Not enough overlapping data ({sample_count} of "
                    f"{self.MIN_POINTS_FOR_CORRELATION} nights needed)."
                ),
            )

        x_vals = [p.x for p in points]
        y_vals = [p.y for p in points]
        pearson_r = self._pearson_r(x_vals, y_vals)
        if pearson_r is None:
            return CorrelationResult(
                title=title,
                x_label=x_label,
                y_label=y_label,
                points=points,
                pearson_r=None,
                sample_count=sample_count,
                interpretation="One of the metrics never varies, so no correlation can be computed.",
            )

        slope, intercept = self._linear_fit(x_vals, y_vals)
        interpretation = self._interpret(pearson_r, sample_count)
        return CorrelationResult(
            title=title,
            x_label=x_label,
            y_label=y_label,
            points=points,
            pearson_r=round(pearson_r, 3),
            sample_count=sample_count,
            interpretation=interpretation,
            regression_slope=slope,
            regression_intercept=intercept,
        )

    def _interpret(self, pearson_r: float, sample_count: int) -> str:
        strength = abs(pearson_r)
        direction = "positive" if pearson_r > 0 else "negative"
        if strength < 0.2:
            summary = "No meaningful relationship"
        elif strength < 0.5:
            summary = f"Weak {direction} relationship"
        elif strength < 0.8:
            summary = f"Moderate {direction} relationship"
        else:
            summary = f"Strong {direction} relationship"
        if sample_count < self.SMALL_SAMPLE_THRESHOLD:
            summary += f" (small sample: {sample_count} nights)"
        return summary

    def _hrv_after_sleep_split(
        self,
        sleep_by_night: dict[str, float],
        hrv_by_day: dict[str, float],
    ) -> SplitComparison | None:
        """Compare next-day HRV after higher-sleep nights vs lower-sleep nights."""
        points = self._pair_sleep_with_next_day(sleep_by_night, hrv_by_day)
        if len(points) < self.MIN_POINTS_FOR_CORRELATION:
            return None

        median_sleep = self._median([p.x for p in points])
        high = [p.y for p in points if p.x >= median_sleep]
        low = [p.y for p in points if p.x < median_sleep]
        if not high or not low:
            return None

        return SplitComparison(
            label=f"HRV after sleeping ≥ vs < {median_sleep:.1f}h",
            group_a_label="More sleep",
            group_a_value=sum(high) / len(high),
            group_b_label="Less sleep",
            group_b_value=sum(low) / len(low),
            unit="ms",
            sample_count=len(points),
        )

    def _weekday_weekend_sleep(self, sleep_by_night: dict[str, float]) -> SplitComparison | None:
        weekday: list[float] = []
        weekend: list[float] = []
        for night_date, sleep_hours in sleep_by_night.items():
            # Friday and Saturday evenings start the nights people sleep in after.
            if date.fromisoformat(night_date).weekday() in (4, 5):
                weekend.append(sleep_hours)
            else:
                weekday.append(sleep_hours)

        if not weekday or not weekend:
            return None

        return SplitComparison(
            label="Weekday vs weekend sleep",
            group_a_label="Weekday nights",
            group_a_value=sum(weekday) / len(weekday),
            group_b_label="Weekend nights",
            group_b_value=sum(weekend) / len(weekend),
            unit="h",
            sample_count=len(weekday) + len(weekend),
        )

    def _pearson_r(self, x_vals: list[float], y_vals: list[float]) -> float | None:
        n = len(x_vals)
        if n < 2:
            return None
        mean_x = sum(x_vals) / n
        mean_y = sum(y_vals) / n
        covariance = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_vals, y_vals))
        variance_x = sum((x - mean_x) ** 2 for x in x_vals)
        variance_y = sum((y - mean_y) ** 2 for y in y_vals)
        if variance_x == 0 or variance_y == 0:
            return None
        return covariance / math.sqrt(variance_x * variance_y)

    def _linear_fit(self, x_vals: list[float], y_vals: list[float]) -> tuple[float, float]:
        n = len(x_vals)
        mean_x = sum(x_vals) / n
        mean_y = sum(y_vals) / n
        numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_vals, y_vals))
        denominator = sum((x - mean_x) ** 2 for x in x_vals)
        slope = numerator / denominator if denominator else 0.0
        return slope, mean_y - slope * mean_x

    def _median(self, values: list[float]) -> float:
        ordered = sorted(values)
        mid = len(ordered) // 2
        if len(ordered) % 2 == 1:
            return ordered[mid]
        return (ordered[mid - 1] + ordered[mid]) / 2
