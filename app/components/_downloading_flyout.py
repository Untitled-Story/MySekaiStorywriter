from PySide6.QtWidgets import QVBoxLayout
from qfluentwidgets import FlyoutViewBase, BodyLabel, IndeterminateProgressBar


class DownloadingFlyout(FlyoutViewBase):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.vBoxLayout = QVBoxLayout(self)
        self.label = BodyLabel(text='Downloading Motions...')
        self.progress_bar = IndeterminateProgressBar()

        self.progress_bar.setFixedWidth(140)

        self.vBoxLayout.setSpacing(12)
        self.vBoxLayout.setContentsMargins(20, 16, 20, 16)
        self.vBoxLayout.addWidget(self.label)
        self.vBoxLayout.addWidget(self.progress_bar)
