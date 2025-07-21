from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout
from qfluentwidgets import SubtitleLabel, MessageBoxBase, IndeterminateProgressRing


class SaveFileMessageBox(MessageBoxBase):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.buttonLayout.removeWidget(self.cancelButton)
        self.cancelButton.hide()
        self.cancelButton.clicked.disconnect()
        self.cancelButton.setParent(None)
        self.cancelButton.deleteLater()
        self.buttonLayout.update()
        self.update()

        title_label = SubtitleLabel(text='Saving your story...')

        progress_ring_layout = QHBoxLayout()
        progress_ring_layout.setContentsMargins(0, 20, 0, 20)
        progress_ring_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        progress_ring = IndeterminateProgressRing()
        progress_ring_layout.addWidget(progress_ring)

        self.yesButton.setDisabled(True)

        self.viewLayout.addWidget(title_label)
        self.viewLayout.addLayout(progress_ring_layout)

        self.widget.setMinimumWidth(350)