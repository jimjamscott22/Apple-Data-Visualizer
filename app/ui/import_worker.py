from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal, Slot

from app.models.imports import ImportResult
from app.services.import_service import ImportService


class ImportWorker(QObject):
    progress = Signal(int, str)
    finished = Signal(object)

    def __init__(self, import_service: ImportService, selected_path: str) -> None:
        super().__init__()
        self._import_service = import_service
        self._selected_path = selected_path

    @Slot()
    def run(self) -> None:
        result = self._import_service.import_file(
            self._selected_path,
            on_progress=self.progress.emit,
        )
        self.finished.emit(result)


def run_import_in_background(
    import_service: ImportService,
    selected_path: str,
    *,
    on_progress,
    on_finished,
) -> tuple[QThread, ImportWorker]:
    """Runs ImportService.import_file on a background QThread.

    The caller must keep the returned (thread, worker) pair referenced
    (e.g. as attributes on the calling widget) until on_finished fires —
    Qt does not keep a running QThread alive on its own, and letting the
    pair get garbage-collected mid-run aborts the import.
    """
    thread = QThread()
    worker = ImportWorker(import_service, selected_path)
    worker.moveToThread(thread)

    thread.started.connect(worker.run)
    worker.progress.connect(on_progress)
    worker.finished.connect(on_finished)
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)

    thread.start()
    return thread, worker
