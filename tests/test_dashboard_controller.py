from __future__ import annotations

from dataclasses import asdict, is_dataclass

from app.database.config import DatabaseSettings
from app.services.activity_analysis_service import ActivityAnalysisService
from app.services.dashboard_controller import DashboardController
from app.services.hrv_analysis_service import HRVAnalysisService
from app.services.import_history_service import ImportHistoryService
from app.services.trends_analysis_service import TrendsAnalysisService


class FakeDatabaseManager:
    def __init__(self) -> None:
        self.settings = DatabaseSettings(
            host="db.local",
            port=3307,
            database="apple_health",
            user="health_reader",
            password="do-not-expose-password",
        )
        self.calls: list[tuple[str, int | None]] = []

    def get_import_statistics(self) -> dict:
        self.calls.append(("get_import_statistics", None))
        return {
            "completed_imports": 2,
            "stored_records": 14,
            "warning_count": 1,
            "duplicate_attempts": 1,
        }

    def get_record_inventory(self) -> list[dict]:
        self.calls.append(("get_record_inventory", None))
        return [
            {
                "metric_name": "step_count",
                "record_count": 14,
                "first_recorded_at": "2026-08-01 09:00:00",
                "last_recorded_at": "2026-08-02 09:00:00",
                "unit": "count",
            }
        ]

    def list_recent_imports(self, limit: int = 50) -> list[dict]:
        self.calls.append(("list_recent_imports", limit))
        return [
            {
                "id": 3,
                "file_name": "export.xml",
                "file_path": "C:/Health/export.xml",
                "file_fingerprint": "do-not-expose-fingerprint",
                "file_size": 1024,
                "import_status": "completed",
                "record_count": 14,
                "warning_count": 1,
                "imported_at": "2026-08-02 10:00:00",
                "notes": '{"source_type":"xml","warnings":["Ignored unknown record"]}',
            }
        ]


def _build_controller(database_manager: FakeDatabaseManager) -> DashboardController:
    return DashboardController(
        database_manager=database_manager,
        hrv_analysis_service=HRVAnalysisService(),
        trends_analysis_service=TrendsAnalysisService(),
        activity_analysis_service=ActivityAnalysisService(),
        import_history_service=ImportHistoryService(),
    )


def _render_model(value: object) -> str:
    if is_dataclass(value):
        return _render_model(asdict(value))
    if isinstance(value, dict):
        return repr({key: _render_model(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return repr([_render_model(item) for item in value])
    return repr(value)


def test_load_imports_summary_orchestrates_reads_and_keeps_credentials_private():
    database_manager = FakeDatabaseManager()

    summary = _build_controller(database_manager).load_imports_summary(limit=12)

    assert database_manager.calls == [
        ("get_import_statistics", None),
        ("get_record_inventory", None),
        ("list_recent_imports", 12),
    ]
    assert summary.database_status.status == "Connected"
    assert summary.database_status.host == "db.local"
    assert summary.database_status.port == 3307
    assert summary.database_status.database == "apple_health"
    assert summary.database_status.user == "health_reader"
    assert summary.statistics.stored_records == 14
    assert summary.inventory[0].metric_name == "step_count"
    assert summary.history[0].source_type == "xml"

    rendered_summary = _render_model(summary)
    assert "do-not-expose-password" not in rendered_summary
    assert "do-not-expose-fingerprint" not in rendered_summary
