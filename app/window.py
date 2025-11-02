import asyncio

import httpx
from PySide6.QtCore import QSize, Signal
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtWidgets import QSizePolicy
from httpx_retries import RetryTransport, Retry
from qasync import asyncSlot
from qfluentwidgets import FluentWindow, FluentIcon

# noinspection PyUnresolvedReferences
import app.resources_rc
from .components import MySplashScreen
from .data_model import MetaData
from .server import FastAPIServer
from .views import MainView, DataView


class Window(FluentWindow):
    data_loaded = Signal(list)

    def __init__(self):
        super().__init__()

        self.server = FastAPIServer()
        if not self.server.server.started:
            self.server.start()

        # noinspection HttpUrlsUsage
        self.server_host = f"http://{self.server.host}:{self.server.port}"

        self.model_list = []
        self.splashScreen = MySplashScreen(QIcon(':/icons/logo.ico'), self)
        self.splashScreen.set_icon_size(QSize(192, 192))
        self.splashScreen.raise_()

        self.metadata_model = MetaData()

        self.data_view = DataView(self.metadata_model, self.server_host, self)
        self.main_view = MainView(self.metadata_model, self.server_host, self)

        self.data_loaded.connect(self.data_view.on_data_loaded)
        self.data_view.model_manage_frame.live2d_preview.webview_loaded.connect(self.on_model_live2d_loaded)

        self._register_views()
        self._initialize_window()

        self.model_live2d_loaded_event = asyncio.Event()

    def _register_views(self):
        self.addSubInterface(self.main_view, FluentIcon.EDIT, 'Edit')
        self.addSubInterface(self.data_view, FluentIcon.LIBRARY, 'Library')

    def _initialize_window(self):
        # 1. 首先获取主屏幕的可用几何信息 (这会正确处理缩放比例)
        desktop = QGuiApplication.primaryScreen().availableGeometry()
        available_width = desktop.width()
        available_height = desktop.height()

        desired_width = int(available_width * 0.8)
        desired_height = int(available_height * 0.8)

        self.resize(desired_width, desired_height)

        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        self.setWindowTitle("My Sekai Storywriter")

        self.move(
            available_width // 2 - self.width() // 2,
            available_height // 2 - self.height() // 2
        )

    def stop_server(self):
        if self.server.server.started:
            self.server.stop()

    # noinspection PyPep8Naming
    def closeEvent(self, event):
        self.stop_server()
        event.accept()

    def on_model_live2d_loaded(self):
        self.model_live2d_loaded_event.set()

    @asyncSlot(str)
    async def initialize_data(self):
        retry = Retry(total=10, backoff_factor=0.5)
        async with httpx.AsyncClient(transport=RetryTransport(retry=retry)) as client:
            print(self.server_host)
            response = await client.get(
                f'{self.server_host}/get/https://storage.sekai.best/sekai-live2d-assets/live2d/model_list.json')
            model_list = response.json()

        self.data_loaded.emit(model_list)

        await self.model_live2d_loaded_event.wait()

        self.splashScreen.finish()
