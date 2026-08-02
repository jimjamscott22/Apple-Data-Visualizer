from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FileInspectionResult:
    is_valid: bool
    message: str
    detected_type: str | None = None


@dataclass(frozen=True)
class ResolvedImportSource:
    selected_path: Path
    export_xml_path: Path
    source_type: str
    file_size: int
    cleanup_dir: Path | None = None


@dataclass(frozen=True)
class ImportResult:
    is_success: bool
    status: str
    message: str
    record_count: int = 0
    warning_count: int = 0
    duplicate_detected: bool = False


@dataclass(frozen=True)
class DatabaseStatusData:
    status: str
    host: str
    port: int
    database: str
    user: str


@dataclass(frozen=True)
class ImportStatistics:
    completed_imports: int = 0
    stored_records: int = 0
    warning_count: int = 0
    duplicate_attempts: int = 0


@dataclass(frozen=True)
class MetricInventoryRecord:
    metric_name: str
    display_name: str
    record_count: int
    first_recorded_at: str | None
    last_recorded_at: str | None
    unit: str | None


@dataclass(frozen=True)
class ImportHistoryRecord:
    id: int
    file_name: str
    file_path: str
    file_size: int | None
    status: str
    status_label: str
    record_count: int
    warning_count: int
    imported_at: str
    source_type: str | None = None
    warnings: tuple[str, ...] = ()
    detail_message: str | None = None
    duplicate_of_import_id: int | None = None


@dataclass(frozen=True)
class ImportsSummaryData:
    database_status: DatabaseStatusData
    statistics: ImportStatistics
    inventory: tuple[MetricInventoryRecord, ...] = ()
    history: tuple[ImportHistoryRecord, ...] = ()
