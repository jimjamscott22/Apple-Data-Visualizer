from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.models.dashboard import OverviewData


class MetricCard(QFrame):
    def __init__(self, label: str, value: str, detail: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("MetricCard")
        self.setMaximumHeight(150)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(8)

        label_widget = QLabel(label)
        label_widget.setObjectName("MetricLabel")
        value_widget = QLabel(value)
        value_widget.setObjectName("MetricValue")
        detail_widget = QLabel(detail)
        detail_widget.setObjectName("BodyMuted")
        detail_widget.setWordWrap(True)

        layout.addWidget(label_widget)
        layout.addWidget(value_widget)
        layout.addWidget(detail_widget)
        layout.addStretch()


class EmptyStateCard(QFrame):
    def __init__(self, title: str, body: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("EmptyStateCard")

        self.layout_root = QVBoxLayout(self)
        self.layout_root.setContentsMargins(22, 22, 22, 22)
        self.layout_root.setSpacing(8)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("SectionTitle")
        self.body_label = QLabel(body)
        self.body_label.setObjectName("BodyMuted")
        self.body_label.setWordWrap(True)

        self.layout_root.addWidget(self.title_label)
        self.layout_root.addWidget(self.body_label)

    def set_content(self, title: str, body: str) -> None:
        self.title_label.setText(title)
        self.body_label.setText(body)


class PlaceholderPage(QWidget):
    def __init__(self, title: str, description: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PageRoot")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        card = QFrame()
        card.setObjectName("PlaceholderCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setObjectName("SectionTitle")
        body_label = QLabel(description)
        body_label.setObjectName("BodyMuted")
        body_label.setWordWrap(True)

        card_layout.addWidget(title_label)
        card_layout.addWidget(body_label)

        layout.addWidget(card)
        layout.addStretch()


class OverviewPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PageRoot")

        self.layout_root = QVBoxLayout(self)
        self.layout_root.setContentsMargins(0, 0, 0, 0)
        self.layout_root.setSpacing(18)

        self.metrics_row = QHBoxLayout()
        self.metrics_row.setSpacing(14)
        self.layout_root.addLayout(self.metrics_row)

        self.import_state_card = EmptyStateCard("", "")
        self.layout_root.addWidget(self.import_state_card)

        self.empty_state = EmptyStateCard(
            "Dashboard foundations are ready",
            "Import flow, parser, and sleep analytics are the next implementation milestones. "
            "This page already reads live state from the local database.",
        )
        self.layout_root.addWidget(self.empty_state)
        self.layout_root.addStretch()

    def render(self, overview: OverviewData) -> None:
        while self.metrics_row.count():
            item = self.metrics_row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for metric in overview.metrics:
            self.metrics_row.addWidget(MetricCard(metric.label, metric.value, metric.detail))

        self._replace_card_contents(
            self.import_state_card,
            overview.import_status.title,
            overview.import_status.detail,
        )

    def _replace_card_contents(self, card: EmptyStateCard, title: str, body: str) -> None:
        card.set_content(title, body)
