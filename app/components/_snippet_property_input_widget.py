from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QSizePolicy
from qfluentwidgets import SubtitleLabel, setFont


class SnippetPropertyInputWidget(QWidget):
    def __init__(self, title: str, widget: QWidget, parent=None):
        super().__init__(parent)

        self._layout = QHBoxLayout()
        self._layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setLayout(self._layout)

        title_widget = SubtitleLabel(text=f'{title}: ')
        setFont(title_widget, fontSize=16)
        self._layout.addWidget(title_widget)
        self._layout.addWidget(widget)