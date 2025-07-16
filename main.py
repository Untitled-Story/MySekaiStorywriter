import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from app import Window

if __name__ == '__main__':
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    window = Window()
    window.show()
    app.exec()
