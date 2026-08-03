from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.models.imports import ImportHistoryRecord, ImportsSummaryData, MetricInventoryRecord
from app.ui.pages.base import EmptyStateCard, MetricCard, right_aligned


class ImportsPage(QWidget):
    """Read-only database and import-history dashboard."""

    refresh_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PageRoot")
        self._history_by_id: dict[int, ImportHistoryRecord] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        self.connection_card, self.connection_form = self._build_connection_card()
        layout.addWidget(self.connection_card)

        self.metrics_row = QHBoxLayout()
        self.metrics_row.setSpacing(14)
        layout.addLayout(self.metrics_row)

        self.inventory_card, self.inventory_table, self.inventory_empty = self._build_inventory_card()
        layout.addWidget(self.inventory_card)

        self.history_card, self.history_table, self.history_empty = self._build_history_card()
        layout.addWidget(self.history_card)

        self.detail_card, self.detail_form, self.detail_context_label = self._build_detail_card()
        layout.addWidget(self.detail_card)
        layout.addStretch()

        self.history_table.itemSelectionChanged.connect(self._render_selected_detail)
        self._set_empty_state()

    def render(
        self,
        summary: ImportsSummaryData,
        preserve_import_id: int | None = None,
    ) -> None:
        """Render a snapshot while preserving the selected history record when possible."""
        selected_id = preserve_import_id
        if selected_id is None:
            selected_id = self._selected_import_id()

        self._render_connection(summary)
        self._render_statistics(summary)
        self._render_inventory(summary.inventory)
        self._render_history(summary.history, selected_id)

    def _build_connection_card(self) -> tuple[QFrame, QFormLayout]:
        card = QFrame()
        card.setObjectName("SettingsCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(12)

        header = QHBoxLayout()
        copy = QVBoxLayout()
        copy.setSpacing(6)
        title = QLabel("Database status")
        title.setObjectName("SectionTitle")
        description = QLabel("Connection details are informational and cannot be edited here.")
        description.setObjectName("BodyMuted")
        description.setWordWrap(True)
        copy.addWidget(title)
        copy.addWidget(description)
        header.addLayout(copy, 1)

        refresh_button = QPushButton("Refresh")
        refresh_button.setObjectName("SecondaryButton")
        refresh_button.setAccessibleName("Refresh import data")
        refresh_button.clicked.connect(self.refresh_requested.emit)
        header.addWidget(refresh_button)
        layout.addLayout(header)

        form = QFormLayout()
        form.setSpacing(10)
        self.connection_status = QLabel()
        self.connection_status.setObjectName("ConnectionStatus")
        self.connection_host = _selectable_label()
        self.connection_database = _selectable_label()
        self.connection_user = _selectable_label()
        form.addRow("Database status:", self.connection_status)
        form.addRow("Host:", self.connection_host)
        form.addRow("Database:", self.connection_database)
        form.addRow("User:", self.connection_user)
        layout.addLayout(form)
        return card, form

    def _build_inventory_card(self) -> tuple[QFrame, QTableWidget, EmptyStateCard]:
        card = _section_card("Record inventory", "All normalized records currently stored.")
        layout = card.layout()
        assert isinstance(layout, QVBoxLayout)

        table = QTableWidget(0, 5)
        table.setObjectName("InventoryTable")
        table.setHorizontalHeaderLabels(
            ["Metric", "Records", "First recorded", "Last recorded", "Unit"]
        )
        _configure_table(table, selectable=False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setMinimumHeight(190)

        empty = EmptyStateCard(
            "No stored records yet",
            "Import an Apple Health export to build a record inventory.",
        )
        layout.addWidget(table)
        layout.addWidget(empty)
        return card, table, empty

    def _build_history_card(self) -> tuple[QFrame, QTableWidget, EmptyStateCard]:
        card = _section_card("Import history", "The 50 most recent import attempts.")
        layout = card.layout()
        assert isinstance(layout, QVBoxLayout)

        table = QTableWidget(0, 6)
        table.setObjectName("ImportHistoryTable")
        table.setHorizontalHeaderLabels(["Imported", "File", "Status", "Records", "Warnings", "Size"])
        _configure_table(table, selectable=True)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        for column in (2, 3, 4, 5):
            table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeToContents)
        table.setMinimumHeight(220)

        empty = EmptyStateCard(
            "No imports yet",
            "Use Import Apple Health Export to add an XML or ZIP export. Import attempts will appear here.",
        )
        layout.addWidget(table)
        layout.addWidget(empty)
        return card, table, empty

    def _build_detail_card(self) -> tuple[QFrame, QFormLayout, QLabel]:
        card = QFrame()
        card.setObjectName("ImportDetailPanel")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(12)

        title = QLabel("Selected import details")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)
        self.detail_file_name = _selectable_label()
        self.detail_file_path = _selectable_label()
        self.detail_imported_at = _selectable_label()
        self.detail_file_size = _selectable_label()
        self.detail_status = _selectable_label()
        self.detail_record_count = _selectable_label()
        self.detail_warning_count = _selectable_label()
        self.detail_source_type = _selectable_label()
        form.addRow("File:", self.detail_file_name)
        form.addRow("Stored path:", self.detail_file_path)
        form.addRow("Imported:", self.detail_imported_at)
        form.addRow("Size:", self.detail_file_size)
        form.addRow("Status:", self.detail_status)
        form.addRow("Records:", self.detail_record_count)
        form.addRow("Warnings:", self.detail_warning_count)
        form.addRow("Source type:", self.detail_source_type)
        layout.addLayout(form)

        context = _selectable_label()
        context.setObjectName("ImportDetailText")
        context.setWordWrap(True)
        layout.addWidget(context)
        return card, form, context

    def _render_connection(self, summary: ImportsSummaryData) -> None:
        status = summary.database_status
        self.connection_status.setText(status.status)
        self.connection_host.setText(f"{status.host}:{status.port}")
        self.connection_database.setText(status.database)
        self.connection_user.setText(status.user)

    def _render_statistics(self, summary: ImportsSummaryData) -> None:
        _clear_layout(self.metrics_row)
        statistics = summary.statistics
        cards = (
            ("Completed imports", statistics.completed_imports, "Successful import attempts"),
            ("Stored records", statistics.stored_records, "All normalized health records"),
            ("Parser warnings", statistics.warning_count, "Warnings recorded across imports"),
            ("Duplicate attempts", statistics.duplicate_attempts, "Attempts with no new records"),
        )
        for label, value, detail in cards:
            self.metrics_row.addWidget(MetricCard(label, f"{value:,}", detail))

    def _render_inventory(self, inventory: tuple[MetricInventoryRecord, ...]) -> None:
        self.inventory_table.setVisible(bool(inventory))
        self.inventory_empty.setVisible(not inventory)
        self.inventory_table.setRowCount(len(inventory))
        for row_index, record in enumerate(inventory):
            self.inventory_table.setItem(row_index, 0, QTableWidgetItem(record.display_name))
            self.inventory_table.setItem(row_index, 1, right_aligned(f"{record.record_count:,}"))
            self.inventory_table.setItem(
                row_index, 2, QTableWidgetItem(record.first_recorded_at or "—")
            )
            self.inventory_table.setItem(
                row_index, 3, QTableWidgetItem(record.last_recorded_at or "—")
            )
            self.inventory_table.setItem(row_index, 4, QTableWidgetItem(record.unit or "—"))

    def _render_history(
        self,
        history: tuple[ImportHistoryRecord, ...],
        selected_id: int | None,
    ) -> None:
        self._history_by_id = {record.id: record for record in history}
        self.history_table.setVisible(bool(history))
        self.history_empty.setVisible(not history)

        with QSignalBlocker(self.history_table):
            self.history_table.clearContents()
            self.history_table.setRowCount(len(history))
            for row_index, record in enumerate(history):
                imported_item = QTableWidgetItem(record.imported_at)
                imported_item.setData(Qt.UserRole, record.id)
                self.history_table.setItem(row_index, 0, imported_item)
                self.history_table.setItem(row_index, 1, QTableWidgetItem(record.file_name))

                status_item = QTableWidgetItem(record.status_label)
                status_item.setForeground(QColor(_status_color(record.status)))
                self.history_table.setItem(row_index, 2, status_item)
                self.history_table.setItem(row_index, 3, right_aligned(f"{record.record_count:,}"))
                self.history_table.setItem(row_index, 4, right_aligned(f"{record.warning_count:,}"))
                self.history_table.setItem(row_index, 5, right_aligned(_format_file_size(record.file_size)))

        if not history:
            self.detail_card.setVisible(False)
            return

        target_id = selected_id if selected_id in self._history_by_id else history[0].id
        target_row = next(index for index, record in enumerate(history) if record.id == target_id)
        self.history_table.selectRow(target_row)
        self._render_detail(self._history_by_id[target_id])

    def _render_selected_detail(self) -> None:
        selected_id = self._selected_import_id()
        if selected_id is not None and selected_id in self._history_by_id:
            self._render_detail(self._history_by_id[selected_id])

    def _selected_import_id(self) -> int | None:
        rows = self.history_table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self.history_table.item(rows[0].row(), 0)
        value = item.data(Qt.UserRole) if item is not None else None
        return value if isinstance(value, int) else None

    def _render_detail(self, record: ImportHistoryRecord) -> None:
        self.detail_card.setVisible(True)
        self.detail_file_name.setText(record.file_name)
        self.detail_file_path.setText(record.file_path)
        self.detail_imported_at.setText(record.imported_at)
        self.detail_file_size.setText(_format_file_size(record.file_size))
        self.detail_status.setText(record.status_label)
        self.detail_status.setObjectName(_status_object_name(record.status))
        self.detail_status.style().unpolish(self.detail_status)
        self.detail_status.style().polish(self.detail_status)
        self.detail_record_count.setText(f"{record.record_count:,}")
        self.detail_warning_count.setText(f"{record.warning_count:,}")
        self.detail_source_type.setText(record.source_type or "Not recorded")
        self.detail_context_label.setText(_detail_message(record))

    def _set_empty_state(self) -> None:
        self.inventory_table.setVisible(False)
        self.history_table.setVisible(False)
        self.detail_card.setVisible(False)


def _section_card(title: str, description: str) -> QFrame:
    card = QFrame()
    card.setObjectName("MetricCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(18, 18, 18, 18)
    layout.setSpacing(10)
    title_label = QLabel(title)
    title_label.setObjectName("SectionTitle")
    description_label = QLabel(description)
    description_label.setObjectName("BodyMuted")
    description_label.setWordWrap(True)
    layout.addWidget(title_label)
    layout.addWidget(description_label)
    return card


def _configure_table(table: QTableWidget, *, selectable: bool) -> None:
    table.verticalHeader().setVisible(False)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setFocusPolicy(Qt.StrongFocus if selectable else Qt.NoFocus)
    table.setAlternatingRowColors(True)
    if selectable:
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
    else:
        table.setSelectionMode(QAbstractItemView.NoSelection)


def _selectable_label() -> QLabel:
    label = QLabel()
    label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    label.setWordWrap(True)
    return label


def _clear_layout(layout: QHBoxLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()


def _format_file_size(value: int | None) -> str:
    if value is None:
        return "—"
    if value < 1024:
        return f"{value} B"
    if value < 1024 * 1024:
        return f"{value / 1024:.1f} KB"
    return f"{value / (1024 * 1024):.1f} MB"


def _status_color(status: str) -> str:
    return {
        "completed": "#65d6a8",
        "duplicate": "#f0c674",
        "failed": "#ff7d8c",
        "in_progress": "#8da2c3",
    }.get(status, "#cfe0ff")


def _status_object_name(status: str) -> str:
    return {
        "completed": "ImportStatusCompleted",
        "duplicate": "ImportStatusDuplicate",
        "failed": "ImportStatusFailed",
        "in_progress": "ImportStatusInProgress",
    }.get(status, "ImportStatusUnknown")


def _detail_message(record: ImportHistoryRecord) -> str:
    if record.status == "completed":
        if record.warnings:
            return "Parser warnings:\n" + "\n".join(f"• {warning}" for warning in record.warnings)
        return "No parser warnings were recorded."
    if record.status == "duplicate":
        reference = (
            f"Duplicate of import #{record.duplicate_of_import_id}. "
            if record.duplicate_of_import_id is not None
            else "This file matches a previous import. "
        )
        return reference + "No records were inserted."
    if record.status == "failed":
        return record.detail_message or "No failure details were recorded."
    if record.status == "in_progress":
        return "This import attempt has not reached a terminal state yet."
    return record.detail_message or "No additional details were recorded for this import."
