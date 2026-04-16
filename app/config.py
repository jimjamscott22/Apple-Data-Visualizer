from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


APP_NAME = "Apple Health Data Analyzer"
APP_SLUG = "apple-health-data-analyzer"
DATABASE_FILENAME = "health_data.sqlite3"


@dataclass(frozen=True)
class AppPaths:
    root_data_dir: Path
    database_path: Path


def get_app_paths() -> AppPaths:
    root_data_dir = Path.home() / f".{APP_SLUG}"
    return AppPaths(
        root_data_dir=root_data_dir,
        database_path=root_data_dir / DATABASE_FILENAME,
    )
