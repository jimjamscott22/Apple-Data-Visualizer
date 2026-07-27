from __future__ import annotations

import pytest

from app.services.activity_analysis_service import ActivityAnalysisService


@pytest.fixture()
def service() -> ActivityAnalysisService:
    return ActivityAnalysisService()


def _daily_row(summary_date: str, total: float | None) -> dict:
    return {"summary_date": summary_date, "total_value": total}


class TestEmptyInputs:
    def test_no_rows_returns_empty_summary(self, service):
        summary = service.compute_summary([], [], days=30)
        assert summary.range_days == 30
        assert summary.day_count == 0
        assert summary.active_days == 0
        assert summary.total_steps is None
        assert summary.avg_daily_steps is None
        assert summary.best_day_steps is None
        assert summary.best_day_date is None
        assert summary.total_distance_km is None
        assert summary.avg_daily_distance_km is None
        assert summary.daily_records == []

    def test_rows_with_only_none_totals_are_ignored(self, service):
        summary = service.compute_summary(
            [_daily_row("2025-03-01", None)],
            [_daily_row("2025-03-01", None)],
            days=7,
        )
        assert summary.day_count == 0
        assert summary.daily_records == []


class TestStepAggregates:
    def test_totals_and_averages(self, service):
        step_rows = [
            _daily_row("2025-03-01", 8000.0),
            _daily_row("2025-03-02", 12000.0),
            _daily_row("2025-03-03", 4000.0),
        ]
        summary = service.compute_summary(step_rows, [], days=30)

        assert summary.total_steps == pytest.approx(24000.0)
        assert summary.avg_daily_steps == pytest.approx(8000.0)
        assert summary.day_count == 3

    def test_best_day_picks_max_steps(self, service):
        step_rows = [
            _daily_row("2025-03-01", 8000.0),
            _daily_row("2025-03-02", 12000.0),
            _daily_row("2025-03-03", 4000.0),
        ]
        summary = service.compute_summary(step_rows, [], days=30)

        assert summary.best_day_steps == pytest.approx(12000.0)
        assert summary.best_day_date == "2025-03-02"

    def test_active_days_counts_only_days_meeting_goal(self, service):
        step_rows = [
            _daily_row("2025-03-01", 10000.0),  # exactly the goal counts
            _daily_row("2025-03-02", 15000.0),
            _daily_row("2025-03-03", 9999.0),  # just short
        ]
        summary = service.compute_summary(step_rows, [], days=30)

        assert summary.active_days == 2


class TestDistanceAggregates:
    def test_distance_totals_and_average(self, service):
        distance_rows = [
            _daily_row("2025-03-01", 3.0),
            _daily_row("2025-03-02", 5.0),
        ]
        summary = service.compute_summary([], distance_rows, days=30)

        assert summary.total_distance_km == pytest.approx(8.0)
        assert summary.avg_daily_distance_km == pytest.approx(4.0)
        # Distance-only days should still appear as records (with steps None).
        assert summary.day_count == 2
        assert all(record.steps is None for record in summary.daily_records)


class TestMergedRecords:
    def test_dates_are_merged_and_sorted(self, service):
        step_rows = [
            _daily_row("2025-03-03", 5000.0),
            _daily_row("2025-03-01", 6000.0),
        ]
        distance_rows = [
            _daily_row("2025-03-02", 4.2),
            _daily_row("2025-03-01", 3.1),
        ]
        summary = service.compute_summary(step_rows, distance_rows, days=30)

        dates = [record.date for record in summary.daily_records]
        assert dates == ["2025-03-01", "2025-03-02", "2025-03-03"]

        by_date = {record.date: record for record in summary.daily_records}
        assert by_date["2025-03-01"].steps == pytest.approx(6000.0)
        assert by_date["2025-03-01"].distance_km == pytest.approx(3.1)
        assert by_date["2025-03-02"].steps is None
        assert by_date["2025-03-02"].distance_km == pytest.approx(4.2)
        assert by_date["2025-03-03"].steps == pytest.approx(5000.0)
        assert by_date["2025-03-03"].distance_km is None
