from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET


APPLE_RECORD_TYPE_MAP = {
    "HKCategoryTypeIdentifierSleepAnalysis": "sleep_analysis",
    "HKQuantityTypeIdentifierStepCount": "step_count",
    "HKQuantityTypeIdentifierHeartRate": "heart_rate",
    "HKQuantityTypeIdentifierRestingHeartRate": "resting_heart_rate",
    "HKQuantityTypeIdentifierHeartRateVariabilitySDNN": "heart_rate_variability",
    "HKQuantityTypeIdentifierRespiratoryRate": "respiratory_rate",
    "HKQuantityTypeIdentifierDistanceWalkingRunning": "walking_running_distance",
}

DATE_FORMAT = "%Y-%m-%d %H:%M:%S %z"
MAX_WARNING_DETAILS = 25

SLEEP_STAGE_MAP = {
    "HKCategoryValueSleepAnalysisInBed": "in_bed",
    "HKCategoryValueSleepAnalysisAsleep": "asleep",
    "HKCategoryValueSleepAnalysisAwake": "awake",
    "HKCategoryValueSleepAnalysisAsleepUnspecified": "asleep_unspecified",
    "HKCategoryValueSleepAnalysisAsleepCore": "asleep_core",
    "HKCategoryValueSleepAnalysisAsleepDeep": "asleep_deep",
    "HKCategoryValueSleepAnalysisAsleepREM": "asleep_rem",
}


class HealthDataParser:
    def parse(self, export_xml_path: Path) -> tuple[list[dict], list[str]]:
        records: list[dict] = []

        def collect_record(record: dict) -> None:
            records.append(record)

        warnings = self.parse_stream(export_xml_path, on_record=collect_record)
        return records, warnings

    def parse_stream(
        self,
        export_xml_path: Path,
        *,
        on_record,
    ) -> list[str]:
        warnings: list[str] = []
        unsupported_types: Counter[str] = Counter()
        malformed_count = 0

        try:
            context = ET.iterparse(export_xml_path, events=("end",))
        except ET.ParseError as exc:
            raise ValueError(f"The XML file could not be parsed: {exc}") from exc

        seen_root = False
        for _, element in context:
            tag_name = self._local_name(element.tag)

            if not seen_root and tag_name == "HealthData":
                seen_root = True

            if tag_name != "Record":
                element.clear()
                continue

            source_type = element.attrib.get("type", "")
            metric_name = APPLE_RECORD_TYPE_MAP.get(source_type)
            if metric_name is None:
                unsupported_types[source_type or "UnknownRecordType"] += 1
                element.clear()
                continue

            try:
                normalized_record = self._parse_record(metric_name, source_type, element.attrib)
            except ValueError as exc:
                malformed_count += 1
                if len(warnings) < MAX_WARNING_DETAILS:
                    warnings.append(str(exc))
                element.clear()
                continue

            on_record(normalized_record)
            element.clear()

        if not seen_root:
            raise ValueError("The selected XML does not look like an Apple Health export.")

        if unsupported_types:
            top_types = ", ".join(
                f"{record_type} ({count})"
                for record_type, count in unsupported_types.most_common(5)
            )
            warnings.append(
                "Skipped "
                f"{sum(unsupported_types.values())} unsupported records across "
                f"{len(unsupported_types)} Apple Health types. Top skipped types: {top_types}."
            )

        if malformed_count:
            warnings.append(f"Skipped {malformed_count} malformed supported records during parsing.")

        return warnings

    def _parse_record(self, metric_name: str, source_type: str, attributes: dict[str, str]) -> dict:
        start_at = self._parse_datetime(attributes.get("startDate"), "startDate", source_type)
        end_at = self._parse_datetime(attributes.get("endDate"), "endDate", source_type)
        source_name = attributes.get("sourceName") or "Unknown Source"
        metadata = {
            "device": attributes.get("device"),
            "creation_date": attributes.get("creationDate"),
        }

        if metric_name == "sleep_analysis":
            duration_hours = max((end_at - start_at).total_seconds() / 3600, 0.0)
            raw_value = attributes.get("value", "")
            metadata["sleep_stage"] = SLEEP_STAGE_MAP.get(raw_value, raw_value or "unknown")
            metadata["apple_value"] = raw_value
            value = round(duration_hours, 4)
            unit = "hours"
        else:
            raw_value = attributes.get("value")
            if raw_value is None:
                raise ValueError(f"Missing value for supported record type {source_type}.")
            try:
                parsed_value = float(raw_value)
            except ValueError as exc:
                raise ValueError(
                    f"Could not parse numeric value '{raw_value}' for supported record type {source_type}."
                ) from exc
            value, unit = self._normalize_quantity(metric_name, parsed_value, attributes.get("unit"))
            metadata["apple_value"] = raw_value
            metadata["apple_unit"] = attributes.get("unit")

        metadata = {key: value for key, value in metadata.items() if value not in (None, "")}
        return {
            "metric_name": metric_name,
            "source_type": source_type,
            "source_name": source_name,
            "start_at": start_at.isoformat(),
            "end_at": end_at.isoformat(),
            "value": value,
            "unit": unit,
            "metadata": metadata,
        }

    def _normalize_quantity(
        self,
        metric_name: str,
        value: float,
        raw_unit: str | None,
    ) -> tuple[float, str]:
        unit = (raw_unit or "").strip()
        if metric_name == "step_count":
            return value, "count"
        if metric_name in {"heart_rate", "resting_heart_rate"}:
            return value, "bpm" if unit == "count/min" else unit or "count/min"
        if metric_name == "heart_rate_variability":
            return value, "ms" if unit == "ms" else unit or "ms"
        if metric_name == "respiratory_rate":
            return value, "breaths/min" if unit == "count/min" else unit or "count/min"
        if metric_name == "walking_running_distance":
            if unit == "km":
                return value, "km"
            if unit == "m":
                return round(value / 1000, 4), "km"
            if unit == "mi":
                return round(value * 1.60934, 4), "km"
            if unit == "ft":
                return round(value * 0.0003048, 4), "km"
            return value, unit or "distance"
        return value, unit or "value"

    def _parse_datetime(self, raw_value: str | None, field_name: str, source_type: str) -> datetime:
        if not raw_value:
            raise ValueError(f"Missing {field_name} for supported record type {source_type}.")
        try:
            return datetime.strptime(raw_value, DATE_FORMAT)
        except ValueError as exc:
            raise ValueError(
                f"Could not parse {field_name} '{raw_value}' for supported record type {source_type}."
            ) from exc

    def _local_name(self, tag: str) -> str:
        return tag.rsplit("}", 1)[-1]
