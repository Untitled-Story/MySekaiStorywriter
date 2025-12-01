from PySide6.QtCore import Signal
from PySide6.QtWidgets import QVBoxLayout, QFrame, QHBoxLayout, QWidget
from qfluentwidgets import CardWidget, IconWidget, FluentIcon, StrongBodyLabel, setFont


class CollapsiblePropertyCard(CardWidget):
    toggled = Signal(bool)

    def __init__(self, title: str, parent=None):
        super().__init__(parent)

        self.is_expanded = False

        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # header
        self.header = QFrame()
        self.header.setFixedHeight(32)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(10, 0, 10, 0)
        header_layout.setSpacing(4)

        # noinspection PyTypeChecker
        self.arrow = IconWidget(FluentIcon.CHEVRON_RIGHT_MED.icon())
        self.arrow.setFixedSize(12, 12)

        # noinspection PyTypeChecker
        self.title_label = StrongBodyLabel(title)
        setFont(self.title_label, 13)

        self.actions = QHBoxLayout()
        self.actions.setSpacing(4)
        self.actions.setContentsMargins(0, 0, 0, 0)

        header_layout.addWidget(self.arrow)
        header_layout.addSpacing(4)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch(1)
        header_layout.addLayout(self.actions)

        # content
        self.content_widget = QWidget()
        self.content_widget.setVisible(False)
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(8, 0, 8, 8)
        content_layout.setSpacing(4)
        self.content_layout = content_layout

        main.addWidget(self.header)
        main.addWidget(self.content_widget)

        self.header.mouseReleaseEvent = self._toggle

    def _toggle(self, _):
        self.is_expanded = not self.is_expanded
        self.content_widget.setVisible(self.is_expanded)
        self._update_arrow()
        self.toggled.emit(self.is_expanded)

    def set_expanded(self, expanded: bool):
        self.is_expanded = expanded
        self.content_widget.setVisible(expanded)
        self._update_arrow()

    def _update_arrow(self):
        icon = FluentIcon.CHEVRON_DOWN_MED if self.is_expanded else FluentIcon.CHEVRON_RIGHT_MED
        self.arrow.setIcon(icon.icon())

    def add_action_widget(self, widget):
        self.actions.addWidget(widget)
