from __future__ import annotations

import pytest

from app.services.trends_analysis_service import TrendsAnalysisService


@pytest.fixture()
def service() -> TrendsAnalysisService:
    return TrendsAnalysisService()


def _sleep_row(night_date: str, hours: float | None) -> dict:
    return {"night_date": night_date, "total_sleep_hours": hours}


def _daily_row(summary_date: str, average: float | None = None, total: float | None = None) -> dict:
    return {"summary_date": summary_date, "average_value": average, "total_value": total}


class TestPearsonR:
    def test_perfect_positive(self, service):
        assert service._pearson_r([1, 2, 3, 4], [2, 4, 6, 8]) == pytest.approx(1.0)

    def test_perfect_negative(self, service):
        assert service._pearson_r([1, 2, 3, 4], [8, 6, 4, 2]) == pytest.approx(-1.0)

    def test_uncorrelated(self, service):
        r = service._pearson_r([1, 2, 3, 4], [1, -1, -1, 1])
        assert r == pytest.approx(0.0)

    def test_constant_series_returns_none(self, service):
        assert service._pearson_r([1, 2, 3], [4, 4, 4]) is None
        assert service._pearson_r([2, 2, 2], [1, 5, 9]) is None

    def test_too_few_points_returns_none(self, service):
        assert service._pearson_r([1], [2]) is None


class TestNightPairing:
    def test_next_day_pairing_crosses_month_boundary(self, service):
        points = service._pair_sleep_with_next_day(
            {"2025-01-31": 7.5},
            {"2025-02-01": 55.0},
        )
        assert len(points) == 1
        assert points[0].x == 7.5
        assert points[0].y == 55.0

    def test_next_day_pairing_crosses_year_boundary(self, service):
        points = service._pair_sleep_with_next_day(
            {"2024-12-31": 6.0},
            {"2025-01-01": 48.0},
        )
        assert len(points) == 1

    def test_same_day_metric_is_not_paired_as_next_day(self, service):
        points = service._pair_sleep_with_next_day(
            {"2025-03-10": 7.0},
            {"2025-03-10": 50.0},
        )
        assert points == []

    def test_same_day_pairing_matches_night_date(self, service):
        points = service._pair_same_day(
            {"2025-03-10": 9000.0, "2025-03-11": 12000.0},
            {"2025-03-10": 7.0},
        )
        assert len(points) == 1
        assert points[0].x == 9000.0
        assert points[0].y == 7.0


class TestComputeSummary:
    def test_insufficient_overlap_reports_no_r(self, service):
        sleep_rows = [_sleep_row("2025-03-10", 7.0), _sleep_row("2025-03-11", 6.5)]
        daily = {"heart_rate_variability": [_daily_row("2025-03-11", average=50.0)]}
        summary = service.compute_summary(sleep_rows, daily, days=30)

        hrv_corr = summary.correlations[0]
        assert hrv_corr.pearson_r is None
        assert hrv_corr.sample_count == 1
        assert summary.strongest is None

    def test_correlated_data_produces_r_and_regression(self, service):
        sleep_rows = [
            _sleep_row(f"2025-03-{10 + i:02d}", 5.0 + i * 0.5) for i in range(8)
        ]
        daily = {
            "heart_rate_variability": [
                _daily_row(f"2025-03-{11 + i:02d}", average=40.0 + i * 2.0) for i in range(8)
            ]
        }
        summary = service.compute_summary(sleep_rows, daily, days=30)

        hrv_corr = summary.correlations[0]
        assert hrv_corr.pearson_r == pytest.approx(1.0)
        assert hrv_corr.sample_count == 8
        assert hrv_corr.regression_slope == pytest.approx(4.0)
        assert "small sample" in hrv_corr.interpretation
        assert summary.strongest is hrv_corr

    def test_null_values_are_skipped(self, service):
        sleep_rows = [_sleep_row("2025-03-10", None), _sleep_row("2025-03-11", 7.0)]
        daily = {"heart_rate_variability": [_daily_row("2025-03-11", average=None)]}
        summary = service.compute_summary(sleep_rows, daily, days=30)
        assert summary.correlations[0].points == []


class TestSplits:
    def test_hrv_median_split_separates_groups(self, service):
        sleep_by_night = {f"2025-03-{10 + i:02d}": hours for i, hours in enumerate([5, 5, 5, 8, 8, 8])}
        hrv_by_day = {
            "2025-03-11": 40.0,
            "2025-03-12": 42.0,
            "2025-03-13": 41.0,
            "2025-03-14": 55.0,
            "2025-03-15": 56.0,
            "2025-03-16": 54.0,
        }
        split = service._hrv_after_sleep_split(sleep_by_night, hrv_by_day)

        assert split is not None
        assert split.group_a_value == pytest.approx(55.0)
        assert split.group_b_value == pytest.approx(41.0)
        assert split.sample_count == 6

    def test_hrv_split_needs_minimum_points(self, service):
        split = service._hrv_after_sleep_split(
            {"2025-03-10": 7.0},
            {"2025-03-11": 50.0},
        )
        assert split is None

    def test_weekday_weekend_split_uses_friday_and_saturday_nights(self, service):
        # 2025-03-14 is a Friday, 2025-03-15 a Saturday, 2025-03-16 a Sunday.
        sleep_by_night = {
            "2025-03-13": 7.0,  # Thursday night -> weekday
            "2025-03-14": 9.0,  # Friday night -> weekend
            "2025-03-15": 9.5,  # Saturday night -> weekend
            "2025-03-16": 7.5,  # Sunday night -> weekday
        }
        split = service._weekday_weekend_sleep(sleep_by_night)

        assert split is not None
        assert split.group_a_value == pytest.approx((7.0 + 7.5) / 2)
        assert split.group_b_value == pytest.approx((9.0 + 9.5) / 2)

    def test_weekday_weekend_split_requires_both_groups(self, service):
        assert service._weekday_weekend_sleep({"2025-03-13": 7.0}) is None


class TestMedian:
    def test_odd_count(self, service):
        assert service._median([3, 1, 2]) == 2

    def test_even_count(self, service):
        assert service._median([4, 1, 3, 2]) == pytest.approx(2.5)
