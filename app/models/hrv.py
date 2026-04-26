from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class HRVDailyRecord:
    date: str
    average_ms: float
    min_ms: float
    max_ms: float
    sample_count: int


@dataclass(frozen=True)
class HRVSummaryData:
    latest_hrv_ms: float | None
    latest_hrv_date: str | None
    avg_7_day_ms: float | None
    avg_30_day_ms: float | None
    trend_direction: str  # "rising", "falling", "stable", "insufficient_data"
    trend_ms_per_week: float | None
    coefficient_of_variation: float | None
    daily_records: list[HRVDailyRecord] = field(default_factory=list)
