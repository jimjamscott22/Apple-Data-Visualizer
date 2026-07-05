from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CorrelationPoint:
    x: float
    y: float
    label_date: str


@dataclass(frozen=True)
class CorrelationResult:
    title: str
    x_label: str
    y_label: str
    points: list[CorrelationPoint]
    pearson_r: float | None
    sample_count: int
    interpretation: str
    regression_slope: float | None = None
    regression_intercept: float | None = None


@dataclass(frozen=True)
class SplitComparison:
    label: str
    group_a_label: str
    group_a_value: float | None
    group_b_label: str
    group_b_value: float | None
    unit: str
    sample_count: int


@dataclass(frozen=True)
class TrendsSummaryData:
    range_days: int
    correlations: list[CorrelationResult] = field(default_factory=list)
    hrv_sleep_split: SplitComparison | None = None
    weekday_weekend_sleep: SplitComparison | None = None
    strongest: CorrelationResult | None = None
