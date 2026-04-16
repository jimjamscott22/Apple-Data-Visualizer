from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MetricCardData:
    label: str
    value: str
    detail: str


@dataclass(frozen=True)
class ImportStatusSummary:
    title: str
    detail: str


@dataclass(frozen=True)
class OverviewData:
    metrics: list[MetricCardData] = field(default_factory=list)
    import_status: ImportStatusSummary = field(
        default_factory=lambda: ImportStatusSummary(
            title="No imports yet",
            detail="Import an Apple Health export to populate dashboard metrics.",
        )
    )
