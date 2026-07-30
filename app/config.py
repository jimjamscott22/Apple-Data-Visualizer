from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

APP_NAME = "Apple Health Data Analyzer"

try:
    APP_VERSION = version("apple-data-visualizer")
except PackageNotFoundError:
    APP_VERSION = "development"
