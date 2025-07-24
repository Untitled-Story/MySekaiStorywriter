from PySide6.QtGui import QPixmap, Qt, QResizeEvent
from PySide6.QtWidgets import QLabel, QSizePolicy


class ImageDisplayWidget(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(1, 1)
        self.pixmap_raw = None

    def clear(self):
        super().clear()
        self.pixmap_raw = None

    def display_image(self, file_path: str):
        self.pixmap_raw = QPixmap(file_path)
        if self.pixmap_raw.isNull():
            return
        self.setPixmap(self.pixmap_raw.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def resizeEvent(self, event: QResizeEvent):
        if self.pixmap():
            self.setPixmap(self.pixmap_raw.scaled(event.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        super().resizeEvent(event)
