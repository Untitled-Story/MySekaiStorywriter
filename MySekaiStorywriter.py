import asyncio
import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from qasync import QEventLoop

from app import Window

if __name__ == '__main__':
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)

    event_loop = QEventLoop(app)
    asyncio.set_event_loop(event_loop)

    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)

    window = Window()
    window.show()

    window.setMicaEffectEnabled(True)

    async def initialize_data():
        await window.initialize_data()


    event_loop.create_task(initialize_data())

    with event_loop:
        event_loop.run_until_complete(app_close_event.wait())
