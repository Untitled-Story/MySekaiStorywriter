import httpx
from PySide6.QtCore import QSize, Signal
from PySide6.QtGui import QGuiApplication, QIcon
from qasync import asyncSlot
from qfluentwidgets import FluentWindow, FluentIcon

# noinspection PyUnresolvedReferences
import app.resources_rc
from .components import MySplashScreen
from .server import FastAPIServer
from .views import MainView, DataView


class Window(FluentWindow):
    data_loaded = Signal(list)

    def __init__(self):
        super().__init__()

        self.model_list = []
        self.splashScreen = MySplashScreen(QIcon(':/icons/logo.ico'), self)
        self.splashScreen.set_icon_size(QSize(192, 192))
        self.splashScreen.raise_()

        self.data_view = DataView(self)
        self.main_view = MainView(self)

        self.data_loaded.connect(self.data_view.on_data_loaded)

        self._register_views()
        self._initialize_window()

        self.server = FastAPIServer()
        if not self.server.server.started:
            self.server.start()

    def _register_views(self):
        self.addSubInterface(self.data_view, FluentIcon.LIBRARY, 'Library')
        self.addSubInterface(self.main_view, FluentIcon.EDIT, 'Edit')

    def _initialize_window(self):
        self.resize(1536, 864)
        self.setWindowTitle("My Sekai Storywriter")

        desktop = QGuiApplication.primaryScreen().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)

    def stop_server(self):
        if self.server.server.started:
            self.server.stop()

    # noinspection PyPep8Naming
    def closeEvent(self, event):
        self.stop_server()
        event.accept()

    @asyncSlot(str)
    async def initialize_data(self):
        async with httpx.AsyncClient() as client:
            response = await client.get('http://127.0.0.1:4521/get-md5/https://storage.sekai.best/sekai-live2d-assets/live2d/model_list.json')
            model_list = response.json()

        self.data_loaded.emit(model_list)
        self.splashScreen.finish()