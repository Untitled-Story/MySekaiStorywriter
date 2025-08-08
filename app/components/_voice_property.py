from PySide6.QtWidgets import QWidget, QHBoxLayout, QFileDialog
from qfluentwidgets import LineEdit, PrimaryPushButton


class VoiceProperty(QWidget):
    def __init__(self):
        super().__init__()
        self._layout = QHBoxLayout()
        self.setLayout(self._layout)

        self.path_container = LineEdit()
        self.path_container.setPlaceholderText("Path")
        self._layout.addWidget(self.path_container)

        self.select_btn = PrimaryPushButton(text='Select')
        self.select_btn.clicked.connect(self.on_select_btn_clicked)
        self._layout.addWidget(self.select_btn)

        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(10)

    def on_select_btn_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select a sound",
            "",
            "Sound File (*.ogg *.mp3 *.wav)"
        )
        self.path_container.setText(file_path)

    @property
    def val(self):
        return self.path_container.text()

    @property
    def text_changed(self):
        return self.path_container.textChanged

    @val.setter
    def val(self, value):
        self.path_container.setText(value)
