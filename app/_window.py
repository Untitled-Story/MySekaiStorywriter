from PySide6.QtGui import QGuiApplication
from qfluentwidgets import FluentWindow, FluentIcon

from ._views import MainView, DataView


class Window(FluentWindow):
    def __init__(self):
        super().__init__()

        # self.data_view = DataView(self)
        self.main_view = MainView(self)

        self._register_views()
        self._initialize_window()


    def _register_views(self):
        # self.addSubInterface(self.data_view, FluentIcon.LIBRARY, 'Library')
        self.addSubInterface(self.main_view, FluentIcon.EDIT, 'Edit')

    def _initialize_window(self):
        self.resize(1280, 720)
        self.setWindowTitle("My Sekai Storywriter")

        desktop = QGuiApplication.primaryScreen().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)
