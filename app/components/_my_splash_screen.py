import sys
from typing import Union

from PySide6.QtCore import QSize, QEvent, Qt
from PySide6.QtGui import QIcon, QColor, QPainter
from PySide6.QtWidgets import QWidget, QGraphicsDropShadowEffect
from qfluentwidgets import FluentIconBase, IconWidget, IndeterminateProgressBar, FluentStyleSheet, isDarkTheme
from qfluentwidgets.common.icon import toQIcon
from qframelesswindow import TitleBar


class MySplashScreen(QWidget):
    def __init__(self, icon: Union[str, QIcon, FluentIconBase], parent=None, enable_shadow=True):
        super().__init__(parent=parent)
        self._icon = icon
        self._iconSize = QSize(96, 96)

        self.titleBar = TitleBar(self)
        self.iconWidget = IconWidget(icon, self)
        self.shadowEffect = QGraphicsDropShadowEffect(self)

        self.progressBar = IndeterminateProgressBar(self)
        self.progressBar.setFixedHeight(4)
        self.progressBar.move(0, 0)

        self.iconWidget.setFixedSize(self._iconSize)
        self.shadowEffect.setColor(QColor(0, 0, 0, 50))
        self.shadowEffect.setBlurRadius(15)
        self.shadowEffect.setOffset(0, 4)

        FluentStyleSheet.FLUENT_WINDOW.apply(self.titleBar)

        if enable_shadow:
            self.iconWidget.setGraphicsEffect(self.shadowEffect)

        if parent:
            parent.installEventFilter(self)

        if sys.platform == "darwin":
            self.titleBar.hide()

    def set_icon(self, icon: Union[str, QIcon, FluentIconBase]):
        self._icon = icon
        self.update()

    def icon(self):
        return toQIcon(self._icon)

    def set_icon_size(self, size: QSize):
        self._iconSize = size
        self.iconWidget.setFixedSize(size)
        self.update()

    def icon_size(self):
        return self._iconSize

    def set_title_bar(self, title_bar: QWidget):
        """ set title bar """
        self.titleBar.deleteLater()
        self.titleBar = title_bar
        title_bar.setParent(self)
        title_bar.raise_()
        self.titleBar.resize(self.width(), self.titleBar.height())

    def eventFilter(self, obj, e: QEvent):
        if obj is self.parent():
            if e.type() == QEvent.Type.Resize:
                # noinspection PyUnresolvedReferences
                self.resize(e.size())
            elif e.type() == QEvent.Type.ChildAdded:
                self.raise_()

        return super().eventFilter(obj, e)

    def resizeEvent(self, e):
        total_height = self._iconSize.height() + self.progressBar.height() + 20

        start_y = (self.height() - total_height) // 2

        icon_x = (self.width() - self._iconSize.width()) // 2
        self.iconWidget.move(icon_x, start_y)

        progress_y = start_y + self._iconSize.height()
        padding = 500
        self.progressBar.move(padding, progress_y + 20)
        self.progressBar.resize(self.width() - padding * 2, self.progressBar.height())

        self.titleBar.resize(self.width(), self.titleBar.height())

    def finish(self):
        """ close splash screen """
        self.close()

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setPen(Qt.PenStyle.NoPen)

        # draw background
        c = 32 if isDarkTheme() else 255
        painter.setBrush(QColor(c, c, c))
        painter.drawRect(self.rect())