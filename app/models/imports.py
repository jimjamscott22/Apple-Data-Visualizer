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
