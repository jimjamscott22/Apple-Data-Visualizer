from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SleepNightRecord:
    night_date: str
    bedtime_at: str | None
    wake_at: str | None
    total_sleep_hours: float
    time_in_bed_hours: float | None
    sleep_efficiency: float | None
    consistency_score: float | None


@dataclass(frozen=True)
class SleepSummaryData:
    range_days: int
    last_night: SleepNightRecord | None
    avg_sleep_hours: float | None
    avg_efficiency: float | None
    avg_consistency: float | None
    avg_bedtime_hours: float | None
    avg_wake_hours: float | None
    nights: list[SleepNightRecord] = field(default_factory=list)
