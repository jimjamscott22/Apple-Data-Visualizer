APP_STYLESHEET = """
QWidget {
    background-color: #09111f;
    color: #eef4ff;
    font-family: "Segoe UI";
    font-size: 14px;
}

QMainWindow, QFrame#AppShell, QWidget#ContentSurface, QWidget#PageRoot {
    background-color: #09111f;
}

QWidget#Sidebar {
    background-color: #0d1729;
    border-right: 1px solid #1d2942;
}

QLabel {
    background: transparent;
}

QWidget#HeaderCard, QFrame#MetricCard, QFrame#EmptyStateCard, QFrame#PlaceholderCard {
    background-color: #0f1b31;
    border: 1px solid #1d2942;
    border-radius: 18px;
}

QLabel#Eyebrow {
    color: #8da2c3;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

QLabel#DisplayTitle {
    font-size: 28px;
    font-weight: 700;
    color: #f6f9ff;
}

QLabel#SectionTitle {
    font-size: 20px;
    font-weight: 700;
    color: #f6f9ff;
}

QLabel#BodyMuted {
    color: #93a8c8;
}

QLabel#MetricValue {
    font-size: 26px;
    font-weight: 700;
}

QLabel#MetricLabel {
    color: #8da2c3;
    font-size: 13px;
    font-weight: 600;
}

QPushButton {
    background-color: #1e6bff;
    border: none;
    border-radius: 12px;
    color: #ffffff;
    padding: 10px 16px;
    font-weight: 700;
}

QPushButton:hover {
    background-color: #3d82ff;
}

QPushButton:pressed {
    background-color: #1659d6;
}

QPushButton#SecondaryButton {
    background-color: #16233b;
    border: 1px solid #253556;
    color: #d7e4ff;
}

QPushButton#SecondaryButton:hover {
    background-color: #1b2d4c;
}

QPushButton#RangeButton {
    background-color: transparent;
    border: 1px solid #253556;
    color: #a9bddb;
    font-weight: 600;
}

QPushButton#RangeButton:hover {
    background-color: #16233b;
}

QPushButton#RangeButton:checked {
    background-color: #1e6bff;
    border: 1px solid #1e6bff;
    color: #ffffff;
}

QPushButton#RangeButton:checked:hover {
    background-color: #3d82ff;
}

QListWidget {
    background: transparent;
    border: none;
    outline: none;
    padding: 8px;
}

QListWidget::item {
    border-radius: 12px;
    padding: 12px 14px;
    margin: 4px 0;
    color: #a9bddb;
}

QListWidget::item:selected {
    background-color: #162845;
    color: #f3f7ff;
}

QListWidget::item:hover:!selected {
    background-color: #111e35;
}

QTableWidget {
    background-color: #0f1b31;
    border: 1px solid #1d2942;
    border-radius: 16px;
    gridline-color: #1d2942;
}

QHeaderView::section {
    background-color: #14233c;
    color: #cfe0ff;
    border: none;
    border-bottom: 1px solid #1d2942;
    padding: 10px;
    font-weight: 700;
}

QScrollArea#PageScrollArea {
    border: none;
    background: transparent;
}

QScrollArea#PageScrollArea > QWidget > QWidget {
    background: transparent;
}

QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #253556;
    border-radius: 5px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background: #34497a;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
    background: transparent;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}
"""
