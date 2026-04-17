from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import tempfile
import zipfile

from app.database.manager import DatabaseManager
from app.models.imports import FileInspectionResult, ImportResult, ResolvedImportSource
from app.parser.health_data_parser import HealthDataParser
from app.services.sleep_analysis_service import SleepAnalysisService


class ImportService:
    SUPPORTED_EXTENSIONS = {".xml", ".zip"}

    def __init__(
        self,
        database_manager: DatabaseManager,
        parser: HealthDataParser,
        sleep_analysis_service: SleepAnalysisService,
    ) -> None:
        self.database_manager = database_manager
        self.parser = parser
        self.sleep_analysis_service = sleep_analysis_service

    def inspect_file(self, selected_path: str) -> FileInspectionResult:
        try:
            resolved = self._resolve_source(Path(selected_path))
        except ValueError as exc:
            return FileInspectionResult(is_valid=False, message=str(exc))
        finally:
            self._cleanup_resolved_source(locals().get("resolved"))

        detected_type = resolved.source_type
        return FileInspectionResult(
            is_valid=True,
            message=(
                f"Validated {resolved.selected_path.name}. Ready to import Apple Health "
                f"{detected_type.upper()} data."
            ),
            detected_type=detected_type,
        )

    def import_file(self, selected_path: str) -> ImportResult:
        resolved: ResolvedImportSource | None = None
        fingerprint: str | None = None
        try:
            resolved = self._resolve_source(Path(selected_path))
            fingerprint = self._fingerprint_file(resolved.export_xml_path)

            existing_import = self.database_manager.find_completed_import_by_fingerprint(fingerprint)
            if existing_import is not None:
                self.database_manager.log_duplicate_import_attempt(
                    file_path=str(resolved.selected_path),
                    file_name=resolved.selected_path.name,
                    file_size=resolved.file_size,
                    file_fingerprint=fingerprint,
                    duplicate_of_id=int(existing_import["id"]),
                )
                return ImportResult(
                    is_success=True,
                    status="duplicate",
                    message=(
                        f"{resolved.selected_path.name} matches a previous import from "
                        f"{existing_import['imported_at']}. No duplicate records were inserted."
                    ),
                    record_count=int(existing_import["record_count"]),
                    duplicate_detected=True,
                )

            records, warnings = self.parser.parse(resolved.export_xml_path)
            import_id = self.database_manager.persist_import(
                file_path=str(resolved.selected_path),
                file_name=resolved.selected_path.name,
                file_size=resolved.file_size,
                file_fingerprint=fingerprint,
                source_type=resolved.source_type,
                records=records,
                warnings=warnings,
            )
            self._refresh_sleep_sessions(import_id=import_id, records=records)
            return ImportResult(
                is_success=True,
                status="completed",
                message=(
                    f"Imported {len(records)} supported records from {resolved.selected_path.name}."
                ),
                record_count=len(records),
                warning_count=len(warnings),
            )
        except ValueError as exc:
            if resolved is not None:
                self.database_manager.log_failed_import(
                    file_path=str(resolved.selected_path),
                    file_name=resolved.selected_path.name,
                    file_size=resolved.file_size,
                    file_fingerprint=fingerprint,
                    notes=str(exc),
                )
            return ImportResult(
                is_success=False,
                status="failed",
                message=str(exc),
            )
        except Exception as exc:
            if resolved is not None:
                self.database_manager.log_failed_import(
                    file_path=str(resolved.selected_path),
                    file_name=resolved.selected_path.name,
                    file_size=resolved.file_size,
                    file_fingerprint=fingerprint,
                    notes=f"Unexpected import failure: {exc}",
                )
            return ImportResult(
                is_success=False,
                status="failed",
                message="The import failed unexpectedly. Check the import history for details.",
            )
        finally:
            self._cleanup_resolved_source(resolved)

    def _resolve_source(self, path: Path) -> ResolvedImportSource:
        if not path.exists() or not path.is_file():
            raise ValueError("The selected file does not exist or cannot be read.")

        suffix = path.suffix.lower()
        if suffix not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                "Select either an Apple Health export.xml file or the exported zip archive."
            )

        if suffix == ".xml":
            return ResolvedImportSource(
                selected_path=path,
                export_xml_path=path,
                source_type="xml",
                file_size=path.stat().st_size,
            )

        try:
            with zipfile.ZipFile(path) as archive:
                export_member = next(
                    (
                        member
                        for member in archive.namelist()
                        if Path(member).name.lower() == "export.xml"
                    ),
                    None,
                )
                if export_member is None:
                    raise ValueError(
                        "The selected zip does not contain an Apple Health export.xml file."
                    )

                temp_dir = Path(tempfile.mkdtemp(prefix="apple-health-import-"))
                target_path = temp_dir / "export.xml"
                with archive.open(export_member) as source_handle, target_path.open("wb") as target_handle:
                    shutil.copyfileobj(source_handle, target_handle)
        except zipfile.BadZipFile as exc:
            raise ValueError("The selected zip archive could not be opened.") from exc

        return ResolvedImportSource(
            selected_path=path,
            export_xml_path=target_path,
            source_type="zip",
            file_size=path.stat().st_size,
            cleanup_dir=temp_dir,
        )

    def _fingerprint_file(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _cleanup_resolved_source(self, resolved: ResolvedImportSource | None) -> None:
        if resolved is None or resolved.cleanup_dir is None:
            return
        shutil.rmtree(resolved.cleanup_dir, ignore_errors=True)

    def _refresh_sleep_sessions(self, *, import_id: int, records: list[dict]) -> None:
        impacted_night_dates = self.sleep_analysis_service.impacted_night_dates(records)
        if not impacted_night_dates:
            return

        stored_sleep_records = [
            record
            for record in self.database_manager.list_sleep_records()
            if self.sleep_analysis_service.night_date_for_record(record) in impacted_night_dates
        ]
        sessions = self.sleep_analysis_service.build_sleep_sessions(stored_sleep_records)
        self.database_manager.replace_sleep_sessions(
            import_id=import_id,
            night_dates=impacted_night_dates,
            sessions=sessions,
        )
