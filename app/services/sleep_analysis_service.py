from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta


ASLEEP_STAGES = {
    "asleep",
    "asleep_unspecified",
    "asleep_core",
    "asleep_deep",
    "asleep_rem",
}


class SleepAnalysisService:
    NIGHT_START_HOUR = 12

    def build_sleep_sessions(self, normalized_records: list[dict]) -> list[dict]:
        grouped_records: dict[str, list[dict]] = defaultdict(list)
        for record in normalized_records:
            if record.get("metric_name") != "sleep_analysis":
                continue
            grouped_records[self.night_date_for_record(record)].append(record)

        sessions: list[dict] = []
        for night_date in sorted(grouped_records):
            session = self._build_session(night_date, grouped_records[night_date])
            if session is not None:
                sessions.append(session)
        return sessions

    def impacted_night_dates(self, normalized_records: list[dict]) -> set[str]:
        return {
            self.night_date_for_record(record)
            for record in normalized_records
            if record.get("metric_name") == "sleep_analysis"
        }

    def night_date_for_record(self, record: dict) -> str:
        start_at = self._parse_iso_datetime(record["start_at"])
        night_anchor = start_at - timedelta(hours=self.NIGHT_START_HOUR)
        return night_anchor.date().isoformat()

    def _build_session(self, night_date: str, records: list[dict]) -> dict | None:
        intervals: list[tuple[datetime, datetime, str]] = []
        asleep_intervals: list[tuple[datetime, datetime]] = []
        in_bed_intervals: list[tuple[datetime, datetime]] = []

        bedtime_at: datetime | None = None
        wake_at: datetime | None = None

        for record in records:
            start_at = self._parse_iso_datetime(record["start_at"])
            end_at = self._parse_iso_datetime(record["end_at"])
            if end_at <= start_at:
                continue

            sleep_stage = str(record.get("metadata", {}).get("sleep_stage", "unknown"))
            intervals.append((start_at, end_at, sleep_stage))

            bedtime_at = start_at if bedtime_at is None else min(bedtime_at, start_at)
            wake_at = end_at if wake_at is None else max(wake_at, end_at)

            if sleep_stage in ASLEEP_STAGES:
                asleep_intervals.append((start_at, end_at))
            if sleep_stage == "in_bed":
                in_bed_intervals.append((start_at, end_at))

        if bedtime_at is None or wake_at is None:
            return None

        total_sleep_hours = self._merged_duration_hours(asleep_intervals)
        if total_sleep_hours <= 0:
            return None

        time_in_bed_hours = self._merged_duration_hours(in_bed_intervals)
        if time_in_bed_hours <= 0:
            time_in_bed_hours = round((wake_at - bedtime_at).total_seconds() / 3600, 4)

        sleep_efficiency = None
        if time_in_bed_hours > 0:
            sleep_efficiency = round(min((total_sleep_hours / time_in_bed_hours) * 100, 100.0), 1)

        consistency_score = self._calculate_consistency_score(
            bedtime_at=bedtime_at,
            wake_at=wake_at,
            total_sleep_hours=total_sleep_hours,
            sleep_efficiency=sleep_efficiency,
        )

        stage_hours = self._stage_duration_hours(intervals)
        summary = {
            "record_count": len(records),
            "stage_hours": stage_hours,
        }

        return {
            "night_date": night_date,
            "bedtime_at": bedtime_at.isoformat(),
            "wake_at": wake_at.isoformat(),
            "total_sleep_hours": total_sleep_hours,
            "time_in_bed_hours": round(time_in_bed_hours, 4),
            "sleep_efficiency": sleep_efficiency,
            "consistency_score": consistency_score,
            "summary": summary,
        }

    def _calculate_consistency_score(
        self,
        *,
        bedtime_at: datetime,
        wake_at: datetime,
        total_sleep_hours: float,
        sleep_efficiency: float | None,
    ) -> float:
        bedtime_hours = bedtime_at.hour + (bedtime_at.minute / 60)
        if bedtime_hours < self.NIGHT_START_HOUR:
            bedtime_hours += 24
        wake_hours = wake_at.hour + (wake_at.minute / 60)

        bedtime_penalty = min(abs(bedtime_hours - 22.5) * 6, 24)
        wake_penalty = min(abs(wake_hours - 7.0) * 5, 20)
        duration_penalty = min(abs(total_sleep_hours - 8.0) * 10, 32)
        efficiency_penalty = 0.0
        if sleep_efficiency is not None:
            efficiency_penalty = min(max(85.0 - sleep_efficiency, 0.0) * 0.8, 24)

        score = 100.0 - bedtime_penalty - wake_penalty - duration_penalty - efficiency_penalty
        return round(max(min(score, 100.0), 0.0), 1)

    def _stage_duration_hours(
        self,
        intervals: list[tuple[datetime, datetime, str]],
    ) -> dict[str, float]:
        grouped: dict[str, list[tuple[datetime, datetime]]] = defaultdict(list)
        for start_at, end_at, sleep_stage in intervals:
            grouped[sleep_stage].append((start_at, end_at))
        return {
            stage: self._merged_duration_hours(stage_intervals)
            for stage, stage_intervals in sorted(grouped.items())
        }

    def _merged_duration_hours(self, intervals: list[tuple[datetime, datetime]]) -> float:
        if not intervals:
            return 0.0

        merged: list[list[datetime]] = []
        for start_at, end_at in sorted(intervals, key=lambda item: item[0]):
            if not merged or start_at > merged[-1][1]:
                merged.append([start_at, end_at])
                continue
            merged[-1][1] = max(merged[-1][1], end_at)

        total_seconds = sum(
            (end_at - start_at).total_seconds()
            for start_at, end_at in merged
        )
        return round(total_seconds / 3600, 4)

    def _parse_iso_datetime(self, raw_value: str) -> datetime:
        return datetime.fromisoformat(raw_value)
