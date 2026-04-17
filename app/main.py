from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.config import get_app_paths
from app.database.manager import DatabaseManager
from app.parser.health_data_parser import HealthDataParser
from app.services.dashboard_controller import DashboardController
from app.services.import_service import ImportService
from app.services.sleep_analysis_service import SleepAnalysisService
from app.theme import APP_STYLESHEET
from app.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Apple Health Data Analyzer")
    app.setStyleSheet(APP_STYLESHEET)

    app_paths = get_app_paths()
    database_manager = DatabaseManager(app_paths.database_path)
    database_manager.initialize()

    dashboard_controller = DashboardController(database_manager)
    import_service = ImportService(
        database_manager=database_manager,
        parser=HealthDataParser(),
        sleep_analysis_service=SleepAnalysisService(),
    )

    window = MainWindow(
        app_paths=app_paths,
        dashboard_controller=dashboard_controller,
        import_service=import_service,
    )
    window.show()
    return app.exec()
