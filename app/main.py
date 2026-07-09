from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from app.database.config import MissingDatabaseSettingsError, get_database_settings
from app.database.errors import DatabaseConnectionError
from app.database.manager import DatabaseManager
from app.parser.health_data_parser import HealthDataParser
from app.services.dashboard_controller import DashboardController
from app.services.hrv_analysis_service import HRVAnalysisService
from app.services.import_service import ImportService
from app.services.sleep_analysis_service import SleepAnalysisService
from app.services.trends_analysis_service import TrendsAnalysisService
from app.theme import APP_STYLESHEET
from app.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Apple Health Data Analyzer")
    app.setStyleSheet(APP_STYLESHEET)

    try:
        database_settings = get_database_settings()
        database_manager = DatabaseManager(database_settings)
        database_manager.initialize()
    except MissingDatabaseSettingsError as exc:
        QMessageBox.critical(None, "Database Not Configured", str(exc))
        return 1
    except DatabaseConnectionError as exc:
        QMessageBox.critical(
            None,
            "Cannot Connect to MariaDB",
            f"{exc}\n\nCheck that the MariaDB server is running and reachable "
            "on your network, and that your connection settings are correct.",
        )
        return 1

    hrv_analysis_service = HRVAnalysisService()
    trends_analysis_service = TrendsAnalysisService()
    dashboard_controller = DashboardController(
        database_manager, hrv_analysis_service, trends_analysis_service
    )
    import_service = ImportService(
        database_manager=database_manager,
        parser=HealthDataParser(),
        sleep_analysis_service=SleepAnalysisService(),
    )

    window = MainWindow(
        database_settings=database_settings,
        dashboard_controller=dashboard_controller,
        import_service=import_service,
    )
    window.show()
    return app.exec()
