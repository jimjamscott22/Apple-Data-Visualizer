from __future__ import annotations


class DatabaseConnectionError(RuntimeError):
    """Raised when the app cannot establish or use a MariaDB connection."""
