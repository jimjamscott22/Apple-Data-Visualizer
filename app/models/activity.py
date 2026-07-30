from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ActivityDayRecord:
    date: str
    steps: float | None
    distance_km: float | None
    goal_met: bool


@dataclass(frozen=True)
class ActivitySummaryData:
    range_days: int
    step_goal: int
    day_count: int
    active_days: int
    total_steps: float | None
    avg_daily_steps: float | None
    best_day_steps: float | None
    best_day_date: str | None
    total_distance_km: float | None
    avg_daily_distance_km: float | None
    daily_records: list[ActivityDayRecord] = field(default_factory=list)
